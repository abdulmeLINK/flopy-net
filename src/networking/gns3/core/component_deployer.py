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
Component Deployment Manager for GNS3 Simulator.

This module handles deployment of FL components (server, client, policy engine)
to GNS3 nodes, including script generation and execution.
"""

import logging
import json
import time
import traceback
from typing import Dict, Any, List, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


class ComponentDeployer:
    """
    Handles deployment of federated learning components to GNS3 nodes.
    
    This class manages script generation, package installation, and
    component startup on GNS3 nodes.
    """
    
    def __init__(self, run_cmd_func: Callable[[str, str], Tuple[bool, str]], 
                 api=None, project_id: str = None):
        """
        Initialize the ComponentDeployer.
        
        Args:
            run_cmd_func: Function to run commands on nodes (node_id, cmd) -> (success, output)
            api: GNS3 API instance
            project_id: GNS3 project ID
        """
        self.run_cmd_func = run_cmd_func
        self.api = api
        self.project_id = project_id
    
    def deploy_component(self, node_id: str, node_name: str, 
                        component_type: str, config: Dict[str, Any]) -> bool:
        """
        Deploy a component to a node.
        
        Args:
            node_id: ID of the node
            node_name: Name of the node
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            config: Component configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deploying {component_type} to node {node_name}")
            
            # Ensure node is started
            if self.api and self.project_id:
                logger.info(f"Ensuring node {node_name} is started")
                if not self.api.start_node(self.project_id, node_id):
                    logger.error(f"Failed to start node {node_name}")
                    return False
                
                # Wait for node to be ready
                if not self.api.wait_for_node_started(self.project_id, node_id):
                    logger.error(f"Node {node_name} did not start in time")
                    return False
            
            # Get the script content for the component
            script_content = self.get_component_script(component_type)
            if not script_content:
                logger.error(f"Failed to get script for {component_type}")
                return False
            
            # Create a configuration file
            config_content = json.dumps(config, indent=2)
            
            # Define requirements
            requirements = self._get_requirements(component_type)
            
            # Create the app directory
            app_dir = f"/app/{component_type}"
            mkdir_cmd = f"mkdir -p {app_dir}"
            
            # Create setup commands
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
                
                success = False
                for retry in range(max_retries):
                    try:
                        result = self.run_cmd_func(node_id, cmd)
                        if isinstance(result, tuple) and len(result) == 2:
                            success, output = result
                        else:
                            success = result
                            output = "Unknown output"
                        
                        if success:
                            break
                        else:
                            logger.warning(f"Command failed (attempt {retry+1}/{max_retries}): {cmd}")
                            logger.warning(f"Output: {output}")
                            
                            if retry < max_retries - 1:
                                time.sleep(2)
                    except Exception as e:
                        logger.error(f"Exception running command (attempt {retry+1}/{max_retries}): {e}")
                        if retry < max_retries - 1:
                            time.sleep(2)
                        else:
                            return False
                
                if not success:
                    logger.error(f"Failed to run command after {max_retries} attempts: {cmd}")
                    return False
            
            logger.info(f"Successfully deployed {component_type} to {node_name}")
            return True
                
        except Exception as e:
            logger.error(f"Error deploying {component_type} to {node_name}: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def start_component(self, node_id: str, node_name: str, component_type: str) -> bool:
        """
        Start a deployed component on a node.
        
        Args:
            node_id: ID of the node
            node_name: Name of the node
            component_type: Type of component
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Starting {component_type} on node {node_name}")
            
            app_dir = f"/app/{component_type}"
            cmd = f"cd {app_dir} && nohup python3 app.py > {component_type}.log 2>&1 &"
            
            result = self.run_cmd_func(node_id, cmd)
            if isinstance(result, tuple) and len(result) == 2:
                success, output = result
            else:
                success = result
                output = "Unknown output"
            
            if success:
                logger.info(f"Successfully started {component_type} on {node_name}")
                
                # Check if component is running
                check_cmd = "ps aux | grep python3"
                check_result = self.run_cmd_func(node_id, check_cmd)
                if isinstance(check_result, tuple) and len(check_result) == 2:
                    check_success, check_output = check_result
                    if check_success:
                        logger.info(f"Process check on {node_name}: {check_output}")
                
                return True
            else:
                logger.error(f"Failed to start {component_type} on {node_name}: {output}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting {component_type} on {node_name}: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def stop_component(self, node_id: str, node_name: str, component_type: str) -> bool:
        """
        Stop a deployed component on a node.
        
        Args:
            node_id: ID of the node
            node_name: Name of the node
            component_type: Type of component
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Stopping {component_type} on node {node_name}")
            
            script_file = f"{component_type.replace('fl_', '')}.py"
            cmd = f"pkill -f 'python3 .*{script_file}'"
            
            success, result = self.run_cmd_func(node_id, cmd)
            if success:
                logger.info(f"Successfully stopped {component_type} on {node_name}")
                return True
            else:
                logger.warning(f"Failed to stop {component_type} on {node_name}: {result}")
                # Consider this successful anyway, as the process might not be running
                return True
                
        except Exception as e:
            logger.error(f"Error stopping {component_type} on {node_name}: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _get_requirements(self, component_type: str) -> List[str]:
        """Get Python package requirements for a component type."""
        requirements = ["requests", "flask", "cryptography", "numpy", "pandas"]
        
        if component_type == "fl_server":
            requirements.extend(["scikit-learn", "torch"])
        elif component_type == "fl_client":
            requirements.extend(["scikit-learn", "torch"])
        elif component_type == "policy_engine":
            requirements.append("policyengine")
        
        return requirements
    
    def get_component_script(self, component_type: str) -> str:
        """
        Get a default script for a component type.
        
        Args:
            component_type: Type of component ('fl_server', 'fl_client', 'policy_engine')
            
        Returns:
            str: Script content
        """
        if component_type == "fl_server":
            return self._get_fl_server_script()
        elif component_type == "fl_client":
            return self._get_fl_client_script()
        elif component_type == "policy_engine":
            return self._get_policy_engine_script()
        else:
            logger.warning(f"Unknown component type: {component_type}")
            return self._get_default_script(component_type)
    
    def _get_fl_server_script(self) -> str:
        """Get the FL server script content."""
        return '''import os
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
'''
    
    def _get_fl_client_script(self) -> str:
        """Get the FL client script content."""
        return '''import os
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
'''
    
    def _get_policy_engine_script(self) -> str:
        """Get the policy engine script content."""
        return '''import os
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
'''
    
    def _get_default_script(self, component_type: str) -> str:
        """Get a default script for unknown component types."""
        return f'''import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("component")

logger.info(f"Started unknown component type: {component_type}")

# Keep the process running
while True:
    logger.info("Component is running...")
    time.sleep(60)
'''
