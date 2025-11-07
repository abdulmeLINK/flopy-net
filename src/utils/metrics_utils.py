#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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