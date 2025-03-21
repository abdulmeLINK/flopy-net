"""
SDN Controller Interface

This module defines the interface for SDN controllers that can manage network 
infrastructure for federated learning.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class ISDNController(ABC):
    """Interface defining the contract for SDN controllers."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the SDN controller.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    @abstractmethod
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology.
        
        Returns:
            Dictionary containing network topology information
        """
        pass
    
    @abstractmethod
    def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific network device.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            Dictionary containing device statistics
        """
        pass
    
    @abstractmethod
    def get_flow_stats(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get flow statistics for devices in the network.
        
        Args:
            device_id: Optional device ID to filter statistics
            
        Returns:
            List of dictionaries containing flow statistics
        """
        pass
    
    @abstractmethod
    def create_flow(self, device_id: str, flow_rule: Dict[str, Any]) -> bool:
        """
        Create a new flow rule on a device.
        
        Args:
            device_id: The ID of the target device
            flow_rule: Flow rule configuration
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_flow(self, device_id: str, flow_id: str) -> bool:
        """
        Remove a flow rule from a device.
        
        Args:
            device_id: The ID of the target device
            flow_id: The ID of the flow to remove
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def optimize_paths(self, source: str, destination: str, 
                       constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Calculate optimal paths between source and destination with constraints.
        
        Args:
            source: Source node ID
            destination: Destination node ID
            constraints: Optional path constraints (bandwidth, latency, etc.)
            
        Returns:
            List of dictionaries representing optimal paths
        """
        pass
    
    @abstractmethod
    def get_link_utilization(self) -> Dict[str, float]:
        """
        Get current link utilization across the network.
        
        Returns:
            Dictionary mapping link IDs to utilization percentages
        """
        pass
    
    @abstractmethod
    def apply_qos_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply quality of service policies to the network.
        
        Args:
            policy: QoS policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        pass 