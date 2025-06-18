"""
Network Policy Handler for SDN Integration.

This module defines the interface and implementation for a policy handler
that provides centralized policy management for SDN controllers in the
federated learning system.

Previously named policy_engine.py, renamed to network_policy_handler.py for clarity.
"""

import time
from typing import Dict, List, Optional, Any, Union, Callable
import threading
import json

from src.core.common.logger import LoggerMixin

class IPolicyEngine(LoggerMixin):
    """Interface for policy engine that provides centralized policy management."""
    
    def __init__(self):
        """Initialize the policy engine."""
        super().__init__()
    
    def validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a network policy against defined rules.
        
        Args:
            policy: Network policy configuration
            
        Returns:
            Dict: Validation result with status and message
        """
        raise NotImplementedError("Policy validation not implemented")
    
    def authorize_flow(self, src_ip: str, dst_ip: str, 
                     protocol: str = "any", port: int = 0) -> bool:
        """
        Check if a flow is authorized based on security policies.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            protocol: Protocol (tcp, udp, icmp, any)
            port: Destination port
            
        Returns:
            bool: Whether the flow is authorized
        """
        raise NotImplementedError("Flow authorization not implemented")
    
    def get_client_priority(self, client_id: str) -> str:
        """
        Get the priority level for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Priority level (high, medium, low)
        """
        raise NotImplementedError("Client priority not implemented")
    
    def register_policy_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for policy updates.
        
        Args:
            callback: Function to call when policies are updated
        """
        raise NotImplementedError("Policy callback registration not implemented")
    
    def get_policies(self) -> List[Dict[str, Any]]:
        """
        Get all active policies from the policy engine.
        
        Returns:
            List[Dict[str, Any]]: List of active policies
        """
        raise NotImplementedError("Get policies not implemented")


class PolicyEngine(IPolicyEngine):
    """Implementation of policy engine for SDN integration."""
    
    def __init__(self, policy_file: Optional[str] = None, refresh_interval: int = 60):
        """
        Initialize the policy engine.
        
        Args:
            policy_file: Path to policy configuration file (optional)
            refresh_interval: Interval to refresh policies in seconds
        """
        super().__init__()
        self.policies = {
            "security": {},  # IP and network-based security rules
            "qos": {},       # QoS priorities for clients
            "bandwidth": {}  # Bandwidth limits
        }
        self.policy_file = policy_file
        self.refresh_interval = refresh_interval
        self.callbacks = []  # List of registered callbacks
        self.stop_refresh = False
        self.refresh_thread = None
        
        # Load initial policies
        if policy_file:
            self._load_policies_from_file(policy_file)
            
            # Start refresh thread
            self.refresh_thread = threading.Thread(target=self._refresh_policies)
            self.refresh_thread.daemon = True
            self.refresh_thread.start()
        
        self.logger.info("Initialized policy engine")
    
    def _load_policies_from_file(self, policy_file: str) -> bool:
        """
        Load policies from a file.
        
        Args:
            policy_file: Path to policy configuration file
            
        Returns:
            bool: Success or failure
        """
        try:
            with open(policy_file, 'r') as f:
                config = json.load(f)
            
            if "security" in config:
                self.policies["security"] = config["security"]
            
            if "qos" in config:
                self.policies["qos"] = config["qos"]
            
            if "bandwidth" in config:
                self.policies["bandwidth"] = config["bandwidth"]
            
            self.logger.info(f"Loaded policies from {policy_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading policies: {e}")
            return False
    
    def _refresh_policies(self) -> None:
        """Periodically refresh policies from the policy file."""
        while not self.stop_refresh:
            time.sleep(self.refresh_interval)
            
            if self.policy_file and not self.stop_refresh:
                old_policies = self.policies.copy()
                if self._load_policies_from_file(self.policy_file):
                    # Check if policies have changed
                    if old_policies != self.policies:
                        self._notify_policy_change()
    
    def _notify_policy_change(self) -> None:
        """Notify registered callbacks about policy changes."""
        for callback in self.callbacks:
            try:
                callback(self.policies)
            except Exception as e:
                self.logger.error(f"Error in policy callback: {e}")
    
    def validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a network policy against defined rules.
        
        Args:
            policy: Network policy configuration
            
        Returns:
            Dict: Validation result with status and message
        """
        try:
            policy_type = policy.get("type", "unknown")
            
            if policy_type == "qos":
                client_id = policy.get("client_id")
                client_ip = policy.get("client_ip")
                server_ip = policy.get("server_ip")
                
                # Check if the client is authorized for QoS
                if client_id not in self.policies["qos"]:
                    # Check if there's a default policy
                    if "*" in self.policies["qos"]:
                        # Use default policy
                        return {
                            "status": "approved",
                            "policy": {
                                **policy,
                                "priority_level": self.policies["qos"]["*"].get("priority", "low")
                            },
                            "message": "Using default QoS policy"
                        }
                    
                    return {
                        "status": "denied",
                        "message": f"No QoS policy defined for client {client_id}"
                    }
                
                # Get client's configured priority
                priority = self.policies["qos"][client_id].get("priority", "low")
                
                # Override the requested priority with the configured one
                return {
                    "status": "approved",
                    "policy": {**policy, "priority_level": priority},
                    "message": f"QoS policy approved for client {client_id}"
                }
                
            elif policy_type == "security":
                target_ip = policy.get("target_ip")
                
                # Check if the IP is already in the blocklist
                if "blocklist" in self.policies["security"]:
                    if target_ip in self.policies["security"]["blocklist"]:
                        return {
                            "status": "approved",
                            "policy": policy,
                            "message": f"IP {target_ip} is already in the blocklist"
                        }
                
                # Check if the IP is in the allowlist (which would prevent blocking)
                if "allowlist" in self.policies["security"]:
                    if target_ip in self.policies["security"]["allowlist"]:
                        return {
                            "status": "denied",
                            "message": f"IP {target_ip} is in the allowlist and cannot be blocked"
                        }
                
                # IP can be blocked
                return {
                    "status": "approved",
                    "policy": policy,
                    "message": f"Security policy approved for IP {target_ip}"
                }
                
            elif policy_type == "bandwidth":
                client_id = policy.get("client_id")
                requested_bandwidth = policy.get("bandwidth_mbps", 10)
                
                # Check if the client has bandwidth limits defined
                if client_id in self.policies["bandwidth"]:
                    max_bandwidth = self.policies["bandwidth"][client_id].get("max_mbps", 100)
                    
                    # Ensure the requested bandwidth doesn't exceed the maximum
                    if requested_bandwidth > max_bandwidth:
                        adjusted_bandwidth = max_bandwidth
                        return {
                            "status": "adjusted",
                            "policy": {**policy, "bandwidth_mbps": adjusted_bandwidth},
                            "message": f"Bandwidth adjusted to maximum allowed ({max_bandwidth} Mbps)"
                        }
                    
                    # Requested bandwidth is within limits
                    return {
                        "status": "approved",
                        "policy": policy,
                        "message": f"Bandwidth policy approved for client {client_id}"
                    }
                
                # No specific limits for this client, check if there's a default policy
                if "*" in self.policies["bandwidth"]:
                    default_max = self.policies["bandwidth"]["*"].get("max_mbps", 100)
                    
                    if requested_bandwidth > default_max:
                        adjusted_bandwidth = default_max
                        return {
                            "status": "adjusted",
                            "policy": {**policy, "bandwidth_mbps": adjusted_bandwidth},
                            "message": f"Bandwidth adjusted to default maximum ({default_max} Mbps)"
                        }
                    
                    return {
                        "status": "approved",
                        "policy": policy,
                        "message": "Using default bandwidth policy"
                    }
                
                # No bandwidth policy defined
                return {
                    "status": "approved",
                    "policy": policy,
                    "message": "No bandwidth policy defined, using requested value"
                }
                
            elif policy_type == "time":
                # Time-based policies (allow access during certain hours)
                return {
                    "status": "approved", 
                    "policy": policy,
                    "message": "Time-based policy approved"
                }
                
            else:
                return {
                    "status": "unknown",
                    "message": f"Unknown policy type: {policy_type}"
                }
                
        except Exception as e:
            self.logger.error(f"Error validating policy: {e}")
            return {
                "status": "error",
                "message": f"Error validating policy: {str(e)}"
            }
    
    def authorize_flow(self, src_ip: str, dst_ip: str, 
                      protocol: str = "any", port: int = 0) -> bool:
        """
        Check if a flow is authorized based on security policies.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            protocol: Protocol (tcp, udp, icmp, any)
            port: Destination port
            
        Returns:
            bool: Whether the flow is authorized
        """
        try:
            # Check if source IP is in blocklist
            if "blocklist" in self.policies["security"]:
                if src_ip in self.policies["security"]["blocklist"]:
                    self.logger.info(f"Flow from {src_ip} to {dst_ip} denied - source IP is blocklisted")
                    return False
            
            # Check if destination IP is in blocklist
            if "blocklist" in self.policies["security"]:
                if dst_ip in self.policies["security"]["blocklist"]:
                    self.logger.info(f"Flow from {src_ip} to {dst_ip} denied - destination IP is blocklisted")
                    return False
            
            # Check specific flow rules
            if "flow_rules" in self.policies["security"]:
                for rule in self.policies["security"]["flow_rules"]:
                    # Check for matching deny rule
                    if (rule.get("action") == "deny" and
                        (rule.get("src_ip") == "*" or rule.get("src_ip") == src_ip) and
                        (rule.get("dst_ip") == "*" or rule.get("dst_ip") == dst_ip) and
                        (rule.get("protocol") == "any" or rule.get("protocol") == protocol) and
                        (rule.get("port") == 0 or rule.get("port") == port)):
                        
                        self.logger.info(f"Flow from {src_ip} to {dst_ip} denied by flow rule")
                        return False
            
            # If we reach here, the flow is allowed
            return True
            
        except Exception as e:
            self.logger.error(f"Error in authorize_flow: {e}")
            # Default to allowing flow in case of errors
            return True
    
    def get_client_priority(self, client_id: str) -> str:
        """
        Get the priority level for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Priority level (high, medium, low)
        """
        try:
            # Check if client has a specific priority
            if client_id in self.policies["qos"]:
                return self.policies["qos"][client_id].get("priority", "low")
            
            # Check if there's a default priority
            if "*" in self.policies["qos"]:
                return self.policies["qos"]["*"].get("priority", "low")
            
            # Default priority
            return "low"
            
        except Exception as e:
            self.logger.error(f"Error in get_client_priority: {e}")
            return "low"  # Default priority in case of errors
    
    def register_policy_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for policy updates.
        
        Args:
            callback: Function to call when policies are updated
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            self.logger.debug(f"Registered policy callback, total callbacks: {len(self.callbacks)}")
    
    def unregister_policy_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Unregister a callback for policy updates.
        
        Args:
            callback: Function to unregister
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            self.logger.debug(f"Unregistered policy callback, remaining callbacks: {len(self.callbacks)}")
    
    def cleanup(self) -> None:
        """Clean up resources used by the policy engine."""
        self.stop_refresh = True
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.refresh_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish
        self.logger.info("Policy engine cleanup complete")
    
    def get_policies(self) -> List[Dict[str, Any]]:
        """
        Get all active policies from the policy engine.
        
        Returns:
            List[Dict[str, Any]]: List of active policies
        """
        result = []
        
        # Convert security policies to list format
        if "blocklist" in self.policies["security"]:
            for ip in self.policies["security"]["blocklist"]:
                result.append({
                    "type": "security",
                    "action": "block",
                    "target_ip": ip
                })
        
        if "flow_rules" in self.policies["security"]:
            for rule in self.policies["security"]["flow_rules"]:
                result.append({
                    "type": "security",
                    "action": rule.get("action", "allow"),
                    "src_ip": rule.get("src_ip", "*"),
                    "dst_ip": rule.get("dst_ip", "*"),
                    "protocol": rule.get("protocol", "any"),
                    "port": rule.get("port", 0)
                })
        
        # Convert QoS policies to list format
        for client_id, policy in self.policies["qos"].items():
            result.append({
                "type": "qos",
                "client_id": client_id,
                "priority_level": policy.get("priority", "low")
            })
        
        # Convert bandwidth policies to list format
        for client_id, policy in self.policies["bandwidth"].items():
            result.append({
                "type": "bandwidth",
                "client_id": client_id,
                "max_mbps": policy.get("max_mbps", 100),
                "min_mbps": policy.get("min_mbps", 0)
            })
        
        return result 