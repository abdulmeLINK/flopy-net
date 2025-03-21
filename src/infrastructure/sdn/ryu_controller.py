"""
Ryu SDN Controller Implementation

This module provides an implementation of the ISDNController interface using Ryu.
"""
import requests
import json
import logging
from typing import Dict, Any, List, Optional

from src.domain.interfaces.sdn_controller import ISDNController

logger = logging.getLogger(__name__)


class RyuController(ISDNController):
    """Implementation of ISDNController using Ryu."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Ryu controller.
        
        Args:
            config: Configuration dictionary containing Ryu connection details
        """
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8080)
        self.base_url = f"http://{self.host}:{self.port}"
        logger.info(f"Initialized Ryu controller at {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a request to the Ryu REST API.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ryu API request failed: {e}")
            return {"error": str(e)}
    
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology from Ryu.
        
        Returns:
            Dictionary containing network topology information
        """
        switches = self._make_request("GET", "stats/switches")
        links = self._make_request("GET", "stats/links")
        
        # Get details for each switch
        devices = []
        for switch_id in switches:
            switch_desc = self._make_request("GET", f"stats/desc/{switch_id}")
            devices.append({
                "id": str(switch_id),
                "description": switch_desc.get(str(switch_id), {})
            })
        
        # Get hosts
        hosts = self._make_request("GET", "stats/hosts")
        
        return {
            "devices": devices,
            "links": links,
            "hosts": hosts
        }
    
    def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific network device.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            Dictionary containing device statistics
        """
        port_stats = self._make_request("GET", f"stats/port/{device_id}")
        flow_stats = self._make_request("GET", f"stats/flow/{device_id}")
        
        return {
            "ports": port_stats.get(device_id, []),
            "flows": flow_stats.get(device_id, [])
        }
    
    def get_flow_stats(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get flow statistics for devices in the network.
        
        Args:
            device_id: Optional device ID to filter statistics
            
        Returns:
            List of dictionaries containing flow statistics
        """
        if device_id:
            response = self._make_request("GET", f"stats/flow/{device_id}")
            return response.get(device_id, [])
        else:
            # Get all switches
            switches = self._make_request("GET", "stats/switches")
            flow_stats = []
            
            # Get flow stats for each switch
            for switch_id in switches:
                response = self._make_request("GET", f"stats/flow/{switch_id}")
                switch_stats = response.get(str(switch_id), [])
                for stat in switch_stats:
                    stat["device_id"] = str(switch_id)
                flow_stats.extend(switch_stats)
            
            return flow_stats
    
    def create_flow(self, device_id: str, flow_rule: Dict[str, Any]) -> bool:
        """
        Create a new flow rule on a device.
        
        Args:
            device_id: The ID of the target device
            flow_rule: Flow rule configuration
            
        Returns:
            True if successful, False otherwise
        """
        endpoint = f"stats/flowentry/add"
        
        # Ensure device_id is in the flow rule
        flow_data = flow_rule.copy()
        flow_data["dpid"] = int(device_id)
        
        response = self._make_request("POST", endpoint, flow_data)
        return "error" not in response
    
    def remove_flow(self, device_id: str, flow_id: str) -> bool:
        """
        Remove a flow rule from a device.
        
        Args:
            device_id: The ID of the target device
            flow_id: The ID of the flow to remove
            
        Returns:
            True if successful, False otherwise
        """
        # In Ryu, we need to specify the match and actions to remove a flow
        # First get the flow details
        flows = self.get_flow_stats(device_id)
        target_flow = None
        
        for flow in flows:
            if str(flow.get("cookie", "")) == flow_id:
                target_flow = flow
                break
        
        if not target_flow:
            logger.error(f"Flow {flow_id} not found on device {device_id}")
            return False
        
        # Create delete request
        delete_data = {
            "dpid": int(device_id),
            "cookie": int(flow_id),
            "cookie_mask": 0xFFFFFFFFFFFFFFFF
        }
        
        endpoint = "stats/flowentry/delete_strict"
        response = self._make_request("POST", endpoint, delete_data)
        return "error" not in response
    
    def optimize_paths(self, source: str, destination: str, 
                       constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Calculate optimal paths between source and destination with constraints.
        
        Args:
            source: Source node ID
            destination: Destination node ID
            constraints: Optional path constraints (bandwidth, latency, etc.)
            
        Returns:
            List of dictionaries representing optimal paths
        """
        # Ryu doesn't have a direct API for path optimization
        # This would typically be implemented as a custom REST endpoint
        # For now, return an empty list
        logger.warning("Path optimization not directly supported in Ryu API")
        return []
    
    def get_link_utilization(self) -> Dict[str, float]:
        """
        Get current link utilization across the network.
        
        Returns:
            Dictionary mapping link IDs to utilization percentages
        """
        # Get all switches
        switches = self._make_request("GET", "stats/switches")
        links = self._make_request("GET", "stats/links")
        utilization = {}
        
        # Get port stats for each switch
        for switch_id in switches:
            port_stats = self._make_request("GET", f"stats/port/{switch_id}")
            switch_ports = port_stats.get(str(switch_id), [])
            
            # Calculate utilization for each port
            for port_stat in switch_ports:
                port_no = port_stat.get("port_no")
                link_id = f"{switch_id}-{port_no}"
                
                # Basic utilization calculation
                tx_bytes = port_stat.get("tx_bytes", 0)
                rx_bytes = port_stat.get("rx_bytes", 0)
                duration_sec = port_stat.get("duration_sec", 1)
                
                if duration_sec > 0:
                    bytes_per_second = (tx_bytes + rx_bytes) / duration_sec
                    bits_per_second = bytes_per_second * 8
                    # Assume 1Gbps link capacity
                    capacity = 1000000000
                    util_percentage = (bits_per_second / capacity) * 100
                    utilization[link_id] = min(100.0, util_percentage)
        
        return utilization
    
    def apply_qos_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply quality of service policies to the network.
        
        Args:
            policy: QoS policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        # QoS in Ryu is implemented through meter and queue configurations
        device_id = policy.get("deviceId")
        if not device_id:
            logger.error("DeviceId is required for QoS policy")
            return False
        
        # Create meter configuration
        meter_config = {
            "dpid": int(device_id),
            "flags": ["KBPS", "BURST", "STATS"],
            "meter_id": policy.get("meterId", 1),
            "bands": [
                {
                    "type": "DROP",
                    "rate": policy.get("rate", 1000),
                    "burst_size": policy.get("burstSize", 500)
                }
            ]
        }
        
        # Add meter
        meter_response = self._make_request("POST", "stats/meterentry/add", meter_config)
        
        # Create flow rule that uses this meter
        flow_rule = {
            "dpid": int(device_id),
            "priority": policy.get("priority", 32768),
            "match": {
                "dl_type": 0x0800,  # IPv4
                "nw_dst": policy.get("destinationIp", "10.0.0.1/32")
            },
            "actions": [
                {
                    "type": "METER",
                    "meter_id": policy.get("meterId", 1)
                },
                {
                    "type": "OUTPUT",
                    "port": policy.get("outputPort", "NORMAL")
                }
            ]
        }
        
        # Add flow
        flow_response = self._make_request("POST", "stats/flowentry/add", flow_rule)
        
        return "error" not in meter_response and "error" not in flow_response 