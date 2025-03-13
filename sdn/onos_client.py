"""
ONOS Controller Client for SDN Integration

This module provides a client for interacting with the ONOS SDN controller
through its REST API, allowing for dynamic network adjustments.
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple, Union
from requests.auth import HTTPBasicAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ONOSClient:
    """Client for interacting with ONOS SDN controller."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8181,
        username: str = "onos",
        password: str = "rocks",
        verify_ssl: bool = False,
    ):
        """
        Initialize the ONOS client.
        
        Args:
            host: ONOS controller hostname
            port: ONOS REST API port
            username: ONOS username
            password: ONOS password
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = f"http://{host}:{port}/onos/v1"
        self.auth = HTTPBasicAuth(username, password)
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = verify_ssl
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        Make a request to the ONOS API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: Query parameters
        
        Returns:
            Response data as dictionary
        
        Raises:
            requests.HTTPError: If the request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = self.session.post(url, json=data, params=params, headers=headers)
            elif method == "PUT":
                response = self.session.put(url, json=data, params=params, headers=headers)
            elif method == "DELETE":
                response = self.session.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
        
        except requests.RequestException as e:
            logger.error(f"ONOS API request failed: {e}")
            raise
    
    # Device-related methods
    
    def get_devices(self) -> List[Dict]:
        """Get all devices in the network."""
        response = self._request("GET", "devices")
        return response.get("devices", [])
    
    def get_device(self, device_id: str) -> Dict:
        """Get details for a specific device."""
        response = self._request("GET", f"devices/{device_id}")
        return response
    
    # Flow-related methods
    
    def get_flows(self, device_id: Optional[str] = None) -> List[Dict]:
        """
        Get flows for all devices or a specific device.
        
        Args:
            device_id: Optional device ID to filter flows
        
        Returns:
            List of flow entries
        """
        if device_id:
            response = self._request("GET", f"flows/{device_id}")
            return response.get("flows", [])
        else:
            response = self._request("GET", "flows")
            return response.get("flows", [])
    
    def add_flow(self, device_id: str, flow: Dict) -> Dict:
        """
        Add a flow rule to a device.
        
        Args:
            device_id: Device ID
            flow: Flow rule definition
        
        Returns:
            Response data
        """
        return self._request("POST", f"flows/{device_id}", data=flow)
    
    def remove_flow(self, device_id: str, flow_id: str) -> Dict:
        """
        Remove a flow rule from a device.
        
        Args:
            device_id: Device ID
            flow_id: Flow rule ID
        
        Returns:
            Response data
        """
        return self._request("DELETE", f"flows/{device_id}/{flow_id}")
    
    # Host-related methods
    
    def get_hosts(self) -> List[Dict]:
        """Get all hosts in the network."""
        response = self._request("GET", "hosts")
        return response.get("hosts", [])
    
    def get_host(self, host_id: str) -> Dict:
        """Get details for a specific host."""
        response = self._request("GET", f"hosts/{host_id}")
        return response
    
    # Topology-related methods
    
    def get_topology(self) -> Dict:
        """Get the network topology overview."""
        return self._request("GET", "topology")
    
    def get_topology_clusters(self) -> List[Dict]:
        """Get topology clusters."""
        response = self._request("GET", "topology/clusters")
        return response.get("clusters", [])
    
    def get_topology_links(self) -> List[Dict]:
        """Get all links in the topology."""
        response = self._request("GET", "links")
        return response.get("links", [])
    
    # Intent-related methods
    
    def get_intents(self) -> List[Dict]:
        """Get all intents in the network."""
        response = self._request("GET", "intents")
        return response.get("intents", [])
    
    def add_intent(self, intent: Dict) -> Dict:
        """
        Add a new intent to the network.
        
        Args:
            intent: Intent definition
        
        Returns:
            Response data
        """
        return self._request("POST", "intents", data=intent)
    
    def remove_intent(self, intent_id: str) -> Dict:
        """
        Remove an intent from the network.
        
        Args:
            intent_id: Intent ID
        
        Returns:
            Response data
        """
        return self._request("DELETE", f"intents/{intent_id}")
    
    # High-level utility methods
    
    def create_path_intent(
        self,
        src_host: str,
        dst_host: str,
        priority: int = 100,
        bidirectional: bool = True,
    ) -> Dict:
        """
        Create a host-to-host path intent.
        
        Args:
            src_host: Source host ID
            dst_host: Destination host ID
            priority: Intent priority
            bidirectional: Whether to create a bidirectional path
        
        Returns:
            Response data
        """
        intent = {
            "type": "HostToHostIntent",
            "appId": "org.onosproject.federated-learning",
            "priority": priority,
            "one": src_host,
            "two": dst_host,
            "bidirectional": bidirectional,
        }
        return self.add_intent(intent)
    
    def allocate_bandwidth(
        self,
        src_device: str,
        dst_device: str,
        bandwidth_mbps: int,
        priority: int = 100,
    ) -> Dict:
        """
        Allocate bandwidth between two devices.
        
        Args:
            src_device: Source device ID
            dst_device: Destination device ID
            bandwidth_mbps: Bandwidth in Mbps
            priority: Flow priority
        
        Returns:
            Response data
        """
        # Convert bandwidth to bits per second
        bandwidth_bps = bandwidth_mbps * 1000000
        
        # Find the connecting link
        links = self.get_topology_links()
        target_link = None
        
        for link in links:
            if (link["src"]["device"] == src_device and link["dst"]["device"] == dst_device):
                target_link = link
                break
        
        if not target_link:
            logger.error(f"No link found between {src_device} and {dst_device}")
            raise ValueError(f"No link found between {src_device} and {dst_device}")
        
        # Create a meter for bandwidth control
        meter = {
            "deviceId": src_device,
            "appId": "org.onosproject.federated-learning",
            "unit": "KB_PER_SEC",
            "bands": [
                {
                    "type": "DROP",
                    "rate": bandwidth_mbps * 1000,  # Convert to KB/s
                    "burstSize": 1000,
                    "prec": 0
                }
            ]
        }
        
        # Add the meter
        meter_result = self._request("POST", "meters", data=meter)
        meter_id = meter_result.get("id")
        
        if not meter_id:
            logger.error("Failed to create meter")
            raise RuntimeError("Failed to create meter")
        
        # Create flow rule that uses the meter
        flow = {
            "priority": priority,
            "timeout": 0,
            "isPermanent": True,
            "deviceId": src_device,
            "treatment": {
                "instructions": [
                    {"type": "OUTPUT", "port": target_link["src"]["port"]},
                    {"type": "METER", "meterId": meter_id}
                ]
            },
            "selector": {
                "criteria": [
                    {"type": "ETH_DST", "mac": "FF:FF:FF:FF:FF:FF"},
                    {"type": "ETH_TYPE", "ethType": "0x800"}
                ]
            }
        }
        
        # Add the flow rule
        return self.add_flow(src_device, flow)
    
    def reroute_traffic(
        self,
        src_host: str,
        dst_host: str,
        priority: int = 200,
    ) -> Dict:
        """
        Reroute traffic between two hosts with higher priority.
        
        Args:
            src_host: Source host ID
            dst_host: Destination host ID
            priority: Intent priority (higher than existing intents)
        
        Returns:
            Response data
        """
        # Get existing intents to check for paths to override
        intents = self.get_intents()
        
        # Remove any existing host-to-host intents between these hosts
        for intent in intents:
            if (
                intent.get("type") == "HostToHostIntent"
                and intent.get("one") == src_host
                and intent.get("two") == dst_host
            ):
                self.remove_intent(intent["id"])
        
        # Create a new intent with higher priority
        return self.create_path_intent(src_host, dst_host, priority)
    
    def isolate_node(self, host_id: str, duration_seconds: int = 300) -> Dict:
        """
        Temporarily isolate a host from the network.
        
        Args:
            host_id: Host ID to isolate
            duration_seconds: Duration of isolation in seconds
        
        Returns:
            Dictionary with isolation status
        """
        # Get host details
        host = self.get_host(host_id)
        if not host:
            logger.error(f"Host {host_id} not found")
            raise ValueError(f"Host {host_id} not found")
        
        # Get the device this host is connected to
        location = host.get("locations", [{}])[0] if host.get("locations") else {}
        if not location:
            logger.error(f"Host {host_id} location not found")
            raise ValueError(f"Host {host_id} location not found")
        
        device_id = location.get("elementId")
        port = location.get("port")
        
        if not device_id or not port:
            logger.error(f"Host {host_id} device or port not found")
            raise ValueError(f"Host {host_id} device or port not found")
        
        # Create a flow rule to drop all traffic from this host
        flow = {
            "priority": 1000,  # High priority
            "timeout": duration_seconds,
            "isPermanent": False,
            "deviceId": device_id,
            "treatment": {
                "instructions": [
                    {"type": "NOACTION"}
                ]
            },
            "selector": {
                "criteria": [
                    {"type": "IN_PORT", "port": port},
                    {"type": "ETH_SRC", "mac": host.get("mac")}
                ]
            }
        }
        
        # Add the flow rule
        result = self.add_flow(device_id, flow)
        return {
            "status": "isolated",
            "host_id": host_id,
            "duration_seconds": duration_seconds,
            "flow_result": result
        }


# Create a default client for easy import
default_client = ONOSClient() 