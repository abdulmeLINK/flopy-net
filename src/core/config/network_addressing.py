"""
Centralized Network Addressing Configuration

This module provides the SINGLE SOURCE OF TRUTH for all network IP addresses
in FLOPY-NET. All components should use this module instead of hardcoding IPs.

Usage:
    from src.core.config.network_addressing import network_config
    
    # Get service URLs
    policy_url = network_config.get_service_url('policy_engine')
    
    # Get GNS3/simulator connection
    gns3_url = network_config.get_simulator_url()
    
    # Get client IPs
    client_ip = network_config.get_client_ip(1)  # First client

Environment Variables (override config file values):
    NETWORK_CONFIG_PATH: Path to network_addressing.json
    GNS3_VM_IP: Override simulator host IP
    SUBNET_PREFIX: Override subnet prefix (e.g., "192.168.50")
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class NetworkAddressingError(Exception):
    """Raised when network configuration is invalid or missing."""
    pass


class NetworkConfig:
    """
    Centralized network configuration manager.
    
    Provides computed IP addresses based on subnet_prefix + ip_suffix pattern.
    This allows changing the entire subnet by modifying only subnet_prefix.
    """
    
    _instance: Optional['NetworkConfig'] = None
    _default_config_path = "config/network_addressing.json"
    
    def __new__(cls) -> 'NetworkConfig':
        """Singleton pattern - ensures one config instance across the app."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration (only runs once due to singleton)."""
        if getattr(self, '_initialized', False):
            return
        
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._apply_env_overrides()
        self._initialized = True
    
    def _find_config_path(self) -> Path:
        """Find the configuration file, checking multiple locations."""
        # Check environment variable first
        env_path = os.getenv('NETWORK_CONFIG_PATH') or os.getenv('NETWORK_CONFIG')
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path
            logger.warning(f"NETWORK_CONFIG_PATH={env_path} not found, checking defaults")
        
        # Check relative to current working directory
        cwd_path = Path(self._default_config_path)
        if cwd_path.exists():
            return cwd_path
        
        # Check relative to this file (for when running from src/)
        module_path = Path(__file__).parent.parent.parent.parent / self._default_config_path
        if module_path.exists():
            return module_path
        
        # Check Docker container path
        docker_path = Path("/app") / self._default_config_path
        if docker_path.exists():
            return docker_path
        
        raise NetworkAddressingError(
            f"Network config not found. Checked:\n"
            f"  - NETWORK_CONFIG_PATH env var\n"
            f"  - {cwd_path.absolute()}\n"
            f"  - {module_path}\n"
            f"  - {docker_path}\n"
            f"Please ensure config/network_addressing.json exists."
        )
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        config_path = self._find_config_path()
        logger.info(f"Loading network config from: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise NetworkAddressingError(f"Invalid JSON in {config_path}: {e}")
        except IOError as e:
            raise NetworkAddressingError(f"Cannot read {config_path}: {e}")
        
        # Validate required sections
        required_sections = ['network', 'services', 'simulator']
        for section in required_sections:
            if section not in self._config:
                raise NetworkAddressingError(f"Missing required section '{section}' in config")
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to config."""
        # Override GNS3/simulator host
        gns3_ip = os.getenv('GNS3_VM_IP') or os.getenv('GNS3_HOST')
        if gns3_ip:
            logger.info(f"Overriding simulator host from env: {gns3_ip}")
            self._config['simulator']['host'] = gns3_ip
        
        # Override subnet prefix (changes all service IPs)
        subnet_prefix = os.getenv('SUBNET_PREFIX')
        if subnet_prefix:
            logger.info(f"Overriding subnet prefix from env: {subnet_prefix}")
            self._config['network']['subnet_prefix'] = subnet_prefix
    
    def reload(self) -> None:
        """Force reload configuration from disk."""
        self._initialized = False
        self._config = {}
        self._load_config()
        self._apply_env_overrides()
        self._initialized = True
        # Clear any cached values
        self.get_service_ip.cache_clear()
        self.get_service_url.cache_clear()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        cls._instance = None
    
    # =========================================================================
    # Network Configuration Properties
    # =========================================================================
    
    @property
    def subnet_prefix(self) -> str:
        """Get the subnet prefix (e.g., '192.168.100')."""
        return self._config['network']['subnet_prefix']
    
    @property
    def subnet(self) -> str:
        """Get the full subnet CIDR (e.g., '192.168.100.0/24')."""
        return self._config['network']['subnet']
    
    @property
    def gateway(self) -> str:
        """Get the gateway IP address."""
        return self._config['network']['gateway']
    
    # =========================================================================
    # Simulator/GNS3 Configuration
    # =========================================================================
    
    @property
    def simulator_host(self) -> str:
        """Get the simulator (GNS3 VM) IP address."""
        return self._config['simulator']['host']
    
    @property
    def simulator_api_port(self) -> int:
        """Get the simulator API port."""
        return self._config['simulator']['api_port']
    
    def get_simulator_url(self, protocol: str = 'http') -> str:
        """Get the full simulator API URL."""
        return f"{protocol}://{self.simulator_host}:{self.simulator_api_port}"
    
    def get_simulator_ssh_config(self) -> Dict[str, Any]:
        """Get SSH configuration for the simulator."""
        ssh_config = self._config['simulator'].get('ssh', {})
        return {
            'host': self.simulator_host,
            'port': ssh_config.get('port', 22),
            'username': ssh_config.get('username', 'gns3'),
            'password': ssh_config.get('password', 'gns3'),
        }
    
    def get_gns3_project_name(self) -> str:
        """Get the GNS3 project name."""
        return self._config['simulator'].get('project_name', 'fl_federation')
    
    # =========================================================================
    # Service IP/URL Methods
    # =========================================================================
    
    def _compute_ip(self, ip_suffix: int) -> str:
        """Compute full IP from subnet prefix and suffix."""
        return f"{self.subnet_prefix}.{ip_suffix}"
    
    @lru_cache(maxsize=32)
    def get_service_ip(self, service_name: str) -> str:
        """
        Get the IP address for a service.
        
        Args:
            service_name: One of 'fl_server', 'policy_engine', 'collector',
                         'sdn_controller', 'openvswitch'
        
        Returns:
            Full IP address string
        """
        services = self._config.get('services', {})
        if service_name not in services:
            raise NetworkAddressingError(f"Unknown service: {service_name}")
        
        service = services[service_name]
        ip_suffix = service.get('ip_suffix') or service.get('base_ip_suffix')
        if ip_suffix is None:
            raise NetworkAddressingError(f"No IP suffix defined for {service_name}")
        
        return self._compute_ip(ip_suffix)
    
    def get_service_port(self, service_name: str, port_name: str = None) -> int:
        """
        Get the port for a service.
        
        Args:
            service_name: Service identifier
            port_name: For services with multiple ports (e.g., 'openflow', 'rest')
        
        Returns:
            Port number
        """
        services = self._config.get('services', {})
        if service_name not in services:
            raise NetworkAddressingError(f"Unknown service: {service_name}")
        
        service = services[service_name]
        
        # Handle single port
        if 'port' in service:
            return service['port']
        
        # Handle multiple ports
        if 'ports' in service:
            ports = service['ports']
            if isinstance(ports, dict):
                if port_name and port_name in ports:
                    return ports[port_name]
                # Return first port if no name specified
                return next(iter(ports.values()))
            elif isinstance(ports, list):
                return ports[0]
        
        raise NetworkAddressingError(f"No port defined for {service_name}")
    
    @lru_cache(maxsize=32)
    def get_service_url(self, service_name: str, protocol: str = 'http', 
                        port_name: str = None) -> str:
        """
        Get the full URL for a service.
        
        Args:
            service_name: Service identifier
            protocol: 'http' or 'https'
            port_name: For services with multiple ports
        
        Returns:
            Full URL string (e.g., 'http://192.168.100.20:5000')
        """
        ip = self.get_service_ip(service_name)
        port = self.get_service_port(service_name, port_name)
        return f"{protocol}://{ip}:{port}"
    
    # =========================================================================
    # FL Client Methods
    # =========================================================================
    
    def get_client_ip(self, client_id: int) -> str:
        """
        Generate IP address for an FL client.
        
        Args:
            client_id: Client number (1-indexed)
        
        Returns:
            Client IP address
        """
        if client_id < 1:
            raise NetworkAddressingError(f"Client ID must be >= 1, got {client_id}")
        
        clients = self._config['services'].get('fl_clients', {})
        base_suffix = clients.get('base_ip_suffix', 101)
        max_clients = clients.get('max_clients', 155)
        
        if client_id > max_clients:
            raise NetworkAddressingError(
                f"Client ID {client_id} exceeds max_clients ({max_clients})"
            )
        
        return self._compute_ip(base_suffix + client_id - 1)
    
    def get_max_clients(self) -> int:
        """Get the maximum number of FL clients supported."""
        return self._config['services']['fl_clients'].get('max_clients', 155)
    
    # =========================================================================
    # Northbound Network (for SDN controller external interface)
    # =========================================================================
    
    def get_northbound_ip(self, component: str) -> str:
        """
        Get northbound network IP for a component.
        
        Args:
            component: 'sdn_controller' or 'collector'
        """
        northbound = self._config.get('northbound', {})
        suffix_key = f"{component}_suffix"
        
        if suffix_key in northbound:
            return self._compute_ip(northbound[suffix_key])
        
        raise NetworkAddressingError(f"No northbound IP for {component}")
    
    def get_northbound_interface(self) -> str:
        """Get the northbound network interface name."""
        return self._config.get('northbound', {}).get('interface', 'eth1')
    
    # =========================================================================
    # IP Ranges (for network policies and firewall rules)
    # =========================================================================
    
    def get_ip_range(self, range_name: str) -> str:
        """
        Get an IP range string.
        
        Args:
            range_name: One of 'server', 'policy', 'controller', 'collector',
                       'northbound', 'ovs', 'clients'
        
        Returns:
            Range string (e.g., '10-19')
        """
        ranges = self._config['network'].get('ip_ranges', {})
        if range_name not in ranges:
            raise NetworkAddressingError(f"Unknown IP range: {range_name}")
        return ranges[range_name]
    
    # =========================================================================
    # Export Methods (for generating config files)
    # =========================================================================
    
    def to_env_dict(self) -> Dict[str, str]:
        """
        Export configuration as environment variable dictionary.
        
        Useful for generating .env files or Docker environment blocks.
        """
        env = {
            # Subnet
            'SUBNET_PREFIX': self.subnet_prefix,
            'SUBNET': self.subnet,
            'GATEWAY': self.gateway,
            
            # Simulator
            'GNS3_VM_IP': self.simulator_host,
            'GNS3_API_PORT': str(self.simulator_api_port),
            'GNS3_URL': self.get_simulator_url(),
            'GNS3_PROJECT_NAME': self.get_gns3_project_name(),
            
            # Service IPs
            'NODE_IP_FL_SERVER': self.get_service_ip('fl_server'),
            'NODE_IP_POLICY_ENGINE': self.get_service_ip('policy_engine'),
            'NODE_IP_COLLECTOR': self.get_service_ip('collector'),
            'NODE_IP_SDN_CONTROLLER': self.get_service_ip('sdn_controller'),
            'NODE_IP_OPENVSWITCH': self.get_service_ip('openvswitch'),
            
            # Service Ports
            'FL_SERVER_PORT': str(self.get_service_port('fl_server')),
            'POLICY_PORT': str(self.get_service_port('policy_engine')),
            'COLLECTOR_PORT': str(self.get_service_port('collector')),
            
            # IP Ranges
            'SERVER_IP_RANGE': self.get_ip_range('server'),
            'POLICY_IP_RANGE': self.get_ip_range('policy'),
            'CONTROLLER_IP_RANGE': self.get_ip_range('controller'),
            'OVS_IP_RANGE': self.get_ip_range('ovs'),
            'CLIENT_IP_RANGE': self.get_ip_range('clients'),
            'NORTHBOUND_IP_RANGE': self.get_ip_range('northbound'),
            'COLLECTOR_IP': str(self._config['services']['collector']['ip_suffix']),
            
            # Northbound
            'NORTHBOUND_INTERFACE': self.get_northbound_interface(),
        }
        
        # Add client IPs (first 10 by default)
        for i in range(1, 11):
            try:
                env[f'NODE_IP_FL_CLIENT_{i}'] = self.get_client_ip(i)
            except NetworkAddressingError:
                break
        
        return env
    
    def to_topology_env(self) -> Dict[str, str]:
        """
        Export configuration for topology files (GNS3 node environment).
        
        Returns a dict suitable for node 'environment' sections.
        """
        env = self.to_env_dict()
        
        # Add service URLs for inter-service communication
        env['POLICY_ENGINE_URL'] = self.get_service_url('policy_engine')
        env['COLLECTOR_URL'] = self.get_service_url('collector')
        env['FL_SERVER_URL'] = self.get_service_url('fl_server')
        
        return env
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary (for advanced use cases)."""
        return self._config.copy()


# =============================================================================
# Global Instance (Singleton)
# =============================================================================

# Create the global instance - lazy initialization on first access
def _get_network_config() -> NetworkConfig:
    """Get or create the NetworkConfig singleton."""
    return NetworkConfig()

# Use property-like access pattern for lazy initialization
class _NetworkConfigProxy:
    """Proxy for lazy initialization of network config."""
    _instance: Optional[NetworkConfig] = None
    
    def __getattr__(self, name):
        if self._instance is None:
            try:
                self._instance = NetworkConfig()
            except NetworkAddressingError as e:
                logger.warning(f"NetworkConfig not available: {e}")
                raise
        return getattr(self._instance, name)

network_config = _NetworkConfigProxy()

# =============================================================================
# Backwards Compatibility Aliases
# =============================================================================

# For code that used the old NetworkAddressing class
NetworkAddressing = NetworkConfig
network_addressing = network_config


# =============================================================================
# Convenience Functions
# =============================================================================

def get_gns3_url() -> str:
    """Quick access to GNS3/simulator URL."""
    return network_config.get_simulator_url()


def get_policy_engine_url() -> str:
    """Quick access to policy engine URL."""
    return network_config.get_service_url('policy_engine')


def get_collector_url() -> str:
    """Quick access to collector URL."""
    return network_config.get_service_url('collector')


def get_fl_server_url() -> str:
    """Quick access to FL server URL."""
    return network_config.get_service_url('fl_server')

