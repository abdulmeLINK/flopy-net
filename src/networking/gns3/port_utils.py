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
Port management utilities for GNS3 network simulations.

This module provides functions for managing and freeing up ports used by GNS3.
"""

import logging
import platform
import subprocess
import traceback

logger = logging.getLogger(__name__)

def kill_port_processes() -> int:
    """
    Identify and terminate processes that are using ports in the GNS3 port range.
    This is a minimal implementation that only logs issues and doesn't attempt fallbacks.
    
    Returns:
        Number of processes killed
    """
    killed_count = 0
    try:
        system = platform.system()
        logger.info(f"Checking for port conflicts on {system}")
        
        # Just log that we would need to check ports, but don't actually kill anything
        logger.info("Port conflict resolution disabled - would need to be handled manually")
        
        # Log a warning that the user needs to make sure ports are available
        logger.warning("GNS3 requires free UDP and TCP ports in the 5000-10000 range")
        logger.warning("If you encounter port conflicts, you may need to manually free up ports")
        
        return killed_count
        
    except Exception as e:
        logger.error(f"Error checking port processes: {e}")
        logger.error(traceback.format_exc())
        return killed_count 