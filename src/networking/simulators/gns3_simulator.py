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
GNS3 Simulator implementation.

This module provides the GNS3Simulator class that implements the INetworkSimulator interface.
"""

import logging
import traceback
from src.networking.interfaces.network_simulator import INetworkSimulator
from src.networking.gns3.core.simulator import GNS3Simulator as CoreGNS3Simulator

# Configure logging
logger = logging.getLogger(__name__)

class GNS3Simulator(INetworkSimulator):
    """GNS3 Simulator wrapper class that implements the INetworkSimulator interface."""
    
    def __init__(self, gns3_server_url=None, gns3_host=None, gns3_port=None, project_id=None, project_name=None):
        """Initialize GNS3Simulator.
        
        Args:
            gns3_server_url: The URL of the GNS3 server, if None, will construct from host and port
            gns3_host: The host of the GNS3 server
            gns3_port: The port of the GNS3 server
            project_id: Optional existing project ID to use instead of creating a new one
            project_name: Optional existing project name to use
        """
        # If server_url is not provided directly, build it from host and port
        if gns3_server_url is None:
            # Use provided host and port or get from config
            host = gns3_host or "localhost"  # Default to localhost only if host is not specified
            port = gns3_port or 3080  # Default to 3080 only if port is not specified
            gns3_server_url = f"http://{host}:{port}/v2"
            
        # Initialize the core simulator with options to reuse existing project
        if project_id and project_name:
            # Initialize the API client first without creating a project
            from src.networking.gns3.core.api import GNS3API
            api = GNS3API(gns3_server_url)
            
            # Initialize the core simulator without creating a project
            self.simulator = CoreGNS3Simulator(gns3_server_url=None)  # Use None to skip auto-project creation
            
            # Setup the core simulator with the provided project details
            self.simulator.api = api
            self.simulator.project_id = project_id
            self.simulator.project_name = project_name
            
            # Set up the topology creator
            from src.networking.gns3.topology.creator import GNS3TopologyCreator
            self.simulator.topology_creator = GNS3TopologyCreator(api, project_id)
        else:
            # Standard initialization that will create a new project
            self.simulator = CoreGNS3Simulator(gns3_server_url=gns3_server_url)
        
        # Forward properties from the core simulator
        self.project_id = self.simulator.project_id
        self.project = self.simulator.project
        self.api = self.simulator.api
        self.topology_creator = self.simulator.topology_creator
        
    # Forward methods to the core simulator
    def create_star_topology(self, node_count, node_type="docker", template_id=None, bandwidth=None, latency=None, packet_loss=None):
        """Create a star topology with the given node count.
        
        Args:
            node_count (int): Number of nodes in the topology
            node_type (str): Type of node to create
            template_id (str): Optional template ID to use for nodes
            bandwidth (int): Bandwidth in Mbps
            latency (int): Latency in ms
            packet_loss (float): Packet loss as a percentage
            
        Returns:
            bool: True if topology was created successfully, False otherwise
        """
        # ... existing implementation ...
        
    def create_star_topology_with_templates(self, node_count, server_template_id=None, client_template_id=None, 
                                           switch_template_id=None, bandwidth=None, latency=None, packet_loss=None):
        """Create a star topology with custom templates for server and client nodes.
        
        Args:
            node_count (int): Number of nodes in the topology
            server_template_id (str): Template ID for the server node
            client_template_id (str): Template ID for client nodes
            switch_template_id (str): Template ID for the switch node
            bandwidth (int): Bandwidth in Mbps
            latency (int): Latency in ms
            packet_loss (float): Packet loss as a percentage
            
        Returns:
            bool: True if topology was created successfully, False otherwise
        """
        try:
            logger.info(f"Creating star topology with {node_count} nodes using custom templates")
            logger.info(f"Server template: {server_template_id}")
            logger.info(f"Client template: {client_template_id}")
            logger.info(f"Switch template: {switch_template_id}")
            
            # Validate project ID
            if not hasattr(self.simulator, 'project_id') or not self.simulator.project_id:
                logger.error("No project ID set in simulator. Cannot create topology.")
                return False
                
            project_id = self.simulator.project_id
            
            # Create a central switch node
            switch_name = "Switch1"
            switch_params = {
                "name": switch_name,
                "node_type": "ethernet_switch"
            }
            
            # Use custom switch template if provided
            if switch_template_id:
                switch_params = {
                    "name": switch_name,
                    "template_id": switch_template_id
                }
                
            success, switch_node = self.simulator.api._make_request('POST', f'/projects/{project_id}/nodes', json=switch_params)
            
            if not success or not switch_node:
                logger.error(f"Failed to create switch node: {switch_node}")
                return False
                
            logger.info(f"Created switch node: {switch_node.get('name')} (ID: {switch_node.get('node_id')})")
            switch_id = switch_node.get('node_id')
            
            # Create server node
            server_name = "Server"
            server_params = {
                "name": server_name,
                "node_type": "docker",
                "compute_id": "local"
            }
            
            # Use custom server template if provided
            if server_template_id:
                server_params = {
                    "name": server_name,
                    "template_id": server_template_id,
                    "compute_id": "local"
                }
                
            success, server_node = self.simulator.api._make_request('POST', f'/projects/{project_id}/nodes', json=server_params)
            
            if not success or not server_node:
                logger.error(f"Failed to create server node: {server_node}")
                return False
                
            logger.info(f"Created server node: {server_node.get('name')} (ID: {server_node.get('node_id')})")
            server_id = server_node.get('node_id')
            
            # Connect server to switch
            link_params = {
                "nodes": [
                    {
                        "node_id": server_id,
                        "adapter_number": 0,
                        "port_number": 0
                    },
                    {
                        "node_id": switch_id,
                        "adapter_number": 0,
                        "port_number": 0
                    }
                ]
            }
            
            success, link = self.simulator.api._make_request('POST', f'/projects/{project_id}/links', json=link_params)
            
            if not success or not link:
                logger.error(f"Failed to create link between server and switch: {link}")
                return False
                
            logger.info(f"Created link between server and switch: {link.get('link_id')}")
            
            # Create client nodes
            client_nodes = []
            for i in range(node_count):
                client_name = f"Client{i+1}"
                client_params = {
                    "name": client_name,
                    "node_type": "docker",
                    "compute_id": "local"
                }
                
                # Use custom client template if provided
                if client_template_id:
                    client_params = {
                        "name": client_name,
                        "template_id": client_template_id,
                        "compute_id": "local"
                    }
                    
                success, client_node = self.simulator.api._make_request('POST', f'/projects/{project_id}/nodes', json=client_params)
                
                if not success or not client_node:
                    logger.error(f"Failed to create client node {i+1}: {client_node}")
                    continue
                    
                logger.info(f"Created client node: {client_node.get('name')} (ID: {client_node.get('node_id')})")
                client_id = client_node.get('node_id')
                client_nodes.append(client_node)
                
                # Connect client to switch
                link_params = {
                    "nodes": [
                        {
                            "node_id": client_id,
                            "adapter_number": 0,
                            "port_number": 0
                        },
                        {
                            "node_id": switch_id,
                            "adapter_number": 0,
                            "port_number": i+1
                        }
                    ]
                }
                
                success, link = self.simulator.api._make_request('POST', f'/projects/{project_id}/links', json=link_params)
                
                if not success or not link:
                    logger.error(f"Failed to create link between client {i+1} and switch: {link}")
                    continue
                    
                logger.info(f"Created link between client {i+1} and switch: {link.get('link_id')}")
                
                # Configure network parameters on the link if specified
                if bandwidth or latency or packet_loss:
                    link_id = link.get('link_id')
                    link_config = {
                        "filters": {}
                    }
                    
                    if bandwidth:
                        link_config["filters"]["bandwidth"] = {
                            "rate": bandwidth,
                            "unit": "mbps"
                        }
                        
                    if latency:
                        link_config["filters"]["delay"] = {
                            "latency": latency,
                            "unit": "ms"
                        }
                        
                    if packet_loss:
                        link_config["filters"]["packet_loss"] = {
                            "value": packet_loss
                        }
                        
                    success, _ = self.simulator.api._make_request('PUT', f'/projects/{project_id}/links/{link_id}', json=link_config)
                    
                    if success:
                        logger.info(f"Configured network parameters on link {link_id}")
                    else:
                        logger.warning(f"Failed to configure network parameters on link {link_id}")
            
            # Start all nodes
            for node_type, node_id in [("switch", switch_id), ("server", server_id)] + [("client", node.get('node_id')) for node in client_nodes]:
                success, _ = self.simulator.api._make_request('POST', f'/projects/{project_id}/nodes/{node_id}/start')
                
                if success:
                    logger.info(f"Started {node_type} node {node_id}")
                else:
                    logger.warning(f"Failed to start {node_type} node {node_id}")
            
            logger.info(f"Successfully created star topology with {len(client_nodes)} client nodes")
            return True
            
        except Exception as e:
            logger.error(f"Error creating star topology with templates: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def create_ring_topology(self, num_nodes, **kwargs):
        """Create a ring topology."""
        return self.simulator.create_ring_topology(num_nodes, **kwargs)
    
    def create_tree_topology(self, num_nodes, **kwargs):
        """Create a tree topology."""
        return self.simulator.create_tree_topology(num_nodes, **kwargs)
        
    def configure_link(self, src, dst, bandwidth=None, latency=None, packet_loss=None):
        """Configure link parameters."""
        return self.simulator.configure_link(src, dst, bandwidth, latency, packet_loss)
        
    def create_custom_topology(self, topology_data):
        """Create a custom topology with specific nodes and links."""
        return self.simulator.create_custom_topology(topology_data)
        
    def get_hosts(self):
        """Get all hosts in the topology."""
        return self.simulator.get_hosts()
        
    def run_cmd_on_host(self, host, cmd):
        """Run a command on a specific host."""
        return self.simulator.run_cmd_on_host(host, cmd)
        
    def create_network(self, topology_type="star", node_count=3, **kwargs):
        """Create a network with the specified topology type."""
        return self.simulator.create_network(topology_type, node_count, **kwargs)
    
    def get_link_stats(self, link_id):
        """Get statistics for a specific link."""
        return self.simulator.get_link_stats(link_id)
    
    def get_templates(self):
        """Get all available templates from the GNS3 server."""
        return self.simulator.get_templates()
    
    def simulate_federated_learning_round(self, model_size_mb=10, num_clients=3):
        """Simulate a federated learning round."""
        return self.simulator.simulate_federated_learning_round(model_size_mb, num_clients)
    
    def start_network(self):
        """Start the network simulation."""
        return self.simulator.start_network()
    
    def stop_network(self):
        """Stop the network simulation."""
        return self.simulator.stop_network()
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self.simulator, 'cleanup') and callable(getattr(self.simulator, 'cleanup')):
            return self.simulator.cleanup()
        return True

# Re-export the GNS3Simulator class
__all__ = ['GNS3Simulator']