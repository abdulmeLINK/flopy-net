#!/usr/bin/env python
"""
Run Simple Federated Learning Simulation

This script runs a simplified federated learning simulation using our infrastructure.
"""
import os
import sys
import logging
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fl_simulation")

# Import our infrastructure components
from src.domain.entities.fl_model import FLModel
from src.domain.entities.client import Client
from src.application.fl_strategies.federated_averaging import FederatedAveraging
from src.infrastructure.repositories.in_memory_client_repository import InMemoryClientRepository
from src.infrastructure.repositories.file_model_repository import FileModelRepository


def init_model() -> FLModel:
    """
    Initialize a simple model with random weights.
    
    Returns:
        Initial model
    """
    # Create a simple model with random weights
    weights = [np.random.rand(10, 10).astype(np.float32) for _ in range(3)]
    
    # Create FLModel instance
    model = FLModel(
        name="simple_model",
        weights=weights
    )
    
    model.metadata = {
        "architecture": "simple_nn",
        "input_shape": [10],
        "output_shape": [10],
        "layers": 3,
        "parameters": sum(w.size for w in weights)
    }
    
    return model


def create_clients(num_clients: int) -> dict:
    """
    Create simulated clients.
    
    Args:
        num_clients: Number of clients to create
    
    Returns:
        Dictionary of clients
    """
    clients = {}
    
    for i in range(num_clients):
        client_id = f"client-{i+1}"
        client = Client(
            client_id=client_id,
            name=f"Client {i+1}"
        )
        client.capabilities = {
            "cpu_cores": np.random.randint(2, 8),
            "memory_mb": np.random.randint(4096, 16384),
            "network_bandwidth_mbps": np.random.randint(10, 100)
        }
        client.update_last_seen()
        
        clients[client_id] = client
    
    return clients


def train_local_model(global_weights, client_id, client_data_size):
    """
    Simulate training on a client.
    
    Args:
        global_weights: Global model weights
        client_id: Client identifier
        client_data_size: Size of client data
        
    Returns:
        Updated weights and metrics
    """
    # Copy global weights and add some random updates
    # In a real system, this would be actual training
    local_weights = [w.copy() + np.random.normal(0, 0.01, w.shape) for w in global_weights]
    
    # Simulate metrics
    metrics = {
        "loss": np.random.uniform(0.5, 2.0),
        "accuracy": np.random.uniform(0.7, 0.95),
        "training_time_seconds": np.random.uniform(5, 30),
        "epochs": 5,
        "data_samples": client_data_size
    }
    
    return local_weights, metrics


def run_simulation(num_rounds, num_clients, output_dir):
    """
    Run the federated learning simulation.
    
    Args:
        num_rounds: Number of training rounds
        num_clients: Number of clients
        output_dir: Output directory for results
    """
    logger.info(f"Starting simulation with {num_clients} clients for {num_rounds} rounds")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize repositories
    client_repo = InMemoryClientRepository()
    model_repo = FileModelRepository(base_dir=output_dir)
    
    # Initialize aggregator
    aggregator = FederatedAveraging()
    
    # Initialize global model
    global_model = init_model()
    
    # Save initial model
    model_repo.save_model(global_model)
    logger.info(f"Saved initial model to {output_dir}")
    
    # Create clients
    clients = create_clients(num_clients)
    for client in clients.values():
        client_repo.add_client(client)
    
    # Track metrics across rounds
    round_metrics = []
    
    # Run federated learning rounds
    for round_num in range(1, num_rounds + 1):
        logger.info(f"Starting round {round_num}")
        
        # Select clients for this round (in a real system, this would use policies)
        # Here we randomly select 70% of clients
        num_selected = max(2, int(0.7 * num_clients))
        selected_client_ids = np.random.choice(list(clients.keys()), num_selected, replace=False)
        logger.info(f"Selected {len(selected_client_ids)} clients for round {round_num}")
        
        # Get client updates
        client_updates = []
        for client_id in selected_client_ids:
            # Simulate different data sizes for clients
            client_data_size = np.random.randint(500, 5000)
            
            # Train local model (simulated)
            local_weights, metrics = train_local_model(
                global_model.weights, 
                client_id, 
                client_data_size
            )
            
            # Create update
            update = {
                "client_id": client_id,
                "weights": local_weights,
                "metadata": {
                    "sample_count": client_data_size,
                    "training_metrics": metrics
                }
            }
            
            client_updates.append(update)
            
            # Store client update
            client_repo.add_client_update(client_id, update)
        
        # Aggregate updates
        logger.info(f"Aggregating {len(client_updates)} client updates")
        aggregated_model = aggregator.aggregate(
            {"weights": global_model.weights, "metadata": global_model.metadata},
            client_updates
        )
        
        # Update global model
        global_model.update_weights(aggregated_model["weights"])
        global_model.metadata.update(aggregated_model["metadata"])
        global_model.metadata["round"] = round_num
        global_model.metadata["timestamp"] = datetime.now().isoformat()
        
        # Save updated model
        model_repo.save_model(global_model, version=f"round_{round_num}")
        
        # Calculate round metrics (in a real system, this would be validation)
        # Here we just average client metrics
        round_accuracy = np.mean([
            update["metadata"]["training_metrics"]["accuracy"] 
            for update in client_updates
        ])
        round_loss = np.mean([
            update["metadata"]["training_metrics"]["loss"] 
            for update in client_updates
        ])
        
        logger.info(f"Round {round_num} metrics - Accuracy: {round_accuracy:.4f}, Loss: {round_loss:.4f}")
        
        # Store round metrics
        round_metrics.append({
            "round": round_num,
            "accuracy": round_accuracy,
            "loss": round_loss,
            "participating_clients": len(client_updates)
        })
    
    # Plot and save metrics
    plot_metrics(round_metrics, output_dir)
    
    logger.info(f"Simulation completed. Results saved to {output_dir}")
    return round_metrics


def plot_metrics(metrics, output_dir):
    """
    Plot and save metrics from the simulation.
    
    Args:
        metrics: List of metrics dictionaries
        output_dir: Output directory
    """
    rounds = [m["round"] for m in metrics]
    accuracy = [m["accuracy"] for m in metrics]
    loss = [m["loss"] for m in metrics]
    
    plt.figure(figsize=(12, 5))
    
    # Plot accuracy
    plt.subplot(1, 2, 1)
    plt.plot(rounds, accuracy, 'b-o', linewidth=2)
    plt.title('Model Accuracy by Round')
    plt.xlabel('Round')
    plt.ylabel('Accuracy')
    plt.grid(True)
    
    # Plot loss
    plt.subplot(1, 2, 2)
    plt.plot(rounds, loss, 'r-o', linewidth=2)
    plt.title('Model Loss by Round')
    plt.xlabel('Round')
    plt.ylabel('Loss')
    plt.grid(True)
    
    plt.tight_layout()
    
    # Save plot
    plt.savefig(os.path.join(output_dir, 'metrics.png'))
    plt.close()
    
    # Save metrics as CSV
    import csv
    with open(os.path.join(output_dir, 'metrics.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=metrics[0].keys())
        writer.writeheader()
        writer.writerows(metrics)


def main():
    """Main function to run the simulation."""
    # Set default parameters
    num_rounds = 10
    num_clients = 20
    output_dir = "models/simple_simulation"
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run a simple federated learning simulation")
    parser.add_argument("--rounds", type=int, default=num_rounds, help="Number of training rounds")
    parser.add_argument("--clients", type=int, default=num_clients, help="Number of clients")
    parser.add_argument("--output-dir", type=str, default=output_dir, help="Output directory")
    args = parser.parse_args()
    
    # Run simulation
    run_simulation(args.rounds, args.clients, args.output_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 