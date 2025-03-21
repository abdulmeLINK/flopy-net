"""
Rule-Based Policy Engine

This module provides an implementation of a rule-based policy engine for the federated learning system.
"""
import logging
from typing import Dict, Any, List, Callable, Optional, Type

from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.policy.policy_base import PolicyBase


class RuleBasedPolicyEngine(IPolicyEngine):
    """
    Rule-based implementation of the policy engine.
    
    This implementation evaluates policies based on rule conditions and actions.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the rule-based policy engine.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.policies = {}
        self.stats = {
            "evaluations": 0,
            "actions_taken": 0
        }
    
    def start(self) -> bool:
        """
        Start the policy engine.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Starting rule-based policy engine")
        self.running = True
        return True
    
    def stop(self) -> bool:
        """
        Stop the policy engine.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Stopping rule-based policy engine")
        self.running = False
        return True
    
    def is_running(self) -> bool:
        """
        Check if the policy engine is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.running
    
    def register_policy(self, policy_type: str, config: Dict[str, Any] = None) -> bool:
        """
        Register a policy with the engine.
        
        Args:
            policy_type: Type of policy to register
            config: Optional policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create policy instance
            if policy_type == "security":
                from src.domain.policy.security_policy import SecurityPolicy
                policy = SecurityPolicy(config or {})
            elif policy_type == "resource":
                from src.domain.policy.resource_policy import ResourcePolicy
                policy = ResourcePolicy(config or {})
            elif policy_type == "privacy":
                from src.domain.policy.privacy_policy import PrivacyPolicy
                policy = PrivacyPolicy(config or {})
            elif policy_type == "custom":
                from src.domain.policy.custom_policy import CustomPolicy
                policy = CustomPolicy(config or {})
            else:
                # Default to base policy
                policy = PolicyBase(policy_type, config or {})
            
            # Store policy
            self.policies[policy_type] = policy
            self.logger.info(f"Registered policy: {policy_type}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error registering policy {policy_type}: {e}")
            return False
    
    def unregister_policy(self, policy_type: str) -> bool:
        """
        Unregister a policy from the engine.
        
        Args:
            policy_type: Type of policy to unregister
            
        Returns:
            True if successful, False otherwise
        """
        if policy_type not in self.policies:
            self.logger.warning(f"Policy {policy_type} not registered")
            return False
        
        del self.policies[policy_type]
        self.logger.info(f"Unregistered policy: {policy_type}")
        return True
    
    def evaluate_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a policy using the provided context.
        
        Args:
            policy_type: Type of policy to evaluate
            context: Context information for evaluation
            
        Returns:
            Policy evaluation result
        """
        if not self.running:
            self.logger.warning("Policy engine not running")
            return {"error": "Engine not running"}
        
        if policy_type not in self.policies:
            self.logger.warning(f"Policy {policy_type} not found")
            return {"error": f"Policy {policy_type} not found"}
        
        try:
            # Track evaluation
            self.stats["evaluations"] += 1
            
            # Get policy
            policy = self.policies[policy_type]
            
            # Evaluate policy
            result = policy.evaluate(context)
            
            # Track actions
            if result.get("action_taken", False):
                self.stats["actions_taken"] += 1
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error evaluating policy {policy_type}: {e}")
            return {"error": str(e)}
    
    def evaluate_policies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all registered policies using the provided context.
        
        Args:
            context: Context information for evaluation
            
        Returns:
            List of policy evaluation results
        """
        if not self.running:
            self.logger.warning("Policy engine not running")
            return [{"error": "Engine not running"}]
        
        results = []
        
        for policy_type in self.policies:
            result = self.evaluate_policy(policy_type, context)
            result["policy_type"] = policy_type
            results.append(result)
        
        return results
    
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
        if policy_type not in self.policies:
            self.logger.warning(f"Policy {policy_type} not found")
            return False
        
        try:
            policy = self.policies[policy_type]
            policy.add_rule(condition_fn, action_fn)
            self.logger.info(f"Added rule to policy {policy_type}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error adding rule to policy {policy_type}: {e}")
            return False
    
    def get_registered_policies(self) -> List[str]:
        """
        Get a list of registered policies.
        
        Returns:
            List of policy names
        """
        return list(self.policies.keys())
    
    def get_policy(self, policy_type: str) -> Optional[PolicyBase]:
        """
        Get a policy by its type.
        
        Args:
            policy_type: Type of policy to get
            
        Returns:
            Policy object or None if not found
        """
        return self.policies.get(policy_type)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the policy engine.
        
        Returns:
            Dictionary containing status information
        """
        return {
            "running": self.running,
            "policy_count": len(self.policies),
            "registered_policies": list(self.policies.keys()),
            "stats": self.stats
        } 