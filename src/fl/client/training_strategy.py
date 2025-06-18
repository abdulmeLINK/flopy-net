"""
Training strategies for federated learning clients.

This module defines the interface and implementations for client training strategies
that can be used in the federated learning process.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from src.core.common.logger import LoggerMixin


class TrainingStrategy(ABC, LoggerMixin):
    """Base class for client training strategies."""
    
    def __init__(self, name: str = "base_strategy"):
        """
        Initialize the training strategy.
        
        Args:
            name: Name of the strategy
        """
        self.name = name
        
    @abstractmethod
    def train(self, model: nn.Module, 
              train_loader: DataLoader, 
              epochs: int,
              device: str = "cpu",
              **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Train the model using this strategy.
        
        Args:
            model: Model to train
            train_loader: DataLoader for training data
            epochs: Number of training epochs
            device: Device to use for training ("cpu" or "cuda")
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            Tuple of (trained_model, metrics)
        """
        pass


class FedAvgStrategy(TrainingStrategy):
    """
    Implementation of the FedAvg training strategy.
    
    This is the standard training strategy from the FedAvg paper
    (https://arxiv.org/abs/1602.05629) that performs SGD on the client data.
    """
    
    def __init__(self, lr: float = 0.01, name: str = "fedavg"):
        """
        Initialize the FedAvg strategy.
        
        Args:
            lr: Learning rate
            name: Name of the strategy
        """
        super().__init__(name=name)
        self.lr = lr
        
    def train(self, model: nn.Module, 
              train_loader: DataLoader, 
              epochs: int = 1,
              device: str = "cpu",
              **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Train the model using the FedAvg strategy.
        
        Args:
            model: Model to train
            train_loader: DataLoader for training data
            epochs: Number of training epochs
            device: Device to use for training ("cpu" or "cuda")
            **kwargs: Additional strategy-specific parameters
                - lr: Learning rate (overrides the one set in the constructor)
                - momentum: Momentum for SGD
                - weight_decay: Weight decay for regularization
                
        Returns:
            Tuple of (trained_model, metrics)
        """
        # Get strategy parameters
        lr = kwargs.get("lr", self.lr)
        momentum = kwargs.get("momentum", 0.0)
        weight_decay = kwargs.get("weight_decay", 0.0)
        
        # Set up the optimizer
        optimizer = optim.SGD(model.parameters(), 
                              lr=lr, 
                              momentum=momentum,
                              weight_decay=weight_decay)
        
        # Set up the loss function
        loss_fn = nn.CrossEntropyLoss()
        
        # Move model to device
        model = model.to(device)
        model.train()
        
        # Initialize metrics
        metrics = {
            "train_loss": [],
            "num_examples": len(train_loader.dataset),
            "num_batches": len(train_loader)
        }
        
        # Training loop
        for epoch in range(epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                # Move data to device
                data, target = data.to(device), target.to(device)
                
                # Zero the gradients
                optimizer.zero_grad()
                
                # Forward pass
                output = model(data)
                loss = loss_fn(output, target)
                
                # Backward pass and optimize
                loss.backward()
                optimizer.step()
                
                # Update metrics
                epoch_loss += loss.item()
                
                # Calculate accuracy
                _, predicted = torch.max(output.data, 1)
                total += target.size(0)
                correct += (predicted == target).sum().item()
                
                # Log batch progress
                if batch_idx % 10 == 0:
                    self.logger.debug(f"Epoch: {epoch+1}/{epochs}, Batch: {batch_idx+1}/{len(train_loader)}, "
                                     f"Loss: {loss.item():.4f}")
            
            # Calculate epoch metrics
            avg_loss = epoch_loss / len(train_loader)
            accuracy = 100.0 * correct / total
            
            # Log epoch metrics
            self.logger.info(f"Epoch {epoch+1}/{epochs} - "
                            f"Loss: {avg_loss:.4f}, "
                            f"Accuracy: {accuracy:.2f}%")
            
            # Add to metrics
            metrics["train_loss"].append(avg_loss)
            metrics[f"epoch_{epoch+1}_accuracy"] = accuracy
        
        # Calculate final metrics
        metrics["final_loss"] = metrics["train_loss"][-1] if metrics["train_loss"] else 0.0
        metrics["final_accuracy"] = metrics.get(f"epoch_{epochs}_accuracy", 0.0)
        
        return model, metrics


class FedProxStrategy(FedAvgStrategy):
    """
    Implementation of the FedProx training strategy.
    
    This strategy extends FedAvg by adding a proximal term to the loss
    function that keeps the local model close to the global model.
    (https://arxiv.org/abs/1812.06127)
    """
    
    def __init__(self, lr: float = 0.01, mu: float = 0.01, name: str = "fedprox"):
        """
        Initialize the FedProx strategy.
        
        Args:
            lr: Learning rate
            mu: Proximal term weight
            name: Name of the strategy
        """
        super().__init__(lr=lr, name=name)
        self.mu = mu
        
    def train(self, model: nn.Module, 
              train_loader: DataLoader, 
              epochs: int = 1,
              device: str = "cpu",
              **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Train the model using the FedProx strategy.
        
        Args:
            model: Model to train
            train_loader: DataLoader for training data
            epochs: Number of training epochs
            device: Device to use for training ("cpu" or "cuda")
            **kwargs: Additional strategy-specific parameters
                - lr: Learning rate (overrides the one set in the constructor)
                - mu: Proximal term weight (overrides the one set in the constructor)
                - global_model: The global model to use as reference for the proximal term
                
        Returns:
            Tuple of (trained_model, metrics)
        """
        # Get strategy parameters
        lr = kwargs.get("lr", self.lr)
        mu = kwargs.get("mu", self.mu)
        global_model = kwargs.get("global_model")
        
        if global_model is None:
            self.logger.warning("FedProx strategy requires a global_model. Falling back to FedAvg.")
            return super().train(model, train_loader, epochs, device, **kwargs)
        
        # Move global model to device and set to eval mode
        global_model = global_model.to(device)
        global_model.eval()
        
        # Set up the optimizer
        optimizer = optim.SGD(model.parameters(), lr=lr)
        
        # Set up the loss function
        loss_fn = nn.CrossEntropyLoss()
        
        # Move model to device
        model = model.to(device)
        model.train()
        
        # Initialize metrics
        metrics = {
            "train_loss": [],
            "proximal_term": [],
            "num_examples": len(train_loader.dataset),
            "num_batches": len(train_loader)
        }
        
        # Training loop
        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_proximal = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                # Move data to device
                data, target = data.to(device), target.to(device)
                
                # Zero the gradients
                optimizer.zero_grad()
                
                # Forward pass
                output = model(data)
                loss = loss_fn(output, target)
                
                # Compute proximal term
                proximal_term = 0.0
                for w, w_t in zip(model.parameters(), global_model.parameters()):
                    proximal_term += (w - w_t).norm(2)**2
                
                # Add proximal term to loss
                loss += (mu / 2) * proximal_term
                
                # Backward pass and optimize
                loss.backward()
                optimizer.step()
                
                # Update metrics
                epoch_loss += loss.item() - (mu / 2) * proximal_term.item()  # Original loss without proximal term
                epoch_proximal += proximal_term.item()
                
                # Calculate accuracy
                _, predicted = torch.max(output.data, 1)
                total += target.size(0)
                correct += (predicted == target).sum().item()
                
                # Log batch progress
                if batch_idx % 10 == 0:
                    self.logger.debug(f"Epoch: {epoch+1}/{epochs}, Batch: {batch_idx+1}/{len(train_loader)}, "
                                     f"Loss: {loss.item():.4f}, Proximal: {proximal_term.item():.4f}")
            
            # Calculate epoch metrics
            avg_loss = epoch_loss / len(train_loader)
            avg_proximal = epoch_proximal / len(train_loader)
            accuracy = 100.0 * correct / total
            
            # Log epoch metrics
            self.logger.info(f"Epoch {epoch+1}/{epochs} - "
                            f"Loss: {avg_loss:.4f}, "
                            f"Proximal: {avg_proximal:.4f}, "
                            f"Accuracy: {accuracy:.2f}%")
            
            # Add to metrics
            metrics["train_loss"].append(avg_loss)
            metrics["proximal_term"].append(avg_proximal)
            metrics[f"epoch_{epoch+1}_accuracy"] = accuracy
        
        # Calculate final metrics
        metrics["final_loss"] = metrics["train_loss"][-1] if metrics["train_loss"] else 0.0
        metrics["final_proximal"] = metrics["proximal_term"][-1] if metrics["proximal_term"] else 0.0
        metrics["final_accuracy"] = metrics.get(f"epoch_{epochs}_accuracy", 0.0)
        
        return model, metrics 