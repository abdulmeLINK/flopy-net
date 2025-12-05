"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Minimal Model Interface for FL Client

This module provides a minimal model interface for simulating FL training
when a proper model handler cannot be created. It generates realistic
model parameters and simulates training/evaluation with realistic timing
and metric progressions.
"""

import logging
import time
import random
import numpy as np
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class MinimalModelInterface:
    """
    Minimal model interface for FL clients when proper model handler is unavailable.
    
    This class simulates realistic model training and evaluation with:
    - Realistic model parameter sizes based on architecture
    - S-curve accuracy progression over training rounds
    - Exponential loss decay
    - Realistic training/evaluation times with variability
    """
    
    # Model configurations for different architectures
    MODEL_CONFIGS = {
        "cnn": {
            "mnist": {"layers": [(32, 5, 5), (64, 5, 5), (128,), (10,)], "base_size_mb": 2.5},
            "cifar10": {"layers": [(64, 3, 3), (128, 3, 3), (256, 3, 3), (512,), (10,)], "base_size_mb": 15.2},
            "medical_mnist": {"layers": [(64, 3, 3), (128, 3, 3), (256, 3, 3), (512,), (6,)], "base_size_mb": 18.7}
        },
        "resnet": {
            "mnist": {"layers": [(64, 7, 7), (128, 3, 3), (256, 3, 3), (512, 3, 3), (10,)], "base_size_mb": 45.8},
            "cifar10": {"layers": [(64, 7, 7), (128, 3, 3), (256, 3, 3), (512, 3, 3), (10,)], "base_size_mb": 47.3},
            "medical_mnist": {"layers": [(64, 7, 7), (128, 3, 3), (256, 3, 3), (512, 3, 3), (6,)], "base_size_mb": 48.1}
        },
        "transformer": {
            "mnist": {"layers": [(512, 8), (1024, 8), (512,), (10,)], "base_size_mb": 125.4},
            "cifar10": {"layers": [(768, 12), (1536, 12), (768,), (10,)], "base_size_mb": 287.6},
            "medical_mnist": {"layers": [(768, 12), (1536, 12), (768,), (6,)], "base_size_mb": 291.2}
        }
    }
    
    def __init__(self, model_type: str, dataset: str):
        """
        Initialize the minimal model interface.
        
        Args:
            model_type: Type of model (cnn, resnet, transformer)
            dataset: Dataset name (mnist, cifar10, medical_mnist)
        """
        self.model_type = model_type
        self.dataset = dataset
        self.model_name = model_type  # For compatibility
        
        # Initialize realistic model parameters
        self.parameters = self._create_realistic_parameters()
        
        # Track training rounds to simulate improvement
        self.round_count = 0
        self.current_accuracy = 0.25  # Start with low accuracy
        self.current_loss = 0.95  # Start with high loss
        self.expected_total_rounds = 10  # Default based on policies
        
    def _create_realistic_parameters(self) -> List[np.ndarray]:
        """Create realistic model parameters with appropriate sizes."""
        # Get configuration for this model type and dataset
        config = self.MODEL_CONFIGS.get(self.model_type, self.MODEL_CONFIGS["cnn"])
        dataset_config = config.get(self.dataset, config.get("cifar10", config["mnist"]))
        
        # Create realistic parameter arrays
        params = []
        total_params = 0
        
        for i, layer_spec in enumerate(dataset_config["layers"]):
            if len(layer_spec) == 3:  # Convolutional layer (out_channels, kernel_h, kernel_w)
                out_channels, kernel_h, kernel_w = layer_spec
                # Assume input channels based on previous layer or dataset
                if i == 0:
                    in_channels = 1 if self.dataset == "mnist" else 3
                else:
                    in_channels = dataset_config["layers"][i-1][0] if len(dataset_config["layers"][i-1]) == 3 else 64
                
                # Weight tensor: (out_channels, in_channels, kernel_h, kernel_w)
                weight_shape = (out_channels, in_channels, kernel_h, kernel_w)
                bias_shape = (out_channels,)
                
                params.append(np.random.randn(*weight_shape).astype(np.float32) * 0.1)
                params.append(np.random.randn(*bias_shape).astype(np.float32) * 0.01)
                
                total_params += np.prod(weight_shape) + np.prod(bias_shape)
                
            elif len(layer_spec) == 2:  # Attention layer (hidden_dim, num_heads)
                hidden_dim, num_heads = layer_spec
                # Simplified transformer layer parameters
                # Query, Key, Value projections
                for _ in range(3):
                    weight_shape = (hidden_dim, hidden_dim)
                    params.append(np.random.randn(*weight_shape).astype(np.float32) * 0.1)
                    total_params += np.prod(weight_shape)
                
                # Output projection
                weight_shape = (hidden_dim, hidden_dim)
                params.append(np.random.randn(*weight_shape).astype(np.float32) * 0.1)
                total_params += np.prod(weight_shape)
                
            else:  # Fully connected layer (out_features,)
                out_features = layer_spec[0]
                # Determine input features from previous layer or flattened conv output
                if i == 0:
                    in_features = 784 if self.dataset == "mnist" else 3072  # Flattened input
                else:
                    prev_layer = dataset_config["layers"][i-1]
                    if len(prev_layer) == 3:  # Previous was conv
                        # Simplified: assume 7x7 feature maps after pooling
                        in_features = prev_layer[0] * 7 * 7
                    else:
                        in_features = prev_layer[0]
                
                weight_shape = (out_features, in_features)
                bias_shape = (out_features,)
                
                params.append(np.random.randn(*weight_shape).astype(np.float32) * 0.1)
                params.append(np.random.randn(*bias_shape).astype(np.float32) * 0.01)
                
                total_params += np.prod(weight_shape) + np.prod(bias_shape)
        
        # Calculate model size in MB (4 bytes per float32 parameter)
        model_size_mb = (total_params * 4) / (1024 * 1024)
        
        logger.info(f"Created realistic {self.model_type} model for {self.dataset}: {total_params:,} parameters, {model_size_mb:.2f} MB")
        
        return params
    
    def _get_complexity_factor(self) -> float:
        """Get complexity factor based on model type and dataset."""
        complexity_factor = 1.0
        if self.model_type == "resnet":
            complexity_factor = 1.5
        elif self.model_type == "transformer":
            complexity_factor = 2.0
        
        if self.dataset == "cifar10":
            complexity_factor *= 1.2
        elif self.dataset == "medical_mnist":
            complexity_factor *= 1.4
            
        return complexity_factor
        
    def train(self, parameters: List[np.ndarray], config: Dict[str, Any]) -> Tuple[List[np.ndarray], int, Dict[str, Any]]:
        """
        Simulate model training.
        
        Args:
            parameters: Model parameters from server
            config: Training configuration
            
        Returns:
            Tuple of (updated_parameters, num_examples, metrics)
        """
        # Extract policy parameters
        learning_rate = config.get("learning_rate", 0.01)
        batch_size = config.get("batch_size", 32)
        local_epochs = config.get("local_epochs", 1)
        momentum = config.get("momentum", 0.9)
        
        # Update expected total rounds if provided in config
        if "total_rounds" in config:
            self.expected_total_rounds = config.get("total_rounds")
        
        # Increment round counter
        self.round_count += 1
        
        logger.info(f"Client training round {self.round_count} starting with {self.model_type} model on {self.dataset}")
        
        # Calculate realistic training time
        base_training_time = 10.0
        random_additional_time = random.uniform(1.0, 10.0)
        complexity_factor = self._get_complexity_factor()
        
        # Factor in epochs and batch size
        epoch_factor = 0.8 + (local_epochs * 0.2)
        batch_factor = max(0.5, 1.0 - (batch_size - 32) * 0.01)
        
        total_training_time = (base_training_time + random_additional_time) * complexity_factor * epoch_factor * batch_factor
        
        # Add network/system variability
        variability = random.uniform(0.8, 1.2)
        total_training_time *= variability
        
        logger.info(f"Simulating realistic client training time: {total_training_time:.2f}s")
        
        # Actually sleep for the calculated time
        time.sleep(total_training_time)
        
        # Update parameters with noise
        updated_params = []
        for param in parameters:
            noise_scale = learning_rate * 0.5
            updated_params.append(param + np.random.normal(0, noise_scale, param.shape).astype(param.dtype))
        
        # Calculate progress
        progress_percent = min(1.0, self.round_count / self.expected_total_rounds)
        
        # S-curve accuracy progression
        base_accuracy = 0.1 + 0.8 * (1 / (1 + np.exp(-8 * (progress_percent - 0.5))))
        accuracy_noise = random.gauss(0, 0.02)
        target_accuracy = float(np.clip(base_accuracy + accuracy_noise, 0.1, 0.98))
        
        # Exponential loss decay
        base_loss = 2.3 * np.exp(-3 * progress_percent) + 0.1
        loss_noise = random.gauss(0, 0.05)
        target_loss = float(np.clip(base_loss + loss_noise, 0.05, 3.0))
        
        # Model-specific adjustments
        if self.model_type == "transformer":
            target_accuracy *= 1.05
            target_loss *= 0.95
        elif self.model_type == "resnet":
            target_accuracy *= 1.02
            target_loss *= 0.98
        
        # Dataset-specific adjustments
        if self.dataset == "mnist":
            target_accuracy = min(0.99, target_accuracy * 1.1)
            target_loss *= 0.8
        elif self.dataset == "medical_mnist":
            target_accuracy *= 0.9
            target_loss *= 1.2
        
        # Learning adjustments
        lr_factor = 1.0 + 0.5 * (learning_rate - 0.01) / 0.01
        epoch_factor = 1.0 + 0.2 * (local_epochs - 1)
        
        # Update metrics with smooth transition
        accuracy_change = (target_accuracy - self.current_accuracy) * 0.3 * lr_factor * epoch_factor
        accuracy_change += random.gauss(0, 0.02)
        self.current_accuracy = max(0.1, min(0.98, self.current_accuracy + accuracy_change))
        
        loss_change = (target_loss - self.current_loss) * 0.3 * lr_factor * epoch_factor
        loss_change += random.gauss(0, 0.03)
        self.current_loss = max(0.05, min(3.0, self.current_loss + loss_change))
        
        num_examples = max(1, batch_size * local_epochs)
        
        logger.info(f"Client training completed: round={self.round_count}/{self.expected_total_rounds}, "
                   f"accuracy={self.current_accuracy:.4f}, loss={self.current_loss:.4f}")
        
        return updated_params, num_examples, {
            "accuracy": float(self.current_accuracy),
            "loss": float(self.current_loss),
            "training_duration": total_training_time,
            "training_round": self.round_count,
            "model_type": self.model_type,
            "dataset": self.dataset
        }
        
    def evaluate(self, parameters: List[np.ndarray], config: Dict[str, Any]) -> Tuple[float, int, Dict[str, Any]]:
        """
        Simulate model evaluation.
        
        Args:
            parameters: Model parameters
            config: Evaluation configuration
            
        Returns:
            Tuple of (loss, num_examples, metrics)
        """
        test_size = config.get("test_size", 0.2)
        
        logger.info(f"Client evaluation starting for {self.model_type} model on {self.dataset}")
        
        # Realistic evaluation time
        base_eval_time = 1.0
        random_eval_time = random.uniform(0.2, 2.0)
        complexity_factor = 1.0
        if self.model_type == "resnet":
            complexity_factor = 1.3
        elif self.model_type == "transformer":
            complexity_factor = 1.8
        
        total_eval_time = (base_eval_time + random_eval_time) * complexity_factor
        time.sleep(total_eval_time)
        
        # Validation metrics (slightly worse than training)
        accuracy_gap = 0.05 + (self.current_accuracy * 0.1)
        eval_accuracy = max(0.0, self.current_accuracy * (1.0 - accuracy_gap * random.uniform(0.5, 1.0)))
        
        loss_gap = 0.05 + (self.current_accuracy * 0.15)
        eval_loss = self.current_loss * (1.0 + loss_gap * random.uniform(0.5, 1.0))
        
        num_examples = max(1, int(100 * test_size))
        
        logger.info(f"Client evaluation completed: accuracy={eval_accuracy:.4f}, loss={eval_loss:.4f}")
        
        return eval_loss, num_examples, {
            "accuracy": float(eval_accuracy),
            "loss": float(eval_loss),
            "evaluation_duration": total_eval_time,
            "training_round": self.round_count,
            "model_type": self.model_type,
            "dataset": self.dataset
        }
