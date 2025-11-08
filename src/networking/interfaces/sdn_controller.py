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
SDN Controller Interface

This module defines the interface that all SDN controllers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class ISDNController(ABC):
    """Interface for SDN Controllers"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the SDN controller with the given configuration.
        
        Args:
            config: Controller configuration dictionary
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the SDN controller.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the SDN controller.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the SDN controller.
        
        Returns:
            Dictionary with status information
        """
        pass
    
    @abstractmethod
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology.
        
        Returns:
            Dictionary representing the network topology
        """
        pass
    
    @abstractmethod
    def add_flow(self, switch_id: str, flow_spec: Dict[str, Any]) -> bool:
        """
        Add a flow entry to a switch.
        
        Args:
            switch_id: ID of the switch
            flow_spec: Flow specification
            
        Returns:
            True if flow was added successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_flow(self, switch_id: str, flow_id: str) -> bool:
        """
        Remove a flow entry from a switch.
        
        Args:
            switch_id: ID of the switch
            flow_id: ID of the flow to remove
            
        Returns:
            True if flow was removed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_flows(self, switch_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get flow entries from one or all switches.
        
        Args:
            switch_id: ID of the switch (None for all switches)
            
        Returns:
            Dictionary mapping switch IDs to lists of flow entries
        """
        pass
    
    @abstractmethod
    def get_switches(self) -> List[Dict[str, Any]]:
        """
        Get all switches in the network.
        
        Returns:
            List of switch information dictionaries
        """
        pass
    
    @abstractmethod
    def get_links(self) -> List[Dict[str, Any]]:
        """
        Get all links in the network.
        
        Returns:
            List of link information dictionaries
        """
        pass
    
    @abstractmethod
    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply a network policy.
        
        Args:
            policy: Policy specification
            
        Returns:
            True if policy was applied successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current network metrics.
        
        Returns:
            Dictionary with metric information
        """
        pass 