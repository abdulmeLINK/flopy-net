import json
import os
from typing import Dict, Any, Optional

class NetworkAddressing:
    """Centralized network IP address management."""
    
    _instance = None
    _config_path = "config/network_addressing.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load network addressing configuration."""
        config_path = os.getenv('NETWORK_CONFIG', self._config_path)
        with open(config_path, 'r') as f:
            self.config = json.load(f)
    
    def get_service_ip(self, service_name: str) -> str:
        """Get IP address for a service."""
        return self.config['services'][service_name]['ip']
    
    def get_service_port(self, service_name: str) -> int:
        """Get port for a service."""
        return self.config['services'][service_name]['port']
    
    def get_service_url(self, service_name: str, protocol: str = 'http') -> str:
        """Get full URL for a service."""
        ip = self.get_service_ip(service_name)
        port = self.get_service_port(service_name)
        return f"{protocol}://{ip}:{port}"
    
    def get_client_ip(self, client_id: int) -> str:
        """Generate FL client IP address."""
        base_ip = self.config['services']['fl_clients']['base_ip']
        base = int(base_ip.split('.')[-1])
        return f"{self.config['subnet_prefix']}.{base + client_id - 1}"
    
    def get_subnet(self) -> str:
        """Get subnet CIDR."""
        return self.config['subnet']

# Global instance
network_addressing = NetworkAddressing()
