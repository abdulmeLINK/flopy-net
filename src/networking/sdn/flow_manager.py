#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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

class FlowManager(LoggerMixin):
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

    def add_client_qos_flow(self, client_id: str, client_ip: str, 
                           server_ip: str, priority_level: str) -> bool:
        """
        Add QoS flow rules for a federated learning client.
        
        Args:
            client_id: Client identifier
            client_ip: Client IP address
            server_ip: FL server IP address
            priority_level: Priority level (high, medium, low)
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create QoS policy object
            qos_policy = {
                "type": "qos",
                "client_id": client_id,
                "client_ip": client_ip,
                "server_ip": server_ip,
                "priority_level": priority_level
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(qos_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"QoS policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation:
                qos_policy = validation["policy"]
                priority_level = qos_policy["priority_level"]
            
            success = True
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            # Check if the flow is authorized
            if not self.policy_engine.authorize_flow(client_ip, server_ip):
                self.logger.warning(f"Flow from {client_ip} to {server_ip} not authorized by policy")
                return False
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Add flow for client -> server traffic
                if hasattr(self.sdn_controller, 'add_qos_flow'):
                    success &= self.sdn_controller.add_qos_flow(
                        switch_name, client_ip, server_ip, priority_level
                    )
                else:
                    self.logger.warning(f"FlowManager: SDN Controller does not support add_qos_flow. Skipping QoS for client {client_id} on switch {switch_name}.")
                
                # Add flow for server -> client traffic
                if hasattr(self.sdn_controller, 'add_qos_flow'):
                    success &= self.sdn_controller.add_qos_flow(
                        switch_name, server_ip, client_ip, priority_level
                    )
                else:
                    # Warning logged above
                    pass
                
                # Store flow rule information
                if client_id not in self.flow_rules:
                    self.flow_rules[client_id] = []
                
                self.flow_rules[client_id].append({
                    "type": "qos",
                    "switch": switch_name,
                    "client_ip": client_ip,
                    "server_ip": server_ip,
                    "priority_level": priority_level
                })
            
            if success:
                self.logger.info(f"FlowManager: Added QoS flow rules for client {client_id} with priority {priority_level}")
            else:
                self.logger.warning(f"FlowManager: Partially added QoS flow rules for client {client_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding QoS flow rules: {e}", exc_info=True)
            return False
    
    def add_security_flow(self, target_ip: str, reason: str = "security_policy") -> bool:
        """
        Add security flow rules to block traffic from a specific IP.
        
        Args:
            target_ip: IP address to block
            reason: Reason for blocking
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create security policy object
            security_policy = {
                "type": "security",
                "target_ip": target_ip,
                "reason": reason
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(security_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Security policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation:
                security_policy = validation["policy"]
            
            success = True
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Add blocking flow rule
                if hasattr(self.sdn_controller, 'add_security_flow'):
                    if not self.sdn_controller.add_security_flow(switch_name, target_ip):
                        success = False
                else:
                     self.logger.warning(f"FlowManager: SDN Controller does not support add_security_flow. Cannot block {target_ip} on switch {switch_name}.")
                     success = False # Mark as failure since we cannot block
                
                # Store flow rule information
                if target_ip not in self.flow_rules:
                    self.flow_rules[target_ip] = []
                
                self.flow_rules[target_ip].append({
                    "type": "security",
                    "switch": switch_name,
                    "target_ip": target_ip,
                    "reason": reason
                })
            
            if success:
                self.logger.info(f"FlowManager: Added security flow rules to block {target_ip} for {reason}")
            else:
                self.logger.warning(f"FlowManager: Partially added security flow rules for {target_ip}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding security flow rules: {e}", exc_info=True)
            return False
    
    def add_bandwidth_limit_flow(self, client_id: str, client_ip: str, 
                                bandwidth_mbps: int) -> bool:
        """
        Add flow rules to limit bandwidth for a client.
        
        Args:
            client_id: Client identifier
            client_ip: Client IP address
            bandwidth_mbps: Bandwidth limit in Mbps
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create bandwidth policy object
            bandwidth_policy = {
                "type": "bandwidth",
                "client_id": client_id,
                "client_ip": client_ip,
                "bandwidth_mbps": bandwidth_mbps
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(bandwidth_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Bandwidth policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation and validation["status"] in ["approved", "modified"]:
                bandwidth_policy = validation["policy"]
                bandwidth_mbps = bandwidth_policy["bandwidth_mbps"]
            
            # This is a placeholder for bandwidth limiting
            # In a real implementation, this would configure meters/queues
            # that would be applied to the client's traffic
            
            self.logger.warning("Bandwidth limiting is not currently implemented")
            
            # Store flow rule information anyway for tracking
            if client_id not in self.flow_rules:
                self.flow_rules[client_id] = []
            
            self.flow_rules[client_id].append({
                "type": "bandwidth_limit",
                "client_ip": client_ip,
                "bandwidth_mbps": bandwidth_mbps
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding bandwidth limit flow rules: {e}", exc_info=True)
            return False
    
    def add_time_based_flow(self, client_id: str, client_ip: str, 
                          server_ip: str, time_window: str,
                          days_of_week: Optional[List[str]] = None) -> bool:
        """
        Add time-based flow rules for a federated learning client.
        
        Args:
            client_id: Client identifier
            client_ip: Client IP address
            server_ip: FL server IP address
            time_window: Time window for access (format: "HH:MM-HH:MM")
            days_of_week: List of days when access is allowed (optional)
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create time-based policy object
            time_policy = {
                "type": "time_based",
                "client_id": client_id,
                "client_ip": client_ip,
                "server_ip": server_ip,
                "time_window": time_window,
                "days_of_week": days_of_week or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(time_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Time-based policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation:
                time_policy = validation["policy"]
                time_window = time_policy["time_window"]
                days_of_week = time_policy["days_of_week"]
            
            success = True
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            # Check if the time-based flow is currently authorized
            import datetime
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            current_day = now.strftime("%a").lower()
            
            # Parse time window
            start_time, end_time = time_window.split("-")
            
            # Check if current time is within window
            time_allowed = start_time <= current_time <= end_time
            day_allowed = current_day in days_of_week
            
            is_active = time_allowed and day_allowed
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Add meta information for the time-based flow
                meta = {
                    "time_window": time_window,
                    "days_of_week": days_of_week,
                    "is_active": is_active
                }
                
                # Add flow rules if currently active
                if is_active:
                    # Add flow for client -> server traffic
                    success &= self.sdn_controller.add_flow(
                        switch=switch["id"], 
                        priority=100, 
                        match={"ipv4_src": client_ip, "ipv4_dst": server_ip},
                        actions=[{"type": "FORWARD"}],
                        idle_timeout=0,
                        hard_timeout=0
                    )
                    
                    # Add flow for server -> client traffic
                    success &= self.sdn_controller.add_flow(
                        switch=switch["id"], 
                        priority=100, 
                        match={"ipv4_src": server_ip, "ipv4_dst": client_ip},
                        actions=[{"type": "FORWARD"}],
                        idle_timeout=0,
                        hard_timeout=0
                    )
                
                # Store time-based flow rule information
                if client_id not in self.flow_rules:
                    self.flow_rules[client_id] = []
                
                self.flow_rules[client_id].append({
                    "type": "time_based",
                    "switch": switch_name,
                    "client_ip": client_ip,
                    "server_ip": server_ip,
                    "time_window": time_window,
                    "days_of_week": days_of_week,
                    "is_active": is_active
                })
            
            if success:
                self.logger.info(f"FlowManager: Added time-based flow rules for client {client_id} with window {time_window}")
                if is_active:
                    self.logger.info(f"FlowManager: Time-based flow for client {client_id} is currently active")
                else:
                    self.logger.info(f"FlowManager: Time-based flow for client {client_id} is currently inactive")
            else:
                self.logger.warning(f"FlowManager: Partially added time-based flow rules for client {client_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding time-based flow rules: {e}", exc_info=True)
            return False
    
    def add_bandwidth_guarantee_flow(self, client_id: str, client_ip: str, 
                                   server_ip: str, min_bandwidth_mbps: int) -> bool:
        """
        Add flow rules with minimum bandwidth guarantee for a client.
        
        Args:
            client_id: Client identifier
            client_ip: Client IP address
            server_ip: FL server IP address
            min_bandwidth_mbps: Minimum guaranteed bandwidth in Mbps
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create bandwidth guarantee policy object
            bw_policy = {
                "type": "bandwidth_guarantee",
                "client_id": client_id,
                "client_ip": client_ip,
                "server_ip": server_ip,
                "min_bandwidth_mbps": min_bandwidth_mbps
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(bw_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Bandwidth guarantee policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation:
                bw_policy = validation["policy"]
                min_bandwidth_mbps = bw_policy["min_bandwidth_mbps"]
            
            success = True
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Create QoS queue with minimum bandwidth guarantee
                queue_id = f"queue_{client_id}"
                port = 1  # Default port, should be determined dynamically
                
                # Configure queue with minimum bandwidth guarantee
                queue_config = {
                    "type": "min-rate",
                    "min_rate": min_bandwidth_mbps * 1000,  # Convert to Kbps
                    "queue_id": queue_id
                }
                
                # Try to create queue using SDN controller
                if hasattr(self.sdn_controller, 'create_qos_queue'):
                    success &= self.sdn_controller.create_qos_queue(
                        switch_id=switch["id"], port=port, queue_config=queue_config
                    )
                else:
                    self.logger.warning(f"FlowManager: SDN Controller does not support creating QoS queues")
                    success = False
                
                # Add flow rule to direct traffic to queue
                if success:
                    # Add flow for client -> server traffic
                    success &= self.sdn_controller.add_flow(
                        switch=switch["id"], 
                        priority=200, 
                        match={"ipv4_src": client_ip, "ipv4_dst": server_ip},
                        actions=[{"type": "SET_QUEUE", "queue_id": queue_id}, {"type": "FORWARD"}],
                        idle_timeout=0,
                        hard_timeout=0
                    )
                    
                    # Add flow for server -> client traffic
                    success &= self.sdn_controller.add_flow(
                        switch=switch["id"], 
                        priority=200, 
                        match={"ipv4_src": server_ip, "ipv4_dst": client_ip},
                        actions=[{"type": "SET_QUEUE", "queue_id": queue_id}, {"type": "FORWARD"}],
                        idle_timeout=0,
                        hard_timeout=0
                    )
                
                # Store bandwidth guarantee flow rule information
                if client_id not in self.flow_rules:
                    self.flow_rules[client_id] = []
                
                self.flow_rules[client_id].append({
                    "type": "bandwidth_guarantee",
                    "switch": switch_name,
                    "client_ip": client_ip,
                    "server_ip": server_ip,
                    "min_bandwidth_mbps": min_bandwidth_mbps,
                    "queue_id": queue_id
                })
            
            if success:
                self.logger.info(f"FlowManager: Added bandwidth guarantee flow rules for client {client_id} with min BW {min_bandwidth_mbps} Mbps")
            else:
                self.logger.warning(f"FlowManager: Partially added bandwidth guarantee flow rules for client {client_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding bandwidth guarantee flow rules: {e}", exc_info=True)
            return False
    
    def add_traffic_priority_flow(self, traffic_type: str, src_ip: str, dst_ip: str, 
                                dst_port: int, priority_level: str) -> bool:
        """
        Add flow rules to prioritize specific types of traffic.
        
        Args:
            traffic_type: Type of traffic to prioritize (e.g., "model_update", "control", "metrics")
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            priority_level: Priority level (high, medium, low)
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create traffic priority policy object
            priority_policy = {
                "type": "traffic_priority",
                "traffic_type": traffic_type,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "dst_port": dst_port,
                "priority_level": priority_level
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(priority_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Traffic priority policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation:
                priority_policy = validation["policy"]
                priority_level = priority_policy["priority_level"]
            
            success = True
            
            # Map priority level to OpenFlow priority values
            priority_values = {
                "high": 300,
                "medium": 200,
                "low": 100
            }
            of_priority = priority_values.get(priority_level, 100)
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Create match dictionary
                match_dict = {}
                
                # Always add eth_type for IP traffic when we have IP address in match
                if src_ip is not None or dst_ip is not None:
                    match_dict["eth_type"] = 0x0800  # IPv4
                
                # Add IP addresses to match if available
                if src_ip is not None:
                    match_dict["ipv4_src"] = src_ip
                
                if dst_ip is not None:
                    match_dict["ipv4_dst"] = dst_ip
                
                # Add protocol if specified
                if traffic_type and traffic_type.lower() != "any":
                    # Handle ARP protocol specially with correct eth_type
                    if traffic_type.lower() == "arp":
                        match_dict["eth_type"] = 0x0806  # ARP eth_type
                    elif traffic_type.lower() == "icmp":
                        match_dict["eth_type"] = 0x0800  # IPv4
                        match_dict["ip_proto"] = 1  # ICMP
                    elif traffic_type.lower() == "tcp":
                        match_dict["eth_type"] = 0x0800  # IPv4
                        match_dict["ip_proto"] = 6  # TCP
                        
                        # Add ports if specified
                        if dst_port is not None and dst_port != "any":
                            try:
                                match_dict["tcp_dst"] = int(dst_port)
                            except ValueError:
                                self.logger.warning(f"Invalid TCP destination port '{dst_port}' in rule '{traffic_type}' traffic, ignoring")
                    
                    elif traffic_type.lower() == "udp":
                        match_dict["eth_type"] = 0x0800  # IPv4
                        match_dict["ip_proto"] = 17  # UDP
                        
                        # Add ports if specified
                        if dst_port is not None and dst_port != "any":
                            try:
                                match_dict["udp_dst"] = int(dst_port)
                            except ValueError:
                                self.logger.warning(f"Invalid UDP destination port '{dst_port}' in rule '{traffic_type}' traffic, ignoring")
                    else:
                        self.logger.warning(f"Unsupported protocol '{traffic_type}' in rule '{traffic_type}' traffic, treating as generic IP")
                        # Just use IPv4 without specific protocol

                # Check for overly generic rules that might block switch-controller communication
                # Allow if an explicit action is 'allow', or if it's very specific (e.g. has L4 info)
                if not match_dict and traffic_type != 'allow': # Empty match implies "match all"
                    self.logger.warning(f"Rule '{traffic_type}' is too generic (matches all traffic) and action is not 'allow'. Skipping to prevent network disruption.")
                    success = False
                
                of_actions = []
                if traffic_type == 'allow':
                    of_actions = [{"type": "OUTPUT", "port": "CONTROLLER"}]  # Changed from NORMAL to CONTROLLER
                elif traffic_type == 'deny':
                    of_actions = []
                else:
                    # For traffic priority, we want to forward normally unless explicitly denied
                    of_actions = [{"type": "OUTPUT", "port": "CONTROLLER"}]
                
                for switch in switches:
                    switch_dpid = switch.get('dpid') or switch.get('id')  # Get DPID, fallback to ID
                    if not switch_dpid:
                        self.logger.warning(f"Could not determine DPID for switch: {switch}. Skipping flow for this switch.")
                        continue

                    # If DPID is a dictionary (switch object was incorrectly passed), extract the actual DPID
                    if isinstance(switch_dpid, dict) and ('dpid' in switch_dpid or 'id' in switch_dpid):
                        actual_dpid = switch_dpid.get('dpid') or switch_dpid.get('id')
                        if actual_dpid:
                            switch_dpid = actual_dpid
                        else:
                            self.logger.warning(f"Could not determine DPID from nested dictionary: {switch_dpid}. Skipping flow for this switch.")
                            continue

                    self.logger.info(f"Adding flow to switch '{switch_dpid}' for rule '{traffic_type}': Match={match_dict}, Actions={of_actions}, Prio={of_priority}")
                    success = self.sdn_controller.add_flow(
                        switch=switch_dpid,  # Use the extracted DPID string
                        priority=of_priority,
                        match=match_dict,
                        actions=of_actions,
                        idle_timeout=0,
                        hard_timeout=0
                    )
                    
                    if success:
                        self.logger.info(f"Successfully added flow for rule '{traffic_type}' on switch '{switch_dpid}'")
                    else:
                        self.logger.error(f"Failed to add flow for rule '{traffic_type}' on switch '{switch_dpid}'")

            if success:
                self.logger.info(f"FlowManager: Added traffic priority flow rules for {traffic_type} traffic with priority {priority_level}")
            else:
                self.logger.warning(f"FlowManager: Partially added traffic priority flow rules for {traffic_type} traffic")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding traffic priority flow rules: {e}", exc_info=True)
            return False
    
    def add_anomaly_detection_flow(self, target_ip: str, protocol: str, port: int,
                                 threshold_pps: int, window_seconds: int) -> bool:
        """
        Add flow rules for anomaly detection and rate limiting.
        
        Args:
            target_ip: IP address to monitor
            protocol: Protocol to monitor (tcp, udp, icmp)
            port: Port to monitor
            threshold_pps: Threshold for packets per second
            window_seconds: Time window for rate calculation in seconds
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create anomaly detection policy object
            anomaly_policy = {
                "type": "anomaly_detection",
                "target_ip": target_ip,
                "protocol": protocol,
                "port": port,
                "threshold_pps": threshold_pps,
                "window_seconds": window_seconds
            }
            
            # Validate policy with policy engine
            validation = self.policy_engine.validate_policy(anomaly_policy)
            
            if validation["status"] == "denied":
                self.logger.warning(f"Anomaly detection policy denied: {validation['message']}")
                return False
            
            # Use the potentially modified policy
            if "policy" in validation:
                anomaly_policy = validation["policy"]
                threshold_pps = anomaly_policy["threshold_pps"]
                window_seconds = anomaly_policy["window_seconds"]
            
            success = True
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Configure meter for rate limiting
                meter_id = 1  # Use a more sophisticated ID in production
                meter_config = {
                    "meter_id": meter_id,
                    "flags": ["PKTPS", "BURST", "STATS"],
                    "bands": [
                        {
                            "type": "DROP",
                            "rate": threshold_pps,
                            "burst_size": threshold_pps * 2
                        }
                    ]
                }
                
                # Try to create meter using SDN controller
                if hasattr(self.sdn_controller, 'add_meter'):
                    success &= self.sdn_controller.add_meter(
                        switch_id=switch["id"], meter_config=meter_config
                    )
                else:
                    self.logger.warning(f"FlowManager: SDN Controller does not support adding meters")
                    success = False
                
                # Create match criteria based on protocol
                match = {"ipv4_dst": target_ip}
                if protocol.lower() == "tcp":
                    match["ip_proto"] = 6
                    if port > 0:
                        match["tcp_dst"] = port
                elif protocol.lower() == "udp":
                    match["ip_proto"] = 17
                    if port > 0:
                        match["udp_dst"] = port
                elif protocol.lower() == "icmp":
                    match["ip_proto"] = 1
                
                # Add flow rule to apply meter
                if success:
                    success &= self.sdn_controller.add_flow(
                        switch=switch["id"], 
                        priority=500,  # High priority for security rules
                        match=match,
                        actions=[{"type": "METER", "meter_id": meter_id}, {"type": "FORWARD"}],
                        idle_timeout=0,
                        hard_timeout=0
                    )
                
                # Store anomaly detection flow rule information
                flow_id = f"{target_ip}_{protocol}_{port}_anomaly"
                if flow_id not in self.flow_rules:
                    self.flow_rules[flow_id] = []
                
                self.flow_rules[flow_id].append({
                    "type": "anomaly_detection",
                    "switch": switch_name,
                    "target_ip": target_ip,
                    "protocol": protocol,
                    "port": port,
                    "threshold_pps": threshold_pps,
                    "window_seconds": window_seconds,
                    "meter_id": meter_id
                })
            
            if success:
                self.logger.info(f"FlowManager: Added anomaly detection flow rules for {target_ip} with threshold {threshold_pps} pps")
            else:
                self.logger.warning(f"FlowManager: Partially added anomaly detection flow rules for {target_ip}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"FlowManager: Error adding anomaly detection flow rules: {e}", exc_info=True)
            return False
    
    def add_path_selection_flow(self, src_ip: str, dst_ip: str, path_nodes: List[str],
                              priority: int = 150, protocol: str = "any") -> bool:
            """
            Add flow rules to enforce a specific path for traffic between source and destination.
            
            Args:
                src_ip: Source IP address
                dst_ip: Destination IP address
                path_nodes: List of switch IDs that should form the path
                priority: Priority of the flow rules
                protocol: Protocol to match (any, tcp, udp, icmp)
                
            Returns:
                bool: Success or failure
            """
            try:
                # Create path selection policy object
                path_policy = {
                    "type": "path_selection",
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "path_nodes": path_nodes,
                    "priority": priority,
                    "protocol": protocol
                }
                
                # Validate policy with policy engine
                validation = self.policy_engine.validate_policy(path_policy)
                
                if validation["status"] == "denied":
                    self.logger.warning(f"Path selection policy denied: {validation['message']}")
                    return False
                
                # Use the potentially modified policy
                if "policy" in validation:
                    path_policy = validation["policy"]
                    path_nodes = path_policy["path_nodes"]
                    priority = path_policy["priority"]
                
                success = True
                
                # Check if the controller supports path-based flows
                if not hasattr(self.sdn_controller, 'create_path'):
                    self.logger.warning(f"FlowManager: SDN Controller does not support path-based flows")
                    return False
                
                # Create match criteria based on protocol
                match = {
                    "ipv4_src": src_ip,
                    "ipv4_dst": dst_ip
                }
                
                if protocol.lower() == "tcp":
                    match["ip_proto"] = 6
                elif protocol.lower() == "udp":
                    match["ip_proto"] = 17
                elif protocol.lower() == "icmp":
                    match["ip_proto"] = 1
                
                # Create the path using SDN controller
                success = self.sdn_controller.create_path(
                    src_ip, dst_ip, path_nodes, priority, match
                )
                
                if success:
                    # Store path selection flow rule information
                    flow_id = f"{src_ip}_{dst_ip}_path"
                    if flow_id not in self.flow_rules:
                        self.flow_rules[flow_id] = []
                    
                    self.flow_rules[flow_id].append({
                        "type": "path_selection",
                        "src_ip": src_ip,
                        "dst_ip": dst_ip,
                        "path_nodes": path_nodes,
                        "priority": priority,
                        "protocol": protocol
                    })
                    
                    self.logger.info(f"FlowManager: Added path selection flow rules for traffic from {src_ip} to {dst_ip}")
                else:
                    self.logger.warning(f"FlowManager: Failed to add path selection flow rules for traffic from {src_ip} to {dst_ip}")
                
                return success
                
            except Exception as e:
                self.logger.error(f"FlowManager: Error adding path selection flow rules: {e}", exc_info=True)
                return False
    
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
        Process and apply policies.
        
        Args:
            policies: List of policy objects
        """
        self.logger.info(f"FlowManager: Processing {len(policies)} policies")
        
        # Track successful and failed policies
        successful_policies = []
        failed_policies = []
        
        # Process each policy
        for policy in policies:
            try:
                policy_id = policy.get('id', 'unknown')
                policy_type = policy.get('type', policy.get('policy_type', 'unknown'))
                policy_name = policy.get('name', f'Policy {policy_id}')
                
                # Skip if policy is disabled
                if not policy.get('enabled', True):
                    self.logger.info(f"FlowManager: Skipping disabled policy: {policy_name}")
                    continue
                
                # Process based on policy type
                if policy_type == 'qos':
                    self._process_qos_policy(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'security':
                    self._process_security_policy(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'network_security':
                    self._process_network_security_policy(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'time_window':
                    self._process_time_window_policy(policy)
                    successful_policies.append(policy_id)
                elif policy_type == 'bandwidth_allocation':
                    self._process_bandwidth_policy(policy)
                    successful_policies.append(policy_id)
                else:
                    self.logger.warning(f"FlowManager: Ignoring unsupported policy type: {policy_type}")
            except Exception as e:
                self.logger.error(f"FlowManager: Error processing policy {policy.get('id', 'unknown')}: {e}", exc_info=True)
                failed_policies.append(policy.get('id', 'unknown'))
        
        self.logger.info(f"FlowManager: Applied {len(successful_policies)} policies successfully, {len(failed_policies)} failed")
    
    def _process_network_security_policy(self, policy: Dict[str, Any]) -> None:
        """
        Process a network security policy and install corresponding flow rules.
        """
        policy_name = policy.get('name', policy.get('id', 'unnamed_policy'))
        self.logger.info(f"FlowManager: Processing network security policy: {policy_name}")
        self.logger.debug(f"FlowManager: Policy details: {json.dumps(policy, indent=2)}")

        # Get switches
        switches = self.sdn_controller.get_switches()
        if not switches:
            self.logger.warning(f"FlowManager: Initial switch check found no switches for policy {policy_name}. Waiting 2s and retrying...")
            time.sleep(2)
            switches = self.sdn_controller.get_switches()

        if not switches:
            self.logger.warning(f"FlowManager: No switches available to apply policy {policy_name}")
            return
            
        # Get rules from the policy
        rules = policy.get('rules', [])
        if not rules:
            self.logger.info(f"FlowManager: No rules found in policy {policy_name}.")
            return

        # Track successful and failed rule applications
        policy_applied_rule_instances = 0 
        policy_failed_rule_instances = 0
        
        # Process each rule in the policy
        for rule_idx, rule in enumerate(rules):
            # Generate a rule_id if one doesn't exist
            rule_id = rule.get('id', rule.get('rule_id', f"{policy_name}_rule_{rule_idx}"))
            
            # Skip disabled rules
            if not rule.get('enabled', True):
                self.logger.info(f"Skipping disabled rule: '{rule_id}' in policy '{policy_name}'")
                continue
                
            # Get controller IP if available
            controller_ip = self.network_config.get('NODE_IP_SDN_CONTROLLER', None)
            
            # Process the individual rule using the helper method
            try:
                # Call the single rule processing method
                success = self._process_single_network_rule(rule_id, rule, controller_ip, None)
                
                # Track success/failure
                if success:
                    policy_applied_rule_instances += 1
                else:
                    policy_failed_rule_instances += 1
            except Exception as e:
                self.logger.error(f"Error processing rule '{rule_id}' in policy '{policy_name}': {e}", exc_info=True)
                policy_failed_rule_instances += 1
                
        # Log summary of rule processing
        if policy_applied_rule_instances > 0 or policy_failed_rule_instances > 0:
            self.logger.info(f"Finished processing policy '{policy_name}'. Applied rule instances: {policy_applied_rule_instances}, Failed rule instances: {policy_failed_rule_instances}")
        else:
            self.logger.info(f"Finished processing policy '{policy_name}'. No rule instances were applied or failed (e.g., all rules disabled or skipped).")
    
    def _get_flow_actions(self, action_str, rule_context=None):
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
            # Use NORMAL for OF actions which processes packets through the standard L2/L3 pipeline
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
            # For now, just allow the traffic
            self.logger.warning(f"Rate limiting not fully implemented, treating as 'allow'")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
        
        else:
            # Default to normal forwarding for unknown actions
            self.logger.warning(f"Unknown action type: {action_str}, defaulting to allow")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
            
        return of_actions

    def _get_switches(self):
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
                # Log DPIDs more safely
                dpid_list_for_logging = []
                for sw_info in switches:
                    # Attempt to get a clean DPID for logging
                    log_dpid = sw_info.get('dpid', sw_info.get('id', 'Unknown DPID'))
                    if isinstance(log_dpid, dict): # If it's still a dict, try to get 'dpid' or 'id' from it
                        actual_id_from_dict = log_dpid.get('dpid', log_dpid.get('id'))
                        if actual_id_from_dict is not None:
                            log_dpid = actual_id_from_dict
                        else: # Fallback to string representation of the dict
                            log_dpid = str(log_dpid)
                    dpid_list_for_logging.append(str(log_dpid)) # Ensure it's a string
                self.logger.info(f"Detected {len(switches)} switches. DPIDs: {dpid_list_for_logging}")
            else:
                self.logger.debug("Still no switches detected after refresh")
                
            return switches
        except Exception as e:
            self.logger.error(f"Error getting switches: {e}")
            return []
            
    def _process_single_network_rule(self, rule_id, rule, controller_ip=None, switch=None):
        """Process a network security policy rule and convert it to flow rules.
        
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
            switches = self._get_switches()
            if not switches:
                self.logger.warning(f"No switches available to apply rule {rule_id}")
                return False
        else:
            switches = [switch]
            
        # Track if at least one switch was successfully configured
        success = False
            
        # Extract rule parameters
        rule_match_info = rule.get('match', {})
        src_ip = rule_match_info.get('src_ip', rule_match_info.get('source_ip', 'any'))
        dst_ip = rule_match_info.get('dst_ip', rule_match_info.get('destination_ip', 'any'))
        protocol = rule_match_info.get('protocol', 'any').lower()
        if not protocol:  # Handle empty string case after lowercasing
            protocol = 'any'
            
        src_port = rule_match_info.get('src_port', rule_match_info.get('source_port'))
        dst_port = rule_match_info.get('dst_port', rule_match_info.get('destination_port'))
        
        action_str = rule.get('action', 'deny').lower()
        
        self.logger.info(f"Processing rule '{rule_id}' (Action: {action_str}, Protocol: {protocol})")
        
        # Resolve source and destination IP types if specified
        src_type = rule_match_info.get('src_type')
        src_ip_val = src_ip
        
        if src_type == 'controller' and controller_ip:
            # Use controller IP
            src_ip_val = controller_ip
            self.logger.info(f"Using controller IP {controller_ip} for source IP")
        elif src_type == 'policy_engine' and self.network_config.get('NODE_IP_POLICY_ENGINE'):
            # Use policy engine IP
            src_ip_val = self.network_config.get('NODE_IP_POLICY_ENGINE')
            self.logger.info(f"Using policy engine IP {src_ip_val} for source IP")
        elif src_type == 'fl_server' and self.network_config.get('NODE_IP_FL_SERVER'):
            # Use FL server IP
            src_ip_val = self.network_config.get('NODE_IP_FL_SERVER')
            self.logger.info(f"Using FL server IP {src_ip_val} for source IP")
        
        # Resolve destination IP type
        dst_type = rule_match_info.get('dst_type')
        dst_ip_val = dst_ip
        
        if dst_type == 'controller' and controller_ip:
            # Use controller IP
            dst_ip_val = controller_ip
            self.logger.info(f"Using controller IP {controller_ip} for destination IP")
        elif dst_type == 'policy_engine' and self.network_config.get('NODE_IP_POLICY_ENGINE'):
            # Use policy engine IP
            dst_ip_val = self.network_config.get('NODE_IP_POLICY_ENGINE')
            self.logger.info(f"Using policy engine IP {dst_ip_val} for destination IP")
        elif dst_type == 'fl_server' and self.network_config.get('NODE_IP_FL_SERVER'):
            # Use FL server IP
            dst_ip_val = self.network_config.get('NODE_IP_FL_SERVER')
            self.logger.info(f"Using FL server IP {dst_ip_val} for destination IP")
        
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
        of_actions = self._get_flow_actions(action_str, {"rule_id": rule_id})
        
        # Set priority based on rule specificity (more specific rules get higher priority)
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
        
        # For generic deny rules, lower the priority to avoid blocking all traffic
        if action_str == 'deny' and specificity < 20:
            self.logger.warning(f"Rule '{rule_id}' is too generic (matches all traffic) and action is not 'allow'. Skipping to prevent network disruption.")
            return False
        
        # For specific allow rules, ensure we have proper actions
        if action_str == 'allow' and not of_actions:
            self.logger.info("Using default NORMAL action for allow rule")
            of_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
        
        # Apply the rule to each switch
        for switch in switches:
            switch_dpid = switch.get('dpid') or switch.get('id')  # Get DPID, fallback to ID
            if not switch_dpid:
                self.logger.warning(f"Could not determine DPID for switch: {switch}. Skipping flow for this switch.")
                continue
            
            # If DPID is a dictionary (switch object was incorrectly passed), extract the actual DPID
            if isinstance(switch_dpid, dict) and ('dpid' in switch_dpid or 'id' in switch_dpid):
                actual_dpid = switch_dpid.get('dpid') or switch_dpid.get('id')
                if actual_dpid:
                    switch_dpid = actual_dpid
                else:
                    self.logger.warning(f"Could not determine DPID from nested dictionary: {switch_dpid}. Skipping flow for this switch.")
                    continue
            
            # Check if switch has empty ports list (indicates connectivity issues)
            switch_ports = switch.get('ports', [])
            if isinstance(switch_ports, list) and len(switch_ports) == 0:
                self.logger.warning(f"Switch '{switch_dpid}' has no ports configured, may have connectivity issues. Installing basic connectivity rule.")
                # For switches with no ports, install a very basic allow-all rule
                basic_match = {'eth_type': 0x0800}  # Match IPv4
                basic_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                
                basic_result = self.sdn_controller.add_flow(
                    switch=switch_dpid,
                    priority=1,  # Low priority
                    match=basic_match,
                    actions=basic_actions,
                    idle_timeout=0,
                    hard_timeout=0
                )
                
                if basic_result:
                    self.logger.info(f"Successfully added basic connectivity flow to switch '{switch_dpid}' with no ports")
                    success = True  # Mark as successful since we added a basic rule
                else:
                    self.logger.error(f"Failed to add even basic connectivity flow to switch '{switch_dpid}' with no ports")
                continue  # Skip the specific rule processing for this switch
            
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
                success = True  # Mark as successful if at least one flow was added
            else:
                self.logger.error(f"Failed to add flow for rule '{rule_id}' on switch '{switch_dpid}'")
                
                # Try with a simpler action as fallback
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
                    self.logger.info(f"Successfully added flow with fallback action for rule '{rule_id}' on switch '{switch_dpid}'")
                    success = True
                else:
                    self.logger.error(f"Failed to add flow with fallback action for rule '{rule_id}' on switch '{switch_dpid}'")
                    
                    # Try a basic flow rule to verify connectivity
                    basic_match = {'eth_type': 0x0800}  # Just match IPv4
                    basic_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                    
                    basic_result = self.sdn_controller.add_flow(
                        switch=switch_dpid,
                        priority=1,
                        match=basic_match,
                        actions=basic_actions
                    )
                    
                    if basic_result:
                        self.logger.info(f"Successfully added basic connectivity flow to switch '{switch_dpid}'")
                    else:
                        self.logger.error(f"Failed to add even basic connectivity flow to switch '{switch_dpid}', check controller-switch communication")
        
        # If not already successful, install a default forward rule for basic connectivity
        if not success:
            # Add a default rule in case specific rules failed
            for switch in switches:
                switch_dpid = switch.get('dpid') or switch.get('id')
                if not switch_dpid:
                    continue
                    
                # Add a low-priority default rule to ensure basic connectivity
                default_match = {'eth_type': 0x0800}  # Match all IPv4
                default_actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                
                default_result = self.sdn_controller.add_flow(
                    switch=switch_dpid,
                    priority=1,  # Low priority
                    match=default_match,
                    actions=default_actions
                )
                
                if default_result:
                    self.logger.info(f"Successfully added default flow rule to switch '{switch_dpid}'")
                    # Don't mark as success since the original rule failed
                
        return success