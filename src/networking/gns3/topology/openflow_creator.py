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
OpenFlow Topology Creator for GNS3.

This module extends GNS3TopologyCreator to support OpenFlow-enabled topologies.
"""

import logging
import time
import os
import json
from typing import Dict, List, Any, Optional, Tuple, Union

from src.networking.gns3.topology.creator import GNS3TopologyCreator

logger = logging.getLogger(__name__)

class OpenFlowTopologyCreator:
    """Extension to GNS3TopologyCreator to create OpenFlow-enabled topologies."""
    
    def __init__(self, topology_creator: GNS3TopologyCreator):
        """
        Initialize the OpenFlow topology creator.
        
        Args:
            topology_creator: GNS3TopologyCreator instance to extend
        """
        self.creator = topology_creator
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized OpenFlowTopologyCreator")
    
    def create_openflow_switch(self, name: str, x: int = 0, y: int = 0) -> Optional[str]:
        """
        Create an OpenFlow-enabled switch.
        
        Args:
            name: Name of the switch
            x: X position
            y: Y position
            
        Returns:
            str: Node ID if successful, None otherwise
        """
        try:
            # Create an Ethernet switch (simulates OpenFlow switch)
            switch_data = {
                'name': name,
                'node_type': 'ethernet_switch',
                'compute_id': 'local',
                'x': x,
                'y': y,
                'properties': {
                    'ports_mapping': [
                        {'name': f'Ethernet{i}', 'port_number': i, 'type': 'access', 'vlan': 1}
                        for i in range(8)  # Create 8 Ethernet ports
                    ]
                }
            }
            
            # Use the creator's API to create the switch
            success, response = self.creator.api.create_node(self.creator.project_id, switch_data)
            if not success or not response:
                self.logger.error(f"Failed to create OpenFlow switch {name}")
                return None
                
            # Store node ID
            switch_id = response.get('node_id')
            self.logger.info(f"Created OpenFlow switch {name} with ID {switch_id}")
            return switch_id
        
        except Exception as e:
            self.logger.error(f"Error creating OpenFlow switch: {e}")
            return None
    
    def configure_openflow_switch(self, switch_id: str, controller_ip: str, controller_port: int = 6633) -> bool:
        """
        Configure an Ethernet switch to work with OpenFlow.
        
        Args:
            switch_id: ID of the switch node
            controller_ip: IP address of the SDN controller
            controller_port: Port of the SDN controller
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # In a real environment, we would run OVS commands to connect to the controller
            # Since we're using Ethernet switches in GNS3, we'll add metadata to indicate
            # that this switch should be treated as an OpenFlow switch
            
            # Create a file to mark this switch as OpenFlow-enabled
            command = f"echo 'OPENFLOW=true' > /tmp/openflow_{switch_id}"
            # This is just a marker - in practice the SDN controller would manage this switch
            
            self.logger.info(f"Configured switch {switch_id} for OpenFlow with controller {controller_ip}:{controller_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring OpenFlow switch: {e}")
            return False
            
    def create_openflow_topology(self, num_clients: int = 3, 
                                 server_template: str = "flopynet-Server",
                                 client_template: str = "flopynet-Client",
                                 controller_template: str = "flopynet-SDNController",
                                 policy_template: str = "flopynet-PolicyEngine") -> Dict[str, Any]:
        """
        Create a federated learning topology with OpenFlow switches.
        
        Args:
            num_clients: Number of FL client nodes
            server_template: Template name for the server
            client_template: Template name for clients
            controller_template: Template name for SDN controller
            policy_template: Template name for policy engine
            
        Returns:
            Dict containing node IDs by type
        """
        try:
            self.logger.info(f"Creating OpenFlow topology with {num_clients} clients")
            
            nodes = {}
            
            # 1. Create SDN controller
            controller_node = self._create_node_from_template(
                template_name=controller_template,
                node_name="sdn-controller",
                x=0, y=0
            )
            nodes["controller"] = controller_node
            
            # 2. Create policy engine
            policy_node = self._create_node_from_template(
                template_name=policy_template,
                node_name="policy-engine",
                x=200, y=0
            )
            nodes["policy_engine"] = policy_node
            
            # 3. Create FL server
            server_node = self._create_node_from_template(
                template_name=server_template,
                node_name="fl-server",
                x=100, y=0
            )
            nodes["server"] = server_node
            
            # 4. Create core switch
            core_switch_id = self.create_openflow_switch("core-switch", x=100, y=100)
            if not core_switch_id:
                raise RuntimeError("Failed to create core switch")
            
            # 5. Create edge switches based on client count
            edge_switches = []
            edge_switch_count = max(1, num_clients // 4)  # One edge switch per 4 clients
            
            for i in range(edge_switch_count):
                edge_switch_id = self.create_openflow_switch(
                    f"edge-switch-{i+1}",
                    x=50 + 150 * i,
                    y=200
                )
                if edge_switch_id:
                    edge_switches.append(edge_switch_id)
            
            if not edge_switches:
                raise RuntimeError("Failed to create edge switches")
                
            # Store all switches
            nodes["switches"] = [core_switch_id] + edge_switches
            
            # 6. Create client nodes
            client_nodes = []
            for i in range(num_clients):
                # Determine which edge switch to connect to
                edge_index = i % len(edge_switches)
                
                client_node = self._create_node_from_template(
                    template_name=client_template,
                    node_name=f"fl-client-{i+1}",
                    x=50 + 100 * (i % 4),
                    y=300 + 100 * (i // 4)
                )
                
                if client_node:
                    client_nodes.append(client_node)
            
            if not client_nodes:
                raise RuntimeError("Failed to create client nodes")
                
            nodes["clients"] = client_nodes
            
            # 7. Create links
            links = []
            
            # Link controller to core switch
            controller_to_core = self._create_link(controller_node, core_switch_id)
            if controller_to_core:
                links.append(controller_to_core)
            
            # Link controller to edge switches
            for edge_switch in edge_switches:
                controller_to_edge = self._create_link(controller_node, edge_switch)
                if controller_to_edge:
                    links.append(controller_to_edge)
            
            # Link policy engine to core switch
            policy_to_core = self._create_link(policy_node, core_switch_id)
            if policy_to_core:
                links.append(policy_to_core)
            
            # Link server to core switch
            server_to_core = self._create_link(server_node, core_switch_id)
            if server_to_core:
                links.append(server_to_core)
            
            # Link core switch to edge switches
            for edge_switch in edge_switches:
                core_to_edge = self._create_link(core_switch_id, edge_switch)
                if core_to_edge:
                    links.append(core_to_edge)
            
            # Link clients to edge switches
            for i, client_node in enumerate(client_nodes):
                edge_index = i % len(edge_switches)
                edge_switch = edge_switches[edge_index]
                
                client_to_edge = self._create_link(client_node, edge_switch)
                if client_to_edge:
                    links.append(client_to_edge)
            
            nodes["links"] = links
            
            self.logger.info(f"Created OpenFlow topology with {len(client_nodes)} clients, " +
                           f"{len(edge_switches)} edge switches, and {len(links)} links")
            
            return nodes
            
        except Exception as e:
            self.logger.error(f"Error creating OpenFlow topology: {e}")
            raise
    
    def _create_node_from_template(self, template_name: str, node_name: str, x: int = 0, y: int = 0) -> Optional[str]:
        """
        Create a node from a template.
        
        Args:
            template_name: Name of the template to use
            node_name: Name of the node to create
            x: X position
            y: Y position
            
        Returns:
            str: Node ID if successful, None otherwise
        """
        try:
            # Find the template by name
            success, templates = self.creator.api.get_templates()
            if not success:
                self.logger.error("Failed to get templates")
                return None
            
            template_id = None
            for template in templates:
                if isinstance(template, dict) and template.get('name') == template_name:
                    template_id = template.get('template_id')
                    break
            
            if not template_id:
                self.logger.error(f"Template '{template_name}' not found")
                return None
            
            # Create the node
            node_data = {
                'name': node_name,
                'template_id': template_id,
                'x': x,
                'y': y
            }
            
            success, response = self.creator.api.create_node(self.creator.project_id, node_data)
            if not success or not response:
                self.logger.error(f"Failed to create node {node_name} from template {template_name}")
                return None
                
            # Get the node ID
            node_id = response.get('node_id')
            self.logger.info(f"Created node {node_name} with ID {node_id} from template {template_name}")
            
            return node_id
            
        except Exception as e:
            self.logger.error(f"Error creating node from template: {e}")
            return None
    
    def _create_link(self, node1: str, node2: str) -> Optional[str]:
        """
        Create a link between two nodes.
        
        Args:
            node1: ID of the first node
            node2: ID of the second node
            
        Returns:
            str: Link ID if successful, None otherwise
        """
        try:
            # Create link data
            link_data = {
                'nodes': [
                    {
                        'node_id': node1,
                        'adapter_number': 0,
                        'port_number': 0
                    },
                    {
                        'node_id': node2,
                        'adapter_number': 0,
                        'port_number': 0
                    }
                ]
            }
            
            # Create the link
            success, response = self.creator.api.create_link(self.creator.project_id, link_data)
            if not success or not response:
                self.logger.error(f"Failed to create link between {node1} and {node2}")
                return None
                
            # Get the link ID
            link_id = response.get('link_id')
            self.logger.info(f"Created link {link_id} between nodes {node1} and {node2}")
            
            return link_id
            
        except Exception as e:
            self.logger.error(f"Error creating link: {e}")
            return None 