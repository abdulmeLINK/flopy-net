"""
Model Repository Interface

This module defines the interface for model repositories used throughout the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

# Import the FLModel class once it's defined
# from src.core.model.fl_model import FLModel


class IModelRepository(ABC):
    """
    Interface for model repositories used throughout the system.
    
    A model repository is responsible for storing, retrieving, and managing
    federated learning models and their versions.
    """
    
    @abstractmethod
    def save_model(self, model, version: Optional[str] = None) -> bool:
        """
        Save a model to the repository.
        
        Args:
            model: The model to save
            version: Optional version string
            
        Returns:
            True if saved successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def load_model(self, name: str, version: Optional[str] = None):
        """
        Load a model from the repository.
        
        Args:
            name: Name of the model to load
            version: Optional version string
            
        Returns:
            The loaded model if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete_model(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a model from the repository.
        
        Args:
            name: Name of the model to delete
            version: Optional version string
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all models in the repository.
        
        Returns:
            List of model metadata dictionaries
        """
        pass
    
    @abstractmethod
    def list_versions(self, model_name: str) -> List[Dict[str, Any]]:
        """
        List all versions of a model in the repository.
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of version metadata dictionaries
        """
        pass 