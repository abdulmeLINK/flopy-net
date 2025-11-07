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
Topology Manager for GNS3 Network Configuration.

This module provides utilities for loading, validating and applying network topology 
configurations to GNS3 deployments.
"""

import os
import json
import logging
import uuid
import ipaddress
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class TopologyManager:
    """
    Manages network topology configurations for GNS3 deployments.
    
    This class handles loading topology configuration files, validating them,
    and providing utilities to apply them to GNS3 environments.
    """
    
    def __init__(self, topology_file: str = None, topology_config: Dict[str, Any] = None):
        """
        Initialize the topology manager.
        
        Args:
            topology_file: Path to topology configuration file (optional)
            topology_config: Topology configuration dictionary (optional)
        """
        self.topology_file = topology_file
        self.topology_config = topology_config
        
        if not self.topology_config and self.topology_file:
            self.load_topology()
        
        self.node_map = {}
        self.ip_assignments = {}
        self._generate_node_map()
        
    def load_topology(self, topology_file: str = None) -> bool:
        """
        Load topology configuration from file.
        
        Args:
            topology_file: Path to topology configuration file (optional)
            
        Returns:
            bool: True if topology loaded successfully, False otherwise
        """
        if topology_file:
            self.topology_file = topology_file
            
        if not self.topology_file or not os.path.exists(self.topology_file):
            logger.error(f"Topology file not found: {self.topology_file}")
            return False
            
        try:
            with open(self.topology_file, 'r') as f:
                self.topology_config = json.load(f)
                
            logger.info(f"Loaded topology configuration from {self.topology_file}")
            self._generate_node_map()
            return True
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in topology file: {self.topology_file}")
            return False
        except Exception as e:
            logger.error(f"Error loading topology file: {e}")
            return False
            
    def save_topology(self, output_file: str = None) -> bool:
        """
        Save current topology configuration to file.
        
        Args:
            output_file: Path to output file (optional)
            
        Returns:
            bool: True if topology saved successfully, False otherwise
        """
        if not self.topology_config:
            logger.error("No topology configuration to save")
            return False
            
        try:
            file_path = output_file or self.topology_file
            if not file_path:
                file_path = f"topology_{uuid.uuid4().hex[:8]}.json"
                
            with open(file_path, 'w') as f:
                json.dump(self.topology_config, f, indent=2)
                
            logger.info(f"Saved topology configuration to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving topology file: {e}")
            return False
    
    def validate_topology(self) -> Tuple[bool, List[str]]:
        """
        Validate the topology configuration.
        
        Checks:
        - Required fields
        - IP address formats
        - Network settings
        - Node configurations
        - Link validity
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        if not self.topology_config:
            return False, ["No topology configuration loaded"]
            
        errors = []
        
        # Check required top-level fields
        required_fields = ["topology_name", "nodes", "links", "network"]
        for field in required_fields:
            if field not in self.topology_config:
                errors.append(f"Missing required field: {field}")
                
        # Check nodes
        if "nodes" in self.topology_config:
            nodes = self.topology_config["nodes"]
            node_names = []
            
            for idx, node in enumerate(nodes):
                node_error_prefix = f"Node #{idx+1}"
                
                # Check required node fields
                if "name" not in node:
                    errors.append(f"{node_error_prefix}: Missing 'name' field")
                else:
                    node_names.append(node["name"])
                    
                if "service_type" not in node:
                    errors.append(f"{node_error_prefix} ({node.get('name', 'unknown')}): Missing 'service_type' field")
                    
                if "ip_address" not in node:
                    errors.append(f"{node_error_prefix} ({node.get('name', 'unknown')}): Missing 'ip_address' field")
                else:
                    # Validate IP format
                    try:
                        ipaddress.ip_address(node["ip_address"])
                    except ValueError:
                        errors.append(f"{node_error_prefix} ({node.get('name', 'unknown')}): Invalid IP address: {node['ip_address']}")
        
        # Check links
        if "links" in self.topology_config:
            links = self.topology_config["links"]
            
            for idx, link in enumerate(links):
                link_error_prefix = f"Link #{idx+1}"
                
                # Check required link fields
                if "source" not in link:
                    errors.append(f"{link_error_prefix}: Missing 'source' field")
                elif link["source"] not in node_names:
                    errors.append(f"{link_error_prefix}: Source node '{link['source']}' not found in nodes")
                    
                if "target" not in link:
                    errors.append(f"{link_error_prefix}: Missing 'target' field")
                elif link["target"] not in node_names:
                    errors.append(f"{link_error_prefix}: Target node '{link['target']}' not found in nodes")
        
        # Check network settings
        if "network" in self.topology_config:
            network = self.topology_config["network"]
            
            if "subnet" not in network:
                errors.append("Network configuration missing 'subnet' field")
            else:
                # Validate subnet format
                try:
                    ipaddress.ip_network(network["subnet"])
                except ValueError:
                    errors.append(f"Invalid subnet format: {network['subnet']}")
        
        return len(errors) == 0, errors
    
    def _generate_node_map(self):
        """Generate maps of node names to configurations."""
        if not self.topology_config or "nodes" not in self.topology_config:
            return
        
        # Clone the nodes to avoid modifying the original structure
        nodes = self.topology_config["nodes"]
        
        # Handle both list and dict formats
        if isinstance(nodes, list):
            # Create a map of node name to node config
            self.node_map = {node["name"]: node for node in nodes if "name" in node}
            # Create a map of node name to IP address
            self.ip_assignments = {node["name"]: node["ip_address"] for node in nodes 
                                if "name" in node and "ip_address" in node}
        elif isinstance(nodes, dict):
            # If nodes is a dictionary (name -> config), create the maps directly
            self.node_map = nodes
            self.ip_assignments = {name: config.get("ip_address") for name, config in nodes.items() 
                                  if "ip_address" in config}
        else:
            logger.error(f"Unexpected nodes type: {type(nodes)}. Expected list or dict.")
            self.node_map = {}
            self.ip_assignments = {}
    
    def get_node_config(self, node_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific node.
        
        Args:
            node_name: Name of the node to get configuration for
            
        Returns:
            Dict with node configuration or None if not found
        """
        return self.node_map.get(node_name)
    
    def get_node_ip(self, node_name: str) -> Optional[str]:
        """
        Get IP address for a specific node.
        
        Args:
            node_name: Name of the node to get IP for
            
        Returns:
            IP address as string or None if not found
        """
        return self.ip_assignments.get(node_name)
    
    def get_node_environment(self, node_name: str) -> Dict[str, str]:
        """
        Get environment variables for a specific node.
        
        Args:
            node_name: Name of the node to get environment for
            
        Returns:
            Dict with environment variables or empty dict if not found
        """
        node_config = self.get_node_config(node_name)
        if not node_config or "environment" not in node_config:
            return {}
            
        return node_config["environment"]
    
    def get_network_conditions(self, node_name: str = None) -> Dict[str, Any]:
        """
        Get network conditions for a specific node or all nodes.
        
        Args:
            node_name: Name of the node to get conditions for (optional)
            
        Returns:
            Dict with network conditions or empty dict if not found
        """
        if not self.topology_config or "network_conditions" not in self.topology_config:
            return {}
            
        conditions = self.topology_config["network_conditions"]
        
        if not node_name:
            return conditions
            
        # Extract conditions specific to this node
        node_conditions = {}
        
        for condition_type, condition_list in conditions.items():
            node_specific = [c for c in condition_list if c.get("node") == node_name]
            if node_specific:
                node_conditions[condition_type] = node_specific[0]
                
        return node_conditions
    
    def generate_ip_map(self) -> str:
        """
        Generate IP map string for use with GNS3_IP_MAP environment variable.
        
        Format: "service1:ip1,service2:ip2,..."
        
        Returns:
            IP map string
        """
        if not self.ip_assignments:
            return ""
            
        return ",".join([f"{name}:{ip}" for name, ip in self.ip_assignments.items()])
    
    def apply_to_gns3_api(self, gns3_api, project_id: str) -> bool:
        """
        Apply topology configuration to a GNS3 project via API.
        
        Args:
            gns3_api: GNS3 API instance
            project_id: GNS3 project ID
            
        Returns:
            bool: True if applied successfully, False otherwise
        """
        if not self.topology_config:
            logger.error("No topology configuration loaded")
            return False
            
        try:
            # Copy topology file to each node
            for node_name, node_ip in self.ip_assignments.items():
                try:
                    # Find node by name
                    success, nodes = gns3_api._make_request('GET', f'/projects/{project_id}/nodes')
                    if not success:
                        logger.error(f"Failed to get nodes for project {project_id}")
                        continue
                        
                    matching_nodes = [n for n in nodes if n.get('name') == node_name]
                    if not matching_nodes:
                        logger.warning(f"No node found with name {node_name}")
                        continue
                        
                    node_id = matching_nodes[0]['node_id']
                    
                    # Ensure config directory exists
                    success, _ = gns3_api._make_request('POST', 
                                            f'/projects/{project_id}/nodes/{node_id}/exec',
                                            json={'command': 'mkdir -p /app/config'})
                    
                    # Create temporary topology file
                    temp_file = f"/tmp/topology_{uuid.uuid4().hex[:8]}.json"
                    with open(temp_file, 'w') as f:
                        json.dump(self.topology_config, f, indent=2)
                    
                    # Upload to node
                    with open(temp_file, 'r') as f:
                        file_content = f.read()
                        
                    success, _ = gns3_api._make_request('POST', 
                                                      f'/projects/{project_id}/nodes/{node_id}/files/app/config/topology.json',
                                                      data=file_content)
                    
                    if success:
                        logger.info(f"Successfully uploaded topology file to {node_name}")
                    else:
                        logger.warning(f"Failed to upload topology file to {node_name}")
                    
                    # Clean up temporary file
                    os.remove(temp_file)
                    
                except Exception as e:
                    logger.error(f"Error applying topology to node {node_name}: {e}")
            
            logger.info(f"Applied topology configuration to GNS3 project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying topology configuration: {e}")
            return False
    
    @staticmethod
    def get_default_topology_path() -> str:
        """Get path to default topology file."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        return os.path.join(base_dir, "src", "config", "network_topology.json")
    
    @classmethod
    def load_default_topology(cls) -> 'TopologyManager':
        """
        Load the default topology configuration.
        
        Returns:
            TopologyManager instance with default topology loaded
        """
        default_path = cls.get_default_topology_path()
        return cls(topology_file=default_path)


# Function for generating network conditions based on network requirements
def generate_network_conditions(
    num_clients: int, 
    bandwidth_range: Tuple[int, int] = (5, 50),
    latency_range: Tuple[int, int] = (5, 100),
    packet_loss_range: Tuple[float, float] = (0.0, 5.0)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate network conditions for a given number of clients.
    
    Args:
        num_clients: Number of clients to generate conditions for
        bandwidth_range: (min, max) range for bandwidth in Mbps
        latency_range: (min, max) range for latency in ms
        packet_loss_range: (min, max) range for packet loss in percentage
        
    Returns:
        Dict with network conditions
    """
    import random
    
    bandwidth_min, bandwidth_max = bandwidth_range
    latency_min, latency_max = latency_range
    loss_min, loss_max = packet_loss_range
    
    # Define priority levels
    priorities = ["high", "medium", "low"]
    
    conditions = {
        "bandwidth_constraints": [],
        "latency_settings": [],
        "packet_loss": []
    }
    
    for i in range(1, num_clients + 1):
        client_name = f"fl-client-{i}"
        
        # Determine client priority (distribute evenly)
        priority_idx = (i - 1) % len(priorities)
        priority = priorities[priority_idx]
        
        # Generate bandwidth based on priority
        if priority == "high":
            bandwidth = random.randint(int(bandwidth_max * 0.7), bandwidth_max)
        elif priority == "medium":
            bandwidth = random.randint(int(bandwidth_max * 0.4), int(bandwidth_max * 0.7))
        else:  # low
            bandwidth = random.randint(bandwidth_min, int(bandwidth_max * 0.4))
            
        # Generate latency and packet loss
        latency = random.randint(latency_min, latency_max)
        packet_loss = round(random.uniform(loss_min, loss_max), 2)
        
        # Add to conditions
        conditions["bandwidth_constraints"].append({
            "node": client_name,
            "bandwidth_mbps": bandwidth,
            "priority": priority
        })
        
        conditions["latency_settings"].append({
            "node": client_name,
            "latency_ms": latency
        })
        
        conditions["packet_loss"].append({
            "node": client_name,
            "loss_percentage": packet_loss
        })
    
    return conditions 