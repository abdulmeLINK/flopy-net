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
Configuration Loader Class

This module provides a ConfigLoader class for loading and accessing configuration 
from a JSON configuration file.

# Note on Naming: This ConfigLoader class provides generic configuration loading capabilities (JSON/YAML).
# It is distinct from the utility function `find_and_load_config` found in `src.core.config.config_loader`,
# which is more specialized for loading the main application configurations (e.g., server_config.json, client_config.json)
# and includes logic for searching default paths. This class is suitable for more general config file loading needs.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

class ConfigLoader:
    """A utility class for loading configuration from a JSON file."""
    
    def __init__(self, config_file: str):
        """
        Initialize the ConfigLoader with a configuration file.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """
        Load the configuration from the file.
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            json.JSONDecodeError: If the configuration file is not valid JSON
        """
        try:
            if not os.path.exists(self.config_file):
                # Try to find the file in common locations
                possible_locations = [
                    self.config_file,  # Try as is first
                    os.path.join(os.getcwd(), self.config_file),  # Relative to cwd
                    os.path.join(os.getcwd(), 'config', os.path.basename(self.config_file)),  # In config dir
                    os.path.join('/app/config', os.path.basename(self.config_file)),  # Docker location
                ]
                
                for location in possible_locations:
                    if os.path.exists(location):
                        self.config_file = location
                        logger.info(f"Found configuration file at: {location}")
                        break
                else:
                    raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
            
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
                logger.info(f"Loaded configuration from: {self.config_file}")
                
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {self.config_file}")
            raise e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {self.config_file}")
            raise e
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise e
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the loaded configuration.
        
        Returns:
            Dict[str, Any]: The loaded configuration
        """
        return self.config
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the configuration using dot notation.
        
        Args:
            key: The key to get, using dot notation (e.g., "server.port")
            default: The default value to return if the key is not found
            
        Returns:
            The value from the configuration, or the default if not found
        """
        if not key:
            return self.config
        
        parts = key.split('.')
        current = self.config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """
        Save the current configuration to a file.
        
        Args:
            config_file: Path to save the configuration to (default: the loaded file)
        """
        save_path = config_file or self.config_file
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.info(f"Saved configuration to: {save_path}")
                
        except Exception as e:
            logger.error(f"Error saving configuration to {save_path}: {e}")
            raise e 