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
    FlMetricsCache,
    MetricsOptimizer,
    cache_fl_metrics,
    get_cache_key,
    invalidate_fl_cache,
)

__all__ = [
    # Response builders
    'build_fl_response',
    'optimize_fl_metrics_query',
    'calculate_fl_statistics',
    'format_round_data',
    # Caching utilities
    'FlMetricsCache',
    'MetricsOptimizer',
    'cache_fl_metrics',
    'get_cache_key',
    'invalidate_fl_cache',
]
