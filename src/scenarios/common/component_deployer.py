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
Component Deployment Mixin for Base Scenario.

This module provides component deployment functionality for scenarios,
including parallel deployment, health checking, and status verification.
"""

import time
import uuid
import traceback
import logging
from typing import Dict, Any, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed

if TYPE_CHECKING:
    from src.networking.gns3.protocols import ComponentDeploymentHost

logger = logging.getLogger(__name__)


class ComponentDeploymentMixin:
    """
    Mixin class providing component deployment methods for scenarios.
    
    This mixin expects the host class to implement ComponentDeploymentHost protocol:
    - logger: logging.Logger instance
    - simulator: Network simulator with component deployment methods
    - config: Dict containing scenario configuration
    - scenario_id: str
    - project_name: str
    - results_dir: str
    - collector_node_name: Optional[str]
    - collector_internal_ip: Optional[str]
    - collector_external_port: int
    - collector_internal_port: int
    - gns3_ssh_port: int
    - gns3_ssh_user: str
    - gns3_ssh_password: str
    - collector_port_forwarding_active: bool
    
    See src/networking/gns3/protocols.py for the formal protocol definition.
    """
    
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
                    component_type = self._get_component_type_from_name(node_name)
                    if not component_type:
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

            # Setup port forwarding for collector if configured
            self._setup_collector_port_forwarding()

            return True
            
        except Exception as e:
            self.logger.error(f"Error deploying components: {str(e)}")
            return False
    
    def _get_component_type_from_name(self, node_name: str) -> str:
        """Determine component type based on node name."""
        if 'server' in node_name:
            return 'fl_server'
        elif 'client' in node_name:
            return 'fl_client'
        elif 'policy' in node_name:
            return 'policy_engine'
        return ''
    
    def _setup_collector_port_forwarding(self) -> None:
        """Setup port forwarding for collector node if configured."""
        from src.scenarios.common.gns3_utils import manage_socat_port_forwarding
        
        if not self.collector_node_name:
            self.logger.info("Collector node name not specified, skipping port forwarding.")
            return
            
        try:
            if not self.collector_internal_ip:
                self.logger.warning(
                    f"Collector internal IP for node '{self.collector_node_name}' is NOT SET. "
                    f"Skipping port forwarding. Please ensure it's configured."
                )
                return
                
            gns3_host = self.config.get("network", {}).get("gns3", {}).get("host")
            if gns3_host and self.gns3_ssh_user and self.gns3_ssh_password:
                self.logger.info(
                    f"Attempting to start port forwarding for collector: "
                    f"GNS3 Host {gns3_host}:{self.collector_external_port} -> "
                    f"Collector Node {self.collector_internal_ip}:{self.collector_internal_port}"
                )
                success = manage_socat_port_forwarding(
                    gns3_server_ip=gns3_host,
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
        except Exception as e:
            self.logger.error(f"Error during collector port forwarding setup: {e}")
            self.logger.error(traceback.format_exc())
    
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
    
    def _wait_for_component(self, component_type: str, node_name: str, 
                           timeout: int = 120, check_interval: int = 5) -> bool:
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
                    
                    # For Docker nodes, also try a benign exec command as a readiness check
                    if self._check_docker_exec_readiness(node_name):
                        return True
                else:
                    self.logger.info(
                        f"Simulator reports {component_type} on {node_name} NOT YET healthy "
                        f"or check_component_health not available."
                    )

                self.logger.info(
                    f"Waiting for {component_type} on {node_name}... "
                    f"({int(time.time() - start_time)}s / {timeout}s)"
                )
                time.sleep(check_interval)
            
            self.logger.error(f"Timeout waiting for {component_type} on {node_name} to become fully ready.")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for {component_type} on {node_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _check_docker_exec_readiness(self, node_name: str) -> bool:
        """Check if Docker node exec endpoint is ready."""
        node_details = None
        if hasattr(self.simulator, 'get_node_details_by_name'):
            node_details = self.simulator.get_node_details_by_name(node_name)
        elif hasattr(self.simulator, 'get_node_by_name'):
            node_info = self.simulator.get_node_by_name(node_name)
            if node_info:
                node_details = {
                    'node_type': node_info.get('node_type') if hasattr(node_info, 'get') else 'unknown'
                }

        # Check if it's a docker node and simulator has execute_command_on_node
        if node_details and node_details.get('node_type') == 'docker' and \
           hasattr(self.simulator, 'execute_command_on_node'):
            self.logger.info(f"Attempting GNS3 exec readiness check for Docker node {node_name}...")
            try:
                self.simulator.execute_command_on_node(node_name, "pwd")
                self.logger.info(f"GNS3 exec readiness check PASSED for {node_name}.")
                return True
            except Exception as exec_e:
                self.logger.warning(
                    f"GNS3 exec readiness check for {node_name} failed: {exec_e}. Retrying..."
                )
                return False
        else:
            # If not Docker, or no exec capability, rely on health check alone
            self.logger.info(f"Node {node_name} is ready (based on simulator health check).")
            return True
    
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
                component_type = self._get_component_type_from_name(node_name)
                if not component_type:
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
