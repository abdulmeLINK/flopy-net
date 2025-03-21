"""
Network Simulator Interface

This module defines the interface for network simulators that can
simulate network conditions for federated learning scenarios.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class INetworkSimulator(ABC):
    """Interface defining the contract for network simulators."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the network simulator.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    @abstractmethod
    def create_topology(self, topology_config: Dict[str, Any]) -> bool:
        """
        Create a network topology based on configuration.
        
        Args:
            topology_config: Topology configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_simulation(self) -> bool:
        """
        Start the network simulation.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_simulation(self) -> bool:
        """
        Stop the network simulation.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get the current status of the simulation.
        
        Returns:
            Dictionary containing simulation status information
        """
        pass
    
    @abstractmethod
    def add_link_delay(self, source: str, target: str, delay_ms: int) -> bool:
        """
        Add delay to a network link.
        
        Args:
            source: Source node ID
            target: Target node ID
            delay_ms: Delay in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_link_loss(self, source: str, target: str, loss_percentage: float) -> bool:
        """
        Add packet loss to a network link.
        
        Args:
            source: Source node ID
            target: Target node ID
            loss_percentage: Loss percentage (0-100)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_link_bandwidth(self, source: str, target: str, bandwidth_mbps: int) -> bool:
        """
        Set bandwidth for a network link.
        
        Args:
            source: Source node ID
            target: Target node ID
            bandwidth_mbps: Bandwidth in Mbps
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_client_node(self, client_id: str, host_config: Dict[str, Any]) -> bool:
        """
        Add a federated learning client node to the simulation.
        
        Args:
            client_id: Unique client identifier
            host_config: Host configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics from the simulation.
        
        Returns:
            Dictionary containing performance metrics
        """
        pass
    
    @abstractmethod
    def save_simulation_state(self, file_path: str) -> bool:
        """
        Save the current simulation state to a file.
        
        Args:
            file_path: Path to save the simulation state
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def load_simulation_state(self, file_path: str) -> bool:
        """
        Load a simulation state from a file.
        
        Args:
            file_path: Path to load the simulation state from
            
        Returns:
            True if successful, False otherwise
        """
        pass 