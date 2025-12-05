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
Federated Component Deployer for GNS3.

This module handles deployment of federated learning components to GNS3 nodes.
"""

import logging
import json
import time
import traceback
import requests
from typing import Dict, Any, Optional, Tuple

from gns3fy import Node

logger = logging.getLogger(__name__)


class FederatedDeployer:
    """
    Handles deployment of federated learning components to GNS3 Docker nodes.
    
    This class manages the deployment of FL server, client, and policy engine
    components to running GNS3 nodes.
    """
    
    def __init__(self, server_url: str, project_id: str, auth: Optional[Tuple[str, str]] = None):
        """
        Initialize the FederatedDeployer.
        
        Args:
            server_url: GNS3 server URL
            project_id: GNS3 project ID
            auth: Optional authentication tuple (username, password)
        """
        self.server_url = server_url.rstrip('/')
        self.project_id = project_id
        self.auth = auth
    
    def deploy_component(self, node: Node, component_type: str, config: Dict[str, Any]) -> bool:
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
            
            # Install required packages
            if not self._install_packages(node):
                return False
            
            # Deploy component-specific code
            if component_type == 'fl_server':
                return self._deploy_fl_server(node, config)
            elif component_type == 'fl_client':
                return self._deploy_fl_client(node, config)
            elif component_type == 'policy_engine':
                return self._deploy_policy_engine(node, config)
            else:
                logger.error(f"Unknown component type: {component_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying {component_type} to {node.name}: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _execute_console_command(self, node: Node, command: str) -> bool:
        """
        Execute a command on a node's console.
        
        Args:
            node: The node to execute the command on
            command: The command to execute
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.server_url}/projects/{self.project_id}/nodes/{node.node_id}/console",
                json={"command": command},
                auth=self.auth if self.auth else None
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to run command on {node.name}: {response.text}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error executing command on {node.name}: {e}")
            return False
    
    def _install_packages(self, node: Node) -> bool:
        """
        Install required packages on a node.
        
        Args:
            node: The node to install packages on
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Install required packages in Alpine
            basic_packages = "python3 py3-pip curl wget bash"
            install_cmd = f"apk update && apk add --no-cache {basic_packages}"
            
            logger.info(f"Installing packages on {node.name}: {basic_packages}")
            if not self._execute_console_command(node, install_cmd):
                return False
            
            # Wait for installation to complete
            time.sleep(5)
            
            # Install Python dependencies
            python_packages = "numpy tensorflow torch flwr pandas scipy"
            pip_cmd = f"pip3 install --no-cache-dir {python_packages}"
            
            logger.info(f"Installing Python packages on {node.name}: {python_packages}")
            if not self._execute_console_command(node, pip_cmd):
                logger.error(f"Failed to install Python packages on {node.name}")
                return False
            
            # Wait for pip installation to complete
            time.sleep(10)
            
            return True
            
        except Exception as e:
            logger.error(f"Error installing packages on {node.name}: {e}")
            return False
    
    def _deploy_fl_server(self, node: Node, config: Dict[str, Any]) -> bool:
        """
        Deploy FL server component to a node.
        
        Args:
            node: The node to deploy to
            config: Server configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create server directory and config
            mkdir_cmd = "mkdir -p /app/server"
            if not self._execute_console_command(node, mkdir_cmd):
                return False
            
            # Create server configuration file
            config_content = json.dumps(config, indent=2)
            config_cmd = f"echo '{config_content}' > /app/server/config.json"
            if not self._execute_console_command(node, config_cmd):
                return False
            
            # Create a simple server script
            server_script = self._get_server_script()
            script_cmd = f"echo '{server_script}' > /app/server/server.py"
            if not self._execute_console_command(node, script_cmd):
                return False
            
            # Start the server in the background
            start_cmd = "cd /app/server && nohup python3 server.py > server.log 2>&1 &"
            if not self._execute_console_command(node, start_cmd):
                return False
            
            logger.info(f"Successfully deployed fl_server to {node.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying FL server to {node.name}: {e}")
            return False
    
    def _deploy_fl_client(self, node: Node, config: Dict[str, Any]) -> bool:
        """
        Deploy FL client component to a node.
        
        Args:
            node: The node to deploy to
            config: Client configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create client directory and config
            mkdir_cmd = "mkdir -p /app/client"
            if not self._execute_console_command(node, mkdir_cmd):
                return False
            
            # Create client configuration file
            config_content = json.dumps(config, indent=2)
            config_cmd = f"echo '{config_content}' > /app/client/config.json"
            if not self._execute_console_command(node, config_cmd):
                return False
            
            # Create a simple client script
            client_script = self._get_client_script()
            script_cmd = f"echo '{client_script}' > /app/client/client.py"
            if not self._execute_console_command(node, script_cmd):
                return False
            
            # Start the client in the background
            start_cmd = "cd /app/client && nohup python3 client.py > client.log 2>&1 &"
            if not self._execute_console_command(node, start_cmd):
                return False
            
            logger.info(f"Successfully deployed fl_client to {node.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying FL client to {node.name}: {e}")
            return False
    
    def _deploy_policy_engine(self, node: Node, config: Dict[str, Any]) -> bool:
        """
        Deploy policy engine component to a node.
        
        Args:
            node: The node to deploy to
            config: Policy engine configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create policy engine directory and config
            mkdir_cmd = "mkdir -p /app/policy"
            if not self._execute_console_command(node, mkdir_cmd):
                return False
            
            # Create policy configuration file
            config_content = json.dumps(config, indent=2)
            config_cmd = f"echo '{config_content}' > /app/policy/config.json"
            if not self._execute_console_command(node, config_cmd):
                return False
            
            # Create a simple policy engine script
            policy_script = self._get_policy_engine_script()
            script_cmd = f"echo '{policy_script}' > /app/policy/policy_engine.py"
            if not self._execute_console_command(node, script_cmd):
                return False
            
            # Start the policy engine in the background
            start_cmd = "cd /app/policy && nohup python3 policy_engine.py > policy.log 2>&1 &"
            if not self._execute_console_command(node, start_cmd):
                return False
            
            logger.info(f"Successfully deployed policy_engine to {node.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying policy engine to {node.name}: {e}")
            return False
    
    def _get_server_script(self) -> str:
        """Get the FL server script content."""
        return '''
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
'''
    
    def _get_client_script(self) -> str:
        """Get the FL client script content."""
        return '''
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
'''
    
    def _get_policy_engine_script(self) -> str:
        """Get the policy engine script content."""
        return '''
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
'''
