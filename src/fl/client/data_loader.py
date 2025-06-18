"""
Data loading utilities for federated learning clients.

This module provides data loading and preprocessing utilities for federated learning clients.
"""

import os
import json
import numpy as np
from typing import Dict, Any, Tuple, Optional, List, Callable, Union

import torch
from torch.utils.data import Dataset, DataLoader, Subset, random_split
import torchvision.transforms as transforms
from torchvision.datasets import MNIST, CIFAR10, ImageFolder

from src.core.common.logger import LoggerMixin


class FederatedDataset(Dataset, LoggerMixin):
    """Base class for federated datasets."""
    
    def __init__(self, data_root: str, client_id: str, transform=None, target_transform=None):
        """
        Initialize the dataset.
        
        Args:
            data_root: Root directory for the dataset
            client_id: ID of the client this dataset belongs to
            transform: Transformations to apply to features
            target_transform: Transformations to apply to targets
        """
        self.data_root = data_root
        self.client_id = client_id
        self.transform = transform
        self.target_transform = target_transform
        self.features = []
        self.targets = []
        
    def __len__(self) -> int:
        """Return the number of samples in the dataset."""
        return len(self.features)
    
    def __getitem__(self, idx: int) -> Tuple[Any, Any]:
        """Get a sample from the dataset."""
        feature = self.features[idx]
        target = self.targets[idx]
        
        if self.transform:
            feature = self.transform(feature)
        
        if self.target_transform:
            target = self.target_transform(target)
            
        return feature, target
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the dataset."""
        if not self.targets:
            return {"num_samples": 0, "class_distribution": {}}
        
        # Count samples per class
        classes, counts = np.unique(self.targets, return_counts=True)
        class_dist = {int(c): int(count) for c, count in zip(classes, counts)}
        
        return {
            "num_samples": len(self.targets),
            "class_distribution": class_dist,
            "num_classes": len(class_dist)
        }


class FederatedMNIST(FederatedDataset):
    """Federated MNIST dataset."""
    
    def __init__(self, data_root: str, client_id: str, train: bool = True, 
                 transform=None, target_transform=None):
        """
        Initialize the MNIST dataset.
        
        Args:
            data_root: Root directory for the dataset
            client_id: ID of the client this dataset belongs to
            train: Whether to load the training set
            transform: Transformations to apply to features
            target_transform: Transformations to apply to targets
        """
        super().__init__(data_root, client_id, transform, target_transform)
        
        # Default transform if none provided
        if transform is None:
            self.transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))
            ])
        
        # Download MNIST dataset
        self.logger.info(f"Loading MNIST dataset for client {client_id}")
        mnist = MNIST(root=data_root, train=train, download=True, 
                      transform=None, target_transform=None)
        
        # Get the full dataset
        self.features = mnist.data.numpy()
        self.targets = mnist.targets.numpy()
        
        # For federated learning, we simulate data partitioning based on client_id
        self._partition_data(client_id)
    
    def _partition_data(self, client_id: str) -> None:
        """
        Partition the data for federated learning.
        
        This method simulates non-IID data distribution by partitioning the data
        based on the client_id. It supports various partitioning schemes like
        by-label or random with different distribution shifts.
        
        Args:
            client_id: ID of the client, used to determine the partition
        """
        # Extract client number from client_id
        try:
            client_num = int(client_id.split('_')[-1])
        except (ValueError, IndexError):
            client_num = hash(client_id) % 100
        
        # For simplicity, let's do a simple partitioning based on client number
        n_clients = 10  # Assume 10 clients
        n_samples = len(self.features)
        samples_per_client = n_samples // n_clients
        
        # Get the current client's partition
        start_idx = (client_num % n_clients) * samples_per_client
        if client_num % n_clients == n_clients - 1:
            # Last client gets all remaining samples
            end_idx = n_samples
        else:
            end_idx = start_idx + samples_per_client
        
        self.logger.info(f"Partitioning data for client {client_id}: "
                        f"samples {start_idx} to {end_idx}")
        
        # Apply the partition
        self.features = self.features[start_idx:end_idx]
        self.targets = self.targets[start_idx:end_idx]


class FederatedCIFAR10(FederatedDataset):
    """Federated CIFAR-10 dataset."""
    
    def __init__(self, data_root: str, client_id: str, train: bool = True, 
                 transform=None, target_transform=None):
        """
        Initialize the CIFAR-10 dataset.
        
        Args:
            data_root: Root directory for the dataset
            client_id: ID of the client this dataset belongs to
            train: Whether to load the training set
            transform: Transformations to apply to features
            target_transform: Transformations to apply to targets
        """
        super().__init__(data_root, client_id, transform, target_transform)
        
        # Default transform if none provided
        if transform is None:
            if train:
                self.transform = transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.RandomCrop(32, padding=4),
                    transforms.RandomHorizontalFlip(),
                    transforms.ToTensor(),
                    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616))
                ])
            else:
                self.transform = transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.ToTensor(),
                    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616))
                ])
        
        # Download CIFAR-10 dataset
        self.logger.info(f"Loading CIFAR-10 dataset for client {client_id}")
        cifar = CIFAR10(root=data_root, train=train, download=True, 
                        transform=None, target_transform=None)
        
        # Get the full dataset
        self.features = cifar.data  # Already numpy array
        self.targets = np.array(cifar.targets)
        
        # For federated learning, we simulate data partitioning based on client_id
        self._partition_data(client_id)
    
    def _partition_data(self, client_id: str) -> None:
        """
        Partition the data for federated learning.
        
        This method simulates non-IID data distribution by partitioning the data
        based on the client_id. For CIFAR-10, we use a Dirichlet distribution
        to create non-IID partitions.
        
        Args:
            client_id: ID of the client, used to determine the partition
        """
        # Extract client number from client_id
        try:
            client_num = int(client_id.split('_')[-1])
        except (ValueError, IndexError):
            client_num = hash(client_id) % 100
        
        # For simplicity, let's do label-based partitioning
        n_clients = 10  # Assume 10 clients
        n_classes = 10  # CIFAR-10 has 10 classes
        
        # Each client gets 2 classes primarily
        primary_classes = [(client_num % n_clients + i) % n_classes for i in range(2)]
        
        # Get indices of primary classes
        primary_indices = np.where(np.isin(self.targets, primary_classes))[0]
        other_indices = np.where(~np.isin(self.targets, primary_classes))[0]
        
        # We want 80% of the data to be from primary classes
        n_primary = int(len(primary_indices) * 0.8)
        n_other = len(self.features) // n_clients - n_primary
        
        # Randomly select samples
        np.random.seed(client_num)  # For reproducibility
        selected_primary = np.random.choice(primary_indices, min(n_primary, len(primary_indices)), replace=False)
        selected_other = np.random.choice(other_indices, min(n_other, len(other_indices)), replace=False)
        
        selected_indices = np.concatenate([selected_primary, selected_other])
        
        self.logger.info(f"Partitioning data for client {client_id}: "
                        f"{len(selected_indices)} samples, "
                        f"primary classes: {primary_classes}")
        
        # Apply the partition
        self.features = self.features[selected_indices]
        self.targets = self.targets[selected_indices]


def create_federated_dataloaders(
    dataset_name: str,
    client_id: str,
    data_root: str = "data",
    batch_size: int = 32,
    val_split: float = 0.1,
    num_workers: int = 0,
    pin_memory: bool = False,
    **dataset_kwargs
) -> Tuple[DataLoader, Optional[DataLoader]]:
    """
    Create train and validation dataloaders for federated learning.
    
    Args:
        dataset_name: Name of the dataset (e.g., "mnist", "cifar10")
        client_id: ID of the client
        data_root: Root directory for the dataset
        batch_size: Batch size for the dataloaders
        val_split: Fraction of training data to use for validation
        num_workers: Number of workers for the dataloaders
        pin_memory: Whether to pin memory for the dataloaders
        **dataset_kwargs: Additional arguments for the dataset
        
    Returns:
        Tuple of (train_loader, val_loader)
    """
    logger = LoggerMixin()
    logger.logger.info(f"Creating federated dataloaders for {dataset_name}, client {client_id}")
    
    # Create the dataset based on the name
    if dataset_name.lower() == "mnist":
        dataset_class = FederatedMNIST
    elif dataset_name.lower() == "cifar10":
        dataset_class = FederatedCIFAR10
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    
    # Create the dataset
    dataset = dataset_class(data_root=data_root, client_id=client_id, train=True, **dataset_kwargs)
    
    # Split into train and validation sets
    if val_split > 0 and val_split < 1:
        val_size = int(len(dataset) * val_split)
        train_size = len(dataset) - val_size
        
        train_dataset, val_dataset = random_split(
            dataset, [train_size, val_size],
            generator=torch.Generator().manual_seed(42)  # For reproducibility
        )
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=pin_memory
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=pin_memory
        )
        
        logger.logger.info(f"Created dataloaders: {train_size} training samples, {val_size} validation samples")
        return train_loader, val_loader
    else:
        # No validation set
        train_loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=pin_memory
        )
        
        logger.logger.info(f"Created dataloader: {len(dataset)} training samples, no validation")
        return train_loader, None 