"""
Model Repository Interface

This module defines the interface for model repositories.
"""
from typing import Dict, Any, Optional, List
from src.domain.entities.fl_model import FLModel


class IModelRepository:
    """
    Interface for model repositories.
    
    This interface defines the contract for storing and retrieving
    federated learning models.
    """
    
    def save_model(self, model: FLModel, version: Optional[str] = None) -> bool:
        """
        Save a model to the repository.
        
        Args:
            model: The model to save
            version: Optional version string
            
        Returns:
            Success status
        """
        raise NotImplementedError
    
    def load_model(self, name: str, version: Optional[str] = None) -> Optional[FLModel]:
        """
        Load a model from the repository.
        
        Args:
            name: The name of the model to load
            version: Optional version string
            
        Returns:
            The loaded model, or None if not found
        """
        raise NotImplementedError
    
    def delete_model(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a model from the repository.
        
        Args:
            name: The name of the model to delete
            version: Optional version string
            
        Returns:
            Success status
        """
        raise NotImplementedError
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all models in the repository.
        
        Returns:
            List of model information dictionaries
        """
        raise NotImplementedError 