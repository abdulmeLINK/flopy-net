"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Run Flower-based Federated Learning system.

This script demonstrates how to run a federated learning system using the Flower framework.
"""

import argparse
import logging
import sys
import os
import threading
import time
import json
from typing import Dict, List, Any
import random

# Add the project root to the path to ensure imports work
import sys

# Import Flower framework
import flwr as fl
from flwr.common import (
    Parameters, ndarrays_to_parameters, parameters_to_ndarrays
)
import numpy as np

# Import server and client
from src.fl.server.fl_server import FLServer
from src.fl.client.fl_client import FlowerClient
from src.core.models.handlers.model_handler import ModelHandler
from src.metrics.metrics_service import MetricsService
from src.policy_engine.policy_engine import PolicyEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("./logs/flower_federated_learning.log")
    ]
)
logger = logging.getLogger("flower_fl")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Flower-based Federated Learning")
    
    parser.add_argument(
        "--clients", type=int, default=5,
        help="Number of clients to simulate"
    )
    parser.add_argument(
        "--rounds", type=int, default=5,
        help="Number of training rounds"
    )
    parser.add_argument(
        "--local_epochs", type=int, default=3,
        help="Number of local training epochs on each client"
    )
    parser.add_argument(
        "--batch_size", type=int, default=32,
        help="Batch size for training"
    )
    parser.add_argument(
        "--model", type=str, default="cnn",
        help="Model architecture (cnn, mlp)"
    )
    parser.add_argument(
        "--dataset", type=str, default="mnist",
        help="Dataset to use (mnist, cifar10, fashion_mnist)"
    )
    parser.add_argument(
        "--server_address", type=str, default="0.0.0.0:8080",
        help="Address of the server"
    )
    parser.add_argument(
        "--client_only", action="store_true",
        help="Run only client(s), not the server"
    )
    parser.add_argument(
        "--server_only", action="store_true",
        help="Run only the server, not clients"
    )
    parser.add_argument(
        "--secure_aggregation", action="store_true",
        help="Enable secure aggregation"
    )
    
    return parser.parse_args()

def start_server(args):
    """Start the Flower server."""
    logger.info(f"Starting server with {args.rounds} rounds")
    
    # Create metrics service
    metrics_service = MetricsService()
    
    # Create policy engine (optional)
    try:
        policy_engine = PolicyEngine()
        logger.info("Created policy engine")
    except Exception as e:
        logger.warning(f"Could not create policy engine: {str(e)}")
        policy_engine = None
    
    # Create model
    model = FederatedModel()
    
    # Configure model_config
    model_config = {
        "type": args.model,
        "dataset": args.dataset,
        "num_classes": 10 if args.dataset == "mnist" else 10,
        "lr": 0.01,
        "batch_size": args.batch_size,
    }
    
    # Create server
    server = FLServer(
        model=model,
        policy_engine=policy_engine,
        num_rounds=args.rounds,
        client_sample_size=args.clients,
        secure_aggregation=args.secure_aggregation,
        min_clients_for_aggregation=max(2, args.clients // 2),  # At least half of clients
        metrics_service=metrics_service,
        model_config=model_config
    )
    
    # Start the server
    server.start_server(server_address=args.server_address)

def start_client(client_id, args, server_address):
    """Start a Flower client."""
    # Create metrics service
    metrics_service = MetricsService()
    
    # Create model handler and data loader
    try:
        # Attempt to import modules that may be available in the real system
        from src.fl.client.data_loader import DataLoader
        
        model_handler = ModelHandler(model_type=args.model)
        data_loader = DataLoader(dataset=args.dataset, client_id=client_id)
        logger.info(f"Client {client_id} initialized with real model handler and data loader")
    except ImportError:
        # Use mock implementations if real ones are not available
        logger.info(f"Client {client_id} using mock model handler and data loader")
        model_handler = None
        data_loader = None
    
    # Create client
    client = FlowerClient(
        client_id=f"client-{client_id}",
        data_source=args.dataset,
        local_epochs=args.local_epochs,
        batch_size=args.batch_size,
        learning_rate=0.01,
        differential_privacy_enabled=False,  # Enable if needed
        metrics_service=metrics_service,
        model_handler=model_handler,
        data_loader=data_loader
    )
    
    # Start client
    logger.info(f"Starting client {client_id}")
    
    # Create a Flower client from our custom NumPyClient implementation
    fl_client = fl.client.start_numpy_client(
        server_address=server_address,
        client=client
    )
    
    logger.info(f"Client {client_id} completed")
    
def main():
    """Main function to run the federated learning system."""
    # Parse arguments
    args = parse_args()
    
    # Ensure logs directory exists relative to the project root
    os.makedirs("./logs", exist_ok=True)
    
    # Extract server address
    server_address = args.server_address
    
    # Start server if not client_only
    if not args.client_only:
        if args.server_only:
            # Run server in main thread
            start_server(args)
        else:
            # Run server in a separate thread if we're also running clients
            server_thread = threading.Thread(target=start_server, args=(args,))
            server_thread.daemon = True
            server_thread.start()
            
            # Wait for server to start
            logger.info("Waiting for server to start...")
            time.sleep(5)
    
    # Start clients if not server_only
    if not args.server_only:
        client_threads = []
        
        # Start clients
        for i in range(args.clients):
            client_thread = threading.Thread(
                target=start_client,
                args=(i, args, server_address)
            )
            client_threads.append(client_thread)
            client_thread.start()
            
            # Small delay between client starts
            time.sleep(0.5)
        
        # Wait for all clients to complete
        for client_thread in client_threads:
            client_thread.join()
    
    # If we started the server in a thread, wait for it to complete
    if not args.client_only and not args.server_only:
        server_thread.join()
    
    logger.info("Federated learning completed")

if __name__ == "__main__":
    main() 