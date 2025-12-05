"""
GNS3 Configuration Loader

Centralized configuration loader for GNS3 connection parameters.
This module provides a single point of access for GNS3 server configuration
across all scripts and source files.

Usage:
    from src.utils.gns3_config import gns3_config, get_gns3_url

    # Get full config
    config = gns3_config.get_config()
    
    # Get specific values
    host = gns3_config.host
    port = gns3_config.port
    
    # Get API URL
    url = get_gns3_url()
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GNS3Config:
    """
    Centralized GNS3 configuration management.
    
    Loads configuration from:
    1. config/gns3_connection.json (primary)
    2. Environment variables (override)
    3. Hardcoded defaults (fallback)
    """
    
    _instance = None
    _config_path = "config/gns3_connection.json"
    
    # Default values
    _defaults = {
        'host': '192.168.141.128',
        'port': 80,
        'api_port': 3080,
        'ssh_port': 22,
        'ssh_username': 'gns3',
        'ssh_password': 'gns3',
        'use_https': False,
        'api_version': 'v2',
        'project_name': 'fl_federation',
        'compute_id': 'local'
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
            cls._instance._load_config()
        return cls._instance
    
    def _find_config_file(self) -> Optional[Path]:
        """Find the GNS3 config file in various locations."""
        possible_paths = [
            Path(os.getenv('GNS3_CONFIG_PATH', '')),
            Path(self._config_path),
            Path('config/gns3_connection.json'),
            Path('/app/config/gns3_connection.json'),
            Path(__file__).parent.parent.parent / 'config' / 'gns3_connection.json',
        ]
        
        for path in possible_paths:
            if path and path.exists():
                return path
        
        return None
    
    def _load_config(self) -> None:
        """Load GNS3 configuration from file and environment."""
        config = dict(self._defaults)
        
        # Try to load from file
        config_path = self._find_config_file()
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                
                # Handle nested 'gns3' key
                if 'gns3' in file_config:
                    gns3_data = file_config['gns3']
                    config['host'] = gns3_data.get('host', config['host'])
                    config['port'] = gns3_data.get('port', config['port'])
                    config['project_name'] = gns3_data.get('project_name', config['project_name'])
                    config['compute_id'] = gns3_data.get('compute_id', config['compute_id'])
                    
                    # SSH config
                    if 'ssh' in gns3_data:
                        ssh = gns3_data['ssh']
                        config['ssh_port'] = ssh.get('port', config['ssh_port'])
                        config['ssh_username'] = ssh.get('username', config['ssh_username'])
                        config['ssh_password'] = ssh.get('password', config['ssh_password'])
                else:
                    # Flat config structure
                    config.update(file_config)
                
                logger.debug(f"Loaded GNS3 config from {config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading GNS3 config from {config_path}: {e}")
        else:
            logger.debug("No GNS3 config file found, using defaults")
        
        # Environment variable overrides
        env_mapping = {
            'GNS3_HOST': 'host',
            'GNS3_PORT': ('port', int),
            'GNS3_API_PORT': ('api_port', int),
            'GNS3_SSH_PORT': ('ssh_port', int),
            'GNS3_SSH_USER': 'ssh_username',
            'GNS3_SSH_PASSWORD': 'ssh_password',
            'GNS3_USE_HTTPS': ('use_https', lambda x: x.lower() == 'true'),
            'GNS3_PROJECT_NAME': 'project_name',
            'GNS3_COMPUTE_ID': 'compute_id',
            'GNS3_VM_IP': 'host',  # Alias from network_addressing
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.environ.get(env_var)
            if value:
                if isinstance(config_key, tuple):
                    key, converter = config_key
                    try:
                        config[key] = converter(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid value for {env_var}: {value}")
                else:
                    config[config_key] = value
        
        self._config = config
    
    def reload(self) -> None:
        """Reload configuration from file and environment."""
        self._load_config()
    
    def get_config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return dict(self._config)
    
    @property
    def host(self) -> str:
        """Get GNS3 server host/IP."""
        return self._config['host']
    
    @property
    def port(self) -> int:
        """Get GNS3 API port."""
        return self._config['port']
    
    @property
    def api_port(self) -> int:
        """Get GNS3 API port (alias for port)."""
        return self._config.get('api_port', self._config['port'])
    
    @property
    def ssh_port(self) -> int:
        """Get SSH port."""
        return self._config['ssh_port']
    
    @property
    def ssh_username(self) -> str:
        """Get SSH username."""
        return self._config['ssh_username']
    
    @property
    def ssh_password(self) -> str:
        """Get SSH password."""
        return self._config['ssh_password']
    
    @property
    def use_https(self) -> bool:
        """Check if HTTPS should be used."""
        return self._config['use_https']
    
    @property
    def project_name(self) -> str:
        """Get default project name."""
        return self._config['project_name']
    
    @property
    def compute_id(self) -> str:
        """Get compute ID."""
        return self._config['compute_id']
    
    def get_api_url(self, path: str = '') -> str:
        """
        Get full API URL for GNS3.
        
        Args:
            path: Optional path to append (e.g., '/v2/projects')
            
        Returns:
            Full URL string
        """
        protocol = 'https' if self.use_https else 'http'
        base_url = f"{protocol}://{self.host}:{self.api_port}"
        if path:
            path = path if path.startswith('/') else f'/{path}'
            return f"{base_url}{path}"
        return base_url
    
    def get_ssh_config(self) -> Dict[str, Any]:
        """Get SSH connection parameters."""
        return {
            'hostname': self.host,
            'port': self.ssh_port,
            'username': self.ssh_username,
            'password': self.ssh_password
        }


# Global singleton instance
gns3_config = GNS3Config()


def get_gns3_url(path: str = '') -> str:
    """
    Convenience function to get GNS3 API URL.
    
    Args:
        path: Optional path to append
        
    Returns:
        Full URL string
    """
    return gns3_config.get_api_url(path)


def get_gns3_ssh_config() -> Dict[str, Any]:
    """
    Convenience function to get GNS3 SSH config.
    
    Returns:
        Dictionary with SSH connection parameters
    """
    return gns3_config.get_ssh_config()
