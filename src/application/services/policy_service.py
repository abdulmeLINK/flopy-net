"""
Policy Service

This module provides services for managing and enforcing policies in the federated learning system.
"""
import logging
from typing import Dict, Any, Optional, List, Callable

from src.domain.interfaces.policy_engine import IPolicyEngine


class PolicyService:
    """
    Policy Service manages policy operations in the federated learning system.
    
    This class is responsible for:
    1. Managing policy rules and strategies
    2. Evaluating policy contexts against rules
    3. Loading and configuring policies
    """
    
    def __init__(self, 
                 policy_engine: IPolicyEngine,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the policy service.
        
        Args:
            policy_engine: Policy engine implementation
            logger: Logger instance
        """
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
    
    def start(self) -> bool:
        """
        Start the policy service.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.policy_engine.is_running():
                self.policy_engine.start()
                self.logger.info("Policy engine started")
            return True
        
        except Exception as e:
            self.logger.error(f"Error starting policy service: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the policy service.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.policy_engine.is_running():
                self.policy_engine.stop()
                self.logger.info("Policy engine stopped")
            return True
        
        except Exception as e:
            self.logger.error(f"Error stopping policy service: {e}")
            return False
    
    def register_policy(self, policy_type: str, config: Dict[str, Any] = None) -> bool:
        """
        Register a policy with the policy engine.
        
        Args:
            policy_type: Type of policy to register
            config: Optional policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Registering policy: {policy_type}")
            result = self.policy_engine.register_policy(policy_type, config or {})
            
            if result:
                self.logger.info(f"Policy {policy_type} registered successfully")
            else:
                self.logger.warning(f"Failed to register policy {policy_type}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error registering policy: {e}")
            return False
    
    def unregister_policy(self, policy_type: str) -> bool:
        """
        Unregister a policy from the policy engine.
        
        Args:
            policy_type: Type of policy to unregister
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Unregistering policy: {policy_type}")
            result = self.policy_engine.unregister_policy(policy_type)
            
            if result:
                self.logger.info(f"Policy {policy_type} unregistered successfully")
            else:
                self.logger.warning(f"Failed to unregister policy {policy_type}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error unregistering policy: {e}")
            return False
    
    def evaluate_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a policy using the provided context.
        
        Args:
            policy_type: Type of policy to evaluate
            context: Context information for evaluation
            
        Returns:
            Policy evaluation result
        """
        try:
            self.logger.debug(f"Evaluating policy: {policy_type}")
            result = self.policy_engine.evaluate_policy(policy_type, context)
            return result or {}
        
        except Exception as e:
            self.logger.error(f"Error evaluating policy: {e}")
            return {}
    
    def evaluate_all_policies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all registered policies using the provided context.
        
        Args:
            context: Context information for evaluation
            
        Returns:
            List of policy evaluation results
        """
        try:
            self.logger.debug("Evaluating all policies")
            results = self.policy_engine.evaluate_policies(context)
            return results or []
        
        except Exception as e:
            self.logger.error(f"Error evaluating policies: {e}")
            return []
    
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
        try:
            self.logger.info(f"Adding rule to policy: {policy_type}")
            result = self.policy_engine.add_rule(policy_type, condition_fn, action_fn)
            
            if result:
                self.logger.info(f"Rule added to policy {policy_type} successfully")
            else:
                self.logger.warning(f"Failed to add rule to policy {policy_type}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error adding rule: {e}")
            return False
    
    def get_policy_list(self) -> List[str]:
        """
        Get a list of registered policies.
        
        Returns:
            List of policy names
        """
        try:
            policies = self.policy_engine.get_registered_policies()
            return policies
        
        except Exception as e:
            self.logger.error(f"Error getting policy list: {e}")
            return []
    
    def get_policy_status(self, policy_type: str) -> Dict[str, Any]:
        """
        Get status information for a specific policy.
        
        Args:
            policy_type: Type of policy to get status for
            
        Returns:
            Policy status information
        """
        try:
            policy = self.policy_engine.get_policy(policy_type)
            if not policy:
                self.logger.warning(f"Policy {policy_type} not found")
                return {"name": policy_type, "registered": False}
            
            return {
                "name": policy_type,
                "registered": True,
                "active": True,
                "rules_count": len(policy.get_rules()),
                "config": policy.get_config()
            }
        
        except Exception as e:
            self.logger.error(f"Error getting policy status: {e}")
            return {"name": policy_type, "error": str(e)}
    
    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get status information for the policy engine.
        
        Returns:
            Policy engine status information
        """
        try:
            return self.policy_engine.get_status()
        
        except Exception as e:
            self.logger.error(f"Error getting policy engine status: {e}")
            return {"running": False, "error": str(e)} 