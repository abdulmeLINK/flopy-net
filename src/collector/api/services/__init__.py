"""
Collector API Services Package

Provides reusable service modules for the collector API.
"""

from .fl_response_builder import (
    build_fl_response,
    optimize_fl_metrics_query,
    calculate_fl_statistics,
    format_round_data,
)

from .metrics_cache import (
    MetricsCache,
    fl_metrics_cache,
    events_cache,
    network_cache,
    get_optimization_params,
    create_cache_key,
)

__all__ = [
    # Response builders
    'build_fl_response',
    'optimize_fl_metrics_query',
    'calculate_fl_statistics',
    'format_round_data',
    # Caching utilities
    'MetricsCache',
    'fl_metrics_cache',
    'events_cache',
    'network_cache',
    'get_optimization_params',
    'create_cache_key',
]
