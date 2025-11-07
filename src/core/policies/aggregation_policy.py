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
Aggregation Policy

This module defines policies for aggregating model updates in federated learning.
"""

from abc import abstractmethod
from typing import Dict, Any, List

from src.core.policies.policy import IPolicy


class IAggregationPolicy(IPolicy):
    """
    Interface for aggregation policies.
    
    Aggregation policies determine how model updates from different
    clients are combined in federated learning.
    """
    
    @abstractmethod
    def aggregate_updates(self, updates: List[Dict[str, Any]], weights: List[float] = None,
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Aggregate model updates from clients.
        
        Args:
            updates: List of model updates from clients
            weights: Optional weights for each update
            context: Additional context for aggregation
            
        Returns:
            Aggregated model update
        """
        pass


class FederatedAveragingPolicy(IAggregationPolicy):
    """
    Federated Averaging (FedAvg) aggregation policy.
    
    This policy implements the FedAvg algorithm, which computes a weighted
    average of client model updates.
    """
    
    def __init__(self, policy_id: str, description: str = "Federated Averaging aggregation policy"):
        self.policy_id = policy_id
        self.policy_type = "model_aggregation"
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
                - updates: Model updates from clients
                - weights: Weights for each update
                
        Returns:
            Dictionary with aggregation result
        """
        updates = context.get('updates', [])
        weights = context.get('weights', None)
        
        aggregated = self.aggregate_updates(updates, weights)
        
        return {
            'aggregated_update': aggregated,
            'policy_id': self.policy_id,
            'policy_type': self.policy_type
        }
    
    def aggregate_updates(self, updates: List[Dict[str, Any]], weights: List[float] = None,
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Aggregate model updates using federated averaging.
        
        Args:
            updates: List of model updates from clients
            weights: Optional weights for each update (e.g., sample sizes)
            context: Additional context for aggregation
            
        Returns:
            Aggregated model update
        """
        if not updates:
            return {}
        
        # If no weights provided, use equal weights
        if weights is None:
            weights = [1.0 / len(updates)] * len(updates)
        else:
            # Normalize weights
            total_weight = sum(weights)
            if total_weight == 0:
                weights = [1.0 / len(updates)] * len(updates)
            else:
                weights = [w / total_weight for w in weights]
        
        # Ensure we have the same number of weights as updates
        if len(weights) != len(updates):
            raise ValueError("Number of weights must match number of updates")
        
        # Perform weighted averaging
        aggregated = {}
        
        # Identify all keys in the updates
        all_keys = set()
        for update in updates:
            all_keys.update(update.keys())
        
        # For each parameter, compute weighted average
        for key in all_keys:
            # Only consider updates that have this key
            valid_updates = [(u, w) for u, w in zip(updates, weights) if key in u]
            
            if not valid_updates:
                continue
            
            # Check if values are numeric (can be averaged)
            first_value = valid_updates[0][0][key]
            
            if isinstance(first_value, (int, float)):
                # Simple weighted average for scalar values
                aggregated[key] = sum(u[key] * w for u, w in valid_updates)
            elif hasattr(first_value, 'shape') and hasattr(first_value, '__mul__'):
                # Assume NumPy-like array
                weighted_sum = valid_updates[0][0][key] * valid_updates[0][1]
                for update, weight in valid_updates[1:]:
                    weighted_sum += update[key] * weight
                aggregated[key] = weighted_sum
            else:
                # Use most common value for non-numeric data
                value_counts = {}
                for update, weight in valid_updates:
                    value = update[key]
                    # Use string representation as dictionary key
                    value_str = str(value)
                    if value_str not in value_counts:
                        value_counts[value_str] = 0
                    value_counts[value_str] += weight
                
                # Find the value with the highest weighted count
                most_common_value_str = max(value_counts, key=value_counts.get)
                
                # Use the actual value from one of the updates
                for update, _ in valid_updates:
                    if str(update[key]) == most_common_value_str:
                        aggregated[key] = update[key]
                        break
        
        return aggregated
    
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
    def from_dict(data: Dict[str, Any]) -> 'FederatedAveragingPolicy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            FederatedAveragingPolicy instance
        """
        policy = FederatedAveragingPolicy(
            policy_id=data['policy_id'],
            description=data.get('description', "Federated Averaging aggregation policy")
        )
        
        if 'parameters' in data:
            policy.parameters = data['parameters']
            
        return policy 