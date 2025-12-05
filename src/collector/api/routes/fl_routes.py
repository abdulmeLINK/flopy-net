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
FL (Federated Learning) Routes for Collector API.

This module provides Flask routes for FL metrics endpoints including:
- /metrics/fl - Main FL metrics endpoint with enhanced round tracking
- /metrics/fl/rounds - Comprehensive FL rounds endpoint  
- /metrics/fl/status - Current FL training status
- /metrics/fl/config - FL configuration and hyperparameters

Extracted from server.py to reduce file size and improve maintainability.
"""

import os
import logging
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

from flask import Blueprint, jsonify, request

from src.collector.api.routes.fl_metrics_processor import (
    FLMetricsCache,
    QueryOptimizer,
    FLMetricsProcessor,
    CollectorRoundsExtractor
)

logger = logging.getLogger(__name__)

# Create Blueprint for FL routes
fl_bp = Blueprint('fl', __name__)

# Module-level variables set by init_fl_routes()
_storage = None
_requires_auth = None

# FL Metrics Cache (using extracted class)
_fl_metrics_cache = FLMetricsCache(ttl=10)

# Processor instances (initialized in init_fl_routes)
_metrics_processor: Optional[FLMetricsProcessor] = None
_rounds_extractor: Optional[CollectorRoundsExtractor] = None


def init_fl_routes(storage, requires_auth_decorator):
    """
    Initialize FL routes with storage and auth decorator.
    
    Args:
        storage: MetricsStorage instance for data access
        requires_auth_decorator: Authentication decorator function
    """
    global _storage, _requires_auth, _metrics_processor, _rounds_extractor
    _storage = storage
    _requires_auth = requires_auth_decorator
    _metrics_processor = FLMetricsProcessor(storage)
    _rounds_extractor = CollectorRoundsExtractor(storage)
    logger.info("FL routes initialized with storage and auth")


def _apply_auth(f):
    """Apply authentication decorator if available."""
    if _requires_auth:
        return _requires_auth(f)
    return f


@fl_bp.route('/metrics/fl', methods=['GET'])
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
            cache_key = _fl_metrics_cache.generate_key(
                limit, include_raw, include_rounds, consolidate_rounds,
                rounds_only, min_round, max_round, start_time, end_time
            )
            
            cached_data = _fl_metrics_cache.get(cache_key)
            if cached_data:
                logger.debug(f"Returning cached FL metrics (key: {cache_key[:8]}...)")
                cached_data['cached'] = True
                cached_data['cache_key'] = cache_key[:8]
                return jsonify(cached_data)
        
        # **OPTIMIZATION STRATEGY**
        optimization_params = {}
        if optimize:
            optimization_params = QueryOptimizer.optimize(limit, include_rounds, rounds_only)
            logger.info(f"Using optimization strategy for limit={limit}: {optimization_params}")
        
        # **ENHANCED METRICS COLLECTION**
        collection_limit = limit
        if optimization_params.get("use_sampling"):
            collection_limit = min(limit * 2, 2000)
        
        # Use processor to collect metrics
        all_fl_metrics = _metrics_processor.collect_metrics(
            rounds_only, collection_limit, start_time, end_time
        )
        
        if not all_fl_metrics:
            response = {
                'metrics': [],
                'count': 0,
                'status': 'success',
                'message': 'No FL metrics found for the specified criteria',
                'execution_time_ms': round((time.time() - start_time_exec) * 1000, 2)
            }
            
            if use_cache and cache_key:
                _fl_metrics_cache.set(cache_key, response)
            
            return jsonify(response)
        
        # **OPTIMIZED PROCESSING**
        all_round_metrics, processed_rounds = _metrics_processor.process_metrics(
            all_fl_metrics, optimization_params, include_raw, include_rounds,
            consolidate_rounds, min_round, max_round
        )
        
        # Sort and limit results
        if consolidate_rounds:
            all_round_metrics.sort(key=lambda x: x.get('round', 0))
        else:
            all_round_metrics.sort(key=lambda x: (x.get('round', 0), x.get('timestamp', '')))
        
        formatted_metrics = all_round_metrics[-limit:] if limit < len(all_round_metrics) else all_round_metrics
        
        # Build response
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
        
        # Add training summary
        training_summary = _metrics_processor.build_training_summary(formatted_metrics)
        if training_summary:
            response['training_summary'] = training_summary
        
        # Cache the response
        if use_cache and cache_key:
            _fl_metrics_cache.set(cache_key, response)
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


def handle_fl_polling_request(since_round: Optional[int], since_timestamp: Optional[str], limit: int) -> Any:
    """Handle FL polling mode request for incremental updates."""
    try:
        # Get recent FL metrics
        all_metrics = _storage.load_metrics(
            type_filter='fl_server',
            limit=limit,
            sort_desc=True
        )
        
        # Filter based on since_round or since_timestamp
        filtered_rounds = []
        
        for metric in all_metrics:
            data = metric.get('data', {})
            round_num = data.get('current_round', 0)
            timestamp = metric.get('timestamp')
            
            if since_round and round_num <= since_round:
                continue
            if since_timestamp and timestamp and timestamp <= since_timestamp:
                continue
                
            filtered_rounds.append({
                'round': round_num,
                'timestamp': timestamp,
                'accuracy': data.get('last_round_metrics', {}).get('accuracy', 0) if isinstance(data.get('last_round_metrics'), dict) else 0,
                'loss': data.get('last_round_metrics', {}).get('loss', 0) if isinstance(data.get('last_round_metrics'), dict) else 0,
                'clients': data.get('connected_clients', 0),
                'status': data.get('status', 'unknown')
            })
        
        return jsonify({
            'rounds': filtered_rounds,
            'count': len(filtered_rounds),
            'polling_mode': True,
            'since_round': since_round,
            'since_timestamp': since_timestamp
        })
        
    except Exception as e:
        logger.error(f"Error in FL polling request: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


def extract_collector_rounds(limit: int, start_round: int, end_round: Optional[int], 
                            min_accuracy: Optional[float], max_accuracy: Optional[float],
                            format_type: str) -> List[Dict[str, Any]]:
    """
    Extract FL rounds from collector storage with enhanced processing.
    
    Delegates to CollectorRoundsExtractor.
    
    Args:
        limit: Maximum number of rounds to return
        start_round: Starting round number
        end_round: Ending round number (optional)
        min_accuracy: Minimum accuracy filter
        max_accuracy: Maximum accuracy filter
        format_type: Response format type
        
    Returns:
        List of formatted round data dictionaries
    """
    if _rounds_extractor:
        return _rounds_extractor.extract(
            limit, start_round, end_round, min_accuracy, max_accuracy, format_type
        )
    
    # Fallback if extractor not initialized
    logger.warning("CollectorRoundsExtractor not initialized, returning empty list")
    return []


@fl_bp.route('/metrics/fl/rounds', methods=['GET'])
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
        min_accuracy: Minimum accuracy filter
        max_accuracy: Maximum accuracy filter
        source: Data source preference ('collector', 'fl_server', 'both')
        format: Response format ('detailed', 'summary', 'chart')
        sort_order: Sort order ('asc', 'desc')
        since_round: Get rounds since this round number
        since_timestamp: Get rounds since this timestamp (ISO format)
        include_stats: Include training statistics summary
        include_charts: Include chart-optimized data format
        polling_mode: Return incremental updates for real-time polling
    """
    try:
        start_time = time.time()
        
        # Parse query parameters
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

        # Handle polling mode
        if polling_mode and (since_round or since_timestamp):
            return handle_fl_polling_request(since_round, since_timestamp, limit)

        # Strategy 1: Try FL server direct access first
        if source in ['fl_server', 'both']:
            try:
                fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")
                fl_server_port = os.getenv("FL_SERVER_PORT", "8081")
                fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
                
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

        # Strategy 2: Get rounds from collector storage
        if source in ['collector', 'both'] or not fl_server_rounds:
            collector_rounds = extract_collector_rounds(limit, start_round, end_round, min_accuracy, max_accuracy, format_type)
            if collector_rounds:
                latest_round = max(latest_round, max(r['round'] for r in collector_rounds))

        # Merge and deduplicate data
        rounds_map = {}
        
        # Add collector rounds first
        for round_data in collector_rounds:
            round_num = round_data.get('round')
            if round_num:
                rounds_map[round_num] = round_data
        
        # FL server data takes precedence
        for round_data in fl_server_rounds:
            round_num = round_data.get('round')
            if round_num:
                rounds_map[round_num] = round_data
        
        # Convert to list and sort
        rounds_data = list(rounds_map.values())
        rounds_data.sort(key=lambda x: x.get('round', 0), reverse=(sort_order == 'desc'))
        
        # Apply pagination
        if offset > 0:
            rounds_data = rounds_data[offset:]
        if limit:
            rounds_data = rounds_data[:limit]
        
        # Build response
        execution_time = time.time() - start_time
        
        response = {
            'rounds': rounds_data,
            'count': len(rounds_data),
            'total_rounds': max(total_rounds, len(rounds_map)),
            'latest_round': latest_round,
            'execution_time_ms': round(execution_time * 1000, 2),
            'format': format_type,
            'source': source,
            'status': 'success'
        }
        
        # Add statistics if requested
        if include_stats and rounds_data:
            accuracies = [r.get('accuracy', 0) for r in rounds_data if r.get('accuracy', 0) > 0]
            losses = [r.get('loss', 0) for r in rounds_data if r.get('loss', 0) > 0]
            
            response['statistics'] = {
                'total_rounds': len(rounds_data),
                'rounds_with_accuracy': len(accuracies),
                'best_accuracy': max(accuracies) if accuracies else 0,
                'avg_accuracy': sum(accuracies) / len(accuracies) if accuracies else 0,
                'min_loss': min(losses) if losses else 0,
                'avg_loss': sum(losses) / len(losses) if losses else 0
            }
        
        # Add chart data if requested
        if include_charts and rounds_data:
            response['chart_data'] = {
                'rounds': [r.get('round') for r in rounds_data],
                'accuracy': [r.get('accuracy', 0) for r in rounds_data],
                'loss': [r.get('loss', 0) for r in rounds_data],
                'clients': [r.get('clients', r.get('clients_connected', 0)) for r in rounds_data]
            }
        
        logger.info(f"FL rounds request completed in {execution_time:.3f}s: {len(rounds_data)} rounds")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in FL rounds endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'rounds': []
        }), 500


@fl_bp.route('/metrics/fl/status', methods=['GET'])
def get_fl_training_status():
    """
    Get current FL training status by directly connecting to the FL server.
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

        fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")
        fl_server_port = os.getenv("FL_SERVER_PORT", "8081")
        fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
        
        logger.info(f"Using FL server URL: {fl_server_url}")

        try:
            # Check FL server health
            health_response = requests.get(f"{fl_server_url}/health", timeout=5)
            if health_response.status_code == 200:
                status_data["fl_server_available"] = True
                
                # Get FL server status
                try:
                    server_status_response = requests.get(f"{fl_server_url}/status", timeout=10)
                    if server_status_response.status_code == 200:
                        server_status = server_status_response.json()
                        status_data["stopped_by_policy"] = server_status.get("training_stopped_by_policy", False)
                except Exception as e:
                    logger.debug(f"Could not get FL server status: {e}")
                
                # Get FL server metrics for max_rounds
                try:
                    metrics_response = requests.get(f"{fl_server_url}/metrics", timeout=10)
                    if metrics_response.status_code == 200:
                        metrics_data = metrics_response.json()
                        if "max_rounds" in metrics_data:
                            status_data["max_rounds"] = metrics_data["max_rounds"]
                        elif "rounds" in metrics_data:
                            status_data["max_rounds"] = metrics_data["rounds"]
                except Exception as e:
                    logger.debug(f"Could not get max_rounds from FL server metrics: {e}")
                
                # Get latest rounds
                rounds_response = requests.get(f"{fl_server_url}/rounds/latest?limit=1", timeout=10)
                
                if rounds_response.status_code == 200:
                    rounds_data = rounds_response.json()
                    rounds = rounds_data.get("rounds", [])
                    latest_round_number = rounds_data.get("latest_round", 0)
                    
                    status_data["current_round"] = latest_round_number
                    
                    if rounds and len(rounds) > 0:
                        latest_round = rounds[0]
                        status_data.update({
                            "latest_accuracy": latest_round.get("accuracy", 0.0),
                            "latest_loss": latest_round.get("loss", 0.0),
                            "connected_clients": latest_round.get("clients", 0),
                            "training_complete": latest_round.get("training_complete", False)
                        })
                    
                    if latest_round_number > 0:
                        status_data["training_active"] = not status_data["training_complete"]
                    
                    logger.info(f"FL status: round {latest_round_number}, active: {status_data['training_active']}")
                
                else:
                    logger.warning(f"FL rounds endpoint returned {rounds_response.status_code}")
                    
            else:
                logger.warning(f"FL server health check failed: {health_response.status_code}")
                status_data["fl_server_available"] = False
                
        except Exception as e:
            logger.error(f"Error connecting to FL server at {fl_server_url}: {e}")
            status_data["fl_server_available"] = False
            status_data["error"] = f"Connection error: {str(e)}"

        # Try to get max_rounds from policy engine
        if status_data.get("max_rounds") is None:
            try:
                policy_engine_url = os.getenv("POLICY_ENGINE_URL", "http://localhost:5000")
                
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
            
            except Exception as e:
                logger.debug(f"Could not get max_rounds from policy engine: {e}")

        # Fallback: get max_rounds from stored FL server metrics
        if status_data.get("max_rounds") is None:
            try:
                fl_server_metrics = _storage.load_metrics(
                    type_filter='fl_server',
                    limit=1,
                    sort_desc=True
                )
                if fl_server_metrics:
                    fl_data = fl_server_metrics[0].get('data', {})
                    if "max_rounds" in fl_data:
                        status_data["max_rounds"] = fl_data["max_rounds"]
                    elif "rounds" in fl_data:
                        status_data["max_rounds"] = fl_data["rounds"]
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


@fl_bp.route('/metrics/fl/config', methods=['GET'])
def get_fl_configuration():
    """
    Get FL configuration and hyperparameters from FL server and policy engine.
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
            fl_metrics = _storage.load_metrics(
                type_filter='fl_server',
                limit=1,
                sort_desc=True
            )
            
            if fl_metrics:
                fl_data = fl_metrics[0].get('data', {})
                
                model_name = fl_data.get('model', 'unknown')
                if model_name and any(term in str(model_name).upper() for term in ['FALLBACK', 'UNKNOWN', 'DEFAULT']):
                    model_name = 'Configuration Pending'

                dataset_name = fl_data.get('dataset', 'unknown')
                if dataset_name and any(term in str(dataset_name).upper() for term in ['FALLBACK', 'UNKNOWN', 'DEFAULT']):
                    dataset_name = 'Configuration Pending'

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
                
                if 'model_config' in fl_data:
                    config_data["model_config"] = fl_data['model_config']
                
                config_data["data_sources"].append("fl_server_collector")
                
                if any(term in str(model_name).upper() for term in ['PENDING', 'UNKNOWN']) or any(term in str(dataset_name).upper() for term in ['PENDING', 'UNKNOWN']):
                    config_data["status"] = "minimal"
                else:
                    config_data["status"] = "partial"
                
                logger.info(f"Retrieved FL config from collector: {config_data['fl_server']}")
        
        except Exception as e:
            logger.warning(f"Could not get FL config from collector: {e}")
        
        # Strategy 2: Get configuration directly from FL server
        try:
            fl_server_host = os.getenv("FL_SERVER_HOST", "fl-server")
            fl_server_port = os.getenv("FL_SERVER_PORT", "8081")
            fl_server_url = f"http://{fl_server_host}:{fl_server_port}"
            
            response = requests.get(f"{fl_server_url}/metrics", timeout=10)
            if response.status_code == 200:
                fl_data = response.json()
                
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
            policy_engine_url = os.getenv("POLICY_ENGINE_URL", "http://localhost:5000")
            
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
        
        # Strategy 4: Extract from CONFIG_LOADED events
        try:
            config_events = _storage.load_events(
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
        
        # Set defaults
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
        
        if not config_data["model_config"]:
            model_name = config_data["fl_server"].get('model', None)
            
            config_data["model_config"] = {
                "model_type": model_name if model_name and model_name != 'unknown' else None,
                "num_classes": None,
                "architecture": None,
                "estimated_parameters": None,
                "source": "server_provided_only"
            }
        
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
