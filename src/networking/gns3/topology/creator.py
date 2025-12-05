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
Topology building methods (star, ring, tree, custom) are provided via TopologyBuilderMixin.
"""

import logging
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
from src.networking.gns3.topology.topology_builders import TopologyBuilderMixin

logger = logging.getLogger(__name__)

class GNS3TopologyCreator(TopologyBuilderMixin):
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
        
    # Topology building methods (create_star_topology, create_ring_topology,
    # create_tree_topology, create_custom_topology) are provided via TopologyBuilderMixin

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