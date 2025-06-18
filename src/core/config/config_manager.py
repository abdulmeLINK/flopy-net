"""
Configuration Manager

This module provides a centralized configuration manager for the federated learning system.
"""
import logging
import os
import json
import yaml
from typing import Dict, Any, Optional
import threading


class ConfigManager:
    """
    Centralized configuration manager.
    
    This class manages configuration for the entire system, loading from
    files and providing access to configuration values.
    """
    
    def __init__(self, config_dir: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            logger: Optional logger
        """
        self.config_dir = config_dir or os.path.join(os.getcwd(), 'config')
        self.config: Dict[str, Any] = {}
        self.lock = threading.RLock()
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure config directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            self.logger.info(f"Created configuration directory: {self.config_dir}")
    
    def load_config(self, config_name: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            config_name: Name of the configuration file (without extension)
            
        Returns:
            True if loaded successfully, False otherwise
        """
        with self.lock:
            try:
                # Try JSON first
                json_path = os.path.join(self.config_dir, f"{config_name}.json")
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        config = json.load(f)
                        self.config.update(config)
                        self.logger.info(f"Loaded configuration from {json_path}")
                        return True
                
                # Try YAML next
                yaml_path = os.path.join(self.config_dir, f"{config_name}.yaml")
                if os.path.exists(yaml_path):
                    with open(yaml_path, 'r') as f:
                        config = yaml.safe_load(f)
                        self.config.update(config)
                        self.logger.info(f"Loaded configuration from {yaml_path}")
                        return True
                
                # Try YML next
                yml_path = os.path.join(self.config_dir, f"{config_name}.yml")
                if os.path.exists(yml_path):
                    with open(yml_path, 'r') as f:
                        config = yaml.safe_load(f)
                        self.config.update(config)
                        self.logger.info(f"Loaded configuration from {yml_path}")
                        return True
                
                self.logger.warning(f"Configuration file {config_name} not found")
                return False
            except Exception as e:
                self.logger.error(f"Error loading configuration {config_name}: {e}")
                return False
    
    def load_configs(self, config_names: list) -> bool:
        """
        Load multiple configuration files.
        
        Args:
            config_names: List of configuration file names
            
        Returns:
            True if all loaded successfully, False otherwise
        """
        with self.lock:
            all_success = True
            for config_name in config_names:
                if not self.load_config(config_name):
                    all_success = False
            return all_success
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (can use dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self.lock:
            # Handle dot notation
            if '.' in key:
                parts = key.split('.')
                value = self.config
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return default
                return value
            
            return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (can use dot notation for nested values)
            value: Value to set
        """
        with self.lock:
            # Handle dot notation
            if '.' in key:
                parts = key.split('.')
                config = self.config
                for part in parts[:-1]:
                    if part not in config:
                        config[part] = {}
                    config = config[part]
                config[parts[-1]] = value
            else:
                self.config[key] = value
            
            self.logger.debug(f"Set configuration {key}")
    
    def save_config(self, config_name: str, format: str = 'json') -> bool:
        """
        Save the current configuration to a file.
        
        Args:
            config_name: Name of the configuration file (without extension)
            format: Format to save in ('json' or 'yaml')
            
        Returns:
            True if saved successfully, False otherwise
        """
        with self.lock:
            try:
                if format == 'json':
                    path = os.path.join(self.config_dir, f"{config_name}.json")
                    with open(path, 'w') as f:
                        json.dump(self.config, f, indent=2)
                elif format in ('yaml', 'yml'):
                    path = os.path.join(self.config_dir, f"{config_name}.yaml")
                    with open(path, 'w') as f:
                        yaml.dump(self.config, f, default_flow_style=False)
                else:
                    self.logger.error(f"Unsupported format: {format}")
                    return False
                
                self.logger.info(f"Saved configuration to {path}")
                return True
            except Exception as e:
                self.logger.error(f"Error saving configuration {config_name}: {e}")
                return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration.
        
        Returns:
            Complete configuration dictionary
        """
        with self.lock:
            return self.config.copy()
    
    def clear(self) -> None:
        """Clear the configuration."""
        with self.lock:
            self.config.clear()
            self.logger.debug("Cleared configuration")
    
    def load_environment_variables(self, prefix: str = 'FL_') -> None:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variables to load
        """
        with self.lock:
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    # Convert key from FL_SERVER_PORT to server.port
                    config_key = key[len(prefix):].lower().replace('_', '.')
                    
                    # Try to convert to appropriate type
                    if value.isdigit():
                        value = int(value)
                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                        value = float(value)
                    
                    self.set(config_key, value)
                    
            self.logger.info("Loaded configuration from environment variables")


# Create a global instance
config_manager = ConfigManager() 