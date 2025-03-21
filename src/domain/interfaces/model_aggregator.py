"""
Model Aggregator Interface

This module defines the interface for a federated learning model aggregator.
"""
from typing import Dict, List, Any, Optional


class IModelAggregator:
    """
    Interface for a federated learning model aggregator.
    
    The aggregator is responsible for combining model updates from clients.
    """
    
    def aggregate(self, global_model: Dict[str, Any], client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate client model updates into a new global model.
        
        Args:
            global_model: Current global model
            client_updates: List of client model updates
            
        Returns:
            Updated global model
        """
        raise NotImplementedError("Method not implemented")
    
    def preprocess_update(self, client_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess a client update before aggregation.
        
        Args:
            client_update: Client model update
            
        Returns:
            Preprocessed client update
        """
        raise NotImplementedError("Method not implemented")
    
    def validate_update(self, client_update: Dict[str, Any]) -> bool:
        """
        Validate a client update.
        
        Args:
            client_update: Client model update
            
        Returns:
            True if update is valid, False otherwise
        """
        raise NotImplementedError("Method not implemented") 