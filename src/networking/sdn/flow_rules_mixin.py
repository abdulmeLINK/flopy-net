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
Flow Rules Mixin for SDN Flow Manager.

This module provides flow rule creation methods for various policy types
including QoS, security, bandwidth, time-based, traffic priority, anomaly
detection, and path selection.
"""

import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.networking.sdn.protocols import FlowRulesHost


class FlowRulesMixin:
    """
    Mixin class providing flow rule creation methods for FlowManager.
    
    This mixin expects the host class to implement FlowRulesHost protocol:
    - logger: Logger instance
    - sdn_controller: SDNControllerProtocol instance
    - policy_engine: PolicyEngineProtocol instance
    - flow_rules: Dict for storing flow rule information
    
    See src/networking/sdn/protocols.py for the formal protocol definition.
    """

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
