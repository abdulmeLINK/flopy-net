"""
Network Simulator Interface for Federated Learning.

This module defines the interface that all network simulators must implement
to be used in the federated learning system.
"""

import abc
from typing import Dict, List, Optional, Tuple, Any

class INetworkSimulator(abc.ABC):
    """Interface for network simulators in federated learning."""
    
    @abc.abstractmethod
    def create_network(self, topo_type: str, topo_params: Dict[str, Any]) -> bool:
        """
        Create a network with the specified topology.
        
        Args:
            topo_type: Type of topology (star, ring, tree, custom)
            topo_params: Parameters for the topology
            
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def create_star_topology(self, n: int) -> bool:
        """
        Create a star topology with n nodes.
        
        Args:
            n: Number of nodes
            
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def create_ring_topology(self, n: int) -> bool:
        """
        Create a ring topology with n nodes.
        
        Args:
            n: Number of nodes
            
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def create_tree_topology(self, depth: int, fanout: int) -> bool:
        """
        Create a tree topology.
        
        Args:
            depth: Tree depth
            fanout: Number of children per node
            
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def create_custom_topology(self, topology: Dict[str, Any]) -> bool:
        """
        Create a custom topology.
        
        Args:
            topology: Topology specification
            
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def start_network(self) -> bool:
        """
        Start the network simulation.
        
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def stop_network(self) -> bool:
        """
        Stop the network simulation.
        
        Returns:
            bool: Success or failure
        """
        pass
    
    @abc.abstractmethod
    def get_hosts(self) -> List[str]:
        """
        Get the list of hosts in the network.
        
        Returns:
            List[str]: List of host names
        """
        pass
    
    @abc.abstractmethod
    def run_cmd_on_host(self, host: str, cmd: str) -> Tuple[bool, str]:
        """
        Run a command on a specific host.
        
        Args:
            host: Host name
            cmd: Command to run
            
        Returns:
            Tuple[bool, str]: Success flag and command output
        """
        pass
    
    @abc.abstractmethod
    def configure_link(self, src: str, dst: str, bandwidth: float, latency: float, 
                       packet_loss: float) -> bool:
        """
        Configure parameters for a specific link.
        
        Args:
            src: Source node
            dst: Destination node
            bandwidth: Bandwidth in Mbps
            latency: Latency in ms
            packet_loss: Packet loss percentage
            
        Returns:
            bool: True if the link was configured successfully, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def get_link_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all links in the network.
        
        Returns:
            List[Dict[str, Any]]: List of link statistics
        """
        pass
    
    @abc.abstractmethod
    def simulate_federated_learning_round(self, model_size: float, num_clients: int) -> Dict[str, Any]:
        """
        Simulate a federated learning round and gather metrics.
        
        Args:
            model_size: Size of the model in MB
            num_clients: Number of clients participating
            
        Returns:
            Dictionary containing simulation results
        """
        pass 