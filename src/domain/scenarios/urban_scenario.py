"""
Urban Federated Learning Scenario

This module implements an urban federated learning scenario with heterogeneous clients
in a city environment with realistic network conditions.
"""
from typing import Dict, Any, List
from src.domain.interfaces.simulation_scenario import ISimulationScenario


class UrbanScenario(ISimulationScenario):
    """
    An urban federated learning scenario simulating a city environment.
    
    This scenario simulates:
    - Mobile and stationary clients with varying capabilities
    - Urban network infrastructure with varying signal quality
    - Rush hour congestion patterns
    - WiFi/cellular handovers
    - High device heterogeneity
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the urban scenario.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.base_config = self._create_config()
        self.config = self.base_config
        
        # Override with custom config if provided
        if config:
            for key, value in config.items():
                if key in self.config:
                    self.config[key] = value
    
    def get_name(self) -> str:
        """
        Get the scenario name.
        
        Returns:
            Scenario name
        """
        return "Urban Federated Learning Scenario"
    
    def get_description(self) -> str:
        """
        Get the scenario description.
        
        Returns:
            Scenario description
        """
        return (
            "An urban federated learning scenario with mobile and stationary clients, "
            "varying network conditions simulating a city environment, including "
            "rush hour traffic patterns, WiFi/cellular handovers, and realistic "
            "urban network infrastructure."
        )
    
    def get_topology_config(self) -> Dict[str, Any]:
        """
        Get the network topology configuration.
        
        Returns:
            Topology configuration dictionary
        """
        return self.config["topology"]
    
    def get_server_config(self) -> Dict[str, Any]:
        """
        Get the server configuration.
        
        Returns:
            Server configuration dictionary
        """
        return self.config["server"]
    
    def get_client_configs(self) -> List[Dict[str, Any]]:
        """
        Get the client configurations.
        
        Returns:
            List of client configuration dictionaries
        """
        return self.config["clients"]
    
    def get_sdn_policies(self) -> List[Dict[str, Any]]:
        """
        Get the SDN policies for the scenario.
        
        Returns:
            List of SDN policy dictionaries
        """
        return self.config["sdn_policies"]
    
    def get_network_conditions(self) -> List[Dict[str, Any]]:
        """
        Get the network conditions for the scenario.
        
        Returns:
            List of network condition dictionaries
        """
        return self.config["network_conditions"]
    
    def get_simulation_events(self) -> List[Dict[str, Any]]:
        """
        Get the simulation events for the scenario.
        
        Returns:
            List of simulation event dictionaries
        """
        return self.config["simulation_events"]
    
    def get_expected_metrics(self) -> Dict[str, Any]:
        """
        Get the expected metrics for the scenario.
        
        Returns:
            Dictionary of expected metrics
        """
        return self.config["expected_metrics"]
    
    def _create_config(self) -> Dict[str, Any]:
        """
        Create the default configuration for the urban scenario.
        
        Returns:
            Configuration dictionary
        """
        # Network topology representing urban infrastructure
        topology = {
            "type": "custom",
            "nodes": [
                # Core network
                {"id": "core", "type": "server", "location": {"x": 0, "y": 0}},
                
                # Cell towers (LTE/5G)
                {"id": "cell_tower_1", "type": "switch", "location": {"x": -20, "y": 20}},
                {"id": "cell_tower_2", "type": "switch", "location": {"x": 20, "y": 20}},
                {"id": "cell_tower_3", "type": "switch", "location": {"x": 0, "y": -20}},
                
                # WiFi access points
                {"id": "wifi_ap_1", "type": "switch", "location": {"x": -10, "y": 10}},
                {"id": "wifi_ap_2", "type": "switch", "location": {"x": 10, "y": 10}},
                {"id": "wifi_ap_3", "type": "switch", "location": {"x": -10, "y": -10}},
                {"id": "wifi_ap_4", "type": "switch", "location": {"x": 10, "y": -10}},
                
                # Local edge servers
                {"id": "edge_server_1", "type": "switch", "location": {"x": -15, "y": 15}},
                {"id": "edge_server_2", "type": "switch", "location": {"x": 15, "y": 15}},
            ],
            "links": [
                # Core to cell towers
                {"source": "core", "target": "cell_tower_1", "bandwidth": 1000, "delay": "10ms", "loss": 0.001},
                {"source": "core", "target": "cell_tower_2", "bandwidth": 1000, "delay": "10ms", "loss": 0.001},
                {"source": "core", "target": "cell_tower_3", "bandwidth": 1000, "delay": "10ms", "loss": 0.001},
                
                # Core to edge servers
                {"source": "core", "target": "edge_server_1", "bandwidth": 2000, "delay": "5ms", "loss": 0.0005},
                {"source": "core", "target": "edge_server_2", "bandwidth": 2000, "delay": "5ms", "loss": 0.0005},
                
                # Edge servers to WiFi APs
                {"source": "edge_server_1", "target": "wifi_ap_1", "bandwidth": 500, "delay": "2ms", "loss": 0.001},
                {"source": "edge_server_1", "target": "wifi_ap_3", "bandwidth": 500, "delay": "2ms", "loss": 0.001},
                {"source": "edge_server_2", "target": "wifi_ap_2", "bandwidth": 500, "delay": "2ms", "loss": 0.001},
                {"source": "edge_server_2", "target": "wifi_ap_4", "bandwidth": 500, "delay": "2ms", "loss": 0.001},
                
                # Edge servers to cell towers
                {"source": "edge_server_1", "target": "cell_tower_1", "bandwidth": 800, "delay": "3ms", "loss": 0.0008},
                {"source": "edge_server_2", "target": "cell_tower_2", "bandwidth": 800, "delay": "3ms", "loss": 0.0008},
            ]
        }
        
        # Server configuration
        server_config = {
            "host": "0.0.0.0",
            "port": 5000,
            "model_aggregation": "federated_averaging",
            "min_clients": 5,
            "max_clients": 30,
            "min_client_availability": 0.6,  # 60% client availability required
            "rounds": 50,
            "epochs": 3,
            "batch_size": 32,
            "learning_rate": 0.01,
            "target_accuracy": 0.85
        }
        
        # Client configurations representing urban devices
        clients = []
        
        # Smartphone clients (varying capabilities)
        for i in range(1, 16):
            # Determine connectivity based on client ID
            connectivity = "cellular" if i % 3 == 0 else "wifi"
            mobility = "stationary" if i % 5 == 0 else "mobile"
            
            # Determine attachment point based on connectivity
            if connectivity == "cellular":
                tower_id = (i % 3) + 1
                attachment_point = f"cell_tower_{tower_id}"
            else:
                ap_id = (i % 4) + 1
                attachment_point = f"wifi_ap_{ap_id}"
            
            # Set performance level based on client ID
            if i % 10 <= 2:  # 30% high-end phones
                performance = "high"
                training_speed = 100
                battery_level = 80 + (i % 20)
                data_samples = 5000 + (i * 100)
                bandwidth = 50 if connectivity == "wifi" else 20
            elif i % 10 <= 7:  # 50% mid-range phones
                performance = "medium"
                training_speed = 60
                battery_level = 60 + (i % 30)
                data_samples = 3000 + (i * 80)
                bandwidth = 30 if connectivity == "wifi" else 15
            else:  # 20% low-end phones
                performance = "low"
                training_speed = 30
                battery_level = 40 + (i % 40)
                data_samples = 1000 + (i * 50)
                bandwidth = 15 if connectivity == "wifi" else 10
            
            clients.append({
                "id": f"smartphone_{i}",
                "type": "smartphone",
                "performance": performance,
                "connection_type": connectivity,
                "mobility": mobility,
                "attachment_point": attachment_point,
                "training_speed": training_speed,  # samples/second
                "resources": {
                    "battery_level": battery_level,
                    "charging": i % 3 == 0,
                    "memory_mb": 2000 if performance == "high" else (1000 if performance == "medium" else 500),
                    "cpu_cores": 8 if performance == "high" else (4 if performance == "medium" else 2),
                    "network_bandwidth_mbps": bandwidth
                },
                "data": {
                    "data_samples": data_samples,
                    "data_distribution": "heterogeneous"
                },
                "location": {
                    "latitude": 40.7128 + (i * 0.01),
                    "longitude": -74.0060 + (i * 0.01),
                    "mobility_pattern": "random_walk" if mobility == "mobile" else "stationary"
                }
            })
        
        # Laptop/Desktop clients (higher stability and resources)
        for i in range(1, 6):
            # All laptops use WiFi
            ap_id = (i % 4) + 1
            attachment_point = f"wifi_ap_{ap_id}"
            
            clients.append({
                "id": f"laptop_{i}",
                "type": "laptop",
                "performance": "high",
                "connection_type": "wifi",
                "mobility": "stationary",
                "attachment_point": attachment_point,
                "training_speed": 150,  # samples/second
                "resources": {
                    "battery_level": 90 if i % 2 == 0 else 100,
                    "charging": True,
                    "memory_mb": 8000,
                    "cpu_cores": 8,
                    "network_bandwidth_mbps": 100
                },
                "data": {
                    "data_samples": 8000 + (i * 500),
                    "data_distribution": "heterogeneous"
                },
                "location": {
                    "latitude": 40.7128 + (i * 0.005),
                    "longitude": -74.0060 + (i * 0.005),
                    "mobility_pattern": "stationary"
                }
            })
        
        # IoT device clients (lower capabilities but stable)
        for i in range(1, 10):
            # IoT devices alternate between WiFi and cellular
            connectivity = "cellular" if i % 2 == 0 else "wifi"
            
            # Determine attachment point based on connectivity
            if connectivity == "cellular":
                tower_id = (i % 3) + 1
                attachment_point = f"cell_tower_{tower_id}"
            else:
                ap_id = (i % 4) + 1
                attachment_point = f"wifi_ap_{ap_id}"
            
            clients.append({
                "id": f"iot_device_{i}",
                "type": "iot",
                "performance": "low",
                "connection_type": connectivity,
                "mobility": "stationary",
                "attachment_point": attachment_point,
                "training_speed": 20,  # samples/second
                "resources": {
                    "battery_level": 70 + (i % 30),
                    "charging": True,
                    "memory_mb": 200,
                    "cpu_cores": 1,
                    "network_bandwidth_mbps": 5 if connectivity == "wifi" else 2
                },
                "data": {
                    "data_samples": 800 + (i * 100),
                    "data_distribution": "specialized"
                },
                "location": {
                    "latitude": 40.7128 - (i * 0.008),
                    "longitude": -74.0060 - (i * 0.008),
                    "mobility_pattern": "stationary"
                }
            })
        
        # Urban network conditions (including interference and congestion)
        network_conditions = [
            # Cell tower backhaul congestion at peak hours
            {"source": "cell_tower_1", "target": "edge_server_1", "bandwidth": 400, "delay": "15ms", "loss": 0.01, 
             "time_periods": [{"start": "08:00", "end": "10:00"}, {"start": "17:00", "end": "19:00"}]},
            {"source": "cell_tower_2", "target": "edge_server_2", "bandwidth": 400, "delay": "15ms", "loss": 0.01, 
             "time_periods": [{"start": "08:00", "end": "10:00"}, {"start": "17:00", "end": "19:00"}]},
            
            # WiFi congestion in business areas during work hours
            {"source": "wifi_ap_1", "target": "edge_server_1", "bandwidth": 250, "delay": "8ms", "loss": 0.02, 
             "time_periods": [{"start": "09:00", "end": "17:00"}]},
            {"source": "wifi_ap_2", "target": "edge_server_2", "bandwidth": 250, "delay": "8ms", "loss": 0.02, 
             "time_periods": [{"start": "09:00", "end": "17:00"}]},
            
            # Residential WiFi congestion in evenings
            {"source": "wifi_ap_3", "target": "edge_server_1", "bandwidth": 300, "delay": "10ms", "loss": 0.015, 
             "time_periods": [{"start": "18:00", "end": "23:00"}]},
            {"source": "wifi_ap_4", "target": "edge_server_2", "bandwidth": 300, "delay": "10ms", "loss": 0.015, 
             "time_periods": [{"start": "18:00", "end": "23:00"}]},
        ]
        
        # SDN policies for urban network management
        sdn_policies = [
            {
                "name": "urban_traffic_management",
                "type": "trafficEngineering",
                "config": {
                    "priority_applications": ["federated_learning"],
                    "congestion_threshold": 0.8,
                    "max_reroute_attempts": 3,
                    "qos_settings": {
                        "federated_learning": {
                            "min_bandwidth": 10,
                            "priority": "high"
                        }
                    }
                }
            },
            {
                "name": "handover_management",
                "type": "mobilityManagement",
                "config": {
                    "triggers": {
                        "signal_threshold": -85,  # dBm
                        "load_threshold": 0.9,
                        "handover_hysteresis": 3  # dB
                    },
                    "preferred_connections": {
                        "high_performance": "wifi",
                        "medium_performance": "wifi",
                        "low_performance": "cellular"
                    }
                }
            }
        ]
        
        # Urban simulation events
        simulation_events = [
            # Rush hour congestion events
            {
                "type": "network_congestion",
                "trigger_time_seconds": 300,  # 5 minutes in
                "duration_seconds": 3600,  # 1 hour
                "data": {
                    "affected_links": [
                        {"source": "cell_tower_1", "target": "edge_server_1", "bandwidth_reduction": 0.5},
                        {"source": "cell_tower_2", "target": "edge_server_2", "bandwidth_reduction": 0.5}
                    ],
                    "reason": "Morning rush hour"
                }
            },
            {
                "type": "network_congestion",
                "trigger_time_seconds": 1800,  # 30 minutes in
                "duration_seconds": 3600,  # 1 hour
                "data": {
                    "affected_links": [
                        {"source": "wifi_ap_1", "target": "edge_server_1", "bandwidth_reduction": 0.4},
                        {"source": "wifi_ap_2", "target": "edge_server_2", "bandwidth_reduction": 0.4}
                    ],
                    "reason": "Business hours increased usage"
                }
            },
            
            # Client mobility events (device handovers)
            {
                "type": "client_handover",
                "trigger_time_seconds": 600,  # 10 minutes in
                "data": {
                    "client_id": "smartphone_3",
                    "from_attachment": "wifi_ap_1",
                    "to_attachment": "cell_tower_1",
                    "reason": "Leaving WiFi coverage area"
                }
            },
            {
                "type": "client_handover",
                "trigger_time_seconds": 1200,  # 20 minutes in
                "data": {
                    "client_id": "smartphone_7",
                    "from_attachment": "cell_tower_2",
                    "to_attachment": "wifi_ap_3",
                    "reason": "Entering WiFi coverage area"
                }
            },
            
            # Client battery events
            {
                "type": "battery_critical",
                "trigger_time_seconds": 1500,  # 25 minutes in
                "data": {
                    "client_id": "smartphone_10",
                    "battery_level": 10,
                    "action": "reduce_computation"
                }
            },
            
            # Temporary outages
            {
                "type": "link_failure",
                "trigger_time_seconds": 2100,  # 35 minutes in
                "duration_seconds": 300,  # 5 minutes
                "data": {
                    "source": "wifi_ap_4",
                    "target": "edge_server_2",
                    "reason": "Maintenance"
                }
            }
        ]
        
        # Expected metrics for validation
        expected_metrics = {
            "fl_performance": {
                "accuracy": {
                    "min": 0.8,
                    "target": 0.85,
                    "max": 0.95
                },
                "loss": {
                    "min": 0.05,
                    "target": 0.1,
                    "max": 0.2
                },
                "convergence_round": {
                    "min": 15,
                    "target": 25,
                    "max": 40
                }
            },
            "network_performance": {
                "average_round_time": {
                    "min": 30,  # seconds
                    "target": 60,
                    "max": 120
                },
                "client_dropout_rate": {
                    "min": 0.05,
                    "target": 0.1,
                    "max": 0.2
                },
                "average_bandwidth_utilization": {
                    "min": 0.3,
                    "target": 0.5,
                    "max": 0.7
                }
            }
        }
        
        return {
            "topology": topology,
            "server": server_config,
            "clients": clients,
            "network_conditions": network_conditions,
            "sdn_policies": sdn_policies,
            "simulation_events": simulation_events,
            "expected_metrics": expected_metrics
        } 