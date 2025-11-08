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
GNS3 Topology Creator for Network Simulations.

This module provides tools for creating GNS3 network topologies for federated learning experiments.
"""

import logging
import math
import time
import os
import sys
import json
import uuid
import traceback
import random
import requests
from typing import Dict, List, Tuple, Optional, Any, Union
import platform

from src.networking.gns3.gns3_api import GNS3API
from gns3fy import Gns3Connector, Project, Node, Link
import requests

logger = logging.getLogger(__name__)

class GNS3TopologyCreator:
    """Utility for creating network topologies in GNS3."""
    
    def __init__(self, server_url: str, project_name: str, username: str = None, password: str = None, auth: Optional[Tuple[str, str]] = None):
        """
        Initialize GNS3 topology creator.
        
        Args:
            server_url: GNS3 server URL
            project_name: Project name
            username: GNS3 username (optional)
            password: GNS3 password (optional)
            auth: Authentication tuple (optional)
        """
        self.server_url = server_url.rstrip('/')
        self.project_name = project_name
        self.username = username
        self.password = password
        self.auth = auth if auth else (username, password) if username and password else None
        self.project = None
        self.connector = None
        self.templates = []  # Store available templates here
        
        # Normalize server URL to ensure it works
        if not self.server_url.endswith('/v2') and not self.server_url.endswith('/v2/'):
            # Check if we already have a URL that ends with /v2
            if not '/v2/' in self.server_url:
                logger.info(f"Appending /v2 to server URL: {self.server_url}")
                self.base_url = f"{self.server_url.rstrip('/')}/v2"
            else:
                self.base_url = self.server_url
        else:
            self.base_url = self.server_url
        
        # Initialize GNS3 API connector
        self.api = GNS3API(self.base_url, username=self.username, password=self.password)
        
        if not self.api:
            raise RuntimeError("Failed to initialize GNS3 API")
        
        logger.info("Successfully initialized GNS3 API")
        
        # Create GNS3 connector for compatibility with gns3fy
        logger.info(f"Creating GNS3Connector with URL: {self.base_url}")
        connector_params = {"url": self.base_url}
        if self.username and self.password:
            connector_params["user"] = self.username
            connector_params["cred"] = self.password
        self.connector = Gns3Connector(**connector_params)
        logger.info("Successfully created GNS3Connector")
        
        # Get list of projects - try multiple API paths 
        logger.info("Getting list of projects from GNS3 server...")
        success = False
        projects = []
        
        # Try with /v2 first
        success, projects = self.api.get_projects()
        
        # If that fails, try without /v2 (in case our URL already had it or the server doesn't use it)
        if not success:
            logger.warning(f"Failed to get projects with path {self.base_url} - trying alternate URL formats")
            
            # Try direct server
            alt_url = server_url.rstrip('/v2').rstrip('/')
            alt_api = GNS3API(alt_url, username=self.username, password=self.password)
            success, projects = alt_api.get_projects()
            
            if success:
                # Update server URL to the working one
                logger.info(f"Successfully connected using URL: {alt_url}")
                self.api = alt_api
                self.base_url = alt_url
                
                # Update connector
                self.connector = Gns3Connector(url=alt_url, user=self.username, cred=self.password)
        
        # If still not working, try some common paths
        if not success:
            # Try with /api
            alt_url = f"{server_url.rstrip('/v2').rstrip('/')}/api"
            alt_api = GNS3API(alt_url, username=self.username, password=self.password)
            success, projects = alt_api.get_projects()
            
            if success:
                # Update server URL to the working one
                logger.info(f"Successfully connected using URL: {alt_url}")
                self.api = alt_api
                self.base_url = alt_url
                
                # Update connector
                self.connector = Gns3Connector(url=alt_url, user=self.username, cred=self.password)
        
        # If all path formats failed, try an HTTP request
        if not success:
            try:
                # Test direct GET to see what works
                base_paths = [
                    server_url.rstrip('/'),
                    f"{server_url.rstrip('/v2').rstrip('/')}/v2",
                    f"{server_url.rstrip('/v2').rstrip('/')}/api",
                    f"{server_url.rstrip('/v2').rstrip('/')}"
                ]
                
                for test_url in base_paths:
                    try:
                        logger.info(f"Testing URL: {test_url}/projects")
                        response = requests.get(f"{test_url}/projects", auth=self.auth, timeout=5)
                        if response.status_code == 200:
                            # Found a working URL!
                            logger.info(f"Found working URL: {test_url}")
                            self.base_url = test_url
                            self.api = GNS3API(test_url, username=self.username, password=self.password)
                            self.connector = Gns3Connector(url=test_url, user=self.username, cred=self.password)
                            success = True
                            projects = response.json()
                            break
                    except Exception as e:
                        logger.warning(f"Failed to test URL {test_url}: {e}")
                
                if not success:
                    logger.error("Could not find a working URL for the GNS3 API")
                    raise RuntimeError("Could not connect to GNS3 API")
            except Exception as e:
                logger.error(f"Error testing various API URLs: {e}")
                raise RuntimeError(f"Failed to connect to GNS3 API: {e}")
        
        # Get available templates
        self._get_available_templates()
        
        if success:
            # Check if project already exists
            logger.info(f"Found {len(projects)} projects on GNS3 server")
            project_exists = False
            for project in projects:
                if project.get('name') == project_name:
                    # Project exists - use it
                    project_exists = True
                    project_id = project.get('project_id')
                    logger.info(f"Using existing project with ID: {project_id}")
                    self.project = Project(
                        name=project_name,
                        project_id=project_id,
                        connector=self.connector
                    )
                    
                    # Open project if not already open
                    try:
                        # Get project status from API
                        success, project_status = self.api.get_project(project_id)
                        if success and project_status.get('status') != 'opened':
                            # Open the project
                            success, _ = self.api.open_project(project_id)
                            if success:
                                logger.info(f"Successfully opened existing project {project_name}")
                            else:
                                logger.warning(f"Failed to open existing project {project_name}")
                        else:
                            logger.info(f"Project {project_name} is already open")
                    except Exception as e:
                        logger.warning(f"Error opening existing project: {e}")
            
            if not project_exists:
                # Create new project
                logger.info(f"Creating new GNS3 project '{project_name}'")
                success, response = self.api.create_project(project_name)
                
                if success:
                    project_id = response.get('project_id')
                    logger.info(f"Using project with ID: {project_id}")
                    self.project = Project(
                        name=project_name,
                        project_id=project_id,
                        connector=self.connector
                    )
                else:
                    logger.error(f"Failed to create project: {response}")
                    raise RuntimeError(f"Failed to create GNS3 project: {response}")
            
            # Initialize project
            try:
                logger.info("Getting project details...")
                self.project.get()
                logger.info("Successfully initialized project")
            except Exception as e:
                logger.error(f"Failed to initialize project: {e}")
                raise RuntimeError(f"Failed to initialize GNS3 project: {e}")
        else:
            logger.error("Failed to get projects from GNS3 server")
            raise RuntimeError("Failed to connect to GNS3 server")
            
    def _get_available_templates(self):
        """Get available templates from GNS3 server.
        
        Returns:
            List of available templates
            
        Raises:
            RuntimeError: If templates cannot be retrieved
        """
        try:
            logger.info("Getting available templates from GNS3 server")
            
            # Get templates from API
            success, templates = self.api.get_templates()
            if not success:
                error_msg = f"Failed to get templates: {templates}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            if not templates:
                # Try direct API call as a fallback for template retrieval only
                logger.warning("No templates returned from API call, trying direct request")
                try:
                    response = requests.get(f"{self.server_url}/templates", auth=self.auth)
                    if response.status_code == 200:
                        templates = response.json()
                        logger.info(f"Retrieved {len(templates)} templates via direct API call")
                        self.templates = templates
                        return templates
                    else:
                        error_msg = f"Direct template request failed with status {response.status_code}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                except Exception as e:
                    error_msg = f"Error in direct API call for templates: {e}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            
            self.templates = templates
            
            # Log available template types
            template_types = {}
            for t in templates:
                t_type = t.get('template_type', 'unknown')
                if t_type not in template_types:
                    template_types[t_type] = []
                template_types[t_type].append(t.get('name', 'unnamed'))
            
            for t_type, names in template_types.items():
                logger.info(f"Found {len(names)} templates of type {t_type}: {names}")
            
            return templates
            
        except Exception as e:
            error_msg = f"Error getting templates: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise RuntimeError(error_msg)

    def create_node(self, node_type: str, name: str, properties: Dict = None, x: int = 0, y: int = 0) -> Optional[Node]:
        """
        Create a node in the GNS3 network.
        
        Args:
            node_type: Type of node ('client', 'server', 'switch', 'router')
            name: Name of the node
            properties: Additional properties
            x: X position
            y: Y position
            
        Returns:
            Node object if successful, None otherwise
        """
        try:
            # Ensure project is open before creating a node
            if not self.ensure_project_is_open():
                logger.error("Cannot create node - project is not open")
                return None
            
            node_type = node_type.lower()
            logger.info(f"Creating {node_type} node '{name}'")
            
            # For switches, try to create Ethernet switch
            if node_type == 'switch':
                try:
                    logger.info(f"Creating Ethernet switch {name} using direct API method")
                    
                    # Create Ethernet switch data
                    data = {
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
                    
                    # Make direct API request
                    url = f"{self.server_url}/projects/{self.project.project_id}/nodes"
                    headers = {"Content-Type": "application/json"}
                    if self.auth:
                        response = requests.post(url, headers=headers, json=data, auth=self.auth)
                    else:
                        response = requests.post(url, headers=headers, json=data)
                    
                    if response.status_code in [200, 201]:
                        node_data = response.json()
                        node_id = node_data.get('node_id')
                        logger.info(f"Successfully created switch node {name} with ID {node_id}")
                        
                        # Create a Node object with the connector
                        node = Node(
                            name=name,
                            node_id=node_id,
                            node_type="ethernet_switch",
                            project_id=self.project.project_id,
                            connector=self.connector
                        )
                        
                        # Get the full node data
                        node.get()
                        return node
                    else:
                        logger.warning(f"Failed to create switch using direct API: {response.status_code} - {response.text}")
                        # Continue to the fallback
                except Exception as e:
                    logger.warning(f"Error creating Ethernet switch with direct API: {e}")
                    # Continue to the fallback
            
            # For client and server nodes, try to create VPCS nodes (which work well with cloud switches)
            if node_type in ['client', 'server']:
                try:
                    logger.info(f"Creating {node_type} node {name} as VPCS")
                    
                    # Create VPCS node directly using REST API
                    url = f"{self.server_url}/projects/{self.project.project_id}/nodes"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        'name': name,
                        'node_type': 'vpcs',
                        'compute_id': 'local',
                        'x': x,
                        'y': y
                    }
                    
                    if self.auth:
                        response = requests.post(url, headers=headers, json=data, auth=self.auth, timeout=10)
                    else:
                        response = requests.post(url, headers=headers, json=data, timeout=10)
                    
                    if response.status_code in [200, 201]:
                        node_data = response.json()
                        node_id = node_data.get('node_id')
                        logger.info(f"Successfully created {node_type} node {name} as VPCS with ID {node_id}")
                        
                        # Create a Node object
                        node = Node(
                            name=name,
                            node_id=node_id,
                            node_type="vpcs",
                            project_id=self.project.project_id,
                            connector=self.connector
                        )
                        
                        # Get the full node data
                        node.get()
                        return node
                    else:
                        logger.error(f"Failed to create VPCS node: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.error(f"Error creating VPCS node: {e}")
            
            # If all else fails, try a cloud node
            try:
                logger.info(f"Creating {node_type} node {name} as Cloud (fallback)")
                
                # Create cloud node directly using REST API
                url = f"{self.server_url}/projects/{self.project.project_id}/nodes"
                headers = {"Content-Type": "application/json"}
                data = {
                    'name': name,
                    'node_type': 'cloud',
                    'compute_id': 'local',
                    'x': x,
                    'y': y
                }
                
                if self.auth:
                    response = requests.post(url, headers=headers, json=data, auth=self.auth, timeout=10)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=10)
                
                if response.status_code in [200, 201]:
                    node_data = response.json()
                    node_id = node_data.get('node_id')
                    logger.info(f"Successfully created {node_type} node {name} as Cloud with ID {node_id}")
                    
                    # Create a Node object
                    node = Node(
                        name=name,
                        node_id=node_id,
                        node_type="cloud",
                        project_id=self.project.project_id,
                        connector=self.connector
                    )
                    
                    # Get the full node data
                    node.get()
                    return node
                else:
                    logger.error(f"Failed to create Cloud node: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error creating Cloud node: {e}")
            
            # If we get here, all creation attempts failed
            logger.error(f"Failed to create {node_type} node {name} after trying all methods")
            return None
        except Exception as e:
            logger.error(f"Error creating node: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def ensure_project_is_open(self) -> bool:
        """
        Ensure the project is open and accessible.
        
        Returns:
            bool: True if project is open and accessible, False otherwise
        """
        if not self.project:
            logger.error("No project object available")
            return False

        logger.info(f"Ensuring project {self.project_name} is open and accessible")
        
        max_retries = 2
        for attempt in range(max_retries):
            # Method 1: Check directly with API if the project is open
            try:
                success, response = self.api.get_project(self.project.project_id)
                if success:
                    status = response.get('status', 'unknown')
                    logger.info(f"Project status (API): {status}")
                    if status == 'opened':
                        logger.info(f"Project {self.project_name} is already open")
                        # Verify accessibility by requesting nodes
                        try:
                            self.project.nodes
                            logger.info(f"Project {self.project_name} is accessible")
                            return True
                        except Exception as e:
                            logger.warning(f"Project is open but not accessible: {str(e)}")
                else:
                    logger.warning(f"Failed to check project status via API: {response}")
            except Exception as e:
                logger.warning(f"Error checking project status via API: {str(e)}")
            
            # Method 2: Try using gns3fy to refresh project and check status
            try:
                self.project.get()
                status = getattr(self.project, 'status', 'unknown')
                logger.info(f"Project status (gns3fy): {status}")
                if status == 'opened':
                    logger.info(f"Project {self.project_name} is confirmed open via gns3fy")
                    return True
                elif status == 'closed':
                    logger.info(f"Project {self.project_name} is closed, attempting to open it...")
                    try:
                        self.project.open()
                        logger.info(f"Successfully opened project {self.project_name}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to open project using gns3fy: {str(e)}")
            except Exception as e:
                logger.warning(f"Error using gns3fy to check project: {str(e)}")
            
            # Method 3: Try a direct API call to open the project
            try:
                open_url = f"{self.server_url}/v2/projects/{self.project.project_id}/open"
                headers = {"Content-Type": "application/json"}
                response = requests.post(open_url, headers=headers, auth=self.auth)
                
                if response.status_code == 200:
                    logger.info(f"Successfully opened project {self.project_name} via direct API call")
                    # Verify accessibility
                    try:
                        time.sleep(2)  # Give it time to fully open
                        self.project.get()
                        self.project.nodes  # Try to access nodes
                        logger.info(f"Project {self.project_name} is accessible")
                        return True
                    except Exception as e:
                        logger.warning(f"Project opened but not accessible: {str(e)}")
                elif response.status_code == 409:
                    # Conflict, project might be in transition
                    logger.warning(f"Project is in transition (409 conflict), waiting before retry...")
                    time.sleep(5)  # Wait longer for transitional state
                    continue
                else:
                    logger.warning(f"Failed to open project via direct API: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"Error with direct API call to open project: {str(e)}")
            
            # If we're still here after all attempts, sleep before retry
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed to open project, will retry")
            time.sleep(3)
        
        # Last resort: If project cannot be opened after retries, attempt to recreate it
        logger.warning(f"Failed to open project {self.project_name} after {max_retries} attempts")
        logger.info("Attempting to recreate the project as a last resort")
        
        if self.recreate_project(self.project.project_id):
            logger.info("Project successfully recreated")
            return True
        else:
            logger.error("Failed to recreate project")
            return False

    def recreate_project(self, project_id: str) -> bool:
        """
        Recreate the project when there are issues opening it.
        
        Args:
            project_id: The ID of the problem project
            
        Returns:
            bool: True if project was successfully recreated, False otherwise
        """
        logger.info(f"Attempting to recreate project {self.project_name}")
        
        # Try with a new project name if the current one might be corrupted
        new_project_name = f"{self.project_name}_{random.randint(1000, 9999)}"
        
        try:
            # First, try to delete the project
            try:
                delete_url = f"{self.server_url}/v2/projects/{project_id}"
                headers = {"Content-Type": "application/json"}
                
                if self.auth:
                    response = requests.delete(delete_url, headers=headers, auth=self.auth)
                else:
                    response = requests.delete(delete_url, headers=headers)
                    
                if response.status_code in [200, 201, 204]:
                    logger.info(f"Successfully deleted project {self.project_name}")
                else:
                    logger.warning(f"Failed to delete project: {response.status_code} - {response.text}")
                    
                    # Try force delete
                    force_delete_url = f"{self.server_url}/v2/projects/{project_id}?force=true"
                    
                    if self.auth:
                        response = requests.delete(force_delete_url, headers=headers, auth=self.auth)
                    else:
                        response = requests.delete(force_delete_url, headers=headers)
                        
                    if response.status_code in [200, 201, 204]:
                        logger.info(f"Successfully force deleted project {self.project_name}")
                    else:
                        logger.warning(f"Failed to force delete project: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"Error deleting project: {e}")
            
            # If we may have cloud node issues on Windows, try with a new project name
            if platform.system() == 'Windows' and "cloud/nodes" in str(requests.get(f"{self.server_url}/v2/projects/{project_id}", 
                                        headers={"Content-Type": "application/json"}, 
                                        auth=self.auth if self.auth else None).text):
                logger.warning("Detected potential cloud node issue on Windows, trying with a new project name")
                self.project_name = new_project_name
            
            # Create a new project
            try:
                create_url = f"{self.server_url}/v2/projects"
                headers = {"Content-Type": "application/json"}
                data = {
                    "name": self.project_name,
                    "auto_open": True
                }
                
                if self.auth:
                    response = requests.post(create_url, headers=headers, json=data, auth=self.auth)
                else:
                    response = requests.post(create_url, headers=headers, json=data)
                    
                if response.status_code in [200, 201]:
                    project_data = response.json()
                    project_id = project_data.get('project_id')
                    logger.info(f"Successfully created new project {self.project_name} with ID {project_id}")
                    
                    # Update the project object with the new ID
                    self.project.project_id = project_id
                    
                    # Update the connector with the new project ID
                    if self.connector and hasattr(self.connector, 'project_id'):
                        self.connector.project_id = project_id
                    
                    # Make sure it's open
                    try:
                        open_url = f"{self.server_url}/v2/projects/{project_id}/open"
                        if self.auth:
                            open_response = requests.post(open_url, headers=headers, auth=self.auth)
                        else:
                            open_response = requests.post(open_url, headers=headers)
                            
                        if open_response.status_code in [200, 201, 204]:
                            logger.info(f"Successfully opened new project {self.project_name}")
                        else:
                            logger.warning(f"Could not explicitly open project: {open_response.status_code}")
                            # Still return True because the project was created with auto_open=True
                    except Exception as e:
                        logger.warning(f"Error opening new project: {e}")
                        # Still return True because the project was created with auto_open=True
                    
                    return True
                elif response.status_code == 409 and "already exists" in response.text:
                    # Project with this name already exists, try with random name
                    logger.warning(f"Project {self.project_name} already exists, trying with a new name")
                    self.project_name = new_project_name
                    
                    # Try again with new name
                    data["name"] = self.project_name
                    
                    if self.auth:
                        response = requests.post(create_url, headers=headers, json=data, auth=self.auth)
                    else:
                        response = requests.post(create_url, headers=headers, json=data)
                        
                    if response.status_code in [200, 201]:
                        project_data = response.json()
                        project_id = project_data.get('project_id')
                        logger.info(f"Successfully created new project {self.project_name} with ID {project_id}")
                        
                        # Update the project object with the new ID
                        self.project.project_id = project_id
                        
                        # Update the connector with the new project ID
                        if self.connector and hasattr(self.connector, 'project_id'):
                            self.connector.project_id = project_id
                        
                        return True
                else:
                    logger.error(f"Failed to create new project: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Error creating new project: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error recreating project: {e}")
            return False

    def _create_cloud_node(self, name: str, x: int = 0, y: int = 0) -> Optional[Node]:
        """
        Create a Cloud node directly using the GNS3 API.
        
        Args:
            name: Name of the cloud node
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Node object if successful, None otherwise
        """
        try:
            logger.info(f"Creating Cloud node {name}")
            
            # Create cloud data
            data = {
                'name': name,
                'node_type': 'cloud',
                'compute_id': 'local',
                'symbol': ':/symbols/cloud.svg',
                'x': x,
                'y': y
            }
            
            # Make direct API request
            url = f"{self.server_url}/projects/{self.project.project_id}/nodes"
            headers = {"Content-Type": "application/json"}
            
            if self.auth:
                response = requests.post(url, headers=headers, json=data, auth=self.auth)
            else:
                response = requests.post(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                node_data = response.json()
                node_id = node_data.get('node_id')
                logger.info(f"Successfully created Cloud node {name} with ID {node_id}")
                
                # Create Node object
                node = Node(
                    name=name,
                    node_id=node_id,
                    node_type="cloud",
                    project_id=self.project.project_id,
                    connector=self.connector
                )
                
                # Get the full node data
                node.get()
                return node
            else:
                logger.error(f"Failed to create Cloud node: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating Cloud node {name}: {e}")
            logger.error(traceback.format_exc())
            return None

    def create_star_topology(self, n: int, **kwargs) -> Dict[str, Any]:
        """
        Create a star topology with n client nodes connected to a central cloud.
        
        Args:
            n (int): Number of client nodes to create
            **kwargs: Additional arguments for node creation
            
        Returns:
            Dict[str, Any]: Dictionary with created nodes and links
        """
        logger.info(f"Creating star topology with {n} nodes using Docker containers")
        
        # Ensure project is open
        if not self.ensure_project_is_open():
            err_msg = "Cannot create topology - project is not open"
            logger.error(err_msg)
            raise Exception(err_msg)
        
        # Find Alpine Linux Docker template
        alpine_template = None
        
        # First, search for exact match on Alpine Linux
        for template in self.templates:
            if template.get('name') == 'Alpine Linux' and template.get('template_type') == 'docker':
                alpine_template = template
                logger.info(f"Found Alpine Linux Docker template: {template.get('name')}")
                break
        
        # If not found, try case-insensitive partial matches
        if not alpine_template:
            for template in self.templates:
                template_name = template.get('name', '').lower()
                if ('alpine' in template_name) and template.get('template_type') == 'docker':
                    alpine_template = template
                    logger.info(f"Found Alpine Linux Docker template with partial match: {template.get('name')}")
                    break
        
        # No more fallbacks - if Alpine Linux template isn't found, fail immediately
        if not alpine_template:
            logger.error("Alpine Linux Docker template not found in GNS3")
            # Print available templates for debugging
            available_templates = [t.get('name') for t in self.templates]
            logger.error(f"Available templates: {available_templates}")
            
            raise RuntimeError("Alpine Linux Docker template not found. Please add Alpine Linux Docker template to GNS3 first.")
        
        # Create central switch
        switch_name = kwargs.get('switch_name', f'switch_{random.randint(1000, 9999)}')
        switch_x = kwargs.get('switch_x', 0)
        switch_y = kwargs.get('switch_y', 0)
        
        logger.info(f"Creating central switch: {switch_name}")
        central_switch = self.create_node(
            node_type='switch',
            name=switch_name,
            x=switch_x,
            y=switch_y
        )
        
        if not central_switch:
            err_msg = "Failed to create central switch"
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        
        # Create server node
        server_name = kwargs.get('server_name', f'fl_server_{random.randint(1000, 9999)}')
        server_x = switch_x
        server_y = switch_y - 100
        
        logger.info(f"Creating server node: {server_name}")
        server_node = self._create_docker_node(
            name=server_name,
            template_id=alpine_template['template_id'],
            x=server_x,
            y=server_y,
            is_server=True
        )
        
        if not server_node:
            err_msg = "Failed to create server node"
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        
        # Create client nodes in a circle around the central hub
        client_nodes = []
        radius = 200
        
        for i in range(n):
            angle = 2 * math.pi * i / n
            x = int(switch_x + radius * math.cos(angle))
            y = int(switch_y + radius * math.sin(angle))
            
            client_name = kwargs.get('client_name_format', 'fl_client_{}').format(i)
            
            logger.info(f"Creating client node: {client_name}")
            client_node = self._create_docker_node(
                name=client_name,
                template_id=alpine_template['template_id'],
                x=x,
                y=y,
                is_server=False
            )
            
            if client_node:
                client_nodes.append(client_node)
            else:
                logger.error(f"Failed to create client node {client_name}")
                # Continue with other clients
        
        if not client_nodes:
            err_msg = "Failed to create any client nodes"
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        
        # Create links between central switch and nodes
        links = []
        failed_links = []
        
        # Link server to switch
        logger.info(f"Creating link between {switch_name} and {server_name}")
        server_link = self.create_link(central_switch, server_node)
        if server_link:
            links.append(server_link)
        else:
            failed_links.append((switch_name, server_name))
        
        # Link clients to switch
        for idx, client in enumerate(client_nodes):
            logger.info(f"Creating link between {switch_name} and {client.name}")
            link = self.create_link(central_switch, client)
            if link:
                links.append(link)
            else:
                failed_links.append((switch_name, client.name))
        
        if not links:
            err_msg = "Failed to create any links in star topology"
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        
        # Log partial success if some links failed
        if failed_links:
            logger.warning(f"Failed to create links for: {failed_links}")
        
        logger.info(f"Star topology created with {len(client_nodes)} client nodes and {len(links)} links")
        
        return {
            'central_switch': central_switch,
            'server_node': server_node,
            'client_nodes': client_nodes,
            'links': links,
            'failed_links': failed_links
        }

    def _create_docker_node(self, name: str, template_id: str, x: int = 0, y: int = 0, is_server: bool = False) -> Optional[Node]:
        """
        Create a Docker node in GNS3.
        
        Args:
            name: Name of the node
            template_id: ID of the Docker template to use
            x: X coordinate
            y: Y coordinate
            is_server: Whether this is a server node
            
        Returns:
            Node object if successful, None otherwise
        """
        try:
            logger.info(f"Creating Docker node '{name}' using template {template_id}")
            
            # Prepare node data
            node_data = {
                'name': name,
                'node_type': 'docker',
                'compute_id': 'local',  # Use local compute
                'x': x,
                'y': y,
                'template_id': template_id,
                'properties': {
                    'adapters': 1,
                    'aux': 5000,
                    'console_type': 'telnet',
                    'console_auto_start': True,
                    'start_command': '/bin/sh',
                    'environment': 'PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8',
                    'extra_hosts': '',
                    'extra_volumes': ['/tmp:/tmp']
                }
            }
            
            # Server nodes may need more resources and different configuration
            if is_server:
                node_data['properties'].update({
                    'adapters': 2,
                    'cpus': 2,
                    'memory': 512,
                    'environment': 'PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nROLE=server',
                })
            else:
                # Client node configuration
                node_data['properties'].update({
                    'cpus': 1,
                    'memory': 256,
                    'environment': 'PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nROLE=client',
                })
            
            # Try creating the node directly through the API
            url = f"{self.server_url}/projects/{self.project.project_id}/nodes"
            headers = {"Content-Type": "application/json"}
            
            if self.auth:
                response = requests.post(url, headers=headers, json=node_data, auth=self.auth)
            else:
                response = requests.post(url, headers=headers, json=node_data)
            
            if response.status_code in [200, 201]:
                node_data = response.json()
                node_id = node_data.get('node_id')
                logger.info(f"Successfully created Docker node {name} with ID {node_id}")
                
                # Create Node object
                node = Node(
                    name=name,
                    node_id=node_id,
                    node_type="docker",
                    project_id=self.project.project_id,
                    connector=self.connector
                )
                
                # Get the full node data
                node.get()
                return node
            else:
                logger.error(f"Failed to create Docker node: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating Docker node {name}: {e}")
            logger.error(traceback.format_exc())
            return None

    def create_link(self, node1, node2) -> Optional[Link]:
        """
        Create a link between two nodes in GNS3.
        
        Args:
            node1: First node
            node2: Second node
            
        Returns:
            Created link or None if failed
        """
        logger.info(f"Creating link between '{node1.name}' and '{node2.name}'")
        
        try:
            # Special handling for links with Cloud nodes
            if 'cloud' in node1.node_type.lower() or 'cloud' in node2.node_type.lower():
                # For clouds, we need to ensure we use proper adapter numbers
                # Clouds often have specialized interfaces rather than generic ones
                cloud_node = node1 if 'cloud' in node1.node_type.lower() else node2
                other_node = node2 if cloud_node == node1 else node1
                
                # Ensure the cloud node has the right interface configuration
                cloud_node.get()  # Refresh the node data
                
                # For the cloud node, use the first available ethernet interface
                cloud_port = 0
                if hasattr(cloud_node, 'ports') and cloud_node.ports:
                    for i, port in enumerate(cloud_node.ports):
                        if 'ethernet' in port.get('name', '').lower():
                            cloud_port = i
                            logger.info(f"Using cloud port {cloud_port} ({port.get('name')})")
                            break
                
                # Try different ports on both nodes to find a working pair
                other_port = 0  # Default port on the other node
                
                # Create link data with proper port configuration
                link_data = {
                    "nodes": [
                        {
                            "node_id": cloud_node.node_id,
                            "adapter_number": cloud_port,
                            "port_number": 0
                        },
                        {
                            "node_id": other_node.node_id,
                            "adapter_number": other_port,
                            "port_number": 0
                        }
                    ]
                }
                
                # Try to create the link
                url = f"{self.server_url}/projects/{self.project.project_id}/links"
                headers = {"Content-Type": "application/json"}
                
                if self.auth:
                    response = requests.post(url, headers=headers, json=link_data, auth=self.auth)
                else:
                    response = requests.post(url, headers=headers, json=link_data)
                
                if response.status_code in [200, 201]:
                    link_data = response.json()
                    link_id = link_data.get('link_id')
                    logger.info(f"Successfully created link with ID {link_id}")
                    
                    # Create a Link object
                    link = Link(
                        project_id=self.project.project_id,
                        link_id=link_id,
                        connector=self.connector
                    )
                    
                    # Get complete link data
                    link.get()
                    return link
                else:
                    logger.warning(f"Failed to create link: {response.status_code} - {response.text}")
                    # Continue to try the alternative method
            
            # Standard handling for regular nodes (like ethernet switches)
            # Find available ports on both nodes
            node1_port = self._find_available_port(node1)
            node2_port = self._find_available_port(node2)
            
            if node1_port == -1 or node2_port == -1:
                logger.error(f"No available ports on node1 ({node1.name}) or node2 ({node2.name})")
                return None
            
            # Create the link with the available ports
            return self._create_direct_link(node1, node2, node1_port, node2_port)
            
        except Exception as e:
            logger.error(f"Error creating link between {node1.name} and {node2.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def _create_direct_link(self, node1: Node, node2: Node, node1_port: int = 0, node2_port: int = 0) -> Optional[Link]:
        """
        Create a link directly using the API, with specified ports to avoid conflicts.
        
        Args:
            node1: First node to connect
            node2: Second node to connect
            node1_port: Port/adapter number on first node
            node2_port: Port/adapter number on second node
            
        Returns:
            Link: Created link or None if failed
        """
        try:
            logger.info(f"Creating direct link between {node1.name} and {node2.name} on ports {node1_port} and {node2_port}")
            
            # Prepare link data
            link_data = {
                "nodes": [
                    {
                        "node_id": node1.node_id,
                        "adapter_number": node1_port,
                        "port_number": 0
                    },
                    {
                        "node_id": node2.node_id,
                        "adapter_number": node2_port,
                        "port_number": 0
                    }
                ]
            }
            
            # Make the API request
            url = f"{self.server_url}/projects/{self.project.project_id}/links"
            headers = {"Content-Type": "application/json"}
            
            if self.auth:
                response = requests.post(url, headers=headers, json=link_data, auth=self.auth)
            else:
                response = requests.post(url, headers=headers, json=link_data)
            
            if response.status_code in [200, 201]:
                link_data = response.json()
                link_id = link_data.get('link_id')
                logger.info(f"Successfully created link with ID {link_id}")
                
                # Create a Link object
                link = Link(
                    project_id=self.project.project_id,
                    link_id=link_id,
                    connector=self.connector
                )
                
                return link
            else:
                logger.error(f"Failed to create link: {response.status_code} - {response.text}")
                
                # If port is already used, try to provide more specific error
                if response.status_code == 409 and "Port is already used" in response.text:
                    logger.error(f"Port conflict: node1({node1_port}) or node2({node2_port}) port already in use")
                
                return None
        except Exception as e:
            logger.error(f"Error creating link: {e}")
            return None

    def _find_available_port(self, node, max_ports=8) -> int:
        """
        Find an available port on a node.
        
        Args:
            node: Node to find port for
            max_ports: Maximum number of ports to check
            
        Returns:
            int: Available port number or -1 if none found
        """
        try:
            # Make sure we have current data for the node
            node.get()
            
            # For Ethernet switch, specific logic
            if 'ethernet_switch' in node.node_type.lower():
                # Get existing links
                links = node.links if hasattr(node, 'links') else []
                used_ports = set()
                for link in links:
                    for port in link.get('nodes', []):
                        if port.get('node_id') == node.node_id:
                            used_ports.add(port.get('adapter_number'))
                
                # Find first available port
                for i in range(max_ports):
                    if i not in used_ports:
                        return i
                        
                logger.warning(f"No available ports on Ethernet switch {node.name}")
                return -1
            
            # For cloud nodes - they often have multiple adapters
            if 'cloud' in node.node_type.lower():
                # Get port information
                ports = node.ports if hasattr(node, 'ports') else []
                links = node.links if hasattr(node, 'links') else []
                
                # Find used ports
                used_ports = set()
                for link in links:
                    for port in link.get('nodes', []):
                        if port.get('node_id') == node.node_id:
                            used_ports.add(port.get('adapter_number'))
                
                # Find first available ethernet port
                for i, port in enumerate(ports):
                    if 'ethernet' in port.get('name', '').lower() and i not in used_ports:
                        return i
                
                # If no ethernet port found, try any available port
                for i in range(max_ports):
                    if i not in used_ports and i < len(ports):
                        return i
                
                logger.warning(f"No available ports on cloud node {node.name}")
                return -1
            
            # For regular nodes - typically use port 0
            # Check if it's already used
            links = node.links if hasattr(node, 'links') else []
            for link in links:
                for port in link.get('nodes', []):
                    if port.get('node_id') == node.node_id and port.get('adapter_number') == 0:
                        logger.warning(f"Port 0 on {node.name} is already used")
                        # Try other ports
                        for i in range(1, max_ports):
                            port_used = False
                            for link in links:
                                for port in link.get('nodes', []):
                                    if port.get('node_id') == node.node_id and port.get('adapter_number') == i:
                                        port_used = True
                                        break
                            if not port_used:
                                return i
                        return -1
            
            # Port 0 is not used
            return 0
            
        except Exception as e:
            logger.error(f"Error finding available port for {node.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0  # Default to port 0 on error

    def deploy_federated_component(self, node: Node, component_type: str, config: Dict[str, Any]) -> bool:
        """
        Deploy a federated learning component to a Docker node.
        
        Args:
            node: The GNS3 node to deploy to
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            config: Configuration for the component
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deploying {component_type} to node {node.name}")
            
            # Ensure the node is started
            node_status = node.status
            if node_status != 'started':
                logger.info(f"Starting node {node.name} (current status: {node_status})")
                node.start()
                time.sleep(2)  # Wait for node to start
            
            # Get node console connection details
            console_url = node.console_url
            if not console_url:
                logger.error(f"Failed to get console URL for node {node.name}")
                return False
            
            # Install required packages in Alpine
            basic_packages = "python3 py3-pip curl wget bash"
            install_cmd = f"apk update && apk add --no-cache {basic_packages}"
            
            try:
                # Execute command to install packages
                logger.info(f"Installing packages on {node.name}: {basic_packages}")
                response = requests.post(
                    f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                    json={"command": install_cmd},
                    auth=self.auth if self.auth else None
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to run command on {node.name}: {response.text}")
                    return False
                
                # Wait for installation to complete
                time.sleep(5)
                
                # Install Python dependencies
                python_packages = "numpy tensorflow torch flwr pandas scipy"
                pip_cmd = f"pip3 install --no-cache-dir {python_packages}"
                
                logger.info(f"Installing Python packages on {node.name}: {python_packages}")
                response = requests.post(
                    f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                    json={"command": pip_cmd},
                    auth=self.auth if self.auth else None
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to install Python packages on {node.name}: {response.text}")
                    return False
                
                # Wait for pip installation to complete
                time.sleep(10)
                
                # Deploy component-specific code
                if component_type == 'fl_server':
                    # Create server directory and config
                    mkdir_cmd = "mkdir -p /app/server"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": mkdir_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Create server configuration file
                    config_content = json.dumps(config, indent=2)
                    config_cmd = f"echo '{config_content}' > /app/server/config.json"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": config_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Create a simple server script
                    server_script = """
import json
import os
import sys
import time

print("Starting Federated Learning Server...")
print("Loading configuration...")

# Load configuration
with open('/app/server/config.json', 'r') as f:
    config = json.load(f)

print(f"Configuration loaded: {config}")
print("Server is ready to accept connections")

# Keep the server running
while True:
    print("Server is running...")
    time.sleep(60)
"""
                    script_cmd = f"echo '{server_script}' > /app/server/server.py"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": script_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Start the server in the background
                    start_cmd = "cd /app/server && nohup python3 server.py > server.log 2>&1 &"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": start_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                elif component_type == 'fl_client':
                    # Create client directory and config
                    mkdir_cmd = "mkdir -p /app/client"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": mkdir_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Create client configuration file
                    config_content = json.dumps(config, indent=2)
                    config_cmd = f"echo '{config_content}' > /app/client/config.json"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": config_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Create a simple client script
                    client_script = """
import json
import os
import sys
import time

print("Starting Federated Learning Client...")
print("Loading configuration...")

# Load configuration
with open('/app/client/config.json', 'r') as f:
    config = json.load(f)

print(f"Configuration loaded: {config}")
print(f"Connecting to server at {config.get('server_host')}:{config.get('server_port')}")

# Keep the client running
while True:
    print("Client is running...")
    time.sleep(30)
"""
                    script_cmd = f"echo '{client_script}' > /app/client/client.py"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": script_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Start the client in the background
                    start_cmd = "cd /app/client && nohup python3 client.py > client.log 2>&1 &"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": start_cmd},
                        auth=self.auth if self.auth else None
                    )
                
                elif component_type == 'policy_engine':
                    # Create policy engine directory and config
                    mkdir_cmd = "mkdir -p /app/policy"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": mkdir_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Create policy configuration file
                    config_content = json.dumps(config, indent=2)
                    config_cmd = f"echo '{config_content}' > /app/policy/config.json"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": config_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Create a simple policy engine script
                    policy_script = """
import json
import os
import sys
import time

print("Starting Policy Engine...")
print("Loading configuration...")

# Load configuration
with open('/app/policy/config.json', 'r') as f:
    config = json.load(f)

print(f"Configuration loaded: {config}")
print(f"Policy Engine is running on {config.get('host')}:{config.get('port')}")

# Keep the policy engine running
while True:
    print("Policy Engine is running...")
    time.sleep(60)
"""
                    script_cmd = f"echo '{policy_script}' > /app/policy/policy_engine.py"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": script_cmd},
                        auth=self.auth if self.auth else None
                    )
                    
                    # Start the policy engine in the background
                    start_cmd = "cd /app/policy && nohup python3 policy_engine.py > policy.log 2>&1 &"
                    response = requests.post(
                        f"{self.server_url}/projects/{self.project.project_id}/nodes/{node.node_id}/console",
                        json={"command": start_cmd},
                        auth=self.auth if self.auth else None
                    )
                
                else:
                    logger.error(f"Unknown component type: {component_type}")
                    return False
                
                logger.info(f"Successfully deployed {component_type} to {node.name}")
                return True
                
            except Exception as e:
                logger.error(f"Error executing command on {node.name}: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error deploying {component_type} to {node.name}: {e}")
            logger.error(traceback.format_exc())
            return False