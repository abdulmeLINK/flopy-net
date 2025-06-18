"""
Utilities for handling metrics data.
"""

from typing import Dict, Any, Optional, List, Union
import logging

logger = logging.getLogger(__name__)

def get_safe_metric(stats: Dict[str, Any], key: str, default_value: Any = 0) -> Any:
    """
    Safely get a metric from stats dictionary, returning a default value if not found.
    
    Args:
        stats: Dictionary containing metrics
        key: Key to retrieve from the dictionary
        default_value: Default value to return if key not found
        
    Returns:
        The value for the key if it exists, otherwise the default value
    """
    if not stats:
        return default_value
        
    if key in stats:
        return stats[key]
    
    logger.debug(f"Metric '{key}' not found in stats dictionary")
    return default_value 