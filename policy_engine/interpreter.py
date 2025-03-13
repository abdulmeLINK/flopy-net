import logging
import operator
from typing import Any, Dict, List, Optional, Union, Callable

from .models import Policy, Condition, Action

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported operators for condition evaluation
OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "contains": lambda a, b: b in a,
    "startswith": lambda a, b: str(a).startswith(str(b)),
    "endswith": lambda a, b: str(a).endswith(str(b)),
}


class PolicyInterpreter:
    """Interprets and executes policies based on runtime data."""
    
    def __init__(self):
        self.action_handlers = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default action handlers."""
        # No default handlers - these should be registered by consumers
        pass
    
    def register_action_handler(self, action_type: str, handler: Callable):
        """Register a handler for a specific action type."""
        self.action_handlers[action_type] = handler
        logger.info(f"Registered handler for action type: {action_type}")
    
    def _evaluate_condition(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition against the provided context."""
        if condition.field not in context:
            logger.warning(f"Field {condition.field} not found in context")
            return False
        
        if condition.operator not in OPERATORS:
            logger.warning(f"Unsupported operator: {condition.operator}")
            return False
        
        field_value = context[condition.field]
        op_func = OPERATORS[condition.operator]
        
        try:
            return op_func(field_value, condition.value)
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def evaluate_policy(self, policy: Policy, context: Dict[str, Any]) -> bool:
        """
        Evaluate if a policy should be applied based on its conditions and context.
        
        Args:
            policy: The policy to evaluate
            context: Dictionary containing runtime data for evaluation
        
        Returns:
            bool: True if policy conditions are met, False otherwise
        """
        if not policy.enabled:
            return False
        
        # If no conditions, policy is always applicable
        if not policy.conditions:
            return True
        
        # All conditions must be met (AND logic)
        for condition in policy.conditions:
            if not self._evaluate_condition(condition, context):
                return False
        
        return True
    
    def execute_action(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a policy action.
        
        Args:
            action: The action to execute
            context: Dictionary containing runtime data
        
        Returns:
            Dict: Result of the action execution
        """
        if action.type not in self.action_handlers:
            logger.warning(f"No handler registered for action type: {action.type}")
            return {"success": False, "error": f"Unsupported action type: {action.type}"}
        
        handler = self.action_handlers[action.type]
        
        try:
            result = handler(action.target, action.parameters, context)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {"success": False, "error": str(e)}
    
    def apply_policy(self, policy: Policy, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate and apply a policy if conditions are met.
        
        Args:
            policy: The policy to apply
            context: Dictionary containing runtime data
        
        Returns:
            List[Dict]: Results of action executions
        """
        if not self.evaluate_policy(policy, context):
            logger.info(f"Policy {policy.policy_id} conditions not met")
            return []
        
        logger.info(f"Applying policy: {policy.policy_id} - {policy.name}")
        
        results = []
        for action in policy.actions:
            result = self.execute_action(action, context)
            results.append(result)
            
            # Stop processing actions if one fails (unless we want to continue)
            if not result["success"]:
                logger.warning(f"Action {action.type}:{action.target} failed, stopping policy execution")
                break
        
        return results
    
    def apply_policies(self, policies: List[Policy], context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply multiple policies to a given context.
        
        Args:
            policies: List of policies to apply
            context: Dictionary containing runtime data
        
        Returns:
            Dict: Map of policy IDs to their execution results
        """
        # Sort policies by priority (higher numbers = higher priority)
        sorted_policies = sorted(policies, key=lambda p: p.priority, reverse=True)
        
        results = {}
        for policy in sorted_policies:
            policy_results = self.apply_policy(policy, context)
            if policy_results:  # Only add to results if actions were taken
                results[policy.policy_id] = policy_results
        
        return results


# Singleton instance for easy import
interpreter = PolicyInterpreter() 