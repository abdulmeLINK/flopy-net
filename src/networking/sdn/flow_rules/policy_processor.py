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
SDN Policy Processor

This module handles processing and applying network policies to SDN switches.
Extracted from FlowManager to improve code organization.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PolicyProcessor:
    """Handles policy processing and flow rule generation for SDN switches."""
    
    def __init__(self, sdn_controller, network_config: Dict[str, Any]):
        """
        Initialize the PolicyProcessor.
        
        Args:
            sdn_controller: SDN controller instance for flow operations
            network_config: Network configuration dictionary
        """
        self.sdn_controller = sdn_controller
        self.network_config = network_config
        self.logger = logger
    
    def process_policies(self, policies: List[Dict[str, Any]], 
                        qos_handler=None, security_handler=None,
                        time_window_handler=None, bandwidth_handler=None) -> Dict[str, List[str]]:
        """
        Process and apply policies.
        
        Args:
            policies: List of policy objects
            qos_handler: Optional callback for QoS policies
            security_handler: Optional callback for security policies
            time_window_handler: Optional callback for time window policies
            bandwidth_handler: Optional callback for bandwidth policies
            
        Returns:
            Dict with 'successful' and 'failed' policy ID lists
        """
        self.logger.info(f"PolicyProcessor: Processing {len(policies)} policies")
        
        successful_policies = []
        failed_policies = []
        
        for policy in policies:
            try:
                policy_id = policy.get('id', 'unknown')
                policy_type = policy.get('type', policy.get('policy_type', 'unknown'))
                policy_name = policy.get('name', f'Policy {policy_id}')
                
                # Skip if policy is disabled
                if not policy.get('enabled', True):
                    self.logger.info(f"PolicyProcessor: Skipping disabled policy: {policy_name}")
                    continue
                
                # Process based on policy type
                if policy_type == 'qos' and qos_handler:
                    qos_handler(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'security' and security_handler:
                    security_handler(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'network_security':
                    self.process_network_security_policy(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'time_window' and time_window_handler:
                    time_window_handler(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'bandwidth_allocation' and bandwidth_handler:
                    bandwidth_handler(policy)
                    successful_policies.append(policy_id)
                else:
                    self.logger.warning(f"PolicyProcessor: Ignoring unsupported policy type: {policy_type}")
            except Exception as e:
                self.logger.error(f"PolicyProcessor: Error processing policy {policy.get('id', 'unknown')}: {e}", exc_info=True)
                failed_policies.append(policy.get('id', 'unknown'))
        
        self.logger.info(f"PolicyProcessor: Applied {len(successful_policies)} policies successfully, {len(failed_policies)} failed")
        return {"successful": successful_policies, "failed": failed_policies}
    
    def process_network_security_policy(self, policy: Dict[str, Any]) -> None:
        """
        Process a network security policy and install corresponding flow rules.
        
        Args:
            policy: Network security policy dictionary
        """
        policy_name = policy.get('name', policy.get('id', 'unnamed_policy'))
        self.logger.info(f"PolicyProcessor: Processing network security policy: {policy_name}")
        self.logger.debug(f"PolicyProcessor: Policy details: {json.dumps(policy, indent=2)}")

        # Get switches
        switches = self.get_switches()
        if not switches:
            self.logger.warning(f"PolicyProcessor: Initial switch check found no switches for policy {policy_name}. Waiting 2s and retrying...")
            time.sleep(2)
            switches = self.get_switches()

        if not switches:
            self.logger.warning(f"PolicyProcessor: No switches available to apply policy {policy_name}")
            return
            
        # Get rules from the policy
        rules = policy.get('rules', [])
        if not rules:
            self.logger.info(f"PolicyProcessor: No rules found in policy {policy_name}.")
            return

        # Track successful and failed rule applications
        policy_applied_rule_instances = 0 
        policy_failed_rule_instances = 0
        
        # Process each rule in the policy
        for rule_idx, rule in enumerate(rules):
            rule_id = rule.get('id', rule.get('rule_id', f"{policy_name}_rule_{rule_idx}"))
            
            # Skip disabled rules
            if not rule.get('enabled', True):
                self.logger.info(f"Skipping disabled rule: '{rule_id}' in policy '{policy_name}'")
                continue
                
            # Get controller IP if available
            controller_ip = self.network_config.get('NODE_IP_SDN_CONTROLLER', None)
            
            try:
                success = self.process_single_network_rule(rule_id, rule, controller_ip, None)
                
                if success:
                    policy_applied_rule_instances += 1
                else:
                    policy_failed_rule_instances += 1
            except Exception as e:
                self.logger.error(f"Error processing rule '{rule_id}' in policy '{policy_name}': {e}", exc_info=True)
                policy_failed_rule_instances += 1
                
        # Log summary
        if policy_applied_rule_instances > 0 or policy_failed_rule_instances > 0:
            self.logger.info(f"Finished processing policy '{policy_name}'. Applied: {policy_applied_rule_instances}, Failed: {policy_failed_rule_instances}")
        else:
            self.logger.info(f"Finished processing policy '{policy_name}'. No rule instances were applied or failed.")
    
    def get_flow_actions(self, action_str: str, rule_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Convert action string to OpenFlow actions.
        
        Args:
            action_str: Action string ('allow', 'deny', 'alert', etc.)
            rule_context: Optional context about the rule for additional actions
            
        Returns:
            List of OVS actions
        """
        of_actions = []
        
        if action_str in ['allow', 'accept', 'permit']:
            self.logger.info("Creating flow action with NORMAL port for traffic forwarding")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
        
        elif action_str == 'deny':
            # Deny action means no actions (packet will be dropped)
            of_actions = []
        
        elif action_str == 'alert':
            # Alert means send to controller for logging
            of_actions = [{"type": "OUTPUT", "port": "CONTROLLER"}]
        
        elif action_str == 'rate_limit':
            # Rate limiting requires metering, which is handled separately
            self.logger.warning(f"Rate limiting not fully implemented, treating as 'allow'")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
        
        else:
            # Default to normal forwarding for unknown actions
            self.logger.warning(f"Unknown action type: {action_str}, defaulting to allow")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
            
        return of_actions

    def get_switches(self) -> List[Dict[str, Any]]:
        """
        Get available switches with better error handling and diagnostics.
        
        Returns:
            List of available switches
        """
        try:
            switches = self.sdn_controller.get_switches()
            
            if not switches:
                self.logger.debug("No switches detected, checking controller connectivity")
                # Try to refresh controller topology
                self.sdn_controller.refresh_topology()
                switches = self.sdn_controller.get_switches()
                
            if switches:
                dpid_list_for_logging = []
                for sw_info in switches:
                    log_dpid = sw_info.get('dpid', sw_info.get('id', 'Unknown DPID'))
                    if isinstance(log_dpid, dict):
                        actual_id_from_dict = log_dpid.get('dpid', log_dpid.get('id'))
                        if actual_id_from_dict is not None:
                            log_dpid = actual_id_from_dict
                        else:
                            log_dpid = str(log_dpid)
                    dpid_list_for_logging.append(str(log_dpid))
                self.logger.info(f"Detected {len(switches)} switches. DPIDs: {dpid_list_for_logging}")
            else:
                self.logger.debug("Still no switches detected after refresh")
                
            return switches
        except Exception as e:
            self.logger.error(f"Error getting switches: {e}")
            return []
    
    def resolve_ip_from_type(self, entity_type: Optional[str], entity_ip_val: Optional[str], 
                            controller_ip: Optional[str] = None) -> str:
        """
        Resolve an IP address based on entity type.
        
        Args:
            entity_type: Type of entity ('controller', 'policy_engine', 'fl_server', etc.)
            entity_ip_val: Current IP value
            controller_ip: Controller IP if available
            
        Returns:
            Resolved IP address string
        """
        if entity_type == 'controller' and controller_ip:
            self.logger.info(f"Using controller IP {controller_ip}")
            return controller_ip
        elif entity_type == 'policy_engine' and self.network_config.get('NODE_IP_POLICY_ENGINE'):
            ip = self.network_config.get('NODE_IP_POLICY_ENGINE')
            self.logger.info(f"Using policy engine IP {ip}")
            return ip
        elif entity_type == 'fl_server' and self.network_config.get('NODE_IP_FL_SERVER'):
            ip = self.network_config.get('NODE_IP_FL_SERVER')
            self.logger.info(f"Using FL server IP {ip}")
            return ip
        return entity_ip_val or 'any'
            
    def process_single_network_rule(self, rule_id: str, rule: Dict[str, Any], 
                                   controller_ip: Optional[str] = None,
                                   switch: Optional[Dict] = None) -> bool:
        """
        Process a network security policy rule and convert it to flow rules.
        
        Args:
            rule_id: Identifier for the rule
            rule: Rule configuration dictionary
            controller_ip: IP address of the SDN controller
            switch: Specific switch to apply rule to, or None for all switches
            
        Returns:
            bool: True if rule was applied successfully, False otherwise
        """
        # Get available switches if none specified
        if not switch:
            switches = self.get_switches()
            if not switches:
                self.logger.warning(f"No switches available to apply rule {rule_id}")
                return False
        else:
            switches = [switch]
            
        success = False
            
        # Extract rule parameters
        rule_match_info = rule.get('match', {})
        src_ip = rule_match_info.get('src_ip', rule_match_info.get('source_ip', 'any'))
        dst_ip = rule_match_info.get('dst_ip', rule_match_info.get('destination_ip', 'any'))
        protocol = rule_match_info.get('protocol', 'any').lower()
        if not protocol:
            protocol = 'any'
            
        src_port = rule_match_info.get('src_port', rule_match_info.get('source_port'))
        dst_port = rule_match_info.get('dst_port', rule_match_info.get('destination_port'))
        
        action_str = rule.get('action', 'deny').lower()
        
        self.logger.info(f"Processing rule '{rule_id}' (Action: {action_str}, Protocol: {protocol})")
        
        # Resolve source and destination IPs
        src_type = rule_match_info.get('src_type')
        src_ip_val = self.resolve_ip_from_type(src_type, src_ip, controller_ip)
        
        dst_type = rule_match_info.get('dst_type')
        dst_ip_val = self.resolve_ip_from_type(dst_type, dst_ip, controller_ip)
        
        # Create match dict for the flow rule
        match_dict = {'eth_type': 0x0800}  # IPv4
        
        # Add IP protocol if specified
        if protocol == 'tcp':
            match_dict['ip_proto'] = 6
        elif protocol == 'udp':
            match_dict['ip_proto'] = 17
        elif protocol == 'icmp':
            match_dict['ip_proto'] = 1
            
        # Add source IP if specified
        if src_ip_val and src_ip_val != 'any':
            match_dict['ipv4_src'] = src_ip_val
            
        # Add destination IP if specified
        if dst_ip_val and dst_ip_val != 'any':
            match_dict['ipv4_dst'] = dst_ip_val
            
        # Add ports if specified and protocol is TCP or UDP
        if protocol in ['tcp', 'udp']:
            if src_port and src_port != 'any':
                match_dict[f'{protocol}_src'] = int(src_port)
            if dst_port and dst_port != 'any':
                match_dict[f'{protocol}_dst'] = int(dst_port)
                
        # Get OpenFlow actions for the rule
        of_actions = self.get_flow_actions(action_str, {"rule_id": rule_id})
        
        # Set priority based on rule specificity
        base_priority = 100
        specificity = 0
        
        if src_ip_val and src_ip_val != 'any':
            specificity += 10
        if dst_ip_val and dst_ip_val != 'any':
            specificity += 10
        if protocol != 'any':
            specificity += 10
        if src_port and src_port != 'any':
            specificity += 5
        if dst_port and dst_port != 'any':
            specificity += 5
            
        priority = base_priority + specificity
        
        # Safety check: prevent overly generic deny rules
        if action_str == 'deny' and specificity < 20:
            self.logger.warning(f"Rule '{rule_id}' is too generic and action is 'deny'. Skipping to prevent network disruption.")
            return False
        
        # Ensure allow rules have proper actions
        if action_str == 'allow' and not of_actions:
            self.logger.info("Using default NORMAL action for allow rule")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
        
        # Apply the rule to each switch
        for switch_info in switches:
            switch_dpid = switch_info.get('dpid') or switch_info.get('id')
            if not switch_dpid:
                self.logger.warning(f"Could not determine DPID for switch: {switch_info}. Skipping.")
                continue
            
            # Handle nested dictionary DPIDs
            if isinstance(switch_dpid, dict) and ('dpid' in switch_dpid or 'id' in switch_dpid):
                actual_dpid = switch_dpid.get('dpid') or switch_dpid.get('id')
                if actual_dpid:
                    switch_dpid = actual_dpid
                else:
                    self.logger.warning(f"Could not determine DPID from nested dictionary. Skipping.")
                    continue
            
            # Check if switch has empty ports list
            switch_ports = switch_info.get('ports', [])
            if isinstance(switch_ports, list) and len(switch_ports) == 0:
                self.logger.warning(f"Switch '{switch_dpid}' has no ports configured. Installing basic connectivity rule.")
                basic_match = {'eth_type': 0x0800}
                basic_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                
                basic_result = self.sdn_controller.add_flow(
                    switch=switch_dpid,
                    priority=1,
                    match=basic_match,
                    actions=basic_actions,
                    idle_timeout=0,
                    hard_timeout=0
                )
                
                if basic_result:
                    self.logger.info(f"Added basic connectivity flow to switch '{switch_dpid}'")
                    success = True
                continue
            
            self.logger.info(f"Adding flow to switch '{switch_dpid}' for rule '{rule_id}': Match={match_dict}, Actions={of_actions}, Prio={priority}")
            
            # Add the flow rule
            result = self.sdn_controller.add_flow(
                switch=switch_dpid,
                priority=priority,
                match=match_dict,
                actions=of_actions,
                idle_timeout=rule.get('idle_timeout', 0),
                hard_timeout=rule.get('hard_timeout', 0)
            )
            
            if result:
                self.logger.info(f"Successfully added flow for rule '{rule_id}' on switch '{switch_dpid}'")
                success = True
            else:
                self.logger.error(f"Failed to add flow for rule '{rule_id}' on switch '{switch_dpid}'")
                
                # Try fallback action
                fallback_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                self.logger.info(f"Trying fallback action: {fallback_actions}")
                
                result = self.sdn_controller.add_flow(
                    switch=switch_dpid,
                    priority=priority,
                    match=match_dict,
                    actions=fallback_actions,
                    idle_timeout=rule.get('idle_timeout', 0),
                    hard_timeout=rule.get('hard_timeout', 0)
                )
                
                if result:
                    self.logger.info(f"Added flow with fallback action for rule '{rule_id}' on switch '{switch_dpid}'")
                    success = True
                else:
                    self.logger.error(f"Failed to add flow with fallback action for rule '{rule_id}'")
                    
                    # Try basic connectivity flow
                    basic_match = {'eth_type': 0x0800}
                    basic_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                    
                    basic_result = self.sdn_controller.add_flow(
                        switch=switch_dpid,
                        priority=1,
                        match=basic_match,
                        actions=basic_actions
                    )
                    
                    if basic_result:
                        self.logger.info(f"Added basic connectivity flow to switch '{switch_dpid}'")
                    else:
                        self.logger.error(f"Failed to add basic connectivity flow to switch '{switch_dpid}'")
        
        # If no success, try default forward rules for basic connectivity
        if not success:
            for switch_info in switches:
                switch_dpid = switch_info.get('dpid') or switch_info.get('id')
                if not switch_dpid:
                    continue
                    
                default_match = {'eth_type': 0x0800}
                default_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                
                default_result = self.sdn_controller.add_flow(
                    switch=switch_dpid,
                    priority=1,
                    match=default_match,
                    actions=default_actions
                )
                
                if default_result:
                    self.logger.info(f"Added default flow rule to switch '{switch_dpid}'")
                
        return success
