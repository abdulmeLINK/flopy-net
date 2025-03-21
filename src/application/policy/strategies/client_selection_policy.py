"""
Client Selection Policy

This module provides a policy for selecting clients based on various criteria,
implementing the strategy pattern for client selection.
"""
from typing import Dict, Any, List
import logging

from src.domain.interfaces.policy import IPolicy


class ClientSelectionPolicy(IPolicy):
    """
    Policy for selecting clients based on various criteria.
    
    This policy evaluates clients based on data size, compute power,
    and other properties to determine which clients should participate
    in federated learning rounds.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the client selection policy.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.min_data_size = self.config.get('min_data_size', 100)
        self.min_compute_power = self.config.get('min_compute_power', 0.5)
        self.max_clients = self.config.get('max_clients', 10)
        self.prioritize_by = self.config.get('prioritize_by', 'data_size')  # 'data_size', 'compute_power', 'random'
        self.logger = logging.getLogger(__name__)
        
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy with the given context.
        
        Args:
            context: Context information including available clients
                and their properties
            
        Returns:
            Policy evaluation result with selected clients
        """
        available_clients = context.get('available_clients', [])
        client_properties = context.get('client_properties', {})
        
        # Filter clients based on minimum requirements
        filtered_clients = []
        for client_id in available_clients:
            if client_id not in client_properties:
                continue
                
            properties = client_properties[client_id]
            data_size = properties.get('data_size', 0)
            compute_power = properties.get('compute_power', 0)
            
            if data_size >= self.min_data_size and compute_power >= self.min_compute_power:
                filtered_clients.append(client_id)
        
        # Sort clients based on prioritization strategy
        if self.prioritize_by == 'data_size':
            sorted_clients = sorted(
                filtered_clients,
                key=lambda c: client_properties.get(c, {}).get('data_size', 0),
                reverse=True
            )
        elif self.prioritize_by == 'compute_power':
            sorted_clients = sorted(
                filtered_clients,
                key=lambda c: client_properties.get(c, {}).get('compute_power', 0),
                reverse=True
            )
        else:  # random
            import random
            sorted_clients = filtered_clients.copy()
            random.shuffle(sorted_clients)
        
        # Limit number of clients
        selected_clients = sorted_clients[:self.max_clients]
        
        return {
            'policy_name': self.get_name(),
            'selected_clients': selected_clients,
            'total_available': len(available_clients),
            'total_filtered': len(filtered_clients),
            'total_selected': len(selected_clients)
        }
    
    def get_name(self) -> str:
        """
        Get the policy name.
        
        Returns:
            Policy name
        """
        return "client_selection"
    
    def get_description(self) -> str:
        """
        Get the policy description.
        
        Returns:
            Policy description
        """
        return "Selects clients based on data size, compute power, and other criteria" 