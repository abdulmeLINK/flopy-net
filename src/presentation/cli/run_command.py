"""
CLI Run Command

This module implements the CLI command for running federated learning
simulations and real-time scenarios.
"""
import os
import sys
import json
import argparse
import logging
import importlib.util
from typing import Dict, Any, List, Optional

from src.domain.interfaces.simulation_scenario import ISimulationScenario
from src.infrastructure.sdn import NETWORK_SIMULATORS, SDN_CONTROLLERS
from src.application.services.simulation_service import SimulationService
from src.application.services.sdn_service import SDNService


def run_command(args: argparse.Namespace) -> None:
    """
    Run the federated learning system based on command line arguments.
    
    Args:
        args: Command line arguments
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting federated learning run")
    
    # Load configuration
    config = _load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        sys.exit(1)
    
    # Initialize components based on run mode
    if args.mode == "simulation":
        _run_simulation(args, config)
    elif args.mode == "server":
        _run_server(args, config)
    elif args.mode == "client":
        _run_client(args, config)
    else:
        logger.error(f"Unknown run mode: {args.mode}")
        sys.exit(1)


def _load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return {}


def _run_simulation(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """
    Run a federated learning simulation.
    
    Args:
        args: Command line arguments
        config: Configuration dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info("Setting up simulation environment")
    
    # Initialize core services
    from src.application.policy.engine import PolicyEngine
    
    # Create policy engine
    policy_engine = PolicyEngine(config=config.get("policy"))
    policy_engine.start()
    
    # Load default policies
    for policy_name in ["client_selection", "simulation", "sdn"]:
        policy_engine.register_policy(policy_name)
    
    # Initialize mock FL server for simulation
    from src.infrastructure.clients.mock_fl_server import MockFLServer
    fl_server = MockFLServer(config=config.get("server"))
    
    # Select network simulator based on configuration
    simulator_type = args.simulator or config.get("simulation", {}).get("simulator", "mock")
    if simulator_type not in NETWORK_SIMULATORS:
        logger.error(f"Unknown network simulator: {simulator_type}")
        sys.exit(1)
    
    simulator_class = NETWORK_SIMULATORS[simulator_type]
    network_simulator = simulator_class(config=config.get("simulation", {}).get("network", {}))
    
    # Initialize SDN controller if needed
    sdn_controller = None
    controller_type = args.controller or config.get("simulation", {}).get("controller", "mock")
    if controller_type in SDN_CONTROLLERS:
        controller_class = SDN_CONTROLLERS[controller_type]
        sdn_controller = controller_class(config=config.get("simulation", {}).get("sdn_controller", {}))
    
    # Initialize SDN manager
    sdn_manager = SDNService(
        sdn_controller=sdn_controller,
        policy_engine=policy_engine,
        network_simulator=network_simulator,
        config=config.get("simulation", {}).get("sdn", {})
    )
    sdn_manager.initialize()
    
    # Initialize simulation manager
    simulation_manager = SimulationService(
        network_simulator=network_simulator,
        policy_engine=policy_engine,
        fl_server=fl_server,
        config=config.get("simulation", {})
    )
    
    # Load scenario from file or create default
    scenario = None
    if args.scenario:
        scenario = _load_scenario(args.scenario)
    else:
        # Use default scenario
        from src.domain.scenarios.default_scenario import DefaultScenario
        scenario = DefaultScenario()
    
    if not scenario:
        logger.error("Failed to load scenario")
        sys.exit(1)
    
    # Load scenario
    if not simulation_manager.load_scenario(scenario):
        logger.error("Failed to load scenario")
        sys.exit(1)
    
    # Register for simulation events
    simulation_manager.register_callback("simulation_completed", _on_simulation_completed)
    simulation_manager.register_callback("round_completed", _on_round_completed)
    
    # Start simulation
    if not simulation_manager.start_simulation():
        logger.error("Failed to start simulation")
        sys.exit(1)
    
    try:
        # Main monitoring loop
        import time
        while simulation_manager.get_simulation_status()["status"] == "running":
            # Display progress
            status = simulation_manager.get_simulation_status()
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
        
        print("\nSimulation completed")
        
        # Display final results
        status = simulation_manager.get_simulation_status()
        metrics = status["metrics"]
        
        print("\nFinal Results:")
        print(f"- Accuracy: {metrics.get('accuracy', 0) * 100:.2f}%")
        print(f"- Loss: {metrics.get('loss', 0):.4f}")
        print(f"- Rounds completed: {status['progress']['rounds_completed']}")
        print(f"- Events recorded: {status['events_count']}")
        
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        simulation_manager.stop_simulation()
    
    # Clean up
    policy_engine.stop()


def _run_server(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """
    Run a federated learning server.
    
    Args:
        args: Command line arguments
        config: Configuration dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting federated learning server")
    
    # Setup server components
    from src.application.policy.engine import PolicyEngine
    
    # Create policy engine
    policy_engine = PolicyEngine(config=config.get("policy"))
    policy_engine.start()
    
    # Load server-side policies
    for policy_name in ["client_selection", "sdn"]:
        policy_engine.register_policy(policy_name)
    
    # Initialize FL server
    from src.infrastructure.clients.fl_server_impl import FLServerImpl
    fl_server = FLServerImpl(config=config.get("server"))
    
    # Initialize SDN controller if specified
    sdn_controller = None
    controller_type = args.controller or config.get("sdn", {}).get("controller", None)
    if controller_type in SDN_CONTROLLERS:
        controller_class = SDN_CONTROLLERS[controller_type]
        sdn_controller = controller_class(config=config.get("sdn", {}).get("controller", {}))
    
        # Initialize SDN manager if controller is available
        if sdn_controller:
            sdn_manager = SDNService(
                sdn_controller=sdn_controller,
                policy_engine=policy_engine,
                config=config.get("sdn", {})
            )
            sdn_manager.initialize()
            logger.info("SDN manager initialized")
    
    # Start FL server
    server_host = args.host or config.get("api", {}).get("host", "0.0.0.0")
    server_port = args.port or config.get("api", {}).get("port", 5000)
    
    from src.presentation.rest.app import create_app
    app = create_app(
        fl_server=fl_server,
        policy_engine=policy_engine,
        sdn_controller=sdn_controller,
        config=config
    )
    
    logger.info(f"Starting server on {server_host}:{server_port}")
    app.run(host=server_host, port=server_port)


def _run_client(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """
    Run a federated learning client.
    
    Args:
        args: Command line arguments
        config: Configuration dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting federated learning client")
    
    # Initialize FL client
    from src.infrastructure.clients.fl_client_impl import FLClientImpl
    
    # Get server URL
    server_url = args.server_url or config.get("client", {}).get("server_url", "http://localhost:5000")
    
    # Initialize client
    client = FLClientImpl(
        server_url=server_url,
        config=config.get("client", {})
    )
    
    # Start client
    try:
        client.start()
        
        # Keep client running
        import time
        while client.is_running():
            time.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("Client interrupted by user")
        client.stop()


def _load_scenario(scenario_path: str) -> Optional[ISimulationScenario]:
    """
    Load a simulation scenario from a Python file.
    
    Args:
        scenario_path: Path to the scenario file
        
    Returns:
        Simulation scenario instance if successful, None otherwise
    """
    try:
        # Get absolute path to the scenario file
        absolute_path = os.path.abspath(scenario_path)
        
        # Load module from file
        spec = importlib.util.spec_from_file_location("scenario_module", absolute_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find first class that implements ISimulationScenario
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, ISimulationScenario) and obj != ISimulationScenario:
                return obj()
        
        logging.error(f"No valid simulation scenario found in {scenario_path}")
        return None
    
    except Exception as e:
        logging.error(f"Error loading scenario from {scenario_path}: {e}")
        return None


def _on_simulation_completed(event_data: Dict[str, Any]) -> None:
    """
    Handle simulation completed event.
    
    Args:
        event_data: Event data
    """
    scenario_name = event_data.get("scenario_name", "Unknown")
    duration = event_data.get("duration", 0)
    metrics = event_data.get("final_metrics", {})
    
    logging.info(f"Simulation '{scenario_name}' completed in {duration:.2f} seconds")
    logging.info(f"Final metrics: Accuracy={metrics.get('accuracy', 0)*100:.2f}%, "
               f"Loss={metrics.get('loss', 0):.4f}")


def _on_round_completed(event_data: Dict[str, Any]) -> None:
    """
    Handle round completed event.
    
    Args:
        event_data: Event data
    """
    round_num = event_data.get("round", 0)
    metrics = event_data.get("metrics", {})
    
    fl_metrics = metrics.get("fl", {})
    accuracy = fl_metrics.get("accuracy", 0) * 100
    loss = fl_metrics.get("loss", 0)
    
    logging.debug(f"Round {round_num} completed: Accuracy={accuracy:.2f}%, Loss={loss:.4f}")


def configure_parser(parser: argparse.ArgumentParser) -> None:
    """
    Configure the argument parser for the run command.
    
    Args:
        parser: Argument parser
    """
    parser.add_argument(
        "--mode", 
        choices=["simulation", "server", "client"], 
        default="simulation",
        help="Run mode (simulation, server, or client)"
    )
    
    parser.add_argument(
        "--config", 
        default="config.json",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--log-level", 
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level"
    )
    
    # Simulation options
    parser.add_argument(
        "--scenario", 
        help="Path to simulation scenario file"
    )
    
    parser.add_argument(
        "--simulator", 
        choices=["mininet", "mock"],
        help="Network simulator to use"
    )
    
    parser.add_argument(
        "--controller", 
        choices=["onos", "ryu", "mock"],
        help="SDN controller to use"
    )
    
    # Server options
    parser.add_argument(
        "--host", 
        help="Server host address"
    )
    
    parser.add_argument(
        "--port", 
        type=int,
        help="Server port"
    )
    
    # Client options
    parser.add_argument(
        "--server-url", 
        help="URL of the federated learning server"
    )


def setup_parser() -> argparse.ArgumentParser:
    """
    Set up and configure the argument parser for the run command.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Federated Learning System with SDN Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a simulation with the default configuration
  federated-learning run

  # Run a simulation with a specific scenario file
  federated-learning run --scenario scenarios/my_scenario.py

  # Run a simulation with a specific network simulator
  federated-learning run --simulator mininet

  # Run a server with the ONOS SDN controller
  federated-learning run --mode server --controller onos

  # Run a client that connects to a specific server
  federated-learning run --mode client --server-url http://server-host:5000
"""
    )
    
    configure_parser(parser)
    return parser


if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()
    run_command(args) 