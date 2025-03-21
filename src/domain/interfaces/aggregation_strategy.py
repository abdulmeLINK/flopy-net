"""
Aggregation Strategy Interface

This module defines the interface for federated learning aggregation strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple


class IAggregationStrategy(ABC):
    """Interface defining the contract for federated learning aggregation strategies."""
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the strategy.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    @abstractmethod
    def aggregate(self, 
                  client_results: List[Tuple[List[Any], int, Dict[str, Any]]], 
                  current_weights: List[Any] = None) -> List[Any]:
        """
        Aggregate the client results to produce updated global parameters.
        
        Args:
            client_results: List of client results, each a tuple of (parameters, num_samples, metrics)
            current_weights: Current global model weights, if available
            
        Returns:
            Aggregated global parameters
        """
        pass
    
    @abstractmethod
    def select_clients(self, 
                       available_clients: List[str], 
                       client_properties: Dict[str, Dict[str, Any]],
                       num_clients: int) -> List[str]:
        """
        Select clients for the current round.
        
        Args:
            available_clients: List of available client IDs
            client_properties: Dictionary mapping client IDs to their properties
            num_clients: Number of clients to select
            
        Returns:
            List of selected client IDs
        """
        pass 