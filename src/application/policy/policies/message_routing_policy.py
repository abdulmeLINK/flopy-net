"""
Message Routing Policy

This module provides a policy for controlling message routing between components
in the federated learning system.
"""
import logging
from typing import Dict, Any, List, Optional

from src.domain.interfaces.policy import IPolicy


class MessageRoutingPolicy(IPolicy):
    """
    Message Routing Policy implementation.
    
    This policy enforces rules for message routing between components.
    It helps ensure that messages are only routed between authorized components
    and that sensitive messages comply with security policies.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the message routing policy.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.name = "message_routing"
        self.rules = {}
        self.description = "Enforces rules for message routing between components"
        self.initialize_rules()
    
    def initialize_rules(self) -> None:
        """Initialize default routing rules."""
        self.rules = {
            "allowed_component_pairs": self.config.get("allowed_component_pairs", [
                # Default component pairs that can communicate with each other
                {"source": "fl_server", "target": "fl_client"},
                {"source": "fl_client", "target": "fl_server"},
                {"source": "fl_server", "target": "sdn_controller"},
                {"source": "sdn_controller", "target": "fl_server"},
                {"source": "fl_client", "target": "policy_engine"},
                {"source": "fl_server", "target": "policy_engine"},
                {"source": "sdn_controller", "target": "policy_engine"},
            ]),
            "restricted_messages": self.config.get("restricted_messages", [
                # Messages that have special routing rules
                "model_update",
                "aggregated_model",
                "client_selection"
            ]),
            "blocked_patterns": self.config.get("blocked_patterns", []),
            "message_priorities": self.config.get("message_priorities", {
                "model_distribution": "high",
                "model_update": "high",
                "aggregated_model": "high",
                "heartbeat": "low",
                "status_update": "low",
                "client_selection": "medium"
            })
        }
        
        self.logger.info("Initialized message routing policy")
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate if a message can be routed based on the context.
        
        Args:
            context: Evaluation context containing message routing information
            
        Returns:
            Dictionary with evaluation results (allowed, reason, etc.)
        """
        source_component = context.get("source_component")
        target_component = context.get("target_component")
        message_type = context.get("message_type", "unknown")
        
        # Log the routing request
        self.logger.debug(f"Evaluating message routing: {source_component} -> {target_component} ({message_type})")
        
        # If target is not specified, assume broadcast which has different rules
        if not target_component:
            return self._evaluate_broadcast(context)
        
        # Check if source and target are allowed to communicate
        if not self._check_component_pair(source_component, target_component):
            return {
                "allowed": False,
                "reason": f"Communication between {source_component} and {target_component} is not allowed by policy"
            }
        
        # Check if message type is restricted
        if message_type in self.rules["restricted_messages"]:
            # Apply special rules for restricted messages
            result = self._evaluate_restricted_message(context)
            if not result.get("allowed", True):
                return result
        
        # Check for blocked patterns in message content
        # (This would require more context about the message payload)
        
        # If all checks pass, allow the message with its priority
        priority = self.rules["message_priorities"].get(message_type, "normal")
        return {
            "allowed": True,
            "reason": "Message routing allowed by policy",
            "priority": priority
        }
    
    def _evaluate_broadcast(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate broadcast message routing.
        
        Args:
            context: Context information
            
        Returns:
            Evaluation result
        """
        source_component = context.get("source_component")
        message_type = context.get("message_type", "unknown")
        
        # Check if the source is allowed to broadcast
        allowed_to_broadcast = source_component in ["fl_server", "policy_engine", "sdn_controller"]
        if not allowed_to_broadcast:
            return {
                "allowed": False,
                "reason": f"Component {source_component} is not allowed to broadcast messages"
            }
        
        # Check specific broadcast restrictions
        if message_type == "model_update" and source_component != "fl_server":
            return {
                "allowed": False,
                "reason": "Only FL server can broadcast model updates"
            }
        
        # If all checks pass
        return {
            "allowed": True,
            "reason": "Broadcast allowed by policy",
            "priority": self.rules["message_priorities"].get(message_type, "normal")
        }
    
    def _check_component_pair(self, source: str, target: str) -> bool:
        """
        Check if the source and target components are allowed to communicate.
        
        Args:
            source: Source component identifier
            target: Target component identifier
            
        Returns:
            True if communication is allowed, False otherwise
        """
        # Special case: policy engine can communicate with anyone
        if source == "policy_engine" or target == "policy_engine":
            return True
        
        # Check allowed component pairs
        for pair in self.rules["allowed_component_pairs"]:
            if pair["source"] == source and pair["target"] == target:
                return True
            # If wildcards are supported
            if pair.get("source", "") == "*" and pair.get("target", "") == target:
                return True
            if pair.get("source", "") == source and pair.get("target", "") == "*":
                return True
        
        return False
    
    def _evaluate_restricted_message(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply special rules for restricted message types.
        
        Args:
            context: Context information
            
        Returns:
            Evaluation result
        """
        source_component = context.get("source_component")
        target_component = context.get("target_component")
        message_type = context.get("message_type")
        
        # Special rules for model updates
        if message_type == "model_update":
            # Only FL clients can send model updates to FL server
            if not (source_component.startswith("fl_client") and target_component == "fl_server"):
                return {
                    "allowed": False,
                    "reason": "Model updates must be sent from FL clients to FL server"
                }
        
        # Special rules for aggregated models
        elif message_type == "aggregated_model":
            # Only FL server can send aggregated models
            if source_component != "fl_server":
                return {
                    "allowed": False,
                    "reason": "Only FL server can send aggregated models"
                }
        
        # Special rules for client selection
        elif message_type == "client_selection":
            # Only FL server can perform client selection
            if source_component != "fl_server":
                return {
                    "allowed": False,
                    "reason": "Only FL server can perform client selection"
                }
        
        # If no violations, allow the message
        return {
            "allowed": True,
            "reason": "Restricted message allowed by policy",
            "priority": self.rules["message_priorities"].get(message_type, "high")
        }
    
    def add_rule(self, rule_name: str, condition_fn: callable, action_fn: callable) -> None:
        """
        Add a custom rule to the policy.
        
        Args:
            rule_name: Name of the rule
            condition_fn: Function that evaluates if the rule applies
            action_fn: Function that defines the action when the rule applies
        """
        self.rules[rule_name] = {
            "condition": condition_fn,
            "action": action_fn
        }
        self.logger.info(f"Added custom rule to message routing policy: {rule_name}")
        
    def get_name(self) -> str:
        """
        Get the policy name.
        
        Returns:
            Policy name
        """
        return self.name
    
    def get_description(self) -> str:
        """
        Get the policy description.
        
        Returns:
            Policy description
        """
        return self.description 