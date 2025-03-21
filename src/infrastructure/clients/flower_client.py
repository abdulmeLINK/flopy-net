"""
Flower Client Adapter

This module provides an adapter for the Flower federated learning client.
"""
import logging
import threading
import time
import random
from typing import Dict, List, Any, Tuple, Optional
import numpy as np

from src.domain.interfaces.fl_client import IFLClient


class FlowerClient(IFLClient):
    """
    Adapter for the Flower federated learning client.
    
    This class adapts the Flower client to the IFLClient interface,
    providing a consistent API regardless of the underlying implementation.
    """
    
    def __init__(
        self,
        client_id: str,
        server_address: str = "localhost:8080",
        data_size: int = 1000,
        compute_power: float = 1.0,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Flower client adapter.
        
        Args:
            client_id: Unique identifier for this client
            server_address: Server address (host:port)
            data_size: Size of the client's local dataset
            compute_power: Relative compute power (affects training time)
            logger: Optional logger
        """
        self.client_id = client_id
        self.server_address = server_address
        self.data_size = data_size
        self.compute_power = compute_power
        self.logger = logger or logging.getLogger(__name__)
        
        self.client_thread = None
        self.is_running = False
        self.local_parameters = None
        self.local_metrics = {
            "accuracy": 0.0,
            "loss": 0.0,
            "training_time": 0.0
        }
    
    def get_parameters(self, config: Dict[str, Any]) -> List[Any]:
        """
        Get the current model parameters.
        
        Args:
            config: A dictionary containing configuration parameters
            
        Returns:
            A list of model parameters
        """
        if self.local_parameters is None:
            # Initialize with random parameters for simulation
            self.local_parameters = [
                np.random.random((10, 10)) for _ in range(3)
            ]
        
        return self.local_parameters
    
    def set_parameters(self, parameters: List[Any]) -> None:
        """
        Set the model parameters.
        
        Args:
            parameters: A list of model parameters
        """
        self.local_parameters = parameters
    
    def fit(self, parameters: List[Any], config: Dict[str, Any]) -> Tuple[List[Any], int, Dict[str, Any]]:
        """
        Train the model on the client's local data.
        
        Args:
            parameters: Initial model parameters
            config: Training configuration
            
        Returns:
            Tuple containing (updated parameters, number of samples, metrics)
        """
        self.logger.info(f"Client {self.client_id} starting training")
        
        # Set parameters
        self.set_parameters(parameters)
        
        # Simulate training time based on compute power
        training_time = 1.0 / self.compute_power
        time.sleep(training_time)
        
        # Simulate parameter updates
        updated_parameters = []
        for param in parameters:
            # Add small random perturbation
            updated_param = param + np.random.normal(0, 0.01, param.shape)
            updated_parameters.append(updated_param)
        
        # Simulate metrics
        accuracy = random.uniform(0.6, 0.95)
        loss = 1.0 - accuracy
        
        metrics = {
            "accuracy": accuracy,
            "loss": loss,
            "training_time": training_time
        }
        
        # Update local state
        self.local_parameters = updated_parameters
        self.local_metrics = metrics
        
        self.logger.info(
            f"Client {self.client_id} completed training with "
            f"accuracy={accuracy:.4f}, loss={loss:.4f}"
        )
        
        return updated_parameters, self.data_size, metrics
    
    def evaluate(self, parameters: List[Any], config: Dict[str, Any]) -> Tuple[float, int, Dict[str, Any]]:
        """
        Evaluate the model on the client's local data.
        
        Args:
            parameters: Model parameters to evaluate
            config: Evaluation configuration
            
        Returns:
            Tuple containing (loss, number of samples, metrics)
        """
        self.logger.info(f"Client {self.client_id} starting evaluation")
        
        # Set parameters
        self.set_parameters(parameters)
        
        # Simulate evaluation time
        eval_time = 0.5 / self.compute_power
        time.sleep(eval_time)
        
        # Simulate metrics
        accuracy = random.uniform(0.7, 0.95)
        loss = 1.0 - accuracy
        
        metrics = {
            "accuracy": accuracy,
            "loss": loss,
            "evaluation_time": eval_time
        }
        
        self.logger.info(
            f"Client {self.client_id} completed evaluation with "
            f"accuracy={accuracy:.4f}, loss={loss:.4f}"
        )
        
        return loss, self.data_size, metrics
    
    def start(self) -> bool:
        """
        Start the client.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("Client is already running")
            return False
        
        try:
            # Create a thread for the client to run in
            self.client_thread = threading.Thread(target=self._run_client)
            self.client_thread.daemon = True
            self.client_thread.start()
            
            # Set running state
            self.is_running = True
            
            self.logger.info(f"Started client {self.client_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start client {self.client_id}: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the client."""
        if not self.is_running:
            self.logger.warning("Client is not running")
            return
        
        try:
            self.is_running = False
            
            # Client thread should terminate on its own when is_running is False
            self.logger.info(f"Stopped client {self.client_id}")
            
        except Exception as e:
            self.logger.error(f"Error stopping client {self.client_id}: {e}")
    
    def _run_client(self) -> None:
        """Run the client in a thread."""
        self.logger.info(f"Client {self.client_id} thread started")
        
        try:
            while self.is_running:
                # Simulate client activity - in a real implementation,
                # this would handle communication with the server
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in client {self.client_id} thread: {e}")
        
        # Set running status to false
        self.is_running = False 