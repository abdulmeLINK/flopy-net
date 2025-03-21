"""
Federated Averaging (FedAvg) Strategy

This module provides an implementation of the Federated Averaging (FedAvg)
strategy for federated learning.
"""
import logging
import numpy as np
from typing import Dict, Any, List, Optional

from src.domain.interfaces.fl_strategy import IFLStrategy


class FedAvgStrategy(IFLStrategy):
    """
    Implementation of the Federated Averaging (FedAvg) strategy.
    
    This strategy aggregates model updates by weighted averaging based on
    data size or other client properties.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the FedAvg strategy.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.min_clients = self.config.get('min_clients', 2)
        self.max_clients = self.config.get('max_clients', 10)
        self.selection_criteria = self.config.get('selection_criteria', 'random')  # 'random', 'data_size', 'compute_power'
        self.weighting_factor = self.config.get('weighting_factor', 'data_size')  # 'data_size', 'uniform', 'compute_power'
        self.logger = logging.getLogger(__name__)
    
    def aggregate(self, model_updates: List[Dict[str, Any]], weights: List[float] = None) -> Dict[str, Any]:
        """
        Aggregate model updates using the FedAvg algorithm.
        
        Args:
            model_updates: List of model updates from clients
            weights: Optional weights for each client update
            
        Returns:
            Aggregated model update
        """
        if not model_updates:
            self.logger.warning("No model updates to aggregate")
            return {}
        
        # If no weights provided, use uniform weighting
        if weights is None:
            weights = [1.0 / len(model_updates)] * len(model_updates)
        else:
            # Normalize weights to sum to 1
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = [1.0 / len(model_updates)] * len(model_updates)
        
        # Check if weights and updates have the same length
        if len(weights) != len(model_updates):
            self.logger.warning("Number of weights does not match number of updates")
            weights = [1.0 / len(model_updates)] * len(model_updates)
        
        self.logger.info(f"Aggregating {len(model_updates)} model updates with weights: {weights}")
        
        # Extract model parameters from updates
        aggregated_update = {}
        
        # Iterate through all parameters in the first update to get structure
        try:
            # Use the first model update as a template for parameter names
            for param_name, param_value in model_updates[0].items():
                if isinstance(param_value, (list, np.ndarray)):
                    # Convert to numpy array for easier operations
                    param_value = np.array(param_value)
                    aggregated_value = np.zeros_like(param_value)
                    
                    # Weighted sum of parameter values across all clients
                    for i, update in enumerate(model_updates):
                        if param_name in update:
                            client_value = np.array(update[param_name])
                            if client_value.shape == param_value.shape:
                                aggregated_value += weights[i] * client_value
                            else:
                                self.logger.warning(f"Parameter shape mismatch for {param_name}")
                    
                    # Convert back to list for serialization
                    aggregated_update[param_name] = aggregated_value.tolist()
                elif isinstance(param_value, (int, float)):
                    # Weighted sum of scalar parameters
                    aggregated_value = 0
                    for i, update in enumerate(model_updates):
                        if param_name in update:
                            aggregated_value += weights[i] * update[param_name]
                    
                    aggregated_update[param_name] = aggregated_value
                else:
                    # For other types, just use the most common value
                    values = [update.get(param_name) for update in model_updates if param_name in update]
                    if values:
                        # Use the most frequent value for non-numeric parameters
                        from collections import Counter
                        counter = Counter(values)
                        aggregated_update[param_name] = counter.most_common(1)[0][0]
        
        except Exception as e:
            self.logger.error(f"Error during aggregation: {e}")
            return {}
        
        self.logger.info("Model aggregation completed successfully")
        return aggregated_update
    
    def client_selection(self, available_clients: List[str], client_properties: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Select clients to participate in a round using the strategy's selection criteria.
        
        Args:
            available_clients: List of available client IDs
            client_properties: Dictionary mapping client IDs to their properties
            
        Returns:
            List of selected client IDs
        """
        if not available_clients:
            self.logger.warning("No clients available for selection")
            return []
        
        # Ensure minimum and maximum client constraints
        num_clients = min(max(self.min_clients, len(available_clients)), self.max_clients)
        
        # Select clients based on the specified criteria
        if self.selection_criteria == 'data_size':
            # Sort by data size
            clients_with_size = [(client_id, client_properties.get(client_id, {}).get('data_size', 0)) 
                                for client_id in available_clients]
            sorted_clients = sorted(clients_with_size, key=lambda x: x[1], reverse=True)
            selected_clients = [client for client, _ in sorted_clients[:num_clients]]
            
        elif self.selection_criteria == 'compute_power':
            # Sort by compute power
            clients_with_power = [(client_id, client_properties.get(client_id, {}).get('compute_power', 0)) 
                                 for client_id in available_clients]
            sorted_clients = sorted(clients_with_power, key=lambda x: x[1], reverse=True)
            selected_clients = [client for client, _ in sorted_clients[:num_clients]]
            
        else:  # random selection
            import random
            selected_clients = random.sample(available_clients, k=min(num_clients, len(available_clients)))
        
        self.logger.info(f"Selected {len(selected_clients)} clients using {self.selection_criteria} criteria")
        return selected_clients
    
    def get_name(self) -> str:
        """
        Get the strategy name.
        
        Returns:
            Strategy name
        """
        return "fedavg"
    
    def get_description(self) -> str:
        """
        Get the strategy description.
        
        Returns:
            Strategy description
        """
        return "Federated Averaging (FedAvg) strategy for aggregating model updates" 