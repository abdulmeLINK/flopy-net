"""
Base Model for all machine learning models in the system.

This module provides the BaseModel abstract class that all model implementations
must inherit from to ensure a consistent interface.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

class BaseModel(ABC):
    """Abstract base class for all models in the system."""
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the base model.
        
        Args:
            model_name: Name of the model
            **kwargs: Additional model parameters
        """
        self.model_name = model_name
        self.model = None
        self.is_trained = False
        self.metrics = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    def build(self) -> None:
        """
        Build the model architecture.
        
        This method must be implemented by all concrete model classes to define
        the model architecture.
        """
        pass
    
    @abstractmethod
    def train(self, data: Any, **kwargs) -> Dict[str, Any]:
        """
        Train the model with provided data.
        
        Args:
            data: Training data
            **kwargs: Additional training parameters
            
        Returns:
            Dict with training metrics and results
        """
        pass
    
    @abstractmethod
    def evaluate(self, data: Any) -> Dict[str, Any]:
        """
        Evaluate the model performance on test data.
        
        Args:
            data: Evaluation data
            
        Returns:
            Dict with evaluation metrics
        """
        pass
    
    @abstractmethod
    def predict(self, data: Any) -> Any:
        """
        Make predictions with the model.
        
        Args:
            data: Input data for prediction
            
        Returns:
            Model predictions
        """
        pass
    
    def save(self, path: str) -> bool:
        """
        Save the model to disk.
        
        Args:
            path: Path to save the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._save_model(path)
            return True
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """
        Load the model from disk.
        
        Args:
            path: Path to load the model from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._load_model(path)
            return True
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    @abstractmethod
    def _save_model(self, path: str) -> None:
        """
        Implementation-specific model saving logic.
        
        Args:
            path: Path to save the model
        """
        pass
    
    @abstractmethod
    def _load_model(self, path: str) -> None:
        """
        Implementation-specific model loading logic.
        
        Args:
            path: Path to load the model from
        """
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get the model metrics.
        
        Returns:
            Dict with model metrics
        """
        return self.metrics
    
    def update_metrics(self, new_metrics: Dict[str, Any]) -> None:
        """
        Update the model metrics.
        
        Args:
            new_metrics: New metrics to add/update
        """
        self.metrics.update(new_metrics)
    
    def get_parameters(self) -> Any:
        """
        Get the model parameters.
        
        Returns:
            Model parameters in a format suitable for federated learning
        """
        raise NotImplementedError("This method must be implemented by subclasses")
    
    def set_parameters(self, parameters: Any) -> None:
        """
        Set the model parameters.
        
        Args:
            parameters: Model parameters to set
        """
        raise NotImplementedError("This method must be implemented by subclasses")
    
    def get_model_size(self) -> int:
        """
        Get the model size in bytes.
        
        Returns:
            Model size in bytes
        """
        raise NotImplementedError("This method must be implemented by subclasses")
    
    def get_model_summary(self) -> str:
        """
        Get a summary of the model architecture.
        
        Returns:
            String representation of the model summary
        """
        raise NotImplementedError("This method must be implemented by subclasses") 