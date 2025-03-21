"""
Policy Engine Implementation

This module provides the core policy engine implementation that evaluates
policies and strategies for the federated learning system.
"""
import logging
import os
import json
import importlib
from typing import Dict, Any, List, Optional, Callable, Type

from src.domain.interfaces.policy import IPolicy
from src.domain.interfaces.policy_engine import IPolicyEngine


class PolicyEngine(IPolicyEngine):
    """
    Core implementation of the policy engine.
    
    This engine coordinates the evaluation of policies and strategies
    in the federated learning system.
    """
    
    def __init__(self, config: Dict[str, Any] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the policy engine.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger
        """
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.policies = {}  # Dictionary of policy_name -> policy_instance
        self.registered_callbacks = {}
        self.enabled = False
        self.active_strategy = None
        self.strategy_config = {}
        self.runtime_rules = {}  # Dictionary of rule_name -> (condition, action)
        self.policy_dirs = self.config.get("policy_dirs", ["src/application/policy/policies"])
        self.policy_registry = {}  # Registry of available policy types
        self._init_policy_registry()
    
    def _init_policy_registry(self) -> None:
        """
        Initialize the policy registry by discovering available policy types.
        This allows easier registration of policies by name.
        """
        # Load built-in policy types
        default_policies = {
            "client_selection": "src.application.policy.policies.client_selection_policy.ClientSelectionPolicy",
            "sdn": "src.application.policy.policies.sdn_policy.SDNPolicy",
            "privacy": "src.application.policy.policies.privacy_policy.PrivacyPolicy",
            "security": "src.application.policy.policies.security_policy.SecurityPolicy",
            "resource": "src.application.policy.policies.resource_policy.ResourcePolicy",
            "message_routing": "src.application.policy.policies.message_routing_policy.MessageRoutingPolicy",
            "message_delivery": "src.application.policy.policies.message_delivery_policy.MessageDeliveryPolicy",
        }
        
        for policy_name, policy_class_path in default_policies.items():
            self.policy_registry[policy_name] = policy_class_path
            
        # Try to load custom policies from policy dirs
        for policy_dir in self.policy_dirs:
            if not os.path.exists(policy_dir):
                self.logger.warning(f"Policy directory does not exist: {policy_dir}")
                continue
                
            # Look for JSON policy registry in the directory
            registry_file = os.path.join(policy_dir, "policy_registry.json")
            if os.path.exists(registry_file):
                try:
                    with open(registry_file, 'r') as f:
                        custom_registry = json.load(f)
                    
                    for policy_name, policy_class_path in custom_registry.items():
                        self.policy_registry[policy_name] = policy_class_path
                        self.logger.debug(f"Registered custom policy type: {policy_name}")
                        
                except Exception as e:
                    self.logger.error(f"Error loading policy registry from {registry_file}: {e}")
    
    def start(self) -> bool:
        """
        Start the policy engine.
        
        Returns:
            True if started successfully, False otherwise
        """
        self.enabled = True
        self.logger.info("Policy Engine started")
        return True
    
    def stop(self) -> None:
        """Stop the policy engine."""
        self.enabled = False
        self.logger.info("Policy Engine stopped")
    
    def is_running(self) -> bool:
        """
        Check if the policy engine is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.enabled
    
    def register_policy(self, policy_name: str, config: Dict[str, Any] = None) -> bool:
        """
        Register a policy with the engine.
        
        Args:
            policy_name: Name of the policy to register
            config: Optional policy configuration
            
        Returns:
            True if registered successfully, False otherwise
        """
        if policy_name in self.policies:
            self.logger.warning(f"Policy {policy_name} already registered")
            return False
        
        try:
            # Check if policy type exists in registry
            if policy_name in self.policy_registry:
                policy_class_path = self.policy_registry[policy_name]
                
                # Import the policy class
                module_path, class_name = policy_class_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                policy_class = getattr(module, class_name)
                
                # Create policy instance
                policy = policy_class(config or {})
                
            else:
                # Try to load from a default location based on name
                try:
                    # Try specific policy module
                    module_name = f"src.application.policy.policies.{policy_name}_policy"
                    class_name = f"{policy_name.title().replace('_', '')}Policy"
                    
                    module = importlib.import_module(module_name)
                    policy_class = getattr(module, class_name)
                    policy = policy_class(config or {})
                    
                except (ImportError, AttributeError) as e:
                    # Fall back to a generic policy
                    from src.domain.policy.policy_base import PolicyBase
                    policy = PolicyBase(policy_name, config or {})
            
            # Store the policy
            self.policies[policy_name] = policy
            self.logger.info(f"Registered policy: {policy_name}")
            
            # Trigger policy registration event
            self.trigger_event("policy_registered", {
                "policy_name": policy_name,
                "policy_type": type(policy).__name__
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering policy {policy_name}: {e}")
            return False
    
    def unregister_policy(self, policy_name: str) -> bool:
        """
        Unregister a policy from the engine.
        
        Args:
            policy_name: Name of the policy to unregister
            
        Returns:
            True if unregistered successfully, False otherwise
        """
        if policy_name not in self.policies:
            self.logger.warning(f"Policy {policy_name} not registered")
            return False
        
        del self.policies[policy_name]
        self.logger.info(f"Unregistered policy: {policy_name}")
        
        # Trigger policy unregistration event
        self.trigger_event("policy_unregistered", {
            "policy_name": policy_name
        })
        
        return True
    
    def evaluate_policy(self, policy_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a policy using the provided context.
        
        Args:
            policy_name: Name of the policy to evaluate
            context: Context information for evaluation
            
        Returns:
            Policy evaluation result
        """
        if not self.enabled:
            self.logger.warning("Policy engine is disabled, skipping policy evaluation")
            return {"allowed": True, "reason": "Policy engine disabled"}
        
        if policy_name not in self.policies:
            if self.config.get("auto_register_missing_policies", False):
                # Auto-register the policy if enabled
                self.register_policy(policy_name)
            else:
                self.logger.warning(f"Policy {policy_name} not registered")
                return {"allowed": True, "reason": "Policy not found"}
        
        try:
            policy = self.policies[policy_name]
            result = policy.evaluate(context)
            
            # Add policy name to result
            if isinstance(result, dict) and "policy_name" not in result:
                result["policy_name"] = policy_name
                
            self.logger.debug(f"Policy {policy_name} evaluation result: {result}")
            
            # Trigger policy evaluation event
            self.trigger_event("policy_evaluated", {
                "policy_name": policy_name,
                "context": context,
                "result": result
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error evaluating policy {policy_name}: {e}")
            return {"allowed": True, "reason": f"Policy evaluation error: {e}"}
    
    def evaluate_policies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all registered policies with the given context.
        
        Args:
            context: Context information for policy evaluation
            
        Returns:
            List of policy evaluation results
        """
        if not self.enabled:
            self.logger.warning("Policy engine is disabled, skipping policy evaluation")
            return []
        
        results = []
        for policy_name, policy in self.policies.items():
            try:
                result = policy.evaluate(context)
                
                # Add policy name to result if not present
                if isinstance(result, dict) and "policy_name" not in result:
                    result["policy_name"] = policy_name
                
                results.append(result)
                self.logger.debug(f"Policy {policy_name} result: {result}")
            except Exception as e:
                self.logger.error(f"Error evaluating policy {policy_name}: {e}")
        
        # Trigger a policy evaluation event
        self.trigger_event("policy_evaluation_completed", {
            "context": context,
            "results": results
        })
        
        return results
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: Type of event to register for
            callback: Callback function to call when event occurs
        """
        if event_type not in self.registered_callbacks:
            self.registered_callbacks[event_type] = []
        
        self.registered_callbacks[event_type].append(callback)
        self.logger.debug(f"Registered callback for event: {event_type}")
    
    def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Trigger an event, calling all registered callbacks.
        
        Args:
            event_type: Type of event to trigger
            event_data: Data for the event
        """
        if not self.enabled:
            self.logger.debug(f"Policy engine disabled, not triggering event: {event_type}")
            return
        
        if event_type in self.registered_callbacks:
            for callback in self.registered_callbacks[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    self.logger.error(f"Error in callback for event {event_type}: {e}")
        else:
            self.logger.debug(f"No callbacks registered for event: {event_type}")
    
    def get_policy(self, policy_name: str) -> Optional[IPolicy]:
        """
        Get a policy by name.
        
        Args:
            policy_name: Name of the policy to get
            
        Returns:
            Policy instance if found, None otherwise
        """
        return self.policies.get(policy_name)
    
    def get_registered_policies(self) -> List[str]:
        """
        Get a list of registered policies.
        
        Returns:
            List of policy names
        """
        return list(self.policies.keys())
    
    def get_available_policy_types(self) -> List[str]:
        """
        Get a list of available policy types.
        
        Returns:
            List of available policy type names
        """
        return list(self.policy_registry.keys())
    
    def add_rule(self, policy_name: str, rule_name: str, condition_fn: Callable[[Dict[str, Any]], bool], 
                action_fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Add a rule to a policy.
        
        Args:
            policy_name: Name of the policy to add the rule to
            rule_name: Name of the rule
            condition_fn: Function to evaluate if rule applies
            action_fn: Function to execute when rule applies
            
        Returns:
            True if successful, False otherwise
        """
        if policy_name not in self.policies:
            self.logger.warning(f"Policy {policy_name} not registered")
            return False
        
        try:
            policy = self.policies[policy_name]
            if hasattr(policy, 'add_rule'):
                policy.add_rule(rule_name, condition_fn, action_fn)
                self.logger.info(f"Added rule '{rule_name}' to policy {policy_name}")
                return True
            else:
                self.logger.warning(f"Policy {policy_name} does not support adding rules")
                return False
        except Exception as e:
            self.logger.error(f"Error adding rule to policy {policy_name}: {e}")
            return False
    
    def load_policy_from_file(self, policy_file: str) -> bool:
        """
        Load a policy from a JSON file.
        
        Args:
            policy_file: Path to the policy JSON file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(policy_file):
                self.logger.error(f"Policy file not found: {policy_file}")
                return False
            
            with open(policy_file, 'r') as f:
                policy_data = json.load(f)
            
            policy_name = policy_data.get("name")
            if not policy_name:
                self.logger.error(f"Policy file missing 'name' field: {policy_file}")
                return False
            
            # Register the policy
            config = policy_data.get("config", {})
            success = self.register_policy(policy_name, config)
            
            if not success:
                return False
            
            # Load rules if provided
            rules = policy_data.get("rules", [])
            for rule in rules:
                rule_name = rule.get("name")
                rule_condition = rule.get("condition")
                rule_action = rule.get("action")
                
                if not all([rule_name, rule_condition, rule_action]):
                    self.logger.warning(f"Skipping invalid rule in policy {policy_name}")
                    continue
                
                # Create condition and action functions
                try:
                    # For simple conditions and actions in JSON format
                    condition_fn = self._create_condition_function(rule_condition)
                    action_fn = self._create_action_function(rule_action)
                    
                    # Add the rule
                    self.add_rule(policy_name, rule_name, condition_fn, action_fn)
                    
                except Exception as e:
                    self.logger.error(f"Error creating rule '{rule_name}' for policy {policy_name}: {e}")
            
            self.logger.info(f"Loaded policy from file: {policy_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading policy from file {policy_file}: {e}")
            return False
    
    def _create_condition_function(self, condition_data: Dict[str, Any]) -> Callable[[Dict[str, Any]], bool]:
        """
        Create a condition function from condition data.
        
        Args:
            condition_data: Condition specification
            
        Returns:
            Condition function
        """
        # This is a simplified implementation that handles basic conditions
        condition_type = condition_data.get("type", "simple")
        
        if condition_type == "simple":
            field = condition_data.get("field")
            operator = condition_data.get("operator", "eq")
            value = condition_data.get("value")
            
            def condition_fn(context: Dict[str, Any]) -> bool:
                if field not in context:
                    return False
                
                context_value = context[field]
                
                if operator == "eq":
                    return context_value == value
                elif operator == "neq":
                    return context_value != value
                elif operator == "gt":
                    return context_value > value
                elif operator == "gte":
                    return context_value >= value
                elif operator == "lt":
                    return context_value < value
                elif operator == "lte":
                    return context_value <= value
                elif operator == "in":
                    return context_value in value
                elif operator == "contains":
                    return value in context_value
                else:
                    return False
            
            return condition_fn
        
        elif condition_type == "and":
            subconditions = [self._create_condition_function(c) for c in condition_data.get("conditions", [])]
            
            def and_condition_fn(context: Dict[str, Any]) -> bool:
                return all(c(context) for c in subconditions)
            
            return and_condition_fn
        
        elif condition_type == "or":
            subconditions = [self._create_condition_function(c) for c in condition_data.get("conditions", [])]
            
            def or_condition_fn(context: Dict[str, Any]) -> bool:
                return any(c(context) for c in subconditions)
            
            return or_condition_fn
        
        elif condition_type == "not":
            subcondition = self._create_condition_function(condition_data.get("condition", {}))
            
            def not_condition_fn(context: Dict[str, Any]) -> bool:
                return not subcondition(context)
            
            return not_condition_fn
        
        else:
            # Default to always true for unknown condition types
            return lambda context: True
    
    def _create_action_function(self, action_data: Dict[str, Any]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """
        Create an action function from action data.
        
        Args:
            action_data: Action specification
            
        Returns:
            Action function
        """
        # This is a simplified implementation that handles basic actions
        action_type = action_data.get("type", "allow")
        
        if action_type == "allow":
            reason = action_data.get("reason", "Allowed by policy")
            
            def allow_action_fn(context: Dict[str, Any]) -> Dict[str, Any]:
                return {"allowed": True, "reason": reason}
            
            return allow_action_fn
        
        elif action_type == "deny":
            reason = action_data.get("reason", "Denied by policy")
            
            def deny_action_fn(context: Dict[str, Any]) -> Dict[str, Any]:
                return {"allowed": False, "reason": reason}
            
            return deny_action_fn
        
        elif action_type == "modify":
            modifications = action_data.get("modifications", {})
            
            def modify_action_fn(context: Dict[str, Any]) -> Dict[str, Any]:
                result = {"allowed": True}
                for key, value in modifications.items():
                    result[key] = value
                return result
            
            return modify_action_fn
        
        else:
            # Default to allow for unknown action types
            return lambda context: {"allowed": True, "reason": "Default action"}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the policy engine.
        
        Returns:
            Dictionary containing the engine status
        """
        return {
            "enabled": self.enabled,
            "registered_policies": self.get_registered_policies(),
            "available_policy_types": self.get_available_policy_types(),
            "active_strategy": self.active_strategy,
            "event_types": list(self.registered_callbacks.keys())
        }

    def set_strategy(self, strategy_name: str, strategy_config: Dict[str, Any] = None) -> bool:
        """
        Set the active federated learning strategy.
        
        Args:
            strategy_name: Name of the strategy to set
            strategy_config: Configuration for the strategy
            
        Returns:
            True if strategy was set successfully, False otherwise
        """
        # Import strategy registry dynamically to avoid circular imports
        try:
            from src.application.fl_strategies.registry import strategy_registry
            
            if strategy_name in strategy_registry:
                self.active_strategy = strategy_name
                self.strategy_config = strategy_config or {}
                
                # Trigger a strategy change event
                self.trigger_event("strategy_changed", {
                    "strategy_name": strategy_name,
                    "strategy_config": self.strategy_config
                })
                
                self.logger.info(f"Active strategy set to: {strategy_name}")
                return True
            else:
                self.logger.error(f"Unknown strategy: {strategy_name}")
                return False
        except ImportError as e:
            self.logger.error(f"Error importing strategy registry: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error setting strategy {strategy_name}: {e}")
            return False
    
    def get_active_strategy(self) -> Optional[str]:
        """
        Get the name of the currently active strategy.
        
        Returns:
            Name of the active strategy, or None if no strategy is active
        """
        return self.active_strategy
    
    def add_runtime_rule(self, rule_name: str, rule_condition: Callable[[Dict[str, Any]], bool], 
                        rule_action: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Add a runtime rule to the policy engine.
        
        Args:
            rule_name: Name of the rule to add
            rule_condition: Function that determines when the rule should be applied
            rule_action: Function that performs the rule's action when the condition is met
            
        Returns:
            True if rule was added successfully, False otherwise
        """
        try:
            if rule_name in self.runtime_rules:
                self.logger.warning(f"Overwriting existing runtime rule: {rule_name}")
                
            self.runtime_rules[rule_name] = (rule_condition, rule_action)
            self.logger.info(f"Added runtime rule: {rule_name}")
            
            # Trigger a rule added event
            self.trigger_event("runtime_rule_added", {
                "rule_name": rule_name
            })
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding runtime rule {rule_name}: {e}")
            return False
    
    def remove_runtime_rule(self, rule_name: str) -> bool:
        """
        Remove a runtime rule from the policy engine.
        
        Args:
            rule_name: Name of the rule to remove
            
        Returns:
            True if rule was removed successfully, False otherwise
        """
        if rule_name in self.runtime_rules:
            del self.runtime_rules[rule_name]
            self.logger.info(f"Removed runtime rule: {rule_name}")
            
            # Trigger a rule removed event
            self.trigger_event("runtime_rule_removed", {
                "rule_name": rule_name
            })
            
            return True
        else:
            self.logger.warning(f"Runtime rule not found: {rule_name}")
            return False
    
    def enforce_runtime_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce all applicable runtime rules on the given context.
        
        Args:
            context: Context information for rule enforcement
            
        Returns:
            Modified context after rule enforcement
        """
        if not self.enabled:
            self.logger.warning("Policy engine is disabled, skipping runtime rule enforcement")
            return context
        
        modified_context = context.copy()
        applied_rules = []
        
        for rule_name, (condition, action) in self.runtime_rules.items():
            try:
                if condition(modified_context):
                    # Rule condition matches, apply the action
                    result = action(modified_context)
                    if isinstance(result, dict):
                        modified_context = result
                        applied_rules.append(rule_name)
                        self.logger.debug(f"Applied runtime rule: {rule_name}")
            except Exception as e:
                self.logger.error(f"Error enforcing runtime rule {rule_name}: {e}")
        
        if applied_rules:
            # Trigger a rules enforced event
            self.trigger_event("runtime_rules_enforced", {
                "original_context": context,
                "modified_context": modified_context,
                "applied_rules": applied_rules
            })
            
            self.logger.info(f"Applied {len(applied_rules)} runtime rules: {', '.join(applied_rules)}")
        
        return modified_context 