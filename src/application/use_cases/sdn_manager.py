"""
SDN Manager Use Case

This module handles integration between the federated learning system 
and the SDN controller, coordinating network policies and optimizations.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple

from src.domain.interfaces.sdn_controller import ISDNController
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.interfaces.network_simulator import INetworkSimulator


class SDNManager:
    """
    SDN Manager coordinates SDN controller, network simulator, and applies policies.
    
    This class is responsible for:
    1. Communicating with the SDN controller
    2. Managing network simulator instances
    3. Applying policy decisions from the policy engine to the network
    4. Collecting network metrics for monitoring and optimization
    """
    
    def __init__(self, 
                 sdn_controller: ISDNController,
                 policy_engine: IPolicyEngine,
                 network_simulator: Optional[INetworkSimulator] = None,
                 config: Dict[str, Any] = None):
        """
        Initialize the SDN Manager.
        
        Args:
            sdn_controller: SDN controller implementation
            policy_engine: Policy engine for applying network policies
            network_simulator: Optional network simulator for testing
            config: Configuration dictionary
        """
        self.sdn_controller = sdn_controller
        self.policy_engine = policy_engine
        self.network_simulator = network_simulator
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.simulation_mode = self.config.get("simulation_mode", False)
        self.active_policies = []
        
        # Register for policy engine events
        self.policy_engine.register_callback("policy_evaluation_completed", 
                                           self._on_policy_evaluation_completed)
        
        self.logger.info("SDN Manager initialized")
    
    def initialize(self) -> bool:
        """
        Initialize the SDN manager, establishing connections and setting up.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Register SDN policy in policy engine if not already registered
            if "sdn" not in [p.get_name() for p in self.active_policies]:
                self.policy_engine.register_policy("sdn", self.config.get("sdn_policy", {}))
                self.active_policies.append(self.policy_engine.get_policy("sdn"))
                self.logger.info("Registered SDN policy")
            
            # Start network simulator if in simulation mode
            if self.simulation_mode and self.network_simulator:
                topology_config = self.config.get("topology", {"type": "single"})
                self.network_simulator.create_topology(topology_config)
                self.network_simulator.start_simulation()
                self.logger.info("Started network simulator")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error initializing SDN Manager: {e}")
            return False
    
    def get_network_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology.
        
        Returns:
            Dictionary containing network topology information
        """
        if self.simulation_mode and self.network_simulator:
            # Get simulated topology
            status = self.network_simulator.get_simulation_status()
            return {
                "devices": status.get("device_count", 0),
                "hosts": status.get("host_count", 0),
                "links": status.get("link_count", 0),
                "type": status.get("topology")
            }
        else:
            # Get real topology from SDN controller
            return self.sdn_controller.get_topology()
    
    def apply_network_policy(self, policy_result: Dict[str, Any]) -> bool:
        """
        Apply network policy decisions to the SDN controller or simulator.
        
        Args:
            policy_result: Policy evaluation result from the policy engine
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.simulation_mode and self.network_simulator:
                return self._apply_policy_to_simulator(policy_result)
            else:
                return self._apply_policy_to_controller(policy_result)
        
        except Exception as e:
            self.logger.error(f"Error applying network policy: {e}")
            return False
    
    def _apply_policy_to_simulator(self, policy_result: Dict[str, Any]) -> bool:
        """
        Apply policy decisions to the network simulator.
        
        Args:
            policy_result: Policy evaluation result
            
        Returns:
            True if successful, False otherwise
        """
        if not self.network_simulator:
            self.logger.error("Network simulator not available")
            return False
        
        # Apply QoS settings to links
        for link_id, link_settings in policy_result.get("link_settings", {}).items():
            if "bandwidth" in link_settings:
                source, target = link_id.split("-")
                self.network_simulator.set_link_bandwidth(
                    source, target, link_settings["bandwidth"]
                )
            
            if "delay" in link_settings:
                source, target = link_id.split("-")
                self.network_simulator.add_link_delay(
                    source, target, link_settings["delay"]
                )
            
            if "loss" in link_settings:
                source, target = link_id.split("-")
                self.network_simulator.add_link_loss(
                    source, target, link_settings["loss"]
                )
        
        # Add client nodes if specified
        for client_id, client_config in policy_result.get("client_configs", {}).items():
            self.network_simulator.add_client_node(client_id, client_config)
        
        return True
    
    def _apply_policy_to_controller(self, policy_result: Dict[str, Any]) -> bool:
        """
        Apply policy decisions to the SDN controller.
        
        Args:
            policy_result: Policy evaluation result
            
        Returns:
            True if successful, False otherwise
        """
        # Apply flow rules
        success = True
        for flow_rule in policy_result.get("flow_rules", []):
            device_id = flow_rule.get("deviceId")
            if not device_id:
                self.logger.warning("Flow rule missing deviceId, skipping")
                continue
                
            if not self.sdn_controller.create_flow(device_id, flow_rule):
                self.logger.error(f"Failed to create flow for device {device_id}")
                success = False
        
        # Apply QoS policies
        for qos_policy in policy_result.get("qos_settings", {}).get("policies", []):
            if not self.sdn_controller.apply_qos_policy(qos_policy):
                self.logger.error("Failed to apply QoS policy")
                success = False
        
        return success
    
    def _on_policy_evaluation_completed(self, event_data: Dict[str, Any]) -> None:
        """
        Handle policy evaluation completed event.
        
        Args:
            event_data: Event data containing policy results
        """
        results = event_data.get("results", [])
        context = event_data.get("context", {})
        
        # Find SDN policy results
        for result in results:
            if result.get("policy_name") == "sdn":
                self.logger.debug("Applying SDN policy result")
                self.apply_network_policy(result)
                break
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """
        Get current network performance metrics.
        
        Returns:
            Dictionary containing network metrics
        """
        metrics = {}
        
        if self.simulation_mode and self.network_simulator:
            # Get metrics from simulator
            perf_metrics = self.network_simulator.get_performance_metrics()
            
            # Extract key metrics
            metrics["ping"] = perf_metrics.get("ping", {})
            metrics["bandwidth"] = perf_metrics.get("bandwidth", {})
            metrics["congestion"] = perf_metrics.get("congestion", {})
        else:
            # Get metrics from SDN controller
            topology = self.sdn_controller.get_topology()
            devices = topology.get("devices", [])
            
            # Get flow stats for all devices
            flow_stats = []
            for device in devices:
                device_id = device.get("id")
                if device_id:
                    flow_stats.extend(self.sdn_controller.get_flow_stats(device_id))
            
            metrics["flow_stats"] = flow_stats
            metrics["link_utilization"] = self.sdn_controller.get_link_utilization()
        
        return metrics
    
    def optimize_client_paths(self, clients: List[Dict[str, Any]], 
                            server_location: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Optimize network paths for federated learning clients.
        
        Args:
            clients: List of client information dictionaries
            server_location: Server location information
            
        Returns:
            Dictionary mapping client IDs to optimized paths (list of switch IDs)
        """
        client_paths = {}
        
        # Create context for policy evaluation
        context = {
            "network_topology": self.get_network_topology(),
            "server_location": server_location,
            "client_locations": {client["id"]: client for client in clients},
            "current_phase": "optimization",
            "congestion_info": self._get_congestion_info()
        }
        
        # Evaluate SDN policy
        policy_results = self.policy_engine.evaluate_policies(context)
        
        # Find SDN policy result
        for result in policy_results:
            if result.get("policy_name") == "sdn":
                client_paths = result.get("client_paths", {})
                
                # Apply the optimized paths to the SDN controller
                self.apply_network_policy(result)
                break
        
        return client_paths
    
    def _get_congestion_info(self) -> Dict[str, Any]:
        """
        Get current network congestion information.
        
        Returns:
            Dictionary containing congestion information
        """
        if self.simulation_mode and self.network_simulator:
            # Get congestion from simulator
            metrics = self.network_simulator.get_performance_metrics()
            return metrics.get("congestion", {})
        else:
            # Calculate congestion from link utilization
            link_utilization = self.sdn_controller.get_link_utilization()
            
            # Identify congested links (utilization > 70%)
            congested_links = []
            for link_id, utilization in link_utilization.items():
                if utilization > 70.0:
                    congested_links.append({
                        "id": link_id,
                        "utilization": utilization
                    })
            
            return {
                "congested_links": congested_links,
                "congestion_level": len(congested_links) / max(1, len(link_utilization))
            }
    
    def shutdown(self) -> None:
        """Shutdown the SDN manager, cleaning up resources."""
        if self.simulation_mode and self.network_simulator:
            self.network_simulator.stop_simulation()
            self.logger.info("Stopped network simulator")
        
        self.logger.info("SDN Manager shutdown complete") 