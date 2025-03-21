"""
Federated Averaging Model Aggregator

This module provides an implementation of the federated averaging algorithm.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from src.domain.interfaces.model_aggregator import IModelAggregator


class FederatedAveraging(IModelAggregator):
    """
    Federated Averaging (FedAvg) implementation.
    
    This class implements the federated averaging algorithm as described in:
    "Communication-Efficient Learning of Deep Networks from Decentralized Data"
    by McMahan et al.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the federated averaging aggregator.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def aggregate(self, global_model: Dict[str, Any], client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate client model updates using federated averaging.
        
        Args:
            global_model: Current global model weights
            client_updates: List of client model updates with weights and metadata
            
        Returns:
            Updated global model
        """
        if not client_updates:
            self.logger.warning("No client updates to aggregate")
            return global_model
        
        # Extract client weights and sample counts
        client_weights = []
        sample_counts = []
        
        for update in client_updates:
            # Validate update
            if not self.validate_update(update):
                self.logger.warning(f"Skipping invalid update from client {update.get('client_id', 'unknown')}")
                continue
            
            # Preprocess update
            processed_update = self.preprocess_update(update)
            
            # Extract weights and sample count
            weights = processed_update.get("weights", [])
            sample_count = processed_update.get("metadata", {}).get("sample_count", 1)
            
            client_weights.append(weights)
            sample_counts.append(sample_count)
        
        if not client_weights:
            self.logger.warning("No valid client updates to aggregate")
            return global_model
        
        # Calculate total sample count
        total_samples = sum(sample_counts)
        
        # Compute weight scaling factors
        scaling_factors = [count / total_samples for count in sample_counts]
        
        # Perform weighted average of model parameters
        aggregated_weights = self._weighted_average(client_weights, scaling_factors)
        
        # Create new global model
        new_global_model = global_model.copy()
        new_global_model["weights"] = aggregated_weights
        
        # Update metadata
        if "metadata" not in new_global_model:
            new_global_model["metadata"] = {}
        
        new_global_model["metadata"]["aggregation_round"] = global_model.get("metadata", {}).get("aggregation_round", 0) + 1
        new_global_model["metadata"]["participating_clients"] = len(client_weights)
        new_global_model["metadata"]["total_samples"] = total_samples
        
        self.logger.info(f"Aggregated {len(client_weights)} client updates with {total_samples} total samples")
        
        return new_global_model
    
    def preprocess_update(self, client_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess a client update before aggregation.
        
        Args:
            client_update: Client model update
            
        Returns:
            Preprocessed client update
        """
        # Create a copy to avoid modifying the original
        processed_update = client_update.copy()
        
        # Ensure metadata exists
        if "metadata" not in processed_update:
            processed_update["metadata"] = {}
        
        # Set default sample count if not provided
        if "sample_count" not in processed_update["metadata"]:
            processed_update["metadata"]["sample_count"] = 1
        
        return processed_update
    
    def validate_update(self, client_update: Dict[str, Any]) -> bool:
        """
        Validate a client update.
        
        Args:
            client_update: Client model update
            
        Returns:
            True if update is valid, False otherwise
        """
        # Check if weights are present
        if "weights" not in client_update:
            self.logger.warning("Client update missing weights")
            return False
        
        weights = client_update.get("weights", [])
        
        # Check if weights are not empty
        if not weights:
            self.logger.warning("Client update has empty weights")
            return False
        
        # Check if weights are valid (not NaN or infinite)
        try:
            for layer_weights in weights:
                if np.isnan(layer_weights).any() or np.isinf(layer_weights).any():
                    self.logger.warning("Client update contains NaN or infinite values")
                    return False
        except Exception as e:
            self.logger.warning(f"Error validating client update: {e}")
            return False
        
        return True
    
    def _weighted_average(self, weights_list: List[List[np.ndarray]], scaling_factors: List[float]) -> List[np.ndarray]:
        """
        Compute weighted average of model weights.
        
        Args:
            weights_list: List of client weight arrays
            scaling_factors: Weight scaling factors (one per client)
            
        Returns:
            Weighted average of weights
        """
        # Initialize with zeros
        avg_weights = [np.zeros_like(w) for w in weights_list[0]]
        
        # Compute weighted average
        for weights, factor in zip(weights_list, scaling_factors):
            for i, w in enumerate(weights):
                avg_weights[i] += w * factor
        
        return avg_weights 