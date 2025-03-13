"""
Federated Learning Scenarios

This module provides simulation scenarios for the FL-SDN dashboard
to demonstrate different use cases, network conditions, and policy applications.
"""

import random
import json
import time
import math
import numpy as np
import pandas as pd
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional

class ScenarioManager:
    """
    Manages and simulates different FL-SDN scenarios.
    Provides data for visualization and demonstration.
    """
    
    def __init__(self):
        """Initialize the scenario manager."""
        self.current_scenario = "normal"
        self.scenarios = {
            "normal": self._smart_city_traffic_scenario,
            "congestion": self._healthcare_monitoring_scenario,
            "security": self._financial_fraud_scenario,
            "resource": self._mobile_keyboard_scenario
        }
        self.scenario_names = {
            "normal": "Smart City Traffic Management",
            "congestion": "Healthcare IoT Monitoring",
            "security": "Financial Fraud Detection", 
            "resource": "Mobile Keyboard Prediction"
        }
        self.scenario_descriptions = {
            "normal": "Optimizing traffic signals using FL from distributed traffic cameras and sensors. Normal network conditions.",
            "congestion": "Medical device data aggregation for patient monitoring. Network experiencing congestion due to high data volume.",
            "security": "Cross-institutional fraud detection with potential malicious nodes attempting to compromise the model.",
            "resource": "Next word prediction on resource-constrained mobile devices requiring optimization."
        }
        
        # Initialize time-dependent variables
        self.start_time = datetime.now()
        self.current_round = 0
        self.max_rounds = 20
        self.time_scale = 1.0  # Time acceleration factor
        
        # Topology information
        self.nodes = {}
        self.links = {}
        self.topology = None
        self._initialize_network_topology()
        
        # FL metrics
        self.fl_metrics = {
            "accuracy": [],
            "loss": [],
            "rounds": [],
            "participation_rate": [],
            "training_time": []
        }
        
        # Application-specific metrics
        self.app_metrics = {
            "normal": {
                "traffic_flow_improvement": [],
                "prediction_accuracy": [],
                "signal_timing_efficiency": []
            },
            "congestion": {
                "alert_latency": [],
                "anomaly_detection_rate": [],
                "false_alarm_rate": []
            },
            "security": {
                "fraud_detection_rate": [],
                "false_positive_rate": [],
                "model_robustness": []
            },
            "resource": {
                "word_prediction_accuracy": [],
                "battery_consumption": [],
                "model_size": []
            }
        }
        
        # Policies
        self.active_policies = []
        self.policy_history = []
        self._initialize_policies()
        
        # Initialize data for current scenario
        self.refresh_data()
    
    def _initialize_network_topology(self):
        """Create network topology for visualization."""
        # Create graph
        G = nx.random_geometric_graph(25, 0.2)
        
        # Node categorization based on node ID
        node_types = {}
        for i in range(25):
            if i == 0:
                node_types[i] = "server"  # FL server
            elif i in [1, 2, 3]:
                node_types[i] = "gateway"  # Network gateways
            else:
                node_types[i] = "client"  # FL clients
        
        # Assign node attributes
        for i in range(25):
            # Base attributes
            node = {
                "id": f"node_{i}",
                "type": node_types[i],
                "status": "active",
                "trust_score": random.uniform(0.7, 1.0),
                "coordinates": (float(G.nodes[i]["pos"][0]), float(G.nodes[i]["pos"][1])),
                "ip_address": f"10.0.0.{i}",
                "uptime": random.randint(1, 30),
                "cpu_usage": random.uniform(10, 80),
                "memory_usage": random.uniform(20, 70),
                "bandwidth": random.uniform(10, 100)
            }
            
            # Add use-case specific attributes based on node type
            if node_types[i] == "client":
                if i % 4 == 0:  # Smart city nodes
                    node["device_type"] = "traffic_camera"
                    node["data_type"] = "video"
                    node["location"] = f"Intersection {random.randint(1, 20)}"
                elif i % 4 == 1:  # Healthcare nodes
                    node["device_type"] = "patient_monitor"
                    node["data_type"] = "vital_signs"
                    node["location"] = f"Hospital Room {random.randint(101, 450)}"
                elif i % 4 == 2:  # Financial nodes
                    node["device_type"] = "transaction_processor"
                    node["data_type"] = "transaction_logs"
                    node["location"] = f"Bank Branch {random.randint(1, 15)}"
                else:  # Mobile keyboard nodes
                    node["device_type"] = "smartphone"
                    node["data_type"] = "text_input"
                    node["battery_level"] = random.uniform(30, 100)
            
            self.nodes[f"node_{i}"] = node
        
        # Process links
        for u, v in G.edges():
            link_id = f"link_{u}_{v}"
            self.links[link_id] = {
                "id": link_id,
                "source": f"node_{u}",
                "target": f"node_{v}",
                "status": "active",
                "bandwidth": random.uniform(10, 100),
                "latency": random.uniform(5, 50),
                "packet_loss": random.uniform(0, 2),
                "throughput": random.uniform(5, 95),
                "utilization": random.uniform(10, 90)
            }
        
        # Save topology for visualization
        self.topology = {
            "nodes": list(self.nodes.values()),
            "links": list(self.links.values())
        }
    
    def _initialize_policies(self):
        """Initialize available policies for scenarios."""
        # Traffic Management Policies
        self.policies = [
            {
                "id": "traffic_opt_001",
                "name": "Traffic Signal Optimization",
                "description": "Optimize traffic signal timing based on ML predictions",
                "type": "Application",
                "scenario": "normal",
                "conditions": [
                    {"metric": "traffic_density", "operator": ">", "value": 75}
                ],
                "actions": [
                    {"action": "adjust_signals", "parameters": {"mode": "dynamic"}}
                ],
                "status": "Active"
            },
            {
                "id": "network_qos_001",
                "name": "QoS for Traffic Data",
                "description": "Apply QoS to ensure timely delivery of traffic data",
                "type": "SDN",
                "scenario": "normal",
                "conditions": [
                    {"metric": "data_type", "operator": "==", "value": "video"}
                ],
                "actions": [
                    {"action": "apply_qos", "parameters": {"priority": "high"}}
                ],
                "status": "Active"
            },
            # Healthcare Monitoring Policies
            {
                "id": "health_latency_001",
                "name": "Critical Alert Prioritization",
                "description": "Prioritize network for critical health alerts",
                "type": "SDN",
                "scenario": "congestion",
                "conditions": [
                    {"metric": "alert_type", "operator": "==", "value": "critical"}
                ],
                "actions": [
                    {"action": "prioritize_traffic", "parameters": {"level": "emergency"}}
                ],
                "status": "Active"
            },
            {
                "id": "congestion_mgmt_001",
                "name": "Network Congestion Management",
                "description": "Reroute traffic during congestion events",
                "type": "SDN",
                "scenario": "congestion",
                "conditions": [
                    {"metric": "network_load", "operator": ">", "value": 85}
                ],
                "actions": [
                    {"action": "reroute_traffic", "parameters": {"strategy": "least_congested"}}
                ],
                "status": "Standby"
            },
            # Financial Fraud Policies
            {
                "id": "security_node_001",
                "name": "Malicious Node Detection",
                "description": "Identify and isolate potentially malicious nodes",
                "type": "Security",
                "scenario": "security",
                "conditions": [
                    {"metric": "trust_score", "operator": "<", "value": 0.6}
                ],
                "actions": [
                    {"action": "isolate_node", "parameters": {"duration_minutes": 30}}
                ],
                "status": "Active"
            },
            {
                "id": "model_protection_001",
                "name": "Model Protection",
                "description": "Apply differential privacy to protect model integrity",
                "type": "FL",
                "scenario": "security",
                "conditions": [
                    {"metric": "attack_probability", "operator": ">", "value": 0.5}
                ],
                "actions": [
                    {"action": "apply_differential_privacy", "parameters": {"noise_level": "medium"}}
                ],
                "status": "Active"
            },
            # Mobile Keyboard Policies
            {
                "id": "resource_opt_001",
                "name": "Battery Preservation",
                "description": "Modify training based on device battery level",
                "type": "FL",
                "scenario": "resource",
                "conditions": [
                    {"metric": "battery_level", "operator": "<", "value": 30}
                ],
                "actions": [
                    {"action": "reduce_computation", "parameters": {"epochs": 2}}
                ],
                "status": "Active"
            },
            {
                "id": "model_compression_001",
                "name": "Model Compression",
                "description": "Compress model for resource-constrained devices",
                "type": "FL",
                "scenario": "resource",
                "conditions": [
                    {"metric": "available_memory", "operator": "<", "value": 500}
                ],
                "actions": [
                    {"action": "quantize_model", "parameters": {"bits": 8}}
                ],
                "status": "Active"
            }
        ]
    
    def set_scenario(self, scenario_id: str):
        """
        Set the current scenario.
        
        Args:
            scenario_id: Identifier for the scenario ('normal', 'congestion', 'security', 'resource')
        """
        if scenario_id in self.scenarios:
            self.current_scenario = scenario_id
            self.start_time = datetime.now()
            self.current_round = 0
            self.refresh_data()
            return True
        return False
    
    def refresh_data(self):
        """Update all scenario data based on the current scenario."""
        # Call the appropriate scenario generator function
        scenario_func = self.scenarios.get(self.current_scenario, self._smart_city_traffic_scenario)
        scenario_func()
        
        # Update time-dependent variables
        elapsed = (datetime.now() - self.start_time).total_seconds() * self.time_scale
        self.current_round = min(int(elapsed / 10), self.max_rounds)
        
        # Update active policies based on scenario
        self._update_active_policies()
    
    def _update_network_metrics(self, scenario_type: str):
        """
        Update network metrics based on scenario type.
        
        Args:
            scenario_type: Type of scenario affecting the network
        """
        # Update node metrics
        for node_id, node in self.nodes.items():
            # Base updates for all nodes
            node["cpu_usage"] = min(max(node["cpu_usage"] + random.uniform(-5, 5), 10), 95)
            node["memory_usage"] = min(max(node["memory_usage"] + random.uniform(-3, 3), 20), 95)
            
            # Scenario-specific updates
            if scenario_type == "normal":
                # Normal operation - stable metrics
                node["status"] = "active"
                node["trust_score"] = min(max(node["trust_score"] + random.uniform(-0.02, 0.02), 0.7), 1.0)
                
            elif scenario_type == "congestion":
                # Network congestion - high bandwidth usage, increased latency
                if node["type"] == "client" and random.random() < 0.3:
                    node["status"] = "congested"
                node["bandwidth"] = max(node["bandwidth"] * 0.8, 10)
                
            elif scenario_type == "security":
                # Security threat - some nodes have low trust scores
                if node["type"] == "client" and node_id in ["node_5", "node_12", "node_18"]:
                    node["status"] = "suspicious"
                    node["trust_score"] = max(node["trust_score"] * 0.7, 0.3)
                
            elif scenario_type == "resource":
                # Resource constraints - low battery, memory issues
                if "battery_level" in node:
                    node["battery_level"] = max(node["battery_level"] - random.uniform(0.5, 1.5), 10)
                if random.random() < 0.2:
                    node["status"] = "resource_limited"
        
        # Update link metrics
        for link_id, link in self.links.items():
            # Base updates
            link["latency"] = max(link["latency"] + random.uniform(-2, 2), 5)
            link["packet_loss"] = max(link["packet_loss"] + random.uniform(-0.5, 0.5), 0)
            
            # Scenario-specific updates
            if scenario_type == "normal":
                link["status"] = "active"
                link["utilization"] = min(max(link["utilization"] + random.uniform(-5, 5), 10), 90)
                
            elif scenario_type == "congestion":
                if random.random() < 0.4:
                    link["status"] = "congested"
                    link["utilization"] = min(link["utilization"] + random.uniform(3, 8), 98)
                    link["latency"] = min(link["latency"] * 1.5, 150)
                
            elif scenario_type == "security":
                src_node = link["source"]
                dst_node = link["target"]
                if src_node in ["node_5", "node_12", "node_18"] or dst_node in ["node_5", "node_12", "node_18"]:
                    link["status"] = "monitored"
                    
            elif scenario_type == "resource":
                link["utilization"] = min(max(link["utilization"] * 0.9, 10), 80)

        # Update topology
        self.topology = {
            "nodes": list(self.nodes.values()),
            "links": list(self.links.values())
        }
    
    def _update_fl_metrics(self, scenario_type: str):
        """
        Update federated learning metrics based on the scenario.
        
        Args:
            scenario_type: Type of scenario affecting FL metrics
        """
        # Calculate round-based progress
        progress = min(self.current_round / self.max_rounds, 1.0)
        
        # Base accuracy and loss curves (different for each scenario)
        if scenario_type == "normal":
            # Steady improvement
            accuracy = 0.5 + 0.45 * (1 - math.exp(-2.5 * progress))
            loss = 1.0 - 0.8 * (1 - math.exp(-3 * progress))
            participation = 0.9 - 0.1 * random.random()
            
        elif scenario_type == "congestion":
            # Good progress but with fluctuations due to network issues
            accuracy = 0.5 + 0.4 * (1 - math.exp(-2 * progress)) + 0.05 * math.sin(progress * 10)
            loss = 1.0 - 0.75 * (1 - math.exp(-2.5 * progress)) + 0.1 * math.sin(progress * 10)
            participation = 0.7 - 0.2 * random.random()
            
        elif scenario_type == "security":
            # Initially good then anomalous behavior causes issues
            if progress < 0.5:
                accuracy = 0.5 + 0.4 * (1 - math.exp(-3 * progress))
                loss = 1.0 - 0.7 * (1 - math.exp(-3 * progress))
            else:
                # Model poisoning attempt
                accuracy = 0.7 - 0.2 * (progress - 0.5)
                loss = 0.4 + 0.5 * (progress - 0.5)
            participation = 0.85 - 0.15 * random.random()
            
        else:  # resource
            # Slower progress due to resource constraints
            accuracy = 0.5 + 0.35 * (1 - math.exp(-1.5 * progress))
            loss = 1.0 - 0.6 * (1 - math.exp(-2 * progress))
            participation = 0.6 - 0.3 * random.random()
        
        # Add some noise
        accuracy += random.uniform(-0.02, 0.02)
        loss += random.uniform(-0.02, 0.02)
        
        # Ensure values are in valid ranges
        accuracy = min(max(accuracy, 0.0), 1.0)
        loss = min(max(loss, 0.0), 1.0)
        participation = min(max(participation, 0.0), 1.0)
        
        # Calculate training time based on scenario
        if scenario_type == "normal":
            training_time = 60 - 30 * progress + random.uniform(-5, 5)
        elif scenario_type == "congestion":
            training_time = 90 - 20 * progress + random.uniform(-10, 20)
        elif scenario_type == "security":
            training_time = 70 - 25 * progress + random.uniform(-5, 15)
        else:  # resource
            training_time = 120 - 40 * progress + random.uniform(-10, 10)
        
        training_time = max(training_time, 10)
        
        # Update FL metrics
        self.fl_metrics["rounds"].append(self.current_round)
        self.fl_metrics["accuracy"].append(accuracy)
        self.fl_metrics["loss"].append(loss)
        self.fl_metrics["participation_rate"].append(participation)
        self.fl_metrics["training_time"].append(training_time)
        
        # Trim lists if they get too long
        max_history = 20
        if len(self.fl_metrics["rounds"]) > max_history:
            for key in self.fl_metrics:
                self.fl_metrics[key] = self.fl_metrics[key][-max_history:]
    
    def _update_app_metrics(self, scenario_type: str):
        """
        Update application-specific metrics for the current scenario.
        
        Args:
            scenario_type: Type of scenario being simulated
        """
        # Calculate progress
        progress = min(self.current_round / self.max_rounds, 1.0)
        
        if scenario_type == "normal":  # Smart City Traffic
            # Traffic flow improvement (percentage)
            flow_improvement = 20 + 50 * progress + random.uniform(-5, 5)
            # Prediction accuracy for traffic patterns
            pred_accuracy = 0.6 + 0.35 * (1 - math.exp(-2 * progress)) + random.uniform(-0.03, 0.03)
            # Signal timing efficiency (percentage improvement)
            signal_efficiency = 15 + 40 * progress + random.uniform(-3, 3)
            
            # Update metrics
            self.app_metrics["normal"]["traffic_flow_improvement"].append(flow_improvement)
            self.app_metrics["normal"]["prediction_accuracy"].append(pred_accuracy)
            self.app_metrics["normal"]["signal_timing_efficiency"].append(signal_efficiency)
            
        elif scenario_type == "congestion":  # Healthcare Monitoring
            # Alert latency (seconds) - should decrease with training
            alert_latency = 10 - 5 * progress + random.uniform(-1, 3)
            # Anomaly detection rate (percentage)
            anomaly_detection = 70 + 25 * progress + random.uniform(-5, 5)
            # False alarm rate (percentage) - should decrease
            false_alarm = 15 - 10 * progress + random.uniform(-2, 4)
            
            # Update metrics
            self.app_metrics["congestion"]["alert_latency"].append(max(alert_latency, 1))
            self.app_metrics["congestion"]["anomaly_detection_rate"].append(min(anomaly_detection, 100))
            self.app_metrics["congestion"]["false_alarm_rate"].append(max(false_alarm, 1))
            
        elif scenario_type == "security":  # Financial Fraud
            # Fraud detection rate (percentage)
            if progress < 0.5:
                fraud_detection = 75 + 20 * progress + random.uniform(-3, 3)
            else:
                # Model poisoning causes issues
                fraud_detection = 85 - 30 * (progress - 0.5) + random.uniform(-5, 5)
            
            # False positive rate (percentage)
            if progress < 0.5:
                false_positive = 12 - 6 * progress + random.uniform(-1, 1)
            else:
                # Increases due to attack
                false_positive = 9 + 15 * (progress - 0.5) + random.uniform(-2, 2)
            
            # Model robustness score (0-100)
            if progress < 0.5:
                robustness = 70 + 20 * progress + random.uniform(-5, 5)
            else:
                # Decreases due to attack
                robustness = 80 - 40 * (progress - 0.5) + random.uniform(-7, 7)
            
            # Update metrics
            self.app_metrics["security"]["fraud_detection_rate"].append(min(max(fraud_detection, 40), 100))
            self.app_metrics["security"]["false_positive_rate"].append(min(max(false_positive, 1), 50))
            self.app_metrics["security"]["model_robustness"].append(min(max(robustness, 20), 100))
            
        elif scenario_type == "resource":  # Mobile Keyboard
            # Word prediction accuracy
            word_accuracy = 0.4 + 0.45 * (1 - math.exp(-1.8 * progress)) + random.uniform(-0.05, 0.05)
            # Battery consumption per prediction (percentage)
            battery_consumption = 0.5 - 0.3 * progress + random.uniform(-0.05, 0.05)
            # Model size (MB) - should decrease with optimization
            model_size = 20 - 12 * progress + random.uniform(-1, 1)
            
            # Update metrics
            self.app_metrics["resource"]["word_prediction_accuracy"].append(min(max(word_accuracy, 0.3), 0.95))
            self.app_metrics["resource"]["battery_consumption"].append(max(battery_consumption, 0.05))
            self.app_metrics["resource"]["model_size"].append(max(model_size, 5))
        
        # Trim lists if necessary
        max_history = 20
        for scenario in self.app_metrics:
            for metric in self.app_metrics[scenario]:
                if len(self.app_metrics[scenario][metric]) > max_history:
                    self.app_metrics[scenario][metric] = self.app_metrics[scenario][metric][-max_history:]
    
    def _update_active_policies(self):
        """Update active policies based on current scenario and conditions."""
        # Clear previous active policies
        self.active_policies = []
        
        # Add relevant policies based on scenario and conditions
        relevant_policies = [p for p in self.policies if p["scenario"] == self.current_scenario]
        
        # Simulate policy activation based on conditions
        for policy in relevant_policies:
            # Initially set as inactive
            policy["status"] = "Standby"
            
            # Check if conditions are met (simplified simulation)
            if self.current_scenario == "normal":
                # Activate traffic optimization in later rounds
                if policy["id"] == "traffic_opt_001" and self.current_round > 5:
                    policy["status"] = "Active"
                # QoS policy is always active
                if policy["id"] == "network_qos_001":
                    policy["status"] = "Active"
                    
            elif self.current_scenario == "congestion":
                # Critical alert prioritization is always active
                if policy["id"] == "health_latency_001":
                    policy["status"] = "Active"
                # Congestion management activates when needed
                if policy["id"] == "congestion_mgmt_001" and self.current_round > 3:
                    policy["status"] = "Active"
                    
            elif self.current_scenario == "security":
                # Malicious node detection activates after attack begins
                if policy["id"] == "security_node_001" and self.current_round > 8:
                    policy["status"] = "Active"
                # Model protection activates after security issues
                if policy["id"] == "model_protection_001" and self.current_round > 10:
                    policy["status"] = "Active"
                    
            elif self.current_scenario == "resource":
                # Battery preservation is occasionally active
                if policy["id"] == "resource_opt_001" and self.current_round % 3 == 0:
                    policy["status"] = "Active"
                # Model compression is always active
                if policy["id"] == "model_compression_001":
                    policy["status"] = "Active"
            
            # Add to active policies if activated
            if policy["status"] == "Active":
                self.active_policies.append(policy)
                
                # Add to policy history with timestamp
                history_entry = {
                    "policy_id": policy["id"],
                    "name": policy["name"],
                    "timestamp": datetime.now().isoformat(),
                    "scenario": self.current_scenario,
                    "result": "Applied" if random.random() < 0.9 else "Failed"
                }
                self.policy_history.append(history_entry)
        
        # Keep only recent history
        max_history = 50
        if len(self.policy_history) > max_history:
            self.policy_history = self.policy_history[-max_history:]
    
    def _smart_city_traffic_scenario(self):
        """Simulate Smart City Traffic Management scenario."""
        self._update_network_metrics("normal")
        self._update_fl_metrics("normal")
        self._update_app_metrics("normal")
    
    def _healthcare_monitoring_scenario(self):
        """Simulate Healthcare IoT Monitoring scenario with network congestion."""
        self._update_network_metrics("congestion")
        self._update_fl_metrics("congestion")
        self._update_app_metrics("congestion")
    
    def _financial_fraud_scenario(self):
        """Simulate Financial Fraud Detection scenario with security threats."""
        self._update_network_metrics("security")
        self._update_fl_metrics("security")
        self._update_app_metrics("security")
    
    def _mobile_keyboard_scenario(self):
        """Simulate Mobile Keyboard Prediction scenario with resource constraints."""
        self._update_network_metrics("resource")
        self._update_fl_metrics("resource")
        self._update_app_metrics("resource")
    
    def get_fl_metrics(self) -> Dict[str, Any]:
        """Get current federated learning metrics."""
        return {
            "rounds": self.fl_metrics["rounds"],
            "accuracy": self.fl_metrics["accuracy"],
            "loss": self.fl_metrics["loss"],
            "participation_rate": self.fl_metrics["participation_rate"],
            "training_time": self.fl_metrics["training_time"],
            "current_round": self.current_round,
            "max_rounds": self.max_rounds
        }
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """Get current network metrics."""
        # Calculate aggregated metrics
        active_nodes = sum(1 for node in self.nodes.values() if node["status"] == "active")
        total_nodes = len(self.nodes)
        
        active_links = sum(1 for link in self.links.values() if link["status"] == "active")
        total_links = len(self.links)
        
        avg_latency = sum(link["latency"] for link in self.links.values()) / total_links if total_links > 0 else 0
        avg_packet_loss = sum(link["packet_loss"] for link in self.links.values()) / total_links if total_links > 0 else 0
        
        return {
            "nodes": {
                "total": total_nodes,
                "active": active_nodes,
                "inactive": total_nodes - active_nodes
            },
            "links": {
                "total": total_links,
                "active": active_links,
                "congested": sum(1 for link in self.links.values() if link["status"] == "congested"),
                "inactive": total_links - active_links
            },
            "performance": {
                "avg_latency": avg_latency,
                "avg_packet_loss": avg_packet_loss,
                "avg_throughput": sum(link["throughput"] for link in self.links.values()) / total_links if total_links > 0 else 0,
                "avg_utilization": sum(link["utilization"] for link in self.links.values()) / total_links if total_links > 0 else 0
            },
            "topology": self.topology
        }
    
    def get_policy_metrics(self) -> Dict[str, Any]:
        """Get current policy metrics."""
        # Count policies by type
        policy_counts = {}
        for policy in self.policies:
            if policy["type"] not in policy_counts:
                policy_counts[policy["type"]] = {"total": 0, "active": 0}
            
            policy_counts[policy["type"]]["total"] += 1
            if policy["status"] == "Active":
                policy_counts[policy["type"]]["active"] += 1
        
        return {
            "active_policies": self.active_policies,
            "policy_history": self.policy_history,
            "policy_counts": policy_counts,
            "total_policies": len(self.policies),
            "active_count": len(self.active_policies)
        }
    
    def get_app_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics for the current scenario."""
        return {
            "scenario": self.current_scenario,
            "name": self.scenario_names[self.current_scenario],
            "description": self.scenario_descriptions[self.current_scenario],
            "metrics": self.app_metrics[self.current_scenario]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics for the dashboard."""
        return {
            "fl": self.get_fl_metrics(),
            "network": self.get_network_metrics(),
            "policy": self.get_policy_metrics(),
            "app": self.get_app_metrics(),
            "timestamp": datetime.now().isoformat(),
            "scenario": {
                "id": self.current_scenario,
                "name": self.scenario_names[self.current_scenario],
                "description": self.scenario_descriptions[self.current_scenario],
                "current_round": self.current_round,
                "max_rounds": self.max_rounds
            }
        }

# Singleton instance to be used throughout the application
scenario_manager = ScenarioManager() 