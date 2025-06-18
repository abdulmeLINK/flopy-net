"""
Network Simulator for Federated Learning.

This module provides a wrapper for different network simulator implementations,
such as Mock, Mininet, and GNS3.
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any, Union

from src.core.common.logger import LoggerMixin
from src.networking.interfaces.network_simulator import INetworkSimulator
from src.networking.simulators.mock_simulator import MockSimulator
from src.policy_engine.policy_engine import PolicyEngine

# Import simulator implementations
try:
    from src.networking.simulators.mininet_simulator import MininetSimulator
except ImportError:
    MininetSimulator = None

try:
    from src.networking.simulators.gns3_simulator import GNS3Simulator
except ImportError:
    GNS3Simulator = None

logger = logging.getLogger(__name__)

class NetworkSimulator(LoggerMixin, INetworkSimulator):
    """Wrapper for different network simulator implementations."""
    
    def __init__(self, simulator_type: str = "mock", params: Dict[str, Any] = None):
        """
        Initialize the network simulator.
        
        Args:
            simulator_type: Type of simulator to use (mock, mininet, gns3)
            params: Parameters for the simulator
        """
        self.simulator_type = simulator_type
        self.params = params or {}
        self.simulator = None # Will be created by subclass or explicitly
        self.sdn_controller = None
        self.policy_engine = None
        self.flow_manager = None
        
        logger.info(f"Initialized NetworkSimulator base with type: {simulator_type}")
        logger.warning("Simulator instance creation deferred to subclass or explicit call.")
        logger.info(f"Initialized NetworkSimulator with type: {simulator_type}")
    
    def _check_gns3_running(self, host='localhost', port=3080) -> bool:
        """Check if GNS3 server is running and accessible.
        
        Args:
            host: GNS3 server host
            port: GNS3 server port
            
        Returns:
            bool: True if GNS3 server is running and accessible
        """
        try:
            response = requests.get(f"http://{host}:{port}/v2/version")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def _create_simulator(self, simulator_type: str, params: Dict[str, Any]) -> INetworkSimulator:
        """
        Create a network simulator based on the type.
        
        Args:
            simulator_type: Type of simulator to create
            params: Parameters to pass to the simulator
            
        Returns:
            A network simulator instance
            
        Raises:
            RuntimeError: If the requested simulator type isn't available
        """
        simulator_type = simulator_type.lower()
        
        if simulator_type == "gns3":
            try:
                from src.networking.simulators.gns3_simulator import GNS3Simulator
                
                # Extract GNS3-specific parameters
                gns3_params = {}
                if params:
                    # Map 'server_url' to the correct parameters
                    if 'server_url' in params:
                        server_url = params['server_url']
                        # Parse server_url to get host and port
                        if server_url:
                            import urllib.parse
                            parsed_url = urllib.parse.urlparse(server_url)
                            if parsed_url.netloc:
                                host_port = parsed_url.netloc.split(':')
                                if len(host_port) > 0:
                                    gns3_params['gns3_host'] = host_port[0]
                                if len(host_port) > 1:
                                    try:
                                        gns3_params['gns3_port'] = int(host_port[1])
                                    except (ValueError, TypeError):
                                        # If port is not a valid integer, use default port
                                        gns3_params['gns3_port'] = 3080
                        # Remove server_url to avoid passing it directly
                        params = {k: v for k, v in params.items() if k != 'server_url'}
                    
                    # Copy other parameters
                    for key, value in params.items():
                        if key in ['project_name', 'username', 'password', 'cleanup_timeout']:
                            gns3_params[key] = value
                    
                logger.info(f"Initializing GNS3Simulator with params: {gns3_params}")
                return GNS3Simulator(**gns3_params)
                
            except ImportError:
                logger.error("GNS3 simulator not available")
                raise RuntimeError("GNS3 simulator not available. Please check your installation.")
                
        elif simulator_type == "mininet":
            try:
                from src.networking.simulators.mininet_simulator import MininetSimulator
                
                # Extract Mininet-specific parameters
                mininet_params = {}
                if params:
                    mininet_params.update(params)
                    
                return MininetSimulator(**mininet_params)
            except ImportError:
                logger.error("Mininet simulator not available")
                raise RuntimeError("Mininet simulator not available. Please check your installation.")
                
        elif simulator_type == "mock":
            logger.error("Mock simulator is not allowed as per project policy")
            raise RuntimeError(
                "Mock simulator is not allowed as per project policy. "
                "Use 'gns3' or 'mininet' as the simulator type."
            )
            
        else:
            logger.error(f"Unsupported simulator type: {simulator_type}")
            raise RuntimeError(f"Unsupported simulator type: {simulator_type}")
    
    def _create_sdn_controller(self, sdn_type: str, host: str, port: int, rest_port: int) -> None:
        """
        Create and configure the SDN controller.
        
        Args:
            sdn_type: Type of SDN controller to create (ryu, onos, etc.)
            host: Controller host address
            port: Controller OpenFlow port
            rest_port: Controller REST API port
        """
        try:
            if sdn_type.lower() == "ryu":
                from src.networking.sdn.ryu_controller import RyuController
                
                # Get Ryu app path from parameters if provided
                app_path = params.get("sdn_controller_app_path", None)
                
                # Create Ryu controller
                self.sdn_controller = RyuController(
                    host=host,
                    port=port, 
                    api_url_prefix='/stats',
                    protocol='http', 
                    timeout=30,
                    ofp_version='OpenFlow13'
                )
                
                logger.info(f"Created Ryu SDN controller at {host}:{port}")
                
            elif sdn_type.lower() == "onos":
                # ONOS controller implementation would go here
                logger.warning("ONOS controller not implemented yet. Using mock controller.")
                from src.networking.simulators.mock_simulator import MockSDNController
                self.sdn_controller = MockSDNController()
                
            else:
                logger.warning(f"Unknown SDN controller type: {sdn_type}. Using mock controller.")
                from src.networking.simulators.mock_simulator import MockSDNController
                self.sdn_controller = MockSDNController()
                
        except Exception as e:
            logger.error(f"Error creating SDN controller: {e}")
            self.sdn_controller = None
    
    def _init_policy_engine(self):
        """Initialize the policy engine and flow manager if needed."""
        try:
            # Check for policy file in parameters
            policy_file = params.get("policy_file", None)
            
            if self.sdn_controller:
                # If we have an SDN controller, use the SDN Policy Engine
                from src.networking.policy.sdn_policy_engine import SDNPolicyEngine
                
                # Create SDN policy engine with controller
                self.policy_engine = SDNPolicyEngine(self.sdn_controller)
                logger.info(f"Initialized SDN policy engine")
                
                # Create flow manager with controller and policy engine
                from src.networking.sdn.flow_manager import FlowManager
                self.flow_manager = FlowManager(self.sdn_controller, self.policy_engine)
                logger.info("Initialized flow manager with policy engine")
            else:
                # If we don't have an SDN controller, use the regular Policy Engine
                self.policy_engine = PolicyEngine()
                logger.info("Initialized standard policy engine")
            
            # If a policy file is provided, load policies from it
            if policy_file and os.path.exists(policy_file):
                self._load_policies_from_file(policy_file)
                
        except ImportError as e:
            logger.warning(f"Could not initialize policy engine: {e}")
        except Exception as e:
            logger.error(f"Error initializing policy engine: {e}")
    
    def _load_policies_from_file(self, policy_file: str) -> None:
        """
        Load policies from a JSON file.
        
        Args:
            policy_file: Path to the policy file
        """
        try:
            import json
            
            with open(policy_file, 'r') as f:
                policies = json.load(f)
            
            # Add each policy to the policy engine
            for policy in policies:
                policy_type = policy.get("type")
                policy_definition = policy.get("definition", {})
                
                if policy_type:
                    self.policy_engine.add_policy(policy_type, policy_definition)
                    logger.info(f"Added policy of type {policy_type} from file")
            
            logger.info(f"Loaded {len(policies)} policies from {policy_file}")
            
        except Exception as e:
            logger.error(f"Error loading policies from file {policy_file}: {e}")
    
    def create_network(self, topo_type: str, topo_params: Dict[str, Any]) -> bool:
        """
        Create a network with the specified topology.
        
        Args:
            topo_type: Type of topology (star, ring, tree, mesh, custom)
            topo_params: Parameters for the topology
            
        Returns:
            bool: Success or failure
        """
        try:
            if not self.simulator:
                logger.error("No simulator available")
                return False
            
            logger.info(f"Creating {topo_type} topology with parameters: {topo_params}")
            
            if topo_type == "star":
                n = topo_params.get("n", 3)
                return self.create_star_topology(n)
            elif topo_type == "ring":
                n = topo_params.get("n", 3)
                return self.create_ring_topology(n)
            elif topo_type == "tree":
                depth = topo_params.get("depth", 2)
                fanout = topo_params.get("fanout", 2)
                return self.create_tree_topology(depth, fanout)
            elif topo_type == "custom":
                topology = topo_params.get("topology", {})
                return self.create_custom_topology(topology)
            elif topo_type == "mesh":
                n = topo_params.get("n", 3)
                bandwidth = topo_params.get("bandwidth", None)
                latency = topo_params.get("latency", None)
                packet_loss = topo_params.get("packet_loss", None)
                return self.create_mesh_topology(n, bandwidth, latency, packet_loss)
            else:
                logger.error(f"Unsupported topology type: {topo_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating network: {e}")
            return False

    def create_star_topology(self, n: int, bandwidth: int = None, latency: int = None, packet_loss: float = None, **kwargs) -> Dict[str, Any]:
        """
        Create a star topology with n nodes.
        
        Args:
            n: Number of nodes
            bandwidth: Bandwidth in Kbps
            latency: Latency in ms
            packet_loss: Packet loss percentage
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Dictionary containing topology information
        """
        if not self.simulator:
            logger.error("No simulator available")
            return {}
        
        # Forward all parameters to the simulator
        return self.simulator.create_star_topology(n=n, bandwidth=bandwidth, latency=latency, packet_loss=packet_loss, **kwargs)
    
    def create_ring_topology(self, n: int) -> bool:
        """
        Create a ring topology with n nodes.
        
        Args:
            n: Number of nodes
            
        Returns:
            bool: Success or failure
        """
        if not self.simulator:
            logger.error("No simulator available")
            return False
        
        return self.simulator.create_ring_topology(n)
    
    def create_tree_topology(self, depth: int, fanout: int) -> bool:
        """
        Create a tree topology.
        
        Args:
            depth: Tree depth
            fanout: Number of children per node
            
        Returns:
            bool: Success or failure
        """
        if not self.simulator:
            logger.error("No simulator available")
            return False
        
        return self.simulator.create_tree_topology(depth, fanout)
    
    def create_custom_topology(self, topology: Dict[str, Any]) -> bool:
        """
        Create a custom topology.
        
        Args:
            topology: Topology specification
            
        Returns:
            bool: Success or failure
        """
        if not self.simulator:
            logger.error("No simulator available")
            return False
        
        return self.simulator.create_custom_topology(topology)
    
    def create_mesh_topology(self, n: int, bandwidth: int = None, latency: int = None, packet_loss: float = None, **kwargs) -> Dict[str, Any]:
        """
        Create a mesh topology with n nodes.
        
        Args:
            n: Number of nodes
            bandwidth: Bandwidth in Kbps
            latency: Latency in ms
            packet_loss: Packet loss percentage
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Dictionary containing topology information
        """
        if not self.simulator:
            logger.error("No simulator available")
            return {}
        
        # Forward all parameters to the simulator
        return self.simulator.create_mesh_topology(n=n, bandwidth=bandwidth, latency=latency, packet_loss=packet_loss, **kwargs)
    
    def set_policy_engine(self, policy_engine) -> None:
        """
        Set the policy engine for network operations.
        
        Args:
            policy_engine: Instance of PolicyEngine
        """
        self.policy_engine = policy_engine
        logger.info("Set policy engine for network simulator")
    
    def set_sdn_controller(self, sdn_controller) -> None:
        """
        Set the SDN controller for network operations.
        
        Args:
            sdn_controller: Instance of SDNController
        """
        self.sdn_controller = sdn_controller
        logger.info(f"Set SDN controller for network simulator: {sdn_controller.__class__.__name__}")
        
        # If the simulator has a method to set the SDN controller, call it
        if hasattr(self.simulator, 'set_sdn_controller'):
            self.simulator.set_sdn_controller(sdn_controller)
    
    def initialize_flow_manager(self) -> bool:
        """
        Initialize the flow manager for SDN-based traffic control.
        
        Returns:
            bool: Success or failure
        """
        try:
            if not self.sdn_controller:
                logger.warning("No SDN controller available for flow management")
                return False
            
            from src.networking.sdn.flow_manager import FlowManager
            self.flow_manager = FlowManager(self.sdn_controller)
            logger.info("Initialized flow manager for network simulator")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing flow manager: {e}")
            return False
    
    def apply_policy(self, flow_src: str, flow_dst: str, policy_id: str) -> bool:
        """
        Apply a policy to a specific flow.
        
        Args:
            flow_src: Source of the flow
            flow_dst: Destination of the flow
            policy_id: ID of the policy to apply
            
        Returns:
            bool: Success or failure
        """
        try:
            if not self.flow_manager:
                logger.warning("No flow manager available to apply policy")
                return False
            
            if not self.policy_engine:
                logger.warning("No policy engine available to apply policy")
                return False
            
            # Get the policy from the policy engine
            policy = self.policy_engine.get_policy(policy_id)
            if not policy:
                logger.error(f"Policy not found: {policy_id}")
                return False
            
            # Apply the policy using the flow manager
            return self.flow_manager.apply_policy(flow_src, flow_dst, policy)
            
        except Exception as e:
            logger.error(f"Error applying policy: {e}")
            return False
    
    def start_network(self) -> bool:
        """
        Start the network simulation.
        
        Returns:
            bool: Success or failure
        """
        try:
            if not self.simulator:
                logger.error("No simulator available")
                return False
            
            # Clean up flow manager if available
            if self.flow_manager:
                self.flow_manager.cleanup()
            
            # Disconnect from SDN controller if available
            if self.sdn_controller:
                self.sdn_controller.disconnect()
            
            return self.simulator.stop_network()
        except Exception as e:
            logger.error(f"Error stopping network: {e}")
            return False
    
    def stop_network(self) -> bool:
        """
        Stop the network simulation.
        
        Returns:
            bool: Success or failure
        """
        try:
            if not self.simulator:
                logger.error("No simulator available")
                return False
            
            # Clean up flow manager if available
            if self.flow_manager:
                self.flow_manager.cleanup()
            
            # Disconnect from SDN controller if available
            if self.sdn_controller:
                self.sdn_controller.disconnect()
            
            return self.simulator.stop_network()
        except Exception as e:
            logger.error(f"Error stopping network: {e}")
            return False
    
    def get_hosts(self) -> List[str]:
        """
        Get the list of hosts in the network.
        
        Returns:
            List[str]: List of host names
        """
        return self.simulator.get_hosts()
    
    def run_cmd_on_host(self, host: str, cmd: str) -> Tuple[bool, str]:
        """
        Run a command on a specific host.
        
        Args:
            host: Host name
            cmd: Command to run
            
        Returns:
            Tuple[bool, str]: Success flag and command output
        """
        return self.simulator.run_cmd_on_host(host, cmd)
    
    def configure_link(self, src: str, dst: str, bandwidth: float, latency: float, 
                       packet_loss: float) -> bool:
        """
        Configure parameters for a specific link.
        
        Args:
            src: Source node
            dst: Destination node
            bandwidth: Bandwidth in Mbps
            latency: Latency in ms
            packet_loss: Packet loss percentage
            
        Returns:
            bool: True if the link was configured successfully, False otherwise
        """
        return self.simulator.configure_link(src, dst, bandwidth, latency, packet_loss)
    
    def configure_all_links(self, bandwidth: float, latency: float, packet_loss: float) -> bool:
        """
        Configure parameters for all links in the network.
        
        Args:
            bandwidth: Bandwidth in Mbps
            latency: Latency in ms
            packet_loss: Packet loss percentage
            
        Returns:
            bool: True if all links were configured successfully, False otherwise
        """
        # This may not be implemented by all simulators, so we'll check for it
        if hasattr(self.simulator, 'configure_all_links'):
            return self.simulator.configure_all_links(bandwidth, latency, packet_loss)
        
        # If not implemented, use the configure_link method for each pair of hosts
        hosts = self.get_hosts()
        if not hosts:
            return False
        
        # Get all links from the topology (if available)
        if hasattr(self.simulator, 'get_topology'):
            topology = self.simulator.get_topology()
            if 'links' in topology:
                for link in topology['links']:
                    src = link.get('source')
                    dst = link.get('target')
                    if src and dst:
                        self.configure_link(src, dst, bandwidth, latency, packet_loss)
                return True
        
        # If we can't get the links from the topology, configure all pairs
        for i in range(len(hosts)):
            for j in range(i+1, len(hosts)):
                src = hosts[i]
                dst = hosts[j]
                self.configure_link(src, dst, bandwidth, latency, packet_loss)
        
        return True
    
    def get_link_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all links in the network.
        
        Returns:
            List[Dict[str, Any]]: List of link statistics
        """
        return self.simulator.get_link_stats()
    
    def simulate_federated_learning_round(self, model_size_mb: int, num_clients: int = 3) -> Dict[str, Any]:
        """
        Simulate a federated learning round with the current network configuration.
        
        Args:
            model_size_mb: Size of the model in MB
            num_clients: Number of clients participating
            
        Returns:
            Dict with simulation results
        """
        if not hasattr(self.simulator, 'simulate_federated_learning_round'):
            if self.simulator_type.lower() == 'gns3':
                # If GNS3 was specifically requested, this is an error
                logger.error("GNS3 simulator does not support federated round simulation")
                raise RuntimeError("GNS3 simulator requested but does not support federated round simulation")
            else:
                logger.warning("This simulator does not support federated round simulation")
                return {
                    "success": False,
                    "message": "Simulator does not support federated round simulation"
                }
        
        try:
            # Call the simulator's method directly
            return self.simulator.simulate_federated_learning_round(model_size_mb, num_clients)
        except Exception as e:
            if self.simulator_type.lower() == 'gns3':
                # If GNS3 was specifically requested, propagate the error
                logger.error(f"GNS3 simulation error: {e}")
                raise
            else:
                logger.warning(f"Error in simulation: {e}")
                return {
                    "success": False,
                    "message": f"Error: {str(e)}"
                }
    
    def get_network_stats(self) -> Dict[str, Any]:
        """
        Get network statistics.
        
        Returns:
            Dict with network statistics
        """
        if hasattr(self.simulator, 'get_network_stats'):
            return self.simulator.get_network_stats()
        
        # Default implementation if the simulator doesn't provide one
        return {
            "simulator_type": self.simulator_type,
            "hosts": len(self.get_hosts()),
            "links": 0,  # This would need to be calculated
            "status": "running" if hasattr(self, 'network_active') and self.network_active else "stopped"
        }
    
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology.
        
        Returns:
            Dict with topology information
        """
        if hasattr(self.simulator, 'get_topology'):
            return self.simulator.get_topology()
        
        # Default implementation if the simulator doesn't provide one
        return {
            "hosts": self.get_hosts(),
            "switches": [],
            "links": []
        }
    
    def apply_sdn_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply an SDN policy to the network.
        
        Args:
            policy: Policy configuration
            
        Returns:
            bool: Success or failure
        """
        try:
            if not self.sdn_controller or not self.sdn_controller.connected:
                logger.error("No active SDN controller available")
                return False
            
            # Use policy engine if available
            if self.policy_engine:
                policy_type = policy.get("type", "unknown")
                return self.policy_engine.add_policy(policy_type, policy) is not None
            
            # Use flow manager if available
            if self.flow_manager:
                return self.flow_manager.apply_network_policy(policy)
            
            # If no policy engine or flow manager, try direct application
            policy_type = policy.get("type", "unknown")
            
            if policy_type == "flow":
                # Basic flow rule policy
                switch = policy.get("switch")
                priority = policy.get("priority", 100)
                match = policy.get("match", {})
                actions = policy.get("actions", [])
                idle_timeout = policy.get("idle_timeout", 0)
                hard_timeout = policy.get("hard_timeout", 0)
                
                if not switch or not match or not actions:
                    logger.error("Missing required parameters for flow policy")
                    return False
                
                return self.sdn_controller.add_flow(
                    switch, priority, match, actions, idle_timeout, hard_timeout
                )
            
            logger.error(f"Cannot apply complex policy of type {policy_type} without policy engine")
            return False
            
        except Exception as e:
            logger.error(f"Error applying SDN policy: {e}")
            return False
    
    def check_policy_compliance(self, src_ip: str, dst_ip: str, 
                              protocol: str = "any", port: int = 0) -> bool:
        """
        Check if a communication path complies with security policies.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            protocol: Protocol (tcp, udp, icmp, any)
            port: Destination port
            
        Returns:
            bool: Whether the path is compliant with security policies
        """
        try:
            # Use policy engine if available
            if self.policy_engine:
                context = {
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "protocol": protocol,
                    "port": port
                }
                
                result = self.policy_engine.check_policy("network_security", context)
                return result.get("allowed", True)
            
            # If no policy engine, use flow manager if available
            if self.flow_manager:
                return self.flow_manager.check_path_policy_compliance(src_ip, dst_ip, protocol, port)
            
            # If neither is available, assume compliance
            logger.warning("No policy engine available to check policy compliance")
            return True
            
        except Exception as e:
            logger.error(f"Error checking policy compliance: {e}")
            return False
    
    def get_policy_engine(self):
        """
        Get the policy engine instance if available.
        
        Returns:
            PolicyEngine instance or None
        """
        return self.policy_engine
    
    def get_flow_manager(self):
        """
        Get the flow manager instance if available.
        
        Returns:
            FlowManager instance or None
        """
        return self.flow_manager
    
    def get_sdn_controller(self) -> Optional[Any]:
        """
        Get the SDN controller instance if available.
        
        Returns:
            SDN controller instance or None
        """
        return self.sdn_controller
    
    def get_simulator_type(self) -> str:
        """
        Get the type of simulator being used.
        
        Returns:
            str: Simulator type (mock, mininet, gns3)
        """
        return self.simulator_type
    
    def cleanup(self) -> bool:
        """
        Clean up resources.
        
        Returns:
            bool: Success or failure
        """
        try:
            if not self.simulator:
                logger.error("No simulator available")
                return False
            
            # Clean up flow manager if available
            if self.flow_manager:
                if hasattr(self.flow_manager, 'cleanup'):
                    self.flow_manager.cleanup()
                self.flow_manager = None
            
            # Clean up policy engine if available
            if self.policy_engine:
                if hasattr(self.policy_engine, 'cleanup'):
                    self.policy_engine.cleanup()
                self.policy_engine = None
            
            # Disconnect from SDN controller if available
            if self.sdn_controller:
                if hasattr(self.sdn_controller, 'disconnect'):
                    self.sdn_controller.disconnect()
                self.sdn_controller = None
            
            return self.simulator.cleanup()
            
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")
            return False 