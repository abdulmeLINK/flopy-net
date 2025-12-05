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
Metrics Cache - Simple in-memory caching for frequently accessed metrics data.

This module provides caching utilities for the Collector API to improve
performance for frequently accessed endpoints like FL metrics.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MetricsCache:
    """Simple in-memory cache for metrics data with TTL support."""
    
    def __init__(self, default_ttl: int = 10):
        """Initialize the metrics cache.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a cached value if available and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        # Check if expired
        timestamp = self._timestamps.get(key, 0)
        if time.time() - timestamp > self._default_ttl:
            self._remove(key)
            return None
        
        logger.debug(f"Cache hit for key: {key[:16]}...")
        return self._cache[key]
    
    def set(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Store data in the cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Optional TTL override
        """
        self._cache[key] = data
        self._timestamps[key] = time.time()
        logger.debug(f"Cached data for key: {key[:16]}...")
    
    def _remove(self, key: str) -> None:
        """Remove a key from the cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._timestamps.clear()
        logger.debug("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > self._default_ttl
        ]
        
        for key in expired_keys:
            self._remove(key)
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


# Global cache instances for different metric types
fl_metrics_cache = MetricsCache(default_ttl=10)
events_cache = MetricsCache(default_ttl=5)
network_cache = MetricsCache(default_ttl=30)


def get_optimization_params(limit: int, include_rounds: bool = True, 
                            rounds_only: bool = False) -> Dict[str, Any]:
    """Get optimization parameters based on request size.
    
    This function determines the optimal query strategy based on the
    requested data size to balance performance and completeness.
    
    Args:
        limit: Maximum number of records to return
        include_rounds: Whether round details are requested
        rounds_only: Whether only round data is requested
        
    Returns:
        Dictionary with optimization parameters
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


def create_cache_key(*args) -> str:
    """Create a cache key from arguments.
    
    Args:
        *args: Values to include in the cache key
        
    Returns:
        MD5 hash as cache key string
    """
    import hashlib
    key_str = "_".join(str(arg) for arg in args)
    return hashlib.md5(key_str.encode()).hexdigest()
