"""
Policy Engine Interface

This module defines the interface for policy engines used throughout the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IPolicyEngine(ABC):
    """
    Interface for policy engines used throughout the system.
    
    A policy engine is responsible for evaluating policies and making decisions
    based on the current context and system state.
    """
    
    @abstractmethod
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an operation is allowed by the policies.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with policy decision and metadata
        """
        pass
    
    @abstractmethod
    def add_policy(self, policy_type: str, policy_definition: Dict[str, Any]) -> str:
        """
        Add a new policy to the policy engine.
        
        Args:
            policy_type: Type of policy to add
            policy_definition: Definition of the policy
            
        Returns:
            ID of the newly added policy
        """
        pass
    
    @abstractmethod
    def remove_policy(self, policy_id: str) -> bool:
        """
        Remove a policy from the policy engine.
        
        Args:
            policy_id: ID of the policy to remove
            
        Returns:
            True if the policy was removed, False otherwise
        """
        pass
    
    @abstractmethod
    def list_policies(self) -> Dict[str, Any]:
        """
        List all policies in the policy engine.
        
        Returns:
            Dictionary mapping policy IDs to policy definitions
        """
        pass 