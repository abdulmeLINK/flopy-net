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
GNS3 API Client for Federated Learning Network Simulator.

This module provides a client for interacting with the GNS3 REST API
to create and manage network projects, nodes, and links.
"""

import logging
import json
import time
import requests
from typing import Dict, List, Optional, Tuple, Any, Union

from src.core.common.logger import LoggerMixin

class GNS3ApiClient(LoggerMixin):
    """Client for interacting with the GNS3 REST API."""
    
    def __init__(self, server_url="http://localhost:3080", timeout=10):
        """
        Initialize the GNS3 API client.
        
        Args:
            server_url: URL of the GNS3 server API
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.server_url = server_url
        self.timeout = timeout
        self.session = requests.Session()
        self.version = None
        
        # Try to get server version
        try:
            self.version = self._get_version()
            self.logger.info(f"Connected to GNS3 server {self.server_url}, version {self.version}")
        except Exception as e:
            self.logger.warning(f"Failed to connect to GNS3 server: {e}")
    
    def _get_version(self) -> str:
        """
        Get the GNS3 server version.
        
        Returns:
            str: Server version
        """
        response = self.session.get(f"{self.server_url}/v2/version", timeout=self.timeout)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("version", "unknown")
        
        return "unknown"
    
    def _make_request(self, method, endpoint, data=None, params=None, retry=1) -> Optional[Dict[str, Any]]:
        """
        Make a request to the GNS3 API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: URL parameters
            retry: Number of retries
            
        Returns:
            Dict or None: Response data or None on failure
        """
        url = f"{self.server_url}/v2{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        json_data = None
        
        if data:
            json_data = json.dumps(data)
        
        for attempt in range(retry + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=json_data,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code in (200, 201, 204):
                    if response.content:
                        return response.json()
                    return {}
                
                # Handle error responses
                self.logger.error(f"GNS3 API error ({response.status_code}): {response.text}")
                
                if attempt < retry:
                    # Wait before retrying
                    time.sleep(1)
                    continue
                
                return None
                
            except requests.RequestException as e:
                self.logger.error(f"Request error: {e}")
                
                if attempt < retry:
                    # Wait before retrying
                    time.sleep(1)
                    continue
                
                return None
    
    # Project Management
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects.
        
        Returns:
            List[Dict]: List of projects
        """
        result = self._make_request("GET", "/projects")
        return result or []
    
    def create_project(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Create a new project.
        
        Args:
            name: Project name
            
        Returns:
            Dict or None: Project information or None on failure
        """
        data = {"name": name}
        return self._make_request("POST", "/projects", data=data)
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project information.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict or None: Project information or None on failure
        """
        return self._make_request("GET", f"/projects/{project_id}")
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("DELETE", f"/projects/{project_id}")
        return result is not None
    
    def start_project(self, project_id: str) -> bool:
        """
        Start all nodes in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("POST", f"/projects/{project_id}/nodes/start")
        return result is not None
    
    def stop_project(self, project_id: str) -> bool:
        """
        Stop all nodes in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("POST", f"/projects/{project_id}/nodes/stop")
        return result is not None
    
    # Node Management
    
    def get_nodes(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all nodes in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List[Dict]: List of nodes
        """
        result = self._make_request("GET", f"/projects/{project_id}/nodes")
        return result or []
    
    def create_node(self, project_id: str, name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Create a new node in a project using either a template or node type.
        
        Args:
            project_id: Project ID
            name: Node name
            **kwargs: Additional parameters which can include:
                - template_id: ID of the template to use
                - node_type: Type of node (for built-in types)
                - x: X position (default 0)
                - y: Y position (default 0)
            
        Returns:
            Dict or None: Node information or None on failure
        """
        # Set default values
        x = kwargs.get('x', 0)
        y = kwargs.get('y', 0)
        compute_id = kwargs.get('compute_id', 'local')
        
        # Base node data
        data = {
            "name": name,
            "compute_id": compute_id,
            "x": x,
            "y": y
        }
        
        # If template_id is provided, use it
        if 'template_id' in kwargs:
            data['template_id'] = kwargs['template_id']
        # Otherwise use node_type if provided
        elif 'node_type' in kwargs:
            data['node_type'] = kwargs['node_type']
            
            # Add specific properties based on node type
            if kwargs['node_type'] == "vpcs":
                data["properties"] = {"base_script_file": "vpcs_base_config.txt"}
            elif kwargs['node_type'] == "open_vswitch_switch":
                data["properties"] = {"controller_mode": "standalone"}
        else:
            self.logger.error("Either template_id or node_type must be provided")
            return None
            
        # Add any additional properties from kwargs
        if 'properties' in kwargs:
            data['properties'] = kwargs['properties']
        
        return self._make_request("POST", f"/projects/{project_id}/nodes", data=data)
    
    def get_node(self, project_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node information.
        
        Args:
            project_id: Project ID
            node_id: Node ID
            
        Returns:
            Dict or None: Node information or None on failure
        """
        return self._make_request("GET", f"/projects/{project_id}/nodes/{node_id}")
    
    def delete_node(self, project_id: str, node_id: str) -> bool:
        """
        Delete a node.
        
        Args:
            project_id: Project ID
            node_id: Node ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("DELETE", f"/projects/{project_id}/nodes/{node_id}")
        return result is not None
    
    def start_node(self, project_id: str, node_id: str) -> bool:
        """
        Start a node.
        
        Args:
            project_id: Project ID
            node_id: Node ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("POST", f"/projects/{project_id}/nodes/{node_id}/start")
        return result is not None
    
    def stop_node(self, project_id: str, node_id: str) -> bool:
        """
        Stop a node.
        
        Args:
            project_id: Project ID
            node_id: Node ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("POST", f"/projects/{project_id}/nodes/{node_id}/stop")
        return result is not None
    
    def configure_node(self, project_id: str, node_name: str, properties: Dict[str, Any]) -> bool:
        """
        Configure a node's properties.
        
        Args:
            project_id: Project ID
            node_name: Node name
            properties: Node properties
            
        Returns:
            bool: Success or failure
        """
        # First find the node by name
        nodes = self.get_nodes(project_id)
        node_id = None
        
        for node in nodes:
            if node.get("name") == node_name:
                node_id = node.get("node_id")
                break
        
        if not node_id:
            self.logger.error(f"Node not found: {node_name}")
            return False
        
        # Update node properties
        result = self._make_request("PUT", f"/projects/{project_id}/nodes/{node_id}", 
                                    data={"properties": properties})
        return result is not None
    
    def exec_command(self, project_id: str, node_name: str, command: str) -> Optional[Dict[str, Any]]:
        """
        Execute a command on a node.
        
        Args:
            project_id: Project ID
            node_name: Node name
            command: Command to execute
            
        Returns:
            Dict or None: Command result or None on failure
        """
        # First find the node by name
        nodes = self.get_nodes(project_id)
        node_id = None
        
        for node in nodes:
            if node.get("name") == node_name:
                node_id = node.get("node_id")
                break
        
        if not node_id:
            self.logger.error(f"Node not found: {node_name}")
            return None
        
        # Execute command
        data = {"command": command}
        return self._make_request("POST", f"/projects/{project_id}/nodes/{node_id}/exec", data=data)
    
    # Link Management
    
    def get_links(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all links in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List[Dict]: List of links
        """
        result = self._make_request("GET", f"/projects/{project_id}/links")
        return result or []
    
    def create_link(self, project_id: str, node_a: str, port_a: int, 
                   node_b: str, port_b: int) -> Optional[str]:
        """
        Create a link between two nodes.
        
        Args:
            project_id: Project ID
            node_a: First node name
            port_a: First node port
            node_b: Second node name
            port_b: Second node port
            
        Returns:
            str or None: Link ID or None on failure
        """
        # Find the node IDs by name
        nodes = self.get_nodes(project_id)
        node_a_id = None
        node_b_id = None
        
        for node in nodes:
            if node.get("name") == node_a:
                node_a_id = node.get("node_id")
            elif node.get("name") == node_b:
                node_b_id = node.get("node_id")
        
        if not node_a_id or not node_b_id:
            self.logger.error(f"Nodes not found: {node_a}, {node_b}")
            return None
        
        # Get available ports
        node_a_ports = self._get_node_ports(project_id, node_a_id)
        node_b_ports = self._get_node_ports(project_id, node_b_id)
        
        # Find the specific ports by port number
        port_a_id = None
        for port in node_a_ports:
            if port.get("port_number") == port_a:
                port_a_id = port.get("adapter_number")
                break
        
        port_b_id = None
        for port in node_b_ports:
            if port.get("port_number") == port_b:
                port_b_id = port.get("adapter_number")
                break
        
        if port_a_id is None or port_b_id is None:
            self.logger.error(f"Ports not found: {port_a}, {port_b}")
            return None
        
        # Create the link
        data = {
            "nodes": [
                {
                    "node_id": node_a_id,
                    "adapter_number": port_a_id,
                    "port_number": port_a
                },
                {
                    "node_id": node_b_id,
                    "adapter_number": port_b_id,
                    "port_number": port_b
                }
            ]
        }
        
        result = self._make_request("POST", f"/projects/{project_id}/links", data=data)
        
        if result:
            return result.get("link_id")
        
        return None
    
    def _get_node_ports(self, project_id: str, node_id: str) -> List[Dict[str, Any]]:
        """
        Get available ports for a node.
        
        Args:
            project_id: Project ID
            node_id: Node ID
            
        Returns:
            List[Dict]: List of ports
        """
        result = self._make_request("GET", f"/projects/{project_id}/nodes/{node_id}/ports")
        return result or []
    
    def get_link(self, project_id: str, link_id: str) -> Optional[Dict[str, Any]]:
        """
        Get link information.
        
        Args:
            project_id: Project ID
            link_id: Link ID
            
        Returns:
            Dict or None: Link information or None on failure
        """
        return self._make_request("GET", f"/projects/{project_id}/links/{link_id}")
    
    def delete_link(self, project_id: str, link_id: str) -> bool:
        """
        Delete a link.
        
        Args:
            project_id: Project ID
            link_id: Link ID
            
        Returns:
            bool: Success or failure
        """
        result = self._make_request("DELETE", f"/projects/{project_id}/links/{link_id}")
        return result is not None
    
    def configure_link(self, project_id: str, link_id: str, 
                       params: Dict[str, Any]) -> bool:
        """
        Configure link parameters.
        
        Args:
            project_id: Project ID
            link_id: Link ID
            params: Link parameters (bandwidth, latency, packet_loss)
            
        Returns:
            bool: Success or failure
        """
        # Create the link filters
        filters = []
        
        if "bandwidth" in params:
            filters.append({
                "type": "bandwidth",
                "value": params["bandwidth"]
            })
        
        if "latency" in params:
            filters.append({
                "type": "latency",
                "value": params["latency"]
            })
        
        if "packet_loss" in params:
            filters.append({
                "type": "packet_loss",
                "value": params["packet_loss"]
            })
        
        if not filters:
            return True  # Nothing to configure
        
        data = {"filters": filters}
        result = self._make_request("PUT", f"/projects/{project_id}/links/{link_id}", data=data)
        return result is not None 