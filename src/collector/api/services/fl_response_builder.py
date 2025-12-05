"""
FL Metrics Response Builder

Utility functions for building FL metrics responses.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def build_fl_response(
    rounds_data: List[Dict[str, Any]],
    total_rounds: int,
    latest_round: int,
    limit: int,
    offset: int,
    format_type: str,
    include_stats: bool,
    include_charts: bool,
    start_round: Optional[int],
    end_round: Optional[int],
    min_accuracy: Optional[float],
    max_accuracy: Optional[float],
    source: str,
    sort_order: str,
    fl_server_count: int,
    collector_count: int,
    start_time: float
) -> Dict[str, Any]:
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


def optimize_fl_metrics_query(limit: int, include_rounds: bool, rounds_only: bool) -> Dict[str, Any]:
    """Optimize FL metrics query parameters based on request size."""
    
    # For large requests, use optimized strategies
    if limit > 500:
        # Large dataset - use sampling and reduced data
        optimized_params = {
            "use_sampling": True,
            "sample_rate": min(0.5, 1000 / limit),
            "include_raw": False,
            "consolidate_rounds": True,
            "batch_size": 200
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


def calculate_fl_statistics(rounds_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics for FL rounds data."""
    if not rounds_data:
        return {}
    
    completed_rounds = [r for r in rounds_data if r.get('accuracy', 0) > 0]
    
    if not completed_rounds:
        return {
            'total_rounds': len(rounds_data),
            'completed_rounds': 0,
            'best_accuracy': 0,
            'latest_accuracy': 0,
            'average_accuracy': 0,
            'accuracy_improvement': 0,
            'training_duration_total': 0
        }
    
    accuracies = [r['accuracy'] for r in completed_rounds]
    
    return {
        'total_rounds': len(rounds_data),
        'completed_rounds': len(completed_rounds),
        'best_accuracy': max(accuracies),
        'latest_accuracy': completed_rounds[-1]['accuracy'],
        'average_accuracy': sum(accuracies) / len(accuracies),
        'accuracy_improvement': accuracies[-1] - accuracies[0] if len(accuracies) > 1 else 0,
        'training_duration_total': sum(r.get('training_duration', 0) for r in rounds_data)
    }


def format_round_data(
    round_num: int,
    data: Dict[str, Any],
    timestamp: Optional[str] = None,
    source: str = 'unknown'
) -> Dict[str, Any]:
    """Format a single round's data into a standard structure."""
    return {
        'round': round_num,
        'timestamp': data.get('timestamp', timestamp),
        'status': data.get('status', 'complete'),
        'accuracy': float(data.get('accuracy', 0)),
        'loss': float(data.get('loss', 0)),
        'training_duration': float(data.get('training_duration', 0)),
        'model_size_mb': float(data.get('model_size_mb', 0)),
        'clients': int(data.get('clients', 0)),
        'data_source': source,
        'training_complete': data.get('training_complete', False)
    }
