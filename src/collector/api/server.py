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
RESTful API Server for Metrics Collector.

This module provides a comprehensive Flask-based REST API for accessing metrics 
collected by the collector with a focus on raw data access and filtering capabilities.
"""

import os
import sys
import json
import logging
import threading
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any

from flask import Flask, jsonify, request, Response, send_file, Blueprint
from flask_cors import CORS
from flask_restful import Api, Resource
from werkzeug.middleware.proxy_fix import ProxyFix

# Ensure src is in the path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.collector.storage import MetricsStorage
from src.collector.api.services.fl_response_builder import (
    build_fl_response,
    optimize_fl_metrics_query,
)
from src.collector.api.routes import fl_bp, init_fl_routes, network_bp, init_network_routes

# Configure logging
logging.basicConfig(
    level=os.getenv("API_LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables for configuration
API_PORT = int(os.getenv("METRICS_API_PORT", "8000"))
METRICS_DIR = os.getenv("METRICS_OUTPUT_DIR", "/logs")
ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() in ("true", "1", "t", "yes")
API_ALLOWED_ORIGINS = os.getenv("API_ALLOWED_ORIGINS", "*")
API_AUTH_ENABLED = os.getenv("API_AUTH_ENABLED", "false").lower() in ("true", "1", "t", "yes")
API_USERNAME = os.getenv("API_USERNAME", "admin")
API_PASSWORD = os.getenv("API_PASSWORD", "securepassword")
API_OUTPUT_FORMAT = os.getenv("API_OUTPUT_FORMAT", "json").lower()

# Initialize Blueprint instead of Flask app for better integration
api_bp = Blueprint('api', __name__)

# Initialize storage
storage = MetricsStorage(output_dir=METRICS_DIR)

# **PERFORMANCE CACHE**
# Simple in-memory cache for frequently accessed data
_fl_metrics_cache = {}
_cache_ttl = 10  # Cache for 10 seconds
_last_cache_time = 0

# Simple authentication middleware if enabled
if API_AUTH_ENABLED:
    import base64
    from functools import wraps
    from flask import request, Response
    
    def check_auth(username, password):
        """Check if the username and password are valid."""
        return username == API_USERNAME and password == API_PASSWORD
    
    def authenticate():
        """Send a 401 response that enables basic auth."""
        return Response(
            'Authentication required', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )
    
    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
            return f(*args, **kwargs)
        return decorated
else:
    # If auth is disabled, use a no-op decorator
    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated

# **PERFORMANCE HELPER FUNCTIONS**
def _get_cached_fl_metrics(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached FL metrics if available and not expired."""
    global _last_cache_time, _fl_metrics_cache
    
    current_time = time.time()
    
    # Check if cache is expired
    if current_time - _last_cache_time > _cache_ttl:
        _fl_metrics_cache.clear()
        _last_cache_time = current_time
        return None
    
    return _fl_metrics_cache.get(cache_key)

def _cache_fl_metrics(cache_key: str, data: Dict[str, Any]) -> None:
    """Cache FL metrics data."""
    global _fl_metrics_cache
    _fl_metrics_cache[cache_key] = data

def _optimize_fl_metrics_query(limit: int, include_rounds: bool, rounds_only: bool) -> Dict[str, Any]:
    """Optimize FL metrics query parameters based on request size."""
    
    # For large requests, use optimized strategies
    if limit > 500:
        # Large dataset - use sampling and reduced data
        optimized_params = {
            "use_sampling": True,
            "sample_rate": min(0.5, 1000 / limit),  # Sample rate to keep reasonable data size
            "include_raw": False,
            "consolidate_rounds": True,
            "batch_size": 200  # Process in smaller batches
        }
    elif limit > 100:
        # Medium dataset - moderate optimization
        optimized_params = {
            "use_sampling": False,
            "include_raw": False,
            "consolidate_rounds": True,
            "batch_size": 100
        }
    else:
        # Small dataset - minimal optimization
        optimized_params = {
            "use_sampling": False,
            "include_raw": include_rounds,
            "consolidate_rounds": True,
            "batch_size": 50
        }
    
    return optimized_params

# API Documentation
@api_bp.route('/', methods=['GET'])
def api_docs():
    """API documentation endpoint."""
    return jsonify({
        "api": "Metrics Collector API",
        "version": "2.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "GET /api/metrics": "Get all metrics with filtering options",
            "GET /api/metrics/latest": "Get latest metrics snapshot",
            "GET /api/metrics/fl": "Get federated learning metrics with enhanced round tracking",
            "GET /api/metrics/fl/rounds": "ENHANCED: Comprehensive FL rounds endpoint (consolidates summary, chart-data, updates)",
            "GET /api/metrics/fl/status": "Get current FL training status and monitoring state",
            "GET /api/metrics/fl/config": "Get FL configuration and hyperparameters from FL server and policy engine",
            "GET /api/metrics/policy": "Get policy engine metrics",
            "GET /api/metrics/network": "Get network metrics",
            "GET /api/metrics/time-range": "Get metrics within a time range",
            "GET /api/metrics/history": "Get historical metrics with pagination",
            "GET /api/metrics/export": "Export metrics as JSON or CSV",
            "GET /api/metrics/status": "Get monitoring service status",
            "GET /api/events": "Get events log with filtering by component, level, and time",
            "GET /api/events/summary": "Get event counts by component and level",
            "GET /api/policy/decisions": "Get policy decision metrics",
            "GET /api/network/topology": "Get detailed network topology from GNS3 and SDN controller",
            "GET /api/network/topology/live": "Get live network topology with real-time updates",
            "POST /api/metrics/query": "Query metrics with complex filters",
            "WS /api/metrics/stream": "WebSocket for real-time metrics updates"
        },
        "fl_rounds_consolidated_features": {
            "multi_format_support": "Supports detailed, summary, and chart-optimized response formats",
            "polling_mode": "Real-time incremental updates with polling_mode=true parameter",
            "comprehensive_filtering": "Round range, accuracy thresholds, data source selection",
            "multiple_sources": "Combines FL server direct access with collector storage",
            "statistics_integration": "Optional training statistics with include_stats=true",
            "chart_optimization": "Chart-ready data format with include_charts=true",
            "performance_tracking": "Execution time monitoring and optimization",
            "enhanced_accuracy_extraction": "Improved accuracy parsing from multiple data formats",
            "replaces_endpoints": [
                "/api/metrics/fl/summary (use format=summary)",
                "/api/metrics/fl/chart-data (use format=chart or include_charts=true)",
                "/api/metrics/fl/rounds/updates (use polling_mode=true)"
            ]
        },
        "fl_metrics_features": {
            "comprehensive_tracking": "Captures both FL server snapshots and individual round metrics for complete coverage",
            "round_filtering": "Filter by round range (min_round, max_round) and accuracy thresholds",
            "multiple_sources": "Combines data from fl_server snapshots and individual fl_round_* metrics",
            "enhanced_statistics": "Provides training summaries, accuracy improvements, and completion tracking",
            "pagination": "Supports limit/offset for large training sessions",
            "real_time": "5-second collection interval for better round coverage",
            "individual_rounds": "Access to detailed per-round metrics via /api/metrics/fl/rounds endpoint"
        },
        "events_features": {
            "filtering": "Filter events by source_component/component, event_type, level, and time range",
            "pagination": "Limit and offset for pagination",
            "real_time": "Get new events since a specific ID using since_id parameter",
            "compatibility": "Works with both source_component/component and event_level/level naming"
        },
        "metrics_features": {
            "filtering": "Filter metrics by type, component, and time range",
            "aggregation": "Aggregate metrics by time interval",
            "pagination": "Limit and offset for pagination",
            "real_time": "WebSocket for real-time updates"
        }
    })

@api_bp.route('/debug/storage', methods=['GET'])
def debug_storage():
    """Debug storage configuration and basic functionality."""
    import os
    
    try:
        # Get storage info
        storage_info = {
            "storage_type": type(storage).__name__,
            "storage_output_dir": getattr(storage, 'output_dir', None),
            "storage_config": getattr(storage, 'config', {}),
            "metrics_dir_env": os.getenv("METRICS_OUTPUT_DIR"),
            "current_working_dir": os.getcwd()
        }
        
        # Try to get database file path if available
        try:
            if hasattr(storage, 'db_path'):
                storage_info["db_path"] = storage.db_path
                storage_info["db_exists"] = os.path.exists(storage.db_path)
                if os.path.exists(storage.db_path):
                    storage_info["db_size_bytes"] = os.path.getsize(storage.db_path)
            elif hasattr(storage, 'filepath'):
                storage_info["storage_filepath"] = storage.filepath  
                storage_info["storage_exists"] = os.path.exists(storage.filepath)
                if os.path.exists(storage.filepath):
                    storage_info["storage_size_bytes"] = os.path.getsize(storage.filepath)
        except Exception as e:
            storage_info["storage_path_error"] = str(e)
        
        # Test basic loading
        try:
            # Check for different metric types
            total_metrics = storage.count_metrics() if hasattr(storage, 'count_metrics') else 0
            
            # Try to get FL server metrics
            if hasattr(storage, 'count_metrics'):
                fl_server_count = storage.count_metrics(type_filter='fl_server')
                storage_info["fl_server_metrics_count"] = fl_server_count
            
            # Get sample metrics
            if hasattr(storage, 'load_metrics'):
                sample_metrics = storage.load_metrics(limit=5)
                storage_info["sample_metrics_count"] = len(sample_metrics)
                storage_info["sample_metric_types"] = list(set(m.get('metric_type', 'unknown') for m in sample_metrics))
            
            storage_info["total_metrics_count"] = total_metrics
            
        except Exception as e:
            storage_info["loading_error"] = str(e)
        
        return jsonify(storage_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Metrics endpoints
@api_bp.route('/metrics', methods=['GET'])
@requires_auth
def get_all_metrics():
    """Get all metrics with filtering options."""
    try:
        # Parse query parameters with memory-safe limits
        start_time = request.args.get('start')
        end_time = request.args.get('end')
        type_filter = request.args.get('type')
        source_component_filter = request.args.get('source_component')
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        sort_by = request.args.get('sort_by', default='timestamp')
        sort_desc = request.args.get('sort_desc', 'true').lower() in ('true', '1', 't', 'yes')
        
        # MEMORY OPTIMIZATION: Enforce strict limits
        limit = min(limit, 1000)  # Maximum 1000 items per request
        offset = max(0, offset)   # No negative offsets
        
        # Load metrics from storage
        metrics = storage.load_metrics(
            start_time=start_time, 
            end_time=end_time,
            type_filter=type_filter,
            source_component=source_component_filter,
            limit=limit,
            offset=offset,
            sort_desc=sort_desc
        )
        
        return jsonify({
            "status": "success",
            "count": len(metrics),
            "offset": offset,
            "limit": limit,
            "total": storage.count_metrics(
                type_filter=type_filter,
                source_component=source_component_filter
            ),
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api_bp.route('/metrics/latest', methods=['GET'])
@requires_auth
def get_latest_metrics():
    """Get the latest metrics snapshot with optimized SQLite queries."""
    try:
        # Get filter parameters
        type_filter = request.args.get('type')
        
        # Use optimized method for FL server metrics
        if type_filter == 'fl_server':
            latest_fl = storage.get_latest_fl_metrics()
            if not latest_fl:
                return jsonify({
                    "status": "success",
                    "message": "No FL metrics found",
                    "metrics": {}
                })
            
            data = latest_fl['data']
            
            # Determine training status
            status = "idle"
            if data.get('training_complete', False):
                status = "complete"
            elif data.get('status') == "unavailable":
                status = "error"
            elif data.get('evaluating', False):
                status = "evaluating"
            elif data.get('aggregating', False):
                status = "aggregating"
            elif latest_fl['round'] > 0:
                status = "training"
            
            # Format the response for the dashboard
            formatted_response = {
                "status": "success",
                "timestamp": latest_fl['timestamp'],
                "round": latest_fl['round'],
                "status": status,
                "accuracy": latest_fl['accuracy'],
                "loss": data.get('loss', data.get('latest_loss', 0)),
                "clients_connected": data.get('connected_clients', 0),
                "clients_total": data.get('total_clients', 0),
                "start_time": data.get('start_time', latest_fl['timestamp']),
                "last_update": latest_fl['timestamp'],
                "training_complete": data.get('training_complete', False),
                "training_duration": data.get('total_training_duration', 0),
                "raw_metrics": data  # Include raw data for debugging
            }
            
            return jsonify(formatted_response)
        
        # For other metric types, use standard method
        metrics = storage.load_metrics(
            limit=1,
            type_filter=type_filter,
            sort_desc=True
        )
        
        if not metrics:
            return jsonify({
                "status": "success",
                "message": "No metrics found",
                "metrics": {}
            })
        
        return jsonify({
            "status": "success",
            "timestamp": metrics[0].get('timestamp', datetime.utcnow().isoformat()),
            "metrics": metrics[0]
        })
    except Exception as e:
        logger.error(f"Error retrieving latest metrics: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Add events endpoint for the API blueprint
@api_bp.route('/events', methods=['GET'])
@requires_auth
def get_events():
    """
    Get events from the collector storage.
    
    Query parameters:
        start_time: ISO format timestamp for filtering events after this time
        end_time: ISO format timestamp for filtering events before this time
        source_component: Filter by source component (FL_SERVER, POLICY_ENGINE, COLLECTOR)
        component: Alias for source_component (backward compatibility)
        event_type: Filter by event type
        event_level: Filter by event level
        level: Alias for event_level (backward compatibility)
        limit: Maximum number of results to return (default: 100)
        offset: Number of results to skip (default: 0)
        since_id: Get events with ID greater than this value
    """
    try:
        # Parse query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        source_component = request.args.get('source_component')
        component = request.args.get('component')  # Dashboard compatibility
        event_type = request.args.get('event_type')
        event_level = request.args.get('event_level')
        level = request.args.get('level')  # Dashboard compatibility
        limit = int(request.args.get('limit', 100))  # No hard maximum limit
        offset = int(request.args.get('offset', 0))
        since_id = request.args.get('since_id')
        
        # Use component as fallback for source_component
        if not source_component and component:
            source_component = component
            
        # Use level as fallback for event_level
        if not event_level and level:
            event_level = level
        
        # Get matching events
        events = storage.load_events(
            start_time=start_time,
            end_time=end_time,
            source_component=source_component,
            event_type=event_type,
            level=event_level,
            limit=limit,
            offset=offset,
            sort_desc=True
        )
        
        # Get total count for pagination
        total_count = storage.count_events(
            source_component=source_component,
            event_type=event_type,
            level=event_level
        )
        
        # Format events for dashboard compatibility
        for event in events:
            # Add 'component' field if not exists for dashboard compatibility
            if 'source_component' in event and 'component' not in event:
                event['component'] = event['source_component']
                
            # Add 'message' field if not exists for dashboard compatibility
            if 'message' not in event:
                if 'details' in event and event['details']:
                    try:
                        if isinstance(event['details'], str):
                            event['message'] = event['details']
                        else:
                            event['message'] = f"{event.get('event_type', 'Event')}: {json.dumps(event['details'])}"
                    except:
                        event['message'] = f"{event.get('event_type', 'Event')}"
                else:
                    event['message'] = event.get('event_type', 'Unknown event')
                    
            # Add 'level' field if not exists for dashboard compatibility, defaulting to INFO
            if 'level' not in event or not event['level']:
                event['level'] = event.get('event_level') or "INFO"
            # Ensure event_level also exists for full compatibility, mirroring level
            if 'event_level' not in event or not event['event_level']:
                event['event_level'] = event['level']
        
        return jsonify({
            'events': events,
            'total': total_count,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error in /events endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/events/summary', methods=['GET'])
@requires_auth
def get_events_summary():
    """
    Get summary information about events.
    
    Returns count of events by component, by level, and total.
    
    Query parameters:
        source_component: Filter by source component
        component: Alias for source_component
        event_type: Filter by event type
        event_level: Filter by event level
        level: Alias for event_level
    """
    try:
        # Parse query parameters
        source_component = request.args.get('source_component')
        component = request.args.get('component')  # Dashboard compatibility
        event_type = request.args.get('event_type')
        event_level = request.args.get('event_level')
        level = request.args.get('level')  # Dashboard compatibility
        
        # Use component as fallback for source_component
        if not source_component and component:
            source_component = component
            
        # Use level as fallback for event_level
        if not event_level and level:
            event_level = level
        
        # Get events matching the filters
        # Use a reasonable default for summary but allow override
        summary_limit = int(request.args.get('summary_limit', 5000))  # Higher default for better accuracy
        events = storage.load_events(
            source_component=source_component,
            event_type=event_type,
            level=event_level,
            limit=summary_limit,  # Configurable limit for summary calculation
            sort_desc=True
        )
        
        # Get total count
        total_count = storage.count_events(
            source_component=source_component,
            event_type=event_type,
            level=event_level
        )
        
        # Count by component and level
        by_component = {}
        by_level = {}
        by_source_component = {}  # Also store original field name
        by_event_level = {}      # Also store original field name
        
        for event in events:
            # Count by component
            component = event.get('component', event.get('source_component', 'unknown'))
            by_component[component] = by_component.get(component, 0) + 1
            
            # Count by original field name too
            source_component = event.get('source_component', 'unknown')
            by_source_component[source_component] = by_source_component.get(source_component, 0) + 1
            
            # Count by level
            level = event.get('level', event.get('event_level', 'INFO'))
            by_level[level] = by_level.get(level, 0) + 1
            
            # Count by original field name too
            event_level = event.get('event_level', 'INFO')
            by_event_level[event_level] = by_event_level.get(event_level, 0) + 1
        
        # If we sampled, adjust the counts proportionally
        if events and total_count > len(events):
            ratio = total_count / len(events)
            
            for comp in by_component:
                by_component[comp] = int(by_component[comp] * ratio)
                
            for comp in by_source_component:
                by_source_component[comp] = int(by_source_component[comp] * ratio)
                
            for lvl in by_level:
                by_level[lvl] = int(by_level[lvl] * ratio)
                
            for lvl in by_event_level:
                by_event_level[lvl] = int(by_event_level[lvl] * ratio)
        
        return jsonify({
            'by_component': by_component,
            'by_source_component': by_source_component,
            'by_level': by_level,
            'by_event_level': by_event_level,
            'total': total_count
        })
    except Exception as e:
        logger.error(f"Error in /events/summary endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/policy/decisions', methods=['GET'])
@requires_auth
def get_policy_decisions():
    """
    Get policy decisions by proxying to the policy engine.
    
    Query parameters:
        start_time: Start time for filtering decisions
        end_time: End time for filtering decisions
        policy_id: Filter by policy ID
        component: Filter by component
        result: Filter by result (allow/deny)
        limit: Maximum number of decisions to return (default: 500)
    """
    try:
        import requests
        
        # Get query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        policy_id = request.args.get('policy_id')
        component = request.args.get('component')
        result = request.args.get('result')
        limit = int(request.args.get('limit', 500))
        
        # Build policy engine URL
        policy_engine_url = os.getenv("POLICY_ENGINE_URL", "http://localhost:5000")
        
        # Build request parameters
        params = {}
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
        if policy_id:
            params['policy_id'] = policy_id
        if component:
            params['component'] = component
        if result:
            params['result'] = result
        if limit:
            params['limit'] = limit
        
        # Make request to policy engine
        response = requests.get(
            f"{policy_engine_url}/api/v1/policy_decisions",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            decisions = response.json()
            return jsonify(decisions)
        else:
            logger.warning(f"Policy engine returned status {response.status_code}")
            return jsonify([]), response.status_code
            
    except Exception as e:
        logger.error(f"Error fetching policy decisions: {e}")
        return jsonify({
            "error": str(e),
            "decisions": []
        }), 500

# Add database optimization endpoint
@api_bp.route('/debug/optimize', methods=['POST'])
@requires_auth
def optimize_database():
    """Manually trigger database optimization."""
    try:
        # Force cleanup and optimization
        storage._cleanup_old_data()
        
        # Get database stats
        with storage._get_connection() as conn:
            # Get table sizes
            cursor = conn.execute("""
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=main.name) as table_count
                FROM sqlite_master WHERE type='table'
            """)
            tables = cursor.fetchall()
            
            stats = {}
            for table in tables:
                table_name = table['name']
                if table_name.startswith('sqlite_'):
                    continue
                    
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats[table_name] = count
            
            # Get database file size
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_mb = (page_count * page_size) / (1024 * 1024)
        
        return jsonify({
            'status': 'success',
            'message': 'Database optimization completed',
            'table_counts': stats,
            'database_size_mb': round(db_size_mb, 2),
            'optimization_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# Network topology and flows routes moved to routes/network_routes.py

@api_bp.route('/performance/metrics', methods=['GET'])
@requires_auth
def get_performance_metrics():
    """
    Get comprehensive network performance metrics with health scoring.
    
    This endpoint provides detailed performance data including:
    - Real-time bandwidth, latency, and packet statistics
    - Network health score (0-100)
    - Port statistics with error rates
    - Performance trends and aggregations
    """
    try:
        # Get network monitor instance
        if not hasattr(storage, 'network_monitor') or not storage.network_monitor:
            return jsonify({
                'error': 'Network monitor not available',
                'message': 'Network monitoring service is not running'
            }), 503
        
        # Get performance metrics from network monitor
        try:
            performance_metrics = storage.network_monitor._get_sdn_performance_metrics()
            
            if not performance_metrics:
                return jsonify({
                    'error': 'No performance data available',
                    'message': 'Unable to collect performance metrics from SDN controller',
                    'timestamp': time.time()
                }), 503
            
            # Calculate network health score (0-100)
            health_score = 100
            
            # Reduce score based on latency (target: < 50ms)
            avg_latency = performance_metrics.get('latency', {}).get('average', 0)
            if avg_latency > 50:
                health_score -= min(30, (avg_latency - 50) / 2)  # Max 30 point reduction
            
            # Reduce score based on low bandwidth utilization (target: > 10 Mbps)
            avg_bandwidth = performance_metrics.get('bandwidth', {}).get('average', 0)
            if avg_bandwidth < 10:  # Less than 10 Mbps
                health_score -= min(20, (10 - avg_bandwidth) * 2)  # Max 20 point reduction
            
            # Reduce score based on packet errors
            total_errors = sum([
                performance_metrics.get('port_statistics', {}).get('total_rx_errors', 0),
                performance_metrics.get('port_statistics', {}).get('total_tx_errors', 0)
            ])
            if total_errors > 0:
                health_score -= min(25, total_errors / 10)  # Max 25 point reduction
            
            # Reduce score based on flow efficiency
            flow_count = performance_metrics.get('flow_statistics', {}).get('total_flows', 0)
            if flow_count == 0:
                health_score -= 15  # No flows active
            elif flow_count > 1000:
                health_score -= min(10, (flow_count - 1000) / 100)  # Too many flows
            
            health_score = max(0, min(100, round(health_score, 1)))
            
            # Add health score and additional metadata
            performance_metrics['network_health'] = {
                'score': health_score,
                'status': 'excellent' if health_score >= 90 else 
                         'good' if health_score >= 75 else 
                         'fair' if health_score >= 50 else 'poor',
                'factors': {
                    'latency_impact': max(0, min(30, (avg_latency - 50) / 2)) if avg_latency > 50 else 0,
                    'bandwidth_impact': max(0, min(20, (10 - avg_bandwidth) * 2)) if avg_bandwidth < 10 else 0,
                    'error_impact': min(25, total_errors / 10) if total_errors > 0 else 0,
                    'flow_impact': 15 if flow_count == 0 else (min(10, (flow_count - 1000) / 100) if flow_count > 1000 else 0)
                }
            }
            
            performance_metrics['collection_timestamp'] = time.time()
            performance_metrics['source'] = 'sdn_controller'
            
            return jsonify(performance_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
            return jsonify({
                'error': 'Performance metrics collection failed',
                'message': str(e),
                'timestamp': time.time()
            }), 500
    
    except Exception as e:
        logger.error(f"Error in performance metrics endpoint: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve performance metrics'
        }), 500

@api_bp.route('/flows/statistics', methods=['GET'])
@requires_auth
def get_flow_statistics():
    """
    Get comprehensive flow statistics with efficiency calculations.
    
    This endpoint provides detailed flow analysis including:
    - Flow distribution by priority, table, and type
    - Match criteria and action statistics
    - Flow efficiency metrics
    - Bandwidth utilization per flow
    """
    try:
        # Get network monitor instance
        if not hasattr(storage, 'network_monitor') or not storage.network_monitor:
            return jsonify({
                'error': 'Network monitor not available',
                'message': 'Network monitoring service is not running'
            }), 503
        
        # Get flow statistics from network monitor
        try:
            flow_stats = storage.network_monitor._get_sdn_flow_statistics()
            
            if not flow_stats:
                return jsonify({
                    'error': 'No flow data available',
                    'message': 'Unable to collect flow statistics from SDN controller',
                    'timestamp': time.time()
                }), 503
            
            # Calculate flow efficiency metrics
            total_flows = flow_stats.get('total_flows', 0)
            active_flows = flow_stats.get('active_flows', 0)
            
            # Flow efficiency (percentage of flows that are actively forwarding traffic)
            flow_efficiency = (active_flows / total_flows * 100) if total_flows > 0 else 0
            
            # Calculate utilization statistics
            flow_utilization = {
                'efficiency_percentage': round(flow_efficiency, 2),
                'total_flows': total_flows,
                'active_flows': active_flows,
                'idle_flows': total_flows - active_flows,
                'flows_per_switch': flow_stats.get('flows_per_switch', {}),
                'priority_distribution': flow_stats.get('priority_distribution', {}),
                'table_distribution': flow_stats.get('table_distribution', {})
            }
            
            # Add efficiency ratings
            efficiency_rating = (
                'excellent' if flow_efficiency >= 80 else
                'good' if flow_efficiency >= 60 else
                'fair' if flow_efficiency >= 40 else
                'poor'
            )
            
            flow_utilization['efficiency_rating'] = efficiency_rating
            
            # Combine with original flow statistics
            result = {
                'flow_statistics': flow_stats,
                'utilization_metrics': flow_utilization,
                'collection_timestamp': time.time(),
                'source': 'sdn_controller'
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error collecting flow statistics: {e}")
            return jsonify({
                'error': 'Flow statistics collection failed',
                'message': str(e),
                'timestamp': time.time()
            }), 500
    
    except Exception as e:
        logger.error(f"Error in flow statistics endpoint: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve flow statistics'
        }), 500

# Create standalone Flask app for running server directly
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize FL routes with storage and auth decorator
init_fl_routes(storage, requires_auth)

# Initialize network routes with storage and auth decorator
init_network_routes(storage, requires_auth)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(fl_bp, url_prefix='/api')  # FL routes at /api/metrics/fl/*
app.register_blueprint(network_bp, url_prefix='/api/network')  # Network routes at /api/network/*

# Enable CORS if configured when running as standalone
if ENABLE_CORS:
    logger.info(f"Enabling CORS with allowed origins: {API_ALLOWED_ORIGINS}")
    CORS(app, resources={r"/*": {"origins": API_ALLOWED_ORIGINS.split(",")}})

# Add WebSocket support for real-time metrics updates
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(app, cors_allowed_origins=API_ALLOWED_ORIGINS.split(","))
    
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"Client connected to WebSocket: {request.sid}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"Client disconnected from WebSocket: {request.sid}")
    
    @socketio.on('subscribe')
    def handle_subscribe(data):
        """
        Handle subscription to real-time metrics.
        Expected data format: {'type': 'fl_server', 'interval': 5000}
        """
        logger.info(f"Client {request.sid} subscribing to: {data}")
        client_id = request.sid
        metric_type = data.get('type', 'all')
        interval = min(max(int(data.get('interval', 5000)), 1000), 30000)  # Between 1-30 seconds
        
        # Store subscription info
        if not hasattr(socketio, 'subscriptions'):
            socketio.subscriptions = {}
        socketio.subscriptions[client_id] = {'type': metric_type, 'interval': interval}
        
        # Start emitting metrics at requested interval
        def emit_metrics():
            while client_id in socketio.subscriptions:
                try:
                    # Get latest metrics of the requested type
                    latest = storage.load_metrics(
                        limit=1,
                        type_filter=metric_type if metric_type != 'all' else None,
                        sort_desc=True
                    )
                    
                    # Emit to the client
                    if latest:
                        socketio.emit('metrics_update', 
                                    {'timestamp': datetime.now().isoformat(), 
                                     'type': metric_type, 
                                     'data': latest[0]}, 
                                    room=client_id)
                except Exception as e:
                    logger.error(f"Error emitting metrics: {e}")
                    
                # Sleep for the requested interval
                socketio.sleep(interval / 1000.0)  # Convert to seconds
        
        # Start the background task
        socketio.start_background_task(emit_metrics)
        
        return {'status': 'subscribed', 'type': metric_type, 'interval': interval}
    
    logger.info("WebSocket support enabled for real-time metrics updates")
    has_websocket = True
except ImportError:
    logger.warning("flask-socketio not installed, WebSocket support disabled")
    has_websocket = False
    socketio = None

# Add '/metrics/stream' endpoint to the API Blueprint too
@api_bp.route('/metrics/stream')
def metrics_stream_info():
    """Information about WebSocket streaming endpoint"""
    if has_websocket:
        return jsonify({
            'status': 'available',
            'websocket_endpoint': '/socket.io/',
            'usage': 'Connect via Socket.IO and emit "subscribe" event with {"type": "fl_server", "interval": 5000}',
            'events': {
                'connect': 'Connection established',
                'subscribe': 'Subscribe to metrics updates',
                'metrics_update': 'Received when new metrics are available'
            }
        })
    else:
        return jsonify({
            'status': 'unavailable',
            'message': 'WebSocket support is not enabled. Install flask-socketio to enable this feature.'
        }), 503

# Stand-alone server
def run_server():
    """Run the API server directly."""
    port = API_PORT
    host = os.getenv("API_HOST", "0.0.0.0")
    
    print(f"Starting Metrics Collector API server on {host}:{port}...")
    
    if socketio:
        # Run with SocketIO if available
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        # Standard Flask run
        app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    run_server()