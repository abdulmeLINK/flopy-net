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
GNS3 Manager for Basic Scenario.

This module provides utilities for interacting with GNS3 to set up the network
environment for basic federated learning scenarios.
"""

import os
import sys
import json
import logging
import random
import time
from typing import Dict, List, Any, Optional, Tuple, Union
import traceback

logger = logging.getLogger(__name__)

class GNS3Manager:
    """
    Manages GNS3 interactions for basic scenario.
    
    This class handles:
    - GNS3 project creation and setup
    - Node creation and management
    - Link creation and management
    - Template management
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the GNS3 manager.
        
        Args:
            config: Configuration dictionary for the scenario
        """
        self.config = config
        self.gns3_config = self.config.get('gns3', {})
        self.api = None
        self.project_id = None
        self.project_name = self.gns3_config.get('project_name', 'basic_fl')
        
        # Initialize the GNS3 API client
        self._init_api()
        
        logger.info("GNS3Manager initialized")
    
    def _init_api(self) -> None:
        """Initialize the GNS3 API client."""
        try:
            # Import GNS3 API dynamically to avoid circular imports
            from src.networking.gns3.core.api import GNS3API
            
            # Debug log to show the entire GNS3 config section
            logger.info(f"GNS3 config section: {json.dumps(self.gns3_config, indent=2)}")
            
            # Get GNS3 server URL from config - more robust extraction
            server_url = None
            
            # Direct server_url in gns3 section
            if 'server_url' in self.gns3_config:
                server_url = self.gns3_config.get('server_url')
                logger.info(f"Found server_url directly in gns3 config section: {server_url}")
            # Host and port in gns3 section
            elif 'host' in self.gns3_config and 'port' in self.gns3_config:
                host = self.gns3_config.get('host')
                port = self.gns3_config.get('port')
                server_url = f"http://{host}:{port}"
                logger.info(f"Constructed server_url from host and port: {server_url}")
            # Check in parent config if gns3 doesn't have it
            elif 'gns3' in self.config:
                gns3_parent = self.config.get('gns3', {})
                if 'server_url' in gns3_parent:
                    server_url = gns3_parent.get('server_url')
                    logger.info(f"Found server_url in parent gns3 section: {server_url}")
                elif 'host' in gns3_parent and 'port' in gns3_parent:
                    host = gns3_parent.get('host')
                    port = gns3_parent.get('port')
                    server_url = f"http://{host}:{port}"
                    logger.info(f"Constructed server_url from parent gns3 section: {server_url}")
            # Check in network section
            elif 'network' in self.config:
                network = self.config.get('network', {})
                if 'gns3' in network:
                    network_gns3 = network.get('gns3', {})
                    if 'server_url' in network_gns3:
                        server_url = network_gns3.get('server_url')
                        logger.info(f"Found server_url in network.gns3 section: {server_url}")
                    elif 'host' in network_gns3 and 'port' in network_gns3:
                        host = network_gns3.get('host')
                        port = network_gns3.get('port')
                        server_url = f"http://{host}:{port}"
                        logger.info(f"Constructed server_url from network.gns3 section: {server_url}")
                elif 'server_url' in network:
                    server_url = network.get('server_url')
                    logger.info(f"Found server_url in network section: {server_url}")
            
            # Log the exact server URL we're using
            logger.info(f"Using GNS3 server URL from config: {server_url}")
            
            # If server_url is missing or empty in config, use default
            if not server_url:
                server_url = 'http://localhost:3080'
                logger.warning(f"No server_url found in config, using default: {server_url}")
            
            # Initialize API client
            self.api = GNS3API(server_url)
            
            logger.info(f"Initialized GNS3 API client for server: {server_url}")
            
        except ImportError:
            logger.error("Failed to import GNS3API, make sure networking.gns3 module is available")
            self.api = None
            
        except Exception as e:
            logger.error(f"Error initializing GNS3 API client: {e}")
            self.api = None
    
    def check_connection(self) -> bool:
        """
        Check connection to GNS3 server.
        
        Returns:
            bool: True if connection is working, False otherwise
        """
        if not self.api:
            logger.error("Cannot check connection: API client not initialized")
            return False
            
        try:
            # Test connection by trying to get the server version
            # GNS3 uses /v2/version endpoint for version info
            success, response = self.api._make_request('GET', 'version')
            
            if success:
                # Log the version information if available
                version = response.get('version', 'unknown')
                logger.info(f"Successfully connected to GNS3 server (version: {version})")
                return True
            else:
                # Try alternative endpoint in case API changed
                alt_success, alt_response = self.api._make_request('GET', 'v2/version')
                if alt_success:
                    version = alt_response.get('version', 'unknown')
                    logger.info(f"Successfully connected to GNS3 server using alternate endpoint (version: {version})")
                    return True
                    
                logger.error(f"Failed to connect to GNS3 server: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking connection to GNS3 server: {e}")
            return False
    
    def setup_project(self) -> bool:
        """
        Set up a GNS3 project for the scenario.
        
        Returns:
            bool: True if project setup was successful, False otherwise
        """
        if not self.api:
            logger.error("Cannot set up project: API client not initialized")
            return False
            
        try:
            # Try to find existing project with matching name
            success, projects = self.api._make_request('GET', 'projects')
            existing_project_id = None
            
            if success:
                for project in projects:
                    if project.get('name') == self.project_name:
                        existing_project_id = project.get('project_id')
                        logger.info(f"Found existing project: {self.project_name} (ID: {existing_project_id})")
                        break
            
            # If project exists, delete it to ensure a clean slate
            if existing_project_id:
                logger.info(f"Deleting existing project: {self.project_name} (ID: {existing_project_id}) to ensure a clean start.")
                delete_success, _ = self.api._make_request('DELETE', f'projects/{existing_project_id}')
                if delete_success:
                    logger.info(f"Successfully deleted project: {self.project_name}")
                else:
                    logger.warning(f"Failed to delete existing project: {self.project_name}. Proceeding to create, but state might not be clean.")
            
            # Always create a new project now
            logger.info(f"Creating new project: {self.project_name}")
            success, project_data = self.api._make_request('POST', 'projects', json={'name': self.project_name})
            
            if success and project_data:
                self.project_id = project_data.get('project_id')
                logger.info(f"Created new project: {self.project_name} (ID: {self.project_id})")
                # Attempt to open the newly created project
                open_success, _ = self.api._make_request('POST', f'projects/{self.project_id}/open')
                if open_success:
                    logger.info(f"Successfully opened newly created project: {self.project_name}")
                    return True
                else:
                    logger.error(f"Created project {self.project_name} but failed to open it.")
                    # Clean up by deleting the project we just created but couldn't open
                    if self.project_id:
                        self.api._make_request('DELETE', f'projects/{self.project_id}') 
                    return False
            else:
                logger.error(f"Failed to create project: {self.project_name}. Response: {project_data}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up project: {e}")
            return False
    
    def reset_project(self) -> bool:
        """
        Reset the GNS3 project by removing all nodes.
        
        Returns:
            bool: True if reset was successful, False otherwise
        """
        if not self.api or not self.project_id:
            logger.error("Cannot reset project: API client or project ID not available")
            return False
            
        try:
            # Get all nodes in the project
            success, nodes = self.api._make_request('GET', f'projects/{self.project_id}/nodes')
            
            if not success:
                logger.error("Failed to get nodes for resetting project")
                return False
                
            # Stop all nodes first
            for node in nodes:
                node_id = node.get('node_id')
                if node_id:
                    self.api._make_request('POST', f'projects/{self.project_id}/nodes/{node_id}/stop')
            
            # Wait for nodes to stop
            time.sleep(2)
            
            # Delete all nodes
            for node in nodes:
                node_id = node.get('node_id')
                if node_id:
                    success, _ = self.api._make_request('DELETE', f'projects/{self.project_id}/nodes/{node_id}')
                    if success:
                        logger.info(f"Deleted node: {node.get('name')} (ID: {node_id})")
                    else:
                        logger.warning(f"Failed to delete node: {node.get('name')} (ID: {node_id})")
            
            logger.info("Project reset completed")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting project: {e}")
            return False
    
    def create_node(self, node_name: str, template_name: str, node_config: dict = None, environment: dict = None) -> tuple:
        """
        Create a node in the GNS3 project.
        
        Args:
            node_name: Name of the node
            template_name: Name of the template to use
            node_config: Specific configuration for this node instance from topology file (optional)
            environment: Dict of environment variables to set
                
        Returns:
            Tuple of (success, node_data)
        """
        node_config = node_config or {} # Ensure node_config is a dict
        try:
            # 1. Find the template by name
            success, templates = self.api._make_request('GET', 'templates')
            if not success:
                logger.error(f"Failed to retrieve templates list: {templates}")
                return False, {}
                
            # Find the template by name
            template = None
            for t in templates:
                if t.get('name') == template_name:
                    template = t
                    break
        
            if not template:
                logger.error(f"Template {template_name} not found")
                return False, {}
                
            template_id = template.get('template_id')
            node_type = template.get('template_type')  # Get node_type from template
            
            # 2. Configure node position and ports
            x_pos = node_config.get('x', 0)
            y_pos = node_config.get('y', 0)
            compute_id = node_config.get('compute_id', 'local')  # Default to local compute
            
            # Format environment variables if provided
            env_str = None
            if environment:
                if isinstance(environment, dict):
                    # Add scenario-level information to environment
                    environment['SCENARIO_TYPE'] = self.config.get('scenario_type', 'unknown')
                    environment['NODE_NAME'] = node_name
                    
                    # Add node IP from node_config if available
                    if 'ip_address' in node_config:
                        environment['NODE_IP'] = node_config['ip_address']
                        
                    # Convert dict to string with newlines - proper GNS3 format
                    env_str = "\n".join([f"{k}={v}" for k, v in environment.items()])
                else:
                    env_str = environment  # Use as-is if already a string
            
            # 3. Prepare node properties based on template type
            properties = {}
            
            # Add environment variables if provided
            if env_str:
                properties['environment'] = env_str
                
            # Add image for Docker containers
            if node_type == 'docker' and template.get('image'):
                properties['image'] = template.get('image')
                
            # For Ethernet switches, potentially set up ports_mapping
            if node_type == 'ethernet_switch' and 'adapters' in node_config:
                ports_mapping = []
                for i in range(int(node_config['adapters'])):
                    ports_mapping.append({
                        'name': f'Ethernet{i}',
                        'port_number': i,
                        'type': 'access',
                        'vlan': 1
                    })
                properties['ports_mapping'] = ports_mapping

            # For Cloud nodes, use ports_mapping from node_config
            if node_type == 'cloud' and 'properties' in node_config and 'ports_mapping' in node_config['properties']:
                properties['ports_mapping'] = node_config['properties']['ports_mapping']
                
            # Configure adapter count if specified
            adapters = node_config.get('adapters')
            if adapters is not None and node_type != 'cloud':  # Skip adapters for Cloud nodes
                logger.info(f"Configured adapter count for {node_name}: {adapters}")
                if node_type == 'docker':
                    properties['adapters'] = adapters
                elif node_type != 'ethernet_switch':  # Don't double-handle for ethernet switches
                    properties['adapters'] = adapters
                    
            # 4. Create the node
            node_data = {
                'name': node_name,
                'template_id': template_id,
                'compute_id': compute_id,
                'x': x_pos,
                'y': y_pos,
                'node_type': node_type,  # Include node_type from template
                'properties': properties
            }
            
            # For docker templates, also get console_type
            if 'console_type' in template:
                node_data['console_type'] = template['console_type']
                
            logger.debug(f"Creating node with data: {node_data}")
            success, created_node = self.api._make_request('POST', f'projects/{self.project_id}/nodes', json=node_data)
        
            if not success:
                logger.warning(f"Failed to create node {node_name}: {created_node}")
                return False, {}
                
            logger.info(f"Created node {node_name} with ID {created_node.get('node_id', 'unknown')}")
            return True, created_node
            
        except Exception as e:
            logger.error(f"Error creating node {node_name}: {e}")
            return False, {}
    
    def create_link(self, node1_id: str, port1: int, node2_id: str, port2: int) -> Tuple[bool, Any]:
        """
        Create a link between two nodes.
        
        Args:
            node1_id: ID of the first node
            port1: Port number on the first node
            node2_id: ID of the second node
            port2: Port number on the second node
            
        Returns:
            Tuple of (success, link_data)
        """
        try:
            # Get adapter and port info for both nodes
            success1, node1 = self.api._make_request('GET', f'projects/{self.project_id}/nodes/{node1_id}')
            success2, node2 = self.api._make_request('GET', f'projects/{self.project_id}/nodes/{node2_id}')
            
            if not success1 or not success2:
                logger.error(f"Failed to get node information for link creation")
                return False, None
                
            # Find the appropriate adapters for the ports
            node1_adapters = node1.get('ports', [])
            node2_adapters = node2.get('ports', [])
            
            # Get the adapter numbers for the ports
            adapter1 = None
            adapter2 = None
            
            for port in node1_adapters:
                if port.get('port_number') == port1:
                    adapter1 = port
                    break
                    
            for port in node2_adapters:
                if port.get('port_number') == port2:
                    adapter2 = port
                    break
            
            if not adapter1:
                logger.warning(f"Port {port1} not found on node {node1.get('name')}, attempting to find available port")
                adapter_info = self._find_available_port(node1_id, node1_adapters)
                if adapter_info:
                    adapter1 = adapter_info[0]
                    port1 = adapter_info[1]
                else:
                    logger.error(f"No available port found on node {node1.get('name')}")
                    return False, None
                    
            if not adapter2:
                logger.warning(f"Port {port2} not found on node {node2.get('name')}, attempting to find available port")
                adapter_info = self._find_available_port(node2_id, node2_adapters)
                if adapter_info:
                    adapter2 = adapter_info[0]
                    port2 = adapter_info[1]
                else:
                    logger.error(f"No available port found on node {node2.get('name')}")
                    return False, None
            
            # Create the link
            nodes_list = [
                {
                    'node_id': node1_id,
                    'adapter_number': adapter1.get('adapter_number', 0),
                    'port_number': port1
                },
                {
                    'node_id': node2_id,
                    'adapter_number': adapter2.get('adapter_number', 0),
                    'port_number': port2
                }
            ]
            
            # Make sure both nodes are started before creating the link
            def ensure_node_started(node_id, node_name):
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    success, node_status = self.api._make_request('GET', f'projects/{self.project_id}/nodes/{node_id}/status')
                    if success and node_status.get('status') == 'started':
                        return True
                    
                    logger.info(f"Node {node_name} not started, starting it...")
                    start_success, _ = self.api._make_request('POST', f'projects/{self.project_id}/nodes/{node_id}/start')
                    if not start_success:
                        logger.warning(f"Failed to start node {node_name}")
                    
                    # Wait before checking again
                    time.sleep(2)
                    retry_count += 1
                
                logger.error(f"Failed to start node {node_name} after {max_retries} attempts")
                return False
            
            # Ensure both nodes are started
            node1_name = node1.get('name', 'Node 1')
            node2_name = node2.get('name', 'Node 2')
            
            if not ensure_node_started(node1_id, node1_name) or not ensure_node_started(node2_id, node2_name):
                logger.error("Cannot create link: Failed to start one or both nodes")
                return False, None
            
            # Create the link
            success, link_data = self.api.create_link(project_id=self.project_id, nodes=nodes_list)
            
            if not success:
                logger.error(f"Failed to create link between {node1_name} and {node2_name}")
                return False, link_data
            
            logger.info(f"Successfully created link between {node1_name} and {node2_name}")
            return True, link_data
            
        except Exception as e:
            logger.error(f"Error creating link: {e}")
            logger.debug(traceback.format_exc())
            return False, None
            
    def _find_available_port(self, node_id: str, adapters: List[Dict[str, Any]]) -> Optional[Tuple[int, int]]:
        """
        Find an available port on a node.
        
        Args:
            node_id: ID of the node
            adapters: List of adapter information for the node
            
        Returns:
            Tuple of (adapter, port) or None if no port is available
        """
        try:
            # Get links for the project
            success, links = self.api._make_request('GET', f'projects/{self.project_id}/links')
            
            if not success:
                logger.error("Failed to get links for finding available port")
                return None
                
            # Create a set of used ports for this node
            used_ports = set()
            for link in links:
                for node in link.get('nodes', []):
                    if node.get('node_id') == node_id:
                        adapter_num = node.get('adapter_number', 0)
                        port_num = node.get('port_number')
                        used_ports.add((adapter_num, port_num))
            
            # Find an available port
            for adapter in adapters:
                adapter_num = adapter.get('adapter_number', 0)
                port_num = adapter.get('port_number')
                
                if (adapter_num, port_num) not in used_ports:
                    return (adapter, port_num)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding available port: {e}")
            return None
    
    def cleanup_project(self) -> bool:
        """
        Clean up the GNS3 project by closing or deleting it.
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        if not self.api or not self.project_id:
            logger.error("Cannot clean up project: API client or project ID not available")
            return False
            
        try:
            # Get the cleanup action from config
            cleanup_action = self.gns3_config.get('cleanup_action', 'close')
            
            if cleanup_action == 'delete':
                # Delete the project
                success, _ = self.api._make_request('DELETE', f'projects/{self.project_id}')
                if success:
                    logger.info(f"Deleted project: {self.project_name}")
                    return True
                else:
                    logger.error(f"Failed to delete project: {self.project_name}")
                    return False
            elif cleanup_action == 'close':
                # Close the project
                success, _ = self.api._make_request('POST', f'projects/{self.project_id}/close')
                if success:
                    logger.info(f"Closed project: {self.project_name}")
                    return True
                else:
                    logger.error(f"Failed to close project: {self.project_name}")
                    return False
            elif cleanup_action == 'stop':
                # Stop all nodes but keep project open
                success, nodes = self.api._make_request('GET', f'projects/{self.project_id}/nodes')
                
                if not success:
                    logger.error("Failed to get nodes for stopping")
                    return False
                    
                for node in nodes:
                    node_id = node.get('node_id')
                    node_name = node.get('name', 'unknown')
                    if node_id:
                        stop_success, _ = self.api._make_request('POST', f'projects/{self.project_id}/nodes/{node_id}/stop')
                        if stop_success:
                            logger.info(f"Stopped node: {node_name}")
                        else:
                            logger.warning(f"Failed to stop node: {node_name}")
                
                logger.info(f"Stopped all nodes in project: {self.project_name}")
                return True
            else:
                logger.warning(f"Unknown cleanup action: {cleanup_action}, project will remain open")
                return True
                
        except Exception as e:
            logger.error(f"Error cleaning up project: {e}")
            return False
    
    def _execute_on_node(self, node_id: str, command: str) -> Tuple[bool, Any]:
        """
        Execute a command on a node.
        
        Args:
            node_id: ID of the node
            command: Command to execute
            
        Returns:
            Tuple of (success, response)
        """
        try:
            # Ensure the node is started
            success, status = self.api._make_request('GET', f'projects/{self.project_id}/nodes/{node_id}/status')
            
            if not success:
                logger.error(f"Failed to get node status for command execution")
                return False, None
                
            if status.get('status') != 'started':
                logger.info(f"Starting node for command execution...")
                start_success, _ = self.api._make_request('POST', f'projects/{self.project_id}/nodes/{node_id}/start')
                
                if not start_success:
                    logger.error(f"Failed to start node for command execution")
                    return False, None
                    
                # Wait for node to start
                time.sleep(5)
            
            # Execute the command
            data = {
                'command': command
            }
            
            success, response = self.api._make_request(
                'POST', 
                f'projects/{self.project_id}/nodes/{node_id}/console/send',
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'}
            )
            
            if success:
                logger.info(f"Executed command on node: {command}")
                return True, response
            else:
                logger.error(f"Failed to execute command: {response}")
                return False, response
                
        except Exception as e:
            logger.error(f"Error executing command on node: {e}")
            return False, str(e)
    
    def _find_next_available_port(self, node_id: str, node_type: str, adapter_number: int = 0) -> int:
        """
        Find the next available port number on a node.
        
        Args:
            node_id: ID of the node
            node_type: Type of the node (e.g., 'docker')
            adapter_number: Adapter number
            
        Returns:
            Next available port number or -1 if no ports are available
        """
        try:
            # Get the node information
            success, node = self.api._make_request('GET', f'projects/{self.project_id}/nodes/{node_id}')
            
            if not success:
                logger.error(f"Failed to get node information for port finding")
                return -1
                
            # Get all links for the project
            success, links = self.api._make_request('GET', f'projects/{self.project_id}/links')
            
            if not success:
                logger.error("Failed to get links for port finding")
                return -1
                
            # Find all used ports for this node
            used_ports = set()
            for link in links:
                for node_info in link.get('nodes', []):
                    if node_info.get('node_id') == node_id and node_info.get('adapter_number') == adapter_number:
                        used_ports.add(node_info.get('port_number'))
            
            # Find the first available port number
            # For Docker nodes, ports typically start at 0
            start_port = 0
            max_ports = 8  # Default max ports per adapter
            
            # Check all potential port numbers
            for port in range(start_port, max_ports):
                if port not in used_ports:
                    return port
            
            # If we reached here, no ports are available
            logger.error(f"No available ports on adapter {adapter_number}")
            return -1
            
        except Exception as e:
            logger.error(f"Error finding next available port: {e}")
            return -1 