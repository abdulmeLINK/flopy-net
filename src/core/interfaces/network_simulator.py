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
Network Simulator Interface

This module defines the interface for network simulators used in the federated learning system.
Network simulators provide the ability to create and manage simulated network environments
for testing federated learning algorithms.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple

class INetworkSimulator(ABC):
    """
    Interface that defines the contract for all network simulator implementations.
    
    Network simulators are responsible for creating and managing a simulated 
    network environment for federated learning clients and servers. They handle
    tasks such as starting and stopping the simulator, retrieving network
    information, and managing client nodes.
    """
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the network simulator.
        
        Returns:
            True if the simulator started successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the network simulator.
        
        Returns:
            True if the simulator stopped successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the network simulator.
        
        Returns:
            Dictionary containing status information about the simulator.
        """
        pass
    
    @abstractmethod
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the network topology information.
        
        Returns:
            Dictionary containing topology details such as nodes and links.
        """
        pass
    
    @abstractmethod
    def get_network_metrics(self) -> Dict[str, Any]:
        """
        Get current network performance metrics.
        
        Returns:
            Dictionary containing network metrics such as bandwidth, latency, and packet loss.
        """
        pass
    
    @abstractmethod
    def add_client_node(self, client_id: str, **kwargs) -> bool:
        """
        Add a new client node to the network.
        
        Args:
            client_id: Unique identifier for the client
            **kwargs: Additional configuration parameters for the client
            
        Returns:
            True if the client was added successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_client_node(self, client_id: str) -> bool:
        """
        Remove a client node from the network.
        
        Args:
            client_id: Unique identifier for the client to remove
            
        Returns:
            True if the client was removed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_client_nodes(self) -> List[Dict[str, Any]]:
        """
        Get information about all client nodes.
        
        Returns:
            List of dictionaries containing client node information
        """
        pass
    
    @abstractmethod
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific client node.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Dictionary containing status information about the client
        """
        pass 