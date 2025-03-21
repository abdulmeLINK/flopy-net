"""
Federated Learning Strategy Interface

This module defines the interface for federated learning strategies
that can be used in the FL system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class IFLStrategy(ABC):
    """Interface defining the contract for federated learning strategies."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the strategy.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    @abstractmethod
    def aggregate(self, model_updates: List[Dict[str, Any]], weights: List[float] = None) -> Dict[str, Any]:
        """
        Aggregate model updates from multiple clients.
        
        Args:
            model_updates: List of model updates from clients
            weights: Optional weights for each client update
            
        Returns:
            Aggregated model update
        """
        pass
    
    @abstractmethod
    def client_selection(self, available_clients: List[str], client_properties: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Select clients to participate in a round.
        
        Args:
            available_clients: List of available client IDs
            client_properties: Dictionary mapping client IDs to their properties
            
        Returns:
            List of selected client IDs
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the strategy name.
        
        Returns:
            Strategy name
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get the strategy description.
        
        Returns:
            Strategy description
        """
        pass 