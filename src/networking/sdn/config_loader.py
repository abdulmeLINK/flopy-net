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
SDN Controller Configuration Loader.

This module provides functionality to load SDN controller configuration.
"""

import os
# import configparser # No longer needed
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_sdn_config(config_path: Optional[str] = None) -> Dict[str, Any]: # config_path is no longer used but kept for API compatibility if ever needed.
    """
    Load SDN controller configuration.
    Currently, this function returns a hardcoded default configuration
    as the INI file 'config/networking/sdn_controller_config.ini' was not found
    and reliance on it has been removed for simplification.

    If specific SDN controller configurations are needed in the future,
    consider using the central JSON/YAML config system (src.core.config.ConfigManager)
    or re-introducing a well-documented file-based config if necessary.
    
    Args:
        config_path: Optional path to a config file (currently ignored).
                    
    Returns:
        Dict containing the configuration
    """
    logger.info("Returning default SDN controller configuration. External INI file loading has been removed.")
    # Default configuration was previously in _get_default_config()
    default_sdn_config = {
        'controller': {
            'enable_policy': True,
            'policy_engine_url': 'http://policy-engine:5000',
            'policy_engine_ip': '', # Typically resolved by Docker DNS using service name
            'northbound_interface': 'eth0',
            'of_port': 6633,       # Standard OpenFlow port
            'rest_port': 8080,       # Common default for Ryu REST API
            'log_level': 'INFO',
            'app_module': 'ryu.app.simple_switch_13' # Default Ryu application
        }
    }
    return default_sdn_config

# _get_default_config() function removed as its content is now in load_sdn_config 