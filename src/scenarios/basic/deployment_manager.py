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
Deployment Manager for Basic Scenario.

This module handles deployment of federated learning components 
for the basic scenario in GNS3.
"""

import os
import sys
import json
import logging
import time
import uuid
import tempfile
import traceback
import copy
from typing import Dict, List, Any, Optional

# Import topology manager
from src.utils.topology_manager import TopologyManager

# Import link manager for link creation and port management
from src.scenarios.basic.link_manager import LinkManager

# Import node creation mixin
from src.scenarios.basic.node_manager import NodeCreationMixin

logger = logging.getLogger(__name__)

class DeploymentManager(NodeCreationMixin):
    """
    Manages deployment of federated learning components for basic scenario.
    
    This class handles:
    - Creating the necessary nodes in GNS3
    - Configuring network connections
    - Deploying components with appropriate configuration
    - Running federated learning workloads
    - Collecting results
    """
    
    def __init__(self, gns3_manager, config, topology_manager=None):
        """
        Initialize the deployment manager.
        
        Args:
            gns3_manager: The GNS3 manager instance
            config: Configuration dictionary
            topology_manager: The topology manager instance (optional)
        """
        self.gns3_manager = gns3_manager
        self.config = config or {}
        
        # Process topology_manager from params
        self.topology_manager = topology_manager
        
        if topology_manager:
            logger.info("Using provided TopologyManager instance")
            self.topology = topology_manager.topology_config
            
            if self.topology:
                nodes = self.topology.get("nodes", [])
                links = self.topology.get("links", [])
                logger.info(f"Topology initialized with {len(nodes)} nodes and {len(links)} links")
            else:
                logger.warning("No topology available in TopologyManager")
                self._init_topology_manager()  # Fall back to loading from config
        else:
            logger.info("No TopologyManager provided, initializing from config")
            self._init_topology_manager()
            
        # Track node IDs for linking
        self.node_ids = {}
        # For backward compatibility - both dicts store the same information
        self.created_nodes_info = self.node_ids
        
        # Legacy attributes maintained for compatibility
        self.node_map = {}
        self.nodes = self.node_ids  # Map of node_name -> node_id
        self.link_map = {}  # Map of link_name -> link_id
        self.fl_results = {}
        self.node_ports = {}  # Map of node_name -> port
        
        # Set up auto-fix flag for topology issues
        self.auto_fix_conflicts = config.get('auto_fix_conflicts', True)
        
        # Initialize link manager (will be fully configured after nodes are created)
        self.link_manager = None
        
        # Check if GNS3 project is available
        if gns3_manager and gns3_manager.project_id:
            logger.info(f"Using existing GNS3 project ID: {gns3_manager.project_id}")
        
        if self.topology_manager:
            # If we have an initialized TopologyManager, use its node_map
            self.node_map = self.topology_manager.node_map
        
        # Make sure we have a valid topology before proceeding
        if not hasattr(self, 'topology') or not self.topology:
            logger.error("Failed to initialize topology. Deployment will likely fail.")
        else:
            logger.info(f"Topology initialized with {len(self.topology.get('nodes', []))} nodes and {len(self.topology.get('links', []))} links")
        
        logger.info("DeploymentManager initialized")
        
    def _init_topology_manager(self):
        """Initialize the topology manager based on configuration."""
        # Check if there's a topology file specified in the config
        topology_file = self.config.get('network', {}).get('topology_file')
        
        if topology_file and os.path.exists(topology_file):
            logger.info(f"Using topology file from config: {topology_file}")
            self.topology_manager = TopologyManager(topology_file=topology_file)
        else:
            # Check for scenario-specific topology
            scenario_type = self.config.get('scenario_type', 'basic')
            default_topology_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "topology",
                f"{scenario_type}_topology.json"
            )
            
            if os.path.exists(default_topology_path):
                logger.info(f"Using scenario-specific topology: {default_topology_path}")
                self.topology_manager = TopologyManager(topology_file=default_topology_path)
            else:
                # Fall back to default topology
                logger.info("Using default topology")
                self.topology_manager = TopologyManager.load_default_topology()
        
        # Validate topology
        if self.topology_manager.topology_config:
            is_valid, errors = self.topology_manager.validate_topology()
            if not is_valid:
                logger.warning(f"Topology validation failed with {len(errors)} errors:")
                for error in errors:
                    logger.warning(f"  - {error}")
            else:
                logger.info("Topology validation successful")
        else:
            logger.warning("No topology configuration loaded")
    
    def _debug_log_templates(self) -> None:
        """Debug method to log all available templates."""
        if not self.gns3_manager or not self.gns3_manager.api:
            logger.error("Cannot log templates: GNS3 manager not initialized")
            return
            
        try:
            success, templates = self.gns3_manager.api._make_request('GET', 'templates')
            
            if not success:
                logger.error("Failed to get templates for debugging")
                return
                
            logger.info(f"Available templates ({len(templates)}):")
            for template in templates:
                template_name = template.get('name')
                template_id = template.get('template_id')
                template_type = template.get('template_type')
                image = template.get('image', 'N/A')
                console_type = template.get('console_type', 'N/A')
                
                logger.info(f"  - {template_name} (ID: {template_id}, Type: {template_type}, Image: {image}, Console: {console_type})")
        
        except Exception as e:
            logger.error(f"Error logging templates: {e}")
    
    def _wait_for_node_to_start(self, node_id: str, max_attempts: int = 10, interval: int = 2) -> bool:
        """
        Wait for a node to reach 'started' status.
        
        Args:
            node_id: ID of the node to wait for
            max_attempts: Maximum number of attempts to check status
            interval: Interval between attempts in seconds
            
        Returns:
            bool: True if node started successfully, False otherwise
        """
        if not self.gns3_manager or not self.gns3_manager.api or not node_id:
            return False
            
        for attempt in range(max_attempts):
            try:
                success, node_info = self.gns3_manager.api._make_request(
                    'GET', 
                    f'projects/{self.gns3_manager.project_id}/nodes/{node_id}'
                )
                
                if success and node_info:
                    status = node_info.get('status')
                    
                    if status == 'started':
                        logger.info(f"Node {node_id} is running (attempt {attempt+1}/{max_attempts})")
                        return True
                    elif status == 'stopped':
                        # Try to start the node
                        logger.info(f"Starting node {node_id} (attempt {attempt+1}/{max_attempts})")
                        self.gns3_manager.api._make_request(
                            'POST',
                            f'projects/{self.gns3_manager.project_id}/nodes/{node_id}/start'
                        )
                        
                logger.debug(f"Waiting for node {node_id} to start (attempt {attempt+1}/{max_attempts})")
                time.sleep(interval)  # Wait before checking again
                
            except Exception as e:
                logger.error(f"Error waiting for node {node_id} to start: {e}")
                time.sleep(interval)
        
        logger.warning(f"Node {node_id} did not start after {max_attempts} attempts")
        return False
    
    def _execute_on_node(self, node_id: str, command: str) -> (bool, Any):
        """
        Execute a command on a node with proper handling for status and retries.
        
        Args:
            node_id: ID of the node to execute command on
            command: Command to execute
            
        Returns:
            Tuple of (success, response)
        """
        if not self.gns3_manager or not self.gns3_manager.api or not node_id:
            return False, None
            
        # Make sure node is running
        if not self._wait_for_node_to_start(node_id):
            return False, None
            
        # Now execute the command
        try:
            success, response = self.gns3_manager.api._make_request(
                'POST',
                f'projects/{self.gns3_manager.project_id}/nodes/{node_id}/exec',
                json={'command': command}
            )
            
            if success:
                logger.info(f"Successfully executed command on node: {command[:50]}...")
                return True, response
            else:
                logger.error(f"Failed to execute command: {response}")
                return False, response
        
        except Exception as e:
            logger.error(f"Error executing command on node {node_id}: {e}")
            return False, None
    
    def deploy_components(self) -> bool:
        """
        Deploy components according to topology.
        
        Returns:
            bool: True if deployment was successful, False otherwise
        """
        if not self.topology_manager or not self.topology:
            logger.error("Cannot deploy components: Topology not available")
            return False
            
        try:
            # --- Start Change: Ensure clean project state ---
            # Ensure GNS3Manager is initialized and project exists or is created cleanly
            if not self.gns3_manager.project_id:
                project_name = self.topology.get("gns3_configuration", {}).get("project_name", "default_fl_project")
                logger.info(f"Attempting to initialize or create GNS3 project: {project_name}")
                
                # Try to find the project first
                project = self.gns3_manager.find_project_by_name(project_name)
                
                if project:
                    logger.warning(f"Project '{project_name}' already exists (ID: {project['project_id']}). Attempting to clean it up.")
                    # Option 1: Delete existing project (more aggressive, ensures clean slate)
                    success_delete = self.gns3_manager.delete_project(project['project_id'])
                    if success_delete:
                        logger.info(f"Successfully deleted existing project '{project_name}'.")
                        # Create a new project
                        project = self.gns3_manager.create_project(project_name)
                        if not project:
                            logger.error(f"Failed to create new project '{project_name}' after deletion.")
                            return False
                    else:
                        logger.error(f"Failed to delete existing project '{project_name}'. Cannot guarantee clean state.")
                        # If deletion fails, we might still try to use the existing project, but it's risky.
                        # For now, let's exit to be safe.
                        return False 
                        
                    # Option 2: Use existing project but clean its nodes/links (less aggressive)
                    # logger.info(f"Attempting to clean existing project '{project_name}' (ID: {project['project_id']})...")
                    # self.gns3_manager.project_id = project['project_id'] # Set project ID to clean it
                    # self.gns3_manager.cleanup_project_environment(delete_project=False) # Clean nodes/links without deleting project
                    # logger.info(f"Finished cleaning existing project '{project_name}'.")

                else:
                    # Project doesn't exist, create it
                    logger.info(f"Project '{project_name}' not found. Creating a new project.")
                    project = self.gns3_manager.create_project(project_name)
                    if not project:
                        logger.error(f"Failed to create GNS3 project '{project_name}'.")
                        return False
                    logger.info(f"Successfully created new project '{project_name}' with ID: {self.gns3_manager.project_id}")

            else:
                logger.info(f"Using existing GNS3 project ID: {self.gns3_manager.project_id}")
                # Optionally clean the existing project environment here as well if needed
                # self.gns3_manager.cleanup_project_environment(delete_project=False)

            # --- End Change ---

            # Debug info before starting actual deployment steps
            logger.debug(f"Starting deployment with topology: {self.topology} in project {self.gns3_manager.project_id}")
            
            # Step 1: Create all nodes first without starting them
            success_nodes = self._create_nodes()
            if not success_nodes:
                logger.error("Failed to create all required nodes. Deployment cannot continue.")
                return False

            # Step 2: Create links between nodes while they're stopped
            success_links = self._create_links()
            if not success_links:
                logger.error("Failed to create required links. Deployment considered failed.")
                return False
            
            # Step 3: Now start all nodes only after links are established
            # Based on new success criteria, the outcome of _start_nodes() is logged 
            # but does not determine the success of deploy_components itself.
            self._start_nodes() # Attempt to start nodes
            
            # Final step: Wait for all services to initialize
            wait_time = 10  # Increased wait time
            logger.info(f"Waiting {wait_time} seconds for services to initialize after node start attempt...")
            time.sleep(wait_time)
            
            logger.info("Deployment of nodes and links considered successful. Node start was attempted.")
            return True # Deployment successful based on new criteria (nodes and links deployed)
            
        except Exception as e:
            logger.error(f"Error during component deployment: {e}")
            logger.debug(traceback.format_exc())
            return False
            
    # Node creation methods (_create_nodes, _create_switch_nodes, _create_regular_nodes, etc.)
    # are provided via NodeCreationMixin from node_manager.py
    def _create_ethernet_switch(self, node_name, template_id, node_config):
        """
        Create an Ethernet switch with properly configured ports
        """
        # For Ethernet switch, we need to ensure it has enough ports
        # Default to 8 ports, but calculate based on links if possible
        num_ports = 8
        
        # Check if adapters number is explicitly specified in the topology
        if 'adapters' in node_config:
            num_ports = node_config['adapters']
            logger.info(f"Using explicitly configured {num_ports} ports for Ethernet switch '{node_name}'")
        else:
            # Count how many connections this switch has in the links section
            required_adapters = self._calculate_required_adapters()
            if node_name in required_adapters:
                # Add a few extra ports to be safe
                num_ports = max(8, required_adapters[node_name] + 4)
                logger.info(f"Calculated {num_ports} ports needed for Ethernet switch '{node_name}' based on links")
            else:
                logger.info(f"Using default {num_ports} ports for Ethernet switch '{node_name}'")
            
        # Get position from node config
        x = node_config.get('x', 0)
        y = node_config.get('y', 0)
        
        # Get compute_id from config or use default 'local'
        compute_id = node_config.get('compute_id', 'local')
        
        # Prepare switch-specific parameters
        node_params = {
            'name': node_name,
            'compute_id': compute_id,
            'node_type': 'ethernet_switch',
            'properties': {
                'ports_mapping': []
            },
            'x': x,
            'y': y
        }
        
        # Create port mappings for all ports
        for i in range(num_ports):
            port_mapping = {
                'name': f'Ethernet{i}',
                'port_number': i,
                'type': 'access',
                'vlan': 1
            }
            node_params['properties']['ports_mapping'].append(port_mapping)
        
        logger.debug(f"Creating Ethernet switch '{node_name}' with {num_ports} ports and params: {node_params}")
        
        # Create the node using direct API call with all parameters correctly positioned
        success, result = self.gns3_manager.api._make_request(
            'POST',
            f'projects/{self.gns3_manager.project_id}/nodes',
            json=node_params
        )
        
        if not success:
            logger.error(f"Failed to create Ethernet switch {node_name}: {result}")
            return False, {}
            
        return success, result
    
    def _create_links(self) -> bool:
        """
        Create links between nodes according to topology.
        
        Delegates to LinkManager for actual link creation and port management.
        
        Returns:
            bool: True if all links were created successfully, False otherwise
        """
        if not self.topology:
            logger.error("Cannot create links: Topology not available")
            return False
        
        # Initialize or update link manager with current node IDs
        if not self.link_manager:
            self.link_manager = LinkManager(
                gns3_manager=self.gns3_manager,
                project_id=self.gns3_manager.project_id,
                node_ids=self.node_ids,
                auto_fix_conflicts=self.auto_fix_conflicts
            )
        else:
            # Update node_ids in case they've changed
            self.link_manager.node_ids = self.node_ids
        
        # Delegate link creation to LinkManager
        result = self.link_manager.create_links(self.topology)
        
        # Sync link_map back from LinkManager
        self.link_map = self.link_manager.link_map
        
        return result
    
    def _log_node_ports(self, node_id, node_name):
        """
        Log the available ports for a node to help with debugging.
        
        Delegates to LinkManager.
        """
        if self.link_manager:
            self.link_manager.log_node_ports(node_id, node_name)
        else:
            logger.warning("LinkManager not initialized, cannot log node ports")
    
    def _ensure_switch_ports(self, switch_id, min_ports):
        """
        Ensure an Ethernet switch has at least the required number of ports.
        
        Delegates to LinkManager.
        """
        if self.link_manager:
            return self.link_manager.ensure_switch_ports(switch_id, min_ports)
        else:
            logger.warning("LinkManager not initialized, cannot ensure switch ports")
            return False
    
    def _start_nodes(self) -> bool:
        """Start all nodes in a specific order based on dependencies."""
        logger.info("Starting all deployed nodes...")
        
        # Determine correct startup order based on dependencies
        # Usually start infrastructure -> server -> clients
        # We'll use the node types to determine order
        policy_nodes = []
        switch_nodes = []
        controller_nodes = []
        server_nodes = []
        client_nodes = []
        other_nodes = []
        
        # Categorize nodes
        for node_name, node_id in self.node_ids.items():
            if "policy" in node_name.lower():
                policy_nodes.append(node_name)
            elif "switch" in node_name.lower() or "ovs" in node_name.lower() or "openvswitch" in node_name.lower():
                switch_nodes.append(node_name)
            elif "controller" in node_name.lower() or "sdn" in node_name.lower():
                controller_nodes.append(node_name)
            elif "server" in node_name.lower() or "collector" in node_name.lower():
                server_nodes.append(node_name)
            elif "client" in node_name.lower():
                client_nodes.append(node_name)
            else:
                other_nodes.append(node_name)
        
        # Start in order: policy -> controller -> switch -> server -> client -> others
        all_nodes_in_order = policy_nodes + controller_nodes + switch_nodes + server_nodes + client_nodes + other_nodes
        
        # Start each node in order
        for node_name in all_nodes_in_order:
            node_id = self.node_ids.get(node_name)
            if not node_id:
                logger.error(f"Node {node_name} not found in node IDs map")
                continue
                
            logger.info(f"Starting node: {node_name} (ID: {node_id})")
            
            # Get current node status
            success, node_info = self.gns3_manager.api.get_node(self.gns3_manager.project_id, node_id)
            if not success:
                logger.error(f"Failed to get node info for {node_name}")
                continue
                
            # Check current status and start if needed
            current_status = node_info.get("status")
            if current_status == "started":
                logger.info(f"Node {node_name} is already started")
                continue
                
            # Get node info again to ensure we have the latest
            success, node_info = self.gns3_manager.api.get_node(self.gns3_manager.project_id, node_id)
            if not success:
                logger.error(f"Failed to get node info for {node_name}")
                continue
                
            # Start the node
            success, _ = self.gns3_manager.api.start_node(self.gns3_manager.project_id, node_id)
            if not success:
                logger.error(f"Failed to start node {node_name}")
                continue
                
        return True
    
    def configure_networking(self) -> bool:
        """
        Configure network conditions and connectivity based on topology.
        
        Returns:
            bool: True if configuration was successful, False otherwise
        """
        if not self.gns3_manager or not self.nodes:
            logger.error("Cannot configure networking: GNS3 manager or nodes not available")
            return False
            
        try:
            logger.info("Configuring network conditions...")
            
            # Extract network conditions from topology if present
            network_conditions = self.topology.get('network_conditions', {})
            
            # Apply link conditions if specified
            for link_key, condition in network_conditions.items():
                if link_key not in self.link_map:
                    logger.warning(f"Link {link_key} not found for network condition configuration")
                    continue
                    
                link_id = self.link_map[link_key]
                
                # Extract condition parameters
                delay = condition.get('delay', 0)
                jitter = condition.get('jitter', 0)
                loss = condition.get('loss', 0)
                bandwidth = condition.get('bandwidth', 0)
                
                # Apply the conditions using GNS3 API
                if delay > 0 or jitter > 0 or loss > 0 or bandwidth > 0:
                    logger.info(f"Applying network conditions to link {link_key}: delay={delay}ms, jitter={jitter}ms, loss={loss}%, bandwidth={bandwidth}kbps")
                    
                    condition_data = {
                        'delay': delay,
                        'jitter': jitter,
                        'loss': loss
                    }
                    
                    if bandwidth > 0:
                        condition_data['bandwidth'] = bandwidth
                    
                    # Apply conditions to link
                    success, _ = self.gns3_manager.api._make_request(
                        'PUT',
                        f'projects/{self.gns3_manager.project_id}/links/{link_id}',
                        json=condition_data
                    )
                    
                    if not success:
                        logger.warning(f"Failed to apply network conditions to link {link_key}")
            
            logger.info("Network configuration completed")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring networking: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def run_federated_learning(self) -> bool:
        """
        Run federated learning workload on deployed components.
        
        Returns:
            bool: True if workload was successfully executed, False otherwise
        """
        if not self.gns3_manager or not self.topology:
            logger.error("Cannot run federated learning: GNS3 manager or nodes not available")
            return False
            
        try:
            logger.info("Starting federated learning workload...")
            
            # --- Start Change: Fix node ID retrieval ---
            # Try both dictionaries where node IDs might be stored
            logger.debug(f"Nodes dictionary: {self.nodes}")
            logger.debug(f"Created nodes info dictionary: {self.created_nodes_info}")
            
            # Find the fl-server node ID
            server_node_id = None
            
            # First try self.nodes (it should be populated in the deploy step)
            server_node_id = self.nodes.get('fl-server')
            if server_node_id:
                logger.info(f"Found fl-server node ID in nodes dictionary: {server_node_id}")
            else:
                # Fallback to created_nodes_info
                server_node_id = self.created_nodes_info.get('fl-server')
                if server_node_id:
                    logger.info(f"Found fl-server node ID in created_nodes_info dictionary: {server_node_id}")
                    # Update self.nodes for future use
                    self.nodes['fl-server'] = server_node_id
            
            # If still not found, we can't proceed
            if not server_node_id:
                logger.error("Could not find fl-server node ID in any dictionary")
                return False
            # --- End Change ---
            
            # Configure and start the FL server
            server_nodes = [n for n in self.nodes.keys() if 'fl-server' in n]
            if not server_nodes:
                logger.error("No FL server node found")
                return False
                
            server_node = server_nodes[0]
            server_node_id = self.node_ids.get(server_node)
            
            if not server_node_id:
                logger.error(f"Node ID for {server_node} not found")
                return False
                
            # Start the FL server
            logger.info(f"FL Server {server_node} (ID: {server_node_id}) is expected to start automatically (via Docker CMD/ENTRYPOINT).")
            
            # Check if the server needs additional configuration
            server_config = {}
            federation_config = self.config.get('federation', {})
            
            # Create server config
            if federation_config:
                server_config['rounds'] = federation_config.get('rounds', 5)
                server_config['min_clients'] = federation_config.get('min_clients', 2)
                server_config['local_epochs'] = federation_config.get('local_epochs', 1)
                
                # Convert to JSON
                server_config_json = json.dumps(server_config)
                
                # Pass as environment variable or save to file
                # self._execute_on_node(
                #     server_node_id, 
                #     f"echo '{server_config_json}' > /app/config/server_config.json"
                # )
                logger.info(f"FL Server {server_node} on node ID {server_node_id} is expected to configure itself (e.g., via baked-in config or ENV VARS).")
            
            # Start the FL clients
            client_nodes = [n for n in self.nodes.keys() if 'fl-client' in n]
            if not client_nodes:
                logger.error("No FL client nodes found")
                return False
                
            logger.info(f"Starting {len(client_nodes)} FL clients...")
            
            # Start each client
            for client_node in client_nodes:
                client_node_id = self.node_ids.get(client_node)
                
                if not client_node_id:
                    logger.warning(f"Node ID for {client_node} not found")
                    continue
                    
                # Get server IP from network config
                server_ip = self.config.get('network', {}).get('ip_map', {}).get(server_node, '192.168.100.10')
                
                # Start the client with server information
                # success, response = self._execute_on_node(
                #     client_node_id,
                #     f"cd /app && python3 -m src.federated.client --server {server_ip}:5000 --start"
                # )
                
                # if not success:
                #     logger.warning(f"Failed to start FL client on {client_node}")
                logger.info(f"FL Client {client_node} (ID: {client_node_id}) is expected to configure (e.g. server IP via ENV VARS) and start automatically (via Docker CMD/ENTRYPOINT).")
                
                # Wait a bit before starting the next client to prevent flooding
                time.sleep(1)
            
            logger.info("Federated learning workload initiation calls complete.")
            return True # Assume success as commands are offloaded to Docker images
                
        except Exception as e:
            logger.error(f"Error running federated learning workload: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_fl_results(self) -> Dict[str, Any]:
        """Get the federated learning results."""
        return self.fl_results
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.gns3_manager:
            logger.info("Cleaning up GNS3 project...")
            self.gns3_manager.cleanup_project()

    def _create_environment_variables(self, node_config):
        """
        Create environment variables for a node based on node config and global settings
        """
        env_vars = {}
        
        # Add common environment variables
        env_vars['SCENARIO_TYPE'] = self.config.get('scenario_type', 'basic')
        env_vars['NODE_NAME'] = node_config.get('name')
        env_vars['SERVICE_TYPE'] = node_config.get('service_type', 'unknown')
        
        # First add the node-specific environment variables from topology
        # These take precedence over other environment variables
        node_env = node_config.get('environment', {})
        if isinstance(node_env, dict):
            for key, value in node_env.items():
                # Ensure values are strings for environment variables
                env_vars[key] = str(value)
                logger.debug(f"Added environment variable from topology: {key}={value}")
        
        # Add network configuration if available
        network_config = self.config.get('network', {})
        if network_config:
            # Get IP directly from topology first (higher priority)
            node_ip = node_config.get('ip_address')
            
            # Fall back to IP map if not in topology
            if not node_ip and 'ip_map' in network_config:
                ip_map = network_config.get('ip_map', {})
                node_ip = ip_map.get(node_config.get('name'))
            
            if node_ip:
                # Extract service type for env var naming
                service_type = env_vars.get('SERVICE_TYPE', 'unknown').upper().replace("-", "_")
                
                # Add node-specific IP variables if not already set from topology
                if f'NODE_IP_{service_type}' not in env_vars:
                    env_vars[f'NODE_IP_{service_type}'] = node_ip
                    logger.debug(f"Added IP variable: NODE_IP_{service_type}={node_ip}")
                
                # Add specific client IP vars if applicable
                if service_type == 'FL_CLIENT' and env_vars.get('CLIENT_ID'):
                    client_num = env_vars['CLIENT_ID'].split('-')[-1]
                    if f'NODE_IP_FL_CLIENT_{client_num}' not in env_vars:
                        env_vars[f'NODE_IP_FL_CLIENT_{client_num}'] = node_ip
                        logger.debug(f"Added client IP variable: NODE_IP_FL_CLIENT_{client_num}={node_ip}")
                    
                    if 'NODE_IP_FL_CLIENT' not in env_vars:
                        env_vars['NODE_IP_FL_CLIENT'] = node_ip
                        logger.debug(f"Added general client IP variable: NODE_IP_FL_CLIENT={node_ip}")
                
                # Add static IP config if needed
                if network_config.get('use_static_ip', False) and 'NODE_IP' not in env_vars:
                    env_vars['NODE_IP'] = node_ip
                    env_vars['USE_STATIC_IP'] = 'true'
                    logger.debug(f"Added static IP configuration: NODE_IP={node_ip}")
            
            # Pass all node IPs from topology to every node for cross-referencing
            # but don't override explicitly set values from the topology
            for topology_node in self.topology.get("nodes", []):
                other_node_name = topology_node.get("name")
                other_node_ip = topology_node.get("ip_address")
                other_service_type = topology_node.get("service_type", "").upper().replace("-", "_")
                
                if other_node_name and other_node_ip and other_service_type:
                    var_name = f"NODE_IP_{other_service_type}"
                    
                    # Special handling for client nodes (add client number)
                    if 'fl-client' in other_node_name.lower() and other_node_name.split('-')[-1].isdigit():
                        client_num = other_node_name.split('-')[-1]
                        var_name = f"NODE_IP_FL_CLIENT_{client_num}"
                    
                    # Only set if not already explicitly defined in the node's environment
                    if var_name not in env_vars:
                        env_vars[var_name] = other_node_ip
                        logger.debug(f"Added cross-reference IP: {var_name}={other_node_ip}")
                
            # Add subnet prefix if available and not already set
            if 'subnet' in network_config and 'SUBNET_PREFIX' not in env_vars:
                subnet_parts = network_config['subnet'].split('.')
                if len(subnet_parts) >= 3:
                    env_vars['SUBNET_PREFIX'] = '.'.join(subnet_parts[:3])
                    logger.debug(f"Added subnet prefix: SUBNET_PREFIX={env_vars['SUBNET_PREFIX']}")
        
        # Make sure we have proper GNS3 network flags set
        env_vars['GNS3_NETWORK'] = 'true'
        env_vars['NETWORK_MODE'] = 'docker'
        
        # Log the final environment variables for debugging
        logger.debug(f"Final environment variables for {node_config.get('name')}: {env_vars}")
        
        return env_vars

    def _calculate_required_adapters(self):
        """
        Calculate how many adapters each node needs based on links in the topology.
        
        Delegates to LinkManager.
        """
        if self.link_manager:
            return self.link_manager.calculate_required_adapters()
        else:
            logger.warning("LinkManager not initialized, cannot calculate required adapters")
            return {}

    def _check_for_port_conflicts(self, links):
        """
        Check for port conflicts in the topology links.
        
        Delegates to LinkManager.
        """
        if self.link_manager:
            return self.link_manager.check_for_port_conflicts(links)
        else:
            logger.warning("LinkManager not initialized, cannot check for port conflicts")
            return {}

    def _resolve_port_conflicts(self, links, conflicts):
        """
        Attempt to automatically resolve port conflicts by reassigning ports.
        
        Delegates to LinkManager.
        """
        if self.link_manager:
            return self.link_manager.resolve_port_conflicts(links, conflicts)
        else:
            logger.warning("LinkManager not initialized, cannot resolve port conflicts")
            return links

    def _find_next_available_adapter(self, node, used_adapters):
        """
        Find the next available adapter number for a node.
        
        Delegates to LinkManager.
        """
        if self.link_manager:
            return self.link_manager._find_next_available_adapter(node, used_adapters)
        else:
            logger.warning("LinkManager not initialized, cannot find next available adapter")
            return 0 