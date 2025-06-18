"""
Basic model implementation for federated learning.

This module defines a model for basic federated learning scenarios.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional

from src.core.models.federated_model import FederatedModel

logger = logging.getLogger(__name__)

class BasicModel(FederatedModel):
    """
    Basic model for federated learning.
    Designed for MNIST classification task.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the basic model.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Set metadata for basic model
        self.metadata.update({
            "model_type": "basic",
            "dataset": "mnist",
            "description": "CNN model for MNIST image classification",
            "num_classes": 10,
            "input_shape": [28, 28, 1]
        })
        
        logger.info("Initialized BasicModel for MNIST dataset")
    
    def train(self, data, **kwargs):
        """
        Train the model on the provided data.
        
        Args:
            data: Training data
            **kwargs: Additional training parameters
            
        Returns:
            Dictionary with training metrics
        """
        logger.info("Training BasicModel")
        
        # Call parent training method
        return super().train(data, **kwargs)
    
    def evaluate(self, data, **kwargs):
        """
        Evaluate the model on the provided data.
        
        Args:
            data: Evaluation data
            **kwargs: Additional evaluation parameters
            
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info("Evaluating BasicModel")
        
        # Call parent evaluation method
        return super().evaluate(data, **kwargs)
    
    def predict(self, data, **kwargs):
        """
        Make predictions using the model.
        
        Args:
            data: Input data for prediction
            **kwargs: Additional prediction parameters
            
        Returns:
            Model predictions
        """
        logger.info("Making predictions with BasicModel")
        
        # Call parent prediction method
        return super().predict(data, **kwargs) 