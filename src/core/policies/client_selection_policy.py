"""
Client Selection Policy

This module defines policies for selecting clients in federated learning.
"""

from abc import abstractmethod
from typing import Dict, Any, List

from src.core.policies.policy import IPolicy


class IClientSelectionPolicy(IPolicy):
    """
    Interface for client selection policies.
    
    Client selection policies determine which clients participate
    in each round of federated learning.
    """
    
    @abstractmethod
    def select_clients(self, available_clients: List[Dict[str, Any]], round_number: int, 
                      target_count: int, context: Dict[str, Any] = None) -> List[str]:
        """
        Select clients for a federated learning round.
        
        Args:
            available_clients: List of available clients with their metadata
            round_number: Current round number
            target_count: Target number of clients to select
            context: Additional context for selection
            
        Returns:
            List of selected client IDs
        """
        pass


class RandomSelectionPolicy(IClientSelectionPolicy):
    """
    Random client selection policy.
    
    This policy selects clients randomly from the pool of available clients.
    """
    
    def __init__(self, policy_id: str, description: str = "Random client selection policy"):
        self.policy_id = policy_id
        self.policy_type = "client_selection"
        self.description = description
        self.parameters = {}
    
    def get_id(self) -> str:
        return self.policy_id
    
    def get_type(self) -> str:
        return self.policy_type
    
    def get_description(self) -> str:
        return self.description
    
    def get_parameters(self) -> Dict[str, Any]:
        return self.parameters
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy in the given context.
        
        Args:
            context: Context for policy evaluation
                - available_clients: List of available clients
                - round_number: Current round number
                - target_count: Target number of clients to select
                
        Returns:
            Dictionary with selected client IDs
        """
        available_clients = context.get('available_clients', [])
        round_number = context.get('round_number', 0)
        target_count = context.get('target_count', 10)
        
        selected_clients = self.select_clients(available_clients, round_number, target_count)
        
        return {
            'selected_clients': selected_clients,
            'policy_id': self.policy_id,
            'policy_type': self.policy_type
        }
    
    def select_clients(self, available_clients: List[Dict[str, Any]], round_number: int, 
                      target_count: int, context: Dict[str, Any] = None) -> List[str]:
        """
        Select clients randomly.
        
        Args:
            available_clients: List of available clients with their metadata
            round_number: Current round number
            target_count: Target number of clients to select
            context: Additional context for selection
            
        Returns:
            List of selected client IDs
        """
        import random
        
        # Get client IDs from available clients
        client_ids = [client['client_id'] for client in available_clients]
        
        # If we have fewer clients than target, select all
        if len(client_ids) <= target_count:
            return client_ids
        
        # Otherwise, randomly select the target number
        return random.sample(client_ids, target_count)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary.
        
        Returns:
            Dictionary representation of the policy
        """
        return {
            'policy_id': self.policy_id,
            'policy_type': self.policy_type,
            'description': self.description,
            'parameters': self.parameters
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RandomSelectionPolicy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            RandomSelectionPolicy instance
        """
        policy = RandomSelectionPolicy(
            policy_id=data['policy_id'],
            description=data.get('description', "Random client selection policy")
        )
        
        if 'parameters' in data:
            policy.parameters = data['parameters']
            
        return policy 