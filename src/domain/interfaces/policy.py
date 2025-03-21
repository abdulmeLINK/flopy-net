"""
Policy Interface

This module defines the interface for policies that can be evaluated
by the policy engine.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class IPolicy(ABC):
    """Interface defining the contract for policies."""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the policy.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy with the given context.
        
        Args:
            context: Context information for policy evaluation
            
        Returns:
            Policy evaluation result
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the policy name.
        
        Returns:
            Policy name
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get the policy description.
        
        Returns:
            Policy description
        """
        pass 