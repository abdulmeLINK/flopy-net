"""
Industrial IoT Federated Learning Scenario

This module implements an industrial IoT federated learning scenario with
factory floor devices, diverse connectivity options, and challenging RF conditions.
"""
from typing import Dict, Any, List
from src.domain.interfaces.simulation_scenario import ISimulationScenario


class IndustrialIoTScenario(ISimulationScenario):
    """
    An industrial IoT federated learning scenario simulating a factory environment.
    
    This scenario simulates:
    - Factory floor IoT sensors and equipment
    - Challenging RF conditions (metal interference, machinery noise)
    - Time-sensitive applications
    - High-reliability requirements
    - Legacy and modern equipment coexistence
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the industrial IoT scenario.
        
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
        return "Industrial IoT Federated Learning Scenario"
    
    def get_description(self) -> str:
        """
        Get the scenario description.
        
        Returns:
            Scenario description
        """
        return (
            "An industrial IoT federated learning scenario simulating a factory environment "
            "with manufacturing equipment, sensors, RF interference, and high-reliability "
            "requirements for time-sensitive applications."
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
        Create the default configuration for the industrial IoT scenario.
        
        Returns:
            Configuration dictionary
        """
        # Network topology for factory floor
        topology = {
            "type": "custom",
            "nodes": [
                # Main control center server
                {"id": "control_center", "type": "server", "location": {"x": 0, "y": 0}},
                
                # Industrial switches/gateways
                {"id": "factory_gateway", "type": "switch", "location": {"x": 0, "y": 10}},
                {"id": "assembly_gateway", "type": "switch", "location": {"x": -20, "y": 0}},
                {"id": "warehouse_gateway", "type": "switch", "location": {"x": 20, "y": 0}},
                {"id": "maintenance_gateway", "type": "switch", "location": {"x": 0, "y": -20}},
                
                # Factory zones
                {"id": "zone_a_switch", "type": "switch", "location": {"x": -15, "y": 15}},
                {"id": "zone_b_switch", "type": "switch", "location": {"x": 15, "y": 15}},
                {"id": "zone_c_switch", "type": "switch", "location": {"x": -15, "y": -15}},
                {"id": "zone_d_switch", "type": "switch", "location": {"x": 15, "y": -15}},
                
                # Edge computing nodes
                {"id": "edge_node_1", "type": "switch", "location": {"x": -5, "y": 5}},
                {"id": "edge_node_2", "type": "switch", "location": {"x": 5, "y": 5}},
            ],
            "links": [
                # Core infrastructure (high reliability backbone)
                {"source": "control_center", "target": "factory_gateway", "bandwidth": 10000, "delay": "1ms", "loss": 0.0001},
                {"source": "control_center", "target": "assembly_gateway", "bandwidth": 10000, "delay": "1ms", "loss": 0.0001},
                {"source": "control_center", "target": "warehouse_gateway", "bandwidth": 10000, "delay": "1ms", "loss": 0.0001},
                {"source": "control_center", "target": "maintenance_gateway", "bandwidth": 10000, "delay": "1ms", "loss": 0.0001},
                
                # Zone connections
                {"source": "factory_gateway", "target": "zone_a_switch", "bandwidth": 1000, "delay": "2ms", "loss": 0.001},
                {"source": "factory_gateway", "target": "zone_b_switch", "bandwidth": 1000, "delay": "2ms", "loss": 0.001},
                {"source": "assembly_gateway", "target": "zone_c_switch", "bandwidth": 1000, "delay": "2ms", "loss": 0.001},
                {"source": "warehouse_gateway", "target": "zone_d_switch", "bandwidth": 1000, "delay": "2ms", "loss": 0.001},
                
                # Edge computing connections
                {"source": "control_center", "target": "edge_node_1", "bandwidth": 5000, "delay": "1ms", "loss": 0.0005},
                {"source": "control_center", "target": "edge_node_2", "bandwidth": 5000, "delay": "1ms", "loss": 0.0005},
                {"source": "edge_node_1", "target": "zone_a_switch", "bandwidth": 1000, "delay": "1ms", "loss": 0.0005},
                {"source": "edge_node_1", "target": "zone_c_switch", "bandwidth": 1000, "delay": "1ms", "loss": 0.0005},
                {"source": "edge_node_2", "target": "zone_b_switch", "bandwidth": 1000, "delay": "1ms", "loss": 0.0005},
                {"source": "edge_node_2", "target": "zone_d_switch", "bandwidth": 1000, "delay": "1ms", "loss": 0.0005},
            ]
        }
        
        # Server configuration
        server_config = {
            "host": "0.0.0.0",
            "port": 5000,
            "model_aggregation": "federated_averaging",
            "min_clients": 10,
            "max_clients": 50,
            "min_client_availability": 0.8,  # 80% client availability required for industrial reliability
            "rounds": 50,
            "epochs": 2,
            "batch_size": 16,
            "learning_rate": 0.005,
            "target_accuracy": 0.92  # Higher accuracy requirements for industrial applications
        }
        
        # Client configurations for industrial equipment
        clients = []
        
        # Smart manufacturing equipment (high performance)
        for i in range(1, 11):
            zone_id = ((i-1) % 4) + 1
            zone_letter = chr(ord('a') + ((i-1) % 4))
            zone_switch = f"zone_{zone_letter}_switch"
            
            clients.append({
                "id": f"machine_{i}",
                "type": "industrial_equipment",
                "performance": "high",
                "connection_type": "wired",
                "mobility": "stationary",
                "attachment_point": zone_switch,
                "training_speed": 120,  # samples/second
                "resources": {
                    "battery_level": 100,  # Always powered
                    "charging": True,
                    "memory_mb": 4000,
                    "cpu_cores": 4,
                    "network_bandwidth_mbps": 1000
                },
                "data": {
                    "data_samples": 10000 + (i * 500),
                    "data_distribution": "specialized",
                    "data_type": f"machine_telemetry_zone_{zone_id}"
                },
                "location": {
                    "zone": f"zone_{zone_letter}",
                    "position": f"machine_position_{i}",
                    "mobility_pattern": "stationary"
                }
            })
        
        # Industrial sensors (low performance but numerous)
        for i in range(1, 31):
            zone_id = ((i-1) % 4) + 1
            zone_letter = chr(ord('a') + ((i-1) % 4))
            zone_switch = f"zone_{zone_letter}_switch"
            
            # Every 5th sensor is wireless
            connectivity = "wireless" if i % 5 == 0 else "wired"
            bandwidth = 10 if connectivity == "wireless" else 100
            
            # Distribute sensors by type
            if i % 3 == 0:
                sensor_type = "temperature"
                data_size = 1000 + (i * 20)
            elif i % 3 == 1:
                sensor_type = "vibration"
                data_size = 2000 + (i * 30)
            else:
                sensor_type = "pressure"
                data_size = 1500 + (i * 25)
            
            clients.append({
                "id": f"sensor_{i}_{sensor_type}",
                "type": "industrial_sensor",
                "subtype": sensor_type,
                "performance": "low",
                "connection_type": connectivity,
                "mobility": "stationary",
                "attachment_point": zone_switch,
                "training_speed": 30,  # samples/second
                "resources": {
                    "battery_level": 100 if connectivity == "wired" else (70 + (i % 30)),
                    "charging": True if connectivity == "wired" else (i % 3 == 0),
                    "memory_mb": 128,
                    "cpu_cores": 1,
                    "network_bandwidth_mbps": bandwidth
                },
                "data": {
                    "data_samples": data_size,
                    "data_distribution": "specialized",
                    "data_type": f"{sensor_type}_data_zone_{zone_id}"
                },
                "location": {
                    "zone": f"zone_{zone_letter}",
                    "position": f"sensor_position_{i}",
                    "mobility_pattern": "stationary"
                }
            })
        
        # Maintenance tablets and handheld devices (mobile)
        for i in range(1, 6):
            clients.append({
                "id": f"maintenance_device_{i}",
                "type": "maintenance_tablet",
                "performance": "medium",
                "connection_type": "wireless",
                "mobility": "mobile",
                "attachment_point": "maintenance_gateway",
                "training_speed": 50,  # samples/second
                "resources": {
                    "battery_level": 75 + (i * 5),
                    "charging": False,
                    "memory_mb": 2000,
                    "cpu_cores": 2,
                    "network_bandwidth_mbps": 30
                },
                "data": {
                    "data_samples": 3000 + (i * 300),
                    "data_distribution": "heterogeneous",
                    "data_type": "maintenance_logs"
                },
                "location": {
                    "zone": "mobile",
                    "position": "variable",
                    "mobility_pattern": "maintenance_route"
                }
            })
        
        # Quality control stations
        for i in range(1, 5):
            zone_letter = chr(ord('a') + (i-1))
            zone_switch = f"zone_{zone_letter}_switch"
            
            clients.append({
                "id": f"quality_station_{i}",
                "type": "quality_control",
                "performance": "high",
                "connection_type": "wired",
                "mobility": "stationary",
                "attachment_point": zone_switch,
                "training_speed": 100,  # samples/second
                "resources": {
                    "battery_level": 100,
                    "charging": True,
                    "memory_mb": 8000,
                    "cpu_cores": 8,
                    "network_bandwidth_mbps": 1000
                },
                "data": {
                    "data_samples": 15000 + (i * 1000),
                    "data_distribution": "specialized",
                    "data_type": "quality_inspection_data"
                },
                "location": {
                    "zone": f"zone_{zone_letter}",
                    "position": f"quality_station_position_{i}",
                    "mobility_pattern": "stationary"
                }
            })
        
        # Industrial network conditions (interference, shift patterns)
        network_conditions = [
            # Metal interference in manufacturing zones causing packet loss
            {"source": "zone_a_switch", "target": "factory_gateway", "loss": 0.02,
             "time_periods": [{"start": "00:00", "end": "23:59"}],
             "reason": "Metal and machinery interference"},
            {"source": "zone_b_switch", "target": "factory_gateway", "loss": 0.025,
             "time_periods": [{"start": "00:00", "end": "23:59"}],
             "reason": "Metal and machinery interference"},
            
            # High traffic during shift changes
            {"source": "control_center", "target": "factory_gateway", "bandwidth": 5000, "delay": "5ms",
             "time_periods": [{"start": "05:45", "end": "06:15"}, {"start": "13:45", "end": "14:15"}, {"start": "21:45", "end": "22:15"}],
             "reason": "Shift change network traffic"},
            
            # Heavy machinery operation causing vibration and interference
            {"source": "zone_c_switch", "target": "assembly_gateway", "loss": 0.03, "delay": "10ms",
             "time_periods": [{"start": "08:00", "end": "16:00"}],
             "reason": "Heavy machinery operation"}
        ]
        
        # SDN policies for industrial networks
        sdn_policies = [
            {
                "name": "industrial_traffic_prioritization",
                "type": "qos",
                "config": {
                    "priority_classes": {
                        "safety_critical": {
                            "priority": 1,
                            "max_latency_ms": 10,
                            "min_bandwidth_mbps": 50
                        },
                        "production_critical": {
                            "priority": 2,
                            "max_latency_ms": 20,
                            "min_bandwidth_mbps": 20
                        },
                        "fl_training": {
                            "priority": 3,
                            "max_latency_ms": 100,
                            "min_bandwidth_mbps": 10
                        },
                        "best_effort": {
                            "priority": 4,
                            "max_latency_ms": 500,
                            "min_bandwidth_mbps": 1
                        }
                    },
                    "traffic_classification": {
                        "model_update": "fl_training",
                        "model_distribution": "fl_training",
                        "safety_alert": "safety_critical",
                        "process_control": "production_critical",
                        "maintenance_data": "best_effort"
                    }
                }
            },
            {
                "name": "industrial_reliability",
                "type": "reliability",
                "config": {
                    "path_redundancy": True,
                    "max_retry_attempts": 5,
                    "error_correction": "enabled",
                    "congestion_threshold": 0.7,
                    "path_diversity": True
                }
            }
        ]
        
        # Industrial simulation events
        simulation_events = [
            # Scheduled maintenance window
            {
                "type": "scheduled_maintenance",
                "trigger_time_seconds": 1200,  # 20 minutes in
                "duration_seconds": 900,  # 15 minutes
                "data": {
                    "affected_clients": ["machine_3", "machine_7"],
                    "reason": "Regular preventive maintenance"
                }
            },
            
            # Network interference from heavy machinery
            {
                "type": "network_interference",
                "trigger_time_seconds": 600,  # 10 minutes in
                "duration_seconds": 300,  # 5 minutes
                "data": {
                    "affected_links": [
                        {"source": "zone_b_switch", "target": "factory_gateway", "loss_increase": 0.05}
                    ],
                    "reason": "Heavy machinery startup causing RF interference"
                }
            },
            
            # Safety emergency causing network prioritization changes
            {
                "type": "safety_emergency",
                "trigger_time_seconds": 2700,  # 45 minutes in
                "duration_seconds": 180,  # 3 minutes
                "data": {
                    "affected_zones": ["zone_a", "zone_b"],
                    "priority_override": "safety_critical",
                    "reason": "Temperature alert in manufacturing area"
                }
            },
            
            # Production line speed increase (affects data generation)
            {
                "type": "production_speed_change",
                "trigger_time_seconds": 1800,  # 30 minutes in
                "data": {
                    "affected_clients": ["machine_1", "machine_2", "machine_5", "machine_6"],
                    "speed_factor": 1.5,
                    "data_rate_increase": 1.5,
                    "reason": "Production quota acceleration"
                }
            },
            
            # Power fluctuation affecting non-UPS equipment
            {
                "type": "power_fluctuation",
                "trigger_time_seconds": 3600,  # 60 minutes in
                "duration_seconds": 120,  # 2 minutes
                "data": {
                    "affected_clients": [f"sensor_{i}_temperature" for i in range(1, 31, 3)],
                    "reason": "Grid instability"
                }
            }
        ]
        
        # Expected metrics for validation
        expected_metrics = {
            "fl_performance": {
                "accuracy": {
                    "min": 0.88,
                    "target": 0.92,
                    "max": 0.97
                },
                "loss": {
                    "min": 0.03,
                    "target": 0.06,
                    "max": 0.12
                },
                "convergence_round": {
                    "min": 20,
                    "target": 30,
                    "max": 45
                }
            },
            "network_performance": {
                "average_round_time": {
                    "min": 20,  # seconds
                    "target": 40,
                    "max": 90
                },
                "client_dropout_rate": {
                    "min": 0.02,
                    "target": 0.05,
                    "max": 0.1
                },
                "packet_loss_rate": {
                    "min": 0.001,
                    "target": 0.01,
                    "max": 0.03
                },
                "communication_overhead": {
                    "min": 10,  # MB per round
                    "target": 20,
                    "max": 50
                }
            },
            "industrial_metrics": {
                "model_inference_latency": {
                    "min": 5,  # ms
                    "target": 15,
                    "max": 50
                },
                "anomaly_detection_accuracy": {
                    "min": 0.9,
                    "target": 0.95,
                    "max": 0.99
                },
                "prediction_horizon": {
                    "min": 60,  # seconds
                    "target": 300,
                    "max": 3600
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