#!/usr/bin/env python
"""
Run Realistic Federated Learning Scenario

This script runs a realistic federated learning scenario with simulated clients,
real policy engine, and SDN integration.
"""
import os
import sys
import json
import logging

# Set logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import components
from src.domain.scenarios.realistic_scenario import RealisticScenario
from src.infrastructure.sdn.mock_simulator import MockNetworkSimulator
from src.infrastructure.sdn.mock_controller import MockSDNController
from src.infrastructure.clients.mock_fl_server import MockFLServer
from src.application.policy.engine import PolicyEngine
from src.application.services.simulation_service import SimulationService
from src.application.services.sdn_service import SDNService


def main():
    """Run the realistic federated learning scenario."""
    logger = logging.getLogger(__name__)
    logger.info("Starting the realistic federated learning scenario")
    
    # Load configurations
    config = {
        "output_dir": "./simulation_results",
        "real_time_simulation": True,
        "round_interval_seconds": 10,
        "logging": {
            "level": "info",
            "file": "simulation.log"
        },
        "simulation": {
            "network": {
                "simulator": "mock",
                "mininet_path": "mn"
            },
            "sdn": {
                "controller": "mock",
                "simulation_mode": True,
                "sdn_policy": {
                    "client_path_optimization": True,
                    "model_transfer_priority": "high",
                    "congestion_avoidance": True
                }
            }
        }
    }
    
    # Create output directory if it doesn't exist
    os.makedirs(config["output_dir"], exist_ok=True)
    
    # Initialize policy engine
    policy_engine = PolicyEngine(config=config.get("policy"))
    policy_engine.start()
    
    # Register policies
    for policy_name in ["client_selection", "simulation", "sdn"]:
        policy_engine.register_policy(policy_name)
        logger.info(f"Registered policy: {policy_name}")
    
    # Initialize mock FL server
    fl_server = MockFLServer(config=config.get("server"))
    
    # Initialize network simulator
    network_simulator = MockNetworkSimulator(config=config.get("simulation", {}).get("network", {}))
    
    # Initialize SDN controller
    sdn_controller = MockSDNController(config=config.get("simulation", {}).get("sdn_controller", {}))
    
    # Initialize SDN service
    sdn_service = SDNService(
        sdn_controller=sdn_controller,
        policy_engine=policy_engine,
        network_simulator=network_simulator,
        config=config.get("simulation", {}).get("sdn", {})
    )
    sdn_service.initialize()
    logger.info("Initialized SDN service")
    
    # Initialize simulation service
    simulation_service = SimulationService(
        network_simulator=network_simulator,
        policy_engine=policy_engine,
        fl_server=fl_server,
        config=config
    )
    
    # Load the realistic scenario
    scenario = RealisticScenario()
    if not simulation_service.load_scenario(scenario):
        logger.error("Failed to load realistic scenario")
        return 1
    
    # Register for simulation events
    simulation_service.register_callback("simulation_completed", on_simulation_completed)
    simulation_service.register_callback("round_completed", on_round_completed)
    
    # Print scenario information
    logger.info(f"Loaded scenario: {scenario.get_name()}")
    logger.info(f"Description: {scenario.get_description()}")
    logger.info(f"Clients: {len(scenario.get_client_configs())}")
    logger.info(f"Rounds: {scenario.get_server_config().get('max_rounds', 10)}")
    
    try:
        # Start the simulation
        if not simulation_service.start_simulation():
            logger.error("Failed to start simulation")
            return 1
        
        # Monitor simulation status
        import time
        print("\nSimulation Progress:")
        print("--------------------")
        
        while simulation_service.get_simulation_status()["status"] == "running":
            # Get current status
            status = simulation_service.get_simulation_status()
            progress = status["progress"]["percentage"]
            rounds = f"{status['progress']['rounds_completed']}/{status['progress']['max_rounds']}"
            
            # Display simulation stats
            metrics = status["metrics"]
            accuracy = metrics.get("accuracy", 0) * 100
            loss = metrics.get("loss", 0)
            
            # Display network metrics
            network = metrics.get("network_summary", {})
            avg_ping = network.get("avg_ping_ms", 0)
            congestion = network.get("congestion_level", 0) * 100
            
            print(f"\rProgress: {progress:.1f}% (Rounds: {rounds}) | "
                 f"Accuracy: {accuracy:.2f}% | Loss: {loss:.4f} | "
                 f"Ping: {avg_ping:.2f}ms | Congestion: {congestion:.1f}%", end="")
            
            time.sleep(1)
        
        print("\n\nSimulation completed successfully!")
        
        # Display final results
        status = simulation_service.get_simulation_status()
        metrics = status["metrics"]
        
        print("\nFinal Results:")
        print("------------------------")
        print(f"Accuracy: {metrics.get('accuracy', 0) * 100:.2f}%")
        print(f"Loss: {metrics.get('loss', 0):.4f}")
        print(f"Rounds completed: {status['progress']['rounds_completed']}")
        print(f"Events recorded: {status['events_count']}")
        
        # Clean up resources
        policy_engine.stop()
        sdn_service.shutdown()
        
        return 0
    
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        simulation_service.stop_simulation()
        policy_engine.stop()
        sdn_service.shutdown()
        return 0
    
    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        simulation_service.stop_simulation()
        policy_engine.stop()
        sdn_service.shutdown()
        return 1


def on_simulation_completed(event_data):
    """
    Handle simulation completed event.
    
    Args:
        event_data: Event data
    """
    logger = logging.getLogger(__name__)
    scenario_name = event_data.get("scenario_name", "Unknown")
    duration = event_data.get("duration", 0)
    metrics = event_data.get("final_metrics", {})
    
    logger.info(f"Simulation '{scenario_name}' completed in {duration:.2f} seconds")
    logger.info(f"Final metrics: Accuracy={metrics.get('accuracy', 0)*100:.2f}%, "
              f"Loss={metrics.get('loss', 0):.4f}")


def on_round_completed(event_data):
    """
    Handle round completed event.
    
    Args:
        event_data: Event data
    """
    logger = logging.getLogger(__name__)
    round_num = event_data.get("round", 0)
    metrics = event_data.get("metrics", {})
    
    fl_metrics = metrics.get("fl", {})
    accuracy = fl_metrics.get("accuracy", 0) * 100
    loss = fl_metrics.get("loss", 0)
    
    logger.info(f"Round {round_num} completed: Accuracy={accuracy:.2f}%, Loss={loss:.4f}")


if __name__ == "__main__":
    sys.exit(main()) 