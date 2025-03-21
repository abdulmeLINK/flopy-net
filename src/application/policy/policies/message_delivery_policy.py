"""
Message Delivery Policy

This module provides a policy for controlling message delivery to specific components
in the federated learning system.
"""
import logging
import time
from typing import Dict, Any, List, Optional

from src.domain.interfaces.policy import IPolicy


class MessageDeliveryPolicy(IPolicy):
    """
    Message Delivery Policy implementation.
    
    This policy enforces rules for delivering messages to specific components.
    It ensures that components only receive messages they are authorized to process
    and respects rate limiting and timing constraints.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the message delivery policy.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.name = "message_delivery"
        self.rules = {}
        self.description = "Enforces rules for message delivery to components"
        self.delivery_stats = {}
        self.initialize_rules()
    
    def initialize_rules(self) -> None:
        """Initialize default delivery rules."""
        self.rules = {
            "rate_limits": self.config.get("rate_limits", {
                # Default rate limits for different message types (messages per minute)
                "model_update": 10,
                "aggregated_model": 5,
                "heartbeat": 30,
                "status_update": 20
            }),
            "component_subscriptions": self.config.get("component_subscriptions", {
                # Default subscriptions for different component types
                "fl_client": ["model_distribution", "aggregated_model", "client_selection"],
                "fl_server": ["model_update", "heartbeat", "status_update"],
                "sdn_controller": ["network_stats", "topology_update", "flow_stats"],
                "policy_engine": ["*"]  # Policy engine can receive all message types
            }),
            "delivery_hours": self.config.get("delivery_hours", {
                # Restricting delivery times for certain message types (24h format)
                "model_distribution": {"start": 0, "end": 24},  # Always allowed
                "system_maintenance": {"start": 22, "end": 4}  # Only during off-hours
            }),
            "priorities": self.config.get("priorities", {
                "high": ["model_distribution", "model_update", "aggregated_model"],
                "medium": ["client_selection", "network_stats"],
                "low": ["heartbeat", "status_update"]
            })
        }
        
        self.logger.info("Initialized message delivery policy")
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate if a message can be delivered based on the context.
        
        Args:
            context: Evaluation context containing message delivery information
            
        Returns:
            Dictionary with evaluation results (allowed, reason, etc.)
        """
        source_component = context.get("source_component")
        target_component = context.get("target_component")
        message_type = context.get("message_type", "unknown")
        timestamp = context.get("timestamp", time.time())
        
        # Log the delivery evaluation
        self.logger.debug(f"Evaluating message delivery: {source_component} -> {target_component} ({message_type})")
        
        # Initialize stats for this component if not present
        if target_component not in self.delivery_stats:
            self.delivery_stats[target_component] = {
                "last_delivery_time": {},
                "delivery_count": {}
            }
        
        # Check if the target component subscribes to this message type
        if not self._check_subscription(target_component, message_type):
            return {
                "allowed": False,
                "reason": f"Component {target_component} does not subscribe to {message_type} messages"
            }
        
        # Check rate limits
        rate_limit_check = self._check_rate_limits(target_component, message_type, timestamp)
        if not rate_limit_check.get("allowed", True):
            return rate_limit_check
        
        # Check delivery hours
        hours_check = self._check_delivery_hours(message_type, timestamp)
        if not hours_check.get("allowed", True):
            return hours_check
        
        # Update delivery stats
        component_stats = self.delivery_stats[target_component]
        if message_type not in component_stats["last_delivery_time"]:
            component_stats["last_delivery_time"][message_type] = timestamp
            component_stats["delivery_count"][message_type] = 1
        else:
            component_stats["last_delivery_time"][message_type] = timestamp
            component_stats["delivery_count"][message_type] += 1
        
        # Determine message priority
        priority = "normal"
        for p, msg_types in self.rules["priorities"].items():
            if message_type in msg_types:
                priority = p
                break
        
        # If all checks pass, allow delivery with priority information
        return {
            "allowed": True,
            "reason": f"Message delivery allowed to {target_component}",
            "priority": priority
        }
    
    def _check_subscription(self, target_component: str, message_type: str) -> bool:
        """
        Check if the target component subscribes to the message type.
        
        Args:
            target_component: Target component identifier
            message_type: Type of message
            
        Returns:
            True if subscribed, False otherwise
        """
        # Handle wildcards and component type patterns
        component_type = None
        for ctype in ["fl_client", "fl_server", "sdn_controller", "policy_engine"]:
            if target_component.startswith(ctype):
                component_type = ctype
                break
        
        # Use exact component name first
        subscriptions = self.rules["component_subscriptions"].get(target_component, [])
        
        # If no exact match, use component type
        if not subscriptions and component_type:
            subscriptions = self.rules["component_subscriptions"].get(component_type, [])
        
        # Check if the component subscribes to this message type
        return message_type in subscriptions or "*" in subscriptions
    
    def _check_rate_limits(self, target_component: str, message_type: str, timestamp: float) -> Dict[str, Any]:
        """
        Check rate limits for message delivery.
        
        Args:
            target_component: Target component identifier
            message_type: Type of message
            timestamp: Current timestamp
            
        Returns:
            Dictionary with check results
        """
        # Get the rate limit for this message type
        rate_limit = self.rules["rate_limits"].get(message_type)
        if not rate_limit:
            # No rate limit defined for this message type
            return {"allowed": True}
        
        # Get stats for this component
        component_stats = self.delivery_stats.get(target_component, {"last_delivery_time": {}, "delivery_count": {}})
        last_delivery = component_stats["last_delivery_time"].get(message_type, 0)
        count = component_stats["delivery_count"].get(message_type, 0)
        
        # Calculate time since last delivery
        time_diff_minutes = (timestamp - last_delivery) / 60
        
        # If it's been more than a minute, reset the count
        if time_diff_minutes >= 1:
            count = 0
        
        # Check if we're over the limit
        if count >= rate_limit:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded for {message_type} to {target_component}",
                "retry_after": int(60 - (time_diff_minutes * 60))  # Seconds until next allowed delivery
            }
        
        return {"allowed": True}
    
    def _check_delivery_hours(self, message_type: str, timestamp: float) -> Dict[str, Any]:
        """
        Check if the message can be delivered at the current time.
        
        Args:
            message_type: Type of message
            timestamp: Current timestamp
            
        Returns:
            Dictionary with check results
        """
        # Get delivery hours for this message type
        hours = self.rules["delivery_hours"].get(message_type)
        if not hours:
            # No time restrictions for this message type
            return {"allowed": True}
        
        # Get current hour
        current_time = time.localtime(timestamp)
        current_hour = current_time.tm_hour
        
        # Check if current hour is within allowed range
        start_hour = hours["start"]
        end_hour = hours["end"]
        
        # Handle ranges that span midnight
        if start_hour > end_hour:
            is_allowed = current_hour >= start_hour or current_hour < end_hour
        else:
            is_allowed = start_hour <= current_hour < end_hour
        
        if not is_allowed:
            return {
                "allowed": False,
                "reason": f"Message type {message_type} cannot be delivered at this time",
                "allowed_hours": f"{start_hour}:00 - {end_hour}:00"
            }
        
        return {"allowed": True}
    
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
        self.logger.info(f"Added custom rule to message delivery policy: {rule_name}")
    
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