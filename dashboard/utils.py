"""
Dashboard Utilities

This module provides utility functions for the dashboard to interact with
the FL server, SDN controller, and policy engine.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
import time
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
POLICY_ENGINE_URL = os.environ.get("POLICY_ENGINE_URL", "http://localhost:8000")
SDN_CONTROLLER_URL = os.environ.get("SDN_CONTROLLER_URL", "http://localhost:8181/onos/v1")
FL_SERVER_URL = os.environ.get("FL_SERVER_URL", "http://localhost:8080")


class DashboardConnector:
    """
    Connector class for the dashboard to interact with the FL server,
    SDN controller, and policy engine.
    """

    def __init__(
        self,
        policy_engine_url: str = POLICY_ENGINE_URL,
        sdn_controller_url: str = SDN_CONTROLLER_URL,
        fl_server_url: str = FL_SERVER_URL,
    ):
        """
        Initialize the dashboard connector.

        Args:
            policy_engine_url: URL of the policy engine API
            sdn_controller_url: URL of the SDN controller API
            fl_server_url: URL of the FL server API
        """
        self.policy_engine_url = policy_engine_url
        self.sdn_controller_url = sdn_controller_url
        self.fl_server_url = fl_server_url
        self.session = requests.Session()
        # Add authentication if needed
        # self.session.auth = ("username", "password")

    def get_network_topology(self) -> Dict[str, Any]:
        """
        Get the network topology from the SDN controller.

        Returns:
            Dict containing network topology information
        """
        try:
            response = self.session.get(f"{self.sdn_controller_url}/topology")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get network topology: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting network topology: {e}")
            return {}

    def get_network_devices(self) -> List[Dict[str, Any]]:
        """
        Get the network devices from the SDN controller.

        Returns:
            List of devices
        """
        try:
            response = self.session.get(f"{self.sdn_controller_url}/devices")
            if response.status_code == 200:
                return response.json().get("devices", [])
            else:
                logger.error(f"Failed to get network devices: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting network devices: {e}")
            return []

    def get_network_hosts(self) -> List[Dict[str, Any]]:
        """
        Get the network hosts from the SDN controller.

        Returns:
            List of hosts
        """
        try:
            response = self.session.get(f"{self.sdn_controller_url}/hosts")
            if response.status_code == 200:
                return response.json().get("hosts", [])
            else:
                logger.error(f"Failed to get network hosts: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting network hosts: {e}")
            return []

    def get_network_links(self) -> List[Dict[str, Any]]:
        """
        Get the network links from the SDN controller.

        Returns:
            List of links
        """
        try:
            response = self.session.get(f"{self.sdn_controller_url}/links")
            if response.status_code == 200:
                return response.json().get("links", [])
            else:
                logger.error(f"Failed to get network links: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting network links: {e}")
            return []

    def get_network_statistics(self) -> Dict[str, Any]:
        """
        Get network statistics from the SDN controller.

        Returns:
            Dict containing network statistics
        """
        try:
            response = self.session.get(f"{self.sdn_controller_url}/statistics")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get network statistics: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting network statistics: {e}")
            return {}

    def get_fl_status(self) -> Dict[str, Any]:
        """
        Get the FL training status from the FL server.

        Returns:
            Dict containing FL training status
        """
        try:
            response = self.session.get(f"{self.fl_server_url}/status")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get FL status: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting FL status: {e}")
            return {}

    def get_fl_metrics(self) -> Dict[str, Any]:
        """
        Get the FL training metrics from the FL server.

        Returns:
            Dict containing FL training metrics
        """
        try:
            response = self.session.get(f"{self.fl_server_url}/metrics")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get FL metrics: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting FL metrics: {e}")
            return {}

    def get_fl_clients(self) -> List[Dict[str, Any]]:
        """
        Get the FL clients from the FL server.

        Returns:
            List of FL clients
        """
        try:
            response = self.session.get(f"{self.fl_server_url}/clients")
            if response.status_code == 200:
                return response.json().get("clients", [])
            else:
                logger.error(f"Failed to get FL clients: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting FL clients: {e}")
            return []

    def get_policies(self) -> List[Dict[str, Any]]:
        """
        Get the policies from the policy engine.

        Returns:
            List of policies
        """
        try:
            response = self.session.get(f"{self.policy_engine_url}/policies")
            if response.status_code == 200:
                return response.json().get("policies", [])
            else:
                logger.error(f"Failed to get policies: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting policies: {e}")
            return []

    def get_active_policies(self) -> List[Dict[str, Any]]:
        """
        Get the active policies from the policy engine.

        Returns:
            List of active policies
        """
        try:
            response = self.session.get(f"{self.policy_engine_url}/policies/active")
            if response.status_code == 200:
                return response.json().get("policies", [])
            else:
                logger.error(f"Failed to get active policies: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting active policies: {e}")
            return []

    def get_policy_history(self) -> List[Dict[str, Any]]:
        """
        Get the policy execution history from the policy engine.

        Returns:
            List of policy execution history entries
        """
        try:
            response = self.session.get(f"{self.policy_engine_url}/policies/history")
            if response.status_code == 200:
                return response.json().get("history", [])
            else:
                logger.error(f"Failed to get policy history: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting policy history: {e}")
            return []

    def get_trust_scores(self) -> Dict[str, float]:
        """
        Get the trust scores for FL clients from the policy engine.

        Returns:
            Dict mapping client IDs to trust scores
        """
        try:
            response = self.session.get(f"{self.policy_engine_url}/trust-scores")
            if response.status_code == 200:
                return response.json().get("trust_scores", {})
            else:
                logger.error(f"Failed to get trust scores: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting trust scores: {e}")
            return {}

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get all data needed for the dashboard.

        Returns:
            Dict containing all data for the dashboard
        """
        network_data = {
            "devices": self.get_network_devices(),
            "hosts": self.get_network_hosts(),
            "links": self.get_network_links(),
            "statistics": self.get_network_statistics(),
            "topology": self.get_network_topology(),
        }

        fl_data = {
            "status": self.get_fl_status(),
            "metrics": self.get_fl_metrics(),
            "clients": self.get_fl_clients(),
        }

        policy_data = {
            "policies": self.get_policies(),
            "active_policies": self.get_active_policies(),
            "history": self.get_policy_history(),
            "trust_scores": self.get_trust_scores(),
        }

        return {
            "network": network_data,
            "fl": fl_data,
            "policy": policy_data,
            "timestamp": datetime.now().isoformat(),
        }


# Mock data generator for testing
class MockDataGenerator:
    """
    Generate mock data for testing the dashboard.
    """

    @staticmethod
    def generate_network_data() -> Dict[str, Any]:
        """
        Generate mock network data.

        Returns:
            Dict containing mock network data
        """
        devices = [
            {
                "id": f"of:000000000000000{i}",
                "type": "SWITCH",
                "available": True,
                "role": "MASTER",
                "mfr": "Nicira, Inc.",
                "hw": "Open vSwitch",
                "sw": "2.5.0",
                "serial": "None",
                "chassisId": f"00:00:00:00:00:0{i}",
            }
            for i in range(1, 6)
        ]

        hosts = [
            {
                "id": f"00:00:00:00:00:0{i}/1",
                "mac": f"00:00:00:00:00:0{i}",
                "vlan": "None",
                "locations": [
                    {
                        "elementId": f"of:000000000000000{(i % 5) + 1}",
                        "port": f"{i}",
                    }
                ],
                "ip": [f"10.0.0.{i}"],
                "configured": False,
            }
            for i in range(1, 11)
        ]

        links = [
            {
                "src": {
                    "port": "1",
                    "device": f"of:000000000000000{i}",
                },
                "dst": {
                    "port": "2",
                    "device": f"of:000000000000000{j}",
                },
                "type": "DIRECT",
                "state": "ACTIVE",
            }
            for i in range(1, 5)
            for j in range(i + 1, 6)
        ]

        return {
            "devices": devices,
            "hosts": hosts,
            "links": links,
            "statistics": {
                "topology_stp_cost": {"value": 15},
                "topology_stp_time": {"value": 3},
                "topology_stp_count": {"value": 5},
            },
            "topology": {
                "time": int(time.time() * 1000),
                "devices": len(devices),
                "hosts": len(hosts),
                "links": len(links),
                "clusters": 1,
            },
        }

    @staticmethod
    def generate_fl_data() -> Dict[str, Any]:
        """
        Generate mock FL data.

        Returns:
            Dict containing mock FL data
        """
        current_round = 10
        
        status = {
            "status": "TRAINING",
            "current_round": current_round,
            "total_rounds": 20,
            "active_clients": 8,
            "total_clients": 10,
            "start_time": (datetime.now() - timedelta(hours=2)).isoformat(),
            "estimated_completion": (datetime.now() + timedelta(hours=2)).isoformat(),
        }
        
        metrics = {
            "rounds": list(range(1, current_round + 1)),
            "accuracy": [0.5 + i * 0.04 for i in range(current_round)],
            "loss": [0.5 - i * 0.04 for i in range(current_round)],
            "client_participation": [7, 8, 10, 9, 8, 7, 8, 9, 10, 8][:current_round],
            "training_time_per_round": [120 - i * 5 for i in range(current_round)],
        }
        
        clients = [
            {
                "id": f"client_{i}",
                "ip": f"10.0.0.{i}",
                "status": "ACTIVE" if i <= 8 else "INACTIVE",
                "last_seen": datetime.now().isoformat() if i <= 8 else (datetime.now() - timedelta(minutes=30)).isoformat(),
                "data_samples": 1000 + i * 100,
                "trust_score": round(0.5 + i * 0.05, 2),
                "training_time": 60 - i * 3,
                "bandwidth": 10 + i * 2,
                "latency": 50 - i * 3 if i <= 8 else 100,
            }
            for i in range(1, 11)
        ]
        
        return {
            "status": status,
            "metrics": metrics,
            "clients": clients,
        }

    @staticmethod
    def generate_policy_data() -> Dict[str, Any]:
        """
        Generate mock policy data.

        Returns:
            Dict containing mock policy data
        """
        policies = [
            {
                "id": "net_opt_001",
                "name": "High Latency Rerouting",
                "description": "Reroute traffic when latency exceeds threshold",
                "type": "SDN",
                "status": "ACTIVE",
                "conditions": [
                    {
                        "metric": "latency",
                        "operator": "gt",
                        "value": 100,
                    }
                ],
                "actions": [
                    {
                        "action": "reroute",
                        "parameters": {"priority": "high"},
                    }
                ],
                "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            },
            {
                "id": "fl_node_001",
                "name": "High Trust Node Selection",
                "description": "Select nodes with high trust scores for training",
                "type": "FL",
                "status": "ACTIVE",
                "conditions": [
                    {
                        "metric": "trust_score",
                        "operator": "lt",
                        "value": 0.7,
                    }
                ],
                "actions": [
                    {
                        "action": "exclude_client",
                        "parameters": {},
                    }
                ],
                "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
            },
            {
                "id": "security_001",
                "name": "Anomaly Detection",
                "description": "Detect and respond to anomalous behavior",
                "type": "SECURITY",
                "status": "STANDBY",
                "conditions": [
                    {
                        "metric": "model_update",
                        "operator": "anomaly",
                        "value": 0.9,
                    }
                ],
                "actions": [
                    {
                        "action": "isolate_node",
                        "parameters": {"duration": 3600},
                    }
                ],
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            },
            {
                "id": "resource_001",
                "name": "Resource Allocation",
                "description": "Allocate bandwidth based on training progress",
                "type": "SDN",
                "status": "ACTIVE",
                "conditions": [
                    {
                        "metric": "training_progress",
                        "operator": "gt",
                        "value": 0.8,
                    }
                ],
                "actions": [
                    {
                        "action": "allocate_bandwidth",
                        "parameters": {"bandwidth": 50},
                    }
                ],
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
            },
            {
                "id": "qos_001",
                "name": "QoS for FL Traffic",
                "description": "Apply QoS to FL traffic",
                "type": "SDN",
                "status": "ACTIVE",
                "conditions": [
                    {
                        "metric": "traffic_type",
                        "operator": "eq",
                        "value": "FL",
                    }
                ],
                "actions": [
                    {
                        "action": "apply_qos",
                        "parameters": {"priority": "high"},
                    }
                ],
                "created_at": (datetime.now() - timedelta(days=4)).isoformat(),
            },
        ]
        
        active_policies = [p for p in policies if p["status"] == "ACTIVE"]
        
        history = [
            {
                "policy_id": p["id"],
                "timestamp": (datetime.now() - timedelta(minutes=i * 10)).isoformat(),
                "result": "SUCCESS" if i % 3 != 0 else "FAILURE",
                "details": "Policy executed successfully" if i % 3 != 0 else "Failed to execute policy",
            }
            for i, p in enumerate(policies)
            for _ in range(3)  # 3 history entries per policy
        ]
        
        trust_scores = {
            f"client_{i}": round(0.5 + i * 0.05, 2) for i in range(1, 11)
        }
        
        return {
            "policies": policies,
            "active_policies": active_policies,
            "history": history,
            "trust_scores": trust_scores,
        }

    @classmethod
    def generate_dashboard_data(cls) -> Dict[str, Any]:
        """
        Generate all mock data for the dashboard.

        Returns:
            Dict containing all mock data for the dashboard
        """
        return {
            "network": cls.generate_network_data(),
            "fl": cls.generate_fl_data(),
            "policy": cls.generate_policy_data(),
            "timestamp": datetime.now().isoformat(),
        }


# Helper functions for data processing
def process_network_topology(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process network topology data for visualization.

    Args:
        network_data: Raw network data

    Returns:
        Processed network data for visualization
    """
    # Extract devices, hosts, and links
    devices = network_data.get("devices", [])
    hosts = network_data.get("hosts", [])
    links = network_data.get("links", [])
    
    # Create a networkx graph
    import networkx as nx
    G = nx.Graph()
    
    # Add devices as nodes
    for device in devices:
        G.add_node(
            device["id"],
            type="device",
            label=device["id"].split(":")[-1],
            data=device,
        )
    
    # Add hosts as nodes
    for host in hosts:
        G.add_node(
            host["id"],
            type="host",
            label=host["id"].split("/")[0],
            data=host,
        )
        
        # Connect hosts to devices
        for location in host.get("locations", []):
            G.add_edge(
                host["id"],
                location["elementId"],
                type="host-device",
            )
    
    # Add links between devices
    for link in links:
        G.add_edge(
            link["src"]["device"],
            link["dst"]["device"],
            type="device-device",
            data=link,
        )
    
    # Generate positions for visualization
    pos = nx.spring_layout(G)
    
    # Convert to format for Plotly
    edge_x = []
    edge_y = []
    edge_text = []
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_text.append(f"Type: {edge[2]['type']}")
    
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []
    
    for node in G.nodes(data=True):
        x, y = pos[node[0]]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{node[1]['label']} ({node[1]['type']})")
        node_color.append(0 if node[1]['type'] == 'device' else 1)
        node_size.append(15 if node[1]['type'] == 'device' else 10)
    
    return {
        "edge_x": edge_x,
        "edge_y": edge_y,
        "edge_text": edge_text,
        "node_x": node_x,
        "node_y": node_y,
        "node_text": node_text,
        "node_color": node_color,
        "node_size": node_size,
    }


def process_fl_metrics(fl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process FL metrics data for visualization.

    Args:
        fl_data: Raw FL data

    Returns:
        Processed FL metrics for visualization
    """
    metrics = fl_data.get("metrics", {})
    
    return {
        "rounds": metrics.get("rounds", []),
        "accuracy": metrics.get("accuracy", []),
        "loss": metrics.get("loss", []),
        "client_participation": metrics.get("client_participation", []),
        "training_time": metrics.get("training_time_per_round", []),
    }


def process_trust_scores(policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process trust scores for visualization.

    Args:
        policy_data: Raw policy data

    Returns:
        Processed trust scores for visualization
    """
    trust_scores = policy_data.get("trust_scores", {})
    
    nodes = []
    scores = []
    
    for node, score in trust_scores.items():
        nodes.append(node)
        scores.append(score)
    
    return {
        "nodes": nodes,
        "scores": scores,
    } 