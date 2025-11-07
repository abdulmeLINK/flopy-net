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
Base Scenario Class.

This module defines the base scenario class that all specific scenarios should inherit from.
It handles common functionality such as GNS3 initialization, Docker template registration,
and network setup that is shared across different scenarios.
"""

import os
import sys
import json
import logging
import uuid
import time
import traceback
import requests
from typing import Dict, Any, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- BEGIN FIX FOR RELATIVE IMPORT ERROR ---
# Add project root to sys.path to allow absolute imports when running directly
_CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_FILE_DIR, '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.scenarios.common.gns3_utils import manage_socat_port_forwarding
# --- END FIX FOR RELATIVE IMPORT ERROR ---

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseScenario:
    """Base class for all federated learning scenarios."""
    
    # Constants
    MAX_RETRY_COUNT = 3
    RETRY_DELAY = 5
    INIT_TIMEOUT = 180  # maximum time to wait for simulator initialization (seconds)
    
    # Success criteria
    SUCCESS_CRITERIA = {
        'network_setup': {
            'timeout': 300,  # seconds
            'required_components': ['server', 'clients', 'policy_engine'],
            'connectivity_checks': True
        },
        'component_deployment': {
            'timeout': 600,  # seconds
            'required_services': ['fl_server', 'fl_clients', 'policy_engine'],
            'health_checks': True
        },
        'training': {
            'timeout': 3600,  # seconds
            'min_rounds': 3,
            'min_accuracy': 0.7,
            'max_loss': 0.5
        }
    }
    
    def __init__(self, config_file_or_results_dir: str = "./results"):
        """Initialize the base scenario.
        
        Args:
            config_file_or_results_dir: Either a path to a config file or a results directory.
                If the path ends with .json, it's treated as a config file.
                Otherwise, it's treated as a results directory.
        """
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # --- BEGIN MOVED INITIALIZATIONS ---
        # Port forwarding attributes (moved up)
        self.collector_node_name: Optional[str] = None 
        self.collector_internal_ip: Optional[str] = None 
        self.collector_internal_port: int = 8000 # Default collector internal port (Changed back from 8082)
        self.collector_external_port: int = 8001 # Default external port on GNS3 host
        self.gns3_server_ip: Optional[str] = None # GNS3 Server IP for socat
        self.gns3_ssh_user: Optional[str] = None 
        self.gns3_ssh_password: Optional[str] = None 
        self.gns3_ssh_port: int = 22 
        self.collector_port_forwarding_active: bool = False

        # Base attributes (moved up)
        self.scenario_id = f"base-scenario-{uuid.uuid4().hex[:8]}"
        self.project_name = f"fl_{uuid.uuid4().hex[:4]}"
        
        # Components and status (moved up)
        self.policy_engine = None
        self.simulator = None
        self.gns3_params = {}
        self.components = {}
        self.deployment_status = {}
        self.metrics = {}
        self.status = "initialized"
        self.results = {}
        # --- END MOVED INITIALIZATIONS ---

        # Determine if the parameter is a config file or results directory
        if config_file_or_results_dir.endswith('.json'):
            # It's a config file
            self.config_file = config_file_or_results_dir
            self.results_dir = "./results"  # Default results directory
            self.logger.info(f"Using config file: {self.config_file}")
            # Don't try to create the config file as a directory
            # Load the config content here
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                    self.logger.info(f"Successfully loaded config content from {self.config_file}")
                    # Call _restructure_config AFTER config is loaded
                    self.config = self._restructure_config(self.config) # Ensure restructured config is stored
            except FileNotFoundError:
                self.logger.error(f"Config file not found at {self.config_file}")
                self.config = {} # Keep it empty if file not found
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding JSON from config file {self.config_file}: {e}")
                self.config = {} # Keep it empty if JSON is invalid
            except Exception as e:
                self.logger.error(f"An unexpected error occurred while loading config file {self.config_file}: {e}")
                self.config = {} # Keep it empty on other errors
                # Even if config loading fails, call restructure with empty config to init defaults
                self.config = self._restructure_config(self.config)
        else:
            # It's a results directory
            self.results_dir = config_file_or_results_dir
            self.config_file = None
            self.config = {} # Initialize empty config
            # Create results directory
            os.makedirs(self.results_dir, exist_ok=True)
            self.logger.info(f"Using results directory: {self.results_dir}")
            # Call _restructure_config with the empty config to set defaults
            self.config = self._restructure_config(self.config)
        
        self.logger.info("Initialized base scenario")
    
    def _load_config(self, scenario_name: str) -> Dict[str, Any]:
        """
        Load configuration for a specific scenario.
        
        Args:
            scenario_name: Name of the scenario
            
        Returns:
            The loaded configuration
            
        Raises:
            RuntimeError: If configuration cannot be loaded
        """
        try:
            # Try loading from scenario-specific config file
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "config", 
                f"{scenario_name}_gns3.json"
            )
            
            self.logger.info(f"Looking for config at: {config_path}")
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.logger.info(f"Loaded configuration from {scenario_name}_gns3.json")
                    return self._restructure_config(config)
            
            # Fallback to centralized config system
            from src.core.config import init_config, get_scenario_config
            
            self.logger.info(f"Config file not found at {config_path}, using centralized config system")
            init_config(scenario=scenario_name)
            config = get_scenario_config(scenario_name)
            
            if not config:
                raise ValueError(f"Failed to load configuration for {scenario_name}")
            
            return self._validate_config(config)
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to load configuration: {str(e)}")
    
    def _restructure_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restructure configuration to ensure it has all required sections.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Restructured configuration
        """
        # Create federation section if it doesn't exist
        if "federation" not in config and "training" in config:
            config["federation"] = {}
            
            # Copy training values to federation section
            training = config.get("training", {})
            config["federation"]["rounds"] = training.get("num_rounds", 3)
            config["federation"]["min_clients"] = training.get("min_clients", 2)
            config["federation"]["num_clients"] = training.get("num_clients", 5)
            config["federation"]["local_epochs"] = training.get("local_epochs", 1)
        
        # Restructure for model configuration
        if "model" not in config:
            config["model"] = {}
            # Use model_type from training section if available
            if "training" in config and "model_type" in config["training"]:
                config["model"]["name"] = config["training"]["model_type"]
            else:
                config["model"]["name"] = "cnn"
        
        # Ensure base keys exist before trying to access them for restructuring
        if "network" not in config:
            config["network"] = {}
        if "collector_forwarding" not in config:
            config["collector_forwarding"] = {}

        # Restructure for data configuration
        if "data" not in config and "dataset" in config:
            config["data"] = config["dataset"]
        
        # Add GNS3 configuration
        if "network" in config and "gns3" not in config["network"]:
            if "gns3_server" in config["network"]:
                server_url = config["network"]["gns3_server"]
                # Extract host and port from URL
                if server_url.startswith("http://"):
                    server_url = server_url[7:]  # Remove 'http://' prefix
                
                # Split by : to separate host and port
                url_parts = server_url.split(':')
                host = url_parts[0]
                port = int(url_parts[1]) if len(url_parts) > 1 else 3080
                
                # Create gns3 section if it doesn't exist
                if "gns3" not in config["network"]:
                    config["network"]["gns3"] = {}
                
                config["network"]["gns3"]["host"] = host
                config["network"]["gns3"]["port"] = port
        
        # Set GNS3 server IP attribute
        self.gns3_server_ip: Optional[str] = config.get("network", {}).get("gns3", {}).get("host")

        # Attempt to load GNS3 SSH details from config if available
        # Users should ensure their scenario config (e.g., scenario_name_gns3.json)
        # or the centralized config provides these under network.gns3_ssh
        gns3_ssh_config = config["network"].get("gns3_ssh", {})
        self.gns3_ssh_user = gns3_ssh_config.get("user", "gns3") # Default to 'gns3'
        self.gns3_ssh_password = gns3_ssh_config.get("password", "gns3") # Default to 'gns3'
        self.gns3_ssh_port = gns3_ssh_config.get("port", 22) # Default to 22

        # Configuration for collector port forwarding (can be overridden by scenario-specific config)
        collector_config = config.get("collector_forwarding", {}) # .get is safe, but we ensured key above
        self.collector_node_name = collector_config.get("node_name", "collector") 
        self.collector_internal_ip = collector_config.get("internal_ip") 
        
        # Use defaults from __init__ if not found in config
        _init_default_collector_internal_port = self.collector_internal_port
        _init_default_collector_external_port = self.collector_external_port
        self.collector_internal_port = collector_config.get("internal_port", _init_default_collector_internal_port)
        self.collector_external_port = collector_config.get("external_port", _init_default_collector_external_port)

        # Default GNS3 server IP if not found in specific config path
        if not self.gns3_server_ip:
            self.gns3_server_ip = "127.0.0.1" # Fallback, user should configure this
            logger.warning(f"GNS3 server IP not found in config at network.gns3.host, defaulting to {self.gns3_server_ip}. Please ensure it's configured.")

        # Ensure that the network section exists before trying to access sub-keys
        if "network" not in config:
            raise ValueError("Missing network configuration")
        
        if config: # Only log if config was not empty to begin with
            self.logger.info("Configuration restructured successfully")
        else:
            self.logger.info("Configuration was empty, restructured with defaults.")
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate required configuration sections are present.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Validated configuration
            
        Raises:
            ValueError: If required sections are missing
        """
        # Validate required configuration sections
        required_sections = ["federation", "network", "model", "data"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate network configuration
        network_config = config["network"]
        if "simulator" not in network_config:
            raise ValueError("Missing simulator type in network configuration")
        if network_config["simulator"] != "gns3":
            raise ValueError("Only GNS3 simulator is supported")
        if "topology" not in network_config:
            raise ValueError("Missing topology type in network configuration")
        
        # Ensure GNS3 configuration exists
        if "gns3" not in network_config:
            # Create default GNS3 configuration
            network_config["gns3"] = {
                "host": "localhost",
                "port": 3080,
                "num_clients": config.get("federation", {}).get("num_clients", 5)
            }
        
        self.logger.info("Configuration validated successfully")
        return config
    
    def _check_gns3_running(self, host='localhost', port=3080) -> bool:
        """
        Check if GNS3 server is running.
        
        Args:
            host: GNS3 server host
            port: GNS3 server port
            
        Returns:
            bool: True if GNS3 server is running, False otherwise
        """
        try:
            self.logger.info(f"Checking if GNS3 server is running at {host}:{port}")
            try:
                response = requests.get(f"http://{host}:{port}/v2/version", timeout=5)
                if response.status_code == 200:
                    self.logger.info(f"GNS3 server is running at {host}:{port}: {response.json()}")
                    return True
                else:
                    self.logger.warning(f"GNS3 server returned status code {response.status_code}")
                    return False
            except Exception as e:
                self.logger.warning(f"Error connecting to GNS3 server: {str(e)}")
                return False
        except Exception as e:
            self.logger.error(f"Error checking GNS3 server: {str(e)}")
            return False
    
    def _setup_network(self, num_clients: int = 5) -> bool:
        """Set up the network for the scenario.
        
        Args:
            num_clients: Number of clients to create in the network
            
        Returns:
            bool: True if network setup was successful, False otherwise
        """
        try:
            # Determine network settings from configuration
            network_config = self.config.get('network', {})
            simulator_type = network_config.get('simulator', 'gns3')
            
            # Ensure we're always using GNS3
            if simulator_type != 'gns3':
                raise ValueError("Only GNS3 simulator is supported for scenarios")
                
            topology_type = network_config.get('topology', 'star')
            
            self.logger.info(f"Setting up network with GNS3 simulator and {topology_type} topology")
            
            # Use GNS3 parameters from config
            self.gns3_params = network_config.get('gns3', {})
            self.logger.info(f"Using project name: {self.project_name}")
            
            # Get host and port parameters
            gns3_host = self.gns3_params.get('host', 'localhost')
            gns3_port = self.gns3_params.get('port', 3080)
            
            self.logger.info(f"Connecting to GNS3 server at {gns3_host}:{gns3_port}")
            
            # Check if GNS3 is running
            if not self._check_gns3_running(host=gns3_host, port=gns3_port):
                error_msg = f"GNS3 server is not running at {gns3_host}:{gns3_port}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Initialize the GNS3 simulator
            self.simulator = self.initialize_simulator(host=gns3_host, port=gns3_port, num_clients=num_clients)
            if not self.simulator:
                raise RuntimeError("GNS3 simulator initialization failed")
            
            # Register GNS3 templates
            if not self._register_gns3_templates():
                raise RuntimeError("Failed to register GNS3 templates")
            
            # Create topology
            if not self._create_topology(topology_type, num_clients):
                raise RuntimeError(f"Failed to create {topology_type} topology")
            
            # Validate topology
            if not self._validate_topology():
                raise RuntimeError("Topology validation failed")
                
            self.logger.info("GNS3 network setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up network: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _create_topology(self, topology_type: str, num_clients: int) -> bool:
        """Create the network topology in GNS3.

        Args:
            topology_type: Type of topology to create (star, mesh, etc.)
            num_clients: Number of clients in the topology

        Returns:
            bool: True if topology creation was successful, False otherwise
        """
        try:
            self.logger.info(f"Creating {topology_type} topology with {num_clients} clients")
            
            # Create topology based on type
            if topology_type == 'star':
                return self.simulator.create_star_topology(num_clients)
            elif topology_type == 'mesh':
                return self.simulator.create_mesh_topology(num_clients)
            else:
                self.logger.error(f"Unsupported topology type: {topology_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating topology: {str(e)}")
            return False
    
    def _validate_topology(self) -> bool:
        """Validate the network topology.
        
        Returns:
            bool: True if topology is valid, False otherwise
        """
        try:
            self.logger.info("Validating network topology")
            
            # Get all nodes
            nodes = self.simulator.get_all_nodes()
            if not nodes:
                self.logger.error("No nodes found in topology")
                return False
            
            # Check for required node types
            required_types = ['server', 'client', 'policy_engine']
            found_types = set()
            
            for node in nodes:
                node_name = node.get('name', '').lower()
                for req_type in required_types:
                    if req_type in node_name:
                        found_types.add(req_type)
            
            # Check if all required types are present
            missing_types = set(required_types) - found_types
            if missing_types:
                self.logger.error(f"Missing required node types: {missing_types}")
                return False
            
            # Test connectivity between nodes
            if not self._test_connectivity():
                self.logger.error("Connectivity test failed")
                return False
            
            self.logger.info("Topology validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating topology: {str(e)}")
            return False
    
    def _deploy_components(self) -> bool:
        """Deploy all components to GNS3 nodes.
        
        Returns:
            bool: True if all components were deployed successfully, False otherwise
        """
        try:
            self.logger.info("Deploying components to GNS3 nodes")
            
            # Get all nodes
            nodes = self.simulator.get_all_nodes()
            if not nodes:
                self.logger.error("No nodes found for component deployment")
                return False
            
            # Deploy components in parallel
            with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
                futures = []
                for node in nodes:
                    node_name = node.get('name', '').lower()
                    
                    # Determine component type based on node name
                    if 'server' in node_name:
                        component_type = 'fl_server'
                    elif 'client' in node_name:
                        component_type = 'fl_client'
                    elif 'policy' in node_name:
                        component_type = 'policy_engine'
                    else:
                        continue
                    
                    # Submit deployment task
                    future = executor.submit(
                        self._deploy_component,
                        component_type,
                        node['node_id'],
                        node_name
                    )
                    futures.append(future)
                
                # Wait for all deployments to complete
                for future in as_completed(futures):
                    try:
                        success = future.result()
                        if not success:
                            self.logger.error("Component deployment failed")
                            return False
                    except Exception as e:
                        self.logger.error(f"Error in component deployment: {str(e)}")
                        return False
            
            # Verify all components are running
            if not self._verify_component_status():
                self.logger.error("Component status verification failed")
                return False
            
            self.logger.info("All components deployed successfully")

            # After all components are deployed and collector_internal_ip is known:
            if self.collector_node_name:
                try:
                    # This is a placeholder. You need to get the actual IP of the collector node.
                    # This might involve querying your GNS3 simulator instance.
                    # Example: self.collector_internal_ip = self.simulator.get_node_ip(self.collector_node_name) # Example
                    # For now, let's assume it's configured or discovered.
                    # If you have a self.components dict like: self.components['collector-0'] = {'ip': '192.168.x.y'}
                    # REMOVED: Flawed dynamic IP discovery for collector, as it's now set from config.
                    # if self.components:
                    #     for node_id, node_data in self.components.items(): # Iterate through deployed components
                    #         # Assuming node_data might have a 'name' or 'type' field to identify the collector
                    #         # And node_data has an 'ip' field
                    #         node_info = self.simulator.get_node_info(node_id) # Hypothetical method
                    #         if node_info and node_info.get('name') == self.collector_node_name:
                    #              # Find an IPv4 address for the collector node
                    #             for interface in node_info.get('interfaces', []):
                    #                 if interface.get('ip_address') and '.' in interface.get('ip_address'): # Basic IPv4 check
                    #                     self.collector_internal_ip = interface.get('ip_address')
                    #                     self.logger.info(f"Discovered collector internal IP: {self.collector_internal_ip} for node {self.collector_node_name}")
                    #                     break
                    #             if not self.collector_internal_ip and node_info.get('name') == self.collector_node_name: 
                    #                 self.logger.warning(f"Could not determine internal IP for collector node: {self.collector_node_name} from node_info: {node_info}")


                    if not self.collector_internal_ip: # This check should ideally not be hit if configured properly
                        self.logger.warning(
                            f"Collector internal IP for node '{self.collector_node_name}' is NOT SET. "
                            f"Skipping port forwarding. Please ensure it's configured (e.g. in 'collector_forwarding.internal_ip') or defaults correctly."
                        )
                    elif self.config.get("network", {}).get("gns3", {}).get("host") and self.gns3_ssh_user and self.gns3_ssh_password:
                        self.logger.info(
                            f"Attempting to start port forwarding for collector: "
                            f"GNS3 Host {self.config['network']['gns3']['host']}:{self.collector_external_port} -> "
                            f"Collector Node {self.collector_internal_ip}:{self.collector_internal_port}"
                        )
                        success = manage_socat_port_forwarding(
                            gns3_server_ip=self.config["network"]["gns3"]["host"],
                            gns3_server_ssh_port=self.gns3_ssh_port,
                            gns3_server_user=self.gns3_ssh_user,
                            gns3_server_password=self.gns3_ssh_password,
                            action="start",
                            external_port=self.collector_external_port,
                            internal_ip=self.collector_internal_ip,
                            internal_port=self.collector_internal_port
                        )
                        if success:
                            self.logger.info("Successfully started port forwarding for collector.")
                            self.collector_port_forwarding_active = True
                        else:
                            self.logger.error("Failed to start port forwarding for collector.")
                            # Decide if this is a critical failure for the scenario
                            # all_deployed_successfully = False 
                except Exception as e:
                    self.logger.error(f"Error during collector port forwarding setup: {e}")
                    self.logger.error(traceback.format_exc())
                    # all_deployed_successfully = False
            else:
                self.logger.info("Collector node name not specified, skipping port forwarding.")

            return True
            
        except Exception as e:
            self.logger.error(f"Error deploying components: {str(e)}")
            return False
    
    def _deploy_component(self, component_type: str, node_id: str, node_name: str) -> bool:
        """Deploy a single component to a GNS3 node.
        
        Args:
            component_type: Type of component to deploy
            node_id: ID of the node to deploy to
            node_name: Name of the node
            
        Returns:
            bool: True if deployment was successful, False otherwise
        """
        try:
            self.logger.info(f"Deploying {component_type} to {node_name}")
            
            # Get component configuration
            config = self._get_component_config(component_type)
            if not config:
                self.logger.error(f"No configuration found for {component_type}")
                return False
            
            # Deploy component using simulator
            success = self.simulator.deploy_component(component_type, node_name, config)
            if not success:
                self.logger.error(f"Failed to deploy {component_type} to {node_name}")
                return False
            
            # Start the component
            if not self.simulator.start_component(component_type, node_name):
                self.logger.error(f"Failed to start {component_type} on {node_name}")
                return False
            
            # Wait for component to be ready
            if not self._wait_for_component(component_type, node_name):
                self.logger.error(f"Component {component_type} on {node_name} failed to start")
                return False
            
            self.logger.info(f"Successfully deployed and started {component_type} on {node_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deploying {component_type} to {node_name}: {str(e)}")
            return False
    
    def _wait_for_component(self, component_type: str, node_name: str, timeout: int = 120, check_interval: int = 5) -> bool:
        """
        Wait for a component to be ready.
        Enhanced to check GNS3 exec readiness for Docker components.
        
        Args:
            component_type: Type of component
            node_name: Name of the node
            timeout: Maximum time to wait in seconds
            check_interval: Interval between checks in seconds
            
        Returns:
            bool: True if component is ready, False otherwise
        """
        try:
            self.logger.info(f"Waiting for {component_type} on {node_name} to be ready (timeout: {timeout}s)")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Standard health check (if implemented by simulator)
                if hasattr(self.simulator, 'check_component_health') and \
                   self.simulator.check_component_health(component_type, node_name):
                    self.logger.info(f"Simulator reports {component_type} on {node_name} is healthy.")
                    
                    # For Docker nodes, also try a benign exec command as a further readiness check
                    # This assumes the simulator has a method like 'get_node_type' or 'get_node_details'
                    # and 'execute_command_on_node'
                    node_details = None
                    if hasattr(self.simulator, 'get_node_details_by_name'): # Ideal
                        node_details = self.simulator.get_node_details_by_name(node_name)
                    elif hasattr(self.simulator, 'get_node_by_name'): # Fallback
                         node_info = self.simulator.get_node_by_name(node_name)
                         if node_info: # Make sure node_info is not None
                            node_details = {'node_type': node_info.get('node_type') if hasattr(node_info, 'get') else 'unknown'}


                    # Check if it's a docker node and simulator has execute_command_on_node
                    if node_details and node_details.get('node_type') == 'docker' and \
                       hasattr(self.simulator, 'execute_command_on_node'):
                        self.logger.info(f"Attempting GNS3 exec readiness check for Docker node {node_name}...")
                        try:
                            # Assuming execute_command_on_node returns a result or raises error
                            # A successful benign command indicates the exec endpoint is responsive
                            # Important: The actual implementation of execute_command_on_node
                            # needs to correctly interpret GNS3 API responses (e.g., handle 404 as not ready)
                            exec_result = self.simulator.execute_command_on_node(node_name, "pwd") # Benign command
                            # If execute_command_on_node doesn't raise an exception for failure,
                            # you might need to check its return value. For now, assume success if no error.
                            self.logger.info(f"GNS3 exec readiness check PASSED for {node_name}.")
                            return True # Component is truly ready
                        except Exception as exec_e:
                            self.logger.warning(f"GNS3 exec readiness check for {node_name} failed: {exec_e}. Retrying...")
                    else:
                        # If not Docker, or no exec capability, or no node_type info, rely on health check alone
                        self.logger.info(f"{component_type} on {node_name} is ready (based on simulator health check).")
                        return True 
                else:
                    self.logger.info(f"Simulator reports {component_type} on {node_name} NOT YET healthy or check_component_health not available.")

                self.logger.info(f"Waiting for {component_type} on {node_name}... ({int(time.time() - start_time)}s / {timeout}s)")
                time.sleep(check_interval)
            
            self.logger.error(f"Timeout waiting for {component_type} on {node_name} to become fully ready.")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for {component_type} on {node_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _verify_component_status(self) -> bool:
        """Verify that all components are running properly.
        
        Returns:
            bool: True if all components are running, False otherwise
        """
        try:
            self.logger.info("Verifying component status")
            
            # Get all nodes
            nodes = self.simulator.get_all_nodes()
            if not nodes:
                self.logger.error("No nodes found for status verification")
                return False
            
            # Check each component
            for node in nodes:
                node_name = node.get('name', '').lower()
                
                # Determine component type
                if 'server' in node_name:
                    component_type = 'fl_server'
                elif 'client' in node_name:
                    component_type = 'fl_client'
                elif 'policy' in node_name:
                    component_type = 'policy_engine'
                else:
                    continue
                
                # Check component health
                if not self.simulator.check_component_health(component_type, node_name):
                    self.logger.error(f"Component {component_type} on {node_name} is not healthy")
                    return False
            
            self.logger.info("All components are running properly")
            return True
                
        except Exception as e:
            self.logger.error(f"Error verifying component status: {str(e)}")
            return False
    
    def _get_component_config(self, component_type: str) -> Dict[str, Any]:
        """Get configuration for a component.
        
        Args:
            component_type: Type of component
            
        Returns:
            Dict containing component configuration
        """
        try:
            # Base configuration
            config = {
                'scenario_id': self.scenario_id,
                'project_name': self.project_name,
                'results_dir': self.results_dir
            }
            
            # Add component-specific configuration
            if component_type == 'fl_server':
                config.update({
                    'num_clients': self.config.get('federation', {}).get('num_clients', 5),
                    'rounds': self.config.get('federation', {}).get('rounds', 3),
                    'model': self.config.get('model', {}).get('name', 'cnn')
                })
            elif component_type == 'fl_client':
                config.update({
                    'client_id': f"client_{uuid.uuid4().hex[:4]}",
                    'server_host': self.config.get('network', {}).get('server_host', 'localhost'),
                    'server_port': self.config.get('network', {}).get('server_port', 8080),
                    'model': self.config.get('model', {}).get('name', 'cnn')
                })
            elif component_type == 'policy_engine':
                config.update({
                    'policies': self.config.get('policies', {}),
                    'enforcement_mode': self.config.get('policy_engine', {}).get('enforcement_mode', 'strict')
                })
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error getting component configuration: {str(e)}")
            return {}
    
    def _check_success_criteria(self) -> bool:
        """Check if the scenario meets all success criteria.
        
        Returns:
            bool: True if all criteria are met, False otherwise
        """
        try:
            self.logger.info("Checking success criteria")
            
            # Check network setup criteria
            if not self._check_network_setup_criteria():
                self.logger.error("Network setup criteria not met")
                return False
            
            # Check component deployment criteria
            if not self._check_deployment_criteria():
                self.logger.error("Component deployment criteria not met")
                return False
            
            # Check training criteria if applicable
            if hasattr(self, 'fl_results') and self.fl_results:
                if not self._check_training_criteria():
                    self.logger.error("Training criteria not met")
                    return False
            
            self.logger.info("All success criteria met")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking success criteria: {str(e)}")
            return False
    
    def _check_network_setup_criteria(self) -> bool:
        """Check if network setup meets success criteria.
        
        Returns:
            bool: True if criteria are met, False otherwise
        """
        try:
            # Check if all required components are present
            nodes = self.simulator.get_all_nodes()
            if not nodes:
                return False
            
            required_components = self.SUCCESS_CRITERIA['network_setup']['required_components']
            found_components = set()
            
            for node in nodes:
                node_name = node.get('name', '').lower()
                for req_comp in required_components:
                    if req_comp in node_name:
                        found_components.add(req_comp)
            
            if len(found_components) != len(required_components):
                self.logger.error(f"Missing required components: {set(required_components) - found_components}")
                return False
            
            # Check connectivity
            if self.SUCCESS_CRITERIA['network_setup']['connectivity_checks']:
                if not self._test_connectivity():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking network setup criteria: {str(e)}")
            return False
    
    def _check_deployment_criteria(self) -> bool:
        """Check if component deployment meets success criteria.
        
        Returns:
            bool: True if criteria are met, False otherwise
        """
        try:
            # Check if all required services are running
            required_services = self.SUCCESS_CRITERIA['component_deployment']['required_services']
            
            for service in required_services:
                if not self.simulator.check_service_health(service):
                    self.logger.error(f"Service {service} is not healthy")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking deployment criteria: {str(e)}")
            return False
    
    def _check_training_criteria(self) -> bool:
        """Check if training meets success criteria.
        
        Returns:
            bool: True if criteria are met, False otherwise
        """
        try:
            criteria = self.SUCCESS_CRITERIA['training']
            
            # Check minimum rounds
            if self.fl_results.get('rounds_completed', 0) < criteria['min_rounds']:
                self.logger.error(f"Not enough rounds completed: {self.fl_results.get('rounds_completed', 0)} < {criteria['min_rounds']}")
                return False
            
            # Check accuracy
            if self.fl_results.get('accuracy', 0) < criteria['min_accuracy']:
                self.logger.error(f"Accuracy too low: {self.fl_results.get('accuracy', 0)} < {criteria['min_accuracy']}")
                return False
            
            # Check loss
            if self.fl_results.get('loss', float('inf')) > criteria['max_loss']:
                self.logger.error(f"Loss too high: {self.fl_results.get('loss', float('inf'))} > {criteria['max_loss']}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking training criteria: {str(e)}")
            return False
    
    def _test_connectivity(self) -> bool:
        """Test network connectivity between nodes.
        
        Returns:
            bool: True if connectivity tests passed, False otherwise
            
        Raises:
            RuntimeError: If simulator is not initialized
        """
        logger.info("Testing network connectivity")
        
        try:
            if not hasattr(self, 'simulator') or not self.simulator:
                error_msg = "Simulator not initialized for connectivity testing"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Get all nodes
            nodes = self.simulator.get_all_nodes()
            if not nodes:
                error_msg = "No nodes found in the GNS3 simulator"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Found {len(nodes)} nodes in the network")
            
            # Find server and client nodes
            server_node = None
            client_nodes = []
            for node in nodes:
                if 'server' in node.name.lower():
                    server_node = node
                elif 'client' in node.name.lower():
                    client_nodes.append(node)
            
            if not server_node:
                error_msg = "Server node not found in GNS3 network"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            if not client_nodes:
                error_msg = "No client nodes found in GNS3 network"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Testing connectivity between server {server_node.name} and {len(client_nodes)} clients")
            
            # Test connectivity by checking if nodes are running
            server_status = self.simulator.get_node_status(server_node.node_id)
            if server_status != 'started':
                error_msg = f"Server node {server_node.name} is not running (status: {server_status})"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Server node {server_node.name} is running")
            
            # Check client nodes
            failed_clients = []
            for client_node in client_nodes:
                client_status = self.simulator.get_node_status(client_node.node_id)
                if client_status != 'started':
                    failed_clients.append(client_node.name)
                    logger.error(f"Client node {client_node.name} is not running (status: {client_status})")
                else:
                    logger.info(f"Client node {client_node.name} is running")
            
            # Ensure all clients are running
            if failed_clients:
                error_msg = f"The following client nodes are not running: {', '.join(failed_clients)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Test connectivity using simulator's test function
            if hasattr(self.simulator, 'test_connectivity') and callable(getattr(self.simulator, 'test_connectivity')):
                connectivity_result = self.simulator.test_connectivity(server_node, client_nodes)
                if not connectivity_result:
                    error_msg = "GNS3 connectivity test failed"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                logger.info("GNS3 connectivity test passed")
            
            logger.info("Network connectivity check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error testing connectivity: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def cleanup_after_scenario(self):
        """Clean up resources after the scenario has finished."""
        self.logger.info(f"Starting cleanup for scenario: {self.scenario_id}")
        
        # Stop collector port forwarding if it was active
        if self.collector_port_forwarding_active:
            self.logger.info(
                f"Attempting to stop port forwarding for collector: "
                f"GNS3 Host {self.config.get('network', {}).get('gns3', {}).get('host')}:{self.collector_external_port}"
            )
            if self.config.get("network", {}).get("gns3", {}).get("host") and self.gns3_ssh_user and self.gns3_ssh_password and self.collector_internal_ip:
                success = manage_socat_port_forwarding(
                    gns3_server_ip=self.config["network"]["gns3"]["host"],
                    gns3_server_ssh_port=self.gns3_ssh_port,
                    gns3_server_user=self.gns3_ssh_user,
                    gns3_server_password=self.gns3_ssh_password,
                    action="stop",
                    external_port=self.collector_external_port,
                    internal_ip=self.collector_internal_ip, # socat stop doesn't strictly need internal IP/port but good for consistency
                    internal_port=self.collector_internal_port
                )
                if success:
                    self.logger.info("Successfully stopped port forwarding for collector.")
                    self.collector_port_forwarding_active = False
                else:
                    self.logger.warning("Failed to stop port forwarding for collector. Manual check may be required on GNS3 server.")
            else:
                self.logger.warning("Missing GNS3 host, SSH credentials, or collector internal IP. Cannot stop port forwarding automatically.")

            # Original cleanup logic from the template (if any, or your specific cleanup)
            if self.simulator:
                try:
                    self.logger.info(f"Closing project: {self.project_name} on GNS3 server.")
                    # Assuming simulator has a method like close_project or similar
                    # self.simulator.close_project(self.project_name) # Example
                    # Or more generically, ensure resources are released
                    if hasattr(self.simulator, 'cleanup'):
                        self.simulator.cleanup()
                    elif hasattr(self.simulator, 'close'):
                         self.simulator.close()
                    self.logger.info("GNS3 project resources cleaned up.")
                except Exception as e:
                    self.logger.error(f"Error during GNS3 cleanup: {e}")
                    self.logger.error(traceback.format_exc())
            
            self.status = "cleaned_up"
            self.logger.info(f"Scenario {self.scenario_id} cleanup complete.")

    def run(self):
        """
        Run the scenario. This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the run method") 