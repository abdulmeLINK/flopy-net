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
Node Manager for Basic Scenario.

This module handles node creation logic for the basic scenario in GNS3,
including template resolution, adapter configuration, and node type handling.
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.networking.gns3.protocols import NodeCreationHost

logger = logging.getLogger(__name__)


class NodeCreationMixin:
    """
    Mixin class providing node creation methods for deployment managers.
    
    This mixin expects the host class to implement NodeCreationHost protocol:
    - logger: logging.Logger instance
    - gns3_manager: GNS3 manager instance with api attribute
    - topology: Dict containing 'nodes' list
    - node_ids: Dict[str, str] mapping node names to IDs
    - _calculate_required_adapters() -> Dict[str, int]
    - _create_environment_variables(node_config) -> Dict
    - _create_ethernet_switch(node_name, template_id, node_config) -> Tuple[bool, Dict]
    
    See src/networking/gns3/protocols.py for the formal protocol definition.
    """
    
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
        if not self._create_switch_nodes(nodes, required_adapters):
            logger.warning("Some switch nodes failed to create")
                
        # Now create the rest of the nodes
        if not self._create_regular_nodes(nodes, required_adapters):
            logger.warning("Some regular nodes failed to create")
                
        # Verify all nodes were created
        expected_nodes = [n['name'] for n in nodes]
        created_nodes = list(self.node_ids.keys())
        missing_nodes = [n for n in expected_nodes if n not in created_nodes]
        
        if missing_nodes:
            logger.error(f"Failed to create the following nodes: {missing_nodes}")
            return False
        
        logger.info(f"Successfully created {len(self.node_ids)} nodes")
        return True
    
    def _create_switch_nodes(self, nodes: List[Dict], required_adapters: Dict[str, int]) -> bool:
        """Create all Ethernet switch nodes first."""
        all_success = True
        
        for node_config in nodes:
            node_name = node_config.get("name")
            service_type = node_config.get("service_type", "").lower()
            template_name = node_config.get("template_name")
            
            if service_type != "switch" or template_name != "Ethernet switch":
                continue  # Skip non-switch nodes in this pass
                
            # Find the template ID for this node type
            template_id = self._find_template_id(template_name)
            
            if not template_id:
                logger.error(f"Template not found for node {node_name}: {template_name}")
                all_success = False
                continue
            
            # Create the Ethernet switch with our special method
            logger.info(f"Creating Ethernet switch node: {node_name} (template: {template_name})")
            success, node_data = self._create_ethernet_switch(node_name, template_id, node_config)
            
            if not success:
                logger.error(f"Failed to create Ethernet switch node: {node_name}")
                all_success = False
                continue
            
            # Store the node ID for linking later
            node_id = node_data.get('node_id')
            if node_id:
                self.node_ids[node_name] = node_id
                logger.info(f"Created Ethernet switch node: {node_name} (ID: {node_id})")
            else:
                logger.error(f"Node created but no node_id returned: {node_name}")
                all_success = False
                
        return all_success
    
    def _create_regular_nodes(self, nodes: List[Dict], required_adapters: Dict[str, int]) -> bool:
        """Create all non-switch nodes."""
        all_success = True
        
        for node_config in nodes:
            node_name = node_config.get("name")
            service_type = node_config.get("service_type", "").lower()
            template_name = node_config.get("template_name")
            
            # Skip Ethernet switches since we already created them
            if service_type == "switch" and template_name == "Ethernet switch":
                continue
                
            # Skip if node already exists in our list
            if node_name in self.node_ids:
                logger.info(f"Node {node_name} already exists, skipping creation")
                continue
                
            # Find the template ID for this node type
            template_id = self._find_template_id(template_name)
            
            if not template_id:
                logger.error(f"Template not found for node {node_name}: {template_name}")
                all_success = False
                continue
            
            # Build node parameters
            node_params = self._build_node_params(
                node_config, node_name, service_type, template_name, 
                template_id, required_adapters
            )
            
            # Create the node
            success, node_data = self._create_single_node(
                node_name, template_name, node_config, node_params
            )
            
            if not success:
                logger.error(f"Failed to create node: {node_name}")
                all_success = False
                continue
            
            # Store the node ID for linking later
            node_id = node_data.get('node_id')
            if node_id:
                self.node_ids[node_name] = node_id
                logger.info(f"Created node: {node_name} (ID: {node_id})")
            else:
                logger.error(f"Node created but no node_id returned: {node_name}")
                all_success = False
                
        return all_success
    
    def _find_template_id(self, template_name: str) -> Optional[str]:
        """Find template ID by name."""
        success, templates = self.gns3_manager.api._make_request('GET', 'templates')
        
        if success:
            for template in templates:
                if template.get('name') == template_name:
                    return template.get('template_id')
        return None
    
    def _build_node_params(self, node_config: Dict, node_name: str, service_type: str,
                          template_name: str, template_id: str, 
                          required_adapters: Dict[str, int]) -> Dict[str, Any]:
        """Build node creation parameters including adapters, coordinates, environment."""
        node_params = {}
        
        # Add x, y coordinates if available
        if 'x' in node_config:
            node_params['x'] = node_config['x']
        if 'y' in node_config:
            node_params['y'] = node_config['y']
        
        # Handle Cloud nodes specially
        if self._is_cloud_node(node_config, template_name):
            return self._build_cloud_node_params(node_config, node_name, template_id)
        
        # Calculate adapter count
        adapters = self._calculate_node_adapters(
            node_config, node_name, service_type, template_id, required_adapters
        )
        if adapters > 0:
            node_params['adapters'] = adapters
            logger.info(f"Setting {adapters} adapters for {node_name} in node_params")
        
        # Create environment variables dict if needed
        if "environment" in node_config:
            env_vars = self._create_environment_variables(node_config)
            if env_vars:
                node_params['environment'] = env_vars
                
        # Special case for OpenVSwitch
        if service_type == "openvswitch":
            node_params['ports_mapping'] = []
            for port_num in range(16):
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
                node_params['adapters'] = template_adapters
                logger.info(f"Using template adapter count: {template_adapters} for {node_name}")
        
        return node_params
    
    def _is_cloud_node(self, node_config: Dict, template_name: str) -> bool:
        """Check if node is a Cloud type."""
        return (node_config.get("service_type", "").lower() == "cloud" or 
                node_config.get("node_type", "").lower() == "cloud" or
                template_name.lower() == "cloud")
    
    def _build_cloud_node_params(self, node_config: Dict, node_name: str, 
                                  template_id: str) -> Dict[str, Any]:
        """Build parameters for Cloud nodes (minimal properties)."""
        logger.info(f"Setting up Cloud node {node_name} with minimal properties")
        return {
            'name': node_name,
            'template_id': template_id,
            'compute_id': 'local',
            'x': node_config.get('x', 0),
            'y': node_config.get('y', 0),
            'node_type': 'cloud'
        }
    
    def _calculate_node_adapters(self, node_config: Dict, node_name: str, 
                                  service_type: str, template_id: str,
                                  required_adapters: Dict[str, int]) -> int:
        """Calculate the number of adapters needed for a node."""
        adapters_needed = required_adapters.get(node_name, 0)
        current_adapters = 1  # Default
        
        if node_name in required_adapters:
            logger.info(f"Node {node_name} needs {adapters_needed} adapter(s)")
            
            if service_type == "openvswitch":
                current_adapters = self._get_ovs_adapters(template_id, adapters_needed)
            elif service_type == "sdn-controller":
                current_adapters = self._get_sdn_controller_adapters(node_config, adapters_needed)
            elif service_type in ["switch", "ethernet_switch"] and "adapters" in node_config:
                # Ethernet switch port count is handled in _create_ethernet_switch
                return 0
            else:
                current_adapters = self._get_default_adapters(
                    node_config, node_name, service_type, template_id, adapters_needed
                )
        else:
            # Node wasn't in required_adapters, check explicit config or template
            current_adapters = self._get_fallback_adapters(
                node_config, node_name, service_type, template_id
            )
        
        return current_adapters
    
    def _get_ovs_adapters(self, template_id: str, adapters_needed: int) -> int:
        """Get adapter count for OpenVSwitch nodes."""
        success, template = self.gns3_manager.api.get_template(template_id)
        if success and template and 'adapters' in template:
            template_adapters = template.get('adapters', 8)
            adapters = max(adapters_needed, template_adapters)
            logger.info(f"Using OpenVSwitch with {adapters} adapters (template specifies {template_adapters})")
            return adapters
        else:
            adapters = max(adapters_needed, 16)
            logger.info(f"Using default of {adapters} adapters for OpenVSwitch")
            return adapters
    
    def _get_sdn_controller_adapters(self, node_config: Dict, adapters_needed: int) -> int:
        """Get adapter count for SDN controller nodes."""
        explicit_adapters = node_config.get('adapters', 0)
        if explicit_adapters > 0:
            adapters = max(adapters_needed, explicit_adapters)
            logger.info(f"Using SDN controller with {adapters} adapters (topology specifies {explicit_adapters})")
            return adapters
        else:
            adapters = max(adapters_needed, 2)
            logger.info(f"Using default of {adapters} adapters for SDN controller")
            return adapters
    
    def _get_default_adapters(self, node_config: Dict, node_name: str, 
                               service_type: str, template_id: str,
                               adapters_needed: int) -> int:
        """Get adapter count for regular nodes (Docker containers, etc.)."""
        explicit_adapters = node_config.get('adapters', 0)
        if explicit_adapters > 0:
            adapters = max(adapters_needed, explicit_adapters)
            logger.info(f"Using explicitly configured {adapters} adapters for {node_name}")
            return adapters
        
        # Check template for default adapter count
        success, template = self.gns3_manager.api.get_template(template_id)
        if success and template and 'adapters' in template:
            template_adapters = template.get('adapters', 1)
            if template_adapters > 1:
                adapters = max(adapters_needed, template_adapters)
                logger.info(f"Using {adapters} adapters for {node_name} (template default is {template_adapters})")
                return adapters
        
        # Check ports in node config
        if 'ports' in node_config and len(node_config['ports']) > 1:
            min_adapters = len(node_config['ports'])
            logger.info(f"Setting {min_adapters} adapters based on ports config for {node_name}")
            return min_adapters
        
        return adapters_needed if adapters_needed > 0 else 1
    
    def _get_fallback_adapters(self, node_config: Dict, node_name: str,
                                service_type: str, template_id: str) -> int:
        """Get adapter count when node wasn't in required_adapters."""
        explicit_adapters = node_config.get('adapters', 0)
        if explicit_adapters > 0:
            logger.info(f"Setting explicitly configured {explicit_adapters} adapters for {node_name}")
            return explicit_adapters
        
        # Check template for default adapter count
        success, template = self.gns3_manager.api.get_template(template_id)
        if success and template and 'adapters' in template:
            template_adapters = template.get('adapters', 1)
            
            # Service type specific minimums
            if service_type == "openvswitch":
                logger.info(f"Setting default 16 adapters for OpenVSwitch {node_name}")
                return 16
            elif service_type == "sdn-controller":
                logger.info(f"Setting default 2 adapters for SDN controller {node_name}")
                return 2
            elif 'ports' in node_config and len(node_config['ports']) > 1:
                min_adapters = len(node_config['ports'])
                logger.info(f"Setting {min_adapters} adapters based on ports config for {node_name}")
                return min_adapters
            elif template_adapters > 1:
                logger.info(f"Using template's default {template_adapters} adapters for {node_name}")
                return template_adapters
        
        return 0  # Don't set adapters if no specific requirement
    
    def _create_single_node(self, node_name: str, template_name: str, 
                            node_config: Dict, node_params: Dict) -> Tuple[bool, Optional[Dict]]:
        """Create a single node using GNS3Manager."""
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
                node_config=full_node_config,
                environment=full_node_config.get('environment')
            )
            return success, node_data
            
        except Exception as e:
            logger.error(f"Error calling gns3_manager.create_node for {node_name}: {e}")
            logger.debug(traceback.format_exc())
            return False, None
