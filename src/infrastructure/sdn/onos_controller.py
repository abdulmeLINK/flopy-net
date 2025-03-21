"""
ONOS SDN Controller Implementation

This module provides an implementation of the ISDNController interface using ONOS.
"""
import requests
import json
import logging
from typing import Dict, Any, List, Optional

from src.domain.interfaces.sdn_controller import ISDNController

logger = logging.getLogger(__name__)


class ONOSController(ISDNController):
    """Implementation of ISDNController using ONOS."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the ONOS controller.
        
        Args:
            config: Configuration dictionary containing ONOS connection details
        """
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8181)
        self.username = self.config.get("username", "onos")
        self.password = self.config.get("password", "rocks")
        self.base_url = f"http://{self.host}:{self.port}/onos/v1"
        self.auth = (self.username, self.password)
        logger.info(f"Initialized ONOS controller at {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a request to the ONOS REST API.
        
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
                response = requests.get(url, auth=self.auth, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, auth=self.auth, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, auth=self.auth, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"ONOS API request failed: {e}")
            return {"error": str(e)}
    
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology from ONOS.
        
        Returns:
            Dictionary containing network topology information
        """
        devices = self._make_request("GET", "devices")
        links = self._make_request("GET", "links")
        hosts = self._make_request("GET", "hosts")
        
        return {
            "devices": devices.get("devices", []),
            "links": links.get("links", []),
            "hosts": hosts.get("hosts", [])
        }
    
    def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific network device.
        
        Args:
            device_id: The ID of the device
            
        Returns:
            Dictionary containing device statistics
        """
        return self._make_request("GET", f"statistics/ports/{device_id}")
    
    def get_flow_stats(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get flow statistics for devices in the network.
        
        Args:
            device_id: Optional device ID to filter statistics
            
        Returns:
            List of dictionaries containing flow statistics
        """
        endpoint = f"statistics/flows/{device_id}" if device_id else "statistics/flows"
        response = self._make_request("GET", endpoint)
        return response.get("flows", [])
    
    def create_flow(self, device_id: str, flow_rule: Dict[str, Any]) -> bool:
        """
        Create a new flow rule on a device.
        
        Args:
            device_id: The ID of the target device
            flow_rule: Flow rule configuration
            
        Returns:
            True if successful, False otherwise
        """
        response = self._make_request("POST", f"flows/{device_id}", flow_rule)
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
        response = self._make_request("DELETE", f"flows/{device_id}/{flow_id}")
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
        payload = {
            "source": source,
            "destination": destination,
            "constraints": constraints or {}
        }
        response = self._make_request("POST", "paths", payload)
        return response.get("paths", [])
    
    def get_link_utilization(self) -> Dict[str, float]:
        """
        Get current link utilization across the network.
        
        Returns:
            Dictionary mapping link IDs to utilization percentages
        """
        links = self._make_request("GET", "links")
        stats = self._make_request("GET", "statistics/ports")
        
        utilization = {}
        link_list = links.get("links", [])
        
        # Calculate utilization based on port statistics
        for link in link_list:
            src_device = link.get("src", {}).get("device", "")
            src_port = link.get("src", {}).get("port", "")
            link_id = f"{src_device}-{src_port}"
            
            # Find port stats for this link
            for device_stat in stats.get("statistics", []):
                if device_stat.get("deviceId") == src_device:
                    for port_stat in device_stat.get("ports", []):
                        if port_stat.get("port") == src_port:
                            bytes_received = port_stat.get("bytesReceived", 0)
                            duration = port_stat.get("durationSec", 1)
                            capacity = 1000000000  # Assume 1Gbps link capacity
                            
                            # Calculate utilization as percentage of capacity
                            if duration > 0:
                                bytes_per_second = bytes_received / duration
                                bits_per_second = bytes_per_second * 8
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
        # QoS in ONOS is implemented through flow rules with specific treatment
        device_id = policy.get("deviceId")
        if not device_id:
            logger.error("DeviceId is required for QoS policy")
            return False
        
        # Create flow rule with QoS treatment
        flow_rule = {
            "priority": policy.get("priority", 40000),
            "timeout": 0,
            "isPermanent": True,
            "deviceId": device_id,
            "treatment": {
                "instructions": [
                    {
                        "type": "QUEUE",
                        "queueId": policy.get("queueId", 0)
                    }
                ],
                "deferred": []
            },
            "selector": {
                "criteria": policy.get("criteria", [])
            }
        }
        
        return self.create_flow(device_id, flow_rule) 