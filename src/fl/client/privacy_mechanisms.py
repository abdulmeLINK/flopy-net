"""
Privacy mechanisms for federated learning clients.

This module provides privacy-enhancing mechanisms for federated learning clients,
including differential privacy and other techniques to protect client data.
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

import torch
import torch.nn as nn
import numpy as np

from src.core.common.logger import LoggerMixin


class PrivacyMechanism(LoggerMixin):
    """Base class for privacy mechanisms."""
    
    def __init__(self, name: str = "base_mechanism"):
        """
        Initialize the privacy mechanism.
        
        Args:
            name: Name of the mechanism
        """
        self.name = name
        
    def apply(self, model: nn.Module, **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Apply the privacy mechanism to the model.
        
        Args:
            model: Model to apply privacy mechanism to
            **kwargs: Additional mechanism-specific parameters
            
        Returns:
            Tuple of (model with privacy applied, privacy metrics)
        """
        # Base implementation does nothing
        self.logger.info(f"Applying {self.name} privacy mechanism")
        return model, {"mechanism": self.name}


class DifferentialPrivacy(PrivacyMechanism):
    """
    Differential privacy mechanism for model updates.
    
    This mechanism adds calibrated noise to model parameters to provide
    differential privacy guarantees.
    """
    
    def __init__(self, 
                 noise_multiplier: float = 1.0,
                 max_grad_norm: float = 1.0,
                 name: str = "differential_privacy"):
        """
        Initialize the differential privacy mechanism.
        
        Args:
            noise_multiplier: Noise multiplier (sigma)
            max_grad_norm: Maximum L2 norm of gradients (clipping threshold)
            name: Name of the mechanism
        """
        super().__init__(name=name)
        self.noise_multiplier = noise_multiplier
        self.max_grad_norm = max_grad_norm
        self.privacy_budget = float('inf')  # epsilon, initially unlimited
        self.privacy_spent = 0.0  # epsilon spent so far
        
    def apply(self, model: nn.Module, **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Apply differential privacy to the model by adding noise to parameters.
        
        Args:
            model: Model to apply differential privacy to
            **kwargs: Additional parameters:
                - noise_multiplier: Override the noise multiplier
                - max_grad_norm: Override the max gradient norm
                - batch_size: Batch size used for training
                - sample_size: Total number of samples in the dataset
                - privacy_budget: Maximum privacy budget to spend (epsilon)
                
        Returns:
            Tuple of (model with DP applied, privacy metrics)
        """
        # Get parameters
        noise_multiplier = kwargs.get('noise_multiplier', self.noise_multiplier)
        max_grad_norm = kwargs.get('max_grad_norm', self.max_grad_norm)
        batch_size = kwargs.get('batch_size', None)
        sample_size = kwargs.get('sample_size', None)
        privacy_budget = kwargs.get('privacy_budget', self.privacy_budget)
        
        # Check if we have exceeded privacy budget
        if self.privacy_spent >= privacy_budget:
            self.logger.warning(f"Privacy budget exceeded: {self.privacy_spent} >= {privacy_budget}")
            return model, {
                "mechanism": self.name,
                "status": "budget_exceeded",
                "privacy_spent": self.privacy_spent,
                "privacy_budget": privacy_budget
            }
        
        # Apply DP-SGD noise addition
        total_norm = 0.0
        clipped_grads = []
        
        # Get model parameters with gradients
        for param in model.parameters():
            if param.grad is not None:
                # Calculate gradient norm
                param_norm = param.grad.data.norm(2)
                total_norm += param_norm.item() ** 2
                
                # Store for later clipping
                clipped_grads.append(param.grad.data)
        
        total_norm = total_norm ** 0.5
        
        # Clip gradients
        clip_coef = max_grad_norm / (total_norm + 1e-6)
        if clip_coef < 1:
            for grad in clipped_grads:
                grad.mul_(clip_coef)
        
        # Add noise to gradients
        for grad in clipped_grads:
            noise = torch.randn_like(grad) * noise_multiplier * max_grad_norm
            grad.add_(noise)
        
        # Calculate privacy spent (approximate using moment accountant)
        # This is a simple approximation - production code should use proper DP accounting
        if batch_size is not None and sample_size is not None:
            # q is the sampling probability
            q = batch_size / sample_size
            
            # Simple approximation of privacy spent
            # In production, use a proper DP accountant like RDP or zCDP
            # This is just a rough estimate based on the analytical Gaussian mechanism
            delta = 1.0 / sample_size  # Standard choice for delta
            epsilon_spent = self._calculate_approximate_epsilon(q, noise_multiplier, delta)
            
            # Update privacy spent
            self.privacy_spent += epsilon_spent
            
            privacy_metrics = {
                "mechanism": self.name,
                "status": "applied",
                "noise_multiplier": noise_multiplier,
                "max_grad_norm": max_grad_norm,
                "clip_coef": clip_coef.item() if isinstance(clip_coef, torch.Tensor) else clip_coef,
                "total_norm_before_clip": total_norm,
                "batch_size": batch_size,
                "sample_size": sample_size,
                "sampling_rate": q,
                "epsilon_spent": epsilon_spent,
                "total_epsilon_spent": self.privacy_spent,
                "privacy_budget": privacy_budget,
                "delta": delta
            }
        else:
            privacy_metrics = {
                "mechanism": self.name,
                "status": "applied",
                "noise_multiplier": noise_multiplier,
                "max_grad_norm": max_grad_norm,
                "clip_coef": clip_coef.item() if isinstance(clip_coef, torch.Tensor) else clip_coef,
                "total_norm_before_clip": total_norm
            }
        
        self.logger.info(f"Applied differential privacy with noise multiplier {noise_multiplier}")
        return model, privacy_metrics
    
    def _calculate_approximate_epsilon(self, q: float, sigma: float, delta: float) -> float:
        """
        Calculate an approximation of epsilon for the given parameters.
        
        Args:
            q: Sampling probability (batch_size / sample_size)
            sigma: Noise multiplier
            delta: Target delta
            
        Returns:
            float: Approximate epsilon spent
        """
        # This is a very simple approximation based on the analytical Gaussian mechanism
        # In production, use a proper DP accounting method
        c = q * math.sqrt(2 * math.log(1.25 / delta))
        return c / sigma
    
    def reset_privacy_budget(self) -> None:
        """Reset the privacy budget tracking."""
        self.privacy_spent = 0.0
        
    def get_privacy_spent(self) -> float:
        """Get the amount of privacy budget spent so far."""
        return self.privacy_spent


class SecureAggregation(PrivacyMechanism):
    """
    Secure aggregation preparation for federated learning.
    
    This class prepares model updates for secure aggregation by adding
    random masks that cancel out during aggregation.
    
    Note: A full secure aggregation protocol requires coordination with 
    the server and other clients. This class only handles the client-side
    preparation.
    """
    
    def __init__(self, 
                 seed: Optional[int] = None,
                 mask_scale: float = 1.0,
                 name: str = "secure_aggregation"):
        """
        Initialize the secure aggregation mechanism.
        
        Args:
            seed: Random seed for mask generation
            mask_scale: Scale factor for random masks
            name: Name of the mechanism
        """
        super().__init__(name=name)
        self.seed = seed if seed is not None else np.random.randint(0, 2**31)
        self.mask_scale = mask_scale
        self.masks = {}  # Stored masks for later removal
        
    def apply(self, model: nn.Module, **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Apply secure aggregation preparation to the model.
        
        This adds random noise to model parameters that will cancel out
        during aggregation on the server.
        
        Args:
            model: Model to prepare for secure aggregation
            **kwargs: Additional parameters:
                - round_id: Current training round ID
                - mask_scale: Override the mask scale
                - client_id: ID of the client
                - num_clients: Total number of clients in the aggregation
                
        Returns:
            Tuple of (model prepared for secure aggregation, metrics)
        """
        # Get parameters
        round_id = kwargs.get('round_id', 0)
        mask_scale = kwargs.get('mask_scale', self.mask_scale)
        client_id = kwargs.get('client_id', 'unknown')
        num_clients = kwargs.get('num_clients', 1)
        
        # Set the random seed based on round ID and client ID for reproducibility
        if isinstance(client_id, str):
            client_seed = hash(client_id) % (2**31)
        else:
            client_seed = client_id
        
        np.random.seed(self.seed + round_id + client_seed)
        
        # Generate and apply masks to each parameter
        masks = []
        with torch.no_grad():
            for param in model.parameters():
                # Generate random mask
                mask = torch.from_numpy(
                    np.random.normal(0, mask_scale, param.size())
                ).to(param.device).type(param.dtype)
                
                # Store mask for potential later removal
                masks.append(mask.clone().cpu().numpy())
                
                # Apply mask to parameter
                param.add_(mask)
        
        # Store masks for this round
        self.masks[round_id] = masks
        
        self.logger.info(f"Applied secure aggregation preparation for round {round_id}, client {client_id}")
        return model, {
            "mechanism": self.name,
            "status": "applied",
            "round_id": round_id,
            "mask_scale": mask_scale,
            "num_clients": num_clients
        }
    
    def remove_mask(self, model: nn.Module, round_id: int) -> nn.Module:
        """
        Remove the mask from the model.
        
        This is used when aggregation fails and the client needs to
        submit an unmasked model.
        
        Args:
            model: Model with mask applied
            round_id: Round ID to identify the mask
            
        Returns:
            nn.Module: Model with mask removed
        """
        if round_id not in self.masks:
            self.logger.warning(f"No mask found for round {round_id}")
            return model
        
        masks = self.masks[round_id]
        
        with torch.no_grad():
            for param, mask in zip(model.parameters(), masks):
                mask_tensor = torch.from_numpy(mask).to(param.device).type(param.dtype)
                param.sub_(mask_tensor)
        
        self.logger.info(f"Removed secure aggregation mask for round {round_id}")
        return model
    
    def clear_masks(self) -> None:
        """Clear all stored masks."""
        self.masks = {}
        self.logger.info("Cleared all secure aggregation masks")


class LocalModelTruncation(PrivacyMechanism):
    """
    Local model truncation for privacy.
    
    This mechanism truncates model updates to reduce the amount of
    information leakage from local training.
    """
    
    def __init__(self, 
                 top_k_percent: float = 0.1,
                 threshold: Optional[float] = None,
                 name: str = "local_model_truncation"):
        """
        Initialize the local model truncation mechanism.
        
        Args:
            top_k_percent: Percentage of parameters to keep (by magnitude)
            threshold: Absolute threshold for truncation (overrides top_k_percent)
            name: Name of the mechanism
        """
        super().__init__(name=name)
        self.top_k_percent = top_k_percent
        self.threshold = threshold
        
    def apply(self, model: nn.Module, **kwargs) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Apply local model truncation to the model.
        
        Args:
            model: Model to truncate
            **kwargs: Additional parameters:
                - top_k_percent: Override the top k percent
                - threshold: Override the absolute threshold
                - reference_model: Reference model to compute updates against
                
        Returns:
            Tuple of (truncated model, metrics)
        """
        # Get parameters
        top_k_percent = kwargs.get('top_k_percent', self.top_k_percent)
        threshold = kwargs.get('threshold', self.threshold)
        reference_model = kwargs.get('reference_model', None)
        
        if reference_model is None:
            self.logger.warning("No reference model provided for truncation, using model as is")
            return model, {
                "mechanism": self.name,
                "status": "skipped",
                "reason": "no_reference_model"
            }
        
        # Calculate model updates (difference from reference model)
        updates = []
        reference_params = list(reference_model.parameters())
        
        for i, param in enumerate(model.parameters()):
            update = param.data - reference_params[i].data
            updates.append(update)
        
        # Flatten all updates into a single vector
        all_updates = torch.cat([update.flatten() for update in updates])
        total_params = all_updates.numel()
        
        # Determine truncation threshold
        if threshold is None:
            # Use top-k percent
            k = max(1, int(total_params * top_k_percent))
            
            # Get the k-th largest value by magnitude
            topk_values = torch.topk(all_updates.abs(), k, largest=True)
            threshold = topk_values.values[-1].item()
        
        # Apply truncation
        with torch.no_grad():
            for i, (param, ref_param) in enumerate(zip(model.parameters(), reference_params.parameters())):
                # Get the update
                update = param.data - ref_param.data
                
                # Create a mask for values to keep (above threshold)
                mask = update.abs() >= threshold
                
                # Apply truncation by keeping only values above threshold
                truncated_update = update * mask
                
                # Apply the truncated update to the reference model
                param.data = ref_param.data + truncated_update
        
        # Calculate metrics
        sparsity = 1.0 - (mask.sum().item() / total_params)
        
        self.logger.info(f"Applied local model truncation with threshold {threshold:.6f}, sparsity {sparsity:.2%}")
        return model, {
            "mechanism": self.name,
            "status": "applied",
            "threshold": threshold,
            "top_k_percent": top_k_percent,
            "sparsity": sparsity,
            "total_params": total_params,
            "params_kept": mask.sum().item()
        } 