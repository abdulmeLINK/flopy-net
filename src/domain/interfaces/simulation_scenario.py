"""
Simulation Scenario Interface

This module defines the interface that all simulation scenarios must implement.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class ISimulationScenario(ABC):
    """
    Interface for simulation scenarios.
    
    This interface defines the contract that all simulation scenarios must follow
    to be compatible with the simulation system.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the display name of the scenario.
        
        Returns:
            The scenario name
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get the description of the scenario.
        
        Returns:
            The scenario description
        """
        pass
    
    @abstractmethod
    def get_topology_config(self) -> Dict[str, Any]:
        """
        Get the network topology configuration.
        
        Returns:
            A dictionary containing the topology configuration
        """
        pass
    
    @abstractmethod
    def get_server_config(self) -> Dict[str, Any]:
        """
        Get the server configuration.
        
        Returns:
            A dictionary containing the server configuration
        """
        pass
    
    @abstractmethod
    def get_client_configs(self) -> List[Dict[str, Any]]:
        """
        Get the client configurations.
        
        Returns:
            A list of dictionaries containing client configurations
        """
        pass
    
    @abstractmethod
    def get_sdn_policies(self) -> List[Dict[str, Any]]:
        """
        Get the SDN policies for the scenario.
        
        Returns:
            A list of dictionaries containing SDN policies
        """
        pass
    
    @abstractmethod
    def get_network_conditions(self) -> List[Dict[str, Any]]:
        """
        Get the network conditions for the scenario.
        
        Returns:
            A list of dictionaries containing network conditions
        """
        pass
    
    @abstractmethod
    def get_simulation_events(self) -> List[Dict[str, Any]]:
        """
        Get the simulation events for the scenario.
        
        Returns:
            A list of dictionaries containing simulation events
        """
        pass
    
    @abstractmethod
    def get_expected_metrics(self) -> Dict[str, Any]:
        """
        Get the expected metrics for the scenario.
        
        Returns:
            A dictionary containing expected metrics
        """
        pass 