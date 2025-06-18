"""
GNS3 API Wrapper.

This module provides a wrapper for the GNS3 REST API.
"""

import logging
import time
import json
import os
import uuid
from typing import Dict, List, Tuple, Optional, Any

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gns3_api")

class GNS3API:
    """Wrapper for the GNS3 REST API."""
    
    def __init__(self, server_url: str = "http://localhost:3080", api_version: str = "v2", username: str = None, password: str = None):
        """
        Initialize the GNS3 API.
        
        Args:
            server_url: URL of the GNS3 server
            api_version: API version to use
            username: Username for GNS3 authentication (if enabled)
            password: Password for GNS3 authentication (if enabled)
        """
        self.server_url = server_url.rstrip("/")
        self.api_version = api_version
        self.base_url = f"{self.server_url}/{self.api_version}"
        self.auth = None
        
        # Configure authentication if provided
        if username and password:
            self.auth = (username, password)
            logger.info(f"Initialized GNS3API with authentication for user: {username}")
        else:
            logger.info(f"Initialized GNS3API without authentication")
        
        logger.info(f"Initialized GNS3API with server URL: {server_url}")
    
    def _make_request(self, method: str, endpoint: str, data=None, params=None, timeout=10) -> Tuple[bool, Any]:
        """
        Make a request to the GNS3 API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (success, response data)
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=timeout,
                auth=self.auth  # Pass authentication if configured
            )
            
            if response.status_code in [200, 201, 204]:
                try:
                    return True, response.json()
                except json.JSONDecodeError:
                    return True, {}
            elif response.status_code == 401:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False, f"Authentication failed: {response.status_code} - {response.text}"
            elif response.status_code == 403:
                logger.error(f"Authorization denied: {response.status_code} - {response.text}")
                return False, f"Authorization denied: {response.status_code} - {response.text}"
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return False, f"API request failed: {response.status_code} - {response.text}"
                
        except Exception as e:
            logger.error(f"Error making request: {e}")
            return False, f"Error making request: {e}"
    
    def get_projects(self) -> Tuple[bool, List[Dict]]:
        """
        Get all projects.
        
        Returns:
            Tuple of (success, list of projects)
        """
        return self._make_request('GET', 'projects')
    
    def get_project(self, project_id: str) -> Tuple[bool, Dict]:
        """
        Get a project by ID.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, project data)
        """
        return self._make_request('GET', f'projects/{project_id}')
    
    def create_project(self, name: str) -> Tuple[bool, Dict]:
        """
        Create a new project.
        
        Args:
            name: Project name
            
        Returns:
            Tuple of (success, project data)
        """
        data = {
            'name': name
        }
        return self._make_request('POST', 'projects', data=data)
    
    def delete_project(self, project_id: str) -> Tuple[bool, Dict]:
        """
        Delete a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('DELETE', f'projects/{project_id}')
    
    def get_project_by_name(self, name: str) -> Tuple[bool, Optional[Dict]]:
        """
        Get a project by name.
        
        Args:
            name: Project name
            
        Returns:
            Tuple of (success, project data or None if not found)
        """
        success, projects = self.get_projects()
        if not success:
            return False, f"Failed to get projects: {projects}"
        
        for project in projects:
            if project['name'] == name:
                return True, project
        
        return True, None
    
    def get_nodes(self, project_id: str) -> Tuple[bool, List[Dict]]:
        """
        Get all nodes in a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, list of nodes)
        """
        return self._make_request('GET', f'projects/{project_id}/nodes')
    
    def get_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict]:
        """
        Get a node by ID.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, node data)
        """
        return self._make_request('GET', f'projects/{project_id}/nodes/{node_id}')
    
    def get_node_by_name(self, project_id: str, name: str) -> Tuple[bool, Optional[Dict]]:
        """
        Get a node by name.
        
        Args:
            project_id: ID of the project
            name: Node name
            
        Returns:
            Tuple of (success, node data or None if not found)
        """
        success, nodes = self.get_nodes(project_id)
        if not success:
            return False, f"Failed to get nodes: {nodes}"
        
        for node in nodes:
            if node['name'] == name:
                return True, node
        
        return True, None
    
    def create_node(self, project_id: str, node_type: str, name: str, compute_id: str = "local", x: int = 0, y: int = 0, **kwargs) -> Tuple[bool, Dict]:
        """
        Create a new node.
        
        Args:
            project_id: ID of the project
            node_type: Type of node to create
            name: Node name
            compute_id: Compute ID
            x: X position
            y: Y position
            kwargs: Additional node parameters
            
        Returns:
            Tuple of (success, node data)
        """
        data = {
            'name': name,
            'node_type': node_type,
            'compute_id': compute_id,
            'x': x,
            'y': y,
            **kwargs
        }
        
        # Try creating the node with increased timeouts and retries
        max_retries = 5
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                response = requests.post(
                    f"{self.base_url}/projects/{project_id}/nodes", 
                    json=data,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    return True, response.json()
                elif response.status_code == 409 and "Port is already used" in response.text:
                    # Port conflict - try to free up ports and retry
                    logger.warning(f"Port conflict when creating node {name}. Attempting to resolve...")
                    # Track port conflicts to trigger aggressive cleanup if needed
                    if hasattr(self, '_port_conflicts'):
                        self._port_conflicts += 1
                    else:
                        self._port_conflicts = 1
                    
                    self._free_conflicting_ports()
                    retry_count += 1
                    time.sleep(5)  # Wait for ports to be freed
                    continue
                else:
                    logger.error(f"Failed to create node: {response.status_code} - {response.text}")
                    return False, f"Failed to create node: {response.status_code} - {response.text}"
            except Exception as e:
                logger.error(f"Error creating node: {e}")
                retry_count += 1
                last_error = str(e)
                time.sleep(3)
        
        # If we get here, all retries failed
        return False, f"Failed to create node after {max_retries} attempts. Last error: {last_error}"
    
    def _free_conflicting_ports(self):
        """
        Free up ports that might be causing conflicts.
        This is a helper method to resolve "Port is already used" errors.
        """
        try:
            import platform
            import subprocess
            import re
            
            if platform.system() == "Windows":
                # Windows approach to free conflicting ports
                try:
                    # Get list of processes using ports in the GNS3 range
                    output = subprocess.check_output("netstat -ano | findstr LISTENING", shell=True).decode('utf-8')
                    # Look for ports in GNS3's typical range (5000-10000)
                    port_pattern = re.compile(r':(\d{4,5})\s+.*LISTENING\s+(\d+)')
                    matches = port_pattern.findall(output)
                    
                    killed_count = 0
                    for port, pid in matches:
                        if 5000 <= int(port) <= 10000:
                            logger.info(f"Killing process {pid} using port {port}")
                            try:
                                subprocess.call(f"taskkill /F /PID {pid}", shell=True)
                                killed_count += 1
                            except Exception:
                                pass
                    
                    if killed_count > 0:
                        logger.info(f"Killed {killed_count} processes to free up ports")
                        time.sleep(2)  # Give time for ports to be released
                except Exception as e:
                    logger.error(f"Error freeing ports on Windows: {e}")
            
            elif platform.system() == "Linux":
                # Linux approach to free conflicting ports
                try:
                    output = subprocess.check_output("netstat -tlnp 2>/dev/null", shell=True).decode('utf-8')
                    port_pattern = re.compile(r':(\d{4,5})\s+.*?LISTEN\s+(\d+)')
                    matches = port_pattern.findall(output)
                    
                    killed_count = 0
                    for port, pid in matches:
                        if 5000 <= int(port) <= 10000:
                            logger.info(f"Killing process {pid} using port {port}")
                            try:
                                subprocess.call(f"kill -9 {pid}", shell=True)
                                killed_count += 1
                            except Exception:
                                pass
                    
                    if killed_count > 0:
                        logger.info(f"Killed {killed_count} processes to free up ports")
                        time.sleep(2)
                except Exception as e:
                    logger.error(f"Error freeing ports on Linux: {e}")
                        
        except Exception as e:
            logger.error(f"Error freeing conflicting ports: {e}")
    
    def delete_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict]:
        """
        Delete a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('DELETE', f'projects/{project_id}/nodes/{node_id}')
    
    def start_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict]:
        """
        Start a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('POST', f'projects/{project_id}/nodes/{node_id}/start')
    
    def stop_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict]:
        """
        Stop a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('POST', f'projects/{project_id}/nodes/{node_id}/stop')
    
    def get_links(self, project_id: str) -> Tuple[bool, List[Dict]]:
        """
        Get all links in a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, list of links)
        """
        return self._make_request('GET', f'projects/{project_id}/links')
    
    def create_link(self, project_id: str, data: Dict) -> Tuple[bool, Dict]:
        """
        Create a link between two nodes in a project.
        
        Args:
            project_id: ID of the project
            data: Dictionary with link data in the format:
                {
                    "nodes": [
                        {
                            "node_id": "<node_id1>",
                            "adapter_number": <adapter_number1>,
                            "port_number": <port_number1>
                        },
                        {
                            "node_id": "<node_id2>",
                            "adapter_number": <adapter_number2>,
                            "port_number": <port_number2>
                        }
                    ]
                }
                
        Returns:
            Tuple of (success, link data)
        """
        return self._make_request('POST', f'projects/{project_id}/links', data)
    
    def delete_link(self, project_id: str, link_id: str) -> Tuple[bool, Dict]:
        """
        Delete a link.
        
        Args:
            project_id: ID of the project
            link_id: ID of the link
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('DELETE', f'projects/{project_id}/links/{link_id}')
    
    def start_all_nodes(self, project_id: str) -> bool:
        """
        Start all nodes in a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Success or failure
        """
        success, nodes = self.get_nodes(project_id)
        if not success:
            logger.error(f"Failed to get nodes: {nodes}")
            return False
        
        all_success = True
        for node in nodes:
            success, response = self.start_node(project_id, node['node_id'])
            if not success:
                logger.error(f"Failed to start node {node['name']}: {response}")
                all_success = False
        
        return all_success
    
    def stop_all_nodes(self, project_id: str) -> bool:
        """
        Stop all nodes in a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Success or failure
        """
        success, nodes = self.get_nodes(project_id)
        if not success:
            logger.error(f"Failed to get nodes: {nodes}")
            return False
        
        all_success = True
        for node in nodes:
            success, response = self.stop_node(project_id, node['node_id'])
            if not success:
                logger.error(f"Failed to stop node {node['name']}: {response}")
                all_success = False
        
        return all_success
    
    def get_templates(self) -> Tuple[bool, List[Dict]]:
        """
        Get all templates.
        
        Returns:
            Tuple of (success, list of templates)
        """
        return self._make_request('GET', 'templates')
    
    def get_template_by_name(self, name: str) -> Tuple[bool, Optional[Dict]]:
        """
        Get a template by name.
        
        Args:
            name: Template name
            
        Returns:
            Tuple of (success, template data or None if not found)
        """
        success, templates = self.get_templates()
        if not success:
            return False, f"Failed to get templates: {templates}"
        
        for template in templates:
            if template['name'] == name:
                return True, template
        
        return True, None
    
    def get_computes(self) -> Tuple[bool, List[Dict]]:
        """
        Get all compute nodes.
        
        Returns:
            Tuple of (success, list of compute nodes)
        """
        return self._make_request('GET', 'computes')
    
    def get_compute(self, compute_id: str) -> Tuple[bool, Dict]:
        """
        Get a compute node by ID.
        
        Args:
            compute_id: ID of the compute node
            
        Returns:
            Tuple of (success, compute node data)
        """
        return self._make_request('GET', f'computes/{compute_id}')
    
    def get_node_files(self, project_id: str, node_id: str) -> Tuple[bool, List[Dict]]:
        """
        Get files in a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, list of files)
        """
        return self._make_request('GET', f'projects/{project_id}/nodes/{node_id}/files')
    
    def get_file_from_node(self, project_id: str, node_id: str, path: str) -> Tuple[bool, str]:
        """
        Get a file from a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            path: Path of the file
            
        Returns:
            Tuple of (success, file content)
        """
        url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}/files{path}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return True, response.text
            else:
                logger.error(f"Failed to get file: {response.status_code} - {response.text}")
                return False, f"Failed to get file: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return False, f"Error getting file: {e}"
    
    def write_file_to_node(self, project_id: str, node_id: str, path: str, content: str) -> Tuple[bool, str]:
        """
        Write a file to a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            path: Path of the file
            content: Content of the file
            
        Returns:
            Tuple of (success, response message)
        """
        url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}/files{path}"
        
        try:
            response = requests.post(url, data=content, timeout=10)
            if response.status_code in [200, 201]:
                return True, "File written successfully"
            else:
                logger.error(f"Failed to write file: {response.status_code} - {response.text}")
                return False, f"Failed to write file: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return False, f"Error writing file: {e}"
    
    def create_directory_on_node(self, project_id: str, node_id: str, path: str) -> Tuple[bool, str]:
        """
        Create a directory on a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            path: Path of the directory
            
        Returns:
            Tuple of (success, response message)
        """
        endpoint = f'projects/{project_id}/nodes/{node_id}/files{path}'
        data = {
            'action': 'create_directory'
        }
        success, response = self._make_request('POST', endpoint, data=data)
        if success:
            return True, "Directory created successfully"
        else:
            return False, response
    
    def execute_command_on_node(self, project_id: str, node_id: str, command: str) -> Tuple[bool, Dict]:
        """
        Execute a command on a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            command: Command to execute
            
        Returns:
            Tuple of (success, command result)
        """
        try:
            # First, get the node type to determine the correct endpoint
            success, node_data = self.get_node(project_id, node_id)
            if not success:
                logger.error(f"Failed to get node information for node {node_id}")
                return False, {"error": "Failed to get node information"}
            
            node_type = node_data.get('node_type', '').lower()
            
            # For VPCS nodes, we need to use a specific method for console commands
            if node_type == 'vpcs':
                logger.info(f"Executing command on VPCS node {node_id}: {command}")
                success, result = self.send_vpcs_command(project_id, node_id, command)
                if success:
                    return True, {"output": result}
                else:
                    return False, {"error": result}
            else:
                # For other node types (like Docker), use the exec endpoint
                data = {
                    'command': command
                }
                return self._make_request('POST', f'projects/{project_id}/nodes/{node_id}/exec', data=data, timeout=30)
        except Exception as e:
            logger.error(f"Error executing command on node {node_id}: {e}")
            return False, {"error": str(e)}
    
    def wait_for_node_status(self, project_id: str, node_id: str, status: str, timeout: int = 60) -> bool:
        """
        Wait for a node to reach a specific status.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            status: Status to wait for
            timeout: Timeout in seconds
            
        Returns:
            Success or failure
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            success, node = self.get_node(project_id, node_id)
            if success and node['status'] == status:
                return True
            time.sleep(1)
        
        return False
    
    def get_project_stats(self, project_id: str) -> Tuple[bool, Dict]:
        """
        Get project statistics.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, project stats)
        """
        return self._make_request('GET', f'projects/{project_id}/stats')
    
    def get_node_console(self, project_id: str, node_id: str) -> Tuple[bool, Dict]:
        """
        Get console configuration for a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, console configuration)
        """
        return self._make_request('GET', f'projects/{project_id}/nodes/{node_id}/console')
    
    def get_node_console_history(self, project_id: str, node_id: str) -> Tuple[bool, str]:
        """
        Get console history for a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, console history)
        """
        url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}/console/read"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return True, response.text
            else:
                logger.error(f"Failed to get console history: {response.status_code} - {response.text}")
                return False, f"Failed to get console history: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Error getting console history: {e}")
            return False, f"Error getting console history: {e}"
    
    def send_vpcs_command(self, project_id: str, node_id: str, command: str) -> Tuple[bool, str]:
        """
        Send a command specifically to a VPCS node's console with improved reliability.
        
        Args:
            project_id: ID of the project
            node_id: ID of the VPCS node
            command: Command to send to the console
            
        Returns:
            Tuple of (success, command result)
        """
        max_retries = 3
        retry_count = 0
        last_error = None
        
        # Pre-format VPCS ping commands
        original_command = command
        if "ping" in command.lower():
            # VPCS uses a simple ping format without Linux options
            ping_parts = command.split()
            if len(ping_parts) > 1:
                target = ping_parts[1]
                # Strip any options and force proper VPCS ping format
                # VPCS ping format: ping <target> [-c count]
                command = f"ping {target} -c 3"  # Default to 3 pings
                logger.info(f"Reformatted ping command to VPCS syntax: {command}")
        
        # First make sure the node is started
        success, node_data = self.get_node(project_id, node_id)
        if not success:
            logger.error(f"Failed to get node information for node {node_id}")
            return False, "Failed to get node information"
        
        # Check if node is running
        node_status = node_data.get('status', '')
        node_name = node_data.get('name', f"node_{node_id}")
        
        if node_status != 'started':
            logger.info(f"Node {node_name} (ID: {node_id}) is not started (status: {node_status}), starting it now")
            start_success, _ = self.start_node(project_id, node_id)
            if not start_success:
                logger.error(f"Failed to start node {node_name}")
                return False, f"Failed to start node {node_name} (status: {node_status})"
            
            # Wait for node to fully start
            logger.info(f"Waiting for node {node_name} to start...")
            if not self.wait_for_node_status(project_id, node_id, 'started', timeout=30):
                logger.error(f"Node {node_name} failed to start within timeout")
                return False, f"Node {node_name} failed to start properly"
            
            # Additional wait time for VPCS to fully initialize
            time.sleep(2)
        
        while retry_count < max_retries:
            try:
                # Import connection pool if available
                try:
                    from src.networking.telnet_connection_pool import connection_pool
                    has_connection_pool = True
                    logger.info(f"Using connection pool for command: {command}")
                except ImportError:
                    has_connection_pool = False
                    logger.info(f"Connection pool not available, using direct telnet")
                
                # Get console information
                success, node_data = self.get_node(project_id, node_id)
                if not success:
                    logger.error(f"Failed to get node information for node {node_id}")
                    retry_count += 1
                    last_error = "Failed to get node information"
                    time.sleep(1)
                    continue
                
                if 'console' not in node_data or not node_data['console']:
                    logger.error(f"No console port found for node {node_id}")
                    retry_count += 1
                    last_error = "No console port found for node"
                    time.sleep(1)
                    continue
                
                console_port = node_data['console']
                console_host = node_data.get('console_host', 'localhost')
                
                logger.info(f"Connecting to console {console_host}:{console_port} for node {node_name}")
                
                # Approach 1: Use connection pool if available
                if has_connection_pool:
                    wait_time = 4 if "ping" in command.lower() else 2
                    success, result = connection_pool.send_command(
                        console_host, console_port, command, wait_time=wait_time
                    )
                    
                    if success:
                        logger.info(f"Command executed successfully via connection pool")
                        return True, result
                    elif "ping" in command.lower() and "host unreachable" in result.lower():
                        # Clear ping failure, don't retry
                        logger.warning(f"Ping failed - host unreachable")
                        return False, result
                    else:
                        logger.warning(f"Command failed via connection pool: {result}")
                
                # Approach 2: Use console API
                try:
                    # Direct console API call
                    console_url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}/console/send"
                    logger.info(f"Using console API for command: {command}")
                    
                    # Send the command to the console
                    console_data = {"text": f"{command}\r\n"}
                    send_response = requests.post(
                        console_url, 
                        json=console_data, 
                        auth=self.auth if self.auth else None,
                        timeout=15
                    )
                    
                    if send_response.status_code in [200, 201, 204]:
                        # Wait for command to complete
                        wait_time = 4 if "ping" in command.lower() else 2
                        logger.info(f"Waiting {wait_time}s for command to complete...")
                        time.sleep(wait_time)
                        
                        # Read the console output
                        read_url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}/console/read"
                        read_response = requests.get(
                            read_url, 
                            auth=self.auth if self.auth else None,
                            timeout=15
                        )
                        
                        if read_response.status_code == 200:
                            console_output = read_response.text
                            
                            # Check for successful ping indicators if it's a ping command
                            if "ping" in command.lower():
                                if "bytes from" in console_output:
                                    logger.info(f"Ping command succeeded via console API")
                                    return True, console_output
                                elif "host unreachable" in console_output.lower():
                                    logger.warning(f"Ping failed - host unreachable")
                                    return False, console_output
                            
                            logger.info(f"Command executed successfully via console API")
                            return True, console_output
                except Exception as e:
                    logger.error(f"Console API approach failed: {str(e)}")
                
                # Approach 3: Direct telnet as last resort
                try:
                    import telnetlib
                    import socket
                    
                    # Connect with a reasonable timeout
                    tn = telnetlib.Telnet(console_host, console_port, timeout=10)
                    
                    # Send a newline to get a prompt
                    tn.write(b"\n")
                    time.sleep(1)
                    
                    # Clear pending output
                    try:
                        pending_output = tn.read_very_eager().decode('utf-8', errors='ignore')
                        logger.debug(f"Cleared pending output: {pending_output}")
                    except:
                        pass
                    
                    # Try to get a prompt
                    tn.write(b"\n")
                    time.sleep(1)
                    
                    prompt_output = ""
                    try:
                        prompt_output = tn.read_until(b">", timeout=5).decode('utf-8', errors='ignore')
                    except socket.timeout:
                        # If timeout, try again
                        tn.write(b"\n")
                        time.sleep(1)
                        try:
                            prompt_output = tn.read_very_eager().decode('utf-8', errors='ignore')
                        except:
                            pass
                    
                    # Send the command
                    logger.info(f"Sending command via direct telnet: {command}")
                    tn.write(f"{command}\n".encode('ascii'))
                    
                    # Wait for command completion
                    wait_time = 4 if "ping" in command.lower() else 2
                    logger.info(f"Waiting {wait_time}s for command to complete...")
                    time.sleep(wait_time)
                    
                    # Read the response
                    result = ""
                    try:
                        result = tn.read_until(b">", timeout=5).decode('utf-8', errors='ignore')
                    except socket.timeout:
                        try:
                            result = tn.read_very_eager().decode('utf-8', errors='ignore')
                        except:
                            result = "Timeout waiting for command completion"
                    
                    # Close the connection
                    try:
                        tn.close()
                    except:
                        pass
                    
                    # Check result
                    if "ping" in command.lower():
                        if "bytes from" in result:
                            logger.info(f"Ping command succeeded via direct telnet")
                            return True, result
                        elif "host unreachable" in result.lower():
                            logger.warning(f"Ping failed - host unreachable")
                            return False, result
                    
                    logger.info(f"Command executed via direct telnet")
                    return True, result
                    
                except Exception as e:
                    logger.error(f"Direct telnet approach failed: {str(e)}")
                    last_error = f"Telnet error: {str(e)}"
                
                # If we're still here, increment retry counter
                retry_count += 1
                time.sleep(2)  # Wait before retry
                
            except Exception as e:
                logger.error(f"General error in send_vpcs_command: {str(e)}")
                retry_count += 1
                last_error = f"General error: {str(e)}"
                time.sleep(2)  # Wait before retry
        
        # If all retries failed
        if "ping" in original_command.lower():
            logger.error(f"Ping failed after {max_retries} retries. Last error: {last_error}")
            return False, f"Host unreachable (ping failed after {max_retries} attempts)"
        else:
            logger.error(f"Failed to send command after {max_retries} retries. Last error: {last_error}")
            return False, f"Failed to send command after {max_retries} retries. Last error: {last_error}"
    
    def update_link(self, project_id: str, link_id: str, data: Dict) -> Tuple[bool, Dict]:
        """
        Update a link's properties.
        
        Args:
            project_id: ID of the project
            link_id: ID of the link
            data: Link properties to update
            
        Returns:
            Tuple of (success, response data)
        """
        try:
            url = f"{self.base_url}/projects/{project_id}/links/{link_id}"
            
            # Use a longer timeout for this operation
            response = requests.put(url, json=data, timeout=30)
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"Successfully updated link {link_id} properties")
                try:
                    return True, response.json()
                except json.JSONDecodeError:
                    return True, {}
            else:
                logger.error(f"Failed to update link {link_id}: {response.status_code} - {response.text}")
                return False, f"{response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Error updating link: {e}")
            return False, f"Error updating link: {e}"
    
    def close_project(self, project_id: str) -> Tuple[bool, Dict]:
        """
        Close a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('POST', f'projects/{project_id}/close')
    
    def open_project(self, project_id: str) -> Tuple[bool, Dict]:
        """
        Open a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, response data)
        """
        return self._make_request('POST', f'projects/{project_id}/open') 