"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
SDN Policy Engine Module.

This module provides policy engine implementation for SDN networking,
allowing integration of policy-based decisions with SDN controllers.
"""

import uuid
import json
import logging
from typing import Dict, List, Any, Optional, Union

from src.policy_engine.policy_engine import PolicyEngine
from src.core.common.logger import LoggerMixin
from src.networking.interfaces.sdn_controller import ISDNController

class SDNPolicyEngine(PolicyEngine):
    """
    SDN Policy Engine for federated learning.
    
    This policy engine integrates with SDN controllers to enforce network
    policies and optimize network traffic based on federated learning requirements.
    """
    
    def __init__(self, sdn_controller: Optional[ISDNController] = None):
        """
        Initialize the SDN Policy Engine.
        
        Args:
            sdn_controller: SDN controller instance (optional)
        """
        super().__init__()
        self.sdn_controller = sdn_controller
        self.policy_cache = {}  # Already initialized in parent class, but keeping for clarity
        self.logger.info("SDN Policy Engine initialized")
    
    def set_controller(self, controller: ISDNController) -> None:
        """
        Set the SDN controller for the policy engine.
        
        Args:
            controller: SDN controller instance
        """
        self.sdn_controller = controller
        self.logger.info(f"SDN controller set: {controller.__class__.__name__}")
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an operation is allowed by the policies.
        
        This extends the parent method to specifically handle network-related policies
        and apply them to the SDN controller when appropriate.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with policy decision and metadata
        """
        # First, check using the parent method
        result = super().check_policy(policy_type, context)
        
        # Apply any network policies to the SDN controller if needed
        if self.sdn_controller and self.sdn_controller.connected and result.get("allowed", False):
            # Apply SDN-specific actions based on the policy type
            if policy_type == "network_qos":
                self._apply_qos_to_sdn(context)
            elif policy_type == "network_security":
                self._apply_security_to_sdn(context)
            elif policy_type == "bandwidth_allocation":
                self._apply_bandwidth_to_sdn(context)
        
        return result
    
    def add_policy(self, policy_type: str, policy_definition: Dict[str, Any]) -> str:
        """
        Add a new policy to the policy engine.
        
        This extends the parent method to apply the policy to the SDN controller
        when appropriate.
        
        Args:
            policy_type: Type of policy to add
            policy_definition: Definition of the policy
            
        Returns:
            ID of the newly added policy
        """
        # Add the policy using the parent method
        policy_id = super().add_policy(policy_type, policy_definition)
        
        # Apply the policy to the SDN controller if relevant and controller is available
        if self.sdn_controller and self.sdn_controller.connected:
            self._apply_policy_to_sdn(policy_id, policy_type, policy_definition)
        
        return policy_id
    
    def _apply_policy_to_sdn(self, policy_id: str, policy_type: str, policy_definition: Dict[str, Any]) -> None:
        """
        Apply a policy to the SDN controller.
        
        Args:
            policy_id: ID of the policy
            policy_type: Type of policy
            policy_definition: Definition of the policy
        """
        try:
            # Handle different policy types
            if policy_type == "network_qos":
                self._apply_qos_policy(policy_definition)
            elif policy_type == "network_security":
                self._apply_security_policy(policy_definition)
            elif policy_type == "bandwidth_allocation":
                self._apply_bandwidth_policy(policy_definition)
            else:
                self.logger.info(f"Policy type {policy_type} does not require SDN application")
            
        except Exception as e:
            self.logger.error(f"Error applying policy to SDN: {e}")
    
    def _apply_qos_to_sdn(self, context: Dict[str, Any]) -> None:
        """
        Apply QoS context to the SDN controller.
        
        Args:
            context: Context with QoS information
        """
        # Implementation depends on the SDN controller specifics
        pass
    
    def _apply_security_to_sdn(self, context: Dict[str, Any]) -> None:
        """
        Apply security context to the SDN controller.
        
        Args:
            context: Context with security information
        """
        # Implementation depends on the SDN controller specifics
        pass
    
    def _apply_bandwidth_to_sdn(self, context: Dict[str, Any]) -> None:
        """
        Apply bandwidth allocation context to the SDN controller.
        
        Args:
            context: Context with bandwidth information
        """
        # Implementation depends on the SDN controller specifics
        pass
    
    def _apply_qos_policy(self, policy_definition: Dict[str, Any]) -> None:
        """
        Apply a QoS policy to the SDN controller.
        
        Args:
            policy_definition: Definition of the policy
        """
        policy_logic = policy_definition.get("logic", {})
        priority_mappings = policy_logic.get("priority_mappings", {})
        
        # Apply QoS policy to switches
        switches = self.sdn_controller.get_switches()
        for switch in switches:
            switch_id = switch.get("id")
            
            # Apply priority queues for different traffic classes
            for traffic_class, priority in priority_mappings.items():
                policy_name = f"qos_{traffic_class}"
                policy_params = {
                    "traffic_class": traffic_class,
                    "priority": priority
                }
                
                self.sdn_controller.create_qos_policy(
                    switch_id, 
                    policy_name, 
                    "priority", 
                    policy_params
                )
        
        self.logger.info(f"Applied QoS policy to {len(switches)} switches")
    
    def _apply_security_policy(self, policy_definition: Dict[str, Any]) -> None:
        """
        Apply a security policy to the SDN controller.
        
        Args:
            policy_definition: Definition of the policy
        """
        policy_logic = policy_definition.get("logic", {})
        blocked_ips = policy_logic.get("blocked_ips", [])
        
        # Apply security policy to switches
        switches = self.sdn_controller.get_switches()
        for switch in switches:
            switch_id = switch.get("id")
            
            # Block specified IPs
            for ip in blocked_ips:
                # Create flow to drop traffic from blocked IP
                match = {
                    "nw_src": ip,
                    "dl_type": 0x0800  # IPv4
                }
                
                # Empty actions list means drop the packet
                actions = []
                
                self.sdn_controller.add_flow(
                    switch_id,
                    200,  # High priority
                    match,
                    actions
                )
        
        self.logger.info(f"Applied security policy to {len(switches)} switches")
    
    def _apply_bandwidth_policy(self, policy_definition: Dict[str, Any]) -> None:
        """
        Apply a bandwidth allocation policy to the SDN controller.
        
        Args:
            policy_definition: Definition of the policy
        """
        policy_logic = policy_definition.get("logic", {})
        bandwidth_limits = policy_logic.get("bandwidth_limits", {})
        
        # Apply bandwidth policy to switches
        switches = self.sdn_controller.get_switches()
        for switch in switches:
            switch_id = switch.get("id")
            
            # Apply bandwidth limits for clients
            for client_id, limit in bandwidth_limits.items():
                if client_id == "default":
                    continue
                
                # Try to get the client's IP or MAC
                client_info = self._get_client_info(client_id)
                
                if not client_info:
                    continue
                
                match = {}
                if "ip" in client_info:
                    match["nw_src"] = client_info["ip"]
                    match["dl_type"] = 0x0800  # IPv4
                elif "mac" in client_info:
                    match["dl_src"] = client_info["mac"]
                
                # Create a meter for bandwidth limiting
                policy_name = f"bw_limit_{client_id}"
                policy_params = {
                    "rate": limit,
                    "burst_size": limit * 0.1  # 10% burst
                }
                
                self.sdn_controller.create_qos_policy(
                    switch_id,
                    policy_name,
                    "meter",
                    policy_params
                )
        
        self.logger.info(f"Applied bandwidth policy to {len(switches)} switches")
    
    def _get_client_info(self, client_id: str) -> Optional[Dict[str, str]]:
        """
        Get client network information from the SDN controller.
        
        Args:
            client_id: ID of the client
            
        Returns:
            Dictionary with client network information or None
        """
        # This is a placeholder - in a real implementation, you would
        # have a mapping of client IDs to network identifiers (IP, MAC)
        # or query the controller for this information
        
        # For now, assume client_id might be an IP or MAC
        hosts = self.sdn_controller.get_hosts()
        
        for host in hosts:
            if isinstance(host, dict):
                mac = host.get("mac")
                ip = host.get("ipv4", [None])[0] if "ipv4" in host else None
                
                if mac == client_id:
                    return {"mac": mac, "ip": ip} if ip else {"mac": mac}
                
                if ip == client_id:
                    return {"ip": ip, "mac": mac} if mac else {"ip": ip}
        
        return None
    
    def remove_policy(self, policy_id: str) -> bool:
        """
        Remove a policy from the policy engine.
        
        This extends the parent method to remove the policy from the SDN controller
        when appropriate.
        
        Args:
            policy_id: ID of the policy to remove
            
        Returns:
            True if the policy was removed, False otherwise
        """
        # Get the policy before removing it
        policy = self.get_policy(policy_id)
        if not policy:
            return False
        
        policy_type = policy.get_type() if hasattr(policy, 'get_type') else "unknown"
        
        # Remove using the parent method
        result = super().remove_policy(policy_id)
        
        # If successful and controller is available, remove policy from SDN
        if result and self.sdn_controller and self.sdn_controller.connected:
            self._remove_policy_from_sdn(policy_id, policy_type, policy.to_dict() if hasattr(policy, 'to_dict') else {})
        
        return result
    
    def _remove_policy_from_sdn(self, policy_id: str, policy_type: str, policy: Dict[str, Any]) -> None:
        """
        Remove a policy from the SDN controller.
        
        Args:
            policy_id: ID of the policy
            policy_type: Type of policy
            policy: Policy definition
        """
        # This is a simplified implementation
        # In a real system, you would need to track which flows were created by which policies
        
        self.logger.info(f"Policy {policy_id} removed from policy engine, but SDN flows remain")
        
        # In a complete implementation, we would remove the flows we created for this policy
    
    def apply_policies_to_network(self) -> bool:
        """
        Apply all policies to the SDN network.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.sdn_controller or not self.sdn_controller.connected:
            self.logger.error("No SDN controller connected")
            return False
        
        try:
            # Apply each policy
            for policy_id, policy in self.policies.items():
                if hasattr(policy, 'get_type'):
                    policy_type = policy.get_type()
                    policy_dict = policy.to_dict() if hasattr(policy, 'to_dict') else {}
                    self._apply_policy_to_sdn(policy_id, policy_type, policy_dict)
            
            # Optimize the network
            self.sdn_controller.optimize_network()
            
            self.logger.info("Applied all policies to the network")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying policies to network: {e}")
            return False 