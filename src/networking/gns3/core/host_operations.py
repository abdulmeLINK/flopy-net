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
Host Operations Mixin for GNS3 Simulator.

This module provides host-related operations for the GNS3 simulator,
including getting hosts, running commands, and testing connectivity.
"""

import logging
import traceback
from typing import Dict, List, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.networking.gns3.protocols import HostOperationsHost

logger = logging.getLogger(__name__)


class HostOperationsMixin:
    """
    Mixin class providing host operation methods for GNS3 simulator.
    
    This mixin expects the host class to implement HostOperationsHost protocol:
    - api: GNS3APIProtocol client
    - project_id: str - GNS3 project ID
    - topology_creator: GNS3TopologyCreator instance
    - get_node_ip(node_name: str) -> Optional[str]
    
    See src/networking/gns3/protocols.py for the formal protocol definition.
    """
    
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
                error_msg = "No Docker or VPCS nodes found in the project"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            return host_names
            
        except Exception as e:
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

    def configure_link(self, src: str, dst: str, bandwidth: float, 
                       latency: float, packet_loss: float) -> bool:
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
