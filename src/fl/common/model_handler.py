#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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
Model handler for federated learning.

This module provides a handler for ML models in federated learning.
"""

import logging
import time
import os
import random
from typing import Dict, List, Tuple, Optional, Any
import importlib

import numpy as np

logger = logging.getLogger(__name__)

class ConfigurationError(ValueError): # Or RuntimeError
    """Custom exception for configuration-related errors."""
    pass

class ModelHandler:
    """Handler for ML models in federated learning."""
    
    def __init__(self, 
                 model_type: str, 
                 dataset: str,
                 model_definition_module: Optional[str] = None,
                 model_class_name: Optional[str] = None,
                 num_classes: int = 10): # Default num_classes, should be configured
        """
        Initialize the model handler.
        
        Args:
            model_type: Type of model to use (cnn, resnet, etc.)
            dataset: Dataset to use (mnist, cifar10, etc.)
            model_definition_module: The module path to the model class (e.g., "src.ml.models.cnn").
            model_class_name: The name of the model class (e.g., "Net").
            num_classes: Number of output classes for the model.
        """
        self.model_type = model_type
        self.dataset = dataset
        self.model_definition_module = model_definition_module
        self.model_class_name = model_class_name
        self.num_classes = num_classes
        
        # Critical: Model creation now happens here and can raise ConfigurationError
        self.model = self._create_model() 
        
        self.train_data = self._load_train_data()
        self.test_data = self._load_test_data()
        
        # Initialize training round counter for realistic progression
        self.training_round = 0
        
        logger.info(f"Initialized ModelHandler with {model_type} model for {dataset} dataset")
    
    def _create_model(self) -> Any: # Return type is actual model instance
        """
        Create a model by dynamically loading it.
        
        Raises:
            ConfigurationError: If the model cannot be loaded due to missing
                                configuration or errors during loading.
        
        Returns:
            The instantiated model with realistic size based on model type.
        """
        model_load_path = "N/A"
        if self.model_definition_module and self.model_class_name:
            model_load_path = f"{self.model_definition_module}.{self.model_class_name}"
            logger.info(f"Attempting to dynamically load model: {model_load_path}")
            try:
                module = importlib.import_module(self.model_definition_module)
                model_class = getattr(module, self.model_class_name)
                
                # Attempt to instantiate with num_classes, then without, common for PyTorch models
                try:
                    model_instance = model_class(num_classes=self.num_classes)
                    logger.info(f"Instantiated model {self.model_class_name} with num_classes={self.num_classes}.")
                except TypeError:
                    logger.warning(
                        f"Could not instantiate {self.model_class_name} with num_classes. "
                        f"Attempting instantiation without num_classes."
                    )
                    try:
                        model_instance = model_class()
                        logger.info(f"Instantiated model {self.model_class_name} without num_classes.")
                    except Exception as e_init:
                        err_msg = (
                            f"Error instantiating model class {model_load_path} "
                            f"(tried with and without num_classes): {e_init}"
                        )
                        logger.error(err_msg)
                        raise ConfigurationError(err_msg) from e_init
                
                logger.info(f"Successfully loaded and instantiated model {model_load_path}")
                return model_instance
            except ImportError as e_imp:
                err_msg = f"Could not import module '{self.model_definition_module}': {e_imp}"
                logger.error(err_msg)
                raise ConfigurationError(err_msg) from e_imp
            except AttributeError as e_attr:
                err_msg = f"Could not find class '{self.model_class_name}' in module '{self.model_definition_module}': {e_attr}"
                logger.error(err_msg)
                raise ConfigurationError(err_msg) from e_attr
            except Exception as e_gen: # Catch any other unexpected errors during loading
                err_msg = f"An unexpected error occurred while loading model {model_load_path}: {e_gen}"
                logger.error(err_msg, exc_info=True) # Log traceback for unexpected errors
                raise ConfigurationError(err_msg) from e_gen
        else:
            # Create realistic simulated model with appropriate size based on model type and dataset
            return self._create_realistic_simulated_model()
    
    def _create_realistic_simulated_model(self) -> Dict[str, Any]:
        """Create a simulated model with realistic parameter sizes."""
        logger.info(f"Creating realistic simulated {self.model_type} model for {self.dataset}")
        
        # Define realistic model architectures and sizes
        model_configs = {
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
        
        # Get configuration for this model type and dataset
        config = model_configs.get(self.model_type, model_configs["cnn"])
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
        
        # Calculate actual model size in MB (4 bytes per float32 parameter)
        actual_size_mb = (total_params * 4) / (1024 * 1024)
        
        # Add some variation to match the target size
        target_size_mb = dataset_config["base_size_mb"]
        size_ratio = target_size_mb / actual_size_mb if actual_size_mb > 0 else 1.0
        
        # Scale parameters to achieve target size (by adding more parameters if needed)
        if size_ratio > 1.1:  # If we need significantly more parameters
            # Add extra dense layers to reach target size
            extra_params_needed = int((target_size_mb - actual_size_mb) * 1024 * 1024 / 4)
            if extra_params_needed > 0:
                # Add a large dense layer
                extra_layer_size = int(np.sqrt(extra_params_needed))
                if extra_layer_size > 0:
                    extra_weight = np.random.randn(extra_layer_size, extra_layer_size).astype(np.float32) * 0.01
                    params.append(extra_weight)
                    total_params += extra_weight.size
        
        final_size_mb = (total_params * 4) / (1024 * 1024)
        
        logger.info(f"Created {self.model_type} model for {self.dataset}: {total_params:,} parameters, {final_size_mb:.2f} MB")
        
        return {
            "params": params,
            "total_parameters": total_params,
            "size_mb": final_size_mb,
            "architecture": dataset_config["layers"],
            "model_type": self.model_type,
            "dataset": self.dataset
        }

    def _load_train_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load training data.
        
        Returns:
            Tuple of (x, y) training data
        """
        # Simulated data for GNS3 deployment testing
        logger.info(f"Loading simulated {self.dataset} training data")
        
        # Return simulated data with the right shape for the dataset
        if self.dataset == "mnist":
            return np.random.rand(1000, 28, 28, 1), np.random.randint(0, 10, size=1000)
        elif self.dataset == "cifar10":
            return np.random.rand(1000, 32, 32, 3), np.random.randint(0, 10, size=1000)
        elif self.dataset == "medical_mnist":
            return np.random.rand(1000, 64, 64, 3), np.random.randint(0, 6, size=1000)
        else:
            # Default dataset shape
            return np.random.rand(1000, 32, 32, 3), np.random.randint(0, 10, size=1000)
    
    def _load_test_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load test data.
        
        Returns:
            Tuple of (x, y) test data
        """
        # Simulated data for GNS3 deployment testing
        logger.info(f"Loading simulated {self.dataset} test data")
        
        # Return simulated data with the right shape for the dataset
        if self.dataset == "mnist":
            return np.random.rand(200, 28, 28, 1), np.random.randint(0, 10, size=200)
        elif self.dataset == "cifar10":
            return np.random.rand(200, 32, 32, 3), np.random.randint(0, 10, size=200)
        elif self.dataset == "medical_mnist":
            return np.random.rand(200, 64, 64, 3), np.random.randint(0, 6, size=200)
        else:
            # Default dataset shape
            return np.random.rand(200, 32, 32, 3), np.random.randint(0, 10, size=200)
    
    def get_weights(self) -> List[np.ndarray]:
        """
        Get model weights.
        
        Returns:
            List of weight arrays
        """
        if isinstance(self.model, dict):
            return self.model["params"]
        else:
            # For real model instances like SimpleCNN, get their weights
            if hasattr(self.model, 'get_weights'):
                return self.model.get_weights()
            elif hasattr(self.model, 'parameters'):
                return self.model.parameters
            else:
                # Fallback: return empty list or create some dummy weights
                logger.warning(f"Model {type(self.model)} doesn't have get_weights method, returning empty list")
                return []
    
    def set_weights(self, weights: List[np.ndarray]) -> None:
        """
        Set model weights.
        
        Args:
            weights: List of weight arrays
        """
        if isinstance(self.model, dict):
            self.model["params"] = weights
        else:
            # For real model instances like SimpleCNN, set their weights
            if hasattr(self.model, 'set_weights'):
                self.model.set_weights(weights)
            elif hasattr(self.model, 'parameters'):
                self.model.parameters = weights
            else:
                logger.warning(f"Model {type(self.model)} doesn't have set_weights method, cannot set weights")
    
    def train(self, parameters=None, config=None) -> Tuple[List[np.ndarray], int, Dict[str, float]]:
        """
        Train the model with realistic timing (10s + random 1-10s).
        
        Args:
            parameters: Model parameters from the server (if None, use current model parameters)
            config: Training configuration (epochs, batch_size, etc.)
            
        Returns:
            Tuple of (updated_parameters, num_examples, metrics)
        """
        # Handle different parameter formats
        if config is None:
            config = {}
        
        # Extract config parameters with defaults
        epochs = config.get("local_epochs", config.get("epochs", 1))
        batch_size = config.get("batch_size", 32)
        learning_rate = config.get("learning_rate", 0.01)
        
        # Use loaded training data (simulated)
        x, y = self.train_data
        
        # Increment training round for realistic progression
        self.training_round += 1
        
        logger.info(f"Training round {self.training_round} for {epochs} epochs with batch size {batch_size}")
        
        # Calculate realistic training time: 10s base + random 1-10s
        base_training_time = 10.0  # Base 10 seconds
        random_additional_time = random.uniform(1.0, 10.0)  # Random 1-10 seconds
        
        # Add complexity factors based on model and dataset
        complexity_factor = 1.0
        if self.model_type == "resnet":
            complexity_factor = 1.5
        elif self.model_type == "transformer":
            complexity_factor = 2.0
        
        if self.dataset == "cifar10":
            complexity_factor *= 1.2
        elif self.dataset == "medical_mnist":
            complexity_factor *= 1.4
        
        # Factor in epochs and batch size
        epoch_factor = 0.8 + (epochs * 0.2)  # More epochs = slightly longer per epoch
        batch_factor = max(0.5, 1.0 - (batch_size - 32) * 0.01)  # Larger batches = slightly more efficient
        
        total_training_time = (base_training_time + random_additional_time) * complexity_factor * epoch_factor * batch_factor
        
        # Add some network/system variability (±20%)
        variability = random.uniform(0.8, 1.2)
        total_training_time *= variability
        
        logger.info(f"Simulating realistic training time: {total_training_time:.2f}s (base: {base_training_time}s, random: {random_additional_time:.1f}s, complexity: {complexity_factor:.1f}x)")
        
        # Actually sleep for the calculated time to simulate real training
        time.sleep(total_training_time)
        
        # Update model parameters if provided
        if parameters is not None:
            # Add some noise to the parameters based on learning rate to simulate training updates
            updated_params = []
            for param in parameters:
                # More aggressive updates with higher learning rates
                noise_scale = learning_rate * 0.5
                updated_params.append(param + np.random.normal(0, noise_scale, param.shape).astype(param.dtype))
        else:
            # Use current model parameters with some updates
            updated_params = self.get_weights()
            for i in range(len(updated_params)):
                noise_scale = learning_rate * 0.5
                updated_params[i] = updated_params[i] + np.random.normal(0, noise_scale, updated_params[i].shape).astype(updated_params[i].dtype)
        
        # More realistic metrics progression based on training round
        progress = min(1.0, self.training_round / 10.0)  # Assume 10 rounds for convergence
        
        # Realistic accuracy progression (S-curve)
        base_accuracy = 0.1 + 0.8 * (1 / (1 + np.exp(-8 * (progress - 0.5))))
        accuracy_noise = random.gauss(0, 0.02)  # Small random variation
        accuracy = float(np.clip(base_accuracy + accuracy_noise, 0.1, 0.98))
        
        # Realistic loss progression (exponential decay)
        base_loss = 2.3 * np.exp(-3 * progress) + 0.1  # Starts high, decreases exponentially
        loss_noise = random.gauss(0, 0.05)
        loss = float(np.clip(base_loss + loss_noise, 0.05, 3.0))
        
        # Add model-specific performance characteristics
        if self.model_type == "transformer":
            accuracy *= 1.05  # Transformers typically perform slightly better
            loss *= 0.95
        elif self.model_type == "resnet":
            accuracy *= 1.02  # ResNets are also good
            loss *= 0.98
        
        # Dataset-specific adjustments
        if self.dataset == "mnist":
            accuracy = min(0.99, accuracy * 1.1)  # MNIST is easier
            loss *= 0.8
        elif self.dataset == "medical_mnist":
            accuracy *= 0.9  # Medical data is harder
            loss *= 1.2
        
        # Calculate number of examples based on batch size and epochs
        num_examples = max(1, batch_size * epochs)
        
        metrics = {
            "loss": loss,
            "accuracy": accuracy,
            "training_duration": total_training_time,
            "training_round": self.training_round,
            "epochs": epochs,
            "batch_size": batch_size,
            "model_size_mb": self.model.get("size_mb", 0.0) if isinstance(self.model, dict) else 0.0,
            "total_parameters": self.model.get("total_parameters", 0) if isinstance(self.model, dict) else 0
        }
        
        logger.info(f"Training completed: accuracy={accuracy:.4f}, loss={loss:.4f}, duration={total_training_time:.2f}s")
        
        return updated_params, num_examples, metrics

    def evaluate(self, parameters=None, config=None) -> Tuple[float, int, Dict[str, float]]:
        """
        Evaluate the model with realistic timing.
        
        Args:
            parameters: Model parameters (if None, use current model parameters)
            config: Evaluation configuration (test_size, etc.)
            
        Returns:
            Tuple of (loss, num_examples, metrics)
        """
        # Handle different parameter formats
        if config is None:
            config = {}
        
        # Extract config parameters with defaults
        test_size = config.get("test_size", 0.2)
        
        # Use loaded test data (simulated)
        x, y = self.test_data
        
        logger.info(f"Evaluating on {len(x)} samples")
        
        # Realistic evaluation time (much faster than training)
        base_eval_time = 1.0  # Base 1 second
        random_eval_time = random.uniform(0.2, 2.0)  # Random 0.2-2 seconds
        
        # Model complexity factor
        complexity_factor = 1.0
        if self.model_type == "resnet":
            complexity_factor = 1.3
        elif self.model_type == "transformer":
            complexity_factor = 1.8
        
        total_eval_time = (base_eval_time + random_eval_time) * complexity_factor
        
        # Actually sleep for evaluation time
        time.sleep(total_eval_time)
        
        # Evaluation metrics are typically slightly worse than training
        progress = min(1.0, self.training_round / 10.0)
        
        # Base performance (slightly worse than training)
        base_accuracy = 0.08 + 0.75 * (1 / (1 + np.exp(-8 * (progress - 0.5))))
        accuracy_noise = random.gauss(0, 0.03)  # Slightly more noise in evaluation
        accuracy = float(np.clip(base_accuracy + accuracy_noise, 0.05, 0.95))
        
        base_loss = 2.5 * np.exp(-2.8 * progress) + 0.15  # Slightly higher than training loss
        loss_noise = random.gauss(0, 0.08)
        loss = float(np.clip(base_loss + loss_noise, 0.1, 3.5))
        
        # Model-specific adjustments
        if self.model_type == "transformer":
            accuracy *= 1.03
            loss *= 0.97
        elif self.model_type == "resnet":
            accuracy *= 1.01
            loss *= 0.99
        
        # Dataset-specific adjustments
        if self.dataset == "mnist":
            accuracy = min(0.98, accuracy * 1.08)
            loss *= 0.85
        elif self.dataset == "medical_mnist":
            accuracy *= 0.88
            loss *= 1.25
        
        # Use an approximation of test set size based on test_size
        num_examples = max(1, int(100 * test_size))  # Simulate test_size proportion of 100 examples
        
        metrics = {
            "accuracy": accuracy,
            "val_accuracy": accuracy,
            "loss": loss,
            "val_loss": loss,
            "num_examples": num_examples,
            "evaluation_duration": total_eval_time,
            "training_round": self.training_round
        }
        
        logger.info(f"Evaluation completed: accuracy={accuracy:.4f}, loss={loss:.4f}, duration={total_eval_time:.2f}s")
        
        return loss, num_examples, metrics

    def predict(self, x: np.ndarray) -> np.ndarray:
        """
        Make predictions with the model.
        
        Args:
            x: Input data
            
        Returns:
            Predictions
        """
        logger.info(f"Predicting on {len(x)} samples")
        
        # Realistic prediction time
        prediction_time = 0.1 + random.uniform(0.05, 0.3)
        time.sleep(prediction_time)
        
        # Return simulated predictions
        if self.dataset == "mnist" or self.dataset == "cifar10":
            return np.random.rand(len(x), 10)  # 10 classes
        elif self.dataset == "medical_mnist":
            return np.random.rand(len(x), 6)  # 6 classes
        else:
            return np.random.rand(len(x), 10)  # Default 10 classes

    def save(self, filepath: str) -> bool:
        """
        Save the model to a file.
        
        Args:
            filepath: Path to save the model
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Realistic saving time based on model size
            model_size_mb = self.model.get("size_mb", 1.0) if isinstance(self.model, dict) else 1.0
            save_time = 0.1 + (model_size_mb * 0.05)  # ~50ms per MB
            time.sleep(save_time)
            
            # Save model parameters to a numpy file
            if isinstance(self.model, dict):
                np.save(filepath, self.model["params"])
            else:
                # For real model instances, save their weights
                np.save(filepath, self.get_weights())
            
            logger.info(f"Model saved to {filepath} ({model_size_mb:.2f} MB in {save_time:.2f}s)")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load(self, filepath: str) -> bool:
        """
        Load the model from a file.
        
        Args:
            filepath: Path to load the model from
            
        Returns:
            bool: Success or failure
        """
        try:
            # Realistic loading time
            load_time = 0.1 + random.uniform(0.05, 0.2)
            time.sleep(load_time)
            
            # Load model parameters from a numpy file
            self.model["params"] = np.load(filepath, allow_pickle=True)
            
            logger.info(f"Model loaded from {filepath} in {load_time:.2f}s")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False 