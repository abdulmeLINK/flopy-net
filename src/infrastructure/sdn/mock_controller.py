"""
Mock SDN Controller

This module provides a mock implementation of the SDN controller.
"""
import logging
import random
from typing import Dict, Any, List, Optional

from src.domain.interfaces.sdn_controller import ISDNController


class MockSDNController(ISDNController):
    """
    Mock implementation of the SDN controller.
    
    This class simulates an SDN controller for testing and development purposes.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the mock SDN controller.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.flows = {}
        self.devices = {}
        self.policies = {}
    
    def start(self) -> bool:
        """
        Start the controller.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Starting mock SDN controller")
        self.running = True
        return True
    
    def stop(self) -> bool:
        """
        Stop the controller.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Stopping mock SDN controller")
        self.running = False
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the controller status.
        
        Returns:
            Dictionary containing controller status
        """
        return {
            "running": self.running,
            "devices": len(self.devices),
            "flows": len(self.flows),
            "policies": len(self.policies)
        }
    
    def discover_devices(self) -> List[Dict[str, Any]]:
        """
        Discover network devices.
        
        Returns:
            List of discovered devices
        """
        # Generate random mock devices
        self.devices = {
            f"switch{i}": {
                "id": f"switch{i}",
                "type": "switch",
                "datapath_id": f"00:00:00:00:00:00:00:{i:02x}",
                "status": "active",
                "ports": random.randint(4, 16)
            } for i in range(1, 6)
        }
        
        # Add mock controller device
        self.devices["controller"] = {
            "id": "controller",
            "type": "controller",
            "datapath_id": "00:00:00:00:00:00:00:00",
            "status": "active",
            "ports": 0
        }
        
        self.logger.info(f"Discovered {len(self.devices)} devices")
        return list(self.devices.values())
    
    def create_flow(self, device_id: str, flow_rule: Dict[str, Any]) -> bool:
        """
        Create a new flow rule on a device.
        
        Args:
            device_id: The ID of the target device
            flow_rule: Flow rule configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            flow_id = flow_rule.get("id", f"flow{len(self.flows) + 1}")
            if flow_id in self.flows:
                self.logger.warning(f"Flow {flow_id} already exists")
                return False
            
            # Add device_id to the flow rule
            flow_rule["device_id"] = device_id
            
            self.flows[flow_id] = flow_rule
            self.logger.info(f"Created flow {flow_id} on device {device_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating flow: {e}")
            return False
    
    def remove_flow(self, device_id: str, flow_id: str) -> bool:
        """
        Remove a flow rule from a device.
        
        Args:
            device_id: The ID of the target device
            flow_id: The ID of the flow to remove
            
        Returns:
            True if successful, False otherwise
        """
        if flow_id not in self.flows:
            self.logger.warning(f"Flow {flow_id} not found")
            return False
        
        if self.flows[flow_id].get("device_id") != device_id:
            self.logger.warning(f"Flow {flow_id} not found on device {device_id}")
            return False
        
        del self.flows[flow_id]
        self.logger.info(f"Deleted flow {flow_id} from device {device_id}")
        return True
    
    def get_flows(self) -> List[Dict[str, Any]]:
        """
        Get all flows in the network.
        
        Returns:
            List of flows
        """
        return list(self.flows.values())
    
    def apply_qos_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply quality of service policies to the network.
        
        Args:
            policy: QoS policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            policy_id = policy.get("id", f"policy{len(self.policies) + 1}")
            if policy_id in self.policies:
                self.logger.warning(f"Policy {policy_id} already exists")
                return False
            
            self.policies[policy_id] = policy
            self.logger.info(f"Applied QoS policy {policy_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error applying QoS policy: {e}")
            return False
    
    def get_link_utilization(self) -> Dict[str, float]:
        """
        Get current link utilization across the network.
        
        Returns:
            Dictionary mapping link IDs to utilization percentages
        """
        # Generate mock link utilization data
        utilization = {}
        # Create links between each pair of devices
        device_ids = list(self.devices.keys())
        for i in range(len(device_ids) - 1):
            for j in range(i + 1, len(device_ids)):
                link_id = f"{device_ids[i]}-{device_ids[j]}"
                utilization[link_id] = random.uniform(10.0, 90.0)
        
        return utilization
    
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology.
        
        Returns:
            Dictionary containing network topology information
        """
        # Create a list of devices
        devices = list(self.devices.values())
        
        # Create a list of links between devices
        links = []
        device_ids = list(self.devices.keys())
        for i in range(len(device_ids) - 1):
            for j in range(i + 1, len(device_ids)):
                links.append({
                    "source": device_ids[i],
                    "target": device_ids[j],
                    "bandwidth": 1000,  # 1 Gbps
                    "delay": "5ms",
                    "loss": 0.0
                })
        
        return {
            "devices": devices,
            "links": links
        }
    
    def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific network device.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            Dictionary containing device statistics
        """
        if device_id not in self.devices:
            self.logger.warning(f"Device {device_id} not found")
            return {}
        
        # Generate mock device statistics
        return {
            "id": device_id,
            "type": self.devices[device_id].get("type", "switch"),
            "uptime": random.randint(3600, 86400),  # 1-24 hours in seconds
            "ports": {
                f"port{i}": {
                    "rx_packets": random.randint(1000, 10000),
                    "tx_packets": random.randint(1000, 10000),
                    "rx_bytes": random.randint(1000000, 10000000),
                    "tx_bytes": random.randint(1000000, 10000000),
                    "rx_errors": random.randint(0, 10),
                    "tx_errors": random.randint(0, 10)
                } for i in range(1, self.devices[device_id].get("ports", 4) + 1)
            },
            "cpu_util": random.uniform(5.0, 30.0),
            "memory_util": random.uniform(20.0, 60.0)
        }
    
    def get_flow_stats(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get flow statistics for devices in the network.
        
        Args:
            device_id: Optional device ID to filter statistics
            
        Returns:
            List of dictionaries containing flow statistics
        """
        result = []
        
        for flow_id, flow in self.flows.items():
            # Filter by device_id if specified
            if device_id and flow.get("device_id") != device_id:
                continue
                
            # Generate mock flow statistics
            stats = {
                "id": flow_id,
                "device_id": flow.get("device_id", "unknown"),
                "packet_count": random.randint(1000, 10000),
                "byte_count": random.randint(1000000, 10000000),
                "duration_sec": random.randint(60, 3600)
            }
            
            result.append(stats)
            
        return result
    
    def optimize_paths(self, source: str, destination: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Calculate optimal paths between source and destination with constraints.
        
        Args:
            source: Source node ID
            destination: Destination node ID
            constraints: Optional path constraints (bandwidth, latency, etc.)
            
        Returns:
            List of dictionaries representing optimal paths
        """
        self.logger.info(f"Optimizing paths from {source} to {destination}")
        
        # In a real implementation, we would calculate the optimal paths
        # For the mock, we just generate a mock path
        
        # Check if source and destination exist
        if source not in self.devices:
            self.logger.warning(f"Source device {source} not found")
            return []
            
        if destination not in self.devices:
            self.logger.warning(f"Destination device {destination} not found")
            return []
        
        # Generate a mock path
        devices_in_path = [source]
        
        # Add some intermediate devices if we have enough
        device_ids = [d for d in self.devices.keys() if d != source and d != destination]
        num_hops = min(random.randint(1, 3), len(device_ids))
        
        if num_hops > 0:
            selected_hops = random.sample(device_ids, num_hops)
            devices_in_path.extend(selected_hops)
        
        devices_in_path.append(destination)
        
        # Create links from the path
        links = []
        for i in range(len(devices_in_path) - 1):
            links.append({
                "source": devices_in_path[i],
                "target": devices_in_path[i + 1]
            })
        
        # Calculate path metrics
        bandwidth = 1000  # 1 Gbps
        latency = 5 * len(links)  # 5ms per hop
        loss = 0.01 * len(links)  # 0.01% loss per hop
        
        # Apply constraints if provided
        if constraints:
            min_bandwidth = constraints.get("min_bandwidth", 0)
            max_latency = constraints.get("max_latency", float('inf'))
            max_loss = constraints.get("max_loss", float('inf'))
            
            # Adjust path metrics based on constraints
            bandwidth = max(bandwidth, min_bandwidth)
            latency = min(latency, max_latency)
            loss = min(loss, max_loss)
        
        path = {
            "devices": devices_in_path,
            "links": links,
            "metrics": {
                "bandwidth": bandwidth,
                "latency": latency,
                "loss": loss,
                "hops": len(links)
            }
        }
        
        return [path] 