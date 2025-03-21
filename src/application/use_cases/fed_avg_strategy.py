"""
FedAvg Aggregation Strategy

This module provides an implementation of the Federated Averaging (FedAvg) 
aggregation strategy.
"""
from typing import Dict, List, Any, Tuple
import logging
import random
import numpy as np

from src.domain.interfaces.aggregation_strategy import IAggregationStrategy


class FedAvgStrategy(IAggregationStrategy):
    """
    Implementation of the Federated Averaging (FedAvg) aggregation strategy.
    
    This strategy aggregates model parameters from clients by computing
    a weighted average based on the number of training samples.
    """
    
    def __init__(self, min_clients: int = 2, min_available_clients: int = 2, 
                 fraction_fit: float = 1.0, logger: logging.Logger = None):
        """
        Initialize the FedAvg strategy.
        
        Args:
            min_clients: Minimum number of clients for aggregation
            min_available_clients: Minimum number of available clients required
            fraction_fit: Fraction of clients to select for training
            logger: Logger instance
        """
        self.min_clients = min_clients
        self.min_available_clients = min_available_clients
        self.fraction_fit = fraction_fit
        self.logger = logger or logging.getLogger(__name__)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the strategy.
        
        Args:
            config: Configuration dictionary
        """
        self.min_clients = config.get("min_clients", self.min_clients)
        self.min_available_clients = config.get("min_available_clients", self.min_available_clients)
        self.fraction_fit = config.get("fraction_fit", self.fraction_fit)
        
        self.logger.info(
            f"Configured FedAvg with min_clients={self.min_clients}, "
            f"min_available_clients={self.min_available_clients}, "
            f"fraction_fit={self.fraction_fit}"
        )
    
    def aggregate(self, 
                 client_results: List[Tuple[List[Any], int, Dict[str, Any]]], 
                 current_weights: List[Any] = None) -> List[Any]:
        """
        Aggregate the client results to produce updated global parameters.
        
        Args:
            client_results: List of client results, each a tuple of (parameters, num_samples, metrics)
            current_weights: Current global model weights, if available
            
        Returns:
            Aggregated global parameters
        """
        if not client_results:
            self.logger.warning("No client results to aggregate")
            return current_weights or []
        
        # Extract parameters and number of samples
        parameters_list = [parameters for parameters, _, _ in client_results]
        sample_counts = [num_samples for _, num_samples, _ in client_results]
        
        # Calculate total number of samples
        total_samples = sum(sample_counts)
        
        if total_samples == 0:
            self.logger.warning("Total sample count is zero, using simple average")
            weights = [1.0 / len(client_results)] * len(client_results)
        else:
            # Calculate weights based on number of samples
            weights = [count / total_samples for count in sample_counts]
        
        # Perform weighted average of parameters
        aggregated_parameters = []
        
        # Check that all clients have the same number of parameters
        if not all(len(params) == len(parameters_list[0]) for params in parameters_list):
            self.logger.error("Clients have different numbers of parameters")
            return current_weights or []
        
        # Aggregate each parameter
        for param_index in range(len(parameters_list[0])):
            # Get corresponding parameter from each client
            parameter_values = [params[param_index] for params in parameters_list]
            
            # Convert parameters to numpy arrays if they aren't already
            parameter_values = [
                np.array(value) if not isinstance(value, np.ndarray) else value
                for value in parameter_values
            ]
            
            # Perform weighted average
            weighted_param = np.zeros_like(parameter_values[0])
            for weight, param in zip(weights, parameter_values):
                weighted_param += weight * param
            
            aggregated_parameters.append(weighted_param)
        
        self.logger.info(f"Aggregated parameters from {len(client_results)} clients")
        return aggregated_parameters
    
    def select_clients(self, 
                      available_clients: List[str], 
                      client_properties: Dict[str, Dict[str, Any]],
                      num_clients: int) -> List[str]:
        """
        Select clients for the current round.
        
        Args:
            available_clients: List of available client IDs
            client_properties: Dictionary mapping client IDs to their properties
            num_clients: Target number of clients to select
            
        Returns:
            List of selected client IDs
        """
        if not available_clients:
            self.logger.warning("No available clients to select from")
            return []
        
        # Check if we have enough available clients
        if len(available_clients) < self.min_available_clients:
            self.logger.warning(
                f"Not enough available clients: {len(available_clients)} < "
                f"{self.min_available_clients}"
            )
            return []
        
        # Calculate number of clients to select
        num_clients_to_select = max(
            self.min_clients,
            min(num_clients, int(self.fraction_fit * len(available_clients)))
        )
        
        # Prioritize clients with more data if the information is available
        if client_properties and all("data_size" in props for props in client_properties.values()):
            # Sort clients by data size (descending)
            sorted_clients = sorted(
                available_clients,
                key=lambda c: client_properties.get(c, {}).get("data_size", 0),
                reverse=True
            )
            
            # Select clients with the most data
            selected_clients = sorted_clients[:num_clients_to_select]
        else:
            # Randomly select clients
            selected_clients = random.sample(
                available_clients, 
                min(num_clients_to_select, len(available_clients))
            )
        
        self.logger.info(
            f"Selected {len(selected_clients)} clients out of {len(available_clients)} "
            f"available clients"
        )
        return selected_clients 