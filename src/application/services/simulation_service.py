"""
Simulation Service

This module handles simulation of federated learning scenarios, coordinating
between SDN simulation, policy engine, and federated learning components.
"""
import time
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from src.domain.interfaces.network_simulator import INetworkSimulator
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.interfaces.fl_server import IFLServer
from src.domain.interfaces.simulation_scenario import ISimulationScenario


class SimulationService:
    """
    Simulation Service coordinates simulation scenarios with network and FL components.
    
    This class is responsible for:
    1. Loading and running simulation scenarios
    2. Coordinating between network simulator and FL components
    3. Collecting and reporting simulation metrics
    4. Managing simulation lifecycle (start, pause, resume, stop)
    """
    
    def __init__(self, 
                 network_simulator: INetworkSimulator,
                 policy_engine: IPolicyEngine,
                 fl_server: IFLServer,
                 config: Dict[str, Any] = None):
        """
        Initialize the Simulation Service.
        
        Args:
            network_simulator: Network simulator instance
            policy_engine: Policy engine for applying policies
            fl_server: Federated learning server instance
            config: Configuration dictionary
        """
        self.network_simulator = network_simulator
        self.policy_engine = policy_engine
        self.fl_server = fl_server
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        self.active_scenario = None
        self.scenario_thread = None
        self.running = False
        self.paused = False
        self.metrics = {}
        self.events = []
        self.start_time = None
        self.callbacks = {}
        
        self.output_dir = self.config.get("output_dir", "./simulation_output")
        
        self.logger.info("Simulation Service initialized")
    
    def load_scenario(self, scenario: ISimulationScenario) -> bool:
        """
        Load a simulation scenario.
        
        Args:
            scenario: Simulation scenario to load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self.active_scenario = scenario
            
            # Configure network simulator with scenario topology
            topology_config = scenario.get_topology_config()
            if not self.network_simulator.create_topology(topology_config):
                self.logger.error("Failed to create network topology")
                return False
            
            # Configure FL server with scenario settings
            server_config = scenario.get_server_config()
            self.fl_server.configure(server_config)
            
            # Register scenario policies with policy engine
            sdn_policies = scenario.get_sdn_policies()
            for policy in sdn_policies:
                policy_name = policy.get("name")
                if policy_name:
                    self.policy_engine.register_policy(policy_name, policy)
            
            self.logger.info(f"Loaded scenario: {scenario.get_name()}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error loading scenario: {e}")
            return False
    
    def start_simulation(self) -> bool:
        """
        Start the simulation.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self.active_scenario:
            self.logger.error("No scenario loaded")
            return False
        
        if self.running:
            self.logger.warning("Simulation already running")
            return True
        
        try:
            # Start network simulator
            if not self.network_simulator.start_simulation():
                self.logger.error("Failed to start network simulator")
                return False
            
            # Initialize metrics
            self.metrics = {
                "network": {},
                "fl": {
                    "accuracy": [],
                    "loss": [],
                    "communication_rounds": 0,
                    "participating_clients": [],
                    "training_time": []
                },
                "events": []
            }
            
            # Reset events
            self.events = []
            
            # Record start time
            self.start_time = time.time()
            
            # Start scenario in a separate thread
            self.running = True
            self.paused = False
            self.scenario_thread = threading.Thread(target=self._run_scenario)
            self.scenario_thread.daemon = True
            self.scenario_thread.start()
            
            self.logger.info(f"Started simulation: {self.active_scenario.get_name()}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error starting simulation: {e}")
            return False
    
    def _run_scenario(self) -> None:
        """Run the simulation scenario in a separate thread."""
        try:
            if not self.active_scenario:
                self.logger.error("No scenario loaded")
                return
            
            # Get client configurations
            client_configs = self.active_scenario.get_client_configs()
            
            # Add clients to simulation
            for client_config in client_configs:
                client_id = client_config.get("id")
                if client_id:
                    self.network_simulator.add_client_node(client_id, client_config)
            
            # Apply network conditions
            network_conditions = self.active_scenario.get_network_conditions()
            for condition in network_conditions:
                source = condition.get("source")
                target = condition.get("target")
                
                if not source or not target:
                    continue
                
                if "bandwidth" in condition:
                    bandwidth = condition["bandwidth"]
                    self.network_simulator.set_link_bandwidth(source, target, bandwidth)
                
                if "delay" in condition:
                    delay = condition["delay"]
                    self.network_simulator.add_link_delay(source, target, delay)
                
                if "loss" in condition:
                    loss = condition["loss"]
                    self.network_simulator.add_link_loss(source, target, loss)
            
            # Process simulation events (timed events)
            simulation_events = self.active_scenario.get_simulation_events()
            for event in simulation_events:
                event_type = event.get("type")
                trigger_time = event.get("trigger_time_seconds", 0)
                
                # Add event to thread pool for delayed execution
                timer = threading.Timer(trigger_time, self._handle_simulation_event, args=[event])
                timer.daemon = True
                timer.start()
            
            # Main simulation loop
            round_counter = 0
            max_rounds = self.active_scenario.get_server_config().get("max_rounds", 10)
            
            while self.running and round_counter < max_rounds:
                if self.paused:
                    time.sleep(0.5)
                    continue
                
                # Record round start time
                round_start = time.time()
                
                # Log simulation progress
                progress = (round_counter / max_rounds) * 100
                self.logger.info(f"Simulation progress: {progress:.1f}% (round {round_counter + 1}/{max_rounds})")
                
                # Trigger round started event
                self._trigger_callback("round_started", {
                    "round": round_counter + 1,
                    "max_rounds": max_rounds
                })
                
                # Collect network metrics
                network_metrics = self.network_simulator.get_performance_metrics()
                self.metrics["network"][f"round_{round_counter + 1}"] = network_metrics
                
                # Run a federated learning round
                fl_metrics = self._simulate_fl_round(round_counter)
                self.metrics["fl"]["accuracy"].append(fl_metrics.get("accuracy", 0))
                self.metrics["fl"]["loss"].append(fl_metrics.get("loss", 0))
                self.metrics["fl"]["participating_clients"].append(fl_metrics.get("participating_clients", []))
                
                # Calculate round duration
                round_duration = time.time() - round_start
                self.metrics["fl"]["training_time"].append(round_duration)
                
                # Record completed round
                self.metrics["fl"]["communication_rounds"] = round_counter + 1
                
                # Trigger round completed event
                self._trigger_callback("round_completed", {
                    "round": round_counter + 1,
                    "metrics": {
                        "network": network_metrics,
                        "fl": fl_metrics,
                        "duration": round_duration
                    }
                })
                
                # Move to next round
                round_counter += 1
                
                # Sleep to simulate real-time operation if needed
                if self.config.get("real_time_simulation", False):
                    time.sleep(self.config.get("round_interval_seconds", 5))
            
            # Simulation completed
            self.running = False
            self.logger.info(f"Simulation completed: {self.active_scenario.get_name()}")
            
            # Save simulation results
            self._save_simulation_results()
            
            # Trigger simulation completed event
            self._trigger_callback("simulation_completed", {
                "scenario_name": self.active_scenario.get_name(),
                "duration": time.time() - self.start_time,
                "rounds_completed": round_counter,
                "final_metrics": {
                    "accuracy": self.metrics["fl"]["accuracy"][-1] if self.metrics["fl"]["accuracy"] else 0,
                    "loss": self.metrics["fl"]["loss"][-1] if self.metrics["fl"]["loss"] else 0
                }
            })
        
        except Exception as e:
            self.logger.error(f"Error in simulation thread: {e}")
            self.running = False
    
    def _handle_simulation_event(self, event: Dict[str, Any]) -> None:
        """
        Handle a simulation event.
        
        Args:
            event: Event configuration dictionary
        """
        event_type = event.get("type")
        event_data = event.get("data", {})
        
        self.logger.info(f"Handling simulation event: {event_type}")
        
        # Record event
        self.events.append({
            "type": event_type,
            "time": time.time() - self.start_time,
            "data": event_data
        })
        
        # Handle different event types
        if event_type == "link_failure":
            source = event_data.get("source")
            target = event_data.get("target")
            
            if source and target:
                # Simulate link failure by setting very high packet loss
                self.network_simulator.add_link_loss(source, target, 100)
        
        elif event_type == "link_congestion":
            source = event_data.get("source")
            target = event_data.get("target")
            bandwidth = event_data.get("bandwidth", 10)  # Reduced bandwidth in Mbps
            
            if source and target:
                # Simulate congestion by reducing bandwidth
                self.network_simulator.set_link_bandwidth(source, target, bandwidth)
        
        elif event_type == "client_join":
            client_id = event_data.get("client_id")
            client_config = event_data.get("config", {})
            
            if client_id:
                # Add new client to simulation
                self.network_simulator.add_client_node(client_id, client_config)
        
        elif event_type == "client_leave":
            # This would be handled by the FL server in real scenarios
            # Here we just log the event
            client_id = event_data.get("client_id")
            if client_id:
                self.logger.info(f"Client leave event for client {client_id}")
        
        # Trigger event callback
        self._trigger_callback("simulation_event", {
            "type": event_type,
            "data": event_data,
            "time": time.time() - self.start_time
        })
    
    def _simulate_fl_round(self, round_num: int) -> Dict[str, Any]:
        """
        Simulate a federated learning round.
        
        Args:
            round_num: Current round number
            
        Returns:
            Dictionary of FL metrics for this round
        """
        # In a real implementation, this would interact with the FL server
        # For this simulation, we'll generate mock metrics
        
        # Simulated accuracy improvement over rounds (logarithmic curve)
        base_accuracy = 0.5
        max_accuracy = 0.95
        accuracy = base_accuracy + (max_accuracy - base_accuracy) * (1 - 1 / (1 + 0.3 * round_num))
        
        # Simulated loss decrease over rounds (exponential decay)
        base_loss = 2.0
        min_loss = 0.1
        loss = base_loss * (0.7 ** round_num) + min_loss
        
        # Get client count from network simulator
        client_count = len(self.active_scenario.get_client_configs())
        
        # Randomly select participating clients (70-90% participation)
        import random
        participation_rate = random.uniform(0.7, 0.9)
        clients_needed = max(2, int(client_count * participation_rate))
        clients = [f"client_{i}" for i in range(1, client_count + 1)]
        participating_clients = random.sample(clients, min(clients_needed, len(clients)))
        
        return {
            "round": round_num + 1,
            "accuracy": accuracy,
            "loss": loss,
            "participating_clients": participating_clients,
            "data_samples_processed": len(participating_clients) * 100,  # Mock value
            "model_size_bytes": 10 * 1024 * 1024  # 10MB mock model size
        }
    
    def _save_simulation_results(self) -> None:
        """Save simulation results to the output directory."""
        if not self.active_scenario:
            return
        
        try:
            import os
            import json
            from datetime import datetime
            
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            scenario_name = self.active_scenario.get_name().replace(" ", "_").lower()
            filename = f"{scenario_name}_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Prepare results
            results = {
                "scenario": {
                    "name": self.active_scenario.get_name(),
                    "description": self.active_scenario.get_description()
                },
                "timestamp": timestamp,
                "duration_seconds": time.time() - self.start_time if self.start_time else 0,
                "metrics": self.metrics,
                "events": self.events,
                "final_state": {
                    "accuracy": self.metrics["fl"]["accuracy"][-1] if self.metrics["fl"]["accuracy"] else 0,
                    "loss": self.metrics["fl"]["loss"][-1] if self.metrics["fl"]["loss"] else 0,
                    "rounds_completed": self.metrics["fl"]["communication_rounds"]
                }
            }
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Saved simulation results to {filepath}")
        
        except Exception as e:
            self.logger.error(f"Error saving simulation results: {e}")
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback function for a specific event type.
        
        Args:
            event_type: Event type to register for
            callback: Callback function to call when event occurs
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        
        self.callbacks[event_type].append(callback)
    
    def _trigger_callback(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Trigger callbacks for a specific event type.
        
        Args:
            event_type: Event type to trigger
            event_data: Event data to pass to callbacks
        """
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    self.logger.error(f"Error in simulation callback: {e}")
    
    def pause_simulation(self) -> bool:
        """
        Pause the simulation.
        
        Returns:
            True if paused successfully, False otherwise
        """
        if not self.running:
            self.logger.warning("Simulation not running")
            return False
        
        if self.paused:
            self.logger.warning("Simulation already paused")
            return True
        
        self.paused = True
        self.logger.info("Simulation paused")
        
        # Trigger pause event
        self._trigger_callback("simulation_paused", {
            "timestamp": time.time(),
            "elapsed_seconds": time.time() - self.start_time if self.start_time else 0
        })
        
        return True
    
    def resume_simulation(self) -> bool:
        """
        Resume the simulation.
        
        Returns:
            True if resumed successfully, False otherwise
        """
        if not self.running:
            self.logger.warning("Simulation not running")
            return False
        
        if not self.paused:
            self.logger.warning("Simulation not paused")
            return True
        
        self.paused = False
        self.logger.info("Simulation resumed")
        
        # Trigger resume event
        self._trigger_callback("simulation_resumed", {
            "timestamp": time.time(),
            "elapsed_seconds": time.time() - self.start_time if self.start_time else 0
        })
        
        return True
    
    def stop_simulation(self) -> bool:
        """
        Stop the simulation.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.running:
            self.logger.warning("Simulation not running")
            return True
        
        self.running = False
        self.paused = False
        
        # Stop network simulator
        self.network_simulator.stop_simulation()
        
        # Wait for scenario thread to complete
        if self.scenario_thread and self.scenario_thread.is_alive():
            self.scenario_thread.join(timeout=5.0)
        
        self.logger.info("Simulation stopped")
        
        # Trigger stop event
        self._trigger_callback("simulation_stopped", {
            "timestamp": time.time(),
            "elapsed_seconds": time.time() - self.start_time if self.start_time else 0,
            "rounds_completed": self.metrics["fl"]["communication_rounds"]
        })
        
        return True
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get the current simulation status.
        
        Returns:
            Dictionary containing simulation status information
        """
        if not self.active_scenario:
            return {"status": "no_scenario"}
        
        status = {
            "scenario": {
                "name": self.active_scenario.get_name(),
                "description": self.active_scenario.get_description()
            },
            "status": "running" if self.running else "stopped",
            "paused": self.paused,
            "progress": {
                "rounds_completed": self.metrics["fl"].get("communication_rounds", 0),
                "max_rounds": self.active_scenario.get_server_config().get("max_rounds", 10),
                "elapsed_seconds": time.time() - self.start_time if self.start_time and self.running else 0,
            },
            "metrics": {
                "accuracy": self.metrics["fl"]["accuracy"][-1] if self.metrics["fl"]["accuracy"] else 0,
                "loss": self.metrics["fl"]["loss"][-1] if self.metrics["fl"]["loss"] else 0,
                "network_summary": self._get_network_metrics_summary()
            },
            "events_count": len(self.events)
        }
        
        # Calculate progress percentage
        if status["progress"]["max_rounds"] > 0:
            status["progress"]["percentage"] = (status["progress"]["rounds_completed"] / 
                                             status["progress"]["max_rounds"]) * 100
        else:
            status["progress"]["percentage"] = 0
        
        return status
    
    def _get_network_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of network metrics.
        
        Returns:
            Dictionary containing network metrics summary
        """
        summary = {}
        
        # If we have network metrics from the last round, use those
        last_round = f"round_{self.metrics['fl'].get('communication_rounds', 0)}"
        if last_round in self.metrics.get("network", {}):
            network_data = self.metrics["network"][last_round]
            
            # Extract ping metrics
            if "ping" in network_data:
                ping_times = [data.get("avg_ms", 0) for data in network_data["ping"].values()]
                if ping_times:
                    summary["avg_ping_ms"] = sum(ping_times) / len(ping_times)
            
            # Extract bandwidth metrics
            if "bandwidth" in network_data:
                bandwidths = [data.get("bandwidth_mbps", 0) for data in network_data["bandwidth"].values()]
                if bandwidths:
                    summary["avg_bandwidth_mbps"] = sum(bandwidths) / len(bandwidths)
            
            # Extract congestion metrics
            if "congestion" in network_data:
                summary["congestion_level"] = network_data["congestion"].get("congestion_level", 0)
                summary["congested_links_count"] = len(network_data["congestion"].get("congested_links", []))
        
        return summary
    
    def get_simulation_metrics(self) -> Dict[str, Any]:
        """
        Get detailed simulation metrics.
        
        Returns:
            Dictionary containing detailed simulation metrics
        """
        return self.metrics
    
    def get_simulation_events(self) -> List[Dict[str, Any]]:
        """
        Get simulation events.
        
        Returns:
            List of simulation events
        """
        return self.events 