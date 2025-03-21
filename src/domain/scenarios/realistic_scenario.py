"""
Realistic Federated Learning Scenario

This module implements a realistic federated learning scenario with heterogeneous clients,
varying network conditions, and real-world challenges.
"""
from typing import Dict, Any, List
from src.domain.interfaces.simulation_scenario import ISimulationScenario


class RealisticScenario(ISimulationScenario):
    """
    A realistic federated learning scenario with heterogeneous clients and network conditions.
    
    This scenario simulates:
    - Heterogeneous clients with varying compute capabilities
    - Realistic network conditions (bandwidth, latency, packet loss)
    - Client dropouts and mobility
    - Network congestion events
    """
    
    def __init__(self):
        """Initialize the realistic scenario."""
        self.config = self._create_config()
    
    def get_name(self) -> str:
        """
        Get the scenario name.
        
        Returns:
            Scenario name
        """
        return "Realistic Federated Learning Scenario"
    
    def get_description(self) -> str:
        """
        Get the scenario description.
        
        Returns:
            Scenario description
        """
        return (
            "A realistic federated learning scenario with heterogeneous clients, "
            "varying network conditions, and common real-world challenges like "
            "client dropouts, varying data distribution, and network congestion."
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
    
    def _create_config(self) -> Dict[str, Any]:
        """
        Create the scenario configuration.
        
        Returns:
            Configuration dictionary
        """
        # Create a tree topology with three switches
        topology = {
            "type": "tree",
            "depth": 2,
            "fanout": 3,
            "switches": [
                {"id": 1, "type": "core"},
                {"id": 2, "type": "edge"},
                {"id": 3, "type": "edge"},
                {"id": 4, "type": "edge"}
            ],
            "hosts": [
                # High-performance clients (e.g., data centers)
                {"id": 1, "connected_to": "s2", "ip": "10.0.0.1", "compute_capability": "high"},
                {"id": 2, "connected_to": "s2", "ip": "10.0.0.2", "compute_capability": "high"},
                
                # Medium-performance clients (e.g., desktops, servers)
                {"id": 3, "connected_to": "s3", "ip": "10.0.0.3", "compute_capability": "medium"},
                {"id": 4, "connected_to": "s3", "ip": "10.0.0.4", "compute_capability": "medium"},
                {"id": 5, "connected_to": "s3", "ip": "10.0.0.5", "compute_capability": "medium"},
                {"id": 6, "connected_to": "s3", "ip": "10.0.0.6", "compute_capability": "medium"},
                
                # Low-performance clients (e.g., mobile devices, IoT)
                {"id": 7, "connected_to": "s4", "ip": "10.0.0.7", "compute_capability": "low"},
                {"id": 8, "connected_to": "s4", "ip": "10.0.0.8", "compute_capability": "low"},
                {"id": 9, "connected_to": "s4", "ip": "10.0.0.9", "compute_capability": "low"},
                {"id": 10, "connected_to": "s4", "ip": "10.0.0.10", "compute_capability": "low"},
                {"id": 11, "connected_to": "s4", "ip": "10.0.0.11", "compute_capability": "low"},
                {"id": 12, "connected_to": "s4", "ip": "10.0.0.12", "compute_capability": "low"}
            ],
            "links": [
                # Core to edge links (high capacity)
                {"source": "s1", "target": "s2", "bandwidth": 1000, "delay": "5ms", "loss": 0.01},
                {"source": "s1", "target": "s3", "bandwidth": 1000, "delay": "5ms", "loss": 0.01},
                {"source": "s1", "target": "s4", "bandwidth": 1000, "delay": "5ms", "loss": 0.01},
                
                # Edge to host links (varying capacity)
                # High-performance clients
                {"source": "s2", "target": "h1", "bandwidth": 1000, "delay": "1ms", "loss": 0.01},
                {"source": "s2", "target": "h2", "bandwidth": 1000, "delay": "1ms", "loss": 0.01},
                
                # Medium-performance clients
                {"source": "s3", "target": "h3", "bandwidth": 100, "delay": "5ms", "loss": 0.05},
                {"source": "s3", "target": "h4", "bandwidth": 100, "delay": "5ms", "loss": 0.05},
                {"source": "s3", "target": "h5", "bandwidth": 100, "delay": "10ms", "loss": 0.05},
                {"source": "s3", "target": "h6", "bandwidth": 100, "delay": "10ms", "loss": 0.05},
                
                # Low-performance clients (e.g., mobile devices)
                {"source": "s4", "target": "h7", "bandwidth": 50, "delay": "15ms", "loss": 0.1},
                {"source": "s4", "target": "h8", "bandwidth": 50, "delay": "15ms", "loss": 0.1},
                {"source": "s4", "target": "h9", "bandwidth": 20, "delay": "25ms", "loss": 0.2},
                {"source": "s4", "target": "h10", "bandwidth": 20, "delay": "25ms", "loss": 0.2},
                {"source": "s4", "target": "h11", "bandwidth": 10, "delay": "50ms", "loss": 0.5},
                {"source": "s4", "target": "h12", "bandwidth": 10, "delay": "50ms", "loss": 0.5}
            ]
        }
        
        # Server configuration
        server_config = {
            "host": "0.0.0.0",
            "port": 5000,
            "max_rounds": 20,
            "min_clients": 5,
            "min_available_clients": 7,
            "client_fraction": 0.7,  # Select 70% of available clients each round
            "aggregation_strategy": "fedavg",
            "model_config": {
                "model_type": "cnn",
                "dataset": "mnist",
                "batch_size": 32,
                "learning_rate": 0.01,
                "momentum": 0.9,
                "local_epochs": 3,
                "optimizer": "sgd"
            }
        }
        
        # Client configurations
        client_configs = [
            # Client 1: High-performance data center node
            {
                "id": "client_1",
                "host": "h1",
                "ip": "10.0.0.1",
                "type": "high_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "iid",  # Independent and Identically Distributed
                    "samples": 10000  # Large dataset
                },
                "training_config": {
                    "batch_size": 64,
                    "local_epochs": 5,
                    "learning_rate": 0.01,
                    "optimizer": "adam"
                },
                "compute_capability": {
                    "cpu_cores": 16,
                    "memory_gb": 64,
                    "gpu": True,
                    "training_time_per_epoch_seconds": 1.2
                },
                "reliability": 0.99,  # 99% uptime
                "bandwidth_mbps": 1000
            },
            
            # Client 2: High-performance data center node
            {
                "id": "client_2",
                "host": "h2",
                "ip": "10.0.0.2",
                "type": "high_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "iid",
                    "samples": 10000
                },
                "training_config": {
                    "batch_size": 64,
                    "local_epochs": 5,
                    "learning_rate": 0.01,
                    "optimizer": "adam"
                },
                "compute_capability": {
                    "cpu_cores": 16,
                    "memory_gb": 64,
                    "gpu": True,
                    "training_time_per_epoch_seconds": 1.2
                },
                "reliability": 0.99,
                "bandwidth_mbps": 1000
            },
            
            # Client 3: Medium-performance enterprise server
            {
                "id": "client_3",
                "host": "h3",
                "ip": "10.0.0.3",
                "type": "medium_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_label_skew",  # Non-IID with label skew
                    "samples": 5000
                },
                "training_config": {
                    "batch_size": 32,
                    "local_epochs": 4,
                    "learning_rate": 0.01,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 8,
                    "memory_gb": 32,
                    "gpu": True,
                    "training_time_per_epoch_seconds": 2.5
                },
                "reliability": 0.97,  # 97% uptime
                "bandwidth_mbps": 100
            },
            
            # Client 4: Medium-performance enterprise server
            {
                "id": "client_4",
                "host": "h4",
                "ip": "10.0.0.4",
                "type": "medium_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_label_skew",
                    "samples": 5000
                },
                "training_config": {
                    "batch_size": 32,
                    "local_epochs": 4,
                    "learning_rate": 0.01,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 8,
                    "memory_gb": 32,
                    "gpu": True,
                    "training_time_per_epoch_seconds": 2.5
                },
                "reliability": 0.97,
                "bandwidth_mbps": 100
            },
            
            # Clients 5-6: Medium-performance devices
            {
                "id": "client_5",
                "host": "h5",
                "ip": "10.0.0.5",
                "type": "medium_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_quantity_skew",  # Non-IID with quantity skew
                    "samples": 3000
                },
                "training_config": {
                    "batch_size": 32,
                    "local_epochs": 3,
                    "learning_rate": 0.01,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 4,
                    "memory_gb": 16,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 5.0
                },
                "reliability": 0.95,
                "bandwidth_mbps": 100
            },
            {
                "id": "client_6",
                "host": "h6",
                "ip": "10.0.0.6",
                "type": "medium_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_quantity_skew",
                    "samples": 3000
                },
                "training_config": {
                    "batch_size": 32,
                    "local_epochs": 3,
                    "learning_rate": 0.01,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 4,
                    "memory_gb": 16,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 5.0
                },
                "reliability": 0.95,
                "bandwidth_mbps": 100
            },
            
            # Clients 7-8: Desktop computers
            {
                "id": "client_7",
                "host": "h7",
                "ip": "10.0.0.7",
                "type": "low_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_label_quantity_skew",  # Non-IID with both label and quantity skew
                    "samples": 2000
                },
                "training_config": {
                    "batch_size": 16,
                    "local_epochs": 2,
                    "learning_rate": 0.01,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 4,
                    "memory_gb": 8,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 8.0
                },
                "reliability": 0.90,
                "bandwidth_mbps": 50
            },
            {
                "id": "client_8",
                "host": "h8",
                "ip": "10.0.0.8",
                "type": "low_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_label_quantity_skew",
                    "samples": 2000
                },
                "training_config": {
                    "batch_size": 16,
                    "local_epochs": 2,
                    "learning_rate": 0.01,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 4,
                    "memory_gb": 8,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 8.0
                },
                "reliability": 0.90,
                "bandwidth_mbps": 50
            },
            
            # Clients 9-10: Mobile devices
            {
                "id": "client_9",
                "host": "h9",
                "ip": "10.0.0.9",
                "type": "low_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_extreme",  # Extreme non-IID (few classes per client)
                    "samples": 1000
                },
                "training_config": {
                    "batch_size": 8,
                    "local_epochs": 1,
                    "learning_rate": 0.005,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 2,
                    "memory_gb": 4,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 12.0
                },
                "reliability": 0.80,
                "bandwidth_mbps": 20
            },
            {
                "id": "client_10",
                "host": "h10",
                "ip": "10.0.0.10",
                "type": "low_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_extreme",
                    "samples": 1000
                },
                "training_config": {
                    "batch_size": 8,
                    "local_epochs": 1,
                    "learning_rate": 0.005,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 2,
                    "memory_gb": 4,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 12.0
                },
                "reliability": 0.80,
                "bandwidth_mbps": 20
            },
            
            # Clients 11-12: IoT/Edge devices
            {
                "id": "client_11",
                "host": "h11",
                "ip": "10.0.0.11",
                "type": "very_low_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_extreme",
                    "samples": 500
                },
                "training_config": {
                    "batch_size": 4,
                    "local_epochs": 1,
                    "learning_rate": 0.001,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 1,
                    "memory_gb": 2,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 20.0
                },
                "reliability": 0.70,  # Unreliable devices
                "bandwidth_mbps": 10
            },
            {
                "id": "client_12",
                "host": "h12",
                "ip": "10.0.0.12",
                "type": "very_low_performance",
                "dataset_distribution": {
                    "dataset": "mnist",
                    "data_partition": "non_iid_extreme",
                    "samples": 500
                },
                "training_config": {
                    "batch_size": 4,
                    "local_epochs": 1,
                    "learning_rate": 0.001,
                    "optimizer": "sgd"
                },
                "compute_capability": {
                    "cpu_cores": 1,
                    "memory_gb": 2,
                    "gpu": False,
                    "training_time_per_epoch_seconds": 20.0
                },
                "reliability": 0.70,
                "bandwidth_mbps": 10
            }
        ]
        
        # SDN policies
        sdn_policies = [
            {
                "name": "network_optimization",
                "type": "sdn",
                "rules": {
                    "client_path_optimization": True,
                    "model_transfer_priority": "high",
                    "congestion_avoidance": True,
                    "bandwidth_allocation": {
                        "model_transfer": 70,
                        "control_traffic": 20,
                        "other_traffic": 10
                    },
                    "traffic_priority": {
                        "server_to_client": 1,
                        "client_to_server": 2,
                        "control_messages": 3,
                        "other_traffic": 4
                    }
                }
            }
        ]
        
        # Network conditions (additional to what's in the topology)
        network_conditions = [
            # No additional conditions, using the ones defined in topology
        ]
        
        # Simulation events (to introduce dynamic behaviors)
        simulation_events = [
            # Client dropout event (simulating a device going offline)
            {
                "type": "client_leave",
                "trigger_time_seconds": 300,
                "data": {
                    "client_id": "client_12"
                }
            },
            
            # New client joining (simulating a new device coming online)
            {
                "type": "client_join",
                "trigger_time_seconds": 500,
                "data": {
                    "client_id": "client_13",
                    "config": {
                        "host": "h4",
                        "ip": "10.0.0.13",
                        "type": "medium_performance",
                        "compute_capability": "medium"
                    }
                }
            },
            
            # Link congestion event (simulating network traffic increase)
            {
                "type": "link_congestion",
                "trigger_time_seconds": 200,
                "data": {
                    "source": "s1",
                    "target": "s4",
                    "bandwidth": 300  # Reduce bandwidth to 300 Mbps (from 1000)
                }
            },
            
            # Link failure event (simulating network problem)
            {
                "type": "link_failure",
                "trigger_time_seconds": 400,
                "data": {
                    "source": "s4",
                    "target": "h11"
                }
            },
            
            # Link recovery (restoring previous link failure)
            {
                "type": "link_recovery",
                "trigger_time_seconds": 450,
                "data": {
                    "source": "s4",
                    "target": "h11"
                }
            },
            
            # Congestion recovery (restoring previous congestion)
            {
                "type": "link_congestion",
                "trigger_time_seconds": 600,
                "data": {
                    "source": "s1",
                    "target": "s4",
                    "bandwidth": 1000  # Restore bandwidth to 1000 Mbps
                }
            }
        ]
        
        # Full configuration
        return {
            "topology": topology,
            "server": server_config,
            "clients": client_configs,
            "sdn_policies": sdn_policies,
            "network_conditions": network_conditions,
            "simulation_events": simulation_events
        } 