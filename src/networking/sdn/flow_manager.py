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
SDN Flow Manager for Federated Learning Network.

This module provides flow management capabilities for SDN controllers,
helping to implement QoS and security policies for federated learning.
"""

import logging
from typing import Dict, List, Optional, Any, Union
import time
import threading
import os
import json

from src.core.common.logger import LoggerMixin
from src.networking.sdn.sdn_controller import ISDNController
from src.networking.policy.network_policy_handler import IPolicyEngine, PolicyEngine
from src.networking.policy.policy_engine_client import PolicyEngineClient
from src.networking.sdn.flow_rules import PolicyProcessor
from src.networking.sdn.flow_rules_mixin import FlowRulesMixin

class FlowManager(FlowRulesMixin, LoggerMixin):
    """Manages flow rules for SDN controllers in federated learning environments."""
    
    _fallback_icmp_match = {"eth_type": 0x0800, "ip_proto": 1}  # IPv4 and ICMP
    _fallback_priority = 10 # Low priority for fallback rule
    _default_fallback_policy_file = "config/sdn_fallback_policies.json" # Default fallback file

    def __init__(self, sdn_controller: ISDNController, policy_engine: Optional[IPolicyEngine] = None,
                 auto_start_polling: bool = True, polling_interval: int = 30,
                 fallback_policy_file: Optional[str] = None):
        """
        Initialize the flow manager.
        
        Args:
            sdn_controller: SDN controller instance
            policy_engine: Policy engine for policy validation (optional)
            auto_start_polling: Whether to automatically start policy polling
            polling_interval: Interval for policy polling in seconds
            fallback_policy_file: Path to local fallback policy JSON file (optional)
        """
        super().__init__()
        self.sdn_controller = sdn_controller
        self.flow_rules = {}  # Store active flow rules (Note: current policy processing doesn't use this)
        self.polling_active = False
        self.policy_engine_connected: bool = False # Track policy engine connection status
        self._lock = threading.Lock() # Lock for managing connection state
        
        # Load network configuration from environment
        self.network_config = self._load_network_config()
        
        # Initialize policy processor for handling flow rules
        self.policy_processor = PolicyProcessor(sdn_controller, self.network_config)
        
        # Create or use provided policy engine
        self.fallback_policy_file = fallback_policy_file or self._default_fallback_policy_file
        
        # Determine script directory for relative path resolution
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        self.fallback_policy_path = os.path.join(self._script_dir, self.fallback_policy_file)
        
        # Setup Policy Engine and initial status check
        self._setup_policy_engine(policy_engine)
        
        # Register for policy updates
        self.policy_engine.register_policy_callback(self._handle_policy_update)
        
        self.logger.info(f"Initialized FlowManager. Initial policy engine status: {'Connected' if self.policy_engine_connected else 'Disconnected'}")
        
        # Apply initial state based on connection status
        self._apply_initial_state()

        # Start policy polling if requested (will trigger updates)
        if auto_start_polling:
            self.start_policy_polling(polling_interval)
    
    def _setup_policy_engine(self, policy_engine: Optional[IPolicyEngine]) -> None:
        """Sets up the policy engine instance and checks initial connection status."""
        if policy_engine is None:
            # Create a default PolicyEngineClient if none provided
            # Adjust URL based on environment or default
            policy_engine_url = os.environ.get("POLICY_ENGINE_URL", "http://policy-engine:5000")
            self.policy_engine = PolicyEngineClient(policy_engine_url=policy_engine_url)
            self.owns_policy_engine = True
            # Check initial status for the created client
            self.policy_engine_connected = self.policy_engine.check_policy_engine_status()
        else:
            self.policy_engine = policy_engine
            self.owns_policy_engine = False
            # Check initial status if it's a client instance
            if isinstance(self.policy_engine, PolicyEngineClient):
                self.policy_engine_connected = self.policy_engine.check_policy_engine_status()
            else:
                # Assume non-client implementations are always 'connected' for status purposes
                self.policy_engine_connected = True

    def _apply_initial_state(self) -> None:
        """Applies the initial flow rules based on policy engine connectivity."""
        if self.policy_engine_connected:
            # Fetch and apply policies from the engine
            self.logger.info("Policy engine connected initially. Fetching policies...")
            try:
                initial_policies = self.policy_engine.get_policies()
                self._process_policies(initial_policies)
            except Exception as e:
                self.logger.error(f"Error fetching initial policies from engine: {e}")
                # Critical failure even though status check passed? Apply minimal fallback.
                self.policy_engine_connected = False # Correct status
                self._apply_fallback_rules() 
        else:
            # Initial connection failed, try local fallback file
            self.logger.warning("Initial connection to policy engine failed. Attempting to load fallback policies from file.")
            fallback_policies = self._load_fallback_policies()
            if fallback_policies:
                self.logger.info(f"Successfully loaded {len(fallback_policies)} policies from fallback file: {self.fallback_policy_path}")
                self._process_policies(fallback_policies)
            else:
                # Loading fallback file also failed, apply minimal ICMP rule
                self.logger.error(f"Failed to load fallback policies from {self.fallback_policy_path}. Applying minimal ICMP fallback rule.")
                self._apply_fallback_rules()

    def _load_fallback_policies(self) -> Optional[List[Dict[str, Any]]]:
        """Loads policies from the local fallback JSON file."""
        try:
            # Use the absolute path determined in __init__
            if not os.path.exists(self.fallback_policy_path):
                 self.logger.error(f"Fallback policy file not found at: {self.fallback_policy_path}")
                 return None
                 
            with open(self.fallback_policy_path, 'r') as f:
                data = json.load(f)
                if "policies" in data and isinstance(data["policies"], list):
                     # Basic validation: ensure policies is a list
                     # Further validation could be added here if needed
                     return data["policies"]
                else:
                     self.logger.error(f"Invalid format in fallback policy file {self.fallback_policy_path}: 'policies' key missing or not a list.")
                     return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from fallback policy file {self.fallback_policy_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading fallback policy file {self.fallback_policy_path}: {e}")
            return None

    def _load_network_config(self) -> Dict[str, Any]:
        """Load network configuration from environment variables."""
        config = {}
        # Load all NODE_IP_ environment variables, store keys in uppercase for consistent access
        for key, value in os.environ.items():
            if key.startswith("NODE_IP_"):
                config[key.upper()] = value
        
        config['SUBNET_PREFIX'] = os.environ.get('SUBNET_PREFIX', '192.168.100')
        
        # Ensure core services have their IPs, using consistent keys (uppercase)
        # These will use the value from the loop if present, or the default.
        config['NODE_IP_FL_SERVER'] = config.get('NODE_IP_FL_SERVER', '192.168.100.10')
        config['NODE_IP_POLICY_ENGINE'] = config.get('NODE_IP_POLICY_ENGINE', '192.168.100.20')
        config['NODE_IP_SDN_CONTROLLER'] = config.get('NODE_IP_SDN_CONTROLLER', '192.168.100.41')
        config['NODE_IP_COLLECTOR'] = config.get('NODE_IP_COLLECTOR') # Will be None if not set

        client_ip_range_str = os.environ.get('CLIENT_IP_RANGE', '100-255')
        try:
            start, end = client_ip_range_str.split('-')
            config['CLIENT_IP_START'] = int(start)
            config['CLIENT_IP_END'] = int(end)
        except (ValueError, AttributeError):
            config['CLIENT_IP_START'] = 100
            config['CLIENT_IP_END'] = 255
            self.logger.warning(f"Failed to parse CLIENT_IP_RANGE '{client_ip_range_str}', using default 100-255")
        
        config['FL_SERVER_PORT'] = int(os.environ.get('FL_SERVER_PORT', '8080'))
        config['POLICY_PORT'] = int(os.environ.get('POLICY_PORT', '5000'))
        
        self.logger.info(f"Loaded network configuration. Found {len(config)} entries.")
        self.logger.debug(f"Full network_config: {json.dumps(config, indent=2)}")
        return config

    def _resolve_ip_from_type(self, entity_type: Optional[str], entity_ip_val: Optional[str]) -> str:
        """
        Resolves an entity type or direct IP to a specific IP address or 'any'.
        Returns 'any' if resolution implies a wildcard.
        """
        # Normalize entity_ip_val: treat None, empty string, or '*' as 'any'
        normalized_ip_val = entity_ip_val.lower() if entity_ip_val else 'any'
        if normalized_ip_val == '*' or normalized_ip_val == '':
            normalized_ip_val = 'any'

        # If entity_ip_val is a specific IP (not 'any'), prioritize it.
        if normalized_ip_val != 'any':
            # Basic IP validation could be done here (e.g. regex for IP format)
            return normalized_ip_val # Return the specific IP

        # If no type, and IP is 'any', return 'any'.
        if not entity_type:
            return 'any'

        entity_type_lower = entity_type.lower()
        resolved_ip: Optional[str] = None
        
        # Standardized keys for looking up in self.network_config (which should have uppercase keys)
        config_key_map = {
            'fl-server': 'NODE_IP_FL_SERVER',
            'policy-engine': 'NODE_IP_POLICY_ENGINE',
            'sdn-controller': 'NODE_IP_SDN_CONTROLLER',
            'collector': 'NODE_IP_COLLECTOR',
        }

        if entity_type_lower in config_key_map:
            resolved_ip = self.network_config.get(config_key_map[entity_type_lower])
        elif entity_type_lower.startswith('fl-client-'): # e.g. fl-client-1
            # Construct the key like NODE_IP_FL_CLIENT_1
            node_ip_env_var = f"NODE_IP_{entity_type.upper().replace('-', '_')}"
            resolved_ip = self.network_config.get(node_ip_env_var)
        elif entity_type_lower == 'openvswitch': 
             # Construct the key like NODE_IP_OPENVSWITCH
             node_ip_env_var = f"NODE_IP_{entity_type.upper().replace('-', '_')}"
             resolved_ip = self.network_config.get(node_ip_env_var)
        elif entity_type_lower == 'fl-client': # Generic 'fl-client' type.
            # This implies 'any' client as normalized_ip_val is 'any' at this point.
            return 'any'
        
        if resolved_ip:
            self.logger.debug(f"Resolved type '{entity_type}' to IP: {resolved_ip}")
            return resolved_ip
        else:
            # If type not recognized or not in config, and normalized_ip_val was 'any', stick to 'any'.
            self.logger.debug(f"Could not resolve type '{entity_type}' to a specific IP via config. Defaulting to 'any'.")
            return 'any' 

    def _handle_policy_update(self, policies: List[Dict[str, Any]]) -> None:
        """Handle policy updates from the policy engine or fallback."""
        self.logger.info(f"FlowManager: Received {len(policies)} policies to handle.")
        self.logger.debug(f"FlowManager: Raw policies received: {json.dumps(policies, indent=2)}")

        if not policies and not self.policy_engine_connected:
            self.logger.warning("FlowManager: No policies received and policy engine is disconnected. Maintaining current state.")
            return

        with self._lock:
            if self.policy_engine_connected:
                # Policy engine is connected (or assumed connected)
                if not self.policy_engine_connected:
                    # Transitioned from disconnected to connected
                    self.logger.info("Policy engine connection restored. Applying policies.")
                    self.policy_engine_connected = True
                    # Remove fallback rules before applying current policies
                    self._remove_fallback_rules()
                    # Process the latest full set of policies
                    self._process_policies(policies) 
                else:
                    # Still connected, process the update
                    self.logger.info("Received policy update while connected. Applying changes.")
                    # TODO: Ideally, only process *changes* or clear old rules first.
                    # Current _process_policies applies the full set, potentially overwriting.
                    # For now, re-applying the full set is the implemented behavior.
                    self._process_policies(policies)
            else:
                # Policy engine is disconnected
                if self.policy_engine_connected:
                    # Transitioned from connected to disconnected
                    self.logger.warning("Policy engine connection lost. Applying fallback rules.")
                    self.policy_engine_connected = False
                    # Apply fallback rules (potentially overwriting existing rules)
                    self._apply_fallback_rules()
                else:
                    # Still disconnected, ensure fallback rules are present (idempotent apply)
                    self.logger.debug("Policy engine still disconnected. Ensuring fallback rules are active.")
                    self._apply_fallback_rules() # Re-apply to be safe

    def _apply_fallback_rules(self) -> None:
        """Apply fallback rules when the policy engine is unreachable."""
        self.logger.info("FlowManager: Applying fallback ICMP allow rule.")
        switches = self.sdn_controller.get_switches()
        self.logger.debug(f"FlowManager: _apply_fallback_rules - Switches found: {json.dumps(switches, indent=2)}")
        if not switches:
             self.logger.warning("FlowManager: Cannot apply fallback rules: No switches found.")
             return
             
        for switch in switches:
            try:
                switch_dpid = switch.get('dpid') or switch.get('id') # Get DPID, fallback to ID
                if not switch_dpid:
                    self.logger.warning(f"Could not determine DPID for switch: {switch}. Skipping fallback rule for this switch.")
                    continue

                # Check if switch_dpid is actually a dictionary instead of a string/int
                if isinstance(switch_dpid, dict) and ('dpid' in switch_dpid or 'id' in switch_dpid):
                    # This suggests switch_dpid was incorrectly assigned to the whole switch object
                    actual_dpid = switch_dpid.get('dpid') or switch_dpid.get('id')
                    if actual_dpid:
                        switch_dpid = actual_dpid
                    else:
                        self.logger.warning(f"Could not determine DPID from nested dictionary: {switch_dpid}. Skipping fallback rule for this switch.")
                        continue

                switch_name = switch.get('name', str(switch_dpid))
                
                success = self.sdn_controller.add_flow(
                    switch=switch_dpid,
                    priority=self._fallback_priority, 
                    match=self._fallback_icmp_match,
                    actions=[{"type": "FORWARD"}],
                    idle_timeout=0, # Persistent rule
                    hard_timeout=0
                )
                if success:
                    self.logger.debug(f"FlowManager: Applied fallback ICMP rule to switch {switch_name}")
                else:
                    self.logger.error(f"FlowManager: Failed to apply fallback ICMP rule to switch {switch_name}")
            except Exception as e:
                 self.logger.error(f"FlowManager: Error applying fallback rule to switch {switch.get('name', str(switch))}: {e}", exc_info=True)

    def _remove_fallback_rules(self) -> None:
        """Remove fallback rules when the policy engine is reachable again."""
        self.logger.info("FlowManager: Removing fallback ICMP allow rule.")
        switches = self.sdn_controller.get_switches()
        if not switches:
             self.logger.warning("FlowManager: Cannot remove fallback rules: No switches found.")
             return
             
        for switch in switches:
            try:
                switch_dpid = switch.get('dpid') or switch.get('id') # Get DPID, fallback to ID
                if not switch_dpid:
                    self.logger.warning(f"Could not determine DPID for switch: {switch}. Skipping fallback rule removal for this switch.")
                    continue

                # Check if switch_dpid is actually a dictionary instead of a string/int
                if isinstance(switch_dpid, dict) and ('dpid' in switch_dpid or 'id' in switch_dpid):
                    # This suggests switch_dpid was incorrectly assigned to the whole switch object
                    actual_dpid = switch_dpid.get('dpid') or switch_dpid.get('id')
                    if actual_dpid:
                        switch_dpid = actual_dpid
                    else:
                        self.logger.warning(f"Could not determine DPID from nested dictionary: {switch_dpid}. Skipping fallback rule removal for this switch.")
                        continue

                switch_name = switch.get('name', str(switch_dpid))
                
                # Remove the specific fallback flow using its match criteria and priority
                success = self.sdn_controller.remove_flow(
                    switch=switch_dpid,
                    match=self._fallback_icmp_match,
                    priority=self._fallback_priority 
                )
                # Note: remove_flow might need exact match or just the cookie/ID depending on controller impl.
                # Add priority matching if the controller supports it, otherwise this might fail.
                if success:
                    self.logger.debug(f"FlowManager: Removed fallback ICMP rule from switch {switch_name}")
                else:
                    # Log warning instead of error, maybe rule didn't exist or controller limitation
                    self.logger.warning(f"FlowManager: Failed to remove fallback ICMP rule from switch {switch_name}. May require manual cleanup or controller limitation.")
            except Exception as e:
                 self.logger.error(f"FlowManager: Error removing fallback rule from switch {switch.get('name', str(switch))}: {e}", exc_info=True)
    
    def remove_client_flows(self, client_id: str) -> bool:
        """
        Remove all flow rules for a specific client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: Success or failure
        """
        try:
            if client_id not in self.flow_rules:
                self.logger.warning(f"FlowManager: No flow rules found for client {client_id}")
                return True
            
            success = True
            
            # Get flow rules for this client
            client_flows_to_remove = self.flow_rules.get(client_id, [])
            if not client_flows_to_remove:
                return True # Nothing to remove
            
            # Get current switches to map stored name to ID
            current_switches = {s['name']: s['id'] for s in self.sdn_controller.get_switches() if 'name' in s and 'id' in s}
            if not current_switches:
                self.logger.warning("FlowManager: Cannot remove flows as no switches were found currently.")
                # Can't map name to ID, potentially leaving stale entries in self.flow_rules
                # Consider if self.flow_rules should be cleared anyway or error returned.
                # For now, return False as the operation could not be fully performed.
                return False 

            removed_flows_indices = []
            for idx, flow in enumerate(client_flows_to_remove):
                stored_switch_name = flow.get("switch")
                if not stored_switch_name:
                     self.logger.warning(f"FlowManager: Flow rule entry for client {client_id} is missing 'switch' name. Skipping removal.")
                     continue
                     
                switch_id = current_switches.get(stored_switch_name)
                if not switch_id:
                    self.logger.warning(f"FlowManager: Could not find current switch ID for stored name '{stored_switch_name}' for client {client_id}. Skipping removal for this switch.")
                    # Mark as failure, as we couldn't remove this specific rule instance
                    success = False
                    continue

                rule_removed = False
                if flow["type"] == "qos":
                    client_ip = flow["client_ip"]
                    server_ip = flow["server_ip"]
                    match1 = {"nw_src": client_ip, "nw_dst": server_ip, "dl_type": 0x0800}
                    match2 = {"nw_src": server_ip, "nw_dst": client_ip, "dl_type": 0x0800}
                    
                    removed1 = self.sdn_controller.remove_flow(switch=switch_id, match=match1)
                    removed2 = self.sdn_controller.remove_flow(switch=switch_id, match=match2)
                    if not removed1 or not removed2:
                         self.logger.warning(f"Failed to fully remove QoS flow for {client_id} on switch {stored_switch_name} (ID: {switch_id})")
                         success = False # Mark overall operation as potentially incomplete
                    else:
                         rule_removed = True
                
                elif flow["type"] == "security":
                    target_ip = flow["target_ip"]
                    match = {"nw_src": target_ip, "dl_type": 0x0800}
                    if not self.sdn_controller.remove_flow(switch=switch_id, match=match):
                        self.logger.warning(f"Failed to remove security flow for {target_ip} on switch {stored_switch_name} (ID: {switch_id})")
                        success = False
                    else:
                        rule_removed = True
                
                # Add similar logic for other flow types if needed (time_based, bandwidth_guarantee, etc.)
                # Currently, only QoS and Security types seem to have specific removal logic here.
                # Other types might rely on general policy updates overwriting/removing them.
                else:
                     self.logger.debug(f"Skipping explicit removal for flow type {flow.get('type')} for client {client_id} on switch {stored_switch_name}. Assumed managed by policy overwrite.")
                     # We might still want to remove the tracking entry if we assume it's gone
                     rule_removed = True # Assume it's handled elsewhere or doesn't need specific removal command

                if rule_removed:
                    removed_flows_indices.append(idx)
            
            # Clean up tracking data for successfully removed rules
            # Iterate backwards to avoid index issues when removing
            for idx in sorted(removed_flows_indices, reverse=True):
                 client_flows_to_remove.pop(idx)
                 
            # If the list becomes empty after removals, delete the client entry
            if not client_flows_to_remove:
                 del self.flow_rules[client_id]
                 self.logger.info(f"FlowManager: Removed all tracked flow rules for client {client_id}")
            elif removed_flows_indices: # Only log if something was actually removed
                 self.logger.info(f"FlowManager: Removed {len(removed_flows_indices)} tracked flow rule instances for client {client_id}")
            
            if not success:
                self.logger.warning(f"FlowManager: Partially removed flow rules for client {client_id}. Some rules may remain active or untracked.")
            
            return success # Return True if all attempted removals succeeded, False otherwise
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error removing client flows for {client_id}: {e}", exc_info=True)
            return False
    
    def get_active_flows(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active flow rules, optionally filtered by client ID.
        
        Args:
            client_id: Client identifier (optional)
            
        Returns:
            List[Dict]: List of active flow rules
        """
        try:
            if client_id is not None:
                return self.flow_rules.get(client_id, [])
            
            # Flatten all flow rules into a single list
            all_flows = []
            for client, flows in self.flow_rules.items():
                for flow in flows:
                    flow_with_client = flow.copy()
                    flow_with_client["client_id"] = client
                    all_flows.append(flow_with_client)
            
            return all_flows
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error getting active flows: {e}", exc_info=True)
            return []
    
    def clear_all_flows(self) -> bool:
        """
        Remove all flow rules managed by this flow manager.
        
        Returns:
            bool: Success or failure
        """
        try:
            success = True
            
            # Get all client IDs
            client_ids = list(self.flow_rules.keys())
            
            # Remove flows for each client
            for client_id in client_ids:
                if not self.remove_client_flows(client_id):
                    success = False
            
            if success:
                self.logger.info("FlowManager: Cleared all flow rules")
            else:
                self.logger.warning("FlowManager: Partially cleared flow rules")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error clearing all flows: {e}", exc_info=True)
            return False
    
    def apply_network_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply a network policy to the SDN network.
        
        Args:
            policy: Network policy configuration
            
        Returns:
            bool: Success or failure
        """
        try:
            # Validate the policy with the policy engine first
            validation = self.policy_engine.validate_policy(policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Policy denied: {validation['message']}")
                return False
            
            # Use potentially modified policy
            if "policy" in validation and validation["status"] in ["approved", "modified"]:
                policy = validation["policy"]
            
            policy_type = policy.get("type", "unknown")
            
            if policy_type == "qos":
                client_id = policy.get("client_id")
                client_ip = policy.get("client_ip")
                server_ip = policy.get("server_ip")
                priority_level = policy.get("priority_level", "medium")
                
                if not client_id or not client_ip or not server_ip:
                    self.logger.error("Missing required parameters for QoS policy")
                    return False
                
                return self.add_client_qos_flow(client_id, client_ip, server_ip, priority_level)
                
            elif policy_type == "security":
                target_ip = policy.get("target_ip")
                reason = policy.get("reason", "security_policy")
                
                if not target_ip:
                    self.logger.error("Missing target IP for security policy")
                    return False
                
                return self.add_security_flow(target_ip, reason)
                
            elif policy_type == "bandwidth":
                client_id = policy.get("client_id")
                client_ip = policy.get("client_ip")
                bandwidth_mbps = policy.get("bandwidth_mbps", 10)
                
                if not client_id or not client_ip:
                    self.logger.error("Missing required parameters for bandwidth policy")
                    return False
                
                return self.add_bandwidth_limit_flow(client_id, client_ip, bandwidth_mbps)
                
            elif policy_type == "time_based":
                client_id = policy.get("client_id")
                client_ip = policy.get("client_ip")
                server_ip = policy.get("server_ip")
                time_window = policy.get("time_window")
                days_of_week = policy.get("days_of_week")
                
                if not client_id or not client_ip or not server_ip or not time_window:
                    self.logger.error("Missing required parameters for time-based policy")
                    return False
                
                return self.add_time_based_flow(client_id, client_ip, server_ip, time_window, days_of_week)
                
            elif policy_type == "bandwidth_guarantee":
                client_id = policy.get("client_id")
                client_ip = policy.get("client_ip")
                server_ip = policy.get("server_ip")
                min_bandwidth_mbps = policy.get("min_bandwidth_mbps", 10)
                
                if not client_id or not client_ip or not server_ip:
                    self.logger.error("Missing required parameters for bandwidth guarantee policy")
                    return False
                
                return self.add_bandwidth_guarantee_flow(client_id, client_ip, server_ip, min_bandwidth_mbps)
                
            elif policy_type == "traffic_priority":
                traffic_type = policy.get("traffic_type")
                src_ip = policy.get("src_ip")
                dst_ip = policy.get("dst_ip")
                dst_port = policy.get("dst_port", 0)
                priority_level = policy.get("priority_level", "medium")
                
                if not traffic_type or not src_ip or not dst_ip:
                    self.logger.error("Missing required parameters for traffic priority policy")
                    return False
                
                return self.add_traffic_priority_flow(traffic_type, src_ip, dst_ip, dst_port, priority_level)
                
            elif policy_type == "anomaly_detection":
                target_ip = policy.get("target_ip")
                protocol = policy.get("protocol", "tcp")
                port = policy.get("port", 0)
                threshold_pps = policy.get("threshold_pps", 1000)
                window_seconds = policy.get("window_seconds", 10)
                
                if not target_ip or not protocol:
                    self.logger.error("Missing required parameters for anomaly detection policy")
                    return False
                
                return self.add_anomaly_detection_flow(target_ip, protocol, port, threshold_pps, window_seconds)
                
            elif policy_type == "path_selection":
                src_ip = policy.get("src_ip")
                dst_ip = policy.get("dst_ip")
                path_nodes = policy.get("path_nodes", [])
                priority = policy.get("priority", 150)
                protocol = policy.get("protocol", "any")
                
                if not src_ip or not dst_ip or not path_nodes:
                    self.logger.error("Missing required parameters for path selection policy")
                    return False
                
                return self.add_path_selection_flow(src_ip, dst_ip, path_nodes, priority, protocol)
                
            else:
                self.logger.error(f"Unknown policy type: {policy_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"FlowManager: Error applying network policy: {e}", exc_info=True)
            return False
    
    def check_path_policy_compliance(self, src_ip: str, dst_ip: str, 
                                   protocol: str = "any", port: int = 0) -> bool:
        """
        Check if a communication path complies with security policies.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            protocol: Protocol (tcp, udp, icmp, any)
            port: Destination port
            
        Returns:
            bool: Whether the path is compliant with security policies
        """
        return self.policy_engine.authorize_flow(src_ip, dst_ip, protocol, port)
    
    def get_client_policy(self, client_id: str) -> Dict[str, Any]:
        """
        Get the policy configuration for a specific client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict: Client policy configuration
        """
        policy = {
            "priority": self.policy_engine.get_client_priority(client_id),
            "flows": self.get_active_flows(client_id)
        }
        
        return policy
    
    def cleanup(self) -> None:
        """Clean up resources when shutting down."""
        try:
            # Stop policy polling if active
            if hasattr(self, 'polling_active') and self.polling_active:
                self.stop_policy_polling()
                
            # Clear all flows
            self.clear_all_flows()
            
            # Unregister from policy engine
            self.policy_engine.unregister_policy_callback(self._handle_policy_update)
            
            # Clean up policy engine if we own it
            if self.owns_policy_engine:
                self.policy_engine.cleanup()
        except Exception as e:
            self.logger.error(f"FlowManager: Error during cleanup: {e}", exc_info=True)
    
    def start_policy_polling(self, interval_seconds: int = 30) -> None:
        """
        Start polling for policy updates from the policy engine.
        
        Args:
            interval_seconds: Interval between policy checks in seconds
        """
        if self.polling_active:
            self.logger.warning("FlowManager: Policy polling already active")
            return
        
        self.polling_interval = interval_seconds
        self.polling_active = True
        
        self.logger.info(f"FlowManager: Starting policy polling thread with interval {interval_seconds}s")
        
        # Start polling in a separate thread
        def poll_policies():
            self.logger.info("FlowManager: Policy polling thread started")
            
            while self.polling_active:
                try:
                    # Get policies from policy engine
                    policies = self.policy_engine.get_policies()
                    
                    if policies:
                        self.logger.info(f"FlowManager: Received {len(policies)} policies from policy engine")
                        # Process policies
                        for policy in policies:
                            if policy.get("enabled", True):
                                # Apply the policy
                                self.logger.debug(f"FlowManager: Processing policy: {policy.get('name', 'Unnamed')} (type: {policy.get('type')})")
                                self.apply_network_policy(policy)
                    else:
                        self.logger.debug("FlowManager: No policies received from policy engine, will retry later")
                    
                except Exception as e:
                    self.logger.error(f"FlowManager: Error polling policies: {e}", exc_info=True)
                
                # Wait for next polling interval
                time.sleep(interval_seconds)
            
            self.logger.info("FlowManager: Policy polling thread stopped")
        
        # Start the polling thread
        self.polling_thread = threading.Thread(target=poll_policies)
        self.polling_thread.daemon = True
        self.polling_thread.start()
    
    def stop_policy_polling(self) -> None:
        """Stop polling for policy updates."""
        self.polling_active = False
        self.logger.info("FlowManager: Policy polling thread stopped")
    
    def _process_policies(self, policies: List[Dict[str, Any]]) -> None:
        """
        Process and apply policies using the PolicyProcessor.
        
        Args:
            policies: List of policy objects
        """
        # Delegate to PolicyProcessor with optional handlers for specific policy types
        result = self.policy_processor.process_policies(
            policies,
            qos_handler=getattr(self, '_process_qos_policy', None),
            security_handler=getattr(self, '_process_security_policy', None),
            time_window_handler=getattr(self, '_process_time_window_policy', None),
            bandwidth_handler=getattr(self, '_process_bandwidth_policy', None)
        )
        
        self.logger.info(f"FlowManager: Policy processing complete. Successful: {len(result['successful'])}, Failed: {len(result['failed'])}")
    
    def _process_network_security_policy(self, policy: Dict[str, Any]) -> None:
        """
        Process a network security policy and install corresponding flow rules.
        Delegates to PolicyProcessor.
        """
        self.policy_processor.process_network_security_policy(policy)
    
    # Delegate to PolicyProcessor for flow action conversion
    def _get_flow_actions(self, action_str, rule_context=None):
        """
        Convert action string to OpenFlow actions.
        Delegates to PolicyProcessor.
        """
        return self.policy_processor.get_flow_actions(action_str, rule_context)

    def _get_switches(self):
        """
        Get available switches with better error handling and diagnostics.
        Delegates to PolicyProcessor.
        """
        return self.policy_processor.get_switches()
            
    def _process_single_network_rule(self, rule_id, rule, controller_ip=None, switch=None):
        """
        Process a network security policy rule and convert it to flow rules.
        Delegates to PolicyProcessor.
        """
        return self.policy_processor.process_single_network_rule(rule_id, rule, controller_ip, switch)
