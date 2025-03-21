"""
Policy Message Broker Service

This module provides a message broker service that integrates with the policy engine
to facilitate communication between components in the federated learning system.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Callable

from src.domain.interfaces.policy_engine import IPolicyEngine


class PolicyMessageBroker:
    """
    Policy Message Broker Service
    
    This service:
    1. Acts as a central message broker for all components
    2. Integrates with the policy engine to enforce policies on messages
    3. Provides a policy-aware messaging layer for the system
    """
    
    def __init__(self, policy_engine: IPolicyEngine, logger: Optional[logging.Logger] = None):
        """
        Initialize the policy message broker.
        
        Args:
            policy_engine: Policy engine for policy enforcement
            logger: Optional logger
        """
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
        self.handlers = {}
        self.subscribers = {}
        self.components = {}
        self.message_stats = {
            "total_messages": 0,
            "policy_rejections": 0,
            "by_component": {},
            "by_message_type": {}
        }
    
    def register_component(self, component_id: str, component_info: Dict[str, Any]) -> bool:
        """
        Register a component with the broker.
        
        Args:
            component_id: Unique component identifier
            component_info: Information about the component
            
        Returns:
            True if registered successfully, False otherwise
        """
        if component_id in self.components:
            self.logger.warning(f"Component already registered: {component_id}")
            return False
        
        self.components[component_id] = {
            "info": component_info,
            "registered_at": time.time(),
            "last_active": time.time(),
            "message_count": 0
        }
        
        self.message_stats["by_component"][component_id] = {
            "sent": 0,
            "received": 0,
            "rejected": 0
        }
        
        self.logger.info(f"Registered component: {component_id}")
        return True
    
    def unregister_component(self, component_id: str) -> bool:
        """
        Unregister a component from the broker.
        
        Args:
            component_id: Component identifier
            
        Returns:
            True if unregistered successfully, False otherwise
        """
        if component_id not in self.components:
            self.logger.warning(f"Component not registered: {component_id}")
            return False
        
        del self.components[component_id]
        
        # Remove component from subscribers
        for message_type in self.subscribers:
            if component_id in self.subscribers[message_type]:
                self.subscribers[message_type].remove(component_id)
        
        self.logger.info(f"Unregistered component: {component_id}")
        return True
    
    def subscribe(self, component_id: str, message_type: str) -> bool:
        """
        Subscribe a component to a message type.
        
        Args:
            component_id: Component identifier
            message_type: Type of message to subscribe to
            
        Returns:
            True if subscribed successfully, False otherwise
        """
        # Check if component is registered
        if component_id not in self.components:
            self.logger.warning(f"Cannot subscribe: Component not registered: {component_id}")
            return False
        
        # Initialize subscribers for this message type if needed
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        
        # Add component to subscribers if not already subscribed
        if component_id not in self.subscribers[message_type]:
            self.subscribers[message_type].append(component_id)
            self.logger.info(f"Component {component_id} subscribed to message type: {message_type}")
        
        return True
    
    def unsubscribe(self, component_id: str, message_type: str) -> bool:
        """
        Unsubscribe a component from a message type.
        
        Args:
            component_id: Component identifier
            message_type: Type of message to unsubscribe from
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        # Check if message type exists
        if message_type not in self.subscribers:
            self.logger.warning(f"Cannot unsubscribe: Message type not found: {message_type}")
            return False
        
        # Remove component from subscribers
        if component_id in self.subscribers[message_type]:
            self.subscribers[message_type].remove(component_id)
            self.logger.info(f"Component {component_id} unsubscribed from message type: {message_type}")
        
        return True
    
    def publish_message(self, 
                        source_component: str, 
                        message_type: str, 
                        payload: Dict[str, Any], 
                        target_component: Optional[str] = None) -> Dict[str, Any]:
        """
        Publish a message to subscribers.
        
        Args:
            source_component: ID of the component sending the message
            message_type: Type of message
            payload: Message payload
            target_component: Optional specific target component
            
        Returns:
            Dictionary with results of the publish operation
        """
        # Check if source component is registered
        if source_component not in self.components:
            self.logger.warning(f"Cannot publish: Source component not registered: {source_component}")
            return {"success": False, "error": "Source component not registered"}
        
        # Update component last active time
        self.components[source_component]["last_active"] = time.time()
        self.components[source_component]["message_count"] += 1
        self.message_stats["by_component"][source_component]["sent"] += 1
        
        # Update message stats
        self.message_stats["total_messages"] += 1
        if message_type not in self.message_stats["by_message_type"]:
            self.message_stats["by_message_type"][message_type] = 0
        self.message_stats["by_message_type"][message_type] += 1
        
        # Create message context for policy check
        message_context = {
            "source_component": source_component,
            "message_type": message_type,
            "timestamp": time.time()
        }
        
        if target_component:
            message_context["target_component"] = target_component
        
        # Check policy
        policy_result = self.policy_engine.evaluate_policy("message_routing", message_context)
        
        # If policy rejects the message, return error
        if not policy_result.get("allowed", True):
            self.logger.warning(f"Message from {source_component} rejected by policy: {policy_result.get('reason', 'Unknown policy violation')}")
            self.message_stats["policy_rejections"] += 1
            self.message_stats["by_component"][source_component]["rejected"] += 1
            
            return {
                "success": False,
                "error": "Message rejected by policy",
                "reason": policy_result.get("reason", "Unknown policy violation")
            }
        
        # Create the message
        message = {
            "source": source_component,
            "message_type": message_type,
            "payload": payload,
            "timestamp": time.time(),
            "id": f"{source_component}_{int(time.time() * 1000)}_{self.message_stats['total_messages']}"
        }
        
        # Determine recipients
        recipients = []
        
        if target_component:
            # Targeted message
            if target_component in self.components:
                recipients = [target_component]
            else:
                self.logger.warning(f"Target component not found: {target_component}")
                return {"success": False, "error": f"Target component not found: {target_component}"}
        else:
            # Broadcast to subscribers
            if message_type in self.subscribers:
                recipients = self.subscribers[message_type]
        
        # Deliver the message to each recipient
        results = {}
        for recipient in recipients:
            # Skip the source component unless it's explicitly targeted
            if recipient == source_component and not (target_component and target_component == source_component):
                continue
                
            try:
                # Check policy for specific recipient
                recipient_context = message_context.copy()
                recipient_context["target_component"] = recipient
                
                policy_result = self.policy_engine.evaluate_policy("message_delivery", recipient_context)
                
                if not policy_result.get("allowed", True):
                    self.logger.warning(f"Message delivery to {recipient} rejected by policy: {policy_result.get('reason', 'Unknown policy violation')}")
                    results[recipient] = {
                        "success": False,
                        "error": "Message delivery rejected by policy",
                        "reason": policy_result.get("reason", "Unknown policy violation")
                    }
                    continue
                
                # Call the handler function for the component
                if recipient in self.handlers and message_type in self.handlers[recipient]:
                    handler = self.handlers[recipient][message_type]
                    result = handler(message)
                    results[recipient] = {"success": True, "result": result}
                    
                    # Update stats
                    self.message_stats["by_component"][recipient]["received"] += 1
                else:
                    self.logger.warning(f"No handler for message type {message_type} in component {recipient}")
                    results[recipient] = {"success": False, "error": "No handler for message type"}
            
            except Exception as e:
                self.logger.error(f"Error delivering message to {recipient}: {e}")
                results[recipient] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message_id": message["id"],
            "recipients": len(recipients),
            "results": results
        }
    
    def register_handler(self, component_id: str, message_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Register a message handler for a component.
        
        Args:
            component_id: Component identifier
            message_type: Type of message to handle
            handler: Function to call when a message of this type is received
            
        Returns:
            True if registered successfully, False otherwise
        """
        # Check if component is registered
        if component_id not in self.components:
            self.logger.warning(f"Cannot register handler: Component not registered: {component_id}")
            return False
        
        # Initialize handlers for this component if needed
        if component_id not in self.handlers:
            self.handlers[component_id] = {}
        
        # Register the handler
        self.handlers[component_id][message_type] = handler
        self.logger.info(f"Registered handler for component {component_id}, message type: {message_type}")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get message broker statistics.
        
        Returns:
            Dictionary containing statistics
        """
        return {
            "components": len(self.components),
            "active_components": sum(1 for c in self.components.values() if time.time() - c["last_active"] < 300),
            "message_types": list(self.subscribers.keys()),
            "message_stats": self.message_stats
        } 