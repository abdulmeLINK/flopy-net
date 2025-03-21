"""
Healthcare Simulation Scenario

This module provides a healthcare simulation scenario for federated learning,
including hospital and clinic environments with various medical devices and
privacy requirements.
"""
from typing import Dict, List, Any, Optional

from src.domain.scenarios.scenario_registry import ISimulationScenario


class HealthcareScenario(ISimulationScenario):
    """
    Healthcare simulation scenario for federated learning.
    
    This scenario simulates a healthcare environment with hospitals, clinics,
    and medical devices, with high privacy and reliability requirements.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the healthcare scenario.
        
        Args:
            config: Optional configuration overrides
        """
        self._config = self._create_config()
        
        # Apply configuration overrides if provided
        if config:
            for key, value in config.items():
                if key in self._config:
                    self._config[key] = value
    
    def get_name(self) -> str:
        """
        Get the name of the scenario.
        
        Returns:
            The scenario name
        """
        return "Healthcare"
    
    def get_description(self) -> str:
        """
        Get the description of the scenario.
        
        Returns:
            The scenario description
        """
        return (
            "Healthcare environment with hospitals, clinics, and medical devices. "
            "Features high privacy requirements (HIPAA compliance), "
            "reliable connectivity, and varying patient data sources."
        )
    
    def get_topology_config(self) -> Dict:
        """
        Get the network topology configuration.
        
        Returns:
            The network topology configuration
        """
        return self._config["topology"]
    
    def get_server_config(self) -> Dict:
        """
        Get the server configuration.
        
        Returns:
            The server configuration
        """
        return self._config["server"]
    
    def get_client_configs(self) -> List[Dict]:
        """
        Get the client configurations.
        
        Returns:
            The client configurations
        """
        return self._config["clients"]
    
    def get_sdn_policies(self) -> Dict:
        """
        Get the SDN policies configuration.
        
        Returns:
            The SDN policies
        """
        return self._config["sdn_policies"]
    
    def get_network_conditions(self) -> Dict:
        """
        Get the network conditions.
        
        Returns:
            The network conditions
        """
        return self._config["network_conditions"]
    
    def get_simulation_events(self) -> List[Dict]:
        """
        Get the simulation events.
        
        Returns:
            The simulation events
        """
        return self._config["simulation_events"]
    
    def get_expected_metrics(self) -> Dict:
        """
        Get the expected metrics for the scenario.
        
        Returns:
            The expected metrics
        """
        return self._config["expected_metrics"]
    
    def _create_config(self) -> Dict[str, Any]:
        """
        Create the default configuration for the healthcare scenario.
        
        Returns:
            The default configuration
        """
        return {
            "topology": {
                "name": "healthcare_network",
                "nodes": [
                    {
                        "id": "central_server",
                        "type": "server",
                        "location": "data_center",
                        "coordinates": [0, 0],
                        "bandwidth": 10000  # 10 Gbps
                    },
                    {
                        "id": "hospital_gateway_1",
                        "type": "gateway",
                        "location": "hospital_a",
                        "coordinates": [1, 5],
                        "bandwidth": 1000  # 1 Gbps
                    },
                    {
                        "id": "hospital_gateway_2",
                        "type": "gateway",
                        "location": "hospital_b",
                        "coordinates": [-2, 3],
                        "bandwidth": 1000  # 1 Gbps
                    },
                    {
                        "id": "clinic_gateway_1",
                        "type": "gateway",
                        "location": "clinic_a",
                        "coordinates": [4, -2],
                        "bandwidth": 500  # 500 Mbps
                    },
                    {
                        "id": "clinic_gateway_2",
                        "type": "gateway",
                        "location": "clinic_b",
                        "coordinates": [-4, -4],
                        "bandwidth": 500  # 500 Mbps
                    },
                    {
                        "id": "remote_site_gateway",
                        "type": "gateway",
                        "location": "remote_site",
                        "coordinates": [6, 6],
                        "bandwidth": 100  # 100 Mbps
                    }
                ],
                "links": [
                    {
                        "source": "central_server",
                        "target": "hospital_gateway_1",
                        "bandwidth": 1000,
                        "latency": 5,  # 5 ms
                        "reliability": 0.999
                    },
                    {
                        "source": "central_server",
                        "target": "hospital_gateway_2",
                        "bandwidth": 1000,
                        "latency": 7,
                        "reliability": 0.999
                    },
                    {
                        "source": "central_server",
                        "target": "clinic_gateway_1",
                        "bandwidth": 500,
                        "latency": 10,
                        "reliability": 0.998
                    },
                    {
                        "source": "central_server",
                        "target": "clinic_gateway_2",
                        "bandwidth": 500,
                        "latency": 12,
                        "reliability": 0.998
                    },
                    {
                        "source": "central_server",
                        "target": "remote_site_gateway",
                        "bandwidth": 100,
                        "latency": 25,
                        "reliability": 0.995
                    }
                ]
            },
            "server": {
                "id": "healthcare_fl_server",
                "location": "central_server",
                "model_type": "medical_diagnostics",
                "aggregation_method": "federated_averaging",
                "rounds": 100,
                "min_clients": 5,
                "min_available_clients": 10,
                "min_sample_size": 100,
                "privacy_mechanism": "differential_privacy",
                "dp_epsilon": 2.0,
                "dp_delta": 1e-5,
                "encryption": "enabled",
                "compliance": {
                    "hipaa": True,
                    "gdpr": True
                }
            },
            "clients": [
                # Hospital A - MRI Machines
                {
                    "id": "hospital_a_mri_1",
                    "type": "mri_scanner",
                    "location": "hospital_gateway_1",
                    "performance": "high",
                    "memory": 16,  # GB
                    "storage": 1000,  # GB
                    "data_quality": "high",
                    "data_volume": "high",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 9.0
                    },
                    "privacy_level": "highest",
                    "department": "radiology"
                },
                {
                    "id": "hospital_a_mri_2",
                    "type": "mri_scanner",
                    "location": "hospital_gateway_1",
                    "performance": "high",
                    "memory": 16,
                    "storage": 1000,
                    "data_quality": "high",
                    "data_volume": "high",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 9.0
                    },
                    "privacy_level": "highest",
                    "department": "radiology"
                },
                
                # Hospital A - CT Scans
                {
                    "id": "hospital_a_ct_1",
                    "type": "ct_scanner",
                    "location": "hospital_gateway_1",
                    "performance": "high",
                    "memory": 12,
                    "storage": 800,
                    "data_quality": "high",
                    "data_volume": "high",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 8.5
                    },
                    "privacy_level": "highest",
                    "department": "radiology"
                },
                
                # Hospital A - Workstations
                {
                    "id": "hospital_a_workstation_1",
                    "type": "medical_workstation",
                    "location": "hospital_gateway_1",
                    "performance": "medium",
                    "memory": 8,
                    "storage": 500,
                    "data_quality": "high",
                    "data_volume": "medium",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 6.0
                    },
                    "privacy_level": "high",
                    "department": "cardiology"
                },
                {
                    "id": "hospital_a_workstation_2",
                    "type": "medical_workstation",
                    "location": "hospital_gateway_1",
                    "performance": "medium",
                    "memory": 8,
                    "storage": 500,
                    "data_quality": "high",
                    "data_volume": "medium",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 6.0
                    },
                    "privacy_level": "high",
                    "department": "neurology"
                },
                
                # Hospital B - MRI Machines
                {
                    "id": "hospital_b_mri_1",
                    "type": "mri_scanner",
                    "location": "hospital_gateway_2",
                    "performance": "high",
                    "memory": 16,
                    "storage": 1000,
                    "data_quality": "high",
                    "data_volume": "high",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 9.0
                    },
                    "privacy_level": "highest",
                    "department": "radiology"
                },
                
                # Hospital B - X-ray machines
                {
                    "id": "hospital_b_xray_1",
                    "type": "xray_machine",
                    "location": "hospital_gateway_2",
                    "performance": "medium",
                    "memory": 8,
                    "storage": 400,
                    "data_quality": "high",
                    "data_volume": "medium",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.998
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 7.0
                    },
                    "privacy_level": "highest",
                    "department": "radiology"
                },
                
                # Hospital B - Workstations
                {
                    "id": "hospital_b_workstation_1",
                    "type": "medical_workstation",
                    "location": "hospital_gateway_2",
                    "performance": "medium",
                    "memory": 8,
                    "storage": 500,
                    "data_quality": "high",
                    "data_volume": "medium",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.999
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 6.0
                    },
                    "privacy_level": "high",
                    "department": "emergency"
                },
                
                # Clinic A - Ultrasound
                {
                    "id": "clinic_a_ultrasound_1",
                    "type": "ultrasound",
                    "location": "clinic_gateway_1",
                    "performance": "medium",
                    "memory": 6,
                    "storage": 300,
                    "data_quality": "medium",
                    "data_volume": "medium",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.997
                    },
                    "mobility": "movable",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 5.0
                    },
                    "privacy_level": "high",
                    "department": "obstetrics"
                },
                
                # Clinic A - Tablets
                {
                    "id": "clinic_a_tablet_1",
                    "type": "medical_tablet",
                    "location": "clinic_gateway_1",
                    "performance": "low",
                    "memory": 4,
                    "storage": 128,
                    "data_quality": "medium",
                    "data_volume": "low",
                    "connectivity": {
                        "type": "wifi",
                        "reliability": 0.99
                    },
                    "mobility": "mobile",
                    "resources": {
                        "power": "battery",
                        "battery_level": 85,
                        "charging": False,
                        "compute_capability": 3.0
                    },
                    "privacy_level": "high",
                    "department": "general_practice"
                },
                {
                    "id": "clinic_a_tablet_2",
                    "type": "medical_tablet",
                    "location": "clinic_gateway_1",
                    "performance": "low",
                    "memory": 4,
                    "storage": 128,
                    "data_quality": "medium",
                    "data_volume": "low",
                    "connectivity": {
                        "type": "wifi",
                        "reliability": 0.99
                    },
                    "mobility": "mobile",
                    "resources": {
                        "power": "battery",
                        "battery_level": 70,
                        "charging": False,
                        "compute_capability": 3.0
                    },
                    "privacy_level": "high",
                    "department": "nursing"
                },
                
                # Clinic B - X-ray
                {
                    "id": "clinic_b_xray_1",
                    "type": "xray_machine",
                    "location": "clinic_gateway_2",
                    "performance": "medium",
                    "memory": 6,
                    "storage": 300,
                    "data_quality": "medium",
                    "data_volume": "medium",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.995
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 5.5
                    },
                    "privacy_level": "high",
                    "department": "radiology"
                },
                
                # Clinic B - Workstations
                {
                    "id": "clinic_b_workstation_1",
                    "type": "medical_workstation",
                    "location": "clinic_gateway_2",
                    "performance": "low",
                    "memory": 6,
                    "storage": 250,
                    "data_quality": "medium",
                    "data_volume": "low",
                    "connectivity": {
                        "type": "wired",
                        "reliability": 0.997
                    },
                    "mobility": "stationary",
                    "resources": {
                        "power": "continuous",
                        "compute_capability": 4.5
                    },
                    "privacy_level": "high",
                    "department": "general_practice"
                },
                
                # Remote Site - Mobile Ultrasound
                {
                    "id": "remote_ultrasound_1",
                    "type": "portable_ultrasound",
                    "location": "remote_site_gateway",
                    "performance": "low",
                    "memory": 4,
                    "storage": 120,
                    "data_quality": "medium",
                    "data_volume": "low",
                    "connectivity": {
                        "type": "wifi",
                        "reliability": 0.98
                    },
                    "mobility": "mobile",
                    "resources": {
                        "power": "battery",
                        "battery_level": 90,
                        "charging": False,
                        "compute_capability": 3.5
                    },
                    "privacy_level": "high",
                    "department": "field_service"
                },
                
                # Remote Site - Tablets
                {
                    "id": "remote_tablet_1",
                    "type": "medical_tablet",
                    "location": "remote_site_gateway",
                    "performance": "low",
                    "memory": 3,
                    "storage": 64,
                    "data_quality": "low",
                    "data_volume": "low",
                    "connectivity": {
                        "type": "cellular",
                        "reliability": 0.95
                    },
                    "mobility": "mobile",
                    "resources": {
                        "power": "battery",
                        "battery_level": 60,
                        "charging": False,
                        "compute_capability": 2.5
                    },
                    "privacy_level": "high",
                    "department": "field_service"
                },
                {
                    "id": "remote_tablet_2",
                    "type": "medical_tablet",
                    "location": "remote_site_gateway",
                    "performance": "low",
                    "memory": 3,
                    "storage": 64,
                    "data_quality": "low",
                    "data_volume": "low",
                    "connectivity": {
                        "type": "cellular",
                        "reliability": 0.95
                    },
                    "mobility": "mobile",
                    "resources": {
                        "power": "battery",
                        "battery_level": 45,
                        "charging": True,
                        "compute_capability": 2.5
                    },
                    "privacy_level": "high",
                    "department": "field_service"
                }
            ],
            "sdn_policies": {
                "traffic_priority": {
                    "fl_training": 3,
                    "model_distribution": 2,
                    "emergency": 1,
                    "patient_critical": 1
                },
                "encryption": "required",
                "encryption_level": "AES-256",
                "client_selection": {
                    "strategy": "data_quality_priority",
                    "balancing": "department_balanced"
                },
                "qos": {
                    "latency_requirements": {
                        "emergency": 50,  # ms
                        "regular": 200    # ms
                    }
                },
                "availability": {
                    "min_battery_level": 30,
                    "min_reliability": 0.95
                }
            },
            "network_conditions": {
                "normal": {
                    "time_periods": [
                        {"start": "00:00", "end": "07:59"},
                        {"start": "19:00", "end": "23:59"}
                    ],
                    "conditions": {
                        "latency_factor": 1.0,
                        "packet_loss": 0.001,
                        "jitter": 1.0  # ms
                    }
                },
                "busy_hours": {
                    "time_periods": [
                        {"start": "08:00", "end": "18:59"}
                    ],
                    "conditions": {
                        "latency_factor": 1.3,
                        "packet_loss": 0.005,
                        "jitter": 3.0  # ms
                    },
                    "reason": "Hospital working hours with increased network traffic"
                },
                "maintenance_window": {
                    "time_periods": [
                        {"start": "02:00", "end": "04:00"}
                    ],
                    "days": ["Saturday"],
                    "conditions": {
                        "latency_factor": 1.5,
                        "packet_loss": 0.01,
                        "jitter": 5.0  # ms
                    },
                    "reason": "Hospital IT infrastructure maintenance window"
                }
            },
            "simulation_events": [
                {
                    "type": "emergency_situation",
                    "trigger_time_seconds": 3600,  # 1 hour into simulation
                    "duration_seconds": 1800,  # 30 minutes
                    "location": "hospital_b",
                    "data": {
                        "traffic_increase": 2.5,
                        "priority_override": True,
                        "affected_departments": ["emergency", "radiology"]
                    },
                    "description": "Mass casualty incident requiring emergency medical response"
                },
                {
                    "type": "network_outage",
                    "trigger_time_seconds": 7200,  # 2 hours into simulation
                    "duration_seconds": 900,  # 15 minutes
                    "location": "clinic_gateway_1",
                    "data": {
                        "complete_outage": True,
                        "failover_active": True
                    },
                    "description": "Network outage at Clinic A affecting all connected devices"
                },
                {
                    "type": "battery_critical",
                    "trigger_time_seconds": 10800,  # 3 hours into simulation
                    "duration_seconds": 600,  # 10 minutes
                    "device_ids": ["clinic_a_tablet_1", "remote_tablet_1"],
                    "data": {
                        "battery_level": 10,
                        "warning_threshold": 15
                    },
                    "description": "Low battery warning on mobile devices"
                },
                {
                    "type": "data_surge",
                    "trigger_time_seconds": 14400,  # 4 hours into simulation
                    "duration_seconds": 3600,  # 1 hour
                    "location": "hospital_gateway_1",
                    "data": {
                        "data_volume_increase": 3.0,
                        "affected_devices": ["hospital_a_mri_1", "hospital_a_mri_2", "hospital_a_ct_1"]
                    },
                    "description": "Surge in imaging studies due to scheduled patient screenings"
                },
                {
                    "type": "security_scan",
                    "trigger_time_seconds": 21600,  # 6 hours into simulation
                    "duration_seconds": 1800,  # 30 minutes
                    "location": "central_server",
                    "data": {
                        "scan_type": "vulnerability",
                        "impact_level": "moderate",
                        "bandwidth_reduction": 0.3
                    },
                    "description": "Scheduled security vulnerability scan on central infrastructure"
                }
            ],
            "expected_metrics": {
                "fl_performance": {
                    "target_accuracy": 0.92,
                    "max_rounds": 100,
                    "convergence_threshold": 0.005,
                    "min_client_participation": 0.7
                },
                "network_performance": {
                    "max_acceptable_latency": 200,  # ms
                    "min_throughput": 10,  # Mbps
                    "max_packet_loss": 0.01
                },
                "healthcare_metrics": {
                    "diagnostic_accuracy": 0.95,
                    "false_positive_rate": 0.03,
                    "model_fairness": 0.9,
                    "patient_data_privacy": "strict"
                }
            }
        } 