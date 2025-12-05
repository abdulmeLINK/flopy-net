# Copyright 2025 flopy-net Contributors (abdulmeLINK)
# SPDX-License-Identifier: Apache-2.0
"""
SDN Flow Rule Builders Module.

Extracted from flow_manager.py to reduce file size.
Provides specialized flow rule builders for different traffic types.
"""
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class FlowRuleBuilderMixin:
    """
    Mixin class for FlowManager that provides flow rule builder methods.
    
    This mixin handles specialized flow rule construction:
    - QoS flows
    - Security flows
    - Bandwidth limit/guarantee flows
    - Time-based flows
    - Traffic priority flows
    - Anomaly detection flows
    - Path selection flows
    """
    
    def add_client_qos_flow(self, client_id: str, client_ip: str, 
                          server_ip: str, priority_level: str = "high") -> bool:
        """
        Add QoS flow rules for a federated learning client.
        
        Args:
            client_id: Client identifier
            client_ip: Client IP address
            server_ip: FL server IP address  
            priority_level: QoS priority level (high, medium, low)
            
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
            if "policy" in validation and validation["status"] in ["approved", "modified"]:
                qos_policy = validation["policy"]
                priority_level = qos_policy.get("priority_level", priority_level)
            
            # Map priority level to OpenFlow priority values
            priority_values = {
                "high": 200,
                "medium": 150,
                "low": 100
            }
            of_priority = priority_values.get(priority_level, 100)
            
            success = True
            
            # Get all switches from the controller
            switches = self.sdn_controller.get_switches()
            
            for switch in switches:
                switch_name = switch["name"]
                
                # Add flow for client -> server traffic
                success &= self.sdn_controller.add_flow(
                    switch=switch["id"], 
                    priority=of_priority, 
                    match={"ipv4_src": client_ip, "ipv4_dst": server_ip},
                    actions=[{"type": "SET_QUEUE", "queue_id": 1}, {"type": "FORWARD"}],
                    idle_timeout=0,
                    hard_timeout=0
                )
                
                # Add flow for server -> client traffic
                success &= self.sdn_controller.add_flow(
                    switch=switch["id"], 
                    priority=of_priority, 
                    match={"ipv4_src": server_ip, "ipv4_dst": client_ip},
                    actions=[{"type": "SET_QUEUE", "queue_id": 1}, {"type": "FORWARD"}],
                    idle_timeout=0,
                    hard_timeout=0
                )
                
                # Store flow rule information for tracking
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
                    success = False  # Mark as failure since we cannot block
                
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
