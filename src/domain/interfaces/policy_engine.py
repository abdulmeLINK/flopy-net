"""
Policy Engine Interface

This module defines the interface for policy engines in the federated learning system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional


class IPolicyEngine(ABC):
    """
    Interface for policy engines in the federated learning system.
    
    A policy engine is responsible for:
    1. Managing and enforcing policies
    2. Evaluating contexts against policy rules
    3. Handling policy decisions
    """
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the policy engine.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the policy engine.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the policy engine is running.
        
        Returns:
            True if running, False otherwise
        """
        pass
    
    @abstractmethod
    def register_policy(self, policy_type: str, config: Dict[str, Any] = None) -> bool:
        """
        Register a policy with the engine.
        
        Args:
            policy_type: Type of policy to register
            config: Optional policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def unregister_policy(self, policy_type: str) -> bool:
        """
        Unregister a policy from the engine.
        
        Args:
            policy_type: Type of policy to unregister
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def evaluate_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a policy using the provided context.
        
        Args:
            policy_type: Type of policy to evaluate
            context: Context information for evaluation
            
        Returns:
            Policy evaluation result
        """
        pass
    
    @abstractmethod
    def evaluate_policies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all registered policies using the provided context.
        
        Args:
            context: Context information for evaluation
            
        Returns:
            List of policy evaluation results
        """
        pass
    
    @abstractmethod
    def add_rule(self, policy_type: str, condition_fn: Callable[[Dict[str, Any]], bool], 
                 action_fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Add a rule to a policy.
        
        Args:
            policy_type: Type of policy to add the rule to
            condition_fn: Function to evaluate if rule applies
            action_fn: Function to execute when rule applies
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_registered_policies(self) -> List[str]:
        """
        Get a list of registered policies.
        
        Returns:
            List of policy names
        """
        pass
    
    @abstractmethod
    def get_policy(self, policy_type: str) -> Any:
        """
        Get a policy by its type.
        
        Args:
            policy_type: Type of policy to get
            
        Returns:
            Policy object or None if not found
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the policy engine.
        
        Returns:
            Dictionary containing status information
        """
        pass 