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
Configuration Management Module

This module provides utilities for loading and managing configuration files.
"""

from src.core.config.config_manager import ConfigManager
from src.core.config.config_loader import load_config_file, get_config_path

# Configuration getters for different services
def get_policy_engine_config(config_path=None):
    """Get the policy engine configuration"""
    if config_path is None:
        config_path = get_config_path('policy_config.json')
    return load_config_file(config_path)

def get_fl_server_config(config_path=None):
    """Get the FL server configuration"""
    if config_path is None:
        config_path = get_config_path('server_config.json')
    return load_config_file(config_path)

def get_fl_client_config(config_path=None):
    """Get the FL client configuration"""
    if config_path is None:
        config_path = get_config_path('client_config.json')
    return load_config_file(config_path)

# If SDN controller or agent specific configurations are needed in the future,
# they should ideally use the JSON/YAML format consistent with ConfigManager
# or have a clear justification for a different format.

__all__ = [
    'ConfigManager',
    'load_config_file',
    'get_config_path',
    'get_policy_engine_config',
    'get_fl_server_config',
    'get_fl_client_config',
] 