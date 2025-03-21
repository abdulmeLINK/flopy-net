#!/usr/bin/env python
"""
Run Federated Learning Simulation with Real Components

This script runs a federated learning simulation using real system components:
- Real policy engine
- Real server implementation
- Real SDN integration
- Only clients are simulated as we can't deploy physical devices
"""
import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, List

# Set logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('full_simulation.log')
    ]
)

# Import components
from src.domain.policy.rule_based_policy_engine import RuleBasedPolicyEngine
from src.infrastructure.repositories.in_memory_client_repository import InMemoryClientRepository
from src.infrastructure.repositories.file_model_repository import FileModelRepository
from src.infrastructure.sdn.mock_simulator import MockNetworkSimulator
from src.infrastructure.sdn.mock_controller import MockSDNController
from src.application.services.server_service import ServerService
from src.application.services.simulation_service import SimulationService
from src.application.services.sdn_service import SDNService
from src.application.services.policy_service import PolicyService
from src.application.services.model_service import ModelService


class SimulatedClient:
    """
    Simulated federated learning client.
    
    This class simulates a federated learning client for testing purposes.
    """
    
    def __init__(self, client_id: str, client_data: Dict[str, Any], logger: logging.Logger = None):
        """
        Initialize the simulated client.
        
        Args:
            client_id: Client identifier
            client_data: Client data and configuration
            logger: Logger instance
        """
        self.client_id = client_id
        self.data = client_data
        self.logger = logger or logging.getLogger(f"client.{client_id}")
        self.model = None
        self.status = "idle"
        self.connected = False
        self.resources = {
            "cpu_cores": client_data.get("cpu_cores", 2),
            "memory_mb": client_data.get("memory_mb", 4096),
            "battery_level": client_data.get("battery_level", 100),
            "network_bandwidth_mbps": client_data.get("network_bandwidth_mbps", 10)
        }
        
    def connect(self, server_service: ServerService) -> bool:
        """
        Connect to the federated learning server.
        
        Args:
            server_service: Server service instance
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Client {self.client_id} connecting to server")
            
            # Register client with server
            client_info = {
                "client_id": self.client_id,
                "capabilities": {
                    "hardware": {
                        "cpu_cores": self.resources["cpu_cores"],
                        "memory_mb": self.resources["memory_mb"]
                    },
                    "network": {
                        "bandwidth_mbps": self.resources["network_bandwidth_mbps"]
                    },
                    "power": {
                        "battery_level": self.resources["battery_level"],
                        "charging": self.data.get("charging", False)
                    }
                },
                "data_samples": self.data.get("data_samples", 0),
                "location": self.data.get("location", {"latitude": 0, "longitude": 0})
            }
            
            success = server_service.register_client(client_info)
            
            if success:
                self.logger.info(f"Client {self.client_id} successfully connected")
                self.connected = True
                self.status = "connected"
                return True
            else:
                self.logger.error(f"Client {self.client_id} failed to connect")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting client {self.client_id}: {e}")
            return False
    
    def download_model(self, server_service: ServerService) -> bool:
        """
        Download the global model from the server.
        
        Args:
            server_service: Server service instance
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            if not self.connected:
                self.logger.warning(f"Client {self.client_id} not connected")
                return False
                
            self.logger.info(f"Client {self.client_id} downloading model")
            self.status = "downloading"
            
            # Request model from server
            model = server_service.get_current_model_for_client(self.client_id)
            
            if model:
                self.logger.info(f"Client {self.client_id} successfully downloaded model")
                self.model = model
                self.status = "ready_to_train"
                return True
            else:
                self.logger.error(f"Client {self.client_id} failed to download model")
                self.status = "error"
                return False
                
        except Exception as e:
            self.logger.error(f"Error downloading model for client {self.client_id}: {e}")
            self.status = "error"
            return False
    
    def train(self, hyperparams: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Train the model using simulated data.
        
        Args:
            hyperparams: Training hyperparameters
            
        Returns:
            Dictionary with training results
        """
        try:
            if not self.model:
                self.logger.warning(f"Client {self.client_id} has no model to train")
                return {"success": False, "error": "No model available"}
                
            self.logger.info(f"Client {self.client_id} starting training")
            self.status = "training"
            
            # Simulate training delay based on resources and data size
            delay = self._calculate_training_delay()
            self.logger.info(f"Training will take {delay:.2f} seconds")
            time.sleep(delay)
            
            # Generate simulated model update and metrics
            model_update = self._generate_model_update()
            metrics = self._generate_training_metrics()
            
            self.logger.info(f"Client {self.client_id} completed training: {metrics}")
            self.status = "trained"
            
            return {
                "success": True,
                "model_update": model_update,
                "metrics": metrics
            }
                
        except Exception as e:
            self.logger.error(f"Error training model for client {self.client_id}: {e}")
            self.status = "error"
            return {"success": False, "error": str(e)}
    
    def upload_update(self, server_service: ServerService, update: Dict[str, Any]) -> bool:
        """
        Upload model update to the server.
        
        Args:
            server_service: Server service instance
            update: Model update and metrics
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            if not self.connected:
                self.logger.warning(f"Client {self.client_id} not connected")
                return False
                
            self.logger.info(f"Client {self.client_id} uploading model update")
            self.status = "uploading"
            
            # Upload update to server
            success = server_service.submit_client_update(
                client_id=self.client_id,
                model_update=update["model_update"],
                metrics=update["metrics"]
            )
            
            if success:
                self.logger.info(f"Client {self.client_id} successfully uploaded update")
                self.status = "completed"
                return True
            else:
                self.logger.error(f"Client {self.client_id} failed to upload update")
                self.status = "error"
                return False
                
        except Exception as e:
            self.logger.error(f"Error uploading update for client {self.client_id}: {e}")
            self.status = "error"
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the server.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            if not self.connected:
                return True
                
            self.logger.info(f"Client {self.client_id} disconnecting")
            self.connected = False
            self.status = "disconnected"
            return True
                
        except Exception as e:
            self.logger.error(f"Error disconnecting client {self.client_id}: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current client status.
        
        Returns:
            Dictionary with client status information
        """
        return {
            "client_id": self.client_id,
            "status": self.status,
            "connected": self.connected,
            "has_model": self.model is not None,
            "resources": self.resources
        }
    
    def _calculate_training_delay(self) -> float:
        """
        Calculate a simulated training delay based on client resources.
        
        Returns:
            Training delay in seconds
        """
        # Base delay
        delay = 5.0
        
        # Adjust based on CPU cores (more cores = less delay)
        cpu_factor = 4 / (self.resources["cpu_cores"] + 1)
        
        # Adjust based on memory (more memory = less delay)
        memory_factor = 1.0
        if self.resources["memory_mb"] < 2048:
            memory_factor = 2.0
        elif self.resources["memory_mb"] > 8192:
            memory_factor = 0.7
            
        # Adjust based on data size
        data_size = self.data.get("data_samples", 1000)
        data_factor = data_size / 1000
        
        # Combine factors
        total_delay = delay * cpu_factor * memory_factor * data_factor
        
        # Add some randomness (±20%)
        import random
        randomness = random.uniform(0.8, 1.2)
        
        return total_delay * randomness
    
    def _generate_model_update(self) -> Dict[str, Any]:
        """
        Generate a simulated model update.
        
        Returns:
            Dictionary with model update
        """
        import random
        
        # Generate simulated weights with small random changes
        return {
            "weights": [random.uniform(-1, 1) for _ in range(10)],
            "bias": random.uniform(-0.5, 0.5)
        }
    
    def _generate_training_metrics(self) -> Dict[str, Any]:
        """
        Generate simulated training metrics.
        
        Returns:
            Dictionary with training metrics
        """
        import random
        
        # Determine client capability level
        if self.resources["cpu_cores"] >= 4 and self.resources["memory_mb"] >= 8192:
            capability = "high"
        elif self.resources["cpu_cores"] >= 2 and self.resources["memory_mb"] >= 4096:
            capability = "medium"
        else:
            capability = "low"
            
        # Base metrics
        base_accuracy = 0.75
        base_loss = 0.25
        
        # Adjust metrics based on capability
        if capability == "high":
            accuracy_adjustment = random.uniform(0.10, 0.20)
            loss_adjustment = random.uniform(-0.15, -0.05)
        elif capability == "medium":
            accuracy_adjustment = random.uniform(0.05, 0.15)
            loss_adjustment = random.uniform(-0.10, 0)
        else:
            accuracy_adjustment = random.uniform(0, 0.10)
            loss_adjustment = random.uniform(-0.05, 0.05)
            
        # Calculate final metrics
        accuracy = min(0.99, base_accuracy + accuracy_adjustment)
        loss = max(0.01, base_loss + loss_adjustment)
        
        return {
            "accuracy": accuracy,
            "loss": loss,
            "training_time_seconds": self._calculate_training_delay(),
            "epochs_completed": 5,
            "data_samples_used": self.data.get("data_samples", 1000),
            "battery_consumed_percent": 0.5 if self.resources["battery_level"] > 20 else 0.3
        }


def create_policy_engine(config: Dict[str, Any], logger: logging.Logger) -> RuleBasedPolicyEngine:
    """
    Create and initialize a policy engine.
    
    Args:
        config: Policy configuration
        logger: Logger instance
        
    Returns:
        Initialized policy engine
    """
    logger.info("Creating policy engine")
    
    # Create engine
    policy_engine = RuleBasedPolicyEngine(config=config)
    
    # Register policies
    policy_engine.register_policy("client_selection")
    policy_engine.register_policy("resource")
    policy_engine.register_policy("privacy")
    policy_engine.register_policy("security")
    
    # Add custom rules
    def low_battery_condition(context):
        return context.get("battery_level", 100) < 20
    
    def low_battery_action(context):
        return {
            "decision": "deny",
            "reason": "Battery level too low"
        }
    
    policy_engine.add_rule("resource", low_battery_condition, low_battery_action)
    
    logger.info("Policy engine created and configured")
    return policy_engine


def create_client_configs(num_clients: int) -> List[Dict[str, Any]]:
    """
    Create configurations for simulated clients.
    
    Args:
        num_clients: Number of clients to create
        
    Returns:
        List of client configurations
    """
    import random
    
    clients = []
    
    # Define client capability profiles
    profiles = [
        {"name": "high", "weight": 0.2},
        {"name": "medium", "weight": 0.5},
        {"name": "low", "weight": 0.3}
    ]
    
    # Define data distributions
    distributions = [
        {"name": "iid", "weight": 0.5},
        {"name": "non_iid_label_skew", "weight": 0.3},
        {"name": "non_iid_quantity_skew", "weight": 0.2}
    ]
    
    for i in range(num_clients):
        # Select profile based on weights
        profile = random.choices(
            [p["name"] for p in profiles],
            [p["weight"] for p in profiles],
            k=1
        )[0]
        
        # Select data distribution based on weights
        distribution = random.choices(
            [d["name"] for d in distributions],
            [d["weight"] for d in distributions],
            k=1
        )[0]
        
        # Generate client configuration based on profile
        if profile == "high":
            config = {
                "cpu_cores": random.randint(4, 8),
                "memory_mb": random.randint(8192, 16384),
                "battery_level": random.randint(50, 100),
                "network_bandwidth_mbps": random.randint(50, 100),
                "charging": random.choices([True, False], [0.6, 0.4], k=1)[0],
                "data_samples": random.randint(5000, 10000),
                "distribution": distribution,
                "location": {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180)
                }
            }
        elif profile == "medium":
            config = {
                "cpu_cores": random.randint(2, 4),
                "memory_mb": random.randint(4096, 8192),
                "battery_level": random.randint(30, 90),
                "network_bandwidth_mbps": random.randint(20, 50),
                "charging": random.choices([True, False], [0.4, 0.6], k=1)[0],
                "data_samples": random.randint(2000, 5000),
                "distribution": distribution,
                "location": {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180)
                }
            }
        else:  # low
            config = {
                "cpu_cores": random.randint(1, 2),
                "memory_mb": random.randint(2048, 4096),
                "battery_level": random.randint(10, 70),
                "network_bandwidth_mbps": random.randint(5, 20),
                "charging": random.choices([True, False], [0.3, 0.7], k=1)[0],
                "data_samples": random.randint(500, 2000),
                "distribution": distribution,
                "location": {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180)
                }
            }
        
        clients.append(config)
    
    return clients


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run federated learning simulation with real components")
    
    parser.add_argument("--clients", type=int, default=10,
                        help="Number of simulated clients (default: 10)")
    parser.add_argument("--rounds", type=int, default=5,
                        help="Number of training rounds (default: 5)")
    parser.add_argument("--output-dir", type=str, default="./simulation_results",
                        help="Directory to store simulation results (default: ./simulation_results)")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO", help="Logging level (default: INFO)")
    
    return parser.parse_args()


def main():
    """Run the full simulation with real components."""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logger
    logger = logging.getLogger("full_simulation")
    logger.setLevel(getattr(logging, args.log_level))
    logger.info("Starting full simulation with real components")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Configuration
    config = {
        "output_dir": args.output_dir,
        "num_clients": args.clients,
        "num_rounds": args.rounds,
        "client_selection": {
            "min_clients": max(1, int(args.clients * 0.5)),
            "max_clients": args.clients,
            "selection_strategy": "random"
        },
        "policy": {
            "enabled": True
        },
        "server": {
            "aggregation_strategy": "fedavg",
            "model_repository_path": os.path.join(args.output_dir, "models")
        }
    }
    
    # Create policy engine
    policy_engine = create_policy_engine(config.get("policy"), logger)
    policy_engine.start()
    logger.info("Policy engine started")
    
    # Create policy service
    policy_service = PolicyService(policy_engine=policy_engine, logger=logger)
    
    # Create repositories
    model_repository = FileModelRepository(
        base_dir=config["server"]["model_repository_path"],
        logger=logger
    )
    client_repository = InMemoryClientRepository(logger=logger)
    
    # Create model service
    model_service = ModelService(model_repository=model_repository, logger=logger)
    
    # Create server service
    server_service = ServerService(
        client_repository=client_repository,
        model_repository=model_repository,
        policy_engine=policy_engine,
        logger=logger
    )
    
    # Create network simulator and SDN controller
    network_simulator = MockNetworkSimulator(config={})
    sdn_controller = MockSDNController(config={})
    
    # Create SDN service
    sdn_service = SDNService(
        sdn_controller=sdn_controller,
        policy_engine=policy_engine,
        network_simulator=network_simulator,
        logger=logger
    )
    sdn_service.initialize()
    logger.info("SDN service initialized")
    
    # Create network topology
    topology_config = {
        "type": "tree",
        "depth": 3,
        "fanout": 2,
        "hosts": args.clients,
        "links": [
            {"source": f"s1", "target": f"s2", "bandwidth": 1000, "delay": "5ms", "loss": 0.0},
            {"source": f"s1", "target": f"s3", "bandwidth": 1000, "delay": "5ms", "loss": 0.0},
            {"source": f"s2", "target": f"s4", "bandwidth": 100, "delay": "10ms", "loss": 0.01},
            {"source": f"s2", "target": f"s5", "bandwidth": 100, "delay": "10ms", "loss": 0.01},
            {"source": f"s3", "target": f"s6", "bandwidth": 100, "delay": "10ms", "loss": 0.01},
            {"source": f"s3", "target": f"s7", "bandwidth": 100, "delay": "10ms", "loss": 0.01}
        ]
    }
    
    network_simulator.create_topology(topology_config)
    network_simulator.start_simulation()
    logger.info("Network simulation started")
    
    # Create simulated clients
    client_configs = create_client_configs(args.clients)
    clients = []
    
    for i, client_config in enumerate(client_configs):
        client_id = f"client-{i+1}"
        client = SimulatedClient(
            client_id=client_id,
            client_data=client_config,
            logger=logger
        )
        clients.append(client)
        
        # Add to network simulation
        network_simulator.add_client_node(
            client_id=client_id,
            client_config={
                "host": f"h{i+1}",
                "bandwidth": client_config["network_bandwidth_mbps"],
                "delay": "5ms",
                "loss": 0.0
            }
        )
    
    logger.info(f"Created {len(clients)} simulated clients")
    
    # Connect clients to server
    connected_clients = []
    for client in clients:
        if client.connect(server_service):
            connected_clients.append(client)
    
    logger.info(f"{len(connected_clients)} clients connected to server")
    
    # Initialize global model
    initial_model = {
        "name": "initial_model",
        "version": "1.0.0",
        "weights": [0.0] * 10,
        "bias": 0.0
    }
    
    # Save initial model
    model_service.save_model(initial_model, version="initial")
    logger.info("Saved initial model")
    
    # Simulation metrics
    simulation_metrics = {
        "rounds": [],
        "global_accuracy": [],
        "global_loss": [],
        "participating_clients": [],
        "runtime_seconds": []
    }
    
    # Run simulation for specified number of rounds
    start_time = time.time()
    
    try:
        # Run FL rounds
        for round_num in range(1, args.rounds + 1):
            logger.info(f"\n=== Starting Round {round_num}/{args.rounds} ===")
            round_start_time = time.time()
            
            # Step 1: Client selection
            available_clients = [c for c in connected_clients if c.status != "error"]
            logger.info(f"Available clients: {len(available_clients)}")
            
            # Select clients based on policy
            min_clients = config["client_selection"]["min_clients"]
            max_clients = min(config["client_selection"]["max_clients"], len(available_clients))
            
            selected_client_ids = server_service.select_clients(min_clients, max_clients)
            selected_clients = [c for c in available_clients if c.client_id in selected_client_ids]
            
            logger.info(f"Selected {len(selected_clients)} clients for round {round_num}")
            
            # Step 2: Model distribution
            logger.info(f"Distributing model to {len(selected_clients)} clients")
            
            for client in selected_clients:
                client.download_model(server_service)
            
            # Step 3: Client training
            logger.info("Clients training...")
            training_results = []
            
            for client in selected_clients:
                # Check if client has model
                if not client.model:
                    logger.warning(f"Client {client.client_id} has no model, skipping training")
                    continue
                
                # Train model
                training_result = client.train()
                
                if training_result["success"]:
                    training_results.append({
                        "client_id": client.client_id,
                        "update": training_result
                    })
                else:
                    logger.warning(f"Client {client.client_id} training failed: {training_result.get('error')}")
            
            logger.info(f"{len(training_results)} clients completed training")
            
            # Step 4: Model update collection
            logger.info("Collecting model updates from clients")
            successful_updates = 0
            
            for result in training_results:
                client_id = result["client_id"]
                client = next((c for c in selected_clients if c.client_id == client_id), None)
                
                if client and client.upload_update(server_service, result["update"]):
                    successful_updates += 1
            
            logger.info(f"Collected {successful_updates} model updates")
            
            # Step 5: Model aggregation
            logger.info("Aggregating model updates")
            aggregation_result = server_service.aggregate_updates(round_num)
            
            if aggregation_result:
                logger.info("Model aggregation successful")
                
                # Get updated metrics
                global_metrics = server_service.get_current_round_metrics()
                global_accuracy = global_metrics.get("accuracy", 0.0)
                global_loss = global_metrics.get("loss", 0.0)
                
                logger.info(f"Round {round_num} results: Accuracy={global_accuracy:.4f}, Loss={global_loss:.4f}")
                
                # Save metrics
                simulation_metrics["rounds"].append(round_num)
                simulation_metrics["global_accuracy"].append(global_accuracy)
                simulation_metrics["global_loss"].append(global_loss)
                simulation_metrics["participating_clients"].append(len(selected_clients))
                
                round_duration = time.time() - round_start_time
                simulation_metrics["runtime_seconds"].append(round_duration)
                
                logger.info(f"Round {round_num} completed in {round_duration:.2f} seconds")
            else:
                logger.error("Model aggregation failed")
        
        # Simulation completed
        total_duration = time.time() - start_time
        logger.info(f"\n=== Simulation completed in {total_duration:.2f} seconds ===")
        
        # Save simulation results
        results_file = os.path.join(args.output_dir, "simulation_results.json")
        with open(results_file, "w") as f:
            json.dump({
                "configuration": config,
                "metrics": simulation_metrics,
                "total_duration_seconds": total_duration,
                "num_clients": args.clients,
                "num_rounds": args.rounds
            }, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        # Print final results
        print("\nFinal Results:")
        print("==============")
        print(f"Clients: {args.clients}")
        print(f"Rounds: {args.rounds}")
        print(f"Final accuracy: {simulation_metrics['global_accuracy'][-1]:.4f}")
        print(f"Final loss: {simulation_metrics['global_loss'][-1]:.4f}")
        print(f"Total duration: {total_duration:.2f} seconds")
        
        # Plot results if matplotlib is available
        try:
            import matplotlib.pyplot as plt
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
            
            # Plot accuracy
            ax1.plot(simulation_metrics["rounds"], simulation_metrics["global_accuracy"], marker='o')
            ax1.set_title("Global Model Accuracy")
            ax1.set_xlabel("Round")
            ax1.set_ylabel("Accuracy")
            ax1.grid(True)
            
            # Plot loss
            ax2.plot(simulation_metrics["rounds"], simulation_metrics["global_loss"], marker='o', color='red')
            ax2.set_title("Global Model Loss")
            ax2.set_xlabel("Round")
            ax2.set_ylabel("Loss")
            ax2.grid(True)
            
            plt.tight_layout()
            
            # Save plot
            plot_file = os.path.join(args.output_dir, "simulation_results.png")
            plt.savefig(plot_file)
            logger.info(f"Plot saved to {plot_file}")
            
        except ImportError:
            logger.warning("matplotlib not available, skipping plot generation")
        
    except KeyboardInterrupt:
        logger.info("\nSimulation interrupted by user")
    
    finally:
        # Clean up
        logger.info("Cleaning up simulation resources")
        
        # Disconnect clients
        for client in clients:
            client.disconnect()
        
        # Stop services
        network_simulator.stop_simulation()
        sdn_service.shutdown()
        policy_engine.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 