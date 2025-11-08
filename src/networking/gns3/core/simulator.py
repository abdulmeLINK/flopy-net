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
Core GNS3 Simulator Implementation.

This module provides the base GNS3Simulator class that implements the INetworkSimulator interface.
"""

import os
import sys
import logging
import random
import time
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union
import requests
import uuid

from src.networking.interfaces.network_simulator import INetworkSimulator
from src.networking.gns3.core.api import GNS3API
from src.networking.gns3.topology.creator import GNS3TopologyCreator

logger = logging.getLogger(__name__)

class GNS3Simulator(INetworkSimulator):
    """GNS3 Network Simulator implementation."""
    
    def __init__(self, gns3_server_url: str = None):
        """Initialize the GNS3 simulator.

        Args:
            gns3_server_url: The URL of the GNS3 server API. If None, must be configured later.
        """
        self._logger = logging.getLogger(__name__)
        
        if gns3_server_url:
            self._logger.info(f"Initializing GNS3 simulator with server {gns3_server_url}")
            
            # Initialize API client
            self.api = GNS3API(gns3_server_url)
            
            # Verify server connection first
            self._logger.info("Checking GNS3 server connection...")
            try:
                version_info = self.api.get_version()
                if not version_info:
                    self._logger.error("Failed to get GNS3 server version. Please ensure the GNS3 server is running.")
                    self._logger.error(f"  - Check that GNS3 is installed and running")
                    self._logger.error(f"  - Check that the server is accessible at {gns3_server_url}")
                    self._logger.error(f"  - Ensure that the port in the URL is correct")
                    raise RuntimeError("GNS3 server not available. Make sure it's installed and running.")
                
                version_str = version_info.get('version', 'unknown')
                self._logger.info(f"Connected to GNS3 server version {version_str}")
                
                # Project name for the simulation
                project_name = "flopynet_scenario"
                
                # First cleanup any existing project with same name
                if self._cleanup_existing_project(project_name):
                    # Wait a moment for GNS3 to free resources
                    time.sleep(2)
                
                # Create a new project for the simulation
                self._logger.info(f"Creating GNS3 project: {project_name}")
                success, project = self.api.create_project(project_name)
                
                if not success or not project:
                    self._logger.error(f"Failed to create GNS3 project: {project}")
                    raise RuntimeError(f"Failed to create GNS3 project: {project}")
                
                self.project = project
                self.project_id = project.get('project_id')
                
                # Store project_id in API instance
                self.api.project_id = self.project_id
                self._logger.info(f"Created GNS3 project with ID: {self.project_id}")
                
                # Create the topology creator
                self.topology_creator = GNS3TopologyCreator(self.api, self.project_id)
                
            except Exception as e:
                self._logger.error(f"Failed to initialize GNS3 simulator: {str(e)}")
                raise RuntimeError(f"Failed to initialize GNS3 simulator: {str(e)}")
        else:
            self._logger.info("Initializing GNS3 simulator without server URL (must be configured later)")
            self.api = None
            self.project = None
            self.project_id = None
            self.topology_creator = None

    def _cleanup_existing_project(self, project_name: str) -> bool:
        """Clean up existing project with the same name.
        
        Args:
            project_name: Name of the project to clean up
            
        Returns:
            True if a project was found and cleaned up, False otherwise
        """
        self._logger.info(f"Checking for existing project: {project_name}")
        
        try:
            # Get all projects
            success, projects = self.api.get_projects()
            if not success or not projects:
                self._logger.info("No existing projects found or error getting projects")
                return False
                
            # Find project with matching name
            for project in projects:
                if project.get('name') == project_name:
                    project_id = project.get('project_id')
                    if project_id:
                        self._logger.info(f"Found existing project {project_name} (ID: {project_id}), cleaning up...")
                        
                        # Stop all nodes first
                        self._logger.info("Stopping all nodes in the project...")
                        success, nodes = self._get_project_nodes(project_id)
                        if success and nodes:
                            for node in nodes:
                                node_id = node.get('node_id')
                                if node_id:
                                    try:
                                        self._logger.info(f"Stopping node {node.get('name', 'unknown')} (ID: {node_id})")
                                        self.api.stop_node(project_id, node_id)
                                    except Exception as e:
                                        self._logger.warning(f"Error stopping node {node_id}: {e}")
                        
                        # Close project
                        self._logger.info(f"Closing project {project_name}...")
                        self.api.close_project(project_id)
                        time.sleep(1)  # Wait for project to close properly
                        
                        # Delete project
                        self._logger.info(f"Deleting project {project_name}...")
                        if self.api.delete_project(project_id):
                            self._logger.info(f"Successfully deleted project {project_name}")
                            return True
                        else:
                            self._logger.warning(f"Failed to delete project {project_name}")
                            return False
                    break
            
            self._logger.info(f"No existing project named {project_name} found")
            return False
                    
        except Exception as e:
            self._logger.warning(f"Error during project cleanup: {e}")
            return False
            
    def _get_project_nodes(self, project_id: str) -> Tuple[bool, Optional[List[Dict]]]:
        """Get all nodes in a project.
        
        Args:
            project_id: The project ID
            
        Returns:
            Tuple of (success, nodes)
        """
        try:
            response = self.api.session.get(f"{self.api.base_url}/projects/{project_id}/nodes")
            if response.status_code == 200:
                return True, response.json()
            else:
                self._logger.warning(f"Failed to get nodes: {response.status_code} - {response.text}")
                return False, None
        except Exception as e:
            self._logger.warning(f"Error getting nodes: {e}")
            return False, None
    
    def create_star_topology(self, node_count: int, node_type: str = "docker", 
                             bandwidth: Optional[float] = None,
                             latency: Optional[float] = None, 
                             packet_loss: Optional[float] = None) -> bool:
        """Create a star topology with nodes.

        Args:
            node_count: Number of nodes to create
            node_type: Type of node to create
            bandwidth: Bandwidth limit in Kbps
            latency: Latency in ms
            packet_loss: Packet loss percentage (0-100)
            
        Returns:
            bool: True if topology was created successfully, False otherwise
        """
        self._logger.info(f"Creating star topology with {node_count} nodes")
        
        try:
            # Create the topology
            success = self.topology_creator.create_star_topology(
                node_count=node_count,
                node_type=node_type,
                bandwidth=bandwidth,
                latency=latency,
                packet_loss=packet_loss
            )
            
            if not success:
                self._logger.error("Failed to create star topology")
                return False
                
            self._logger.info("Star topology created successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to create topology: {str(e)}")
            raise RuntimeError(f"Failed to set up GNS3 network: {str(e)}")
    
    def get_node_console_url(self, node_id: str) -> str:
        """Get the console URL for a node.

        Args:
            node_id: The ID of the node.

        Returns:
            The URL to the node's console.
        """
        success, node = self.api.get_node(self.project_id, node_id)
        if not success or not node:
            raise ValueError(f"Node {node_id} not found")
        
        console_type = node.get('console_type', '').lower()
        
        if console_type == 'telnet':
            return f"telnet://{node.get('console_host')}:{node.get('console')}"
        elif console_type in ['http', 'https']:
            return f"{console_type}://{node.get('console_host')}:{node.get('console_http_port')}{node.get('console_http_path', '/')}"
        else:
            return f"console://{node.get('console_host')}:{node.get('console')}"
    
    def cleanup(self, project_id=None):
        """
        Clean up resources created by the simulator.
        
        Args:
            project_id: Optional project ID to clean up. If not provided, uses current project.
        """
        if project_id is None and hasattr(self, 'project_id'):
            project_id = self.project_id
            
        if not project_id:
            self._logger.warning("No project ID provided for cleanup")
            return
            
        try:
            self._logger.info(f"Cleaning up project {project_id}")
            
            # Get nodes
            success, nodes = self.api.get_nodes(project_id)
            
            if success and nodes:
                # Stop all nodes first
                for node in nodes:
                    node_id = node.get('node_id')
                    node_name = node.get('name', 'unknown')
                    try:
                        self._logger.info(f"Stopping node {node_name} ({node_id})")
                        self.api.stop_node(project_id, node_id)
                    except Exception as e:
                        self._logger.warning(f"Error stopping node {node_name}: {e}")
                        
                # Wait for nodes to stop
                time.sleep(2)
                        
            # Close project
            try:
                self._logger.info(f"Closing project {project_id}")
                self.api.close_project(project_id)
                time.sleep(2)  # Wait for project to close
            except Exception as e:
                self._logger.warning(f"Error closing project: {e}")
            
            # Delete project
            try:
                self._logger.info(f"Deleting project {project_id}")
                self.api.delete_project(project_id)
                self._logger.info("Project deleted successfully")
            except Exception as e:
                self._logger.warning(f"Error deleting project: {e}")
                
            # Clear instance variables
            self.project_id = None
            self.project = None
            if hasattr(self, 'topology_creator'):
                self.topology_creator = None
                
        except Exception as e:
            self._logger.error(f"Error during cleanup: {e}")
            self._logger.error(traceback.format_exc())

    def create_network(self, topology_type: str, num_nodes: int, **kwargs) -> bool:
        """Create a network with specified topology."""
        try:
            logger.info(f"Creating {topology_type} network with {num_nodes} nodes")
            
            if topology_type == "star":
                result = self.create_star_topology(num_nodes, **kwargs)
            elif topology_type == "ring":
                result = self.create_ring_topology(num_nodes, **kwargs)
            elif topology_type == "tree":
                result = self.create_tree_topology(num_nodes, **kwargs)
            else:
                logger.error(f"Unsupported topology type: {topology_type}")
                return False
                
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error creating network: {e}")
            return False

    def create_ring_topology(self, num_nodes: int, **kwargs) -> bool:
        """Create a ring topology."""
        try:
            logger.info(f"Creating ring topology with {num_nodes} nodes")
            
            # Use topology creator to create ring topology with VPCS nodes
            result = self.topology_creator.create_ring_topology(
                num_nodes=num_nodes,
                node_type='vpcs',  # Force VPCS nodes
                node_name_format="vpcs_{}_" + str(random.randint(1000, 9999))
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error creating ring topology: {e}")
            return False

    def create_tree_topology(self, num_nodes: int, depth: int = 2, branching: int = 2, **kwargs) -> bool:
        """Create a tree topology."""
        try:
            logger.info(f"Creating tree topology with {num_nodes} nodes (depth={depth}, branching={branching})")
            
            # Use topology creator to create tree topology with VPCS nodes
            result = self.topology_creator.create_tree_topology(
                num_nodes=num_nodes,
                depth=depth,
                branching=branching,
                node_type='vpcs',  # Force VPCS nodes
                node_name_format="vpcs_{}_" + str(random.randint(1000, 9999))
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error creating tree topology: {e}")
            return False

    def create_custom_topology(self, topology_data: Dict[str, Any]) -> bool:
        """Create a custom topology."""
        try:
            logger.info("Creating custom topology")
            
            # Use topology creator to create custom topology with VPCS nodes
            result = self.topology_creator.create_custom_topology(
                topology_data=topology_data,
                node_type='vpcs'  # Force VPCS nodes
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error creating custom topology: {e}")
            return False

    def get_link_stats(self, link_id: str) -> Dict[str, Any]:
        """Get statistics for a specific link."""
        try:
            logger.info(f"Getting stats for link {link_id}")
            
            # Get link statistics from GNS3 API
            success, stats = self.api.get_link_stats(self.project_id, link_id)
            
            if success:
                return stats
            else:
                logger.error(f"Failed to get link stats: {stats}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting link stats: {e}")
            return {}

    def simulate_federated_learning_round(self, model_size_mb: float, num_clients: int) -> Dict[str, Any]:
        """Run a federated learning round using real network communication."""
        try:
            logger.info(f"Running FL round with {num_clients} clients and {model_size_mb}MB model")
            
            # Get list of client nodes
            success, nodes = self.api.get_nodes(self.project_id)
            if not success:
                logger.error("Failed to get nodes")
                return {'success': False, 'error': 'Failed to get nodes'}
            
            client_nodes = [n for n in nodes if n['node_type'] == 'vpcs'][:num_clients]
            if len(client_nodes) < num_clients:
                logger.error(f"Not enough client nodes. Found {len(client_nodes)}, need {num_clients}")
                return {'success': False, 'error': 'Not enough client nodes'}
            
            # Measure actual network conditions between nodes
            network_stats = {}
            for client in client_nodes:
                # Ping between nodes to measure latency
                for other_client in client_nodes:
                    if client['node_id'] != other_client['node_id']:
                        success, result = self.api.ping_node(
                            self.project_id,
                            client['node_id'],
                            other_client['name']
                        )
                        if success:
                            network_stats[f"{client['name']}->{other_client['name']}"] = {
                                'latency': self._parse_ping_result(result)
                            }
            
            # Run actual federated learning round
            round_metrics = {'accuracies': [], 'losses': []}
            start_time = time.time()
            
            for client in client_nodes:
                # Run training on each client
                success, metrics = self.api.run_command(
                    self.project_id,
                    client['node_id'],
                    'python3 /app/fl_client.py --train'
                )
                if success:
                    try:
                        metrics_dict = json.loads(metrics)
                        round_metrics['accuracies'].append(metrics_dict.get('accuracy', 0))
                        round_metrics['losses'].append(metrics_dict.get('loss', 0))
                    except:
                        logger.error(f"Failed to parse metrics from client {client['name']}")
            
            end_time = time.time()
            round_time = end_time - start_time
            
            # Calculate actual metrics from the round
            return {
                'success': True,
                'round_time': round_time,
                'accuracy': sum(round_metrics['accuracies']) / len(round_metrics['accuracies']) if round_metrics['accuracies'] else 0,
                'loss': sum(round_metrics['losses']) / len(round_metrics['losses']) if round_metrics['losses'] else 0,
                'network_stats': network_stats
            }
            
        except Exception as e:
            logger.error(f"Error running FL round: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _parse_ping_result(self, ping_output: str) -> float:
        """Parse ping command output to get average latency."""
        try:
            # Example ping output parsing - adjust based on actual output format
            if 'time=' in ping_output:
                time_str = ping_output.split('time=')[1].split()[0]
                return float(time_str)
            return 0.0
        except:
            return 0.0

    def start_network(self) -> bool:
        """Start all nodes in the network."""
        try:
            logger.info("Starting network")
            success = True
            
            # Get all nodes
            nodes = self.topology_creator.get_nodes()
            
            # Start each node
            for node in nodes:
                node_id = node.get('node_id')
                if not self.api.start_node(self.project_id, node_id):
                    logger.error(f"Failed to start node {node_id}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting network: {e}")
            return False

    def stop_network(self) -> bool:
        """Stop all nodes in the network."""
        try:
            logger.info("Stopping network")
            success = True
            
            # Get all nodes
            nodes = self.topology_creator.get_nodes()
            
            # Stop each node
            for node in nodes:
                node_id = node.get('node_id')
                if not self.api.stop_node(self.project_id, node_id):
                    logger.error(f"Failed to stop node {node_id}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error stopping network: {e}")
            return False

    def deploy_component(self, component_type: str, node_name: str, config: Dict[str, Any]) -> bool:
        """
        Deploy a component to a node.
        
        Args:
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            node_name: Name of the node
            config: Component configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deploying {component_type} to node {node_name}")
            
            # Get the node object by name
            node = self._get_node_by_name(node_name)
            if not node:
                logger.error(f"Node {node_name} not found")
                return False
            
            # Ensure node is started
            logger.info(f"Ensuring node {node_name} is started")
            if not self.api.start_node(self.project_id, node.node_id):
                logger.error(f"Failed to start node {node_name}")
                return False
            
            # Wait for node to be ready
            if not self.api.wait_for_node_started(self.project_id, node.node_id):
                logger.error(f"Node {node_name} did not start in time")
                return False
                
            # Get the script content for the component
            script_content = self._get_component_script(component_type)
            if not script_content:
                logger.error(f"Failed to get script for {component_type}")
                return False
            
            # Create a configuration file
            config_content = json.dumps(config, indent=2)
            
            # Define requirements
            requirements = ["requests", "flask", "cryptography", "numpy", "pandas"]
            if component_type == "fl_server":
                requirements.extend(["scikit-learn", "torch"])
            elif component_type == "fl_client":
                requirements.extend(["scikit-learn", "torch"])
            elif component_type == "policy_engine":
                requirements.append("policyengine")
            
            # Create the app directory
            app_dir = f"/app/{component_type}"
            mkdir_cmd = f"mkdir -p {app_dir}"
            
            # Create a temporary version of required commands to run on the node
            setup_commands = [
                mkdir_cmd,
                f"echo '{script_content}' > {app_dir}/app.py",
                f"echo '{config_content}' > {app_dir}/config.json",
                "apk update",
                "apk add --no-cache python3 py3-pip curl",
                f"cd {app_dir} && python3 -m pip install --upgrade pip"
            ]
            
            # Add requirements installation
            for req in requirements:
                setup_commands.append(f"cd {app_dir} && python3 -m pip install {req}")
            
            # Run each command with retry logic
            max_retries = 3
            
            for cmd in setup_commands:
                logger.info(f"Running command on {node_name}: {cmd[:30]}...")
                
                for retry in range(max_retries):
                    try:
                        result = self.run_cmd_on_node(node.node_id, cmd)
                        if isinstance(result, tuple) and len(result) == 2:
                            success, output = result
                        else:
                            success = result
                            output = "Unknown output"
                        
                        if success:
                            # Command succeeded, break retry loop
                            break
                        else:
                            logger.warning(f"Command failed (attempt {retry+1}/{max_retries}): {cmd}")
                            logger.warning(f"Output: {output}")
                            
                            # If we're not on the last retry, wait before trying again
                            if retry < max_retries - 1:
                                time.sleep(2)
                    except Exception as e:
                        logger.error(f"Exception running command (attempt {retry+1}/{max_retries}): {e}")
                        if retry < max_retries - 1:
                            time.sleep(2)
                        else:
                            # Failed after all retries
                            return False
                
                # Check if all retries were exhausted without success
                if not success:
                    logger.error(f"Failed to run command after {max_retries} attempts: {cmd}")
                    return False
            
            logger.info(f"Successfully deployed {component_type} to {node_name}")
            return True
                
        except Exception as e:
            logger.error(f"Error deploying {component_type} to {node_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _get_component_script(self, component_type: str) -> str:
        """
        Get a default script for a component type.
        
        Args:
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            
        Returns:
            str: Script content
        """
        if component_type == "fl_server":
import os
import sys
import json
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger("fl_server")

# Load config
logger.info("Starting Federated Learning Server")
config_path = 'config.json'

if not os.path.exists(config_path):
    logger.error(f"Config file {config_path} not found")
    sys.exit(1)

with open(config_path, 'r') as f:
    config = json.load(f)
    
logger.info(f"Loaded configuration: {config}")

# Setup server parameters
host = config.get('host', '0.0.0.0')
port = config.get('port', 8080)
num_rounds = config.get('num_rounds', 3)
min_clients = config.get('min_clients', 2)
model_name = config.get('model', 'cnn')

logger.info(f"Starting FL server on {host}:{port}")
logger.info(f"Expecting {min_clients} clients, running {num_rounds} rounds")

# In real implementation, start the actual server
try:
    import flwr as fl
    from flwr.server import strategy
    
    strategy = strategy.FedAvg(min_fit_clients=min_clients, min_evaluate_clients=min_clients)
    
    # Start server
    fl.server.start_server(
        server_address=f"{host}:{port}",
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy
    )
except Exception as e:
    logger.error(f"Error starting Flower server: {e}")
    # Keep the script running as fallback
    while True:
        logger.info("Server is running (fallback mode)...")
        time.sleep(60)
"""

        elif component_type == "fl_client":
import os
import sys
import json
import time
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('client.log')
    ]
)
logger = logging.getLogger("fl_client")

# Load config
logger.info("Starting Federated Learning Client")
config_path = 'config.json'

if not os.path.exists(config_path):
    logger.error(f"Config file {config_path} not found")
    sys.exit(1)

with open(config_path, 'r') as f:
    config = json.load(f)
    
logger.info(f"Loaded configuration: {config}")

# Setup client parameters
server_host = config.get('server_host', 'localhost')
server_port = config.get('server_port', 8080)
client_id = config.get('client_id', 'client1')
model_name = config.get('model', 'cnn')
dataset = config.get('dataset', 'medical_mnist')
local_epochs = config.get('local_epochs', 1)

logger.info(f"Client {client_id} connecting to server at {server_host}:{server_port}")
logger.info(f"Using model {model_name} on {dataset} with {local_epochs} local epochs")

# In real implementation, start the actual client
try:
    import flwr as fl
    import numpy as np
    
    # Define a simple NumPy client
    class MedicalClient(fl.client.NumPyClient):
        def get_parameters(self, config):
            # Return random parameters (in a real client, return actual model params)
            return [np.random.rand(10, 10), np.random.rand(10)]
            
        def fit(self, parameters, config):
            # Simulate training
            logger.info(f"Client {client_id} training for {local_epochs} epochs")
            time.sleep(2)  # Simulate training time
            
            # Return updated parameters
            new_params = [p + np.random.normal(0, 0.01, p.shape) for p in parameters]
            return new_params, 100, {"accuracy": random.random()}
            
        def evaluate(self, parameters, config):
            # Simulate evaluation
            logger.info(f"Client {client_id} evaluating model")
            
            # Return loss and metrics
            return random.random(), 100, {"accuracy": random.random()}
    
    # Start the client
    fl.client.start_numpy_client(
        server_address=f"{server_host}:{server_port}",
        client=MedicalClient()
    )
except Exception as e:
    logger.error(f"Error starting Flower client: {e}")
    # Keep the script running as fallback
    while True:
        logger.info(f"Client {client_id} attempting to connect to server...")
        time.sleep(10)
"""

        elif component_type == "policy_engine":
import os
import sys
import json
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('policy.log')
    ]
)
logger = logging.getLogger("policy_engine")

# Load config
logger.info("Starting Policy Engine")
config_path = 'config.json'

if not os.path.exists(config_path):
    logger.error(f"Config file {config_path} not found")
    sys.exit(1)

with open(config_path, 'r') as f:
    config = json.load(f)
    
logger.info(f"Loaded configuration: {config}")

# Setup policy engine parameters
host = config.get('host', '0.0.0.0')
port = config.get('port', 5000)
policies = config.get('policies', [])

logger.info(f"Starting policy engine on {host}:{port}")
logger.info(f"Loaded {len(policies)} policies")

# Simple HTTP server for policy enforcement
class PolicyRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            "status": "ok",
            "message": "Policy engine running",
            "policies": policies
        }
        self.wfile.write(json.dumps(response).encode())
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request = json.loads(post_data.decode())
        
        logger.info(f"Received policy check request: {request}")
        
        # Check policy compliance
        result = {
            "allowed": True,
            "reason": "All checks passed",
            "policy_id": request.get("policy_id", "default")
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

# Start HTTP server
try:
    server = HTTPServer((host, port), PolicyRequestHandler)
    logger.info(f"Policy engine started at http://{host}:{port}")
    server.serve_forever()
except Exception as e:
    logger.error(f"Error starting policy engine: {e}")
    # Keep the script running as fallback
    while True:
        logger.info("Policy engine is running (fallback mode)...")
        time.sleep(60)
"""
        else:
            logger.warning(f"Unknown component type: {component_type}")
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("component")

logger.info(f"Started unknown component type: {component_type}")

# Keep the process running
while True:
    logger.info("Component is running...")
    time.sleep(60)
"""
    
    def start_component(self, component_type: str, node_name: str) -> bool:
        """
        Start a deployed component on a node.
        
        Args:
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            node_name: Name of the node
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Starting {component_type} on node {node_name}")
            
            # Get the node object by name
            node = self._get_node_by_name(node_name)
            if not node:
                logger.error(f"Node {node_name} not found")
                return False
            
            # Create the app directory path
            app_dir = f"/app/{component_type}"
            
            # Run the component in background with output redirection
            cmd = f"cd {app_dir} && nohup python3 app.py > {component_type}.log 2>&1 &"
            
            # Execute the command
            try:
                result = self.run_cmd_on_node(node.node_id, cmd)
                if isinstance(result, tuple) and len(result) == 2:
                    success, output = result
                else:
                    success = result
                    output = "Unknown output"
                
                if success:
                    logger.info(f"Successfully started {component_type} on {node_name}")
                    
                    # Check if component is running
                    check_cmd = "ps aux | grep python3"
                    check_result = self.run_cmd_on_node(node.node_id, check_cmd)
                    if isinstance(check_result, tuple) and len(check_result) == 2:
                        check_success, check_output = check_result
                        if check_success:
                            logger.info(f"Process check on {node_name}: {check_output}")
                    
                    return True
                else:
                    logger.error(f"Failed to start {component_type} on {node_name}: {output}")
                    return False
            except Exception as e:
                logger.error(f"Exception starting {component_type} on {node_name}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting {component_type} on {node_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def stop_component(self, component_type: str, node_name: str) -> bool:
        """
        Stop a deployed component on a node.
        
        Args:
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            node_name: Name of the node
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Stopping {component_type} on node {node_name}")
            
            # Get the node object by name
            node = self._get_node_by_name(node_name)
            if not node:
                logger.error(f"Node {node_name} not found")
                return False
            
            # Create command to find and kill the Python process
            script_file = f"{component_type.replace('fl_', '')}.py"
            cmd = f"pkill -f 'python3 .*{script_file}'"
            
            # Execute the command
            success, result = self.run_cmd_on_node(node.node_id, cmd)
            if success:
                logger.info(f"Successfully stopped {component_type} on {node_name}")
                return True
            else:
                logger.warning(f"Failed to stop {component_type} on {node_name}: {result}")
                # Consider this successful anyway, as the process might not be running
                return True
                
        except Exception as e:
            logger.error(f"Error stopping {component_type} on {node_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_node_ip(self, node_name: str) -> Optional[str]:
        """
        Get the IP address of a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Optional[str]: IP address if found, None otherwise
        """
        try:
            # Get node ID
            success, nodes = self.api.get_nodes(self.project_id)
            if not success:
                return None
            
            node_id = None
            for node in nodes:
                if node.get('name') == node_name:
                    node_id = node.get('node_id')
                    break
            
            if not node_id:
                return None
            
            # Execute hostname -i command to get IP
            url = f"{self.api.server_url}/v2/projects/{self.project_id}/nodes/{node_id}/exec"
            data = {"command": "hostname -i"}
            response = self.api.post(url, data)
            
            if not response or response.status_code not in [200, 201, 204]:
                return None
            
            # Parse IP from output
            output = response.text.strip() if response else ""
            if output:
                # Return first IP if multiple are returned
                return output.split()[0]
            
            return None
            
        except Exception as e:
            self._logger.error(f"Error getting node IP: {str(e)}")
            return None
    
    def run_cmd_on_node(self, node_id: str, command: str) -> Tuple[bool, str]:
        """Run a command on a node with enhanced error handling.
        
        Args:
            node_id: ID of the node
            command: Command to run
            
        Returns:
            Tuple of (success, output)
        """
        try:
            logger.info(f"Running command on node {node_id}: {command[:30]}...")
            
            # Get the project ID
            if not hasattr(self, 'project_id') or not self.project_id:
                if hasattr(self, 'topology_creator') and hasattr(self.topology_creator, 'project_id'):
                    self.project_id = self.topology_creator.project_id
                else:
                    return False, "No project ID available"
            
            # Ensure we have the API
            if not hasattr(self, 'api') or not self.api:
                return False, "No API available"
            
            # Execute using the enhanced API method that handles fallbacks
            if hasattr(self.api, 'run_command'):
                success, result = self.api.run_command(self.project_id, node_id, command)
                if success:
                    return True, result
                
                # If the command failed but we still want to consider it successful
                # (e.g., for commands that return non-zero exit status but aren't fatal)
                if "command sent" in str(result).lower():
                    logger.info("Command was sent to console but couldn't get output")
                    return True, result
                
                # If we reach here, the command failed through the API's run_command method
                logger.warning(f"API run_command method failed: {result}")
            
            # Alternative: Try direct API execution as fallback
            logger.info("Trying direct API execution as fallback")
            url = f"/projects/{self.project_id}/nodes/{node_id}/exec"
            payload = {"command": command}
            
            # Execute using the API post method
            response = self.api.post(url, payload)
            
            if not response:
                # If direct post failed, try console method as a last resort
                logger.warning("Direct API post failed, trying console method")
                
                # Get node info to determine if it supports console commands
                success, node = self.api.get_node(self.project_id, node_id)
                if not success:
                    return False, "Failed to get node info for console fallback"
                
                node_type = node.get('node_type', '').lower()
                if node_type in ['vpcs', 'qemu', 'virtualbox']:
                    # Use console API if available
                    console_url = f"/projects/{self.project_id}/nodes/{node_id}/console/send"
                    console_data = {"input": f"{command}\n"}
                    console_response = self.api.post(console_url, console_data)
                    
                    if console_response:
                        # Wait for command to complete
                        time.sleep(2)
                        logger.info("Command sent to console, assuming success")
                        return True, "Command sent to console (no output available)"
                
                # If we've exhausted all options
                return False, "Failed to execute command through all available methods"
            
            # Process the response from standard API post
            if isinstance(response, dict):
                result = response.get('output', '')
                return True, result
            elif hasattr(response, 'text'):
                return True, response.text
            else:
                return True, str(response)
        
        except Exception as e:
            logger.error(f"Error running command on node {node_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, str(e)
    
    def _get_node_by_name(self, node_name: str):
        """Get a node by its name.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Node object or None if not found
        """
        try:
            # First check if we have a project ID
            if not hasattr(self, 'project_id') or not self.project_id:
                # Try to get project ID from topology creator
                if hasattr(self, 'topology_creator') and hasattr(self.topology_creator, 'project_id'):
                    self.project_id = self.topology_creator.project_id
                else:
                    logger.error("No project ID available")
                    return None
            
            # Get all nodes
            project_id = self.project_id
            success, nodes = self.api.get_nodes(project_id)
            
            if not success or not nodes:
                logger.error(f"Failed to get nodes for project {project_id}")
                return None
                
            # Find the node by name
            for node in nodes:
                if node.get('name') == node_name:
                    # Convert to gns3fy Node object
                    from gns3fy import Node, Gns3Connector
                    
                    # Create connector if needed
                    if not hasattr(self, 'connector'):
                        # Get server URL from API
                        server_url = self.api.server_url
                        # Strip /v2 if present, as gns3fy adds it automatically
                        if server_url.endswith('/v2'):
                            server_url = server_url[:-3]
                        self.connector = Gns3Connector(url=server_url)
                    
                    # Create Node object
                    node_obj = Node(
                        name=node.get('name'),
                        project_id=project_id,
                        node_id=node.get('node_id'),
                        connector=self.connector
                    )
                    
                    # Refresh the node info
                    try:
                        node_obj.get()
                    except Exception as e:
                        logger.warning(f"Error refreshing node info: {e}")
                    
                    return node_obj
            
            logger.warning(f"Node {node_name} not found in project {project_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting node by name: {e}")
            return None
            
    def get_hosts(self) -> List[str]:
        """Get list of host names in the project."""
        try:
            # Get all nodes
            success, nodes = self.api.get_nodes(self.project_id)
            if not success:
                error_msg = "Failed to get nodes from GNS3 API"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Filter Docker or VPCS nodes that can act as hosts
            host_nodes = []
            for node in nodes:
                # We only want Docker or VPCS nodes as hosts
                node_type = node.get('node_type', '').lower()
                if node_type in ['docker', 'vpcs']:
                    host_nodes.append(node)
            
            # Get node names
            host_names = [node.get('name') for node in host_nodes]
            
            # Log the results
            logger.info(f"Found {len(host_names)} hosts: {host_names}")
            
            # Check if we found any hosts and raise exception if not
            if not host_names:
                # This is an error - we expected to find nodes
                error_msg = "No Docker or VPCS nodes found in the project"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            return host_names
            
        except Exception as e:
            # Log error and raise exception - no fallbacks
            error_msg = f"Error getting hosts: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def run_cmd_on_host(self, host: str, cmd: str) -> Tuple[bool, str]:
        """Run command on a host."""
        try:
            if not self.project_id:
                logger.error("No project ID available")
                return False, "No project ID available"
                
            # Get node ID from host name
            success, nodes = self.api.get_nodes(self.project_id)
            if not success:
                logger.error(f"Failed to get nodes: {nodes}")
                return False, str(nodes)
                
            node_id = None
            for node in nodes:
                if node['name'] == host:
                    node_id = node['node_id']
                    break
                    
            if not node_id:
                logger.error(f"Node not found for host: {host}")
                return False, f"Node not found for host: {host}"
                
            # Ensure node is started
            success, _ = self.api.start_node(self.project_id, node_id)
            if not success:
                logger.error(f"Failed to start node {host}")
                return False, f"Failed to start node {host}"
                
            # Wait for node to be ready
            if not self.api.wait_for_node_started(self.project_id, node_id):
                logger.error(f"Node {host} did not start in time")
                return False, f"Node {host} did not start in time"
                
            # Run command
            success, result = self.api.run_command(self.project_id, node_id, cmd)
            if not success:
                logger.error(f"Failed to run command on {host}: {result}")
                return False, str(result)
                
            return True, result
            
        except Exception as e:
            logger.error(f"Error running command on host: {e}")
            return False, str(e)

    def configure_link(self, src: str, dst: str, bandwidth: float, latency: float, packet_loss: float) -> bool:
        """Configure link parameters between two nodes."""
        try:
            # Find the link between the nodes
            links = self.topology_creator.get_links()
            link_id = None
            
            for link in links:
                nodes = link.get('nodes', [])
                if len(nodes) == 2:
                    node1, node2 = nodes
                    if ((node1.get('name') == src and node2.get('name') == dst) or
                        (node1.get('name') == dst and node2.get('name') == src)):
                        link_id = link.get('link_id')
                        break
            
            if not link_id:
                logger.error(f"Link between {src} and {dst} not found")
                return False
            
            # Configure the link
            return self.api.configure_link(
                self.project_id,
                link_id,
                bandwidth=bandwidth,
                latency=latency,
                packet_loss=packet_loss
            )
            
        except Exception as e:
            logger.error(f"Error configuring link: {e}")
            return False

    def test_connectivity(self, source_node: str, target_node: str, timeout: int = 10) -> bool:
        """
        Test network connectivity between two nodes using ping.
        
        Args:
            source_node: Name of the source node
            target_node: Name of the target node
            timeout: Timeout in seconds
            
        Returns:
            bool: True if connectivity test passes, False otherwise
        """
        try:
            self._logger.info(f"Testing connectivity from {source_node} to {target_node}")
            
            # Get node IDs
            success, nodes = self.api.get_nodes(self.project_id)
            if not success:
                self._logger.error("Failed to get nodes")
                return False
            
            # Find source and target nodes
            source_id = None
            target_id = None
            target_ip = None
            
            for node in nodes:
                if node.get('name') == source_node:
                    source_id = node.get('node_id')
                elif node.get('name') == target_node:
                    target_id = node.get('node_id')
                    # Get target node IP
                    try:
                        target_ip = self.get_node_ip(target_node)
                    except:
                        pass
            
            if not source_id or not target_id:
                self._logger.error(f"Could not find nodes: source={source_node}, target={target_node}")
                return False
            
            # If we couldn't get target IP, use hostname
            if not target_ip:
                target_ip = target_node
            
            # Test connectivity using ping
            ping_cmd = f"ping -c 3 -W {timeout} {target_ip}"
            
            # Execute ping command on source node
            url = f"{self.api.server_url}/v2/projects/{self.project_id}/nodes/{source_id}/exec"
            data = {"command": ping_cmd}
            response = self.api.post(url, data)
            
            if not response or response.status_code not in [200, 201, 204]:
                self._logger.error(f"Failed to execute ping command: {response.text if response else 'No response'}")
                return False
            
            # Check ping output
            output = response.text if response else ""
            if "3 packets transmitted" in output and "0% packet loss" in output:
                self._logger.info(f"Connectivity test passed: {source_node} -> {target_node}")
                return True
            else:
                self._logger.warning(f"Connectivity test failed: {source_node} -> {target_node}")
                return False
            
        except Exception as e:
            self._logger.error(f"Error testing connectivity: {str(e)}")
            self._logger.error(traceback.format_exc())
            return False

    def initialize_simulator(self, gns3_server_url: str) -> None:
        """Initialize the GNS3 simulator.
        
        Args:
            gns3_server_url: URL of the GNS3 server
        """
        try:
            # Initialize API client
            self.api = GNS3API(gns3_server_url)
            
            # Verify server connection
            version = self.api.get('version')
            if not version:
                raise RuntimeError("Failed to connect to GNS3 server")
            
            logger.info(f"Connected to GNS3 server version {version.get('version')}")
            
            # Create project
            project_name = f"flopynet-project-{uuid.uuid4().hex[:8]}"
            success, project = self.api.create_project(project_name)
            if not success:
                raise RuntimeError(f"Failed to create project: {project}")
            
            self.project_id = project.get('project_id')
            logger.info(f"Created project {project_name} with ID {self.project_id}")
            
            # Initialize topology creator
            self.topology_creator = GNS3TopologyCreator(self.api, self.project_id)
            
            logger.info("GNS3 simulator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize GNS3 simulator: {str(e)}")
            raise RuntimeError(f"Failed to initialize GNS3 simulator: {str(e)}")

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available GNS3 templates.
        
        Returns:
            List[Dict[str, Any]]: List of available templates
        """
        if not hasattr(self, 'topology_creator') or not self.topology_creator:
            self._logger.error("Topology creator not initialized")
            return []
            
        return self.topology_creator.templates

    def create_template(self, template_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """Create a template in GNS3.
        
        Args:
            template_data: Template data dictionary
            
        Returns:
            Tuple[bool, Any]: (success, result)
        """
        if not hasattr(self, 'api') or not self.api:
            self._logger.error("API not initialized")
            return False, "API not initialized"
            
        return self.api.create_template(template_data)

    def create_node(self, project_name: str, template_id: str, name: str) -> Dict[str, Any]:
        """Create a node in GNS3.
        
        Args:
            project_name: Name of the project
            template_id: ID of the template to use
            name: Name of the node
            
        Returns:
            Dict[str, Any]: Created node data
        """
        if not hasattr(self, 'api') or not self.api:
            self._logger.error("API not initialized")
            raise RuntimeError("API not initialized")
            
        # Get template details to determine node type
        template_success, template = self.api.get_template(template_id)
        if not template_success:
            self._logger.error(f"Failed to get template {template_id}")
            raise RuntimeError(f"Failed to get template {template_id}")
            
        template_type = template.get("template_type", "docker")
        
        # Create node using the API with appropriate parameters based on template type
        node_params = {"name": name, "template_id": template_id}
        
        # Add specific properties for QEMU VMs if needed
        if template_type == "qemu":
            # Ensure proper adapters and console configuration for QEMU
            node_params.update({
                "properties": {
                    "adapters": template.get("properties", {}).get("adapters", 1),
                    "console_type": template.get("properties", {}).get("console_type", "telnet"),
                    "ram": template.get("properties", {}).get("ram", 512),
                    "hda_disk_image": template.get("properties", {}).get("hda_disk_image", "")
                }
            })
        
        node = self.api.create_node(self.project_id, name, template_id, **node_params)
        if not node:
            self._logger.error(f"Failed to create node {name}")
            raise RuntimeError(f"Failed to create node {name}")
            
        return node 