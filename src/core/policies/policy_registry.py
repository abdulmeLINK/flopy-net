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
Policy Registry

This module provides a central registry for managing policies in the system.
"""

from typing import Dict, Any, List, Type, Optional, TypeVar
import logging

from src.core.policies.policy import IPolicy
from src.core.policies.client_selection_policy import IClientSelectionPolicy, RandomSelectionPolicy
from src.core.policies.network_policy import INetworkPolicy, ShortestPathPolicy
from src.core.policies.aggregation_policy import IAggregationPolicy, FederatedAveragingPolicy
from src.core.policies.privacy_policy import IPrivacyPolicy, DifferentialPrivacyPolicy
from src.core.policies.scheduling_policy import ISchedulingPolicy, PeriodicSchedulingPolicy

# Type variable for policy types
T = TypeVar('T', bound=IPolicy)

logger = logging.getLogger(__name__)


class PolicyRegistry:
    """
    Central registry for managing policies.
    
    The registry maintains collections of policies by type and
    provides methods for registering, retrieving, and managing policies.
    """
    
    def __init__(self):
        """Initialize an empty policy registry."""
        # Main registry dictionary - maps policy types to collections of policies
        self._registry: Dict[str, Dict[str, IPolicy]] = {
            "client_selection": {},
            "network": {},
            "model_aggregation": {},
            "privacy": {},
            "scheduling": {}
        }
        
        # Default policies
        self._default_policies: Dict[str, str] = {}
        
        # Policy class mappings for deserialization
        self._policy_classes: Dict[str, Type[IPolicy]] = {
            "client_selection": {
                "random": RandomSelectionPolicy
            },
            "network": {
                "shortest_path": ShortestPathPolicy
            },
            "model_aggregation": {
                "fedavg": FederatedAveragingPolicy
            },
            "privacy": {
                "differential_privacy": DifferentialPrivacyPolicy
            },
            "scheduling": {
                "periodic": PeriodicSchedulingPolicy
            }
        }
    
    def register_policy(self, policy: IPolicy) -> None:
        """
        Register a policy with the registry.
        
        Args:
            policy: The policy to register
            
        Raises:
            ValueError: If the policy type is not supported
        """
        policy_type = policy.get_type()
        policy_id = policy.get_id()
        
        if policy_type not in self._registry:
            raise ValueError(f"Unsupported policy type: {policy_type}")
        
        logger.info(f"Registering {policy_type} policy: {policy_id}")
        self._registry[policy_type][policy_id] = policy
    
    def unregister_policy(self, policy_type: str, policy_id: str) -> bool:
        """
        Unregister a policy from the registry.
        
        Args:
            policy_type: Type of the policy
            policy_id: ID of the policy to unregister
            
        Returns:
            True if the policy was unregistered, False otherwise
        """
        if policy_type not in self._registry:
            logger.warning(f"Attempted to unregister policy from unknown type: {policy_type}")
            return False
        
        if policy_id not in self._registry[policy_type]:
            logger.warning(f"Attempted to unregister unknown policy: {policy_id}")
            return False
        
        # Check if this is the default policy
        if self._default_policies.get(policy_type) == policy_id:
            logger.warning(f"Unregistering default {policy_type} policy: {policy_id}")
            self._default_policies.pop(policy_type)
        
        logger.info(f"Unregistering {policy_type} policy: {policy_id}")
        self._registry[policy_type].pop(policy_id)
        return True
    
    def get_policy(self, policy_type: str, policy_id: str) -> Optional[IPolicy]:
        """
        Get a policy by type and ID.
        
        Args:
            policy_type: Type of the policy
            policy_id: ID of the policy
            
        Returns:
            The policy instance or None if not found
        """
        if policy_type not in self._registry:
            logger.warning(f"Requested policy of unknown type: {policy_type}")
            return None
        
        return self._registry[policy_type].get(policy_id)
    
    def get_policy_typed(self, policy_type: str, policy_id: str, policy_class: Type[T]) -> Optional[T]:
        """
        Get a policy by type and ID with the correct return type.
        
        Args:
            policy_type: Type of the policy
            policy_id: ID of the policy
            policy_class: Expected policy class type
            
        Returns:
            The policy instance or None if not found
        """
        policy = self.get_policy(policy_type, policy_id)
        if policy is None:
            return None
        
        if not isinstance(policy, policy_class):
            logger.warning(f"Policy {policy_id} is not of expected type {policy_class.__name__}")
            return None
        
        return policy
    
    def set_default_policy(self, policy_type: str, policy_id: str) -> bool:
        """
        Set the default policy for a specific type.
        
        Args:
            policy_type: Type of policy
            policy_id: ID of the policy to set as default
            
        Returns:
            True if successful, False otherwise
        """
        if policy_type not in self._registry:
            logger.warning(f"Attempted to set default for unknown policy type: {policy_type}")
            return False
        
        if policy_id not in self._registry[policy_type]:
            logger.warning(f"Attempted to set unknown policy as default: {policy_id}")
            return False
        
        logger.info(f"Setting default {policy_type} policy to: {policy_id}")
        self._default_policies[policy_type] = policy_id
        return True
    
    def get_default_policy(self, policy_type: str) -> Optional[IPolicy]:
        """
        Get the default policy for a specific type.
        
        Args:
            policy_type: Type of policy
            
        Returns:
            The default policy instance or None if not set
        """
        if policy_type not in self._registry:
            logger.warning(f"Requested default policy of unknown type: {policy_type}")
            return None
        
        if policy_type not in self._default_policies:
            logger.warning(f"No default policy set for type: {policy_type}")
            return None
        
        default_id = self._default_policies[policy_type]
        return self._registry[policy_type].get(default_id)
    
    def get_default_policy_typed(self, policy_type: str, policy_class: Type[T]) -> Optional[T]:
        """
        Get the default policy for a specific type with the correct return type.
        
        Args:
            policy_type: Type of policy
            policy_class: Expected policy class type
            
        Returns:
            The default policy instance or None if not set
        """
        policy = self.get_default_policy(policy_type)
        if policy is None:
            return None
        
        if not isinstance(policy, policy_class):
            logger.warning(f"Default policy for {policy_type} is not of expected type {policy_class.__name__}")
            return None
        
        return policy
    
    def list_policies(self, policy_type: str = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        List all registered policies, optionally filtered by type.
        
        Args:
            policy_type: Type of policies to list, or None for all
            
        Returns:
            Dictionary of policy information
        """
        result = {}
        
        types_to_list = [policy_type] if policy_type else self._registry.keys()
        
        for p_type in types_to_list:
            if p_type not in self._registry:
                continue
            
            result[p_type] = {}
            
            for p_id, policy in self._registry[p_type].items():
                result[p_type][p_id] = {
                    "id": p_id,
                    "type": p_type,
                    "description": policy.get_description(),
                    "is_default": self._default_policies.get(p_type) == p_id,
                    "parameters": policy.get_parameters()
                }
        
        return result
    
    def register_policy_class(self, policy_type: str, policy_subtype: str, policy_class: Type[IPolicy]) -> None:
        """
        Register a policy class for deserialization.
        
        Args:
            policy_type: Type of the policy
            policy_subtype: Subtype of the policy
            policy_class: Policy class to register
        """
        if policy_type not in self._policy_classes:
            self._policy_classes[policy_type] = {}
        
        self._policy_classes[policy_type][policy_subtype] = policy_class
    
    def create_policy_from_dict(self, data: Dict[str, Any]) -> Optional[IPolicy]:
        """
        Create a policy instance from dictionary data.
        
        Args:
            data: Dictionary containing policy data
            
        Returns:
            Policy instance or None if creation failed
        """
        policy_type = data.get('policy_type')
        if not policy_type:
            logger.error("Policy data missing 'policy_type'")
            return None
        
        policy_subtype = data.get('policy_subtype', 'default')
        
        if policy_type not in self._policy_classes:
            logger.error(f"Unknown policy type: {policy_type}")
            return None
        
        if policy_subtype not in self._policy_classes[policy_type]:
            logger.error(f"Unknown policy subtype: {policy_subtype} for type {policy_type}")
            return None
        
        policy_class = self._policy_classes[policy_type][policy_subtype]
        
        try:
            # Use the class's from_dict method to create the instance
            policy = policy_class.from_dict(data)
            return policy
        except Exception as e:
            logger.error(f"Failed to create policy from data: {e}")
            return None
    
    def initialize_default_policies(self) -> None:
        """Initialize the registry with default policies for each type."""
        # Client Selection
        random_selection = RandomSelectionPolicy(
            policy_id="default_random_selection",
            description="Default random client selection policy"
        )
        self.register_policy(random_selection)
        self.set_default_policy("client_selection", random_selection.get_id())
        
        # Network
        shortest_path = ShortestPathPolicy(
            policy_id="default_shortest_path",
            description="Default shortest path routing policy"
        )
        self.register_policy(shortest_path)
        self.set_default_policy("network", shortest_path.get_id())
        
        # Aggregation
        fedavg = FederatedAveragingPolicy(
            policy_id="default_fedavg",
            description="Default Federated Averaging aggregation policy"
        )
        self.register_policy(fedavg)
        self.set_default_policy("model_aggregation", fedavg.get_id())
        
        # Privacy
        diff_privacy = DifferentialPrivacyPolicy(
            policy_id="default_diff_privacy",
            description="Default Differential Privacy policy",
            epsilon=1.0, 
            delta=1e-5
        )
        self.register_policy(diff_privacy)
        self.set_default_policy("privacy", diff_privacy.get_id())
        
        # Scheduling
        periodic = PeriodicSchedulingPolicy(
            policy_id="default_periodic",
            description="Default Periodic Scheduling policy",
            interval_seconds=3600
        )
        self.register_policy(periodic)
        self.set_default_policy("scheduling", periodic.get_id())
        
        logger.info("Initialized default policies")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the registry to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the registry
        """
        result = {
            "default_policies": self._default_policies,
            "policies": {}
        }
        
        for policy_type, policies in self._registry.items():
            result["policies"][policy_type] = {}
            for policy_id, policy in policies.items():
                result["policies"][policy_type][policy_id] = policy.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicyRegistry':
        """
        Create a registry from a dictionary.
        
        Args:
            data: Dictionary data for the registry
            
        Returns:
            Populated PolicyRegistry instance
        """
        registry = cls()
        
        if "policies" in data:
            for policy_type, policies in data["policies"].items():
                for policy_id, policy_data in policies.items():
                    policy = registry.create_policy_from_dict(policy_data)
                    if policy:
                        registry.register_policy(policy)
        
        if "default_policies" in data:
            for policy_type, policy_id in data["default_policies"].items():
                registry.set_default_policy(policy_type, policy_id)
        
        return registry


# Singleton instance of the registry
_REGISTRY = None


def get_policy_registry() -> PolicyRegistry:
    """
    Get the global policy registry instance.
    
    Returns:
        The global PolicyRegistry instance
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PolicyRegistry()
        _REGISTRY.initialize_default_policies()
    
    return _REGISTRY 