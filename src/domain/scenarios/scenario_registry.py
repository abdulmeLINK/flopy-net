"""
Scenario Registry Module

This module provides a registry for simulation scenarios in the federated learning system.
"""
import logging
from typing import Dict, List, Type, Optional
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger(__name__)

class ISimulationScenario(ABC):
    """Interface for simulation scenarios."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the scenario."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get the description of the scenario."""
        pass
    
    @abstractmethod
    def get_topology_config(self) -> Dict:
        """Get the network topology configuration."""
        pass
    
    @abstractmethod
    def get_server_config(self) -> Dict:
        """Get the server configuration."""
        pass
    
    @abstractmethod
    def get_client_configs(self) -> List[Dict]:
        """Get the client configurations."""
        pass
    
    @abstractmethod
    def get_sdn_policies(self) -> Dict:
        """Get the SDN policies configuration."""
        pass
    
    @abstractmethod
    def get_network_conditions(self) -> Dict:
        """Get the network conditions."""
        pass
    
    @abstractmethod
    def get_simulation_events(self) -> List[Dict]:
        """Get the simulation events."""
        pass
    
    @abstractmethod
    def get_expected_metrics(self) -> Dict:
        """Get the expected metrics for the scenario."""
        pass


class ScenarioRegistry:
    """
    Registry for simulation scenarios.
    
    This class provides functionality to register, retrieve, and manage
    simulation scenarios.
    """
    
    _instance = None
    
    def __new__(cls):
        """
        Create a new instance of ScenarioRegistry using the Singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super(ScenarioRegistry, cls).__new__(cls)
            cls._instance._scenarios = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the scenario registry.
        """
        if not self._initialized:
            self._scenarios = {}
            self._initialized = True
    
    def register_scenario(self, scenario_class: Type[ISimulationScenario]) -> None:
        """
        Register a simulation scenario.
        
        Args:
            scenario_class: The scenario class to register
        """
        # Create an instance to get the name
        scenario = scenario_class()
        name = scenario.get_name()
        
        if name in self._scenarios:
            logger.warning(f"Scenario '{name}' already registered, overwriting")
        
        self._scenarios[name] = scenario_class
        logger.info(f"Registered scenario '{name}'")
    
    def get_scenario(self, name: str) -> Optional[ISimulationScenario]:
        """
        Get a simulation scenario by name.
        
        Args:
            name: The name of the scenario
            
        Returns:
            The scenario instance if found, None otherwise
        """
        scenario_class = self._scenarios.get(name)
        if scenario_class:
            return scenario_class()
        
        logger.warning(f"Scenario '{name}' not found in registry")
        return None
    
    def get_all_scenarios(self) -> Dict[str, ISimulationScenario]:
        """
        Get all registered scenarios.
        
        Returns:
            Dictionary mapping scenario names to scenario instances
        """
        return {name: scenario_class() for name, scenario_class in self._scenarios.items()}
    
    def get_scenario_names(self) -> List[str]:
        """
        Get the names of all registered scenarios.
        
        Returns:
            List of scenario names
        """
        return list(self._scenarios.keys())
    
    def get_scenario_info(self) -> List[Dict]:
        """
        Get information about all registered scenarios.
        
        Returns:
            List of dictionaries containing scenario name and description
        """
        result = []
        for name, scenario_class in self._scenarios.items():
            scenario = scenario_class()
            result.append({
                "name": scenario.get_name(),
                "description": scenario.get_description()
            })
        return result 