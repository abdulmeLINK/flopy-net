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
FL Metrics Processor - Handles FL metrics processing and transformation.

Extracted from fl_routes.py to improve maintainability and reduce file size.
Provides classes for:
- Metrics query optimization
- Metrics processing and transformation
- Round data extraction and formatting
"""

import re
import time
import logging
import hashlib
from typing import Optional, Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)


class FLMetricsCache:
    """
    Simple cache for FL metrics with TTL-based expiration.
    """
    
    def __init__(self, ttl: int = 10):
        """
        Initialize the cache.
        
        Args:
            ttl: Cache time-to-live in seconds
        """
        self._cache: Dict[str, Any] = {}
        self._ttl = ttl
        self._last_cache_time = 0
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached FL metrics if available and not expired."""
        current_time = time.time()
        
        # Check if cache is expired
        if current_time - self._last_cache_time > self._ttl:
            self._cache.clear()
            self._last_cache_time = current_time
            return None
        
        return self._cache.get(cache_key)
    
    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Cache FL metrics data."""
        self._cache[cache_key] = data
    
    def generate_key(self, limit: int, include_raw: bool, include_rounds: bool,
                     consolidate_rounds: bool, rounds_only: bool, min_round: int,
                     max_round: Optional[int], start_time: Optional[str],
                     end_time: Optional[str]) -> str:
        """Generate a cache key from query parameters."""
        params_str = (f"l{limit}_ir{include_raw}_inc{include_rounds}_cr{consolidate_rounds}"
                     f"_ro{rounds_only}_min{min_round}_max{max_round}_st{start_time}_et{end_time}")
        return hashlib.md5(params_str.encode()).hexdigest()


class QueryOptimizer:
    """
    Optimizes FL metrics query parameters based on request size.
    """
    
    @staticmethod
    def optimize(limit: int, include_rounds: bool, rounds_only: bool) -> Dict[str, Any]:
        """
        Optimize FL metrics query parameters based on request size.
        
        Args:
            limit: Number of metrics requested
            include_rounds: Whether rounds are included
            rounds_only: Whether only rounds are requested
            
        Returns:
            Dictionary of optimization parameters
        """
        if limit > 500:
            # Large dataset - use sampling and reduced data
            return {
                "use_sampling": True,
                "sample_rate": min(0.5, 1000 / limit),
                "include_raw": False,
                "consolidate_rounds": True,
                "batch_size": 200
            }
        elif limit > 100:
            # Medium dataset - moderate optimization
            return {
                "use_sampling": False,
                "include_raw": False,
                "consolidate_rounds": True,
                "batch_size": 100
            }
        else:
            # Small dataset - minimal optimization
            return {
                "use_sampling": False,
                "include_raw": include_rounds,
                "consolidate_rounds": True,
                "batch_size": 50
            }


class FLMetricsProcessor:
    """
    Processes and transforms FL metrics data from various sources.
    """
    
    def __init__(self, storage):
        """
        Initialize the processor.
        
        Args:
            storage: MetricsStorage instance for data access
        """
        self.storage = storage
    
    def collect_metrics(self, rounds_only: bool, collection_limit: int,
                       start_time: Optional[str], end_time: Optional[str]) -> List[Dict[str, Any]]:
        """
        Collect FL metrics from storage.
        
        Args:
            rounds_only: Whether to collect only round metrics
            collection_limit: Maximum metrics to collect
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            List of FL metrics
        """
        if not rounds_only:
            return self._collect_all_fl_metrics(collection_limit, start_time, end_time)
        else:
            return self._collect_round_metrics_only(collection_limit, start_time, end_time)
    
    def _collect_all_fl_metrics(self, collection_limit: int,
                                start_time: Optional[str],
                                end_time: Optional[str]) -> List[Dict[str, Any]]:
        """Collect all types of FL metrics."""
        # Get main FL server metrics
        fl_server_metrics = self.storage.load_metrics(
            type_filter='fl_server',
            limit=min(collection_limit, 500),
            sort_desc=True,
            start_time=start_time,
            end_time=end_time
        )
        
        # Get training progress metrics
        fl_training_progress_metrics = self.storage.load_metrics(
            type_filter='fl_training_progress',
            limit=min(collection_limit, 500),
            sort_desc=True,
            start_time=start_time,
            end_time=end_time
        )
        
        # Get individual round metrics
        individual_round_metrics = self._collect_individual_round_metrics(
            collection_limit, start_time, end_time
        )
        
        # Combine all FL metrics
        all_fl_metrics = individual_round_metrics + fl_training_progress_metrics + fl_server_metrics
        
        # Remove duplicates
        return self._deduplicate_metrics(all_fl_metrics, collection_limit)
    
    def _collect_individual_round_metrics(self, collection_limit: int,
                                          start_time: Optional[str],
                                          end_time: Optional[str]) -> List[Dict[str, Any]]:
        """Collect individual round metrics."""
        individual_round_metrics = []
        try:
            all_recent_metrics = self.storage.load_metrics(
                limit=min(100, collection_limit * 2),
                sort_desc=True,
                start_time=start_time,
                end_time=end_time
            )
            
            for metric in all_recent_metrics:
                if metric.get('metric_type', '').startswith('fl_round_'):
                    individual_round_metrics.append(metric)
            
            if individual_round_metrics and len(individual_round_metrics) < collection_limit:
                round_metrics = self.storage.load_metrics(
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
        
        return individual_round_metrics
    
    def _collect_round_metrics_only(self, collection_limit: int,
                                    start_time: Optional[str],
                                    end_time: Optional[str]) -> List[Dict[str, Any]]:
        """Collect only round metrics."""
        try:
            all_metrics_sample = self.storage.load_metrics(
                limit=min(collection_limit * 3, 1500),
                sort_desc=True,
                start_time=start_time,
                end_time=end_time
            )
            
            round_metrics = [
                m for m in all_metrics_sample
                if m.get('metric_type', '').startswith('fl_round_')
            ]
            
            return round_metrics[:collection_limit]
            
        except Exception as e:
            logger.error(f"Error loading round metrics: {e}")
            return []
    
    def _deduplicate_metrics(self, metrics: List[Dict[str, Any]],
                            limit: int) -> List[Dict[str, Any]]:
        """Remove duplicate metrics by timestamp."""
        seen_timestamps: Set[str] = set()
        unique_metrics = []
        
        for metric in metrics:
            timestamp = metric.get('timestamp')
            if timestamp not in seen_timestamps:
                seen_timestamps.add(timestamp)
                unique_metrics.append(metric)
        
        return unique_metrics[:limit]
    
    def process_metrics(self, all_fl_metrics: List[Dict[str, Any]],
                       optimization_params: Dict[str, Any],
                       include_raw: bool, include_rounds: bool,
                       consolidate_rounds: bool, min_round: int,
                       max_round: Optional[int]) -> Tuple[List[Dict[str, Any]], Set[int]]:
        """
        Process FL metrics and extract round data.
        
        Args:
            all_fl_metrics: List of raw FL metrics
            optimization_params: Query optimization parameters
            include_raw: Whether to include raw metrics
            include_rounds: Whether to include round details
            consolidate_rounds: Whether to consolidate rounds
            min_round: Minimum round filter
            max_round: Maximum round filter
            
        Returns:
            Tuple of (processed round metrics, set of processed round numbers)
        """
        all_round_metrics: List[Dict[str, Any]] = []
        processed_rounds: Set[int] = set()
        
        batch_size = optimization_params.get("batch_size", len(all_fl_metrics))
        
        for i in range(0, len(all_fl_metrics), batch_size):
            batch = all_fl_metrics[i:i + batch_size]
            
            for metric in batch:
                round_metrics = self._process_single_metric(
                    metric, optimization_params, include_raw, include_rounds,
                    consolidate_rounds, min_round, max_round, processed_rounds
                )
                all_round_metrics.extend(round_metrics)
        
        return all_round_metrics, processed_rounds
    
    def _process_single_metric(self, metric: Dict[str, Any],
                               optimization_params: Dict[str, Any],
                               include_raw: bool, include_rounds: bool,
                               consolidate_rounds: bool, min_round: int,
                               max_round: Optional[int],
                               processed_rounds: Set[int]) -> List[Dict[str, Any]]:
        """Process a single metric and extract round data."""
        results = []
        raw_metrics = metric.get('data', {})
        base_timestamp = metric.get('timestamp')
        metric_type = metric.get('metric_type', '')
        
        # Handle individual round metrics
        if metric_type.startswith('fl_round_'):
            round_metric = self._process_individual_round_metric(
                metric, raw_metrics, base_timestamp, metric_type,
                optimization_params, include_raw, consolidate_rounds, processed_rounds
            )
            if round_metric:
                results.append(round_metric)
        
        # Handle FL server snapshot metrics
        elif metric_type == 'fl_server':
            server_results = self._process_fl_server_metric(
                metric, raw_metrics, base_timestamp, optimization_params,
                include_raw, include_rounds, consolidate_rounds,
                min_round, max_round, processed_rounds
            )
            results.extend(server_results)
        
        return results
    
    def _process_individual_round_metric(self, metric: Dict[str, Any],
                                         raw_metrics: Dict[str, Any],
                                         base_timestamp: str,
                                         metric_type: str,
                                         optimization_params: Dict[str, Any],
                                         include_raw: bool,
                                         consolidate_rounds: bool,
                                         processed_rounds: Set[int]) -> Optional[Dict[str, Any]]:
        """Process an individual round metric."""
        try:
            round_num = int(metric_type.split('_')[-1])
            if consolidate_rounds and round_num in processed_rounds:
                return None
            
            processed_rounds.add(round_num)
            
            clients_connected = self._extract_clients_connected(raw_metrics)
            model_size_mb = self._extract_model_size(raw_metrics)
            
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
            
            if not optimization_params.get("use_sampling"):
                round_metric['model_size_mb'] = model_size_mb
            
            if include_raw and not optimization_params.get("use_sampling"):
                round_metric['raw_metrics'] = raw_metrics
            
            return round_metric
            
        except (ValueError, IndexError):
            return None
    
    def _process_fl_server_metric(self, metric: Dict[str, Any],
                                  raw_metrics: Dict[str, Any],
                                  base_timestamp: str,
                                  optimization_params: Dict[str, Any],
                                  include_raw: bool,
                                  include_rounds: bool,
                                  consolidate_rounds: bool,
                                  min_round: int,
                                  max_round: Optional[int],
                                  processed_rounds: Set[int]) -> List[Dict[str, Any]]:
        """Process an FL server snapshot metric."""
        results = []
        current_round = raw_metrics.get('current_round', 0)
        
        accuracy, loss = self._extract_accuracy_loss(raw_metrics)
        
        fl_server_metric = {
            'timestamp': base_timestamp,
            'round': current_round,
            'status': raw_metrics.get('status', 'unknown'),
            'clients_connected': raw_metrics.get('connected_clients', 0),
            'clients_total': raw_metrics.get('connected_clients', 0),
            'accuracy': accuracy,
            'loss': loss,
            'training_complete': raw_metrics.get('training_complete', False),
            'data_state': raw_metrics.get('data_state', 'training'),
            'source': 'fl_server_snapshot',
            'model_size_mb': raw_metrics.get('model_size_mb', 0)
        }
        
        if not optimization_params.get("use_sampling"):
            fl_server_metric['model_size_mb'] = raw_metrics.get('model_size_mb', 0)
            fl_server_metric['training_duration'] = raw_metrics.get('total_training_duration', 0)
        
        if include_raw and not optimization_params.get("use_sampling"):
            fl_server_metric['raw_metrics'] = raw_metrics
        
        results.append(fl_server_metric)
        
        # Extract rounds history
        rounds_history = self._extract_rounds_history(raw_metrics)
        
        if rounds_history and include_rounds:
            history_results = self._process_rounds_history(
                rounds_history, raw_metrics, base_timestamp, optimization_params,
                include_raw, consolidate_rounds, min_round, max_round, processed_rounds
            )
            results.extend(history_results)
        else:
            snapshot_result = self._process_snapshot_only(
                raw_metrics, base_timestamp, optimization_params, include_raw,
                consolidate_rounds, min_round, max_round, processed_rounds
            )
            if snapshot_result:
                results.append(snapshot_result)
        
        return results
    
    def _extract_accuracy_loss(self, raw_metrics: Dict[str, Any]) -> Tuple[float, float]:
        """Extract accuracy and loss from raw metrics."""
        accuracy = 0.0
        loss = 0.0
        
        if 'last_round_metrics' in raw_metrics:
            last_round = raw_metrics['last_round_metrics']
            if isinstance(last_round, dict):
                accuracy = last_round.get('accuracy', 0)
                loss = last_round.get('loss', 0)
            elif isinstance(last_round, str) and 'accuracy=' in last_round:
                acc_match = re.search(r'accuracy=([0-9.]+)', last_round)
                loss_match = re.search(r'loss=([0-9.]+)', last_round)
                if acc_match:
                    accuracy = float(acc_match.group(1))
                if loss_match:
                    loss = float(loss_match.group(1))
        
        if accuracy == 0.0 and 'training_stats' in raw_metrics:
            training_stats = raw_metrics['training_stats']
            if isinstance(training_stats, dict):
                accuracy = training_stats.get('latest_accuracy', training_stats.get('best_accuracy', 0))
            elif isinstance(training_stats, str) and 'accuracy=' in training_stats:
                acc_match = re.search(r'latest_accuracy=([0-9.]+)', training_stats)
                if not acc_match:
                    acc_match = re.search(r'best_accuracy=([0-9.]+)', training_stats)
                if acc_match:
                    accuracy = float(acc_match.group(1))
        
        return accuracy, loss
    
    def _extract_clients_connected(self, raw_metrics: Dict[str, Any]) -> int:
        """Extract clients connected from raw metrics."""
        clients_connected = (
            raw_metrics.get('clients') or
            raw_metrics.get('clients_connected') or
            raw_metrics.get('connected_clients') or
            raw_metrics.get('successful_clients') or
            raw_metrics.get('participating_clients') or
            0
        )
        return clients_connected
    
    def _extract_model_size(self, raw_metrics: Dict[str, Any]) -> float:
        """Extract model size from raw metrics."""
        model_size_mb = raw_metrics.get('model_size_mb', 0.0)
        if model_size_mb is None or model_size_mb == 0:
            model_size_mb = raw_metrics.get('model_size', 0.0)
        return model_size_mb
    
    def _extract_rounds_history(self, raw_metrics: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Extract rounds history from raw metrics."""
        if 'rounds_history' in raw_metrics and isinstance(raw_metrics['rounds_history'], list):
            return raw_metrics['rounds_history']
        elif 'round_history' in raw_metrics and isinstance(raw_metrics['round_history'], list):
            return raw_metrics['round_history']
        elif 'rounds' in raw_metrics and isinstance(raw_metrics['rounds'], list):
            return raw_metrics['rounds']
        return None
    
    def _process_rounds_history(self, rounds_history: List[Dict[str, Any]],
                                raw_metrics: Dict[str, Any],
                                base_timestamp: str,
                                optimization_params: Dict[str, Any],
                                include_raw: bool,
                                consolidate_rounds: bool,
                                min_round: int,
                                max_round: Optional[int],
                                processed_rounds: Set[int]) -> List[Dict[str, Any]]:
        """Process rounds history from FL server metrics."""
        results = []
        
        if optimization_params.get("use_sampling") and len(rounds_history) > 100:
            step = max(1, len(rounds_history) // 50)
            rounds_history = rounds_history[::step]
        
        for idx, round_entry in enumerate(rounds_history):
            round_num = round_entry.get('round', idx + 1)
            
            if round_num < min_round or (max_round is not None and round_num > max_round):
                continue
            
            if consolidate_rounds and round_num in processed_rounds:
                continue
            
            processed_rounds.add(round_num)
            
            round_timestamp = round_entry.get('timestamp', base_timestamp)
            
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
            
            if not optimization_params.get("use_sampling"):
                round_metric['model_size_mb'] = raw_metrics.get('model_size_mb', 0)
            
            if include_raw and not optimization_params.get("use_sampling"):
                round_metric['raw_metrics'] = {
                    'round_data': round_entry,
                    'server_data': raw_metrics
                }
            
            results.append(round_metric)
        
        return results
    
    def _process_snapshot_only(self, raw_metrics: Dict[str, Any],
                               base_timestamp: str,
                               optimization_params: Dict[str, Any],
                               include_raw: bool,
                               consolidate_rounds: bool,
                               min_round: int,
                               max_round: Optional[int],
                               processed_rounds: Set[int]) -> Optional[Dict[str, Any]]:
        """Process FL server snapshot when no rounds history available."""
        last_round_metrics = raw_metrics.get('last_round_metrics', {})
        current_round = raw_metrics.get('current_round', 0)
        
        if current_round < min_round or (max_round is not None and current_round > max_round):
            return None
        
        if consolidate_rounds and current_round in processed_rounds:
            return None
        
        processed_rounds.add(current_round)
        
        formatted_metric = {
            'timestamp': base_timestamp,
            'round': current_round,
            'status': raw_metrics.get('status', 'unknown'),
            'clients_connected': raw_metrics.get('connected_clients', 0),
            'clients_total': raw_metrics.get('connected_clients', 0),
            'accuracy': last_round_metrics.get('accuracy', 0) if isinstance(last_round_metrics, dict) else 0,
            'loss': last_round_metrics.get('loss', 0) if isinstance(last_round_metrics, dict) else 0,
            'training_complete': raw_metrics.get('training_complete', False),
            'training_duration': raw_metrics.get('total_training_duration', 0),
            'data_state': 'training_complete' if raw_metrics.get('training_complete', False) else ('training' if current_round > 0 else 'initializing'),
            'source': 'fl_server_snapshot',
            'model_size_mb': raw_metrics.get('model_size_mb', 0)
        }
        
        if not optimization_params.get("use_sampling"):
            formatted_metric['model_size_mb'] = raw_metrics.get('model_size_mb', 0)
        
        if include_raw and not optimization_params.get("use_sampling"):
            formatted_metric['raw_metrics'] = raw_metrics
        
        return formatted_metric
    
    def build_training_summary(self, formatted_metrics: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build training summary from formatted metrics."""
        if not formatted_metrics:
            return None
        
        completed_rounds = [m for m in formatted_metrics if m.get('accuracy', 0) > 0]
        if not completed_rounds:
            return None
        
        accuracies = [m['accuracy'] for m in completed_rounds]
        
        return {
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


class CollectorRoundsExtractor:
    """
    Extracts FL rounds from collector storage with enhanced processing.
    """
    
    def __init__(self, storage):
        """
        Initialize the extractor.
        
        Args:
            storage: MetricsStorage instance for data access
        """
        self.storage = storage
    
    def extract(self, limit: int, start_round: int, end_round: Optional[int],
               min_accuracy: Optional[float], max_accuracy: Optional[float],
               format_type: str) -> List[Dict[str, Any]]:
        """
        Extract FL rounds from collector storage.
        
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
        collector_rounds = []
        
        try:
            # Get FL metrics from storage
            all_fl_metrics = self.storage.load_metrics(
                type_filter='fl_server',
                limit=limit * 3,
                sort_desc=True
            )
            
            # Also try individual round metrics
            try:
                all_recent = self.storage.load_metrics(limit=limit * 5, sort_desc=True)
                round_metrics = [m for m in all_recent if m.get('metric_type', '').startswith('fl_round_')]
                all_fl_metrics = round_metrics + all_fl_metrics
            except Exception:
                pass
            
            processed_metrics = self._process_raw_metrics(all_fl_metrics)
            collector_rounds = self._convert_to_rounds(
                processed_metrics, start_round, end_round,
                min_accuracy, max_accuracy, format_type
            )
            
            logger.info(f"Retrieved {len(collector_rounds)} rounds from enhanced FL processing")
            
        except Exception as e:
            logger.error(f"Error processing FL metrics directly: {e}")
        
        return collector_rounds
    
    def _process_raw_metrics(self, all_fl_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw metrics into a normalized format."""
        processed_metrics = []
        
        for metric in all_fl_metrics:
            try:
                data = metric.get('data', {})
                metric_type = metric.get('metric_type', '')
                
                # Enhanced round number extraction
                round_num = (
                    data.get('round') or
                    data.get('current_round') or
                    (int(metric_type.split('_')[-1]) if metric_type.startswith('fl_round_') and metric_type.split('_')[-1].isdigit() else 0) or
                    0
                )
                
                if round_num > 0:
                    clients_connected = self._extract_clients(data)
                    model_size_mb = self._extract_model_size(data)
                    accuracy = self._extract_accuracy(data)
                    loss = self._extract_loss(data)
                    
                    processed_metric = {
                        'round': round_num,
                        'timestamp': metric.get('timestamp', data.get('timestamp')),
                        'accuracy': accuracy,
                        'loss': loss,
                        'clients_connected': clients_connected,
                        'training_duration': data.get('training_duration', 0),
                        'model_size_mb': model_size_mb,
                        'status': data.get('status', 'complete'),
                        'source_type': metric_type
                    }
                    
                    processed_metrics.append(processed_metric)
            
            except Exception as e:
                logger.debug(f"Error processing FL metric: {e}")
                continue
        
        return processed_metrics
    
    def _extract_clients(self, data: Dict[str, Any]) -> int:
        """Extract clients connected from metric data."""
        client_sources = [
            data.get('clients'),
            data.get('clients_connected'),
            data.get('connected_clients'),
            data.get('successful_clients'),
            data.get('participating_clients'),
            data.get('num_clients'),
            data.get('last_round_metrics', {}).get('clients') if isinstance(data.get('last_round_metrics'), dict) else None,
        ]
        
        for source in client_sources:
            if source is not None and source > 0:
                return int(source)
        
        return 0
    
    def _extract_model_size(self, data: Dict[str, Any]) -> float:
        """Extract model size from metric data."""
        model_size_sources = [
            data.get('model_size_mb'),
            data.get('model_size'),
            data.get('last_round_metrics', {}).get('model_size_mb') if isinstance(data.get('last_round_metrics'), dict) else None,
        ]
        
        for source in model_size_sources:
            if source is not None and source > 0:
                try:
                    return float(source)
                except (ValueError, TypeError):
                    continue
        
        return 0.0
    
    def _extract_accuracy(self, data: Dict[str, Any]) -> float:
        """Extract accuracy from metric data."""
        return (
            data.get('accuracy') or
            (data.get('last_round_metrics', {}).get('accuracy') if isinstance(data.get('last_round_metrics'), dict) else 0) or
            0
        )
    
    def _extract_loss(self, data: Dict[str, Any]) -> float:
        """Extract loss from metric data."""
        return (
            data.get('loss') or
            (data.get('last_round_metrics', {}).get('loss') if isinstance(data.get('last_round_metrics'), dict) else 0) or
            0
        )
    
    def _convert_to_rounds(self, processed_metrics: List[Dict[str, Any]],
                          start_round: int, end_round: Optional[int],
                          min_accuracy: Optional[float], max_accuracy: Optional[float],
                          format_type: str) -> List[Dict[str, Any]]:
        """Convert processed metrics to round format with filtering."""
        collector_rounds = []
        
        for metric in processed_metrics:
            try:
                round_num = metric.get('round', 0)
                
                if round_num <= 0:
                    continue
                if round_num < start_round:
                    continue
                if end_round and round_num > end_round:
                    continue
                
                accuracy = metric.get('accuracy', 0)
                
                if min_accuracy is not None and accuracy < min_accuracy:
                    continue
                if max_accuracy is not None and accuracy > max_accuracy:
                    continue
                
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
                
                # Avoid duplicates
                if not any(r['round'] == round_num for r in collector_rounds):
                    collector_rounds.append(round_data)
            
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping invalid FL metric for round conversion: {e}")
                continue
        
        return collector_rounds
