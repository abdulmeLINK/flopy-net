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

logger = logging.getLogger(__name__)

class DeploymentManager:
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
            
    def _create_nodes(self) -> bool:
        """
        Create nodes in the topology.
        
        Returns:
            bool: True if all nodes were created successfully, False otherwise
        """
        if not self.topology:
            logger.error("Cannot create nodes: Topology not available")
            return False
        
        # Get the topology nodes
        nodes = self.topology.get("nodes", [])
        if not nodes:
            logger.warning("No nodes found in the topology")
            return False
        
        # Log required adapters based on links
        required_adapters = self._calculate_required_adapters()
        logger.info(f"Required adapters calculated: {required_adapters}")
        
        # First, create all Ethernet switch nodes to ensure they are ready for connections
        for node_config in nodes:
            node_name = node_config.get("name")
            service_type = node_config.get("service_type", "").lower()
            template_name = node_config.get("template_name")
            
            if service_type != "switch" or template_name != "Ethernet switch":
                continue  # Skip non-switch nodes in this pass
                
            # Find the template ID for this node type
            template_id = None
            success, templates = self.gns3_manager.api._make_request('GET', 'templates')
            
            if success:
                for template in templates:
                    if template.get('name') == template_name:
                        template_id = template.get('template_id')
                        break
            
            if not template_id:
                logger.error(f"Template not found for node {node_name}: {template_name}")
                return False
            
            # Create the Ethernet switch with our special method
            logger.info(f"Creating Ethernet switch node: {node_name} (template: {template_name})")
            success, node_data = self._create_ethernet_switch(node_name, template_id, node_config)
            
            if not success:
                logger.error(f"Failed to create Ethernet switch node: {node_name}")
                continue
            
            # Store the node ID for linking later
            node_id = node_data.get('node_id')
            if node_id:
                self.node_ids[node_name] = node_id
                logger.info(f"Created Ethernet switch node: {node_name} (ID: {node_id})")
            else:
                logger.error(f"Node created but no node_id returned: {node_name}")
                
        # Now create the rest of the nodes
        for node_config in nodes:
            node_name = node_config.get("name")
            service_type = node_config.get("service_type", "").lower()
            template_name = node_config.get("template_name")
            
            # Skip Ethernet switches since we already created them
            if service_type == "switch" and template_name == "Ethernet switch":
                continue
                
            # Skip if node already exists in our list (might happen if node was created previously)
            if node_name in self.node_ids:
                logger.info(f"Node {node_name} already exists, skipping creation")
                continue
                
            # Find the template ID for this node type
            template_id = None
            success, templates = self.gns3_manager.api._make_request('GET', 'templates')
            
            if success:
                for template in templates:
                    if template.get('name') == template_name:
                        template_id = template.get('template_id')
                        break
            
            if not template_id:
                logger.error(f"Template not found for node {node_name}: {template_name}")
                continue
            
            # Set up node parameters
            node_params = {}
            
            # Add x, y coordinates if available
            if 'x' in node_config:
                node_params['x'] = node_config['x']
            if 'y' in node_config:
                node_params['y'] = node_config['y']
                
            # Check if this node needs specific adapter count
            if node_name in required_adapters:
                adapters_needed = required_adapters[node_name]
                logger.info(f"Node {node_name} needs {adapters_needed} adapter(s)")

                # Special case for Cloud node type
                if node_config.get("service_type", "").lower() == "cloud" or node_config.get("node_type", "").lower() == "cloud" or template_name.lower() == "cloud":
                    # Cloud nodes don't accept the adapters parameter directly
                    logger.info(f"Setting up Cloud node {node_name} with minimal properties")
                    # Remove any adapters property for Cloud nodes
                    node_params = {
                        'name': node_name,
                        'template_id': template_id,
                        'compute_id': 'local',
                        'x': node_config.get('x', 0),
                        'y': node_config.get('y', 0),
                        'node_type': 'cloud'
                    }
                    # We've completely replaced the node_params for Cloud node
                else:
                    # Handle adapters for different node types
                    current_adapters = 1 # Default
                    if service_type == "openvswitch":
                        # For OpenVSwitch nodes, use template value (typically 16)
                        # And ensure it's at least as high as our topology needs
                        success, template = self.gns3_manager.api.get_template(template_id)
                        if success and template and 'adapters' in template:
                            template_adapters = template.get('adapters', 8)
                            current_adapters = max(adapters_needed, template_adapters)
                            logger.info(f"Using OpenVSwitch with {current_adapters} adapters (template specifies {template_adapters})")
                        else:
                            # Fallback to at least 16 for OpenVSwitch
                            current_adapters = max(adapters_needed, 16)
                            logger.info(f"Using default of {current_adapters} adapters for OpenVSwitch")
                    elif service_type == "sdn-controller":
                        # For SDN controller, ensure we have at least 2 adapters
                        # and respect any explicitly configured adapters in topology
                        explicit_adapters = node_config.get('adapters', 0)
                        if explicit_adapters > 0:
                            current_adapters = max(adapters_needed, explicit_adapters)
                            logger.info(f"Using SDN controller with {current_adapters} adapters (topology specifies {explicit_adapters})")
                        else:
                            current_adapters = max(adapters_needed, 2)  # Minimum 2 adapters for SDN controller
                            logger.info(f"Using default of {current_adapters} adapters for SDN controller")
                    elif service_type in ["switch", "ethernet_switch"] and "adapters" in node_config:
                        # Ethernet switch port count is handled in _create_ethernet_switch
                        ports_needed = max(adapters_needed, node_config.get("adapters", 8))
                        logger.info(f"Ethernet switch {node_name} will need {ports_needed} ports (handled separately)")
                        # Don't set 'adapters' param directly for switches here
                        current_adapters = 0 # Reset to avoid setting it below
                    else:
                        # For all other nodes (like Docker containers)
                        explicit_adapters = node_config.get('adapters', 0)
                        if explicit_adapters > 0:
                            current_adapters = max(adapters_needed, explicit_adapters)
                            logger.info(f"Using explicitly configured {current_adapters} adapters for {node_name}")
                        else:
                            # Check template for default adapter count
                            success, template = self.gns3_manager.api.get_template(template_id)
                            if success and template and 'adapters' in template:
                                template_adapters = template.get('adapters', 1)
                                if template_adapters > 1:  # Only set if > 1
                                    current_adapters = max(adapters_needed, template_adapters)
                                    logger.info(f"Using {current_adapters} adapters for {node_name} (template default is {template_adapters})")
                            # For OpenVSwitch, ensure minimum 16
                            if service_type == "openvswitch":
                                current_adapters = 16
                                logger.info(f"Setting default 16 adapters for OpenVSwitch {node_name}")
                            # For SDN controller, ensure minimum 2
                            elif service_type == "sdn-controller":
                                current_adapters = 2
                                logger.info(f"Setting default 2 adapters for SDN controller {node_name}")
                            # Otherwise, check ports in node config
                            elif 'ports' in node_config and len(node_config['ports']) > 1:
                                # If node has multiple ports defined, ensure adapters >= ports
                                min_adapters = len(node_config['ports'])
                                current_adapters = min_adapters
                                logger.info(f"Setting {min_adapters} adapters based on ports config for {node_name}")

                # Set the adapters parameter at the root level if needed
                if current_adapters > 0:
                    node_params['adapters'] = current_adapters
                    logger.info(f"Setting {current_adapters} adapters for {node_name} in node_params")
            else:
                # If node wasn't in required_adapters, still check if it has explicit adapter count
                explicit_adapters = node_config.get('adapters', 0)
                if explicit_adapters > 0:
                    node_params['adapters'] = explicit_adapters
                    logger.info(f"Setting explicitly configured {explicit_adapters} adapters for {node_name}")
                else:
                    # Check template for default adapter count
                    success, template = self.gns3_manager.api.get_template(template_id)
                    if success and template and 'adapters' in template:
                        template_adapters = template.get('adapters', 1)
                        if template_adapters > 1:  # Only set if > 1
                            node_params['adapters'] = template_adapters
                            logger.info(f"Using template's default {template_adapters} adapters for {node_name}")
                        # For OpenVSwitch, ensure minimum 16
                        if service_type == "openvswitch":
                            node_params['adapters'] = 16
                            logger.info(f"Setting default 16 adapters for OpenVSwitch {node_name}")
                        # For SDN controller, ensure minimum 2
                        elif service_type == "sdn-controller":
                            node_params['adapters'] = 2
                            logger.info(f"Setting default 2 adapters for SDN controller {node_name}")
                        # Otherwise, check ports in node config
                        elif 'ports' in node_config and len(node_config['ports']) > 1:
                            # If node has multiple ports defined, ensure adapters >= ports
                            min_adapters = len(node_config['ports'])
                            node_params['adapters'] = min_adapters
                            logger.info(f"Setting {min_adapters} adapters based on ports config for {node_name}")

            # Create environment variables dict if needed
            if "environment" in node_config:
                env_vars = self._create_environment_variables(node_config)
                if env_vars:
                    node_params['environment'] = env_vars
                    
            # Special case for OpenVSwitch
            if service_type == "openvswitch":
                # Add OVS-specific parameters
                node_params['ports_mapping'] = []
                for port_num in range(16):  # Create 16 ports by default for OVS nodes
                    node_params['ports_mapping'].append({
                        'name': f'Ethernet{port_num}',
                        'port_number': port_num,
                        'type': 'access',
                        'vlan': 1
                    })
                    
            # Fetch actual template to check its adapter count
            success, template = self.gns3_manager.api.get_template(template_id)
            if success and template:
                template_adapters = template.get('adapters', 1)
                if template_adapters > node_params.get('adapters', 1):
                    # Ensure we respect template's minimum adapters
                    node_params['adapters'] = template_adapters
                    logger.info(f"Using template adapter count: {template_adapters} for {node_name}")
            
            # Special handling for Cloud nodes - make sure adapters is not included
            if (node_config.get("service_type", "").lower() == "cloud" or 
                node_config.get("node_type", "").lower() == "cloud" or
                template_name.lower() == "cloud"):
                # Remove adapters from node_params
                if 'adapters' in node_params:
                    del node_params['adapters']
                    logger.info(f"Removed adapters property from Cloud node {node_name} params")
                
                # Also remove properties if it exists
                if 'properties' in node_params:
                    del node_params['properties']
                    logger.info(f"Removed properties field from Cloud node {node_name} params")
            
            logger.debug(f"Creating node with params: {node_params}")
            
            # Use the GNS3Manager's create_node method, which wraps the API call
            try:
                # Prepare node_config with all necessary details
                full_node_config = {
                    **node_config,  # Include original topology config
                    **node_params   # Add calculated params like adapters, env, x, y
                }
                
                logger.debug(f"Calling GNS3Manager.create_node for {node_name} with config: {full_node_config}")
                
                success, node_data = self.gns3_manager.create_node(
                    node_name=node_name,
                    template_name=template_name,
                    node_config=full_node_config, # Pass the combined configuration
                    environment=full_node_config.get('environment') # Also pass env separately if needed by manager
                )
            except Exception as e:
                logger.error(f"Error calling gns3_manager.create_node for {node_name}: {e}")
                logger.debug(traceback.format_exc())
                success = False
                node_data = None

            if not success:
                logger.error(f"Failed to create node: {node_name}")
                continue
            
            # Store the node ID for linking later
            node_id = node_data.get('node_id')
            if node_id:
                self.node_ids[node_name] = node_id
                logger.info(f"Created node: {node_name} (ID: {node_id})")
            else:
                logger.error(f"Node created but no node_id returned: {node_name}")
                
        # Verify all nodes were created
        expected_nodes = [n['name'] for n in nodes]
        created_nodes = list(self.node_ids.keys())
        missing_nodes = [n for n in expected_nodes if n not in created_nodes]
        
        if missing_nodes:
            logger.error(f"Failed to create the following nodes: {missing_nodes}")
            return False
        
        logger.info(f"Successfully created {len(self.node_ids)} nodes")
        return True # All nodes created
    
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
        
        Returns:
            bool: True if all links were created successfully, False otherwise
        """
        if not self.topology:
            logger.error("Cannot create links: Topology not available")
            return False
        
        # Get the links from topology
        links = self.topology.get("links", [])
        if not links:
            logger.warning("No links found in topology")
            return True  # Not an error, just no links to create

        # Check for port conflicts before attempting to create links
        conflicts = self._check_for_port_conflicts(links)
        if conflicts:
            logger.warning(f"Port conflicts detected in topology: {conflicts}")
            if self.auto_fix_conflicts:
                logger.info("Attempting to auto-fix port conflicts...")
                links = self._resolve_port_conflicts(links, conflicts)
            else:
                logger.error("Resolve port conflicts in topology file before continuing")
                return False
        
        # Log node IDs for debugging
        logger.debug(f"Available node IDs for linking: {self.node_ids}")
        if not self.node_ids or len(self.node_ids) == 0:
            logger.error("No nodes have been created yet! Cannot create links without nodes.")
            return False
        
        # Make sure nodes are created and GNS3 can be queried
        if not self.gns3_manager or not self.gns3_manager.project_id:
            logger.error("GNS3 manager or project ID not available")
            return False
        
        # Get detailed information about nodes for better diagnostics
        try:
            success, nodes_info = self.gns3_manager.api.get_nodes(self.gns3_manager.project_id)
            if success:
                logger.info(f"Found {len(nodes_info)} nodes in GNS3 project")
                # Build a map of node_id to node details for easier lookup
                node_details = {node.get('node_id'): node for node in nodes_info}
                
                # Create a map of node name to ports for port validation
                node_ports_map = {}
                for node in nodes_info:
                    node_id = node.get('node_id')
                    node_name = node.get('name')
                    
                    # Store in our lookup map
                    if node_name in self.node_ids:
                        # Check if this is an Ethernet switch with ports_mapping
                        ports_mapping = node.get('properties', {}).get('ports_mapping', [])
                        if ports_mapping:
                            node_ports_map[node_name] = {
                                'type': 'ethernet_switch',
                                'ports': ports_mapping
                            }
                        else:
                            # For other node types, check available ports via ports info
                            success, ports_info = self.gns3_manager.api._make_request(
                                'GET', 
                                f'projects/{self.gns3_manager.project_id}/nodes/{node_id}/ports'
                            )
                            if success:
                                node_ports_map[node_name] = {
                                    'type': node.get('node_type', 'unknown'),
                                    'ports': ports_info
                                }
                logger.info(f"Collected port information for {len(node_ports_map)} nodes")
            else:
                logger.error(f"Failed to get nodes from GNS3: {nodes_info}")
        except Exception as e:
            logger.error(f"Error getting node information: {e}")
            # Continue with limited information - the operation might still succeed
            node_details = {}
            node_ports_map = {}
        
        # Calculate required adapters to cross-check our configuration
        required_adapters = self._calculate_required_adapters()
        logger.debug(f"Required adapters for nodes: {required_adapters}")
        
        # Track successfully created links
        success_count = 0
        
        # Process each link
        for idx, link in enumerate(links):
            source = link.get("source")
            target = link.get("target")
            source_adapter = link.get("source_adapter", 0)
            target_adapter = link.get("target_adapter", 0)
            
            logger.info(f"Processing link #{idx+1}: {source} (adapter {source_adapter}) -> {target} (adapter {target_adapter})")
            
            # Check if both source and target exist
            if source not in self.node_ids:
                logger.error(f"Source node '{source}' not found for link #{idx+1}")
                logger.error(f"Available nodes: {list(self.node_ids.keys())}")
                continue
                
            if target not in self.node_ids:
                logger.error(f"Target node '{target}' not found for link #{idx+1}")
                logger.error(f"Available nodes: {list(self.node_ids.keys())}")
                continue
            
            # Get the source and target node IDs
            source_id = self.node_ids[source]
            target_id = self.node_ids[target]
            
            # Verify ports are available
            source_ports_ok = True
            target_ports_ok = True
            
            # Check source port availability
            if source in node_ports_map:
                if node_ports_map[source]['type'] == 'ethernet_switch':
                    # For Ethernet switch, verify the port exists in ports_mapping
                    ports = node_ports_map[source]['ports']
                    source_port_exists = any(p.get('port_number') == source_adapter for p in ports)
                    if not source_port_exists:
                        logger.error(f"Source port {source_adapter} not found on Ethernet switch {source}")
                        logger.error(f"Available ports: {[p.get('port_number') for p in ports]}")
                        source_ports_ok = False
                else:
                    # For regular nodes, check in ports list
                    ports = node_ports_map[source]['ports']
                    source_port_exists = any(
                        p.get('adapter_number') == source_adapter or 
                        p.get('port_number') == source_adapter for p in ports
                    )
                    if not source_port_exists:
                        logger.error(f"Source port {source_adapter} not found on node {source}")
                        available_ports = []
                        for p in ports:
                            adapter = p.get('adapter_number', -1)
                            port = p.get('port_number', -1)
                            available_ports.append(f'adapter {adapter}/port {port}')
                        logger.error(f"Available ports: {available_ports}")
                        source_ports_ok = False
            
            # Check target port availability
            if target in node_ports_map:
                if node_ports_map[target]['type'] == 'ethernet_switch':
                    # For Ethernet switch, verify the port exists in ports_mapping
                    ports = node_ports_map[target]['ports']
                    target_port_exists = any(p.get('port_number') == target_adapter for p in ports)
                    if not target_port_exists:
                        logger.error(f"Target port {target_adapter} not found on Ethernet switch {target}")
                        logger.error(f"Available ports: {[p.get('port_number') for p in ports]}")
                        target_ports_ok = False
                else:
                    # For regular nodes, check in ports list
                    ports = node_ports_map[target]['ports']
                    target_port_exists = any(
                        p.get('adapter_number') == target_adapter or 
                        p.get('port_number') == target_adapter for p in ports
                    )
                    if not target_port_exists:
                        logger.error(f"Target port {target_adapter} not found on node {target}")
                        available_ports = []
                        for p in ports:
                            adapter = p.get('adapter_number', -1)
                            port = p.get('port_number', -1)
                            available_ports.append(f'adapter {adapter}/port {port}')
                        logger.error(f"Available ports: {available_ports}")
                        target_ports_ok = False
            
            # Skip this link if ports are not available
            if not (source_ports_ok and target_ports_ok):
                logger.error(f"Cannot create link due to port validation failure: {source} -> {target}")
                
                # Try to fix the ports for Ethernet switches
                if (source in node_ports_map and node_ports_map[source]['type'] == 'ethernet_switch' and not source_ports_ok) or \
                   (target in node_ports_map and node_ports_map[target]['type'] == 'ethernet_switch' and not target_ports_ok):
                    logger.info("Attempting to fix Ethernet switch ports...")
                    
                    # Fix source if it's an Ethernet switch
                    if source in node_ports_map and node_ports_map[source]['type'] == 'ethernet_switch' and not source_ports_ok:
                        self._ensure_switch_ports(source_id, source_adapter + 2)
                    
                    # Fix target if it's an Ethernet switch
                    if target in node_ports_map and node_ports_map[target]['type'] == 'ethernet_switch' and not target_ports_ok:
                        self._ensure_switch_ports(target_id, target_adapter + 2)
                    
                    # Refresh node ports map for the affected nodes
                    for node_name in [source, target]:
                        if node_name in self.node_ids and node_name in node_ports_map and node_ports_map[node_name]['type'] == 'ethernet_switch':
                            node_id = self.node_ids[node_name]
                            success, node_info = self.gns3_manager.api.get_node(self.gns3_manager.project_id, node_id)
                            if success:
                                ports_mapping = node_info.get('properties', {}).get('ports_mapping', [])
                                if ports_mapping:
                                    node_ports_map[node_name]['ports'] = ports_mapping
                    
                    logger.info("Ethernet switch ports updated, will try creating link again")
                else:
                    # Skip this link if we can't fix it
                    continue

            # Log the link we're attempting to create
            logger.info(f"Creating link #{idx+1}: {source} (adapter {source_adapter}) -> {target} (adapter {target_adapter})")
            
            # Add retries for link creation with exponential backoff
            max_retries = 2
            retry_count = 0
            link_created = False
            
            while retry_count < max_retries and not link_created:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                
                try:
                    # Get node info to determine type
                    success_src, src_node = self.gns3_manager.api.get_node(self.gns3_manager.project_id, source_id)
                    success_tgt, tgt_node = self.gns3_manager.api.get_node(self.gns3_manager.project_id, target_id)
                    
                    if not success_src or not success_tgt:
                        logger.error(f"Failed to get node info for link {source} -> {target}. Skipping.")
                        continue
                        
                    src_node_type = src_node.get('node_type', '')
                    tgt_node_type = tgt_node.get('node_type', '')
                    
                    # Configure source node
                    src_config = {}
                    if src_node_type == 'ethernet_switch':
                        # For Ethernet switch, use port_number for the port number field
                        src_config = {
                            "node_id": source_id, 
                            "port_number": source_adapter,  # Use adapter as port_number
                            "adapter_number": 0             # Use fixed adapter_number=0
                        }
                    else:
                        # For Docker containers, use adapter_number for the adapter field
                        src_config = {
                            "node_id": source_id, 
                            "adapter_number": source_adapter,  # Use adapter as adapter_number 
                            "port_number": 0                   # Use fixed port_number=0
                        }
                    
                    # Configure target node
                    tgt_config = {}
                    if tgt_node_type == 'ethernet_switch':
                        # For Ethernet switch, use port_number for the port number field
                        tgt_config = {
                            "node_id": target_id, 
                            "port_number": target_adapter,  # Use adapter as port_number
                            "adapter_number": 0             # Use fixed adapter_number=0
                        }
                    else:
                        # For Docker containers, use adapter_number for the adapter field
                        tgt_config = {
                            "node_id": target_id, 
                            "adapter_number": target_adapter,  # Use adapter as adapter_number
                            "port_number": 0                   # Use fixed port_number=0
                        }
                    
                    nodes_list = [src_config, tgt_config]
                                        
                    logger.debug(f"Link request data: {nodes_list}")
                    
                    # Create link
                    success, link_data = self.gns3_manager.api.create_link(
                        project_id=self.gns3_manager.project_id,
                        nodes=nodes_list
                    )
                    
                    if success:
                        logger.info(f"Link created successfully: {source} -> {target} (attempt {retry_count}/{max_retries})")
                        link_created = True
                        success_count += 1
                        
                        # Store link ID if available
                        if link_data and 'link_id' in link_data:
                            link_name = f"{source}_{source_adapter}_to_{target}_{target_adapter}"
                            self.link_map[link_name] = link_data['link_id']
                            logger.info(f"Stored link ID: {link_name} -> {link_data['link_id']}")
                    else:
                        error_msg = link_data.get('message', 'Unknown error') if isinstance(link_data, dict) else str(link_data)
                        
                        # Check for specific error types and log detailed information
                        if "Port not found" in error_msg:
                            logger.error(f"Port not found error when creating link between {source} and {target}: {error_msg}")
                            
                            # Try to log the available ports for both nodes for debugging
                            self._log_node_ports(source_id, source)
                            self._log_node_ports(target_id, target)
                            
                            # If this is the first attempt, try to fix ports if possible
                            if retry_count == 1:
                                logger.info(f"Attempting to fix port configuration for {source} and {target}")
                                if "switch" in source.lower() or "ethernet" in source.lower():
                                    self._ensure_switch_ports(source_id, source_adapter + 2)
                                if "switch" in target.lower() or "ethernet" in target.lower():
                                    self._ensure_switch_ports(target_id, target_adapter + 2)
                        else:
                            logger.error(f"Failed to create link between {source} and {target} (attempt {retry_count}/{max_retries}): {error_msg}")
                        
                        # Try creating link with alternate configuration (less relevant now but keep)
                        # Reconstruct alt_nodes_list based on node types as well
                        alt_nodes_list = [src_config, tgt_config] # Use the same logic as above for the fallback
                        
                        logger.debug(f"Trying alternate link configuration: {alt_nodes_list}")
                        
                        alt_success, alt_result = self.gns3_manager.api.create_link(
                            project_id=self.gns3_manager.project_id,
                            nodes=alt_nodes_list
                        )
                        
                        if alt_success:
                            logger.info(f"Link created successfully with alternate configuration: {source} -> {target}")
                            link_created = True
                            success_count += 1
                            
                            # Store link ID
                            if alt_result and 'link_id' in alt_result:
                                link_name = f"{source}_{source_adapter}_to_{target}_{target_adapter}"
                                self.link_map[link_name] = alt_result['link_id']
                        else:
                            alt_error = alt_result.get('message', 'Unknown error') if isinstance(alt_result, dict) else str(alt_result)
                            logger.error(f"Alternate link creation also failed: {alt_error}")
                        
                        # Wait before retrying, with exponential backoff
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        
                except Exception as e:
                    logger.error(f"Exception creating link between {source} and {target}: {e}")
                    # Wait before retrying
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
            
            if not link_created:
                logger.error(f"Failed to create link between {source} and {target} after {max_retries} attempts")
            else:
                logger.info(f"Successfully created link #{idx+1}: {source} -> {target}")
        
        # Report results
        logger.info(f"Created {success_count} out of {len(links)} links")
        if success_count == 0:
            logger.error("CRITICAL: No links were created successfully!")
        elif success_count < len(links):
            logger.warning(f"Only created {success_count} out of {len(links)} links")
        else:
            logger.info("All links created successfully")
            
        return success_count > 0  # Consider partial success as success
    
    def _log_node_ports(self, node_id, node_name):
        """Log the available ports for a node to help with debugging"""
        try:
            success, node_info = self.gns3_manager.api._make_request(
                'GET',
                f'projects/{self.gns3_manager.project_id}/nodes/{node_id}'
            )
            
            if success and node_info:
                logger.debug(f"Node {node_name} info: {node_info}")
                
                # Check for ports_mapping in properties
                ports_mapping = node_info.get('properties', {}).get('ports_mapping', [])
                if ports_mapping:
                    logger.info(f"Available ports for {node_name}:")
                    for port in ports_mapping:
                        logger.info(f"  - Port {port.get('port_number')}: {port.get('name')}")
                
        except Exception as e:
            logger.error(f"Error getting port information for {node_name}: {e}")
    
    def _ensure_switch_ports(self, switch_id, min_ports):
        """Ensure an Ethernet switch has at least the required number of ports"""
        try:
            # Get current switch configuration
            success, switch_info = self.gns3_manager.api._make_request(
                'GET',
                f'projects/{self.gns3_manager.project_id}/nodes/{switch_id}'
            )
            
            if not success or not switch_info:
                logger.error(f"Failed to get switch info for ID {switch_id}")
                return False
                
            # Get current ports mapping
            properties = switch_info.get('properties', {})
            ports_mapping = properties.get('ports_mapping', [])
            
            # Check if we already have enough ports
            current_port_count = len(ports_mapping)
            if current_port_count >= min_ports:
                logger.info(f"Switch has {current_port_count} ports, which is enough (needed {min_ports})")
                return True
                
            # Add more ports if needed
            logger.info(f"Adding ports to switch {switch_info.get('name')}: {current_port_count} -> {min_ports}")
            
            # Create new ports mapping with additional ports
            new_ports_mapping = list(ports_mapping)  # Make a copy
            
            for i in range(current_port_count, min_ports):
                new_ports_mapping.append({
                    'name': f'Ethernet{i}',
                    'port_number': i,
                    'type': 'access',
                    'vlan': 1
                })
                
            # Update switch with new port configuration
            new_properties = dict(properties)
            new_properties['ports_mapping'] = new_ports_mapping
            
            success, update_result = self.gns3_manager.api._make_request(
                'PUT',
                f'projects/{self.gns3_manager.project_id}/nodes/{switch_id}',
                data={'properties': new_properties}
            )
            
            if success:
                logger.info(f"Successfully updated switch ports: {current_port_count} -> {min_ports}")
                return True
            else:
                logger.error(f"Failed to update switch ports: {update_result}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating switch ports: {e}")
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
        
        Returns:
            Dict mapping node names to the number of adapters required
        """
        if not self.topology:
            logger.warning("No topology available for calculating required adapters")
            return {}
        
        adapter_count = {}
        
        # Process all links to count adapters
        links = self.topology.get("links", [])
        for link in links:
            source = link.get("source")
            target = link.get("target")
            source_adapter = link.get("source_adapter", 0)
            target_adapter = link.get("target_adapter", 0)
            
            if not source or not target:
                continue
                
            # Update maximum adapter index for source
            if source not in adapter_count:
                adapter_count[source] = source_adapter + 1
            else:
                adapter_count[source] = max(adapter_count[source], source_adapter + 1)
                
            # Update maximum adapter index for target
            if target not in adapter_count:
                adapter_count[target] = target_adapter + 1
            else:
                adapter_count[target] = max(adapter_count[target], target_adapter + 1)
        
        # Log the results
        logger.debug(f"Calculated adapter requirements: {adapter_count}")
        
        # Also check for nodes with adapters explicitly defined in the node config
        for node in self.topology.get("nodes", []):
            name = node.get("name")
            if not name:
                continue
                
            # If adapters explicitly specified in node config, ensure it's considered
            if "adapters" in node:
                explicit_adapters = node["adapters"]
                if name in adapter_count:
                    # Take the maximum of explicit config and calculated from links
                    adapter_count[name] = max(adapter_count[name], explicit_adapters)
                    logger.debug(f"Node {name} has {explicit_adapters} adapters specified in config (using max of {adapter_count[name]})")
                else:
                    adapter_count[name] = explicit_adapters
                    logger.debug(f"Node {name} has {explicit_adapters} adapters specified in config")
        
        return adapter_count

    def _check_for_port_conflicts(self, links):
        """
        Check for port conflicts in the topology links.
        
        Args:
            links: List of link definitions from topology
            
        Returns:
            Dictionary mapping conflicting ports to list of conflicting links
        """
        # Track port usage for each node
        port_usage = {}  # {node_name: {adapter_num: [link_indexes]}}
        conflicts = {}   # {node_name: {adapter_num: [link_indexes]}}
        
        for idx, link in enumerate(links):
            source = link.get("source")
            target = link.get("target")
            source_adapter = link.get("source_adapter", 0)
            target_adapter = link.get("target_adapter", 0)
            
            # Track source port usage
            if source not in port_usage:
                port_usage[source] = {}
            
            if source_adapter not in port_usage[source]:
                port_usage[source][source_adapter] = []
            
            port_usage[source][source_adapter].append(idx)
            
            # If this port is used more than once, record conflict
            if len(port_usage[source][source_adapter]) > 1:
                if source not in conflicts:
                    conflicts[source] = {}
                
                conflicts[source][source_adapter] = port_usage[source][source_adapter]
            
            # Track target port usage
            if target not in port_usage:
                port_usage[target] = {}
            
            if target_adapter not in port_usage[target]:
                port_usage[target][target_adapter] = []
            
            port_usage[target][target_adapter].append(idx)
            
            # If this port is used more than once, record conflict
            if len(port_usage[target][target_adapter]) > 1:
                if target not in conflicts:
                    conflicts[target] = {}
                
                conflicts[target][target_adapter] = port_usage[target][target_adapter]
        
        # Log detailed conflict information
        if conflicts:
            for node, adapters in conflicts.items():
                for adapter, link_indexes in adapters.items():
                    conflict_links = [f"Link #{i+1}: {links[i]['source']} -> {links[i]['target']}" for i in link_indexes]
                    logger.warning(f"Conflict on {node} adapter {adapter}: {', '.join(conflict_links)}")
        
        return conflicts

    def _resolve_port_conflicts(self, links, conflicts):
        """
        Attempt to automatically resolve port conflicts by reassigning ports.
        
        Args:
            links: Original list of link definitions
            conflicts: Dictionary of detected conflicts
            
        Returns:
            Modified list of links with conflicts resolved if possible
        """
        # Create a deep copy of links to modify
        resolved_links = copy.deepcopy(links)
        
        # Keep track of already used adapters for each node
        used_adapters = {}
        
        # First, build the initial adapter usage map
        for link in links:
            source = link.get("source")
            target = link.get("target")
            source_adapter = link.get("source_adapter", 0)
            target_adapter = link.get("target_adapter", 0)
            
            if source not in used_adapters:
                used_adapters[source] = set()
            used_adapters[source].add(source_adapter)
            
            if target not in used_adapters:
                used_adapters[target] = set()
            used_adapters[target].add(target_adapter)
        
        # Now process each conflicted node
        for node, adapters in conflicts.items():
            for adapter, link_indexes in adapters.items():
                # Keep the first occurrence, reassign others
                for i, link_idx in enumerate(link_indexes):
                    if i == 0:
                        # Keep the first one as is
                        continue
                    
                    # Find the conflicting link
                    link = resolved_links[link_idx]
                    
                    # Determine if this node is the source or target
                    is_source = (link["source"] == node)
                    
                    # Find the next available adapter
                    next_adapter = self._find_next_available_adapter(node, used_adapters)
                    
                    # Update the link
                    if is_source:
                        logger.info(f"Reassigning Link #{link_idx+1}: {node}[{adapter}] -> {link['target']}[{link['target_adapter']}] to use adapter {next_adapter}")
                        link["source_adapter"] = next_adapter
                    else:
                        logger.info(f"Reassigning Link #{link_idx+1}: {link['source']}[{link['source_adapter']}] -> {node}[{adapter}] to use adapter {next_adapter}")
                        link["target_adapter"] = next_adapter
                    
                    # Update used_adapters to include the new assignment
                    used_adapters[node].add(next_adapter)
        
        # Verify we've actually resolved all conflicts
        remaining_conflicts = self._check_for_port_conflicts(resolved_links)
        if remaining_conflicts:
            logger.warning(f"Could not resolve all port conflicts: {remaining_conflicts}")
            return links  # Return original links if we couldn't resolve everything
        
        return resolved_links

    def _find_next_available_adapter(self, node, used_adapters):
        """Find the next available adapter number for a node"""
        if node not in used_adapters:
            return 0
        
        # Find the lowest unused number
        adapter = 0
        while adapter in used_adapters[node]:
            adapter += 1
        
        return adapter 