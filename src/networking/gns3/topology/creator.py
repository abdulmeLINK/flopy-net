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
GNS3 Topology Creator.

This module provides functionality for creating various network topologies in GNS3.
"""

import logging
import math
import random
import time
import os
import json
from typing import Dict, List, Any, Optional, Tuple, Union
import requests
from gns3fy import Project, Node, Link, Gns3Connector
import traceback
import uuid

from src.networking.gns3.core.api import GNS3API

logger = logging.getLogger(__name__)

class GNS3TopologyCreator:
    """Creates and manages GNS3 network topologies."""
    
    def __init__(self, api: Any, project_id: str, node_type: str = "docker"):
        """Initialize the topology creator.
        
        Args:
            api: GNS3 API client instance
            project_id: ID of the GNS3 project
            node_type: Type of nodes to create (default: docker)
        """
        self.logger = logging.getLogger(__name__)
        self.api = api
        self.project_id = project_id
        self.node_type = node_type
        self.templates = {}
        
        self.logger.info(f"Initialized GNS3TopologyCreator for project {project_id} with {node_type} nodes")
        
        # Load templates
        self._load_templates()
        
        # Check if project exists and is open
        if hasattr(self.api, 'get_project'):
            success, project = self.api.get_project(self.project_id)
            if not success or not project:
                raise RuntimeError(f"Project with ID {self.project_id} not found")
            
            self.project = project
            
            # Ensure the project is open
            if hasattr(project, 'get') and project.get('status') != 'opened':
                self.logger.info(f"Opening project {self.project_id}")
                success, response = self.api.open_project(self.project_id)
                if not success:
                    raise RuntimeError(f"Failed to open project: {response}")
                self.logger.info(f"Project {self.project_id} opened successfully")
        
        # Get templates - make multiple attempts if needed
        templates = self._discover_templates()
        self.templates = templates if templates else []
        
        # Find required templates
        self.vpcs_template = None
        self.cloud_template = None
        self.docker_template = None
        self.alpine_template = None  # Specifically track the Alpine Linux template
        
        # Only look for templates if we got a valid list
        if isinstance(self.templates, list) and self.templates:
            for template in self.templates:
                try:
                    template_name = template.get('name', '')
                    template_type = template.get('template_type', '')
                    template_id = template.get('template_id', '')
                    
                    # Log all templates for debugging
                    self.logger.info(f"Found template: {template_name} ({template_type}) - ID: {template_id}")
                    
                    # Look specifically for Alpine Linux by name
                    if template_name == 'Alpine Linux' and template_type == 'docker':
                        self.alpine_template = template
                        self.docker_template = template  # Set as default Docker template
                        self.logger.info(f"Found Alpine Linux Docker template: {template_name} (ID: {template_id})")
                    elif template_type == 'docker':
                        # Keep track of other Docker templates as fallback
                        if not self.docker_template:
                            self.docker_template = template
                            self.logger.info(f"Found Docker template: {template_name} (ID: {template_id})")
                    elif template_name == 'Cloud' or template_type == 'cloud':
                        self.cloud_template = template
                        self.logger.info(f"Found Cloud template: {template_name} (ID: {template_id})")
                    elif template_name == 'VPCS' or template_type == 'vpcs':
                        self.vpcs_template = template
                        self.logger.info(f"Found VPCS template: {template_name} (ID: {template_id})")
                except Exception as e:
                    self.logger.warning(f"Error processing template: {e}")
        
    def _load_templates(self):
        """Load available templates from GNS3 server."""
        try:
            # Get templates from API
            success, templates = self.api.get_templates()
            if not success:
                self.logger.error("Failed to get templates from API")
                return
            
            # Store templates by name for easy lookup
            for template in templates:
                if isinstance(template, dict) and 'name' in template:
                    name = template['name']
                    self.templates[name] = template
                    self.logger.info(f"Found template: {name} ({template.get('template_type', 'unknown')}) - ID: {template.get('template_id')}")
                    
                    # Log specific template types we're interested in
                    template_type = template.get('template_type', '').lower()
                    if template_type == 'docker' and 'Alpine' in name:
                        self.logger.info(f"Found Alpine Linux Docker template: {name} (ID: {template.get('template_id')})")
                    elif template_type == 'cloud':
                        self.logger.info(f"Found Cloud template: {name} (ID: {template.get('template_id')})")
                    elif template_type == 'vpcs':
                        self.logger.info(f"Found VPCS template: {name} (ID: {template.get('template_id')})")
            
            self.logger.info(f"Available templates: {list(self.templates.keys())}")
            
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by its name.
        
        Args:
            name: Name of the template
            
        Returns:
            Template dict if found, None otherwise
        """
        self.logger.info(f"Looking for template with name '{name}' (case-insensitive)")
        
        # First try exact match
        for template in self.templates:
            if template.get('name') == name:
                self.logger.info(f"Found exact match for template: {name}")
                return template
                
        # If exact match not found, try case-insensitive match
        for template in self.templates:
            template_name = template.get('name', '')
            if template_name.lower() == name.lower():
                self.logger.info(f"Found case-insensitive match for template: {template_name}")
                return template
                
        # If still not found, try partial match
        for template in self.templates:
            template_name = template.get('name', '')
            if name.lower() in template_name.lower():
                self.logger.info(f"Found partial match for template: {template_name}")
                return template
                
        # If docker specified, try to find any docker template
        if name.lower() == 'docker':
            for template in self.templates:
                template_type = template.get('template_type', '')
                if template_type.lower() == 'docker':
                    self.logger.info(f"Found docker template: {template.get('name')}")
                    return template
        
        self.logger.error(f"No template found with name '{name}'")
        self.logger.info("Available templates:")
        for template in self.templates:
            self.logger.info(f"  - {template.get('name')} ({template.get('template_type', 'unknown')})")
            
        return None
    
    def _discover_templates(self) -> List[Dict[str, Any]]:
        """Discover templates from GNS3 server with multiple attempts."""
        templates = []
        
        # First attempt: Use API client
        try:
            templates = self.api.get_templates()
            if isinstance(templates, list):
                self.logger.info(f"Got {len(templates)} templates using API client")
                # Log template names
                try:
                    template_names = [t.get('name') for t in templates]
                    self.logger.info(f"Available templates: {template_names}")
                except Exception as e:
                    self.logger.warning(f"Error logging template names: {e}")
                return templates
        except Exception as e:
            self.logger.warning(f"Error getting templates via API: {e}")
        
        # Second attempt: Direct API call
        try:
            self.logger.info("Making direct API call to get templates")
            server_url = self.api.server_url
            # Try to make direct call without auth (simpler)
            response = requests.get(f"{server_url}/templates")
            if response.status_code == 200:
                templates = response.json()
                self.logger.info(f"Got {len(templates)} templates using direct API call")
                # Log template names
                try:
                    template_names = [t.get('name') for t in templates]
                    self.logger.info(f"Available templates: {template_names}")
                except Exception as e:
                    self.logger.warning(f"Error logging template names: {e}")
                return templates
        except Exception as e:
            self.logger.warning(f"Direct API call failed: {e}")
        
        # If all attempts fail, return empty list
        self.logger.warning("Failed to get templates, will try to proceed without them")
        return []
        
    def create_star_topology(self, node_count: int, node_type: str = "vpcs",
                           bandwidth: Optional[int] = None,
                           latency: Optional[int] = None,
                           packet_loss: Optional[float] = None) -> bool:
        """Create a star topology with the specified number of nodes.
        
        Args:
            node_count: Number of nodes to create
            node_type: Type of nodes to create (docker or vpcs)
            bandwidth: Optional bandwidth limit in kbps
            latency: Optional latency in ms
            packet_loss: Optional packet loss percentage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating star topology with {node_count} nodes of type {node_type}")
            
            # Get Ethernet switch template for central node
            switch_template = self.get_template_by_name("Ethernet switch")
            if not switch_template:
                self.logger.error("Ethernet switch template not found for central node, trying Cloud template")
                switch_template = self.get_template_by_name("Cloud")
                if not switch_template:
                    self.logger.error("No suitable template found for central node")
                    return False
                
            # Create the central node using the switch template
            success, central_node = self.api.create_node(
                project_id=self.project_id,
                name="central-node",
                template_id=switch_template["template_id"],
                compute_id="local",
                x=0,
                y=0
            )
            
            if not success or not isinstance(central_node, dict):
                self.logger.error("Failed to create central node")
                return False
            
            central_node_id = central_node.get('node_id')
            if not central_node_id:
                self.logger.error("Invalid central node data - missing node_id")
                return False
            
            self.logger.info(f"Created central node with ID: {central_node_id}")
            
            # Calculate positions for nodes in a circle around the central node
            radius = 200  # Distance from center
            nodes = []
            
            for i in range(node_count):
                # Calculate position on the circle
                angle = (2 * math.pi * i) / node_count
                x = int(radius * math.cos(angle))
                y = int(radius * math.sin(angle))
                
                # Set node type based on parameter
                node_template_id = None
                node_compute_id = "local"
                
                if node_type.lower() == "docker":
                    # Use Alpine Docker template for docker nodes
                    docker_template = self.get_template_by_name("Alpine Linux")
                    if not docker_template:
                        # Try fallback to just "Alpine" if "Alpine Linux" isn't found
                        docker_template = self.get_template_by_name("Alpine")
                    if docker_template:
                        node_template_id = docker_template.get('template_id')
                    node_compute_id = "local"  # Use local compute for Docker
                elif node_type.lower() == "vpcs":
                    # Use VPCS template
                    vpcs_template = self.get_template_by_name("VPCS")
                    if vpcs_template:
                        node_template_id = vpcs_template.get('template_id')
                
                if not node_template_id:
                    self.logger.error(f"Could not find template for node type: {node_type}")
                    self.logger.error("Available templates:")
                    for template in self.templates:
                        self.logger.error(f"  - {template.get('name')} ({template.get('template_type')})")
                    return False
                
                # Create the node with separate parameters
                node_properties = {}
                if node_type.lower() == "docker":
                    # For Docker nodes, we need to include image property
                    template_info = self.get_template_by_name("Alpine Linux") or self.get_template_by_name("Alpine")
                    if template_info:
                        # Explicitly set required docker properties
                        image = template_info.get('image', 'alpine:latest')
                        node_properties = {
                            "console_type": "telnet",
                            "image": image,
                            "adapters": template_info.get('adapters', 1),
                            "start_command": template_info.get('start_command', ''),
                            "environment": template_info.get('environment', '')
                        }
                        self.logger.info(f"Using Docker image: {image} for node-{i+1}")
                    else:
                        # Fallback to basic Alpine configuration
                        node_properties = {
                            "console_type": "telnet",
                            "image": "alpine:latest",
                            "adapters": 1
                        }
                        self.logger.warning(f"Using fallback Alpine image for node-{i+1}")
                
                success, node = self.api.create_node(
                    project_id=self.project_id,
                    name=f"node-{i+1}",
                    template_id=node_template_id,
                    node_type=node_type,
                    compute_id=node_compute_id,
                    x=x,
                    y=y,
                    properties=node_properties
                )
                
                if not success or not isinstance(node, dict):
                    self.logger.error(f"Failed to create node {i+1}")
                    return False
                
                node_id = node.get('node_id')
                if not node_id:
                    self.logger.error(f"Invalid node data for node {i+1} - missing node_id")
                    return False
                
                nodes.append(node)
                self.logger.info(f"Created node {i+1} with ID: {node_id}")
            
            # Create links between nodes and central node
            for i, node in enumerate(nodes):
                node_id = node.get("node_id")
                if not node_id:
                    self.logger.error(f"Node ID not found for node {i}")
                    continue
                
                # For the node side
                node_link_data = {
                    "node_id": node_id,
                    "adapter_number": 0,
                    "port_number": 0
                }
                
                # For the central node side - switches have ports 0 to n
                central_link_data = {
                    "node_id": central_node_id,
                    "adapter_number": 0,
                    "port_number": i
                }
                
                # Create link data with both endpoints
                link_data = [node_link_data, central_link_data]
                
                # Add filters if any parameters are specified
                filters = {}
                if any([bandwidth, latency, packet_loss]):
                    if bandwidth:
                        filters["bandwidth"] = {
                            "rate": bandwidth,
                            "delay": 0
                        }
                    if latency:
                        filters["delay"] = {
                            "latency": latency,
                            "jitter": 0
                        }
                    if packet_loss:
                        filters["loss"] = {
                            "percent": packet_loss
                        }
                
                # Create the link
                link_success, link = self.api.create_link(
                    project_id=self.project_id,
                    nodes=link_data,
                    filters=filters if filters else None
                )
                
                if not link_success:
                    self.logger.error(f"Failed to create link between central node and node {i}")
                    # Continue trying to create other links
                    continue
            
            self.logger.info("Star topology created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating star topology: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def create_ring_topology(self, num_nodes: int, node_type: str = "vpcs",
                           node_name_format: str = "node_{}", **kwargs) -> bool:
        """Create a ring topology.
        
        Args:
            num_nodes: Number of nodes
            node_type: Type of nodes to create
            node_name_format: Format string for node names
            **kwargs: Additional node properties
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating ring topology with {num_nodes} nodes")
            
            # Get node template
            template = self.get_template_by_name(node_type)
            if not template:
                self.logger.error(f"Template for {node_type} not found")
                return False
            
            # Create nodes
            node_ids = []
            for i in range(num_nodes):
                # Prepare properties for node creation
                node_properties = kwargs.get("properties", {})
                if node_type == "docker":
                    # For Docker nodes, get template info to extract image
                    template_info = template
                    if template_info:
                        # Ensure required Docker properties are set
                        if "image" not in node_properties:
                            node_properties["image"] = template_info.get('image', 'alpine:latest')
                        if "console_type" not in node_properties:
                            node_properties["console_type"] = "telnet"
                        if "adapters" not in node_properties:
                            node_properties["adapters"] = template_info.get('adapters', 1)
                        
                        self.logger.info(f"Using Docker image: {node_properties['image']} for {node_name_format.format(i+1)}")
                
                # Create node with proper parameters
                success, node = self.api.create_node(
                    project_id=self.project_id,
                    name=node_name_format.format(i+1),
                    template_id=template["template_id"],
                    node_type=node_type,
                    compute_id="local",
                    x=100 * (i + 1),
                    y=100,
                    properties=node_properties
                )
                
                if not success or not node:
                    self.logger.error(f"Failed to create node {i+1}")
                    return False
                
                node_ids.append(node["node_id"])
            
            # Create links in ring
            for i in range(num_nodes):
                next_i = (i + 1) % num_nodes
                
                link_data = {
                    "nodes": [
                        {
                            "node_id": node_ids[i],
                            "adapter_number": 0,
                            "port_number": 0
                        },
                        {
                            "node_id": node_ids[next_i],
                            "adapter_number": 0,
                            "port_number": 1
                        }
                    ],
                    "filters": {}
                }
                
                # Check API class type to determine correct call format
                if hasattr(self.api, 'create_link'):
                    if 'gns3.core.api' in str(self.api.__class__):
                        # For core.api.GNS3API, just pass link_data
                        try:
                            response = self.api.create_link(link_data)
                            success = True
                        except Exception as e:
                            self.logger.error(f"Error creating link: {str(e)}")
                            success = False
                    else:
                        # For gns3_api.GNS3API, pass project_id and data
                        success, link = self.api.create_link(
                            project_id=self.project_id,
                            data=link_data
                        )
                else:
                    self.logger.error("API does not have create_link method")
                    success = False
                
                if not success:
                    self.logger.error(f"Failed to create link between nodes {i+1} and {next_i+1}")
                    return False
            
            self.logger.info("Ring topology created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating ring topology: {e}")
            return False

    def create_tree_topology(self, num_nodes: int, depth: int = 2, branching: int = 2, 
                           node_type: str = "vpcs", node_name_format: str = "node_{}", **kwargs) -> bool:
        """Create a tree topology.
        
        Args:
            num_nodes: Maximum number of nodes to create (actual number may be less)
            depth: The depth of the tree
            branching: The branching factor (children per node)
            node_type: Type of nodes to create
            node_name_format: Format string for node names
            **kwargs: Additional node properties
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating tree topology with up to {num_nodes} nodes (depth={depth}, branching={branching})")
            
            # Get node template
            template = self.get_template_by_name(node_type)
            if not template:
                self.logger.error(f"Template for {node_type} not found")
                return False
            
            # Prepare root node data
            root_node_data = {
                "name": node_name_format.format(0),
                "node_type": node_type,
                "compute_id": "local",
                "template_id": template["template_id"],
                "x": 0,
                "y": 0,
                **kwargs
            }
            
            # Add properties for Docker nodes
            if node_type == "docker":
                properties = root_node_data.get("properties", {})
                # Ensure required Docker properties are set
                if "image" not in properties:
                    properties["image"] = template.get('image', 'alpine:latest')
                if "console_type" not in properties:
                    properties["console_type"] = "telnet"
                if "adapters" not in properties:
                    properties["adapters"] = template.get('adapters', 1)
                    
                root_node_data["properties"] = properties
                self.logger.info(f"Using Docker image: {properties['image']} for root node")
            
            # Create root node
            root_node = self.api.create_node(root_node_data)
            
            if not root_node:
                self.logger.error("Failed to create root node")
                return False
            
            root_id = root_node["node_id"]
            node_ids = [root_id]
            
            # Create child nodes level by level (breadth-first)
            current_level = [root_id]
            node_count = 1
            
            for level in range(1, depth):
                next_level = []
                level_y = level * 100  # Y position for this level
                
                for parent_id in current_level:
                    parent_index = node_ids.index(parent_id)
                    
                    # Calculate X position based on parent index
                    parent_x = 100 * parent_index
                    
                    # Create children for this parent
                    for child in range(branching):
                        # Stop if we've reached the max node count
                        if node_count >= num_nodes:
                            break
                            
                        # Prepare child node data
                        child_x = parent_x + (child - branching/2) * 100
                        child_node_data = {
                            "name": node_name_format.format(node_count),
                            "node_type": node_type,
                            "compute_id": "local",
                            "template_id": template["template_id"],
                            "x": child_x,
                            "y": level_y,
                            **kwargs
                        }
                        
                        # Add properties for Docker nodes
                        if node_type == "docker":
                            child_properties = child_node_data.get("properties", {})
                            # Ensure required Docker properties are set
                            if "image" not in child_properties:
                                child_properties["image"] = properties["image"]
                            if "console_type" not in child_properties:
                                child_properties["console_type"] = properties["console_type"]
                            if "adapters" not in child_properties:
                                child_properties["adapters"] = properties["adapters"]
                            
                            child_node_data["properties"] = child_properties
                            self.logger.info(f"Using Docker image: {child_properties['image']} for child node {node_count}")
                        
                        # Create child node
                        child_node = self.api.create_node(child_node_data)
                        
                        if not child_node:
                            self.logger.error(f"Failed to create child node {node_count}")
                            return False
                        
                        child_id = child_node["node_id"]
                        node_ids.append(child_id)
                        next_level.append(child_id)
                        
                        # Create link between parent and child
                        link_data = {
                            "nodes": [
                                {
                                    "node_id": parent_id,
                                    "adapter_number": 0,
                                    "port_number": child
                                },
                                {
                                    "node_id": child_id,
                                    "adapter_number": 0,
                                    "port_number": 0
                                }
                            ],
                            "filters": {}
                        }
                        
                        # Check API class type to determine correct call format
                        if hasattr(self.api, 'create_link'):
                            if 'gns3.core.api' in str(self.api.__class__):
                                # For core.api.GNS3API, just pass link_data
                                try:
                                    link = self.api.create_link(link_data)
                                    success = True
                                except Exception as e:
                                    self.logger.error(f"Error creating link: {str(e)}")
                                    success = False
                                    link = None
                            else:
                                # For gns3_api.GNS3API, pass project_id and data
                                success, link = self.api.create_link(
                                    project_id=self.project_id,
                                    data=link_data
                                )
                        else:
                            self.logger.error("API does not have create_link method")
                            success = False
                            link = None
                        
                        if not success or not link:
                            self.logger.error(f"Failed to create link between nodes {parent_id} and {child_id}")
                            return False
                        
                        node_count += 1
                    
                # Move to next level
                current_level = next_level
                
                # Stop if we've reached the max node count
                if node_count >= num_nodes:
                    break
            
            self.logger.info(f"Tree topology created successfully with {node_count} nodes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating tree topology: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def create_custom_topology(self, topology_data: Dict[str, Any], node_type: str = "vpcs") -> bool:
        """Create a custom topology based on a topology definition.
        
        Args:
            topology_data: Dictionary defining the topology with 'nodes' and 'links' sections
            node_type: Default node type to use if not specified in node data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Creating custom topology")
            
            # Validate topology data
            if not isinstance(topology_data, dict):
                self.logger.error("Invalid topology data: must be a dictionary")
                return False
                
            if 'nodes' not in topology_data:
                self.logger.error("Missing 'nodes' section in topology data")
                return False
                
            nodes = topology_data.get('nodes', [])
            links = topology_data.get('links', [])
            
            if not nodes:
                self.logger.error("No nodes defined in topology data")
                return False
                
            self.logger.info(f"Creating {len(nodes)} nodes and {len(links)} links")
            
            # Get default template for node_type
            default_template = self.get_template_by_name(node_type)
            if not default_template:
                self.logger.error(f"Default template for {node_type} not found")
                return False
            
            # Create nodes
            node_map = {}  # Map node names to IDs
            for i, node_data in enumerate(nodes):
                # Extract node properties
                node_name = node_data.get('name', f"node_{i}")
                node_type_specific = node_data.get('type', node_type)
                position_x = node_data.get('x', i * 100)
                position_y = node_data.get('y', i * 100)
                
                # Get template for this node type
                if node_type_specific != node_type:
                    template = self.get_template_by_name(node_type_specific)
                    if not template:
                        self.logger.warning(f"Template for {node_type_specific} not found, using default {node_type}")
                        template = default_template
                else:
                    template = default_template
                
                # Prepare node data
                create_node_data = {
                    "name": node_name,
                    "node_type": node_type_specific,
                    "compute_id": "local",
                    "template_id": template["template_id"],
                    "x": position_x,
                    "y": position_y
                }
                
                # Add properties for Docker nodes
                if node_type_specific == "docker":
                    properties = create_node_data.get("properties", {})
                    # Ensure required Docker properties are set
                    if "image" not in properties:
                        properties["image"] = template.get('image', 'alpine:latest')
                    if "console_type" not in properties:
                        properties["console_type"] = "telnet"
                    if "adapters" not in properties:
                        properties["adapters"] = template.get('adapters', 1)
                    
                    create_node_data["properties"] = properties
                    self.logger.info(f"Using Docker image: {properties['image']} for node {node_name}")
                
                # Create node
                node = self.api.create_node(create_node_data)
                
                if not node:
                    self.logger.error(f"Failed to create node {node_name}")
                    return False
                
                # Store node ID for link creation
                node_map[node_name] = node.get("node_id")
                self.logger.info(f"Created node: {node_name} (ID: {node_map[node_name]})")
            
            # Create links
            for i, link_data in enumerate(links):
                # Extract link properties
                source_name = link_data.get('source')
                target_name = link_data.get('target')
                
                if not source_name or not target_name:
                    self.logger.error(f"Invalid link data at index {i}: missing source or target")
                    continue
                    
                if source_name not in node_map:
                    self.logger.error(f"Source node '{source_name}' not found")
                    continue
                    
                if target_name not in node_map:
                    self.logger.error(f"Target node '{target_name}' not found")
                    continue
                
                # Create link with default adapter/port numbers
                source_adapter = link_data.get('source_adapter', 0)
                source_port = link_data.get('source_port', 0)
                target_adapter = link_data.get('target_adapter', 0)
                target_port = link_data.get('target_port', 0)
                
                link_data = {
                    "nodes": [
                        {
                            "node_id": node_map[source_name],
                            "adapter_number": source_adapter,
                            "port_number": source_port
                        },
                        {
                            "node_id": node_map[target_name],
                            "adapter_number": target_adapter,
                            "port_number": target_port
                        }
                    ],
                    "filters": link_data.get('filters', {})
                }
                
                # Check API class type to determine correct call format
                if hasattr(self.api, 'create_link'):
                    if 'gns3.core.api' in str(self.api.__class__):
                        # For core.api.GNS3API, just pass link_data
                        try:
                            link = self.api.create_link(link_data)
                            success = True
                        except Exception as e:
                            self.logger.error(f"Error creating link: {str(e)}")
                            success = False
                            link = None
                    else:
                        # For gns3_api.GNS3API, pass project_id and data
                        success, link = self.api.create_link(
                            project_id=self.project_id,
                            data=link_data
                        )
                else:
                    self.logger.error("API does not have create_link method")
                    success = False
                    link = None
                
                if not success or not link:
                    self.logger.error(f"Failed to create link between {source_name} and {target_name}")
                    continue
                    
                self.logger.info(f"Created link: {source_name} → {target_name}")
            
            self.logger.info("Custom topology created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating custom topology: {e}")
            self.logger.error(traceback.format_exc())
            return False
        
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes in the project."""
        success, nodes = self.api.get_nodes(self.project["project_id"])
        return nodes if success else []
        
    def get_links(self) -> List[Dict[str, Any]]:
        """Get all links in the project."""
        success, links = self.api.get_links(self.project["project_id"])
        return links if success else []

    def create_node(self, node_type: str, name: str, x: int = 0, y: int = 0) -> Optional[Dict[str, Any]]:
        """Create a node in the GNS3 project.
        
        Args:
            node_type: Type of node to create (docker, vpcs, cloud)
            name: Name of the node
            x: X coordinate for node placement
            y: Y coordinate for node placement
            
        Returns:
            Node data if successful, None otherwise
        """
        try:
            self.logger.info(f"Creating {node_type} node named {name}")
            
            if node_type == "cloud":
                # Create cloud node
                cloud_template = self.get_template_by_name("Cloud")
                if not cloud_template:
                    self.logger.error("Cloud template not found")
                    return None
                
                success, node = self.api.create_node({
                    "name": name,
                    "node_type": "cloud",
                    "compute_id": "local",
                    "x": x,
                    "y": y,
                    "template_id": cloud_template["template_id"]
                })
                
                if not success:
                    self.logger.error(f"Failed to create cloud node: {node}")
                    return None
                    
                return node
                
            elif node_type == "docker":
                # Create docker node
                docker_template = self.get_template_by_name("Alpine Linux")
                if not docker_template:
                    self.logger.error("Docker template not found")
                    return None
                
                success, node = self.api.create_node({
                    "name": name,
                    "node_type": "docker",
                    "compute_id": "local",
                    "x": x,
                    "y": y,
                    "template_id": docker_template["template_id"],
                    "properties": {
                        "console_type": "telnet",
                        "image": docker_template.get("image", "alpine:latest"),
                        "adapters": docker_template.get("adapters", 1),
                        "start_command": docker_template.get("start_command", ""),
                        "environment": docker_template.get("environment", "")
                    }
                })
                
                if not success:
                    self.logger.error(f"Failed to create docker node: {node}")
                    return None
                    
                return node
                
            elif node_type == "vpcs":
                # Create VPCS node
                vpcs_template = self.get_template_by_name("VPCS")
                if not vpcs_template:
                    self.logger.error("VPCS template not found")
                    return None
                
                success, node = self.api.create_node({
                    "name": name,
                    "node_type": "vpcs",
                    "compute_id": "local",
                    "x": x,
                    "y": y,
                    "template_id": vpcs_template["template_id"]
                })
                
                if not success:
                    self.logger.error(f"Failed to create VPCS node: {node}")
                    return None
                    
                return node
                
            else:
                self.logger.error(f"Unsupported node type: {node_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating node: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    def _create_cloud_node(self, name: str, x: int = 0, y: int = 0) -> Optional[Dict[str, Any]]:
        """Create a cloud node.
        
        Args:
            name: Name of the node
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Node data if successful, None otherwise
        """
        try:
            # Find cloud template
            cloud_template = None
            for template in self.templates:
                if template.get("name") == "Cloud":
                    cloud_template = template
                    break
                    
            if not cloud_template:
                self.logger.error("Cloud template not found")
                return None
            
            # Create cloud node
            node_data = {
                "name": name,
                "node_type": "cloud",
                "template_id": cloud_template["template_id"],
                "x": x,
                "y": y,
                "compute_id": "local"
            }
            
            success, response = self.api.create_node(self.project["project_id"], node_data)
            if not success:
                self.logger.error(f"Failed to create cloud node {name}: {response}")
                return None
                
            return response
            
        except Exception as e:
            self.logger.error(f"Error creating cloud node {name}: {e}")
            return None

    def deploy_component(self, component_type: str, node_name: str, config: Dict[str, Any]) -> bool:
        """Deploy a component to a GNS3 node.
        
        Args:
            component_type: Type of component to deploy (fl_server, fl_client, policy_engine)
            node_name: Name of the node to deploy to
            config: Component configuration
            
        Returns:
            bool: True if deployment was successful, False otherwise
        """
        try:
            self.logger.info(f"Deploying {component_type} to node {node_name}")
            
            # Get node by name
            node = self.get_node_by_name(node_name)
            if not node:
                self.logger.error(f"Node {node_name} not found")
                return False
                
            # Create deployment directory
            deploy_dir = f"/root/{component_type}"
            mkdir_cmd = f"mkdir -p {deploy_dir}"
            if not self.run_command_on_node(node["node_id"], mkdir_cmd):
                self.logger.error(f"Failed to create deployment directory on {node_name}")
                return False
                
            # Write component script
            script_content = self._get_component_script(component_type, config)
            script_path = f"{deploy_dir}/run.py"
            write_script_cmd = f"echo '{script_content}' > {script_path}"
            if not self.run_command_on_node(node["node_id"], write_script_cmd):
                self.logger.error(f"Failed to write component script on {node_name}")
                return False
                
            # Write config file
            config_path = f"{deploy_dir}/config.json"
            config_content = json.dumps(config, indent=2)
            write_config_cmd = f"echo '{config_content}' > {config_path}"
            if not self.run_command_on_node(node["node_id"], write_config_cmd):
                self.logger.error(f"Failed to write config file on {node_name}")
                return False
                
            # Install Python and pip if not present
            if not self.run_command_on_node(node["node_id"], "which python3"):
                self.logger.info(f"Installing Python on {node_name}")
                install_python_cmd = "apk add --no-cache python3 py3-pip"
                if not self.run_command_on_node(node["node_id"], install_python_cmd):
                    self.logger.error(f"Failed to install Python on {node_name}")
                    return False
                    
            # Install required packages
            if "packages" in config:
                self.logger.info(f"Installing Python packages on {node_name}")
                for package in config["packages"]:
                    install_pkg_cmd = f"pip3 install {package}"
                    if not self.run_command_on_node(node["node_id"], install_pkg_cmd):
                        self.logger.error(f"Failed to install package {package} on {node_name}")
                        return False
                        
            self.logger.info(f"Successfully deployed {component_type} to {node_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deploying component: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
            
    def run_command_on_node(self, node_id: str, command: str) -> bool:
        """Run a command on a GNS3 node via the API.
        
        Args:
            node_id: ID of the node to run command on
            command: Command to run
            
        Returns:
            bool: True if command was successful, False otherwise
        """
        try:
            url = f"/projects/{self.project_id}/nodes/{node_id}/exec"
            data = {"cmd": command}
            response = self.api.post(url, data)
            
            if not response or response.status_code != 200:
                self.logger.error(f"Command failed: {command}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error running command: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
            
    def get_node_by_name(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get a node by its name.
        
        Args:
            node_name: Name of the node to get
            
        Returns:
            dict: Node data if found, None otherwise
        """
        try:
            nodes = self.api.get_nodes()
            for node in nodes:
                if node.get("name") == node_name:
                    return node
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting node: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None
            
    def _get_component_script(self, component_type: str, config: Dict[str, Any]) -> str:
        """Get the Python script content for a component type.
        
        Args:
            component_type: Type of component (fl_server, fl_client, policy_engine)
            config: Component configuration
            
        Returns:
            str: Python script content
        """
        if component_type == "fl_server":
            return """
import json
import flwr as fl

def main():
    with open('config.json') as f:
        config = json.load(f)
        
    server = fl.server.Server(config)
    fl.server.start_server(server=server)

if __name__ == '__main__':
    main()
"""
        elif component_type == "fl_client":
            return """
import json
import flwr as fl
import tensorflow as tf

def main():
    with open('config.json') as f:
        config = json.load(f)
        
    class FlowerClient(fl.client.NumPyClient):
        def get_parameters(self, config):
            return model.get_weights()
            
        def fit(self, parameters, config):
            model.set_weights(parameters)
            history = model.fit(x_train, y_train, epochs=1, batch_size=32)
            return model.get_weights(), len(x_train), {}
            
        def evaluate(self, parameters, config):
            model.set_weights(parameters)
            loss, accuracy = model.evaluate(x_test, y_test)
            return loss, len(x_test), {"accuracy": accuracy}
            
    fl.client.start_numpy_client(server_address=config["server_address"], client=FlowerClient())

if __name__ == '__main__':
    main()
"""
        elif component_type == "policy_engine":
            return """
import json

def main():
    with open('config.json') as f:
        config = json.load(f)
        
    # Policy engine implementation
    pass

if __name__ == '__main__':
    main()
"""
        else:
            raise ValueError(f"Unknown component type: {component_type}")