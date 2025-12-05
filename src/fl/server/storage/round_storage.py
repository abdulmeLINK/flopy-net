"""
FL Round Storage

Persistent storage for Federated Learning rounds using SQLite.
"""

import json
import logging
import sqlite3
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FLRoundStorage:
    """Persistent storage for FL rounds using SQLite."""
    
    def __init__(self, db_path: str = "./fl_rounds.db"):
        """Initialize the FL rounds storage."""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fl_rounds (
                    round_number INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'complete',
                    accuracy REAL DEFAULT 0.0,
                    loss REAL DEFAULT 0.0,
                    training_duration REAL DEFAULT 0.0,
                    model_size_mb REAL DEFAULT 0.0,
                    clients INTEGER DEFAULT 0,
                    raw_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_round_number ON fl_rounds(round_number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON fl_rounds(timestamp)')
            conn.commit()
    
    def store_round(self, round_data: Dict[str, Any]):
        """Store a round's data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO fl_rounds 
                    (round_number, timestamp, status, accuracy, loss, training_duration, 
                     model_size_mb, clients, raw_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    round_data.get('round', 0),
                    round_data.get('timestamp', datetime.datetime.now(datetime.timezone.utc).isoformat()),
                    round_data.get('status', 'complete'),
                    round_data.get('accuracy', 0.0),
                    round_data.get('loss', 0.0),
                    round_data.get('training_duration', 0.0),
                    round_data.get('model_size_mb', 0.0),
                    round_data.get('clients', 0),
                    json.dumps(round_data.get('raw_metrics', {}))
                ))
                conn.commit()
                logger.debug(f"Stored round {round_data.get('round', 0)} to persistent storage")
        except Exception as e:
            logger.error(f"Error storing round data: {e}")
    
    def get_rounds(
        self, 
        start_round: int = 1, 
        end_round: Optional[int] = None, 
        limit: int = 1000, 
        offset: int = 0, 
        min_accuracy: Optional[float] = None, 
        max_accuracy: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get rounds with filtering and limiting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query with filters
                where_clauses = ["round_number >= ?"]
                params: List[Any] = [start_round]
                
                if end_round is not None:
                    where_clauses.append("round_number <= ?")
                    params.append(end_round)
                
                if min_accuracy is not None:
                    where_clauses.append("accuracy >= ?")
                    params.append(min_accuracy)
                
                if max_accuracy is not None:
                    where_clauses.append("accuracy <= ?")
                    params.append(max_accuracy)
                
                where_clause = " AND ".join(where_clauses)
                
                query = f'''
                    SELECT round_number as round, timestamp, status, accuracy, loss, 
                           training_duration, model_size_mb, clients, raw_metrics
                    FROM fl_rounds 
                    WHERE {where_clause}
                    ORDER BY round_number ASC
                    LIMIT ? OFFSET ?
                '''
                
                params.extend([limit, offset])
                cursor = conn.execute(query, params)
                
                rounds = []
                for row in cursor.fetchall():
                    round_data = dict(row)
                    # Parse raw_metrics back to dict
                    try:
                        round_data['raw_metrics'] = json.loads(round_data.get('raw_metrics', '{}'))
                    except Exception:
                        round_data['raw_metrics'] = {}
                    rounds.append(round_data)
                
                return rounds
        except Exception as e:
            logger.error(f"Error getting rounds: {e}")
            return []
    
    def get_round_count(
        self, 
        start_round: int = 1, 
        end_round: Optional[int] = None,
        min_accuracy: Optional[float] = None, 
        max_accuracy: Optional[float] = None
    ) -> int:
        """Get total count of rounds matching criteria."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                where_clauses = ["round_number >= ?"]
                params: List[Any] = [start_round]
                
                if end_round is not None:
                    where_clauses.append("round_number <= ?")
                    params.append(end_round)
                
                if min_accuracy is not None:
                    where_clauses.append("accuracy >= ?")
                    params.append(min_accuracy)
                
                if max_accuracy is not None:
                    where_clauses.append("accuracy <= ?")
                    params.append(max_accuracy)
                
                where_clause = " AND ".join(where_clauses)
                query = f"SELECT COUNT(*) FROM fl_rounds WHERE {where_clause}"
                
                cursor = conn.execute(query, params)
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting round count: {e}")
            return 0
    
    def get_latest_round_number(self) -> int:
        """Get the latest round number."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT MAX(round_number) FROM fl_rounds")
                result = cursor.fetchone()[0]
                return result if result is not None else 0
        except Exception as e:
            logger.error(f"Error getting latest round: {e}")
            return 0
    
    def delete_round(self, round_number: int) -> bool:
        """Delete a specific round."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM fl_rounds WHERE round_number = ?", (round_number,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting round {round_number}: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all rounds from storage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM fl_rounds")
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing all rounds: {e}")
            return False
