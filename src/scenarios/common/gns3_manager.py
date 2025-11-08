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
GNS3 Manager

This module provides a GNS3Manager class for interacting with a GNS3 server,
creating projects, deploying nodes, and managing network configurations.
"""

import os
import time
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Union

try:
    import gns3fy
except ImportError:
    raise ImportError("gns3fy is required. Install it with: pip install gns3fy")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GNS3Manager:
    """
    A manager class for interacting with a GNS3 server.
    
    This class provides methods for creating projects, deploying nodes,
    setting up network topologies, and managing the GNS3 environment.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 3080):
        """
        Initialize a GNS3Manager instance.
        
        Args:
            host: GNS3 server hostname or IP
            port: GNS3 server API port
        """
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.server = None
        self.project = None
        self._connect()
        
    def _connect(self) -> None:
        """
        Connect to the GNS3 server.
        
        Raises:
            ConnectionError: If connection to GNS3 server fails
        """
        try:
            logger.info(f"Connecting to GNS3 server at {self.server_url}")
            self.server = gns3fy.Gns3Connector(self.server_url)
            
            # Check connection by getting version
            version = self.server.get_version()
            logger.info(f"Connected to GNS3 server (version: {version.get('version', 'unknown')})")
        except Exception as e:
            logger.error(f"Failed to connect to GNS3 server: {e}")
            raise ConnectionError(f"Could not connect to GNS3 server: {e}")
            
    def create_project(self, name: str) -> str:
        """
        Create a new project or get an existing project with the given name.
        
        Args:
            name: Project name
            
        Returns:
            str: Project ID
            
        Raises:
            RuntimeError: If project creation fails
        """
        try:
            # Check if project already exists
            projects = self.server.get_projects()
            for project in projects:
                if project["name"] == name:
                    logger.info(f"Project '{name}' already exists with ID: {project['project_id']}")
                    self.project = gns3fy.Project(name=name, connector=self.server)
                    self.project.get()
                    return project["project_id"]
                    
            # Create new project
            logger.info(f"Creating new project: {name}")
            project = gns3fy.Project(name=name, connector=self.server)
            project.create()
            logger.info(f"Created project '{name}' with ID: {project.project_id}")
            self.project = project
            return project.project_id
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise RuntimeError(f"Failed to create project: {e}")
            
    def open_project(self, project_id: str) -> None:
        """
        Open an existing project by ID.
        
        Args:
            project_id: The GNS3 project ID
            
        Raises:
            RuntimeError: If opening project fails
        """
        try:
            logger.info(f"Opening project with ID: {project_id}")
            projects = self.server.get_projects()
            for project in projects:
                if project["project_id"] == project_id:
                    self.project = gns3fy.Project(project_id=project_id, connector=self.server)
                    self.project.get()
                    logger.info(f"Opened project: {self.project.name}")
                    return
                    
            logger.error(f"Project with ID {project_id} not found")
            raise RuntimeError(f"Project with ID {project_id} not found")
            
        except Exception as e:
            logger.error(f"Failed to open project: {e}")
            raise RuntimeError(f"Failed to open project: {e}")
            
    def get_template_id(self, template_name: str) -> Optional[str]:
        """
        Get the ID of a template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Optional[str]: Template ID if found, None otherwise
        """
        try:
            templates = self.server.get_templates()
            for template in templates:
                if template["name"] == template_name:
                    return template["template_id"]
                    
            logger.warning(f"Template '{template_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting template ID: {e}")
            return None
            
    def create_node(self, 
                   name: str, 
                   template_name: str, 
                   x: int = 0, 
                   y: int = 0, 
                   compute_id: str = "local") -> Optional[Dict[str, Any]]:
        """
        Create a node in the current project.
        
        Args:
            name: Node name
            template_name: Template name to use for the node
            x: X position in the topology
            y: Y position in the topology
            compute_id: Compute ID (default: "local")
            
        Returns:
            Optional[Dict[str, Any]]: Node information if successful, None otherwise
            
        Raises:
            RuntimeError: If node creation fails
        """
        if self.project is None:
            logger.error("No project is open. Call create_project() or open_project() first.")
            raise RuntimeError("No project is open")
            
        template_id = self.get_template_id(template_name)
        if template_id is None:
            raise RuntimeError(f"Template '{template_name}' not found")
            
        try:
            logger.info(f"Creating node '{name}' using template '{template_name}'")
            node = self.project.create_node(
                name=name, 
                template_id=template_id, 
                x=x, 
                y=y, 
                compute_id=compute_id
            )
            logger.info(f"Created node '{name}' with ID: {node.node_id}")
            return {
                "node_id": node.node_id,
                "name": node.name,
                "template_id": template_id,
                "template_name": template_name
            }
            
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            raise RuntimeError(f"Failed to create node: {e}")
            
    def get_node(self, node_name: str) -> Optional[gns3fy.Node]:
        """
        Get a node by name.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Optional[gns3fy.Node]: Node object if found, None otherwise
        """
        if self.project is None:
            logger.error("No project is open")
            return None
            
        try:
            # Update project nodes
            self.project.get()
            for node in self.project.nodes:
                if node.name == node_name:
                    return node
                    
            logger.warning(f"Node '{node_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting node: {e}")
            return None
            
    def start_node(self, node_name: str) -> bool:
        """
        Start a node by name.
        
        Args:
            node_name: Name of the node
            
        Returns:
            bool: True if successful, False otherwise
        """
        node = self.get_node(node_name)
        if node is None:
            logger.error(f"Cannot start node '{node_name}': node not found")
            return False
            
        try:
            logger.info(f"Starting node '{node_name}'")
            node.start()
            logger.info(f"Node '{node_name}' started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start node '{node_name}': {e}")
            return False
            
    def stop_node(self, node_name: str) -> bool:
        """
        Stop a node by name.
        
        Args:
            node_name: Name of the node
            
        Returns:
            bool: True if successful, False otherwise
        """
        node = self.get_node(node_name)
        if node is None:
            logger.error(f"Cannot stop node '{node_name}': node not found")
            return False
            
        try:
            logger.info(f"Stopping node '{node_name}'")
            node.stop()
            logger.info(f"Node '{node_name}' stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop node '{node_name}': {e}")
            return False
            
    def delete_node(self, node_name: str) -> bool:
        """
        Delete a node by name.
        
        Args:
            node_name: Name of the node
            
        Returns:
            bool: True if successful, False otherwise
        """
        node = self.get_node(node_name)
        if node is None:
            logger.warning(f"Cannot delete node '{node_name}': node not found")
            return False
            
        try:
            logger.info(f"Deleting node '{node_name}'")
            node.delete()
            logger.info(f"Node '{node_name}' deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete node '{node_name}': {e}")
            return False
            
    def create_link(self, 
                   node1_name: str, 
                   port1: Union[int, str], 
                   node2_name: str, 
                   port2: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Create a link between two nodes.
        
        Args:
            node1_name: Name of the first node
            port1: Port number or name on the first node
            node2_name: Name of the second node
            port2: Port number or name on the second node
            
        Returns:
            Optional[Dict[str, Any]]: Link information if successful, None otherwise
        """
        if self.project is None:
            logger.error("No project is open")
            return None
            
        node1 = self.get_node(node1_name)
        node2 = self.get_node(node2_name)
        
        if node1 is None:
            logger.error(f"Node '{node1_name}' not found")
            return None
            
        if node2 is None:
            logger.error(f"Node '{node2_name}' not found")
            return None
            
        # Get port objects from nodes
        node1_port = None
        node2_port = None
        
        # Update node information to get ports
        node1.get()
        node2.get()
        
        # Find port by number or name
        for port in node1.ports:
            if (isinstance(port1, int) and port.port_number == port1) or (isinstance(port1, str) and port.name == port1):
                node1_port = port
                break
                
        for port in node2.ports:
            if (isinstance(port2, int) and port.port_number == port2) or (isinstance(port2, str) and port.name == port2):
                node2_port = port
                break
                
        if node1_port is None:
            logger.error(f"Port '{port1}' not found on node '{node1_name}'")
            return None
            
        if node2_port is None:
            logger.error(f"Port '{port2}' not found on node '{node2_name}'")
            return None
            
        try:
            logger.info(f"Creating link between '{node1_name}:{node1_port.name}' and '{node2_name}:{node2_port.name}'")
            link = self.project.create_link(
                node1.node_id, node1_port.adapter_number, node1_port.port_number,
                node2.node_id, node2_port.adapter_number, node2_port.port_number
            )
            logger.info(f"Created link with ID: {link.link_id}")
            return {
                "link_id": link.link_id,
                "node1": node1_name,
                "port1": node1_port.name,
                "node2": node2_name,
                "port2": node2_port.name
            }
            
        except Exception as e:
            logger.error(f"Failed to create link: {e}")
            return None
            
    def start_all_nodes(self) -> bool:
        """
        Start all nodes in the current project.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.project is None:
            logger.error("No project is open")
            return False
            
        try:
            logger.info("Starting all nodes")
            self.project.start_all_nodes()
            logger.info("All nodes started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start all nodes: {e}")
            return False
            
    def stop_all_nodes(self) -> bool:
        """
        Stop all nodes in the current project.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.project is None:
            logger.error("No project is open")
            return False
            
        try:
            logger.info("Stopping all nodes")
            self.project.stop_all_nodes()
            logger.info("All nodes stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop all nodes: {e}")
            return False
            
    def wait_for_node_status(self, node_name: str, status: str, timeout: int = 60) -> bool:
        """
        Wait for a node to reach a specific status.
        
        Args:
            node_name: Name of the node
            status: Status to wait for (e.g., "started", "stopped")
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if node reached the status, False if timed out
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            node = self.get_node(node_name)
            if node is None:
                logger.error(f"Node '{node_name}' not found")
                return False
                
            if node.status == status:
                logger.info(f"Node '{node_name}' reached status '{status}'")
                return True
                
            logger.debug(f"Waiting for node '{node_name}' to reach status '{status}', current status: {node.status}")
            time.sleep(1)
            
        logger.error(f"Timeout waiting for node '{node_name}' to reach status '{status}'")
        return False
        
    def get_node_console(self, node_name: str) -> Optional[Dict[str, Any]]:
        """
        Get console information for a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Optional[Dict[str, Any]]: Console information if successful, None otherwise
        """
        node = self.get_node(node_name)
        if node is None:
            logger.error(f"Node '{node_name}' not found")
            return None
            
        try:
            node.get()
            return {
                "console_type": node.console_type,
                "console_host": self.host,
                "console_port": node.console
            }
            
        except Exception as e:
            logger.error(f"Failed to get console information for node '{node_name}': {e}")
            return None
            
    def export_project_config(self, output_file: str) -> bool:
        """
        Export the current project configuration to a file.
        
        Args:
            output_file: Path to the output file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.project is None:
            logger.error("No project is open")
            return False
            
        try:
            # Update project information
            self.project.get()
            
            # Get all nodes and links
            nodes = []
            for node in self.project.nodes:
                node_info = {
                    "node_id": node.node_id,
                    "name": node.name,
                    "node_type": node.node_type,
                    "status": node.status,
                    "console_type": node.console_type,
                    "console_port": node.console,
                    "x": node.x,
                    "y": node.y
                }
                nodes.append(node_info)
                
            links = []
            for link in self.project.links:
                link_info = {
                    "link_id": link.link_id,
                    "nodes": [
                        {
                            "node_id": link.nodes[0]["node_id"],
                            "adapter_number": link.nodes[0]["adapter_number"],
                            "port_number": link.nodes[0]["port_number"]
                        },
                        {
                            "node_id": link.nodes[1]["node_id"],
                            "adapter_number": link.nodes[1]["adapter_number"],
                            "port_number": link.nodes[1]["port_number"]
                        }
                    ]
                }
                links.append(link_info)
                
            # Create project configuration
            config = {
                "project": {
                    "project_id": self.project.project_id,
                    "name": self.project.name,
                    "status": self.project.status
                },
                "nodes": nodes,
                "links": links
            }
            
            # Write to file
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            logger.info(f"Project configuration exported to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export project configuration: {e}")
            return False
            
    def delete_project(self) -> bool:
        """
        Delete the current project.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.project is None:
            logger.error("No project is open")
            return False
            
        try:
            project_name = self.project.name
            logger.info(f"Deleting project '{project_name}'")
            self.project.delete()
            logger.info(f"Project '{project_name}' deleted")
            self.project = None
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False 