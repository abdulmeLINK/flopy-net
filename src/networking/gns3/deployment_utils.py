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
Deployment utilities for GNS3.

This module provides utilities for preparing deployment packages for GNS3 nodes.
"""

import os
import shutil
import logging
import json
import tempfile
import zipfile
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deployment_utils")

class DeploymentPreparer:
    """Prepares deployment packages for GNS3 nodes."""
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the deployment preparer.
        
        Args:
            output_dir: Directory to store deployment packages
        """
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "gns3_deployments")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Initialized deployment preparer with output directory: {self.output_dir}")
    
    def prepare_package(self, component_type: str, config: Dict[str, Any], package_name: str = None) -> Optional[str]:
        """
        Prepare a deployment package.
        
        Args:
            component_type: Type of component (fl_client, fl_server, policy_engine, sdn_controller)
            config: Component configuration
            package_name: Name of the package (if None, will be generated)
            
        Returns:
            Path to the prepared package, or None if preparation failed
        """
        try:
            # Create a temporary directory for the package
            package_dir = tempfile.mkdtemp(prefix=f"{component_type}_")
            
            # Get the component files
            files = self._get_component_files(component_type)
            
            # Copy files to the package directory
            for src_file, dst_file in files.items():
                dst_path = os.path.join(package_dir, dst_file)
                
                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # Copy the file
                if os.path.exists(src_file):
                    shutil.copy2(src_file, dst_path)
                    logger.info(f"Copied {src_file} to {dst_path}")
                else:
                    logger.warning(f"Source file not found: {src_file}")
            
            # Create config file
            config_path = os.path.join(package_dir, "config.json")
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            # Create deployment script
            self._create_deployment_script(package_dir, component_type)
            
            # Create package ZIP file
            if not package_name:
                package_name = f"{component_type}_{os.path.basename(package_dir)}.zip"
            
            package_path = os.path.join(self.output_dir, package_name)
            
            with zipfile.ZipFile(package_path, "w") as zipf:
                for root, _, files in os.walk(package_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Created deployment package: {package_path}")
            
            # Clean up temporary directory
            shutil.rmtree(package_dir)
            
            return package_path
        
        except Exception as e:
            logger.error(f"Error preparing deployment package: {e}")
            return None
    
    def _get_component_files(self, component_type: str) -> Dict[str, str]:
        """
        Get the list of files needed for a component.
        
        Args:
            component_type: Type of component
            
        Returns:
            Dict mapping source file path to destination file path
        """
        # Base directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        
        if component_type == "fl_client":
            return {
                os.path.join(base_dir, "src/fl/client/fl_client.py"): "fl_client.py",
                os.path.join(base_dir, "src/fl/common/model_handler.py"): "model_handler.py",
                os.path.join(base_dir, "src/fl/common/utils.py"): "utils.py",
                os.path.join(base_dir, "src/fl/common/requirements.txt"): "requirements.txt"
            }
        elif component_type == "fl_server":
            return {
                os.path.join(base_dir, "src/fl/server/fl_server.py"): "fl_server.py",
                os.path.join(base_dir, "src/fl/common/model_handler.py"): "model_handler.py",
                os.path.join(base_dir, "src/fl/common/utils.py"): "utils.py",
                os.path.join(base_dir, "src/fl/common/requirements.txt"): "requirements.txt"
            }
        elif component_type == "policy_engine":
            return {
                os.path.join(base_dir, "src/policy_engine/policy_engine.py"): "policy_engine.py",
                os.path.join(base_dir, "src/policy_engine/requirements.txt"): "requirements.txt"
            }
        elif component_type == "sdn_controller":
            return {
                os.path.join(base_dir, "src/networking/sdn/ryu_controller.py"): "ryu_controller.py",
                os.path.join(base_dir, "src/networking/sdn/flow_manager.py"): "flow_manager.py",
                os.path.join(base_dir, "src/networking/sdn/requirements.txt"): "requirements.txt"
            }
        else:
            logger.warning(f"Unknown component type: {component_type}")
            return {}
    
    def _create_deployment_script(self, package_dir: str, component_type: str) -> None:
        """
        Create a deployment script for the package.
        
        Args:
            package_dir: Directory where the package is being prepared
            component_type: Type of component
        """
        if component_type == "fl_client":
            script = """#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Run FL client
python fl_client.py --config config.json
"""
        elif component_type == "fl_server":
            script = """#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Run FL server
python fl_server.py --config config.json
"""
        elif component_type == "policy_engine":
            script = """#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Run policy engine
python policy_engine.py --config config.json
"""
        elif component_type == "sdn_controller":
            script = """#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Run SDN controller
ryu-manager ryu_controller.py
"""
        else:
            logger.warning(f"Unknown component type: {component_type}")
            return
        
        # Write the script to the package directory
        script_path = os.path.join(package_dir, "deploy.sh")
        with open(script_path, "w") as f:
            f.write(script)
        
        # Make the script executable
        os.chmod(script_path, 0o755)


def prepare_fl_client_package(config: Dict[str, Any]) -> Optional[str]:
    """
    Prepare a deployment package for an FL client.
    
    Args:
        config: Client configuration
        
    Returns:
        Path to the prepared package, or None if preparation failed
    """
    preparer = DeploymentPreparer()
    return preparer.prepare_package("fl_client", config)


def prepare_fl_server_package(config: Dict[str, Any]) -> Optional[str]:
    """
    Prepare a deployment package for an FL server.
    
    Args:
        config: Server configuration
        
    Returns:
        Path to the prepared package, or None if preparation failed
    """
    preparer = DeploymentPreparer()
    return preparer.prepare_package("fl_server", config)


def prepare_policy_engine_package(config: Dict[str, Any]) -> Optional[str]:
    """
    Prepare a deployment package for a policy engine.
    
    Args:
        config: Policy engine configuration
        
    Returns:
        Path to the prepared package, or None if preparation failed
    """
    preparer = DeploymentPreparer()
    return preparer.prepare_package("policy_engine", config)


def prepare_sdn_controller_package(config: Dict[str, Any]) -> Optional[str]:
    """
    Prepare a deployment package for an SDN controller.
    
    Args:
        config: SDN controller configuration
        
    Returns:
        Path to the prepared package, or None if preparation failed
    """
    preparer = DeploymentPreparer()
    return preparer.prepare_package("sdn_controller", config)


# Example usage
if __name__ == "__main__":
    # Example FL client configuration
    client_config = {
        "server_host": "10.0.0.1",
        "server_port": 8080,
        "client_id": "client_1",
        "model": "cnn",
        "dataset": "mnist",
        "local_epochs": 1
    }
    
    # Example FL server configuration
    server_config = {
        "host": "0.0.0.0",
        "port": 8080,
        "num_rounds": 3,
        "model": "cnn",
        "dataset": "mnist",
        "min_clients": 2
    }
    
    # Prepare packages
    client_package = prepare_fl_client_package(client_config)
    server_package = prepare_fl_server_package(server_config)
    
    print(f"Prepared client package: {client_package}")
    print(f"Prepared server package: {server_package}") 