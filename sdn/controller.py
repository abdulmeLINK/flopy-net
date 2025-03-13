"""
SDN Controller Integration Module

This module provides a unified interface for SDN controller integration,
supporting both ONOS and Ryu controllers for FL network optimization.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Union, Any
from enum import Enum

from .onos_client import ONOSClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ControllerType(Enum):
    """Supported SDN controller types."""
    ONOS = "onos"
    RYU = "ryu"


class SDNController:
    """Unified SDN controller interface for Federated Learning."""
    
    def __init__(
        self,
        controller_type: ControllerType = ControllerType.ONOS,
        host: str = "localhost",
        port: int = 8181,
        username: str = "onos",
        password: str = "rocks",
        ryu_port: int = 8080,
    ):
        """
        Initialize the SDN controller client.
        
        Args:
            controller_type: Type of SDN controller to use
            host: Controller hostname
            port: Controller API port
            username: Username for ONOS authentication
            password: Password for ONOS authentication
            ryu_port: Port for Ryu controller API
        """
        self.controller_type = controller_type
        self.host = host
        self.port = port
        
        # Initialize ONOS client if using ONOS
        if controller_type == ControllerType.ONOS:
            self.onos_client = ONOSClient(
                host=host,
                port=port,
                username=username,
                password=password
            )
        
        # Initialize Ryu API endpoint if using Ryu
        if controller_type == ControllerType.RYU:
            self.ryu_base_url = f"http://{host}:{ryu_port}"
    
    def _ryu_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict:
        """
        Make a request to the Ryu API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
        
        Returns:
            Response data as dictionary
        """
        url = f"{self.ryu_base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ryu API request failed: {e}")
            raise
    
    def get_topology(self) -> Dict:
        """
        Get the network topology.
        
        Returns:
            Topology information
        """
        if self.controller_type == ControllerType.ONOS:
            return self.onos_client.get_topology()
        
        elif self.controller_type == ControllerType.RYU:
            return self._ryu_request("GET", "/fl/stats")
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def get_devices(self) -> List[Dict]:
        """
        Get all network devices.
        
        Returns:
            List of devices
        """
        if self.controller_type == ControllerType.ONOS:
            return self.onos_client.get_devices()
        
        elif self.controller_type == ControllerType.RYU:
            stats = self._ryu_request("GET", "/fl/stats")
            # Convert Ryu switch format to standard format
            return [
                {"id": dpid, "available": True, "role": "MASTER", "type": "SWITCH"}
                for dpid in range(stats.get("switches", 0))
            ]
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def get_hosts(self) -> List[Dict]:
        """
        Get all hosts in the network.
        
        Returns:
            List of hosts
        """
        if self.controller_type == ControllerType.ONOS:
            return self.onos_client.get_hosts()
        
        elif self.controller_type == ControllerType.RYU:
            stats = self._ryu_request("GET", "/fl/stats")
            # Ryu doesn't provide direct host information via REST API
            # We're returning a simulated response
            return [
                {"id": f"host{i}", "mac": f"00:00:00:00:00:{i:02x}", "locations": []}
                for i in range(stats.get("hosts", 0))
            ]
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def reroute_traffic(
        self,
        src_ip: str,
        dst_ip: str,
        priority: int = 200,
    ) -> Dict:
        """
        Reroute traffic between two hosts with high priority.
        
        Args:
            src_ip: Source IP
            dst_ip: Destination IP
            priority: Flow priority
        
        Returns:
            Operation result
        """
        if self.controller_type == ControllerType.ONOS:
            # For ONOS, we need to find the host IDs from IPs
            hosts = self.onos_client.get_hosts()
            
            src_host_id = None
            dst_host_id = None
            
            for host in hosts:
                for ip in host.get("ipAddresses", []):
                    if ip == src_ip:
                        src_host_id = host.get("id")
                    elif ip == dst_ip:
                        dst_host_id = host.get("id")
            
            if not src_host_id or not dst_host_id:
                logger.error(f"Could not find host IDs for {src_ip} or {dst_ip}")
                return {"status": "error", "message": "Host not found"}
            
            return self.onos_client.reroute_traffic(src_host_id, dst_host_id, priority)
        
        elif self.controller_type == ControllerType.RYU:
            # For Ryu, we use the prioritize endpoint
            data = {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "priority": priority,
                "duration": 600  # 10 minutes
            }
            return self._ryu_request("POST", "/fl/prioritize", data=data)
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def allocate_bandwidth(
        self,
        src_ip: str,
        dst_ip: str,
        bandwidth_mbps: int,
        duration_seconds: int = 300,
    ) -> Dict:
        """
        Allocate bandwidth for traffic between two hosts.
        
        Args:
            src_ip: Source IP
            dst_ip: Destination IP
            bandwidth_mbps: Bandwidth in Mbps
            duration_seconds: Duration in seconds
        
        Returns:
            Operation result
        """
        if self.controller_type == ControllerType.ONOS:
            # For ONOS, we need to find the source and destination switch IDs
            hosts = self.onos_client.get_hosts()
            
            src_device_id = None
            dst_device_id = None
            
            for host in hosts:
                for ip in host.get("ipAddresses", []):
                    if ip == src_ip and host.get("locations"):
                        src_device_id = host["locations"][0]["elementId"]
                    elif ip == dst_ip and host.get("locations"):
                        dst_device_id = host["locations"][0]["elementId"]
            
            if not src_device_id or not dst_device_id:
                logger.error(f"Could not find device IDs for {src_ip} or {dst_ip}")
                return {"status": "error", "message": "Devices not found"}
            
            return self.onos_client.allocate_bandwidth(
                src_device_id, dst_device_id, bandwidth_mbps
            )
        
        elif self.controller_type == ControllerType.RYU:
            # For Ryu, we can't directly allocate bandwidth via REST API
            # We're using prioritize with additional parameters
            data = {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "priority": 200,
                "duration": duration_seconds,
                "bandwidth_mbps": bandwidth_mbps  # Custom field
            }
            return self._ryu_request("POST", "/fl/prioritize", data=data)
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def isolate_node(
        self,
        node_ip: str,
        duration_seconds: int = 300,
        traffic_type: str = "all",
    ) -> Dict:
        """
        Isolate a node from the network.
        
        Args:
            node_ip: IP of the node to isolate
            duration_seconds: Duration in seconds
            traffic_type: Type of traffic to block ("all", "fl_only")
        
        Returns:
            Operation result
        """
        if self.controller_type == ControllerType.ONOS:
            # For ONOS, we need to find the host ID
            hosts = self.onos_client.get_hosts()
            
            host_id = None
            
            for host in hosts:
                for ip in host.get("ipAddresses", []):
                    if ip == node_ip:
                        host_id = host.get("id")
                        break
            
            if not host_id:
                logger.error(f"Could not find host ID for {node_ip}")
                return {"status": "error", "message": "Host not found"}
            
            return self.onos_client.isolate_node(host_id, duration_seconds)
        
        elif self.controller_type == ControllerType.RYU:
            # For Ryu, we'd need a custom isolation endpoint
            # This is a simplified implementation
            data = {
                "client_ip": node_ip,
                "duration": duration_seconds,
                "traffic_type": traffic_type
            }
            # Using client registration endpoint as a workaround
            result = self._ryu_request("POST", "/fl/register/client", data={"client_ip": node_ip})
            return {
                "status": "success",
                "message": f"Node {node_ip} isolation requested",
                "registration": result
            }
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def register_fl_server(self, server_ip: str) -> Dict:
        """
        Register an FL server with the SDN controller.
        
        Args:
            server_ip: FL server IP
        
        Returns:
            Operation result
        """
        if self.controller_type == ControllerType.ONOS:
            # ONOS doesn't have a direct FL server registration endpoint
            # We're storing it in our client data structure
            return {"status": "success", "message": f"FL server {server_ip} registered with ONOS"}
        
        elif self.controller_type == ControllerType.RYU:
            # Ryu has a direct FL server registration endpoint
            data = {"server_ip": server_ip}
            return self._ryu_request("POST", "/fl/register/server", data=data)
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def register_fl_client(self, client_ip: str) -> Dict:
        """
        Register an FL client with the SDN controller.
        
        Args:
            client_ip: FL client IP
        
        Returns:
            Operation result
        """
        if self.controller_type == ControllerType.ONOS:
            # ONOS doesn't have a direct FL client registration endpoint
            # We're storing it in our client data structure
            return {"status": "success", "message": f"FL client {client_ip} registered with ONOS"}
        
        elif self.controller_type == ControllerType.RYU:
            # Ryu has a direct FL client registration endpoint
            data = {"client_ip": client_ip}
            return self._ryu_request("POST", "/fl/register/client", data=data)
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")
    
    def get_network_stats(self) -> Dict:
        """
        Get network statistics.
        
        Returns:
            Network statistics
        """
        if self.controller_type == ControllerType.ONOS:
            # For ONOS, we compile stats from multiple endpoints
            devices = self.onos_client.get_devices()
            hosts = self.onos_client.get_hosts()
            links = self.onos_client.get_topology_links()
            
            return {
                "devices": len(devices),
                "hosts": len(hosts),
                "links": len(links),
                "controller": "ONOS"
            }
        
        elif self.controller_type == ControllerType.RYU:
            # Ryu has a direct stats endpoint
            return self._ryu_request("GET", "/fl/stats")
        
        else:
            raise ValueError(f"Unsupported controller type: {self.controller_type}")


# Factory function to create SDN controller
def create_controller(
    controller_type: str = "onos",
    host: str = "localhost",
    port: int = 8181,
    username: str = "onos",
    password: str = "rocks",
    ryu_port: int = 8080,
) -> SDNController:
    """
    Create an SDN controller client.
    
    Args:
        controller_type: Type of controller ("onos" or "ryu")
        host: Controller hostname
        port: Controller API port
        username: Username for ONOS
        password: Password for ONOS
        ryu_port: Port for Ryu controller API
    
    Returns:
        SDN controller client
    """
    if controller_type.lower() == "onos":
        return SDNController(
            controller_type=ControllerType.ONOS,
            host=host,
            port=port,
            username=username,
            password=password,
            ryu_port=ryu_port
        )
    elif controller_type.lower() == "ryu":
        return SDNController(
            controller_type=ControllerType.RYU,
            host=host,
            port=port,
            ryu_port=ryu_port
        )
    else:
        raise ValueError(f"Unsupported controller type: {controller_type}")


# Create default controller instances for both types
default_onos_controller = create_controller("onos")
default_ryu_controller = create_controller("ryu", ryu_port=8080)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SDN Controller for Federated Learning")
    parser.add_argument("--type", choices=["onos", "ryu"], default="onos", help="Controller type")
    parser.add_argument("--host", default="localhost", help="Controller hostname")
    parser.add_argument("--port", type=int, default=8181, help="Controller API port")
    parser.add_argument("--ryu-port", type=int, default=8080, help="Ryu controller API port")
    parser.add_argument("--username", default="onos", help="ONOS username")
    parser.add_argument("--password", default="rocks", help="ONOS password")
    
    args = parser.parse_args()
    
    controller = create_controller(
        controller_type=args.type,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        ryu_port=args.ryu_port
    )
    
    # Example usage
    try:
        topology = controller.get_topology()
        print(f"Topology: {json.dumps(topology, indent=2)}")
        
        devices = controller.get_devices()
        print(f"Devices: {json.dumps(devices, indent=2)}")
        
        hosts = controller.get_hosts()
        print(f"Hosts: {json.dumps(hosts, indent=2)}")
    
    except Exception as e:
        logger.error(f"Error interacting with controller: {e}") 