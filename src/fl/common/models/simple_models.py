"""
Simple neural network models for federated learning demonstrations.
These are basic implementations to support FL training without complex dependencies.
"""

import numpy as np
from typing import Tuple, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SimpleCNN:
    """
    A simple CNN implementation for MNIST and CIFAR-10 datasets.
    This is a basic implementation for FL demonstration purposes.
    """
    
    def __init__(self, num_classes: int = 10, input_shape: Tuple[int, int, int] = (28, 28, 1)):
        """
        Initialize the Simple CNN.
        
        Args:
            num_classes: Number of output classes
            input_shape: Shape of input data (height, width, channels)
        """
        self.num_classes = num_classes
        self.input_shape = input_shape
        self.parameters = self._initialize_parameters()
        
    def _initialize_parameters(self) -> List[np.ndarray]:
        """Initialize model parameters with random weights."""
        params = []
        
        # Simple architecture: Conv -> Conv -> FC -> FC
        # Conv1: 32 filters, 5x5 kernel
        in_channels = self.input_shape[2]
        params.append(np.random.randn(32, in_channels, 5, 5).astype(np.float32) * 0.1)  # weights
        params.append(np.random.randn(32).astype(np.float32) * 0.01)  # bias
        
        # Conv2: 64 filters, 5x5 kernel
        params.append(np.random.randn(64, 32, 5, 5).astype(np.float32) * 0.1)  # weights
        params.append(np.random.randn(64).astype(np.float32) * 0.01)  # bias
        
        # Estimate flattened size after convolutions and pooling
        # Assuming 2x2 max pooling after each conv layer
        h_after_conv = self.input_shape[0] // 4  # Two pooling layers
        w_after_conv = self.input_shape[1] // 4
        flattened_size = 64 * h_after_conv * w_after_conv
        
        # FC1: Hidden layer with 128 units
        params.append(np.random.randn(128, flattened_size).astype(np.float32) * 0.1)  # weights
        params.append(np.random.randn(128).astype(np.float32) * 0.01)  # bias
        
        # FC2: Output layer
        params.append(np.random.randn(self.num_classes, 128).astype(np.float32) * 0.1)  # weights
        params.append(np.random.randn(self.num_classes).astype(np.float32) * 0.01)  # bias
        
        return params
    
    def get_weights(self) -> List[np.ndarray]:
        """Get model weights."""
        return self.parameters
    
    def set_weights(self, weights: List[np.ndarray]) -> None:
        """Set model weights."""
        self.parameters = weights
    
    def get_model_size_mb(self) -> float:
        """
        Calculate the model size in megabytes.
        
        Returns:
            Model size in MB
        """
        total_params = 0
        for param in self.parameters:
            total_params += param.size
        
        # Each parameter is float32 (4 bytes)
        size_bytes = total_params * 4
        size_mb = size_bytes / (1024 * 1024)
        
        return round(size_mb, 6)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed model information.
        
        Returns:
            Dictionary with model statistics
        """
        total_params = sum(param.size for param in self.parameters)
        size_mb = self.get_model_size_mb()
        
        return {
            'model_type': 'SimpleCNN',
            'total_parameters': total_params,
            'size_mb': size_mb,
            'input_shape': self.input_shape,
            'num_classes': self.num_classes,
            'architecture': f'Conv({self.input_shape[2]}->32)->Conv(32->64)->FC({64 * (self.input_shape[0]//4) * (self.input_shape[1]//4)}->128)->FC(128->{self.num_classes})'
        }
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Forward pass (simplified simulation).
        
        Args:
            x: Input data
            
        Returns:
            Output predictions
        """
        # This is a simplified simulation - in practice would implement actual convolution
        batch_size = x.shape[0]
        return np.random.randn(batch_size, self.num_classes).astype(np.float32)
    
    def train_step(self, x: np.ndarray, y: np.ndarray, learning_rate: float = 0.01) -> Dict[str, float]:
        """
        Perform one training step (simplified simulation).
        
        Args:
            x: Input data
            y: Target labels
            learning_rate: Learning rate for updates
            
        Returns:
            Training metrics
        """
        # Simulate training by adding noise to parameters
        for i, param in enumerate(self.parameters):
            noise = np.random.normal(0, learning_rate * 0.1, param.shape).astype(param.dtype)
            self.parameters[i] = param + noise
        
        # Return simulated metrics including model size
        return {
            'loss': np.random.uniform(0.1, 2.0),
            'accuracy': np.random.uniform(0.1, 0.95),
            'model_size_mb': self.get_model_size_mb()
        }


class SimpleMLP:
    """
    A simple Multi-Layer Perceptron implementation.
    This is a basic implementation for FL demonstration purposes.
    """
    
    def __init__(self, num_classes: int = 10, input_size: int = 784, hidden_sizes: List[int] = None):
        """
        Initialize the Simple MLP.
        
        Args:
            num_classes: Number of output classes
            input_size: Size of input features
            hidden_sizes: List of hidden layer sizes
        """
        self.num_classes = num_classes
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes or [128, 64]
        self.parameters = self._initialize_parameters()
        
    def _initialize_parameters(self) -> List[np.ndarray]:
        """Initialize model parameters with random weights."""
        params = []
        
        # Build layers: input -> hidden1 -> hidden2 -> ... -> output
        layer_sizes = [self.input_size] + self.hidden_sizes + [self.num_classes]
        
        for i in range(len(layer_sizes) - 1):
            in_size = layer_sizes[i]
            out_size = layer_sizes[i + 1]
            
            # Xavier initialization
            std = np.sqrt(2.0 / (in_size + out_size))
            weights = np.random.randn(out_size, in_size).astype(np.float32) * std
            bias = np.zeros(out_size).astype(np.float32)
            
            params.append(weights)
            params.append(bias)
        
        return params
    
    def get_weights(self) -> List[np.ndarray]:
        """Get model weights."""
        return self.parameters
    
    def set_weights(self, weights: List[np.ndarray]) -> None:
        """Set model weights."""
        self.parameters = weights
    
    def get_model_size_mb(self) -> float:
        """
        Calculate the model size in megabytes.
        
        Returns:
            Model size in MB
        """
        total_params = 0
        for param in self.parameters:
            total_params += param.size
        
        # Each parameter is float32 (4 bytes)
        size_bytes = total_params * 4
        size_mb = size_bytes / (1024 * 1024)
        
        return round(size_mb, 6)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed model information.
        
        Returns:
            Dictionary with model statistics
        """
        total_params = sum(param.size for param in self.parameters)
        size_mb = self.get_model_size_mb()
        
        layer_sizes = [self.input_size] + self.hidden_sizes + [self.num_classes]
        architecture = ' -> '.join([f'FC({layer_sizes[i]}->{layer_sizes[i+1]})' 
                                  for i in range(len(layer_sizes)-1)])
        
        return {
            'model_type': 'SimpleMLP',
            'total_parameters': total_params,
            'size_mb': size_mb,
            'input_size': self.input_size,
            'hidden_sizes': self.hidden_sizes,
            'num_classes': self.num_classes,
            'architecture': architecture
        }
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Forward pass (simplified simulation).
        
        Args:
            x: Input data
            
        Returns:
            Output predictions
        """
        # This is a simplified simulation - in practice would implement actual forward pass
        batch_size = x.shape[0]
        return np.random.randn(batch_size, self.num_classes).astype(np.float32)
    
    def train_step(self, x: np.ndarray, y: np.ndarray, learning_rate: float = 0.01) -> Dict[str, float]:
        """
        Perform one training step (simplified simulation).
        
        Args:
            x: Input data
            y: Target labels
            learning_rate: Learning rate for updates
            
        Returns:
            Training metrics
        """
        # Simulate training by adding noise to parameters
        for i, param in enumerate(self.parameters):
            noise = np.random.normal(0, learning_rate * 0.1, param.shape).astype(param.dtype)
            self.parameters[i] = param + noise
        
        # Return simulated metrics including model size
        return {
            'loss': np.random.uniform(0.1, 2.0),
            'accuracy': np.random.uniform(0.1, 0.95),
            'model_size_mb': self.get_model_size_mb()
        }


# Utility function to get model by name
def get_model_class(model_name: str):
    """
    Get model class by name.
    
    Args:
        model_name: Name of the model ('cnn' or 'mlp')
        
    Returns:
        Model class
    """
    model_map = {
        'cnn': SimpleCNN,
        'mlp': SimpleMLP,
        'simple_cnn': SimpleCNN,
        'simple_mlp': SimpleMLP
    }
    
    return model_map.get(model_name.lower(), SimpleCNN)  # Default to CNN 


# Utility function to calculate model size for any model
def calculate_model_size_mb(model_instance) -> float:
    """
    Calculate model size in MB for any model that has get_model_size_mb method.
    
    Args:
        model_instance: Model instance
        
    Returns:
        Model size in MB, or 0.0 if not calculable
    """
    try:
        if hasattr(model_instance, 'get_model_size_mb'):
            return model_instance.get_model_size_mb()
        elif hasattr(model_instance, 'parameters'):
            # Fallback calculation for models with parameters attribute
            total_params = sum(param.size for param in model_instance.parameters)
            size_bytes = total_params * 4  # Assume float32
            return round(size_bytes / (1024 * 1024), 6)
        else:
            return 0.0
    except Exception as e:
        logger.warning(f"Could not calculate model size: {e}")
        return 0.0 