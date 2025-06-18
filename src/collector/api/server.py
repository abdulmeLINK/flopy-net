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

@api_bp.route('/metrics/fl', methods=['GET'])
@requires_auth
def get_fl_metrics():
    """
    Get FL metrics with enhanced round-by-round access and performance optimizations.
    
    Query parameters:
        limit: Limit the number of metrics to return (default: 100, max: 1000)
        include_raw: Include raw metrics in response (default: false)
        include_rounds: Include detailed round history (default: true) 
        consolidate_rounds: Consolidate rounds_history to one entry per round (default: true)
        rounds_only: Return only individual round data (default: false)
        min_round: Minimum round number to include (default: 0)
        max_round: Maximum round number to include (default: no limit)
        start_time: Start time for filtering (ISO format)
        end_time: End time for filtering (ISO format)
        use_cache: Use cached data if available (default: true)
        optimize: Enable performance optimizations for large datasets (default: true)
    """
    import time
    import hashlib
    
    start_time_exec = time.time()
    
    try:
        # Parse query parameters
        limit_param = request.args.get('limit', '100')
        try:
            limit = min(int(limit_param) if limit_param and limit_param.strip() else 100, 1000)
        except ValueError:
            limit = 100
        
        include_raw = request.args.get('include_raw', 'false').lower() == 'true'
        include_rounds = request.args.get('include_rounds', 'true').lower() == 'true'
        consolidate_rounds = request.args.get('consolidate_rounds', 'true').lower() == 'true'
        rounds_only = request.args.get('rounds_only', 'false').lower() == 'true'
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        optimize = request.args.get('optimize', 'true').lower() == 'true'
        
        # Round filtering parameters
        min_round = int(request.args.get('min_round', 0))
        max_round_param = request.args.get('max_round')
        max_round = int(max_round_param) if max_round_param else None
        
        # Get time range parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # **CACHING STRATEGY**
        cache_key = None
        if use_cache:
            # Create cache key from request parameters
            params_str = f"l{limit}_ir{include_raw}_inc{include_rounds}_cr{consolidate_rounds}_ro{rounds_only}_min{min_round}_max{max_round}_st{start_time}_et{end_time}"
            cache_key = hashlib.md5(params_str.encode()).hexdigest()
            
            # Try to get cached data
            cached_data = _get_cached_fl_metrics(cache_key)
            if cached_data:
                logger.debug(f"Returning cached FL metrics (key: {cache_key[:8]}...)")
                cached_data['cached'] = True
                cached_data['cache_key'] = cache_key[:8]
                return jsonify(cached_data)
        
        # **OPTIMIZATION STRATEGY**
        optimization_params = {}
        if optimize:
            optimization_params = _optimize_fl_metrics_query(limit, include_rounds, rounds_only)
            logger.info(f"Using optimization strategy for limit={limit}: {optimization_params}")
        
        # **ENHANCED METRICS COLLECTION**
        all_metrics = []
        
        # Adjust collection strategy based on optimization
        collection_limit = limit
        if optimization_params.get("use_sampling"):
            # For sampling, collect more data to sample from
            collection_limit = min(limit * 2, 2000)
        
        if not rounds_only:
            # Get main FL server metrics with optimized parameters
            fl_server_metrics = storage.load_metrics(
                type_filter='fl_server', 
                limit=min(collection_limit, 500),  # Cap FL server metrics
                sort_desc=True,
                start_time=start_time,
                end_time=end_time
            )
            
            # Also get training progress metrics (used by Docker collector)
            fl_training_progress_metrics = storage.load_metrics(
                type_filter='fl_training_progress',
                limit=min(collection_limit, 500),
                sort_desc=True,
                start_time=start_time,
                end_time=end_time
            )
            
            # **NEW: Look for individual round metrics (primary Docker collector format)**
            individual_round_metrics = []
            try:
                # Get a sample of all metrics to find round patterns
                all_recent_metrics = storage.load_metrics(
                    limit=min(100, collection_limit * 2),
                    sort_desc=True,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # Filter for fl_round_X metrics
                for metric in all_recent_metrics:
                    if metric.get('metric_type', '').startswith('fl_round_'):
                        individual_round_metrics.append(metric)
                        
                # If we have individual rounds, get more of them
                if individual_round_metrics and len(individual_round_metrics) < collection_limit:
                    # Find the pattern of round metrics
                    round_metrics = storage.load_metrics(
                        limit=min(collection_limit * 2, 1000),
                        sort_desc=True,
                        start_time=start_time,
                        end_time=end_time
                    )
                    individual_round_metrics = [
                        m for m in round_metrics 
                        if m.get('metric_type', '').startswith('fl_round_')
                    ][:collection_limit]
                    
            except Exception as e:
                logger.warning(f"Error collecting individual round metrics: {e}")
            
            # Combine all FL metrics, prioritizing individual rounds
            all_fl_metrics = individual_round_metrics + fl_training_progress_metrics + fl_server_metrics
            
            # Remove duplicates while preserving order
            seen_timestamps = set()
            unique_metrics = []
            for metric in all_fl_metrics:
                timestamp = metric.get('timestamp')
                if timestamp not in seen_timestamps:
                    seen_timestamps.add(timestamp)
                    unique_metrics.append(metric)
                    
            all_fl_metrics = unique_metrics[:collection_limit]
            total_fl_metrics = len(all_fl_metrics)
            
        else:
            # Get individual round metrics only
            try:
                all_metrics_sample = storage.load_metrics(
                    limit=min(collection_limit * 3, 1500),
                    sort_desc=True,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # Filter for round metrics
                round_metrics = [
                    m for m in all_metrics_sample 
                    if m.get('metric_type', '').startswith('fl_round_')
                ]
                
                all_fl_metrics = round_metrics[:collection_limit]
                total_fl_metrics = len(round_metrics)
                
            except Exception as e:
                logger.error(f"Error loading round metrics: {e}")
                all_fl_metrics = []
                total_fl_metrics = 0
        
        if not all_fl_metrics:
            response = {
                'metrics': [],
                'count': 0,
                'status': 'success',
                'message': 'No FL metrics found for the specified criteria',
                'execution_time_ms': round((time.time() - start_time_exec) * 1000, 2)
            }
            
            # Cache empty response
            if use_cache and cache_key:
                _cache_fl_metrics(cache_key, response)
            
            return jsonify(response)
        
        # **OPTIMIZED PROCESSING**
        all_round_metrics = []
        processed_rounds = set()
        
        # Process metrics with batch optimization if needed
        batch_size = optimization_params.get("batch_size", len(all_fl_metrics))
        
        for i in range(0, len(all_fl_metrics), batch_size):
            batch = all_fl_metrics[i:i + batch_size]
            
            for metric in batch:
                raw_metrics = metric.get('data', {})
                base_timestamp = metric.get('timestamp')
                metric_type = metric.get('metric_type', '')
                
                # Handle individual round metrics
                if metric_type.startswith('fl_round_'):
                    try:
                        round_num = int(metric_type.split('_')[-1])
                        if consolidate_rounds and round_num in processed_rounds:
                            continue
                        
                        processed_rounds.add(round_num)
                        
                        # Enhanced client data extraction with multiple fallbacks
                        clients_connected = (
                            raw_metrics.get('clients') or
                            raw_metrics.get('clients_connected') or  
                            raw_metrics.get('connected_clients') or
                            raw_metrics.get('successful_clients') or
                            raw_metrics.get('participating_clients') or
                            0
                        )
                        
                        # Enhanced model size extraction  
                        model_size_mb = raw_metrics.get('model_size_mb', 0.0)
                        if model_size_mb is None or model_size_mb == 0:
                            # Try other possible field names
                            model_size_mb = raw_metrics.get('model_size', 0.0)
                        
                        # Create formatted round metric with minimal data for optimization
                        round_metric = {
                            'timestamp': raw_metrics.get('timestamp', base_timestamp),
                            'round': round_num,
                            'status': raw_metrics.get('status', 'unknown'),
                            'clients_connected': clients_connected,
                            'clients_total': raw_metrics.get('clients', 0),
                            'accuracy': raw_metrics.get('accuracy', 0),
                            'loss': raw_metrics.get('loss', 0),
                            'training_complete': raw_metrics.get('data_state') == 'training_complete',
                            'training_duration': raw_metrics.get('training_duration', 0),
                            'data_state': raw_metrics.get('data_state', 'training'),
                            'source': 'individual_round',
                            'model_size_mb': model_size_mb
                        }
                        
                        # Only include optional fields if requested and not optimizing
                        if not optimization_params.get("use_sampling"):
                            round_metric['model_size_mb'] = model_size_mb
                        
                        # Include raw metrics if requested and not optimizing
                        if include_raw and not optimization_params.get("use_sampling"):
                            round_metric['raw_metrics'] = raw_metrics
                        
                        all_round_metrics.append(round_metric)
                        continue
                    except (ValueError, IndexError):
                        pass
                
                # Handle FL server snapshot metrics (existing logic but optimized)
                if metric_type == 'fl_server':
                    # **NEW: Enhanced extraction from FL server data**
                    current_round = raw_metrics.get('current_round', 0)
                    
                    # Extract accuracy using the same logic as FL monitor
                    accuracy = 0.0
                    loss = 0.0
                    
                    # Check last_round_metrics first
                    if 'last_round_metrics' in raw_metrics:
                        last_round = raw_metrics['last_round_metrics']
                        if isinstance(last_round, dict):
                            accuracy = last_round.get('accuracy', 0)
                            loss = last_round.get('loss', 0)
                        elif isinstance(last_round, str) and 'accuracy=' in last_round:
                            # Parse string format "@{accuracy=0.84; loss=0.055; ...}"
                            import re
                            acc_match = re.search(r'accuracy=([0-9.]+)', last_round)
                            loss_match = re.search(r'loss=([0-9.]+)', last_round)
                            if acc_match:
                                accuracy = float(acc_match.group(1))
                            if loss_match:
                                loss = float(loss_match.group(1))
                    
                    # Fallback to training_stats
                    if accuracy == 0.0 and 'training_stats' in raw_metrics:
                        training_stats = raw_metrics['training_stats']
                        if isinstance(training_stats, dict):
                            accuracy = training_stats.get('latest_accuracy', training_stats.get('best_accuracy', 0))
                        elif isinstance(training_stats, str) and 'accuracy=' in training_stats:
                            import re
                            acc_match = re.search(r'latest_accuracy=([0-9.]+)', training_stats)
                            if not acc_match:
                                acc_match = re.search(r'best_accuracy=([0-9.]+)', training_stats)
                            if acc_match:
                                accuracy = float(acc_match.group(1))
                    
                    # Create formatted FL server metric with extracted values
                    fl_server_metric = {
                        'timestamp': base_timestamp,
                        'round': current_round,
                        'status': raw_metrics.get('status', 'unknown'),
                        'clients_connected': raw_metrics.get('connected_clients', 0),
                        'clients_total': raw_metrics.get('connected_clients', 0),
                        'accuracy': accuracy,  # Use extracted accuracy
                        'loss': loss,         # Use extracted loss
                        'training_complete': raw_metrics.get('training_complete', False),
                        'data_state': raw_metrics.get('data_state', 'training'),
                        'source': 'fl_server_snapshot',
                        'model_size_mb': raw_metrics.get('model_size_mb', 0)
                    }
                    
                    # Add optional fields if not optimizing
                    if not optimization_params.get("use_sampling"):
                        fl_server_metric['model_size_mb'] = raw_metrics.get('model_size_mb', 0)
                        fl_server_metric['training_duration'] = raw_metrics.get('total_training_duration', 0)
                    
                    # Include raw metrics if requested and not optimizing
                    if include_raw and not optimization_params.get("use_sampling"):
                        fl_server_metric['raw_metrics'] = raw_metrics
                    
                    all_round_metrics.append(fl_server_metric)
                    
                    # Extract rounds history
                    rounds_history = None
                    if 'rounds_history' in raw_metrics and isinstance(raw_metrics['rounds_history'], list):
                        rounds_history = raw_metrics['rounds_history']
                    elif 'round_history' in raw_metrics and isinstance(raw_metrics['round_history'], list):
                        rounds_history = raw_metrics['round_history']
                    elif 'rounds' in raw_metrics and isinstance(raw_metrics['rounds'], list):
                        rounds_history = raw_metrics['rounds']
                    
                    if rounds_history and include_rounds:
                        # Apply sampling to round history for large datasets
                        if optimization_params.get("use_sampling") and len(rounds_history) > 100:
                            step = max(1, len(rounds_history) // 50)  # Sample every nth round
                            rounds_history = rounds_history[::step]
                            logger.debug(f"Sampled round history: {len(rounds_history)} rounds")
                        
                        for i, round_entry in enumerate(rounds_history):
                            round_num = round_entry.get('round', i + 1)
                            
                            # Apply round filtering
                            if round_num < min_round or (max_round is not None and round_num > max_round):
                                continue
                            
                            # Skip if we've already processed this round
                            if consolidate_rounds and round_num in processed_rounds:
                                continue
                            
                            processed_rounds.add(round_num)
                            
                            round_timestamp = round_entry.get('timestamp', base_timestamp)
                            
                            # Create metric entry with optimization considerations
                            round_metric = {
                                'timestamp': round_timestamp,
                                'round': round_num,
                                'status': round_entry.get('status', 'unknown'),
                                'clients_connected': raw_metrics.get('connected_clients', 0),
                                'clients_total': raw_metrics.get('connected_clients', 0),
                                'accuracy': round_entry.get('accuracy', 0),
                                'loss': round_entry.get('loss', 0),
                                'training_complete': raw_metrics.get('training_complete', False),
                                'training_duration': round_entry.get('training_duration', 0),
                                'data_state': 'training' if not raw_metrics.get('training_complete', False) else 'training_complete',
                                'source': 'fl_server_history',
                                'model_size_mb': raw_metrics.get('model_size_mb', 0)
                            }
                            
                            # Only include optional fields if not optimizing
                            if not optimization_params.get("use_sampling"):
                                round_metric['model_size_mb'] = raw_metrics.get('model_size_mb', 0)
                            
                            # Include raw metrics only if explicitly requested and not optimizing
                            if include_raw and not optimization_params.get("use_sampling"):
                                round_metric['raw_metrics'] = {
                                    'round_data': round_entry,
                                    'server_data': raw_metrics
                                }
                            
                            all_round_metrics.append(round_metric)
                    else:
                        # Create a single metric entry using current round data
                        last_round_metrics = raw_metrics.get('last_round_metrics', {})
                        current_round = raw_metrics.get('current_round', 0)
                        
                        # Apply round filtering
                        if current_round < min_round or (max_round is not None and current_round > max_round):
                            continue
                        
                        # Skip if we've already processed this round
                        if consolidate_rounds and current_round in processed_rounds:
                            continue
                        
                        processed_rounds.add(current_round)
                        
                        formatted_metric = {
                            'timestamp': base_timestamp,
                            'round': current_round,
                            'status': raw_metrics.get('status', 'unknown'),
                            'clients_connected': raw_metrics.get('connected_clients', 0),
                            'clients_total': raw_metrics.get('connected_clients', 0),
                            'accuracy': last_round_metrics.get('accuracy', 0),
                            'loss': last_round_metrics.get('loss', 0),
                            'training_complete': raw_metrics.get('training_complete', False),
                            'training_duration': raw_metrics.get('total_training_duration', 0),
                            'data_state': 'training_complete' if raw_metrics.get('training_complete', False) else ('training' if current_round > 0 else 'initializing'),
                            'source': 'fl_server_snapshot',
                            'model_size_mb': raw_metrics.get('model_size_mb', 0)
                        }
                        
                        # Only include optional fields if not optimizing
                        if not optimization_params.get("use_sampling"):
                            formatted_metric['model_size_mb'] = raw_metrics.get('model_size_mb', 0)
                        
                        # Include raw metrics only if explicitly requested and not optimizing
                        if include_raw and not optimization_params.get("use_sampling"):
                            formatted_metric['raw_metrics'] = raw_metrics
                        
                        all_round_metrics.append(formatted_metric)
        
        # **SORT AND LIMIT RESULTS**
        if consolidate_rounds:
            all_round_metrics.sort(key=lambda x: x.get('round', 0))
        else:
            all_round_metrics.sort(key=lambda x: (x.get('round', 0), x.get('timestamp', '')))
        
        # Apply final limit
        formatted_metrics = all_round_metrics[-limit:] if limit < len(all_round_metrics) else all_round_metrics
        
        # **ENHANCED RESPONSE WITH STATS AND PERFORMANCE INFO**
        execution_time = time.time() - start_time_exec
        
        response = {
            'metrics': formatted_metrics,
            'count': len(formatted_metrics),
            'total_rounds_found': len(processed_rounds),
            'status': 'success',
            'execution_time_ms': round(execution_time * 1000, 2),
            'optimizations_applied': optimization_params if optimize else {},
            'performance_info': {
                'cached': False,
                'processing_time_ms': round(execution_time * 1000, 2),
                'total_metrics_processed': len(all_fl_metrics),
                'optimization_enabled': optimize
            }
        }
        
        # Add training summary if we have data
        if formatted_metrics:
            completed_rounds = [m for m in formatted_metrics if m.get('accuracy', 0) > 0]
            if completed_rounds:
                accuracies = [m['accuracy'] for m in completed_rounds]
                response['training_summary'] = {
                    'total_rounds': len(formatted_metrics),
                    'completed_rounds': len(completed_rounds),
                    'best_accuracy': max(accuracies),
                    'latest_accuracy': completed_rounds[-1]['accuracy'],
                    'accuracy_improvement': accuracies[-1] - accuracies[0] if len(accuracies) > 1 else 0,
                    'round_range': {
                        'min': min([m['round'] for m in formatted_metrics]),
                        'max': max([m['round'] for m in formatted_metrics])
                    }
                }
        
        # Cache the response
        if use_cache and cache_key:
            _cache_fl_metrics(cache_key, response)
            logger.debug(f"Cached FL metrics response (key: {cache_key[:8]}...)")
        
        logger.info(f"FL metrics request completed in {execution_time:.3f}s: {len(formatted_metrics)} metrics, {len(processed_rounds)} rounds")
        
        return jsonify(response)
        
    except Exception as e:
        execution_time = time.time() - start_time_exec
        logger.error(f"Error in FL metrics endpoint after {execution_time:.3f}s: {str(e)}")
        return jsonify({
            'error': str(e), 
            'status': 'error',
            'execution_time_ms': round(execution_time * 1000, 2)
        }), 500

# **ENHANCED FL ROUNDS ENDPOINT - Consolidated from multiple endpoints**
@api_bp.route('/metrics/fl/rounds', methods=['GET'])
@requires_auth
def get_fl_rounds_history():
    """
    Comprehensive FL rounds endpoint - consolidated from multiple endpoints.
    
    Replaces:
    - /metrics/fl/rounds (original)
    - /metrics/fl/summary
    - /metrics/fl/chart-data
    - /metrics/fl/rounds/updates (via polling parameter)
    
    Query Parameters:
        start_round: Starting round number (default: 1)
        end_round: Ending round number (default: latest)
        limit: Maximum number of rounds to return (default: 1000, max: 10000)
        offset: Number of rounds to skip for pagination (default: 0)
        min_accuracy: Minimum accuracy filter (default: no filter)
        max_accuracy: Maximum accuracy filter (default: no filter)
        source: Data source preference ('collector', 'fl_server', 'both') (default: 'both')
        format: Response format ('detailed', 'summary', 'chart') (default: 'detailed')
        sort_order: Sort order ('asc', 'desc') (default: 'asc')
        since_round: Get rounds since this round number (for incremental updates)
        since_timestamp: Get rounds since this timestamp (ISO format)
        include_stats: Include training statistics summary (default: false)
        include_charts: Include chart-optimized data format (default: false)
        polling_mode: Return incremental updates for real-time polling (default: false)
    """
    try:
        start_time = time.time()
        
        # Parse query parameters with better defaults
        start_round = int(request.args.get('start_round', 1))
        end_round = request.args.get('end_round')
        end_round = int(end_round) if end_round else None
        limit = min(int(request.args.get('limit', 1000)), 10000)
        offset = int(request.args.get('offset', 0))
        min_accuracy = request.args.get('min_accuracy', type=float)
        max_accuracy = request.args.get('max_accuracy', type=float)
        source = request.args.get('source', 'both').lower()
        format_type = request.args.get('format', 'detailed').lower()
        sort_order = request.args.get('sort_order', 'asc').lower()
        since_round = request.args.get('since_round', type=int)
        since_timestamp = request.args.get('since_timestamp')
        include_stats = request.args.get('include_stats', 'false').lower() == 'true'
        include_charts = request.args.get('include_charts', 'false').lower() == 'true'
        polling_mode = request.args.get('polling_mode', 'false').lower() == 'true'

        logger.info(f"FL rounds request: start={start_round}, end={end_round}, limit={limit}, source={source}, format={format_type}")

        rounds_data = []
        total_rounds = 0
        latest_round = 0
        collector_rounds = []
        fl_server_rounds = []

        # Handle polling mode (replaces /rounds/updates endpoint)
        if polling_mode and (since_round or since_timestamp):
            return handle_fl_polling_request(since_round, since_timestamp, limit)

        # Strategy 1: Try FL server direct access first (most up-to-date)
        if source in ['fl_server', 'both']:
            try:
                import requests
                # Use the same FL server approach as the collector FL monitor
                fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")
                fl_server_port = os.getenv("FL_SERVER_PORT", "8081")
                fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
                
                # Build FL server request parameters
                fl_params = {
                    'start_round': start_round,
                    'limit': limit,
                    'offset': offset
                }
                if end_round:
                    fl_params['end_round'] = end_round
                if min_accuracy is not None:
                    fl_params['min_accuracy'] = min_accuracy
                if max_accuracy is not None:
                    fl_params['max_accuracy'] = max_accuracy

                fl_response = requests.get(f"{fl_server_url}/rounds", params=fl_params, timeout=10)
                
                if fl_response.status_code == 200:
                    fl_data = fl_response.json()
                    fl_server_rounds = fl_data.get('rounds', [])
                    total_rounds = max(total_rounds, fl_data.get('total_rounds', 0))
                    latest_round = max(latest_round, fl_data.get('latest_round', 0))
                    
                    logger.info(f"Retrieved {len(fl_server_rounds)} rounds from FL server")
                else:
                    logger.warning(f"FL server rounds endpoint returned {fl_response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Failed to get rounds from FL server: {e}")

        # Strategy 2: Get rounds from collector storage with enhanced extraction
        if source in ['collector', 'both'] or not fl_server_rounds:
            collector_rounds = extract_collector_rounds(limit, start_round, end_round, min_accuracy, max_accuracy, format_type)
            if collector_rounds:
                latest_round = max(latest_round, max(r['round'] for r in collector_rounds))

        # Merge and deduplicate data (prefer FL server data over collector data)
        rounds_map = {}
        
        # Add collector rounds first
        for round_data in collector_rounds:
            round_num = round_data['round']
            rounds_map[round_num] = round_data
        
        # Add FL server rounds (overwriting collector data for same rounds)
        for round_data in fl_server_rounds:
            round_num = round_data.get('round', 0)
            if round_num > 0:
                # Mark FL server as preferred source
                round_data['data_source'] = 'fl_server'
                rounds_map[round_num] = round_data

        # Convert to list and sort
        rounds_data = list(rounds_map.values())
        
        # Apply sorting
        if sort_order == 'desc':
            rounds_data.sort(key=lambda x: x['round'], reverse=True)
        else:
            rounds_data.sort(key=lambda x: x['round'])
        
        # Apply limit after merging and sorting
        total_available = len(rounds_data)
        rounds_data = rounds_data[:limit]

        # Get accurate total count
        if not total_rounds:
            total_rounds = total_available

        # Enhanced response formatting based on format type
        response_data = build_fl_response(
            rounds_data, total_rounds, latest_round, limit, offset,
            format_type, include_stats, include_charts,
            start_round, end_round, min_accuracy, max_accuracy, source, sort_order,
            len(fl_server_rounds), len(collector_rounds), start_time
        )

        execution_time = (time.time() - start_time) * 1000
        logger.info(f"FL rounds response: {len(rounds_data)} rounds, latest: {latest_round}, time: {execution_time:.2f}ms")
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in FL rounds endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"Failed to retrieve FL rounds: {str(e)}",
            "rounds": [],
            "total_rounds": 0,
            "latest_round": 0,
            "status": "error"
        }), 500


def handle_fl_polling_request(since_round, since_timestamp, limit):
    """Handle polling mode requests for real-time updates."""
    try:
        new_rounds = []
        latest_round = 0
        events = []

        # Get new rounds from storage
        all_metrics = storage.load_metrics(
            type_filter=None,
            limit=limit * 2,
            start_time=since_timestamp
        )
        
        for metric in all_metrics:
            metric_name = metric.get('metric_type', '')
            if metric_name.startswith('fl_round_') and not metric_name.endswith('_event'):
                try:
                    round_num = int(metric_name.replace('fl_round_', '').split('_')[0])
                    
                    if not since_round or round_num > since_round:
                        data = metric.get('data', {})
                        round_data = {
                            'round': round_num,
                            'timestamp': data.get('timestamp', metric.get('timestamp')),
                            'status': data.get('status', 'complete'),
                            'accuracy': data.get('accuracy', 0),
                            'loss': data.get('loss', 0),
                            'training_duration': data.get('training_duration', 0),
                            'clients': data.get('clients', 0),
                            'data_source': data.get('data_source', 'collector'),
                            'training_complete': data.get('training_complete', False)
                        }
                        
                        new_rounds.append(round_data)
                        latest_round = max(latest_round, round_num)
                
                except (ValueError, KeyError):
                    continue

        # Sort by round number
        new_rounds.sort(key=lambda x: x['round'])
        new_rounds = new_rounds[:limit]

        # Try to get latest round from FL server for comparison
        fl_server_latest = 0
        try:
            import requests
            # Use the same FL server approach as the collector FL monitor
            fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")
            fl_server_port = os.getenv("FL_SERVER_PORT", "8081")
            fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
            fl_response = requests.get(f"{fl_server_url}/rounds/latest?limit=1", timeout=5)
            
            if fl_response.status_code == 200:
                fl_data = fl_response.json()
                fl_server_latest = fl_data.get('latest_round', 0)
                
        except Exception as e:
            logger.debug(f"Could not get latest round from FL server: {e}")

        return jsonify({
            "new_rounds": new_rounds,
            "count": len(new_rounds),
            "latest_round_collector": latest_round,
            "latest_round_fl_server": fl_server_latest,
            "since_round": since_round,
            "has_more": len(new_rounds) == limit,
            "timestamp": datetime.now().isoformat(),
            "polling_mode": True
        })

    except Exception as e:
        logger.error(f"Error in FL polling request: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"Failed to get FL rounds updates: {str(e)}",
            "new_rounds": [],
            "count": 0,
            "polling_mode": True
        }), 500


def extract_collector_rounds(limit, start_round, end_round, min_accuracy, max_accuracy, format_type):
    """Extract FL rounds from collector storage with enhanced accuracy extraction."""
    collector_rounds = []
    
    try:
        # Get FL metrics from storage using enhanced processing
        # First try to get individual FL round metrics which have more detailed data
        fl_round_metrics = storage.load_metrics(
            type_filter='fl_round_',  # Get individual round metrics
            limit=limit * 3,  # Get extra to handle filtering
            offset=0
        )
        
        logger.debug(f"Retrieved {len(fl_round_metrics)} individual FL round metrics from storage")
        
        # Also get general FL server metrics for fallback data
        fl_server_metrics = storage.load_metrics(
            type_filter='fl_server',
            limit=limit * 2,  # Get some server snapshots too
            offset=0
        )
        
        logger.debug(f"Retrieved {len(fl_server_metrics)} FL server metrics from storage")
        
        # Combine and process all FL metrics
        all_fl_metrics = fl_round_metrics + fl_server_metrics
        
        # Get the latest FL server status for fallback client data
        fallback_clients = 0
        try:
            latest_fl_status = storage.load_metrics(type_filter='fl_server', limit=1, sort_desc=True)
            if latest_fl_status:
                status_data = latest_fl_status[0].get('data', {})
                fallback_clients = status_data.get('connected_clients', status_data.get('clients_connected', 0))
        except Exception as e:
            logger.debug(f"Could not get fallback client count: {e}")
            fallback_clients = 0
        
        # Calculate realistic model size based on common FL models
        def calculate_realistic_model_size(model_type: str = 'cnn') -> float:
            """Calculate realistic model size for common FL models."""
            if model_type.lower() in ['cnn', 'simple_cnn']:
                # SimpleCNN: ~32*1*25 + 32 + 64*32*25 + 64 + 128*flat + 128 + 10*128 + 10 parameters
                # For MNIST (28x28): flat = 64 * 7 * 7 = 3136
                conv1_params = 32 * 1 * 25 + 32  # 832
                conv2_params = 64 * 32 * 25 + 64  # 51264  
                fc1_params = 128 * 3136 + 128  # 401536
                fc2_params = 10 * 128 + 10  # 1290
                total_params = conv1_params + conv2_params + fc1_params + fc2_params  # ~454,922
                size_mb = (total_params * 4) / (1024 * 1024)  # float32 = 4 bytes
                return round(size_mb, 6)
            elif model_type.lower() in ['mlp', 'simple_mlp']:
                # SimpleMLP: 784*128 + 128 + 128*64 + 64 + 64*10 + 10 parameters  
                layer1_params = 784 * 128 + 128  # 100480
                layer2_params = 128 * 64 + 64  # 8256
                layer3_params = 64 * 10 + 10  # 650
                total_params = layer1_params + layer2_params + layer3_params  # ~109,386
                size_mb = (total_params * 4) / (1024 * 1024)  # float32 = 4 bytes
                return round(size_mb, 6)
            else:
                # Default medium-sized model
                return 1.5  # 1.5 MB default
        
        # Process FL metrics to extract round data using only server-provided data
        processed_metrics = []
        
        for metric in all_fl_metrics:
            try:
                data = metric.get('data', {})
                metric_type = metric.get('type', '')
                
                # Enhanced round number extraction
                round_num = (
                    data.get('round') or
                    data.get('current_round') or
                    # Extract from type if it's an individual round metric (e.g., 'fl_round_500')
                    (int(metric_type.split('_')[-1]) if metric_type.startswith('fl_round_') and metric_type.split('_')[-1].isdigit() else 0) or
                    0
                )
                
                if round_num > 0:
                    # Enhanced client data extraction with multiple fallbacks and data sources
                    clients_connected = 0
                    
                    # Try different field names and nested structures
                    client_sources = [
                        data.get('clients'),
                        data.get('clients_connected'),  
                        data.get('connected_clients'),
                        data.get('successful_clients'),
                        data.get('participating_clients'),
                        data.get('num_clients'),
                        # Check nested structures
                        data.get('last_round_metrics', {}).get('clients'),
                        data.get('training_stats', {}).get('participating_clients'),
                        # Check rounds history for this specific round
                        next((r.get('clients') for r in data.get('rounds_history', []) if r.get('round') == round_num), None),
                        # Check raw metrics
                        data.get('raw_metrics', {}).get('clients'),
                        data.get('raw_metrics', {}).get('participating_clients')
                    ]
                    
                    for source in client_sources:
                        if source is not None and source > 0:
                            clients_connected = int(source)
                            break
                    
                    # Enhanced model size extraction with multiple fallbacks
                    model_size_mb = 0.0
                    
                    model_size_sources = [
                        data.get('model_size_mb'),
                        data.get('model_size'),
                        # Check nested structures
                        data.get('last_round_metrics', {}).get('model_size_mb'),
                        # Check rounds history for this specific round
                        next((r.get('model_size_mb') for r in data.get('rounds_history', []) if r.get('round') == round_num), None),
                        # Check raw metrics
                        data.get('raw_metrics', {}).get('model_size_mb'),
                        data.get('raw_metrics', {}).get('model_size')
                    ]
                    
                    for source in model_size_sources:
                        if source is not None and source > 0:
                            try:
                                model_size_mb = float(source)
                                break
                            except (ValueError, TypeError):
                                continue
                    
                    # Extract accuracy with enhanced fallbacks
                    accuracy = (
                        data.get('accuracy') or
                        data.get('last_round_metrics', {}).get('accuracy') or
                        # Check rounds history for this specific round
                        next((r.get('accuracy') for r in data.get('rounds_history', []) if r.get('round') == round_num), 0) or
                        0
                    )
                    
                    # Extract loss with enhanced fallbacks
                    loss = (
                        data.get('loss') or
                        data.get('last_round_metrics', {}).get('loss') or
                        # Check rounds history for this specific round
                        next((r.get('loss') for r in data.get('rounds_history', []) if r.get('round') == round_num), 0) or
                        0
                    )
                    
                    # Format metric using only server data
                    processed_metric = {
                        'round': round_num,
                        'timestamp': metric.get('timestamp', data.get('timestamp')),
                        'accuracy': accuracy,
                        'loss': loss,
                        'clients_connected': clients_connected,
                        'training_duration': data.get('training_duration', 0),
                        'model_size_mb': model_size_mb,
                        'status': data.get('status', 'complete'),
                        'source_type': metric_type  # Track where this data came from
                    }
                    
                    processed_metrics.append(processed_metric)
            
            except Exception as e:
                logger.debug(f"Error processing FL metric: {e}")
                continue
        
        logger.debug(f"Processed {len(processed_metrics)} FL metrics")
        
        # Convert processed metrics to round format with filtering
        for metric in processed_metrics:
            try:
                round_num = metric.get('round', 0)
                
                # Skip if no round number
                if round_num <= 0:
                    continue
                
                # Apply filters
                if round_num < start_round:
                    continue
                if end_round and round_num > end_round:
                    continue
                    
                accuracy = metric.get('accuracy', 0)
                
                if min_accuracy is not None and accuracy < min_accuracy:
                    continue
                if max_accuracy is not None and accuracy > max_accuracy:
                    continue
                
                # Convert FL metric to round format
                round_data = {
                    'round': round_num,
                    'timestamp': metric.get('timestamp'),
                    'status': metric.get('status', 'complete'),
                    'accuracy': accuracy,
                    'loss': metric.get('loss', 0),
                    'training_duration': metric.get('training_duration', 0),
                    'model_size_mb': metric.get('model_size_mb', 0),
                    'clients': metric.get('clients_connected', 0),
                    'clients_connected': metric.get('clients_connected', 0),
                    'data_source': 'collector_enhanced',
                    'raw_metrics': metric if format_type == 'detailed' else {}
                }
                
                # Avoid duplicates - check if we already have this round
                if not any(r['round'] == round_num for r in collector_rounds):
                    collector_rounds.append(round_data)
            
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping invalid FL metric for round conversion: {e}")
                continue
        
        logger.info(f"Retrieved {len(collector_rounds)} rounds from enhanced FL processing")
        
    except Exception as e:
        logger.error(f"Error processing FL metrics directly: {e}")

    return collector_rounds


def build_fl_response(rounds_data, total_rounds, latest_round, limit, offset,
                     format_type, include_stats, include_charts,
                     start_round, end_round, min_accuracy, max_accuracy, source, sort_order,
                     fl_server_count, collector_count, start_time):
    """Build comprehensive FL response with multiple format options."""
    
    # Base response structure
    response_data = {
        "rounds": rounds_data,
        "total_rounds": total_rounds,
        "returned_rounds": len(rounds_data),
        "latest_round": latest_round,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(rounds_data) < total_rounds
        },
        "filters": {
            "start_round": start_round,
            "end_round": end_round,
            "min_accuracy": min_accuracy,
            "max_accuracy": max_accuracy,
            "source": source,
            "format": format_type,
            "sort_order": sort_order
        },
        "sources_used": {
            "fl_server_rounds": fl_server_count,
            "collector_rounds": collector_count,
            "merged_rounds": len(rounds_data)
        }
    }
    
    # Format response based on format type
    if format_type == 'summary':
        # Remove detailed fields for summary format
        for round_data in rounds_data:
            round_data.pop('raw_metrics', None)
            round_data.pop('training_duration', None)
            round_data.pop('model_size_mb', None)
    
    elif format_type == 'chart':
        # Add chart-optimized data format
        if rounds_data:
            response_data['chart_data'] = {
                'accuracy': [r['accuracy'] for r in rounds_data],
                'loss': [r['loss'] for r in rounds_data],
                'rounds': [r['round'] for r in rounds_data],
                'timestamps': [r['timestamp'] for r in rounds_data],
                'clients': [r.get('clients', 0) for r in rounds_data]
            }
    
    # Add training statistics if requested
    if include_stats and rounds_data:
        completed_rounds = [r for r in rounds_data if r['accuracy'] > 0]
        if completed_rounds:
            accuracies = [r['accuracy'] for r in completed_rounds]
            response_data['statistics'] = {
                'total_rounds': len(rounds_data),
                'completed_rounds': len(completed_rounds),
                'best_accuracy': max(accuracies),
                'latest_accuracy': completed_rounds[-1]['accuracy'],
                'average_accuracy': sum(accuracies) / len(accuracies),
                'accuracy_improvement': accuracies[-1] - accuracies[0] if len(accuracies) > 1 else 0,
                'training_duration_total': sum(r.get('training_duration', 0) for r in rounds_data)
            }
    
    # Add chart data if requested
    if include_charts and rounds_data:
        response_data['chart_optimization'] = {
            'data_optimized_for_charts': True,
            'recommended_chart_types': ['line', 'area', 'scatter'],
            'data_points': len(rounds_data)
        }
    
    # Add performance metadata
    execution_time = (time.time() - start_time) * 1000
    response_data['metadata'] = {
        'execution_time_ms': round(execution_time, 2),
        'query_optimization': 'enhanced_fl_processing',
        'response_timestamp': datetime.now().isoformat(),
        'api_version': '2.0_consolidated'
    }
    
    return response_data

@api_bp.route('/metrics/fl/status', methods=['GET'])
@requires_auth
def get_fl_training_status():
    """
    Get current FL training status by directly connecting to the FL server
    using the same URL that the FL monitor successfully uses.
    """
    try:
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "training_active": False,
            "current_round": 0,
            "latest_accuracy": 0.0,
            "latest_loss": 0.0,
            "connected_clients": 0,
            "training_complete": False,
            "data_source": "fl_server_direct",
            "fl_server_available": False,
            "collector_monitoring": True,
            "max_rounds": None,
            "stopped_by_policy": False
        }

        # Use the same FL server approach as the collector FL monitor
        # Get FL server host and port from environment (same as collector uses)
        fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")  # Use Docker service name
        fl_server_port = os.getenv("FL_SERVER_PORT", "8081")  # Metrics port
        fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
        
        logger.info(f"Using FL server URL: {fl_server_url}")

        try:
            import requests
            
            # Check FL server health first
            health_response = requests.get(f"{fl_server_url}/health", timeout=5)
            if health_response.status_code == 200:
                status_data["fl_server_available"] = True
                
                # Get FL server status including policy information
                try:
                    server_status_response = requests.get(f"{fl_server_url}/status", timeout=10)
                    if server_status_response.status_code == 200:
                        server_status = server_status_response.json()
                        # Extract stopped_by_policy status
                        status_data["stopped_by_policy"] = server_status.get("training_stopped_by_policy", False)
                        logger.debug(f"Got stopped_by_policy from FL server: {status_data['stopped_by_policy']}")
                except Exception as e:
                    logger.debug(f"Could not get FL server status: {e}")
                
                # Try to get FL server metrics for max_rounds
                try:
                    metrics_response = requests.get(f"{fl_server_url}/metrics", timeout=10)
                    if metrics_response.status_code == 200:
                        metrics_data = metrics_response.json()
                        # Extract max_rounds from FL server metrics
                        if "max_rounds" in metrics_data:
                            status_data["max_rounds"] = metrics_data["max_rounds"]
                            logger.debug(f"Got max_rounds from FL server metrics: {status_data['max_rounds']}")
                        elif "rounds" in metrics_data:
                            status_data["max_rounds"] = metrics_data["rounds"]
                            logger.debug(f"Got max_rounds from FL server rounds: {status_data['max_rounds']}")
                except Exception as e:
                    logger.debug(f"Could not get max_rounds from FL server metrics: {e}")
                
                # Get latest rounds directly from FL server
                rounds_response = requests.get(f"{fl_server_url}/rounds/latest?limit=1", timeout=10)
                
                if rounds_response.status_code == 200:
                    rounds_data = rounds_response.json()
                    rounds = rounds_data.get("rounds", [])
                    latest_round_number = rounds_data.get("latest_round", 0)
                    
                    status_data["current_round"] = latest_round_number;
                    
                    if rounds and len(rounds) > 0:
                        latest_round = rounds[0]
                        status_data.update({
                            "latest_accuracy": latest_round.get("accuracy", 0.0),
                            "latest_loss": latest_round.get("loss", 0.0),
                            "connected_clients": latest_round.get("clients", 0),
                            "training_complete": latest_round.get("training_complete", False)
                        })
                    
                    # If we have recent rounds, training is likely active
                    if latest_round_number > 0:
                        status_data["training_active"] = not status_data["training_complete"]
                    
                    logger.info(f"FL status: round {latest_round_number}, active: {status_data['training_active']}")
                
                else:
                    logger.warning(f"FL rounds endpoint returned {rounds_response.status_code}")
                    status_data["fl_server_available"] = True  # Health check passed
                    
            else:
                logger.warning(f"FL server health check failed: {health_response.status_code}")
                status_data["fl_server_available"] = False
                
        except Exception as e:
            logger.error(f"Error connecting to FL server at {fl_server_url}: {e}")
            status_data["fl_server_available"] = False
            status_data["error"] = f"Connection error: {str(e)}"

        # Try to get max_rounds from policy engine (if not already obtained from FL server)
        if status_data.get("max_rounds") is None:
            try:
                policy_engine_url = os.getenv("POLICY_ENGINE_URL", "http://localhost:5000")
                import requests
                
                context = {
                    "server_id": "default-server",
                    "operation": "training_configuration",
                    "current_round": status_data["current_round"],
                    "timestamp": datetime.now().timestamp()
                }
                
                policy_response = requests.post(
                    f"{policy_engine_url}/check",
                    json={
                        "policy_type": "fl_training_parameters",
                        "context": context
                    },
                    timeout=5
                )
                
                if policy_response.status_code == 200:
                    policy_result = policy_response.json()
                    parameters = policy_result.get("parameters", {})
                    if "total_rounds" in parameters:
                        status_data["max_rounds"] = int(parameters["total_rounds"])
                        logger.debug(f"Got max_rounds from policy engine: {status_data['max_rounds']}")
            
            except Exception as e:
                logger.debug(f"Could not get max_rounds from policy engine: {e}")

        # Final fallback: try to get max_rounds from stored FL server metrics
        if status_data.get("max_rounds") is None:
            try:
                fl_server_metrics = storage.load_metrics(
                    type_filter='fl_server',
                    limit=1,
                    sort_desc=True
                )
                if fl_server_metrics:
                    fl_data = fl_server_metrics[0].get('data', {})
                    if "max_rounds" in fl_data:
                        status_data["max_rounds"] = fl_data["max_rounds"]
                        logger.debug(f"Got max_rounds from stored FL server metrics: {status_data['max_rounds']}")
                    elif "rounds" in fl_data:
                        status_data["max_rounds"] = fl_data["rounds"]
                        logger.debug(f"Got max_rounds from stored FL server rounds: {status_data['max_rounds']}")
            except Exception as e:
                logger.debug(f"Could not get max_rounds from stored metrics: {e}")

        # Final determination of training status
        current_round = status_data["current_round"]
        max_rounds = status_data.get("max_rounds")
        training_complete = status_data["training_complete"]
        stopped_by_policy = status_data["stopped_by_policy"]
        
        if stopped_by_policy:
            status_data["training_active"] = False
        elif training_complete:
            status_data["training_active"] = False
        elif current_round > 0 and status_data["fl_server_available"]:
            if max_rounds and current_round >= max_rounds:
                status_data["training_active"] = False
                status_data["training_complete"] = True
            else:
                status_data["training_active"] = True
        else:
            status_data["training_active"] = False

        logger.info(f"FL status final: round {current_round}/{max_rounds or '?'}, "
                   f"complete: {status_data['training_complete']}, active: {status_data['training_active']}")

        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Error getting FL training status: {e}")
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "training_active": False,
            "current_round": 0,
            "latest_accuracy": 0.0,
            "latest_loss": 0.0,
            "connected_clients": 0,
            "training_complete": False,
            "data_source": "error",
            "fl_server_available": False,
            "collector_monitoring": False,
            "error": str(e)
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

@api_bp.route('/network/topology', methods=['GET'])
@requires_auth
def get_network_topology():
    """
    Get detailed network topology data from GNS3 and SDN controller.
    
    This endpoint provides comprehensive topology information including:
    - GNS3 nodes and links
    - SDN switches, ports, and flows
    - Host discovery from SDN controller
    - Link bandwidth and latency metrics
    """
    try:
        # Get query parameters
        source = request.args.get('source', 'all')  # 'all', 'gns3', 'sdn'
        include_metrics = request.args.get('include_metrics', 'true').lower() == 'true'
        format_type = request.args.get('format', 'detailed')  # 'detailed', 'summary'
        
        # Get latest network metrics containing topology data
        latest_network = storage.load_metrics(
            type_filter='network',
            limit=1,
            sort_desc=True
        )
        
        # If no stored network data, try to get live data directly from network monitor
        if not latest_network:
            logger.warning("No stored network data found, attempting to collect live topology data")
            
            # Try to access network monitor for live collection
            if hasattr(storage, 'network_monitor') and storage.network_monitor:
                try:
                    topology = storage.network_monitor.get_live_topology()
                    
                    # Create minimal network data structure
                    network_data = {
                        "status": "live_collection",
                        "project_name": "unknown",
                        "project_id": "unknown",
                        "project_status": "unknown",
                        "topology": topology,
                        "collection_timestamp": time.time()
                    }
                    
                    # Continue with normal processing below
                    
                except Exception as e:
                    logger.error(f"Failed to collect live topology data: {e}")
                    
                    # Return empty topology structure instead of 404
                    return jsonify({
                        'nodes': [],
                        'links': [],
                        'switches': [],
                        'hosts': [],
                        'statistics': {
                            'total_nodes': 0,
                            'total_links': 0,
                            'total_switches': 0,
                            'total_hosts': 0,
                            'gns3_links': 0,
                            'sdn_links': 0
                        },
                        'project_info': {
                            'name': 'no_project',
                            'id': 'unknown',
                            'status': 'disconnected'
                        },
                        'timestamp': time.time(),
                        'collection_time': time.time(),
                        'message': 'Network monitoring not available - empty topology returned'
                    })
            else:
                # Return empty topology structure instead of 404
                return jsonify({
                    'nodes': [],
                    'links': [],
                    'switches': [],
                    'hosts': [],
                    'statistics': {
                        'total_nodes': 0,
                        'total_links': 0,
                        'total_switches': 0,
                        'total_hosts': 0,
                        'gns3_links': 0,
                        'sdn_links': 0
                    },
                    'project_info': {
                        'name': 'no_project',
                        'id': 'unknown',
                        'status': 'disconnected'
                    },
                    'timestamp': time.time(),
                    'collection_time': time.time(),
                    'message': 'Network monitor not available - empty topology returned'
                })
        else:
            network_data = latest_network[0].get('data', {})
        
        topology = network_data.get('topology', {})
        
        # If no topology data in stored metrics, still try to return a valid structure
        if not topology:
            logger.warning("No topology data in stored network metrics")
            topology = {
                "nodes": [],
                "links": [],
                "switches": [],
                "hosts": [],
                "timestamp": time.time()
            }
        
        # Filter data based on source parameter
        result = {
            'timestamp': topology.get('timestamp', time.time()),
            'collection_time': network_data.get('collection_timestamp', time.time()),
            'project_info': {
                'name': network_data.get('project_name', 'unknown'),
                'id': network_data.get('project_id', 'unknown'),
                'status': network_data.get('project_status', 'unknown')
            }
        }
        
        if source in ['all', 'gns3']:
            result['nodes'] = topology.get('nodes', [])
            result['links'] = [link for link in topology.get('links', []) 
                             if link.get('source') == 'gns3' or source == 'gns3']
        
        if source in ['all', 'sdn']:
            result['switches'] = topology.get('switches', [])
            result['hosts'] = topology.get('hosts', [])
            if source == 'sdn':
                result['links'] = [link for link in topology.get('links', []) 
                                 if link.get('source') == 'sdn']
            elif source == 'all':
                if 'links' not in result:
                    result['links'] = []
                result['links'].extend([link for link in topology.get('links', []) 
                                      if link.get('source') == 'sdn'])
        
        # Add summary statistics
        result['statistics'] = {
            'total_nodes': len(result.get('nodes', [])),
            'total_links': len(result.get('links', [])),
            'total_switches': len(result.get('switches', [])),
            'total_hosts': len(result.get('hosts', [])),
            'gns3_links': len([l for l in result.get('links', []) if l.get('source') == 'gns3']),
            'sdn_links': len([l for l in result.get('links', []) if l.get('source') == 'sdn'])
        }
        
        # Include network performance metrics if requested
        if include_metrics:
            result['metrics'] = {
                'sdn_status': network_data.get('sdn_status', 'unknown'),
                'switches_count': network_data.get('switches_count', 0),
                'total_flows': network_data.get('total_flows', 0),
                'total_ports': network_data.get('total_ports', 0),
                'avg_latency_ms': network_data.get('avg_latency_ms', 0),
                'packet_loss_percent': network_data.get('packet_loss_percent', 0),
                'bandwidth_utilization_percent': network_data.get('bandwidth_utilization_percent', 0)
            }
        
        # Format output based on format_type
        if format_type == 'summary':
            # Return simplified version for overview displays
            return jsonify({
                'summary': result['statistics'],
                'status': {
                    'gns3_connected': network_data.get('status') == 'connected',
                    'sdn_connected': network_data.get('sdn_status') == 'connected',
                    'project_name': result['project_info']['name']
                },
                'timestamp': result['timestamp']
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting network topology: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve network topology data'
        }), 500

@api_bp.route('/network/topology/live', methods=['GET'])
@requires_auth
def get_live_network_topology():
    """
    Get live network topology data by directly querying network monitor.
    This bypasses storage for real-time topology updates.
    """
    try:
        # Access the network monitor if available
        if hasattr(storage, 'network_monitor') and storage.network_monitor:
            network_monitor = storage.network_monitor
            
            # Trigger fresh topology collection
            topology_data = network_monitor.get_live_topology()
            
            return jsonify({
                'topology': topology_data,
                'timestamp': time.time(),
                'source': 'live_query',
                'statistics': {
                    'total_nodes': len(topology_data.get('nodes', [])),
                    'total_links': len(topology_data.get('links', [])),
                    'total_switches': len(topology_data.get('switches', [])),
                    'total_hosts': len(topology_data.get('hosts', []))
                }
            })
        else:
            # Return empty topology structure instead of 503 error
            return jsonify({
                'topology': {
                    'nodes': [],
                    'links': [],
                    'switches': [],
                    'hosts': [],
                    'timestamp': time.time()
                },
                'timestamp': time.time(),
                'source': 'no_monitor',
                'statistics': {
                    'total_nodes': 0,
                    'total_links': 0,
                    'total_switches': 0,
                    'total_hosts': 0
                },
                'message': 'Network monitor not available - empty topology returned'
            })
            
    except Exception as e:
        logger.error(f"Error getting live network topology: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve live network topology'
        }), 500

@api_bp.route('/network/flows', methods=['GET'])
@requires_auth
def get_network_flows():
    """
    Get OpenFlow flows from all switches in the network.
    This endpoint queries the SDN controller directly for flow data.
    """
    try:
        # Get SDN controller URL from network monitor
        if hasattr(storage, 'network_monitor') and storage.network_monitor:
            sdn_controller_url = storage.network_monitor.sdn_controller_url
        else:
            sdn_controller_url = "http://localhost:8181"
        
        all_flows = []
        
        try:
            # Get all flows from Ryu SDN controller
            flows_response = requests.get(f"{sdn_controller_url}/stats/flows", timeout=10)
            
            if flows_response.status_code == 200:
                flows_data = flows_response.json()
                logger.info(f"Retrieved {len(flows_data)} flows from SDN controller")
                
                # Process flows - Ryu returns a flat dict with flow_id as key and flow data as value
                for flow_id, flow_data in flows_data.items():
                    # Extract datapath_id from flow data
                    datapath_id = flow_data.get("datapath_id")
                    
                    # Convert datapath_id to hex string for consistency
                    if datapath_id:
                        switch_dpid_str = f"{datapath_id:016x}"
                    else:
                        switch_dpid_str = "unknown"
                    
                    # Enhance flow with additional metadata
                    enhanced_flow = flow_data.copy()
                    enhanced_flow["flow_id"] = flow_id
                    enhanced_flow["switch_dpid"] = switch_dpid_str
                    enhanced_flow["switch_name"] = f"Switch-{switch_dpid_str}"
                    enhanced_flow["datapath_id_hex"] = switch_dpid_str
                    
                    all_flows.append(enhanced_flow)
                    
                logger.info(f"Total flows processed: {len(all_flows)}")
            else:
                logger.warning(f"Could not get flows from SDN controller: HTTP {flows_response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"Could not connect to SDN controller for flows: {e}")
        
        # Organize flows by type/category for better presentation
        flow_summary = {
            "total_flows": len(all_flows),
            "switches_with_flows": len(set(flow.get("switch_dpid") for flow in all_flows)),
            "priority_stats": {},
            "table_stats": {}
        }
        
        # Categorize flows by priority and table
        for flow in all_flows:
            # Priority statistics
            priority = flow.get("priority", 0)
            if priority not in flow_summary["priority_stats"]:
                flow_summary["priority_stats"][priority] = 0
            flow_summary["priority_stats"][priority] += 1
            
            # Table statistics (use table_id if available, otherwise default to 0)
            table_id = flow.get("table_id", 0)
            if table_id not in flow_summary["table_stats"]:
                flow_summary["table_stats"][table_id] = 0
            flow_summary["table_stats"][table_id] += 1
        
        return jsonify({
            "flows": all_flows,
            "summary": flow_summary,
            "timestamp": time.time(),
            "source": "sdn_controller"
        })
        
    except Exception as e:
        logger.error(f"Error getting network flows: {e}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve network flows'
        }), 500

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

@api_bp.route('/metrics/fl/config', methods=['GET'])
@requires_auth
def get_fl_configuration():
    """
    Get FL configuration and hyperparameters from FL server and policy engine.
    
    This endpoint provides comprehensive training configuration including:
    - Basic FL parameters (model, dataset, rounds)
    - Policy-derived parameters
    - Training hyperparameters
    - Server configuration
    """
    try:
        start_time = time.time()
        
        config_data = {
            "timestamp": datetime.now().isoformat(),
            "fl_server": {},
            "policy_engine": {},
            "training_parameters": {},
            "model_config": {},
            "federation_config": {},
            "data_sources": [],
            "status": "unknown"
        }
        
        # Strategy 1: Get configuration from FL server metrics
        try:
            fl_metrics = storage.load_metrics(
                type_filter='fl_server',
                limit=1,
                sort_desc=True
            )
            
            if fl_metrics:
                fl_data = fl_metrics[0].get('data', {})
                
                # Handle fallback model names properly
                model_name = fl_data.get('model', 'unknown')
                if model_name and any(term in str(model_name).upper() for term in ['FALLBACK', 'UNKNOWN', 'DEFAULT']):
                    model_name = 'Configuration Pending'

                dataset_name = fl_data.get('dataset', 'unknown')
                if dataset_name and any(term in str(dataset_name).upper() for term in ['FALLBACK', 'UNKNOWN', 'DEFAULT']):
                    dataset_name = 'Configuration Pending'

                # Extract basic configuration
                config_data["fl_server"] = {
                    "model": model_name,
                    "dataset": dataset_name,
                    "total_rounds": fl_data.get('max_rounds', fl_data.get('rounds', 0)),
                    "current_round": fl_data.get('current_round', 0),
                    "min_clients": fl_data.get('min_clients', 0),
                    "min_available_clients": fl_data.get('min_available_clients', 0),
                    "server_host": fl_data.get('host', 'unknown'),
                    "server_port": fl_data.get('port', 0),
                    "metrics_port": fl_data.get('metrics_port', 0),
                    "training_complete": fl_data.get('training_complete', False),
                    "stay_alive_after_training": fl_data.get('stay_alive_after_training', False),
                    "source": "collector_storage"
                }
                
                # Extract model configuration if available
                if 'model_config' in fl_data:
                    config_data["model_config"] = fl_data['model_config']
                
                config_data["data_sources"].append("fl_server_collector")
                
                # Set better status based on data quality
                if any(term in str(model_name).upper() for term in ['PENDING', 'UNKNOWN']) or any(term in str(dataset_name).upper() for term in ['PENDING', 'UNKNOWN']):
                    config_data["status"] = "minimal"
                else:
                    config_data["status"] = "partial"
                
                logger.info(f"Retrieved FL config from collector: {config_data['fl_server']}")
        
        except Exception as e:
            logger.warning(f"Could not get FL config from collector: {e}")
        
        # Strategy 2: Get configuration directly from FL server
        try:
            import requests
            # Use the same FL server approach as the collector FL monitor
            fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")
            fl_server_port = os.getenv("FL_SERVER_PORT", "8081")
            fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
            
            # Try to get FL server metrics directly
            response = requests.get(f"{fl_server_url}/metrics", timeout=10)
            if response.status_code == 200:
                fl_data = response.json()
                
                # Update/enhance FL server configuration
                config_data["fl_server"].update({
                    "model": fl_data.get('model', config_data["fl_server"].get('model', 'unknown')),
                    "dataset": fl_data.get('dataset', config_data["fl_server"].get('dataset', 'unknown')),
                    "total_rounds": fl_data.get('max_rounds', fl_data.get('rounds', config_data["fl_server"].get('total_rounds', 0))),
                    "current_round": fl_data.get('current_round', config_data["fl_server"].get('current_round', 0)),
                    "min_clients": fl_data.get('min_clients', config_data["fl_server"].get('min_clients', 0)),
                    "min_available_clients": fl_data.get('min_available_clients', config_data["fl_server"].get('min_available_clients', 0)),
                    "training_complete": fl_data.get('training_complete', config_data["fl_server"].get('training_complete', False)),
                    "source": "fl_server_direct"
                })
                
                config_data["data_sources"].append("fl_server_direct")
                config_data["status"] = "enhanced"
                
                logger.info(f"Enhanced FL config from direct FL server: {config_data['fl_server']}")
        
        except Exception as e:
            logger.debug(f"Could not get FL config directly from FL server: {e}")
        
        # Strategy 3: Get policy-derived parameters from policy engine
        try:
            import requests
            policy_engine_url = os.getenv("POLICY_ENGINE_URL", "http://localhost:5000")
            
            # Check fl_training_parameters policy
            context = {
                "server_id": "default-server",
                "operation": "training_configuration",
                "model": config_data["fl_server"].get('model', 'unknown'),
                "dataset": config_data["fl_server"].get('dataset', 'unknown'),
                "timestamp": datetime.now().timestamp()
            }
            
            policy_response = requests.post(
                f"{policy_engine_url}/check",
                json={
                    "policy_type": "fl_training_parameters",
                    "context": context
                },
                timeout=10
            )
            
            if policy_response.status_code == 200:
                policy_result = policy_response.json()
                parameters = policy_result.get("parameters", {})
                
                if parameters:
                    config_data["policy_engine"] = {
                        "policy_allowed": policy_result.get("allowed", False),
                        "policy_decision": policy_result.get("decision", "unknown"),
                        "total_rounds": parameters.get("total_rounds"),
                        "local_epochs": parameters.get("local_epochs"),
                        "batch_size": parameters.get("batch_size"),
                        "learning_rate": parameters.get("learning_rate"),
                        "min_clients": parameters.get("min_clients"),
                        "min_available_clients": parameters.get("min_available_clients"),
                        "max_clients": parameters.get("max_clients"),
                        "aggregation_strategy": parameters.get("aggregation_strategy"),
                        "evaluation_strategy": parameters.get("evaluation_strategy"),
                        "privacy_mechanism": parameters.get("privacy_mechanism"),
                        "differential_privacy_epsilon": parameters.get("differential_privacy_epsilon"),
                        "differential_privacy_delta": parameters.get("differential_privacy_delta"),
                        "secure_aggregation": parameters.get("secure_aggregation"),
                        "source": "policy_engine"
                    }
                    
                    # Merge policy parameters into training_parameters
                    config_data["training_parameters"] = {
                        "total_rounds": parameters.get("total_rounds", config_data["fl_server"].get('total_rounds')),
                        "local_epochs": parameters.get("local_epochs", 1),
                        "batch_size": parameters.get("batch_size", 32),
                        "learning_rate": parameters.get("learning_rate", 0.01),
                        "aggregation_strategy": parameters.get("aggregation_strategy", "fedavg"),
                        "evaluation_strategy": parameters.get("evaluation_strategy", "centralized"),
                        "privacy_mechanism": parameters.get("privacy_mechanism", "none"),
                        "differential_privacy_epsilon": parameters.get("differential_privacy_epsilon"),
                        "differential_privacy_delta": parameters.get("differential_privacy_delta"),
                        "secure_aggregation": parameters.get("secure_aggregation", False)
                    }
                    
                    config_data["data_sources"].append("policy_engine")
                    config_data["status"] = "comprehensive"
                    
                    logger.info(f"Retrieved policy parameters: {config_data['policy_engine']}")
        
        except Exception as e:
            logger.debug(f"Could not get policy parameters: {e}")
        
        # Strategy 4: Extract from CONFIG_LOADED events if available
        try:
            config_events = storage.load_events(
                source_component="FL_SERVER",
                event_type="CONFIG_LOADED",
                limit=1,
                sort_desc=True
            )
            
            if config_events:
                event_details = config_events[0].get('details', {})
                config_summary = event_details.get('config_summary', {})
                
                if config_summary:
                    config_data["federation_config"] = {
                        "model": config_summary.get('model'),
                        "dataset": config_summary.get('dataset'),
                        "rounds": config_summary.get('rounds'),
                        "min_clients": config_summary.get('min_clients'),
                        "min_available_clients": config_summary.get('min_available_clients'),
                        "stay_alive_after_training": config_summary.get('stay_alive_after_training'),
                        "source": "fl_server_events",
                        "timestamp": config_events[0].get('timestamp')
                    }
                    
                    config_data["data_sources"].append("fl_server_events")
                    
                    logger.info(f"Enhanced config from FL server events: {config_data['federation_config']}")
        
        except Exception as e:
            logger.debug(f"Could not get config from FL server events: {e}")
        
        # Set default training parameters if none found
        if not config_data["training_parameters"]:
            config_data["training_parameters"] = {
                "total_rounds": config_data["fl_server"].get('total_rounds', 0),
                "local_epochs": None,
                "batch_size": None,
                "learning_rate": None,
                "aggregation_strategy": None,
                "evaluation_strategy": None,
                "privacy_mechanism": None,
                "secure_aggregation": None
            }
        
        # Set default model config if none found - only provide what we actually know
        if not config_data["model_config"]:
            model_name = config_data["fl_server"].get('model', None)
            dataset_name = config_data["fl_server"].get('dataset', None)
            
            # Only provide minimal structure, no assumptions about specific models
            config_data["model_config"] = {
                "model_type": model_name if model_name and model_name != 'unknown' else None,
                "num_classes": None,
                "architecture": None,
                "estimated_parameters": None,
                "source": "server_provided_only"
            }
        
        # Final status determination
        if config_data["status"] == "unknown" and config_data["data_sources"]:
            config_data["status"] = "basic"
        
        # Add metadata
        execution_time = (time.time() - start_time) * 1000
        config_data["metadata"] = {
            "execution_time_ms": round(execution_time, 2),
            "data_sources_used": config_data["data_sources"],
            "config_completeness": config_data["status"],
            "timestamp": datetime.now().isoformat(),
            "api_version": "2.0"
        }
        
        logger.info(f"FL config request completed in {execution_time:.2f}ms using sources: {config_data['data_sources']}")
        
        return jsonify(config_data)
        
    except Exception as e:
        logger.error(f"Error in FL config endpoint: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "fl_server": {},
            "policy_engine": {},
            "training_parameters": {},
            "model_config": {},
            "federation_config": {}
        }), 500

# Create standalone Flask app for running server directly
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.register_blueprint(api_bp, url_prefix='/api')

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