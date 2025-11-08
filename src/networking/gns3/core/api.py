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
GNS3 API Client.

This module provides a client for interacting with the GNS3 REST API.
"""

import logging
import requests
import time
import os
import json
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class GNS3API:
    """Client for interacting with GNS3 REST API."""
    
    def __init__(self, base_url: str):
        """Initialize the GNS3 API client.

        Args:
            base_url: The base URL of the GNS3 server API.
        """
        # Ensure base_url is properly formatted
        if not base_url.startswith('http'):
            base_url = f'http://{base_url}'
            
        # Parse and normalize URL to ensure consistent format
        parsed_url = urlparse(base_url)
        base_path = parsed_url.path
        if not base_path.endswith('/v2'):
            if base_path.endswith('/'):
                base_path = f"{base_path}v2"
            else:
                base_path = f"{base_path}/v2"
                
        # Reconstruct URL with normalized path but without trailing slash
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}".rstrip('/')
        self.server_url = self.base_url
        
        # Set up session
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for local development
        self.session.allow_redirects = True
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized GNS3 API client with base URL: {self.base_url}")
        
        # Test connection
        try:
            success, version = self._make_request('GET', 'version')
            if success:
                self.logger.info(f"Successfully connected to GNS3 server at {self.base_url}")
                self.logger.info(f"GNS3 version: {version.get('version')}")
            else:
                self.logger.error("Failed to connect to GNS3 server")
        except Exception as e:
            self.logger.error(f"Error connecting to GNS3 server: {str(e)}")
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint to ensure consistent format.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Normalized endpoint without leading slash
        """
        # Remove leading and trailing slashes for consistency
        return endpoint.strip('/')
    
    def _make_request(self, method: str, endpoint: str, max_retries: int = None, retry_delay: int = None, **kwargs) -> Tuple[bool, Any]:
        """Make HTTP request to GNS3 API with retry logic.
        
        Args:
            method: The HTTP method (GET, POST, PUT, DELETE)
            endpoint: The API endpoint
            max_retries: Maximum number of retry attempts (defaults to self._default_max_retries if set)
            retry_delay: Delay between retries in seconds (defaults to self._default_retry_delay if set)
            **kwargs: Additional request parameters
                - timeout: Request timeout in seconds
        
        Returns:
            Tuple[bool, Any]: Tuple of (success, response_data)
        """
        # Use instance defaults if parameters are not provided
        max_retries = max_retries or getattr(self, '_default_max_retries', 3)
        retry_delay = retry_delay or getattr(self, '_default_retry_delay', 1)
        
        # Set default timeout if not provided, using instance default if available
        timeout = kwargs.pop('timeout', getattr(self, '_default_timeout', 30))
        
        # Special handling for version endpoint
        if endpoint == 'version':
            # First try v2/version
            url = f"{self.base_url}/{self._normalize_endpoint('version')}"
        else:
            # Normalize endpoint
            normalized_endpoint = self._normalize_endpoint(endpoint)
            # Prepare URL
            url = f"{self.base_url}/{normalized_endpoint}"
        
        # Log the request
        self.logger.info(f"API REQUEST: {method} {url}")
        if 'json' in kwargs:
            self.logger.info(f"REQUEST DATA: {kwargs['json']}")
        
        # Try the request with retries
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, timeout=timeout, **kwargs)
                
                # Check response
                if response.ok:
                    self.logger.info(f"API RESPONSE: {response.status_code} - OK")
                    try:
                        return True, response.json()
                    except ValueError:
                        return True, response.text
                else:
                    # Log error and try to parse error message
                    error_msg = response.text
                    try:
                        error_json = response.json()
                        if isinstance(error_json, dict) and 'message' in error_json:
                            error_msg = error_json['message']
                    except:
                        pass
                    
                    self.logger.error(f"API request failed: {response.status_code} - {error_msg}")
                    
                    # Special case for version endpoint - try without v2 prefix if it failed
                    if endpoint == 'version' and attempt == 0:
                        self.logger.info("Trying alternative version endpoint...")
                        # Try base URL without /v2 component
                        base_url_parts = self.base_url.split('/v2')
                        if len(base_url_parts) > 1:
                            alt_url = base_url_parts[0] + '/v2/version'
                        else:
                            alt_url = self.base_url.rstrip('/') + '/version'
                        
                        self.logger.info(f"Trying alternative version URL: {alt_url}")
                        try:
                            alt_response = self.session.request(method, alt_url, timeout=timeout, **kwargs)
                            if alt_response.ok:
                                self.logger.info(f"Alternative version endpoint succeeded: {alt_response.status_code}")
                                try:
                                    return True, alt_response.json()
                                except ValueError:
                                    return True, alt_response.text
                        except Exception as e:
                            self.logger.warning(f"Alternative version endpoint failed: {e}")
                    
                    # Check if retry might help
                    if response.status_code in [429, 500, 502, 503, 504] and attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                        time.sleep(retry_delay)
                        continue
                    
                    return False, error_msg
                    
            except requests.exceptions.Timeout:
                self.logger.error(f"API request timed out after {timeout} seconds")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                return False, f"Request timed out after {timeout} seconds"
                
            except requests.exceptions.ConnectionError:
                self.logger.error(f"Connection error to GNS3 server")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                return False, "Connection error to GNS3 server"
                
            except Exception as e:
                self.logger.error(f"API request failed: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                return False, str(e)
    
    def get_version(self) -> Optional[Dict[str, Any]]:
        """Get the GNS3 server version.

        Returns:
            Dict containing version information or None if failed.
        """
        try:
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Attempting to connect to GNS3 server (attempt {attempt+1}/{max_retries})...")
                    success, version_info = self._make_request('GET', 'version', timeout=5)
                    
                    if success and isinstance(version_info, dict):
                        return version_info
                    else:
                        self.logger.error(f"Invalid version response format: {version_info}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            return None
                        
                except Exception as e:
                    self.logger.warning(f"Connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        self.logger.error("Could not connect to GNS3 server after multiple attempts")
                        self.logger.error("Please make sure the GNS3 server is running and accessible at the specified URL")
                        self.logger.error(f"Server URL: {self.base_url}")
                        return None
            return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get GNS3 version: {str(e)}")
            return None
    
    def get_projects(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """Get all projects.
        
        Returns:
            Tuple of (success, projects)
            - success: True if successful, False otherwise
            - projects: List of project data if successful, None otherwise
        """
        return self._make_request('GET', 'projects')
    
    def create_project(self, name: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Create a new GNS3 project.

        Args:
            name: Name of the project to create.

        Returns:
            Tuple of (success, project_data)
        """
        return self._make_request('POST', 'projects', json={"name": name})
    
    def get_project(self, project_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Get a project by ID.
        
        Args:
            project_id: The ID of the project to get
            
        Returns:
            Tuple of (success, project_data)
        """
        return self._make_request('GET', f'projects/{project_id}')
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            True if successful, False otherwise
        """
        success, _ = self._make_request('DELETE', f'projects/{project_id}')
        return success
    
    def open_project(self, project_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Open a project.
        
        Args:
            project_id: The ID of the project to open
            
        Returns:
            Tuple of (success, project_data)
        """
        # First check if the project is already open
        success, project = self.get_project(project_id)
        if success and project.get('status') == 'opened':
            return True, project
            
        # If project exists but not open, try to open it
        if success:
            return self._make_request('POST', f'projects/{project_id}/open')
        
        return False, None
    
    def close_project(self, project_id: str) -> bool:
        """Close a project.
        
        Args:
            project_id: The ID of the project to close
            
        Returns:
            True if successful, False otherwise
        """
        success, _ = self._make_request('POST', f'projects/{project_id}/close')
        return success
    
    def get_nodes(self, project_id: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """Get all nodes in a project.
        
        Args:
            project_id: The ID of the project
            
        Returns:
            Tuple of (success, nodes)
            - success: True if successful, False otherwise
            - nodes: List of node data if successful, None otherwise
        """
        return self._make_request('GET', f'projects/{project_id}/nodes')
    
    def create_node(self, project_id: str, name: str, template_id: str, **kwargs) -> Tuple[bool, Dict]:
        """Create a node in a project.
        
        Args:
            project_id: The ID of the project
            name: The name of the node
            template_id: The ID of the template to use
            **kwargs: Additional node parameters
                - x: X position (default: 0)
                - y: Y position (default: 0)
                - compute_id: Compute ID (default: 'local')
                - node_type: Node type (default: determined from template)
                - properties: Node properties (optional)
                - adapters: Number of adapters for the node (optional)
                
        Returns:
            Tuple of (success, node_data)
        """
        try:
            # Get template info first to set proper node parameters
            success, template = self.get_template(template_id)
            if not success:
                self.logger.error(f"Failed to get template information for {template_id}")
                return False, {}
                
            # Set node data
            node_data = {
                'name': name,
                'template_id': template_id,
                'x': kwargs.get('x', 0),
                'y': kwargs.get('y', 0),
                'compute_id': kwargs.get('compute_id', 'local')
            }
            
            # Add node type from template or kwargs
            node_type = kwargs.get('node_type')
            if not node_type and template:
                node_type = template.get('template_type')
            if node_type:
                node_data['node_type'] = node_type
                
            # Add console type from template
            console_type = template.get('console_type')
            if console_type:
                node_data['console_type'] = console_type
                
            # Set up properties if not already present
            if 'properties' not in node_data:
                node_data['properties'] = {}
                
            # Add properties if provided (merge with existing properties)
            properties = kwargs.get('properties', {})
            if properties:
                node_data['properties'].update(properties)
                
            # For docker nodes, include image if available
            if node_type == 'docker' and template.get('image'):
                node_data['properties']['image'] = template.get('image')
                
            # Handle adapters count differently based on node type
            if 'adapters' in kwargs and kwargs['adapters'] is not None:
                adapters_count = kwargs['adapters']
                self.logger.debug(f"Processing adapters={adapters_count} for node {name}")
                
                # For Ethernet switch, adapters go in ports_mapping
                if node_type == 'ethernet_switch':
                    if 'ports_mapping' not in node_data['properties']:
                        node_data['properties']['ports_mapping'] = []
                        for i in range(adapters_count):
                            node_data['properties']['ports_mapping'].append({
                                'name': f'Ethernet{i}',
                                'port_number': i,
                                'type': 'access',
                                'vlan': 1
                            })
                # For Docker nodes, adapters go in adapters property within properties
                elif node_type == 'docker':
                    node_data['properties']['adapters'] = adapters_count
                # For other node types, handle according to their specific requirements
                else:
                    # For some node types, adapters might be a top-level parameter
                    node_data['adapters'] = adapters_count
                    
            # Create the node
            self.logger.debug(f"Creating node with data: {node_data}")
            success, node = self._make_request(
                'POST', 
                f'projects/{project_id}/nodes',
                json=node_data
            )
            
            if not success:
                return False, {}
                
            # If environment variables are provided separately for Docker nodes and they weren't already set,
            # update the node to set them
            environment = kwargs.get('environment')
            if success and environment and node_type == 'docker' and node.get('node_id'):
                node_id = node.get('node_id')
                
                # Format environment as a string
                if isinstance(environment, dict):
                    env_str = " ".join([f"{k}={v}" for k, v in environment.items()])
                else:
                    env_str = environment
                    
                # Update the node with environment variables
                update_data = {
                    'properties': {
                        'environment': env_str
                    }
                }
                
                success, updated_node = self._make_request(
                    'PUT',
                    f'projects/{project_id}/nodes/{node_id}',
                    json=update_data
                )
                
                if success:
                    self.logger.info(f"Updated node {name} with environment variables")
                    return True, updated_node
                else:
                    self.logger.warning(f"Created node {name} but failed to set environment variables")
                    return True, node
            
            return success, node
            
        except Exception as e:
            self.logger.error(f"Error creating node: {str(e)}")
            return False, {}
    
    def update_node(self, project_id: str, node_id: str, node_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Update a node."""
        return self._make_request('PUT', f'projects/{project_id}/nodes/{node_id}', json=node_data)
    
    def get_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get a node by ID."""
        return self._make_request('GET', f'projects/{project_id}/nodes/{node_id}')
    
    def delete_node(self, project_id: str, node_id: str) -> Tuple[bool, Any]:
        """Delete a node."""
        return self._make_request('DELETE', f'projects/{project_id}/nodes/{node_id}')
    
    def start_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Start a node.
        
        Args:
            project_id: The ID of the project
            node_id: The ID of the node
            
        Returns:
            Tuple of (success, response)
        """
        # Check node status first
        success, node = self.get_node(project_id, node_id)
        if success and node.get('status') == 'started':
            self.logger.info(f"Node {node_id} is already started")
            return True, node
            
        return self._make_request('POST', f'projects/{project_id}/nodes/{node_id}/start')
    
    def stop_node(self, project_id: str, node_id: str) -> bool:
        """Stop a node.
        
        Args:
            project_id: The ID of the project
            node_id: The ID of the node
            
        Returns:
            True if successful, False otherwise
        """
        # Check node status first
        success, node = self.get_node(project_id, node_id)
        if success and node.get('status') == 'stopped':
            self.logger.info(f"Node {node_id} is already stopped")
            return True
            
        success, _ = self._make_request('POST', f'projects/{project_id}/nodes/{node_id}/stop')
        return success
    
    def get_links(self, project_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Get all links in a project."""
        return self._make_request('GET', f'projects/{project_id}/links')
    
    def create_link(self, project_id: str = None, nodes: List[Dict] = None, filters: Optional[Dict] = None) -> Tuple[bool, Dict[str, Any]]:
        """Create a link between nodes.
        
        Args:
            project_id: The ID of the project
            nodes: List of node connection data
                Each node entry should have:
                - node_id: ID of the node
                - adapter_number: Adapter number
                - port_number: Port number
            filters: Link filters (optional)
            
        Returns:
            Tuple of (success, link_data)
        """
        if not project_id or not nodes or len(nodes) != 2:
            self.logger.error("Invalid parameters for create_link")
            return False, {}
            
        # Prepare link data
        link_data = {'nodes': nodes}
        if filters:
            link_data['filters'] = filters
            
        return self._make_request('POST', f'projects/{project_id}/links', json=link_data)
    
    def delete_link(self, project_id: str, link_id: str) -> Tuple[bool, Any]:
        """Delete a link."""
        return self._make_request('DELETE', f'projects/{project_id}/links/{link_id}')
    
    def configure_link(self, project_id: str, link_id: str, **params) -> Tuple[bool, Any]:
        """Configure a link."""
        return self._make_request('PUT', f'projects/{project_id}/links/{link_id}', json=params)
    
    def get_templates(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """Get all templates.
        
        Returns:
            Tuple of (success, templates)
        """
        return self._make_request('GET', 'templates')
    
    def get_template(self, template_id: str) -> Tuple[bool, Dict]:
        """Get template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Tuple of (success, template)
        """
        return self._make_request('GET', f'templates/{template_id}')
    
    def create_template(self, template_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """Create a template.
        
        Args:
            template_data: Template data
            
        Returns:
            Tuple of (success, template)
        """
        return self._make_request('POST', 'templates', json=template_data)
    
    def delete_template(self, template_id: str) -> Tuple[bool, Any]:
        """Delete a template."""
        return self._make_request('DELETE', f'templates/{template_id}')
    
    def run_command(self, project_id: str, node_id: str, command: str, retries: int = 3, retry_delay: int = 2) -> Tuple[bool, str]:
        """Run a command on a node.
        
        This method tries multiple approaches to run commands on nodes.
        
        Args:
            project_id: The ID of the project
            node_id: The ID of the node
            command: The command to run
            retries: Number of retries if the command fails
            retry_delay: Delay between retries in seconds
            
        Returns:
            Tuple of (success, command_output)
        """
        # Make sure the node is running
        success, node = self.get_node(project_id, node_id)
        if not success:
            self.logger.error(f"Failed to get node {node_id}")
            return False, f"Failed to get node {node_id}"
            
        # If node is not started, try to start it
        if node.get('status') != 'started':
            self.logger.info(f"Node {node_id} is not started, attempting to start it")
            start_success, _ = self.start_node(project_id, node_id)
            if not start_success:
                self.logger.error(f"Failed to start node {node_id}")
                return False, f"Failed to start node {node_id}"
                
            # Give the node some time to start
            time.sleep(2)
        
        # Try using the exec API endpoint first
        success, result = self._make_request(
            'POST', 
            f'projects/{project_id}/nodes/{node_id}/exec',
            json={'command': command}, 
            timeout=30
        )
        
        if success:
            self.logger.info(f"GNS3 exec successful for node {node_id}")
            return True, result if isinstance(result, str) else json.dumps(result)
            
        # If exec failed, try the run_command method
        self.logger.warning(f"GNS3 exec failed for node {node_id}, trying run_command")
        return self.run_command(project_id, node_id, command)
    
    def execute_command_on_node(self, project_id: str, node_id: str, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """Execute a command on a node using the best method for the node type.
        
        Args:
            project_id: The ID of the project
            node_id: The ID of the node
            command: The command to execute
            timeout: Timeout for the command execution
            
        Returns:
            Tuple of (success, command_output)
        """
        self.logger.info(f"Executing command on node {node_id}: {command}")
        
        # Make sure the node is running
        success, node = self.get_node(project_id, node_id)
        if not success:
            self.logger.error(f"Failed to get node {node_id}")
            return False, f"Failed to get node {node_id}"
            
        # If node is not started, try to start it
        if node.get('status') != 'started':
            self.logger.info(f"Node {node_id} is not started, attempting to start it")
            start_success, _ = self.start_node(project_id, node_id)
            if not start_success:
                self.logger.error(f"Failed to start node {node_id}")
                return False, f"Failed to start node {node_id}"
                
            # Give the node some time to start
            time.sleep(2)
        
        # Try using the exec API endpoint first
        success, result = self._make_request(
            'POST', 
            f'projects/{project_id}/nodes/{node_id}/exec',
            json={'command': command}, 
            timeout=timeout
        )
        
        if success:
            self.logger.info(f"GNS3 exec successful for node {node_id}")
            return True, result if isinstance(result, str) else json.dumps(result)
            
        # If exec failed, try the run_command method
        self.logger.warning(f"GNS3 exec failed for node {node_id}, trying run_command")
        return self.run_command(project_id, node_id, command)
    
    def wait_for_node_started(self, project_id: str, node_id: str, timeout: int = 30) -> bool:
        """Wait for node to be started.
        
        Args:
            project_id: The ID of the project
            node_id: The ID of the node
            timeout: Timeout in seconds
            
        Returns:
            True if node started, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            success, node = self.get_node(project_id, node_id)
            if success and node.get('status') == 'started':
                return True
            time.sleep(1)
        return False
    
    def wait_for_node_stopped(self, project_id: str, node_id: str, timeout: int = 30) -> bool:
        """Wait for node to be stopped."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            success, node = self.get_node(project_id, node_id)
            if success and node.get('status') == 'stopped':
                return True
            time.sleep(1)
        return False
    
    def get_node_status(self, project_id: str, node_id: str) -> str:
        """Get the status of a node.
        
        Args:
            project_id: The ID of the project
            node_id: The ID of the node
            
        Returns:
            Status of the node as a string (e.g., 'started', 'stopped', 'suspended')
        """
        success, node = self.get_node(project_id, node_id)
        if success and node:
            return node.get('status', 'unknown') 