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
Link Manager for GNS3 topology link creation and management.

This module handles:
- Creating links between nodes in GNS3
- Port conflict detection and resolution
- Adapter calculation and management
"""

import copy
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Set

logger = logging.getLogger(__name__)


class LinkManager:
    """
    Manages link creation and port management for GNS3 topologies.
    
    This class handles:
    - Creating links between nodes according to topology
    - Detecting and resolving port conflicts
    - Calculating required adapters for nodes
    - Managing Ethernet switch ports
    """
    
    def __init__(self, gns3_manager, project_id: str, node_ids: Dict[str, str], 
                 auto_fix_conflicts: bool = True):
        """
        Initialize the link manager.
        
        Args:
            gns3_manager: The GNS3 manager instance with API access
            project_id: The GNS3 project ID
            node_ids: Dictionary mapping node names to their GNS3 node IDs
            auto_fix_conflicts: Whether to automatically fix port conflicts
        """
        self.gns3_manager = gns3_manager
        self.project_id = project_id
        self.node_ids = node_ids
        self.auto_fix_conflicts = auto_fix_conflicts
        self.link_map = {}  # Map of link_name -> link_id
    
    def calculate_required_adapters(self, topology: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate how many adapters each node needs based on links in the topology.
        
        Args:
            topology: The topology configuration dictionary
            
        Returns:
            Dict mapping node names to the number of adapters required
        """
        # Count how many adapters each node needs based on link connections
        adapter_count = {}
        
        links = topology.get("links", [])
        for link in links:
            source = link.get("source")
            target = link.get("target")
            source_adapter = link.get("source_adapter", 0)
            target_adapter = link.get("target_adapter", 0)
            
            # Track highest adapter number used for each node
            if source:
                if source not in adapter_count:
                    adapter_count[source] = 0
                adapter_count[source] = max(adapter_count[source], source_adapter + 1)
            
            if target:
                if target not in adapter_count:
                    adapter_count[target] = 0
                adapter_count[target] = max(adapter_count[target], target_adapter + 1)
        
        return adapter_count
    
    def check_for_port_conflicts(self, links: List[Dict[str, Any]]) -> Dict[str, Dict[int, List[int]]]:
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
    
    def resolve_port_conflicts(self, links: List[Dict[str, Any]], 
                               conflicts: Dict[str, Dict[int, List[int]]]) -> List[Dict[str, Any]]:
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
        remaining_conflicts = self.check_for_port_conflicts(resolved_links)
        if remaining_conflicts:
            logger.warning(f"Could not resolve all port conflicts: {remaining_conflicts}")
            return links  # Return original links if we couldn't resolve everything
        
        return resolved_links
    
    def _find_next_available_adapter(self, node: str, used_adapters: Dict[str, Set[int]]) -> int:
        """
        Find the next available adapter number for a node.
        
        Args:
            node: Node name
            used_adapters: Dictionary of used adapters per node
            
        Returns:
            Next available adapter number
        """
        if node not in used_adapters:
            return 0
        
        # Find the lowest unused number
        adapter = 0
        while adapter in used_adapters[node]:
            adapter += 1
        
        return adapter
    
    def log_node_ports(self, node_id: str, node_name: str) -> None:
        """
        Log the available ports for a node to help with debugging.
        
        Args:
            node_id: GNS3 node ID
            node_name: Human-readable node name
        """
        try:
            success, node_info = self.gns3_manager.api._make_request(
                'GET',
                f'projects/{self.project_id}/nodes/{node_id}'
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
    
    def ensure_switch_ports(self, switch_id: str, min_ports: int) -> bool:
        """
        Ensure an Ethernet switch has at least the required number of ports.
        
        Args:
            switch_id: GNS3 switch node ID
            min_ports: Minimum number of ports required
            
        Returns:
            bool: True if switch has enough ports or was updated successfully
        """
        try:
            # Get current switch configuration
            success, switch_info = self.gns3_manager.api._make_request(
                'GET',
                f'projects/{self.project_id}/nodes/{switch_id}'
            )
            
            if not success or not switch_info:
                logger.error(f"Failed to get switch info for ID {switch_id}")
                return False
            
            # Get current ports
            current_ports = switch_info.get('properties', {}).get('ports_mapping', [])
            current_port_count = len(current_ports)
            
            if current_port_count >= min_ports:
                logger.debug(f"Switch {switch_id} already has {current_port_count} ports (>= {min_ports})")
                return True
            
            # Create new ports mapping with additional ports
            new_ports = list(current_ports)  # Copy existing ports
            for i in range(current_port_count, min_ports):
                new_port = {
                    'name': f'Ethernet{i}',
                    'port_number': i,
                    'type': 'access',
                    'vlan': 1
                }
                new_ports.append(new_port)
            
            # Update switch with new ports
            update_data = {
                'properties': {
                    'ports_mapping': new_ports
                }
            }
            
            logger.info(f"Updating switch {switch_id} from {current_port_count} to {min_ports} ports")
            
            success, update_result = self.gns3_manager.api._make_request(
                'PUT',
                f'projects/{self.project_id}/nodes/{switch_id}',
                json=update_data
            )
            
            if success:
                logger.info(f"Successfully updated switch {switch_id} to {min_ports} ports")
                return True
            else:
                logger.error(f"Failed to update switch ports: {update_result}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating switch ports: {e}")
            return False
    
    def _get_node_ports_map(self, nodes_info: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Build a map of node names to their port information.
        
        Args:
            nodes_info: List of node information from GNS3
            
        Returns:
            Dictionary mapping node names to port information
        """
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
                        f'projects/{self.project_id}/nodes/{node_id}/ports'
                    )
                    if success:
                        node_ports_map[node_name] = {
                            'type': node.get('node_type', 'unknown'),
                            'ports': ports_info
                        }
        
        return node_ports_map
    
    def _validate_port(self, node_name: str, adapter: int, 
                       node_ports_map: Dict[str, Dict[str, Any]]) -> bool:
        """
        Validate that a port exists on a node.
        
        Args:
            node_name: Name of the node
            adapter: Adapter/port number to check
            node_ports_map: Port information map
            
        Returns:
            bool: True if port exists, False otherwise
        """
        if node_name not in node_ports_map:
            return True  # Assume OK if we don't have port info
        
        node_info = node_ports_map[node_name]
        ports = node_info['ports']
        
        if node_info['type'] == 'ethernet_switch':
            # For Ethernet switch, verify the port exists in ports_mapping
            port_exists = any(p.get('port_number') == adapter for p in ports)
            if not port_exists:
                logger.error(f"Port {adapter} not found on Ethernet switch {node_name}")
                logger.error(f"Available ports: {[p.get('port_number') for p in ports]}")
            return port_exists
        else:
            # For regular nodes, check in ports list
            port_exists = any(
                p.get('adapter_number') == adapter or 
                p.get('port_number') == adapter for p in ports
            )
            if not port_exists:
                logger.error(f"Port {adapter} not found on node {node_name}")
                available_ports = []
                for p in ports:
                    a = p.get('adapter_number', -1)
                    port = p.get('port_number', -1)
                    available_ports.append(f'adapter {a}/port {port}')
                logger.error(f"Available ports: {available_ports}")
            return port_exists
    
    def _build_link_config(self, node_id: str, adapter: int, 
                           node_type: str) -> Dict[str, Any]:
        """
        Build the link configuration for a node endpoint.
        
        Args:
            node_id: GNS3 node ID
            adapter: Adapter/port number
            node_type: Type of the node
            
        Returns:
            Dictionary with link configuration
        """
        if node_type == 'ethernet_switch':
            # For Ethernet switch, use port_number for the port number field
            return {
                "node_id": node_id, 
                "port_number": adapter,  # Use adapter as port_number
                "adapter_number": 0      # Use fixed adapter_number=0
            }
        else:
            # For Docker containers, use adapter_number for the adapter field
            return {
                "node_id": node_id, 
                "adapter_number": adapter,  # Use adapter as adapter_number 
                "port_number": 0            # Use fixed port_number=0
            }
    
    def create_link(self, source: str, target: str, 
                    source_adapter: int, target_adapter: int,
                    node_ports_map: Dict[str, Dict[str, Any]],
                    max_retries: int = 2) -> Tuple[bool, Optional[str]]:
        """
        Create a single link between two nodes.
        
        Args:
            source: Source node name
            target: Target node name
            source_adapter: Source adapter number
            target_adapter: Target adapter number
            node_ports_map: Port information map
            max_retries: Maximum number of retries
            
        Returns:
            Tuple of (success, link_id or None)
        """
        source_id = self.node_ids.get(source)
        target_id = self.node_ids.get(target)
        
        if not source_id or not target_id:
            logger.error(f"Node IDs not found for link {source} -> {target}")
            return False, None
        
        retry_count = 0
        while retry_count < max_retries:
            retry_count += 1
            wait_time = 2 ** retry_count  # Exponential backoff
            
            try:
                # Get node info to determine type
                success_src, src_node = self.gns3_manager.api.get_node(self.project_id, source_id)
                success_tgt, tgt_node = self.gns3_manager.api.get_node(self.project_id, target_id)
                
                if not success_src or not success_tgt:
                    logger.error(f"Failed to get node info for link {source} -> {target}. Skipping.")
                    continue
                    
                src_node_type = src_node.get('node_type', '')
                tgt_node_type = tgt_node.get('node_type', '')
                
                # Build link configurations
                src_config = self._build_link_config(source_id, source_adapter, src_node_type)
                tgt_config = self._build_link_config(target_id, target_adapter, tgt_node_type)
                
                nodes_list = [src_config, tgt_config]
                logger.debug(f"Link request data: {nodes_list}")
                
                # Create link
                success, link_data = self.gns3_manager.api.create_link(
                    project_id=self.project_id,
                    nodes=nodes_list
                )
                
                if success:
                    logger.info(f"Link created successfully: {source} -> {target} (attempt {retry_count}/{max_retries})")
                    link_id = link_data.get('link_id') if link_data else None
                    
                    # Store link ID
                    if link_id:
                        link_name = f"{source}_{source_adapter}_to_{target}_{target_adapter}"
                        self.link_map[link_name] = link_id
                        logger.info(f"Stored link ID: {link_name} -> {link_id}")
                    
                    return True, link_id
                else:
                    error_msg = link_data.get('message', 'Unknown error') if isinstance(link_data, dict) else str(link_data)
                    
                    # Check for specific error types
                    if "Port not found" in error_msg:
                        logger.error(f"Port not found error when creating link between {source} and {target}: {error_msg}")
                        self.log_node_ports(source_id, source)
                        self.log_node_ports(target_id, target)
                        
                        # Try to fix ports if possible
                        if retry_count == 1:
                            logger.info(f"Attempting to fix port configuration for {source} and {target}")
                            if "switch" in source.lower() or "ethernet" in source.lower():
                                self.ensure_switch_ports(source_id, source_adapter + 2)
                            if "switch" in target.lower() or "ethernet" in target.lower():
                                self.ensure_switch_ports(target_id, target_adapter + 2)
                    else:
                        logger.error(f"Failed to create link between {source} and {target} (attempt {retry_count}/{max_retries}): {error_msg}")
                    
                    # Wait before retrying
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"Exception creating link between {source} and {target}: {e}")
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        logger.error(f"Failed to create link between {source} and {target} after {max_retries} attempts")
        return False, None
    
    def create_links(self, topology: Dict[str, Any]) -> bool:
        """
        Create all links according to topology.
        
        Args:
            topology: The topology configuration dictionary
            
        Returns:
            bool: True if at least some links were created, False otherwise
        """
        if not topology:
            logger.error("Cannot create links: Topology not available")
            return False
        
        # Get the links from topology
        links = topology.get("links", [])
        if not links:
            logger.warning("No links found in topology")
            return True  # Not an error, just no links to create

        # Check for port conflicts before attempting to create links
        conflicts = self.check_for_port_conflicts(links)
        if conflicts:
            logger.warning(f"Port conflicts detected in topology: {conflicts}")
            if self.auto_fix_conflicts:
                logger.info("Attempting to auto-fix port conflicts...")
                links = self.resolve_port_conflicts(links, conflicts)
            else:
                logger.error("Resolve port conflicts in topology file before continuing")
                return False
        
        # Log node IDs for debugging
        logger.debug(f"Available node IDs for linking: {self.node_ids}")
        if not self.node_ids or len(self.node_ids) == 0:
            logger.error("No nodes have been created yet! Cannot create links without nodes.")
            return False
        
        # Make sure GNS3 can be queried
        if not self.gns3_manager or not self.project_id:
            logger.error("GNS3 manager or project ID not available")
            return False
        
        # Get detailed information about nodes
        node_ports_map = {}
        try:
            success, nodes_info = self.gns3_manager.api.get_nodes(self.project_id)
            if success:
                logger.info(f"Found {len(nodes_info)} nodes in GNS3 project")
                node_ports_map = self._get_node_ports_map(nodes_info)
                logger.info(f"Collected port information for {len(node_ports_map)} nodes")
            else:
                logger.error(f"Failed to get nodes from GNS3: {nodes_info}")
        except Exception as e:
            logger.error(f"Error getting node information: {e}")
        
        # Calculate required adapters for cross-check
        required_adapters = self.calculate_required_adapters(topology)
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
            
            # Validate ports
            source_ports_ok = self._validate_port(source, source_adapter, node_ports_map)
            target_ports_ok = self._validate_port(target, target_adapter, node_ports_map)
            
            # Try to fix switch ports if validation failed
            if not (source_ports_ok and target_ports_ok):
                source_id = self.node_ids[source]
                target_id = self.node_ids[target]
                
                if source in node_ports_map and node_ports_map[source]['type'] == 'ethernet_switch' and not source_ports_ok:
                    self.ensure_switch_ports(source_id, source_adapter + 2)
                
                if target in node_ports_map and node_ports_map[target]['type'] == 'ethernet_switch' and not target_ports_ok:
                    self.ensure_switch_ports(target_id, target_adapter + 2)
                
                # Refresh port info for affected switches
                for node_name in [source, target]:
                    if node_name in self.node_ids and node_name in node_ports_map and node_ports_map[node_name]['type'] == 'ethernet_switch':
                        node_id = self.node_ids[node_name]
                        success, node_info = self.gns3_manager.api.get_node(self.project_id, node_id)
                        if success:
                            ports_mapping = node_info.get('properties', {}).get('ports_mapping', [])
                            if ports_mapping:
                                node_ports_map[node_name]['ports'] = ports_mapping
            
            # Create the link
            success, _ = self.create_link(source, target, source_adapter, target_adapter, node_ports_map)
            if success:
                success_count += 1
                logger.info(f"Successfully created link #{idx+1}: {source} -> {target}")
            else:
                logger.error(f"Failed to create link #{idx+1}: {source} -> {target}")
        
        # Report results
        logger.info(f"Created {success_count} out of {len(links)} links")
        if success_count == 0:
            logger.error("CRITICAL: No links were created successfully!")
        elif success_count < len(links):
            logger.warning(f"Only created {success_count} out of {len(links)} links")
        else:
            logger.info("All links created successfully")
            
        return success_count > 0  # Consider partial success as success
