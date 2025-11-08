"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
SQLite-based storage for collected metrics with optimized performance and memory usage.
"""
import logging
import sqlite3
import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class MetricsStorage:
    """SQLite-based metrics storage with performance optimizations."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MetricsStorage, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, output_dir: str = "/logs", db_name: str = "metrics.db", 
                 max_age_days: int = 7, cleanup_interval_hours: int = 6):
        """Initialize SQLite-based metrics storage.

        Args:
            output_dir: Directory for the database file
            db_name: Name of the SQLite database file
            max_age_days: Maximum age of metrics to keep (default: 7 days)
            cleanup_interval_hours: How often to run cleanup (default: 6 hours)
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.output_dir = output_dir
            self.db_path = os.path.join(output_dir, db_name)
            self.max_age_days = max_age_days
            self.cleanup_interval_hours = cleanup_interval_hours
            self._last_cleanup = datetime.now()
            self._connection_pool = {}
            self._pool_lock = threading.Lock()

            try:
                os.makedirs(self.output_dir, exist_ok=True)
                self._init_database()
                self._create_indexes()
                logger.info(f"SQLite metrics storage initialized: {self.db_path}")
                
                # Run initial cleanup
                self._cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Failed to initialize SQLite storage: {e}")
                raise

            self._initialized = True

    @contextmanager
    def _get_connection(self):
        """Get a thread-safe database connection with connection pooling."""
        thread_id = threading.get_ident()
        
        with self._pool_lock:
            if thread_id not in self._connection_pool:
                conn = sqlite3.connect(
                    self.db_path, 
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                # Performance optimizations
                conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
                conn.execute("PRAGMA cache_size=10000")  # 10MB cache
                conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp
                self._connection_pool[thread_id] = conn
            
            conn = self._connection_pool[thread_id]
        
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e

    def _init_database(self):
        """Initialize database tables with optimized schema."""
        with self._get_connection() as conn:
            # Main metrics table with optimized columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    timestamp_iso TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    source_component TEXT,
                    round_number INTEGER,
                    accuracy REAL,
                    loss REAL,
                    status TEXT,
                    data_json TEXT NOT NULL,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    timestamp_iso TEXT NOT NULL,
                    event_id TEXT,
                    source_component TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_level TEXT DEFAULT 'INFO',
                    message TEXT,
                    details_json TEXT,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # FL training summary table for fast dashboard queries
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fl_training_summary (
                    round_number INTEGER PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    accuracy REAL,
                    loss REAL,
                    training_duration REAL,
                    model_size_mb REAL,
                    clients_count INTEGER,
                    status TEXT,
                    training_complete BOOLEAN DEFAULT 0,
                    updated_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            conn.commit()

    def _create_indexes(self):
        """Create optimized indexes for fast queries."""
        with self._get_connection() as conn:
            # Metrics table indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp ON metrics(metric_type, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_round ON metrics(round_number) WHERE round_number IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_metrics_fl_rounds ON metrics(metric_type, round_number) WHERE metric_type LIKE 'fl_round_%'",
                "CREATE INDEX IF NOT EXISTS idx_metrics_source_timestamp ON metrics(source_component, timestamp DESC)",
                
                # Events table indexes
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_events_component_timestamp ON events(source_component, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_events_type_timestamp ON events(event_type, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_events_level ON events(event_level)",
                
                # FL summary indexes
                "CREATE INDEX IF NOT EXISTS idx_fl_summary_round ON fl_training_summary(round_number DESC)",
                "CREATE INDEX IF NOT EXISTS idx_fl_summary_timestamp ON fl_training_summary(timestamp DESC)"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                except sqlite3.Error as e:
                    logger.warning(f"Index creation warning: {e}")
            
            conn.commit()

    def _should_cleanup(self) -> bool:
        """Check if cleanup should run."""
        now = datetime.now()
        time_since_cleanup = now - self._last_cleanup
        return time_since_cleanup.total_seconds() / 3600 >= self.cleanup_interval_hours

    def _cleanup_old_data(self):
        """Remove old data and optimize database."""
        try:
            # First, cleanup duplicates
            self.cleanup_duplicate_rounds()
            
            cutoff_time = time.time() - (self.max_age_days * 24 * 3600)
            
            # First, perform data operations within transaction
            with self._get_connection() as conn:
                # Archive old FL rounds to summary table before deletion
                conn.execute("""
                    INSERT OR REPLACE INTO fl_training_summary 
                    (round_number, timestamp, accuracy, loss, training_duration, 
                     model_size_mb, clients_count, status, training_complete, updated_at)
                    SELECT 
                        round_number,
                        timestamp,
                        accuracy,
                        loss,
                        JSON_EXTRACT(data_json, '$.training_duration') as training_duration,
                        JSON_EXTRACT(data_json, '$.model_size_mb') as model_size_mb,
                        JSON_EXTRACT(data_json, '$.clients') as clients_count,
                        status,
                        CASE WHEN JSON_EXTRACT(data_json, '$.data_state') = 'training_complete' THEN 1 ELSE 0 END,
                        julianday('now')
                    FROM metrics 
                    WHERE metric_type LIKE 'fl_round_%' 
                    AND round_number IS NOT NULL 
                    AND timestamp < ?
                """, (cutoff_time,))
                
                # Delete old metrics
                result = conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_time,))
                deleted_metrics = result.rowcount
                
                # Delete old events
                result = conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_time,))
                deleted_events = result.rowcount
                
                conn.commit()
                
            # Vacuum database OUTSIDE of transaction context to reclaim space
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("VACUUM")
                conn.close()
                logger.info(f"Cleanup completed: {deleted_metrics} metrics, {deleted_events} events deleted. Database optimized.")
            except sqlite3.Error as vacuum_error:
                logger.warning(f"Database VACUUM operation failed: {vacuum_error} (data cleanup successful)")
                
            self._last_cleanup = datetime.now()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def store_metric(self, metric_type: str, data: dict):
        """Store a metric with optimized processing."""
        if self._should_cleanup():
            self._cleanup_old_data()

        timestamp = time.time()
        timestamp_iso = datetime.now().isoformat()
        
        # Extract common fields for fast queries
        round_number = None
        accuracy = None
        loss = None
        status = None
        source_component = None
        
        # Extract round number from metric type
        if metric_type.startswith('fl_round_'):
            try:
                round_number = int(metric_type.split('_')[-1])
            except (ValueError, IndexError):
                pass
        
        # Extract common fields from data
        if isinstance(data, dict):
            accuracy = data.get('accuracy')
            loss = data.get('loss')
            status = data.get('status')
            source_component = data.get('source_component', data.get('source'))
            
            # Try to extract round from data if not in metric_type
            if round_number is None:
                round_number = data.get('round', data.get('current_round'))

        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO metrics 
                    (timestamp, timestamp_iso, metric_type, source_component, 
                     round_number, accuracy, loss, status, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, timestamp_iso, metric_type, source_component,
                    round_number, accuracy, loss, status, json.dumps(data, default=str)
                ))
                
                # Update FL summary for fast dashboard access
                if round_number is not None and accuracy is not None:
                    model_size_mb = data.get('model_size_mb')
                    
                    # Ensure model_size_mb is properly converted to float
                    try:
                        if model_size_mb is None:
                            model_size_mb = 0.0
                        elif isinstance(model_size_mb, str):
                            model_size_mb = float(model_size_mb) if model_size_mb else 0.0
                        else:
                            model_size_mb = float(model_size_mb)
                    except (ValueError, TypeError):
                        logger.warning(f"Storage: Invalid model_size_mb value '{model_size_mb}' for round {round_number}, using 0.0")
                        model_size_mb = 0.0
                    
                    logger.debug(f"Storage: Storing FL summary for round {round_number} with model_size_mb: {model_size_mb} (type: {type(model_size_mb)})")
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO fl_training_summary 
                        (round_number, timestamp, accuracy, loss, training_duration,
                         model_size_mb, clients_count, status, training_complete, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, julianday('now'))
                    """, (
                        round_number, timestamp, accuracy, loss,
                        data.get('training_duration'), model_size_mb,
                        data.get('clients', data.get('connected_clients')), status,
                        1 if data.get('data_state') == 'training_complete' else 0
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")

    def store_event(self, event: Dict[str, Any]):
        """Store an event efficiently."""
        timestamp = time.time()
        timestamp_iso = datetime.now().isoformat()
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO events 
                    (timestamp, timestamp_iso, event_id, source_component, 
                     event_type, event_level, message, details_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, timestamp_iso,
                    event.get('event_id', event.get('id')),
                    event.get('source_component'),
                    event.get('event_type'),
                    event.get('event_level', event.get('level', 'INFO')),
                    event.get('message'),
                    json.dumps(event.get('details', {}), default=str)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store event: {e}")

    def load_metrics(self, start_time: Optional[str] = None, end_time: Optional[str] = None,
                    type_filter: Optional[str] = None, limit: int = 100, offset: int = 0,
                    sort_desc: bool = True, source_component: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load metrics with optimized SQLite queries."""
        try:
            # Convert time filters to timestamps
            start_ts = None
            end_ts = None
            if start_time:
                try:
                    start_ts = datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp()
                except:
                    pass
            if end_time:
                try:
                    end_ts = datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp()
                except:
                    pass

            # Build optimized query
            where_conditions = []
            params = []
            
            if start_ts:
                where_conditions.append("timestamp >= ?")
                params.append(start_ts)
            if end_ts:
                where_conditions.append("timestamp <= ?")
                params.append(end_ts)
            if type_filter:
                where_conditions.append("metric_type = ?")
                params.append(type_filter)
            if source_component:
                where_conditions.append("source_component = ?")
                params.append(source_component)

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            order_clause = "ORDER BY timestamp DESC" if sort_desc else "ORDER BY timestamp ASC"
            
            query = f"""
                SELECT timestamp_iso as timestamp, metric_type, data_json
                FROM metrics 
                WHERE {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                results = []
                
                for row in cursor:
                    try:
                        data = json.loads(row['data_json'])
                        results.append({
                            'timestamp': row['timestamp'],
                            'metric_type': row['metric_type'],
                            'data': data
                        })
                    except json.JSONDecodeError:
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
            return []

    def get_fl_summary_fast(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get FL training summary data optimized for dashboard charts."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT round_number, timestamp, accuracy, loss, training_duration,
                           model_size_mb, clients_count, status, training_complete
                    FROM fl_training_summary 
                    ORDER BY round_number ASC
                    LIMIT ?
                """, (limit,))
                
                results = []
                for row in cursor:
                    results.append({
                        'round': row['round_number'],
                        'timestamp': datetime.fromtimestamp(row['timestamp']).isoformat(),
                        'accuracy': row['accuracy'] or 0,
                        'loss': row['loss'] or 0,
                        'training_duration': row['training_duration'] or 0,
                        'model_size_mb': row['model_size_mb'] or 0,
                        'clients_count': row['clients_count'] or 0,
                        'status': row['status'] or 'unknown',
                        'training_complete': bool(row['training_complete'])
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error loading FL summary: {e}")
            return []

    def get_latest_fl_metrics(self) -> Optional[Dict[str, Any]]:
        """Get latest FL metrics optimized for dashboard overview."""
        try:
            with self._get_connection() as conn:
                # Get latest FL server metrics
                cursor = conn.execute("""
                    SELECT timestamp_iso, data_json, accuracy, round_number, status
                    FROM metrics 
                    WHERE metric_type = 'fl_server'
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                data = json.loads(row['data_json'])
                
                # Also get latest round summary for accuracy if needed
                if not row['accuracy'] or row['accuracy'] == 0:
                    cursor = conn.execute("""
                        SELECT accuracy, loss FROM fl_training_summary 
                        ORDER BY round_number DESC LIMIT 1
                    """)
                    summary_row = cursor.fetchone()
                    if summary_row:
                        data['latest_accuracy'] = summary_row['accuracy']
                        data['latest_loss'] = summary_row['loss']
                
                return {
                    'timestamp': row['timestamp_iso'],
                    'data': data,
                    'round': row['round_number'] or data.get('current_round', 0),
                    'accuracy': row['accuracy'] or data.get('latest_accuracy', 0),
                    'status': row['status'] or data.get('status', 'unknown')
                }
                
        except Exception as e:
            logger.error(f"Error getting latest FL metrics: {e}")
            return None

    def count_metrics(self, type_filter: Optional[str] = None, source_component: Optional[str] = None) -> int:
        """Count metrics efficiently."""
        try:
            where_conditions = []
            params = []
            
            if type_filter:
                where_conditions.append("metric_type = ?")
                params.append(type_filter)
            if source_component:
                where_conditions.append("source_component = ?")
                params.append(source_component)

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            with self._get_connection() as conn:
                cursor = conn.execute(f"SELECT COUNT(*) FROM metrics WHERE {where_clause}", params)
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error counting metrics: {e}")
            return 0

    def load_events(self, start_time: Optional[str] = None, end_time: Optional[str] = None,
                   source_component: Optional[str] = None, event_type: Optional[str] = None, 
                   limit: int = 100, offset: int = 0, sort_desc: bool = True,
                   component: Optional[str] = None, level: Optional[str] = None,
                   since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load events efficiently."""
        try:
            # Handle backward compatibility
            if component and not source_component:
                source_component = component

            # Convert time filters
            start_ts = None
            end_ts = None
            if start_time:
                try:
                    start_ts = datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp()
                except:
                    pass
            if end_time:
                try:
                    end_ts = datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp()
                except:
                    pass

            # Build query
            where_conditions = []
            params = []
            
            if start_ts:
                where_conditions.append("timestamp >= ?")
                params.append(start_ts)
            if end_ts:
                where_conditions.append("timestamp <= ?")
                params.append(end_ts)
            if source_component:
                where_conditions.append("source_component = ?")
                params.append(source_component)
            if event_type:
                where_conditions.append("event_type = ?")
                params.append(event_type)
            if level:
                where_conditions.append("event_level = ?")
                params.append(level)
            if since_id:
                where_conditions.append("id > ?")
                params.append(int(since_id))

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            order_clause = "ORDER BY timestamp DESC" if sort_desc else "ORDER BY timestamp ASC"
            
            query = f"""
                SELECT id, timestamp_iso, event_id, source_component, event_type, 
                       event_level, message, details_json
                FROM events 
                WHERE {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                results = []
                
                for row in cursor:
                    try:
                        details = json.loads(row['details_json'] or '{}')
                        results.append({
                            'id': row['id'],
                            'event_id': row['event_id'],
                            'timestamp': row['timestamp_iso'],
                            'source_component': row['source_component'],
                            'component': row['source_component'],  # Compatibility
                            'event_type': row['event_type'],
                            'event_level': row['event_level'],
                            'level': row['event_level'],  # Compatibility
                            'message': row['message'],
                            'details': details
                        })
                    except json.JSONDecodeError:
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Error loading events: {e}")
            return []

    def count_events(self, source_component: Optional[str] = None, event_type: Optional[str] = None,
                    level: Optional[str] = None) -> int:
        """Count events efficiently."""
        try:
            where_conditions = []
            params = []
            
            if source_component:
                where_conditions.append("source_component = ?")
                params.append(source_component)
            if event_type:
                where_conditions.append("event_type = ?")
                params.append(event_type)
            if level:
                where_conditions.append("event_level = ?")
                params.append(level)

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            with self._get_connection() as conn:
                cursor = conn.execute(f"SELECT COUNT(*) FROM events WHERE {where_clause}", params)
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error counting events: {e}")
            return 0

    def close(self):
        """Close all database connections."""
        with self._pool_lock:
            for conn in self._connection_pool.values():
                try:
                    conn.close()
                except:
                    pass
            self._connection_pool.clear()
        logger.info("SQLite storage connections closed")

    def cleanup_duplicate_rounds(self):
        """Remove duplicate round records keeping only the latest entry per round."""
        try:
            with self._get_connection() as conn:
                # Remove duplicates from metrics table, keeping only the latest timestamp for each round
                conn.execute("""
                    DELETE FROM metrics 
                    WHERE id NOT IN (
                        SELECT MAX(id) 
                        FROM metrics 
                        WHERE metric_type LIKE 'fl_round_%' 
                        AND round_number IS NOT NULL 
                        GROUP BY round_number
                    ) 
                    AND metric_type LIKE 'fl_round_%'
                    AND round_number IS NOT NULL
                """)
                
                # Remove duplicates from FL training summary
                conn.execute("""
                    DELETE FROM fl_training_summary 
                    WHERE rowid NOT IN (
                        SELECT MAX(rowid) 
                        FROM fl_training_summary 
                        GROUP BY round_number
                    )
                """)
                
                conn.commit()
                logger.debug("Cleaned up duplicate round records")
                
        except Exception as e:
            logger.error(f"Error cleaning up duplicate rounds: {e}")