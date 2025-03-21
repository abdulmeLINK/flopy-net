"""
Simulation Runner Service

This module provides the service for running federated learning simulations
with different scenarios and policy configurations.
"""
import logging
import time
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable

from src.domain.policy.policy_engine import PolicyEngine
from src.domain.scenarios.scenario_registry import ScenarioRegistry, ISimulationScenario

# Configure logging
logger = logging.getLogger(__name__)

class SimulationStatus(Enum):
    """Enumeration of simulation status states."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimulationInfo:
    """Data class for storing simulation information."""
    id: str
    scenario_name: str
    scenario: ISimulationScenario
    status: SimulationStatus
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    config_overrides: Dict[str, Any] = None
    metrics: Dict[str, Any] = None
    policy_engine: Optional[PolicyEngine] = None


class SimulationRunner:
    """
    Simulation Runner for federated learning simulations.
    
    This class provides functionality to start, stop, and manage
    federated learning simulations with different scenarios.
    """
    
    _instance = None
    
    def __new__(cls):
        """
        Create a new instance of SimulationRunner using the Singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super(SimulationRunner, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the simulation runner.
        """
        if not self._initialized:
            self._initialized = True
            self._simulations = {}
            self._scenario_registry = ScenarioRegistry()
            self._simulation_threads = {}
            self._stop_events = {}
            self._policy_check_interval = 60  # seconds
            logger.info("Simulation runner initialized")
    
    def start_simulation(self, scenario_name: str, simulation_id: str = None, 
                       config_overrides: Dict[str, Any] = None,
                       policy_config: Dict[str, Any] = None) -> Optional[str]:
        """
        Start a new simulation with the specified scenario.
        
        Args:
            scenario_name: The name of the scenario to run
            simulation_id: Optional ID for the simulation (auto-generated if not provided)
            config_overrides: Optional configuration overrides for the scenario
            policy_config: Optional policy configuration overrides
            
        Returns:
            The simulation ID if successful, None otherwise
        """
        # Generate simulation ID if not provided
        if simulation_id is None:
            simulation_id = f"sim_{int(time.time())}_{scenario_name}"
        
        # Check if simulation with this ID already exists
        if simulation_id in self._simulations:
            logger.error(f"Simulation with ID {simulation_id} already exists")
            return None
        
        # Get the scenario
        scenario = self._scenario_registry.get_scenario(scenario_name)
        if scenario is None:
            logger.error(f"Scenario '{scenario_name}' not found")
            return None
        
        # Initialize policy engine for this simulation
        policy_engine = PolicyEngine()
        policy_engine.load_policies_for_domain(scenario_name)
        
        # Apply policy overrides if provided
        if policy_config:
            policy_engine.update_policy_config(policy_config)
        
        # Create simulation info
        simulation_info = SimulationInfo(
            id=simulation_id,
            scenario_name=scenario_name,
            scenario=scenario,
            status=SimulationStatus.NOT_STARTED,
            config_overrides=config_overrides,
            metrics={},
            policy_engine=policy_engine
        )
        
        # Store simulation info
        self._simulations[simulation_id] = simulation_info
        
        # Create stop event for the simulation thread
        stop_event = threading.Event()
        self._stop_events[simulation_id] = stop_event
        
        # Apply policy rules to the scenario configuration
        self._apply_policy_rules(simulation_info)
        
        # Start simulation in a separate thread
        simulation_thread = threading.Thread(
            target=self._run_simulation,
            args=(simulation_id, stop_event),
            daemon=True
        )
        self._simulation_threads[simulation_id] = simulation_thread
        simulation_thread.start()
        
        logger.info(f"Started simulation {simulation_id} with scenario {scenario_name}")
        return simulation_id
    
    def _apply_policy_rules(self, simulation_info: SimulationInfo) -> None:
        """
        Apply policy rules to the simulation configuration.
        
        Args:
            simulation_info: The simulation information
        """
        policy_engine = simulation_info.policy_engine
        if not policy_engine:
            logger.warning("No policy engine available for simulation")
            return
        
        logger.info(f"Applying policy rules to simulation {simulation_info.id}")
        
        # Apply server configuration policies
        server_config = simulation_info.scenario.get_server_config()
        server_policies = policy_engine.query_policies("server_config")
        for policy in server_policies:
            for key, value in policy.items():
                if key in server_config:
                    logger.info(f"Applying server policy: {key}={value}")
                    server_config[key] = value
        
        # Apply client selection policies
        client_configs = simulation_info.scenario.get_client_configs()
        client_policies = policy_engine.query_policies("client_selection")
        for client_config in client_configs:
            for policy in client_policies:
                for key, value in policy.items():
                    if key in client_config:
                        logger.info(f"Applying client policy: {key}={value}")
                        client_config[key] = value
        
        # Apply network policies
        network_policies = policy_engine.query_policies("network")
        sdn_policies = simulation_info.scenario.get_sdn_policies()
        for policy in network_policies:
            for key, value in policy.items():
                if key in sdn_policies:
                    logger.info(f"Applying network policy: {key}={value}")
                    sdn_policies[key] = value
    
    def _check_policy_updates(self, simulation_info: SimulationInfo) -> None:
        """
        Check for policy updates during simulation.
        
        Args:
            simulation_info: The simulation information
        """
        policy_engine = simulation_info.policy_engine
        if not policy_engine:
            return
        
        # Refresh policies for the domain
        policy_engine.refresh_policies(simulation_info.scenario_name)
        
        # Re-apply policy rules
        self._apply_policy_rules(simulation_info)
    
    def _run_simulation(self, simulation_id: str, stop_event: threading.Event) -> None:
        """
        Run the simulation in a separate thread.
        
        Args:
            simulation_id: The simulation ID
            stop_event: Event to signal the thread to stop
        """
        simulation_info = self._simulations.get(simulation_id)
        if not simulation_info:
            logger.error(f"Simulation {simulation_id} not found")
            return
        
        try:
            # Update simulation status
            simulation_info.status = SimulationStatus.RUNNING
            simulation_info.start_time = time.time()
            
            logger.info(f"Running simulation {simulation_id}")
            
            # TODO: Implement actual simulation logic here
            # This would include setting up the network topology, deploying clients,
            # configuring the server, and running the federated learning process
            
            # Simulate running a federated learning process
            last_policy_check = time.time()
            iteration = 0
            
            while not stop_event.is_set():
                # Check if it's time to check for policy updates
                current_time = time.time()
                if current_time - last_policy_check > self._policy_check_interval:
                    self._check_policy_updates(simulation_info)
                    last_policy_check = current_time
                
                # Simulate a federated learning iteration
                logger.info(f"Simulation {simulation_id} iteration {iteration}")
                
                # Collect metrics
                simulation_info.metrics[f"iteration_{iteration}"] = {
                    "accuracy": 0.5 + 0.01 * iteration,  # Simulated accuracy improvement
                    "loss": 1.0 - 0.01 * iteration,  # Simulated loss reduction
                    "clients_participated": 10
                }
                
                iteration += 1
                
                # End simulation after a number of iterations
                if iteration >= 10:
                    break
                
                # Sleep to simulate time passing
                time.sleep(1)
                
                # Check if simulation has been paused or stopped
                if stop_event.is_set():
                    break
            
            # Update simulation status based on stop condition
            if stop_event.is_set():
                simulation_info.status = SimulationStatus.PAUSED
            else:
                simulation_info.status = SimulationStatus.COMPLETED
                
        except Exception as e:
            logger.error(f"Error running simulation {simulation_id}: {str(e)}")
            simulation_info.status = SimulationStatus.FAILED
            simulation_info.metrics["error"] = str(e)
        finally:
            simulation_info.end_time = time.time()
    
    def stop_simulation(self, simulation_id: str) -> bool:
        """
        Stop a running simulation.
        
        Args:
            simulation_id: The ID of the simulation to stop
            
        Returns:
            True if successful, False otherwise
        """
        if simulation_id not in self._simulations:
            logger.error(f"Simulation {simulation_id} not found")
            return False
        
        simulation_info = self._simulations[simulation_id]
        
        if simulation_info.status != SimulationStatus.RUNNING:
            logger.warning(f"Simulation {simulation_id} is not running")
            return False
        
        # Signal the simulation thread to stop
        stop_event = self._stop_events.get(simulation_id)
        if stop_event:
            stop_event.set()
        
        # Wait for the thread to finish
        simulation_thread = self._simulation_threads.get(simulation_id)
        if simulation_thread and simulation_thread.is_alive():
            simulation_thread.join(timeout=5)
        
        logger.info(f"Stopped simulation {simulation_id}")
        return True
    
    def get_simulation_info(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a simulation.
        
        Args:
            simulation_id: The ID of the simulation
            
        Returns:
            Dictionary with simulation information if found, None otherwise
        """
        simulation_info = self._simulations.get(simulation_id)
        if not simulation_info:
            logger.error(f"Simulation {simulation_id} not found")
            return None
        
        # Convert simulation info to dictionary
        result = {
            "id": simulation_info.id,
            "scenario_name": simulation_info.scenario_name,
            "status": simulation_info.status.value,
            "start_time": simulation_info.start_time,
            "end_time": simulation_info.end_time,
            "metrics": simulation_info.metrics
        }
        
        return result
    
    def list_simulations(self) -> List[Dict[str, Any]]:
        """
        List all simulations.
        
        Returns:
            List of dictionaries with simulation information
        """
        result = []
        for simulation_id, simulation_info in self._simulations.items():
            result.append({
                "id": simulation_id,
                "scenario_name": simulation_info.scenario_name,
                "status": simulation_info.status.value,
                "start_time": simulation_info.start_time,
                "end_time": simulation_info.end_time
            })
        return result
    
    def get_available_scenarios(self) -> List[Dict[str, str]]:
        """
        Get a list of available scenarios.
        
        Returns:
            List of dictionaries with scenario information
        """
        return self._scenario_registry.get_scenario_info() 