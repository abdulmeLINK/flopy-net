"""
Federated Learning Model Repository Interface

This module defines the interface for a federated learning model repository.
"""
from typing import Any, Dict, List, Optional

from src.domain.entities.fl_model import FLModel


class IFLModelRepository:
    """
    Interface for a federated learning model repository.
    
    The repository is responsible for storing and retrieving models.
    """
    
    def save_model(self, model: FLModel, version: Optional[str] = None) -> bool:
        """
        Save a model to the repository.
        
        Args:
            model: Model to save
            version: Optional version identifier
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def load_model(self, name: str, version: Optional[str] = None) -> Optional[FLModel]:
        """
        Load a model from the repository.
        
        Args:
            name: Name of the model to load
            version: Optional version to load (defaults to latest)
            
        Returns:
            Loaded model, or None if not found
        """
        raise NotImplementedError("Method not implemented")
    
    def delete_model(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a model from the repository.
        
        Args:
            name: Name of the model to delete
            version: Optional version to delete (defaults to all versions)
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all models in the repository.
        
        Returns:
            List of model metadata dictionaries
        """
        raise NotImplementedError("Method not implemented")
    
    def list_versions(self, model_name: str) -> List[Dict[str, Any]]:
        """
        List all versions of a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of version metadata dictionaries
        """
        raise NotImplementedError("Method not implemented") 