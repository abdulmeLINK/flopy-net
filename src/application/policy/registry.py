"""
Policy Registry

This module maintains a registry of all available policies that can be
used by the policy engine.
"""
from typing import Dict, Type, Any

from src.domain.interfaces.policy import IPolicy
from src.application.policy.strategies.client_selection_policy import ClientSelectionPolicy
from src.application.policy.strategies.simulation_policy import SimulationPolicy
from src.application.policy.strategies.sdn_policy import SDNPolicy

# abdulmelik beni de sikiyo kıskan orospu proje

# Registry of all available policies
policy_registry: Dict[str, Type[IPolicy]] = {
    "client_selection": ClientSelectionPolicy,
    "simulation": SimulationPolicy,
    "sdn": SDNPolicy
}


def register_policy(policy_name: str, policy_class: Type[IPolicy]) -> None:
    """
    Register a policy in the registry.
    
    Args:
        policy_name: Name of the policy
        policy_class: Policy class
    """
    policy_registry[policy_name] = policy_class


def unregister_policy(policy_name: str) -> bool:
    """
    Unregister a policy from the registry.
    
    Args:
        policy_name: Name of the policy to unregister
        
    Returns:
        True if policy was unregistered, False if policy was not found
    """
    if policy_name in policy_registry:
        del policy_registry[policy_name]
        return True
    return False


def get_policy_class(policy_name: str) -> Type[IPolicy]:
    """
    Get a policy class by name.
    
    Args:
        policy_name: Name of the policy to get
        
    Returns:
        Policy class if found
        
    Raises:
        KeyError: If policy is not found
    """
    if policy_name not in policy_registry:
        raise KeyError(f"Policy not found: {policy_name}")
    
    return policy_registry[policy_name]


def create_policy(policy_name: str, **kwargs) -> IPolicy:
    """
    Create a policy instance by name.
    
    Args:
        policy_name: Name of the policy to create
        **kwargs: Arguments to pass to the policy constructor
        
    Returns:
        Policy instance
        
    Raises:
        KeyError: If policy is not found
    """
    policy_class = get_policy_class(policy_name)
    return policy_class(**kwargs)


def list_available_policies() -> Dict[str, str]:
    """
    List all available policies and their descriptions.
    
    Returns:
        Dictionary mapping policy names to descriptions
    """
    return {
        name: policy_class().__class__.__doc__ or "No description available"
        for name, policy_class in policy_registry.items()
    } 