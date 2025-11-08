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
Deployment Manager

This module provides a class for managing the deployment of federated learning
components in a GNS3 environment. It handles the deployment of servers, clients,
and policy engines for various federated learning scenarios.
"""

import logging
import time
import subprocess
import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentManager:
    """
    A class to manage the deployment of federated learning components in a GNS3 environment.
    
    This class handles the setup and configuration of servers, clients, and policy engines
    for various federated learning scenarios.
    """
    
    def __init__(self, config: Dict[str, Any], gns3_manager):
        """
        Initialize the deployment manager.
        
        Args:
            config: Dictionary containing deployment configuration
            gns3_manager: Instance of GNS3Manager for managing GNS3 resources
        """
        self.config = config
        self.gns3_manager = gns3_manager
        
        # Get scenario settings
        self.scenario_config = config.get('scenario', {})
        self.server_config = config.get('server', {})
        self.client_config = config.get('clients', {})
        self.policy_engine_config = config.get('policy_engine', {})
        
        # Initialize component tracking
        self.deployed_components = {
            'server': None,
            'clients': [],
            'policy_engine': None
        }
        
    def setup_gns3_environment(self) -> bool:
        """
        Set up the GNS3 environment for deployment.
        
        This includes creating/connecting to the GNS3 project and verifying
        that the required templates are available.
        
        Returns:
            bool: True if setup is successful, False otherwise
        """
        try:
            # Check connection to GNS3 server
            if not self.gns3_manager.check_connection():
                logger.error("Cannot connect to GNS3 server")
                return False
                
            # Create or load project
            if not self.gns3_manager.get_or_create_project():
                logger.error("Failed to create or load GNS3 project")
                return False
                
            # Verify required templates
            required_templates = self._get_required_templates()
            for template_name in required_templates:
                if not self.gns3_manager.find_template(template_name):
                    logger.error(f"Required template '{template_name}' not found in GNS3 server")
                    return False
                    
            logger.info("GNS3 environment setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up GNS3 environment: {e}")
            return False
            
    def _get_required_templates(self) -> List[str]:
        """
        Get a list of required templates based on the configuration.
        
        Returns:
            List of template names required for the deployment
        """
        templates = []
        
        # Add network templates
        network_templates = self.config.get('network', {}).get('templates', {})
        
        # Add server template if configured
        if self.server_config.get('enabled', True):
            server_template = network_templates.get('server', 'federated-learning-server')
            templates.append(server_template)
            
        # Add client template if configured
        if self.client_config.get('count', 0) > 0:
            client_template = network_templates.get('client', 'federated-learning-client')
            templates.append(client_template)
            
        # Add policy engine template if configured
        if self.policy_engine_config.get('enabled', False):
            policy_template = network_templates.get('policy_engine', 'federated-learning-policy')
            templates.append(policy_template)
            
        # Add switch template if using a switch
        if self.config.get('network', {}).get('create_switch', True):
            switch_template = network_templates.get('switch', 'Ethernet switch')
            templates.append(switch_template)
            
        return templates
        
    def create_network_topology(self) -> bool:
        """
        Create the network topology for the federated learning scenario.
        
        This includes creating nodes and links based on the configuration.
        
        Returns:
            bool: True if topology creation is successful, False otherwise
        """
        return self.gns3_manager.create_network_topology()
        
    def deploy_server(self) -> bool:
        """
        Deploy the federated learning server.
        
        Returns:
            bool: True if server deployment is successful, False otherwise
        """
        if not self.server_config.get('enabled', True):
            logger.info("Server deployment is disabled")
            return True
            
        try:
            # Start the server node
            logger.info("Starting server node")
            if not self.gns3_manager.start_node('server'):
                logger.error("Failed to start server node")
                return False
                
            # Wait for the server to start
            if not self.gns3_manager.wait_for_node_status('server', 'started', timeout=60):
                logger.error("Server node failed to start within the timeout")
                return False
                
            # Track the deployed server
            self.deployed_components['server'] = 'server'
            
            logger.info("Server deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying server: {e}")
            return False
            
    def deploy_clients(self) -> bool:
        """
        Deploy federated learning clients.
        
        Returns:
            bool: True if client deployment is successful, False otherwise
        """
        client_count = self.client_config.get('count', 0)
        if client_count <= 0:
            logger.info("No clients to deploy")
            return True
            
        try:
            # Start client nodes
            for i in range(1, client_count + 1):
                client_name = f'client{i}'
                logger.info(f"Starting client node {client_name}")
                
                if not self.gns3_manager.start_node(client_name):
                    logger.error(f"Failed to start client node {client_name}")
                    return False
                    
                # Wait for the client to start
                if not self.gns3_manager.wait_for_node_status(client_name, 'started', timeout=60):
                    logger.error(f"Client node {client_name} failed to start within the timeout")
                    return False
                    
                # Track the deployed client
                self.deployed_components['clients'].append(client_name)
                
            logger.info(f"Deployed {client_count} clients successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying clients: {e}")
            return False
            
    def deploy_policy_engine(self) -> bool:
        """
        Deploy policy engine if enabled.
        
        Returns:
            bool: True if policy engine deployment is successful or not needed, False otherwise
        """
        if not self.policy_engine_config.get('enabled', False):
            logger.info("Policy engine deployment is disabled")
            return True
            
        try:
            # Start policy engine node
            logger.info("Starting policy engine node")
            if not self.gns3_manager.start_node('policy_engine'):
                logger.error("Failed to start policy engine node")
                return False
                
            # Wait for the policy engine to start
            if not self.gns3_manager.wait_for_node_status('policy_engine', 'started', timeout=60):
                logger.error("Policy engine node failed to start within the timeout")
                return False
                
            # Track the deployed policy engine
            self.deployed_components['policy_engine'] = 'policy_engine'
            
            logger.info("Policy engine deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying policy engine: {e}")
            return False
            
    def configure_components(self) -> bool:
        """
        Configure all deployed components.
        
        This includes setting up the server, clients, and policy engine
        for the federated learning scenario.
        
        Returns:
            bool: True if configuration is successful, False otherwise
        """
        try:
            # Configure server if deployed
            if self.deployed_components['server']:
                if not self._configure_server():
                    logger.error("Failed to configure server")
                    return False
                    
            # Configure clients if deployed
            if self.deployed_components['clients']:
                if not self._configure_clients():
                    logger.error("Failed to configure clients")
                    return False
                    
            # Configure policy engine if deployed
            if self.deployed_components['policy_engine']:
                if not self._configure_policy_engine():
                    logger.error("Failed to configure policy engine")
                    return False
                    
            logger.info("All components configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring components: {e}")
            return False
            
    def _configure_server(self) -> bool:
        """
        Configure the federated learning server.
        
        Returns:
            bool: True if server configuration is successful, False otherwise
        """
        # This method should be overridden by specific scenario implementations
        logger.info("Server configuration not implemented in base class")
        return True
        
    def _configure_clients(self) -> bool:
        """
        Configure the federated learning clients.
        
        Returns:
            bool: True if client configuration is successful, False otherwise
        """
        # This method should be overridden by specific scenario implementations
        logger.info("Client configuration not implemented in base class")
        return True
        
    def _configure_policy_engine(self) -> bool:
        """
        Configure the policy engine.
        
        Returns:
            bool: True if policy engine configuration is successful, False otherwise
        """
        # This method should be overridden by specific scenario implementations
        logger.info("Policy engine configuration not implemented in base class")
        return True
        
    def deploy_all(self) -> bool:
        """
        Deploy all components for the federated learning scenario.
        
        This includes setting up the GNS3 environment, creating the network topology,
        deploying the server, clients, and policy engine, and configuring them.
        
        Returns:
            bool: True if deployment is successful, False otherwise
        """
        try:
            # Setup GNS3 environment
            if not self.setup_gns3_environment():
                logger.error("Failed to setup GNS3 environment")
                return False
                
            # Create network topology
            if not self.create_network_topology():
                logger.error("Failed to create network topology")
                return False
                
            # Deploy server
            if not self.deploy_server():
                logger.error("Failed to deploy server")
                return False
                
            # Deploy clients
            if not self.deploy_clients():
                logger.error("Failed to deploy clients")
                return False
                
            # Deploy policy engine
            if not self.deploy_policy_engine():
                logger.error("Failed to deploy policy engine")
                return False
                
            # Configure components
            if not self.configure_components():
                logger.error("Failed to configure components")
                return False
                
            logger.info("All components deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying components: {e}")
            return False
            
    def stop_all(self) -> bool:
        """
        Stop all deployed components.
        
        Returns:
            bool: True if all components are stopped successfully, False otherwise
        """
        return self.gns3_manager.stop_all_nodes()
        
    def cleanup(self) -> bool:
        """
        Clean up all resources used by the deployment.
        
        Returns:
            bool: True if cleanup is successful, False otherwise
        """
        try:
            # Stop all nodes
            if not self.stop_all():
                logger.warning("Failed to stop all nodes during cleanup")
                
            # Delete the project if configured
            if self.config.get('cleanup', {}).get('delete_project', False):
                if not self.gns3_manager.delete_project():
                    logger.warning("Failed to delete project during cleanup")
                    
            logger.info("Cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False
            
    def get_console_urls(self) -> Dict[str, str]:
        """
        Get the console URLs for all deployed components.
        
        Returns:
            Dictionary mapping component names to console URLs
        """
        console_urls = {}
        
        # Get server console URL
        if self.deployed_components['server']:
            server_url = self.gns3_manager.get_console_url(self.deployed_components['server'])
            if server_url:
                console_urls['server'] = server_url
                
        # Get client console URLs
        for i, client in enumerate(self.deployed_components['clients']):
            client_url = self.gns3_manager.get_console_url(client)
            if client_url:
                console_urls[f'client{i+1}'] = client_url
                
        # Get policy engine console URL
        if self.deployed_components['policy_engine']:
            policy_url = self.gns3_manager.get_console_url(self.deployed_components['policy_engine'])
            if policy_url:
                console_urls['policy_engine'] = policy_url
                
        return console_urls
        
    def save_deployment_info(self, output_file: str) -> bool:
        """
        Save deployment information to a file.
        
        Args:
            output_file: Path to the output file
            
        Returns:
            bool: True if information is saved successfully, False otherwise
        """
        try:
            deployment_info = {
                'scenario': self.scenario_config.get('name', 'unknown'),
                'components': {
                    'server': self.deployed_components['server'],
                    'clients': self.deployed_components['clients'],
                    'policy_engine': self.deployed_components['policy_engine']
                },
                'console_urls': self.get_console_urls(),
                'topology': {
                    'project_name': self.gns3_manager.project_name,
                    'project_id': self.gns3_manager.project.project_id if self.gns3_manager.project else None
                }
            }
            
            logger.info(f"Saving deployment information to {output_file}")
            with open(output_file, 'w') as f:
                json.dump(deployment_info, f, indent=2)
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving deployment information: {e}")
            return False 