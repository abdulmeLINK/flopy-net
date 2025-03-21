"""
Federated Learning Client Interface

This module defines the interface for a federated learning client.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple


class IFLClient(ABC):
    """Interface defining the contract for federated learning clients."""
    
    @abstractmethod
    def get_parameters(self, config: Dict[str, Any]) -> List[Any]:
        """
        Get the current model parameters.
        
        Args:
            config: A dictionary containing configuration parameters
            
        Returns:
            A list of model parameters
        """
        pass
    
    @abstractmethod
    def set_parameters(self, parameters: List[Any]) -> None:
        """
        Set the model parameters.
        
        Args:
            parameters: A list of model parameters
        """
        pass
    
    @abstractmethod
    def fit(self, parameters: List[Any], config: Dict[str, Any]) -> Tuple[List[Any], int, Dict[str, Any]]:
        """
        Train the model on the client's local data.
        
        Args:
            parameters: Initial model parameters
            config: Training configuration
            
        Returns:
            Tuple containing (updated parameters, number of samples, metrics)
        """
        pass
    
    @abstractmethod
    def evaluate(self, parameters: List[Any], config: Dict[str, Any]) -> Tuple[float, int, Dict[str, Any]]:
        """
        Evaluate the model on the client's local data.
        
        Args:
            parameters: Model parameters to evaluate
            config: Evaluation configuration
            
        Returns:
            Tuple containing (loss, number of samples, metrics)
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the client.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the client."""
        pass 