"""
Model handler for federated learning clients.

This module provides utilities for handling models in federated learning clients,
including model loading, saving, serialization, and parameter management.
"""

import os
import json
import pickle
from typing import Dict, Any, Optional, List, Tuple, Union, BinaryIO

import torch
import torch.nn as nn
import numpy as np

from src.core.common.logger import LoggerMixin


class ModelHandler(LoggerMixin):
    """Handler for federated learning models on clients."""
    
    def __init__(self, model_dir: str = "models"):
        """
        Initialize the model handler.
        
        Args:
            model_dir: Directory for storing models
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
    def save_model(self, model: nn.Module, filename: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a model to disk.
        
        Args:
            model: The model to save
            filename: Filename to save the model to
            metadata: Additional metadata to save with the model
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create the full path
            path = os.path.join(self.model_dir, filename)
            
            # Create metadata dict
            save_dict = {
                "model_state_dict": model.state_dict(),
                "model_class": model.__class__.__name__,
                "model_module": model.__class__.__module__,
                "metadata": metadata or {}
            }
            
            # Save the model
            torch.save(save_dict, path)
            self.logger.info(f"Model saved to {path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model: nn.Module, filename: str) -> Tuple[Optional[nn.Module], Optional[Dict[str, Any]]]:
        """
        Load a model from disk.
        
        Args:
            model: The model instance to load parameters into
            filename: Filename to load the model from
            
        Returns:
            Tuple of (loaded_model, metadata) or (None, None) on failure
        """
        try:
            # Create the full path
            path = os.path.join(self.model_dir, filename)
            
            # Load the model
            checkpoint = torch.load(path, map_location=torch.device('cpu'))
            model.load_state_dict(checkpoint["model_state_dict"])
            metadata = checkpoint.get("metadata", {})
            
            self.logger.info(f"Model loaded from {path}")
            return model, metadata
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return None, None
    
    def serialize_model(self, model: nn.Module) -> bytes:
        """
        Serialize a model to bytes.
        
        Args:
            model: The model to serialize
            
        Returns:
            bytes: Serialized model
        """
        try:
            # Only serialize the state dict for efficiency
            buffer = pickle.dumps(model.state_dict())
            self.logger.debug(f"Model serialized, size: {len(buffer)} bytes")
            return buffer
        except Exception as e:
            self.logger.error(f"Error serializing model: {e}")
            raise
    
    def deserialize_model(self, model: nn.Module, serialized_model: bytes) -> nn.Module:
        """
        Deserialize a model from bytes.
        
        Args:
            model: The model instance to load parameters into
            serialized_model: Serialized model bytes
            
        Returns:
            nn.Module: Model with loaded parameters
        """
        try:
            # Load the state dict
            state_dict = pickle.loads(serialized_model)
            model.load_state_dict(state_dict)
            self.logger.debug(f"Model deserialized, size: {len(serialized_model)} bytes")
            return model
        except Exception as e:
            self.logger.error(f"Error deserializing model: {e}")
            raise
    
    def get_model_size(self, model: nn.Module) -> int:
        """
        Get the size of a model in bytes.
        
        Args:
            model: The model to measure
            
        Returns:
            int: Size in bytes
        """
        try:
            # Serialize the model to get its size
            serialized = self.serialize_model(model)
            return len(serialized)
        except Exception as e:
            self.logger.error(f"Error getting model size: {e}")
            return -1
    
    def get_model_parameters(self, model: nn.Module) -> List[np.ndarray]:
        """
        Get the parameters of a model as numpy arrays.
        
        Args:
            model: The model to get parameters from
            
        Returns:
            List[np.ndarray]: Model parameters
        """
        return [param.detach().cpu().numpy() for param in model.parameters()]
    
    def set_model_parameters(self, model: nn.Module, parameters: List[np.ndarray]) -> nn.Module:
        """
        Set the parameters of a model from numpy arrays.
        
        Args:
            model: The model to set parameters for
            parameters: Model parameters as numpy arrays
            
        Returns:
            nn.Module: Model with updated parameters
        """
        with torch.no_grad():
            for param, array in zip(model.parameters(), parameters):
                param.copy_(torch.tensor(array))
        return model
    
    def get_model_gradients(self, model: nn.Module) -> List[np.ndarray]:
        """
        Get the gradients of a model as numpy arrays.
        
        Args:
            model: The model to get gradients from
            
        Returns:
            List[np.ndarray]: Model gradients
        """
        return [param.grad.detach().cpu().numpy() if param.grad is not None else np.zeros_like(param.detach().cpu().numpy())
                for param in model.parameters()]
    
    def set_model_gradients(self, model: nn.Module, gradients: List[np.ndarray]) -> nn.Module:
        """
        Set the gradients of a model from numpy arrays.
        
        Args:
            model: The model to set gradients for
            gradients: Model gradients as numpy arrays
            
        Returns:
            nn.Module: Model with updated gradients
        """
        with torch.no_grad():
            for param, grad_array in zip(model.parameters(), gradients):
                if param.grad is None:
                    param.grad = torch.tensor(grad_array).to(param.device)
                else:
                    param.grad.copy_(torch.tensor(grad_array).to(param.device))
        return model
    
    def evaluate(self, parameters: List[np.ndarray], config: Dict[str, Any]) -> Tuple[float, int, Dict[str, Any]]:
        """
        Evaluate a model with the given parameters.
        
        Args:
            parameters: Model parameters as numpy arrays
            config: Evaluation configuration
            
        Returns:
            Tuple of (loss, number of examples, metrics)
        """
        try:
            # Get model and dataset
            model = config.get("model")
            test_loader = config.get("test_loader")
            
            if model is None or test_loader is None:
                self.logger.error("Model or test_loader not provided in config")
                return 1.0, 1, {"accuracy": 0.0, "error": "Model or test_loader not provided"}
            
            # Set the model parameters
            self.set_model_parameters(model, parameters)
            
            # Set the device
            device = config.get("device", "cpu")
            model = model.to(device)
            model.eval()
            
            # Set up the loss function
            loss_fn = nn.CrossEntropyLoss()
            
            # Evaluation metrics
            total_loss = 0.0
            correct = 0
            total = 0
            
            # Disable gradients for evaluation
            with torch.no_grad():
                for data, target in test_loader:
                    # Move data to device
                    data, target = data.to(device), target.to(device)
                    
                    # Forward pass
                    output = model(data)
                    loss = loss_fn(output, target)
                    
                    # Update metrics
                    total_loss += loss.item() * target.size(0)
                    
                    # Calculate accuracy
                    _, predicted = torch.max(output.data, 1)
                    total += target.size(0)
                    correct += (predicted == target).sum().item()
            
            # Calculate final metrics
            avg_loss = total_loss / total if total > 0 else 0.0
            accuracy = correct / total if total > 0 else 0.0
            
            # Log evaluation results
            self.logger.info(f"Evaluation - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}")
            
            return avg_loss, total, {"accuracy": accuracy, "loss": avg_loss}
        except Exception as e:
            self.logger.error(f"Error evaluating model: {e}")
            return 1.0, 1, {"accuracy": 0.0, "error": str(e)} 