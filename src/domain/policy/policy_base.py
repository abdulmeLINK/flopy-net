"""
Policy Base Class

This module provides the base class for policies in the federated learning system.
"""
import logging
from typing import Dict, Any, List, Callable, Optional, Tuple


class PolicyBase:
    """
    Base class for policies in the federated learning system.
    
    This class provides common functionality for all policy implementations.
    """
    
    def __init__(self, policy_type: str, config: Dict[str, Any] = None):
        """
        Initialize the policy.
        
        Args:
            policy_type: Type of policy
            config: Optional policy configuration
        """
        self.policy_type = policy_type
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{policy_type}")
        self.rules = []  # List of (condition, action) tuples
    
    def add_rule(self, condition_fn: Callable[[Dict[str, Any]], bool], 
                 action_fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Add a rule to the policy.
        
        Args:
            condition_fn: Function to evaluate if rule applies
            action_fn: Function to execute when rule applies
        """
        self.rules.append((condition_fn, action_fn))
        self.logger.debug(f"Added rule to policy {self.policy_type}")
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy with the given context.
        
        Args:
            context: Context information for evaluation
            
        Returns:
            Policy evaluation result
        """
        self.logger.debug(f"Evaluating policy {self.policy_type}")
        
        # Start with default allow result
        result = {
            "policy_type": self.policy_type,
            "decision": "allow",
            "action_taken": False,
            "modified_context": context.copy()
        }
        
        # Apply each rule in order
        for i, (condition_fn, action_fn) in enumerate(self.rules):
            try:
                # Check if rule condition applies
                if condition_fn(context):
                    self.logger.debug(f"Rule {i} condition met for policy {self.policy_type}")
                    
                    # Apply rule action
                    action_result = action_fn(result["modified_context"])
                    
                    # Update result
                    if isinstance(action_result, dict):
                        # If action returned a dict, update the modified context
                        result["modified_context"].update(action_result)
                        
                        # Check if action specified a decision
                        if "decision" in action_result:
                            result["decision"] = action_result["decision"]
                        
                        # Mark that an action was taken
                        result["action_taken"] = True
                        
                        # Record which rule was applied
                        result["applied_rule"] = i
                        
                        self.logger.debug(f"Applied rule {i} action for policy {self.policy_type}")
                    
                    # Check if we should stop evaluating rules
                    if result["decision"] == "deny":
                        self.logger.info(f"Policy {self.policy_type} evaluation resulted in deny")
                        break
            
            except Exception as e:
                self.logger.error(f"Error evaluating rule {i} for policy {self.policy_type}: {e}")
                # Continue with next rule
        
        return result
    
    def get_rules(self) -> List[Tuple[Callable, Callable]]:
        """
        Get the list of rules for this policy.
        
        Returns:
            List of (condition, action) tuples
        """
        return self.rules
    
    def clear_rules(self) -> None:
        """Clear all rules from this policy."""
        self.rules = []
        self.logger.debug(f"Cleared all rules from policy {self.policy_type}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the policy configuration.
        
        Returns:
            Policy configuration dictionary
        """
        return self.config 