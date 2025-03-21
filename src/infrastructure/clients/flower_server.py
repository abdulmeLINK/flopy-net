"""
Flower Server Adapter

This module provides an adapter for the Flower federated learning server.
"""
import logging
from typing import Dict, List, Any, Optional
import threading
from datetime import datetime, timedelta

from src.domain.interfaces.fl_server import IFLServer
from src.application.policy.engine import PolicyEngine


class FlowerServer(IFLServer):
    """
    Adapter for the Flower federated learning server.
    
    This class adapts the Flower server to the IFLServer interface,
    providing a consistent API regardless of the underlying implementation.
    """
    
    def __init__(
        self,
        server_address: str = "0.0.0.0:8080",
        num_rounds: int = 3,
        min_clients: int = 2,
        fraction_fit: float = 1.0,
        policy_engine: Optional[PolicyEngine] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Flower server adapter.
        
        Args:
            server_address: Server address (host:port)
            num_rounds: Number of federated learning rounds
            min_clients: Minimum number of clients required
            fraction_fit: Fraction of clients to select for training
            policy_engine: Optional policy engine
            logger: Optional logger
        """
        self.server_address = server_address
        self.num_rounds = num_rounds
        self.min_clients = min_clients
        self.fraction_fit = fraction_fit
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
        
        self.server_thread = None
        self.is_running = False
        self.clients = {}
        self.status = "idle"
        self.config = {}
        
        # Initialize metrics
        self.metrics = {
            "rounds_completed": 0,
            "clients_participated": 0,
            "global_accuracy": 0.0,
            "global_loss": 0.0,
            "start_time": None,
            "estimated_completion": None
        }
    
    def start(self) -> bool:
        """
        Start the server.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("Server is already running")
            return False
        
        try:
            # Create a thread for the server to run in
            self.server_thread = threading.Thread(target=self._run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Set running state
            self.is_running = True
            self.status = "running"
            self.metrics["start_time"] = datetime.now().isoformat()
            self.metrics["estimated_completion"] = (
                datetime.now() + timedelta(minutes=self.num_rounds)
            ).isoformat()
            
            self.logger.info(f"Started server on {self.server_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            self.is_running = False
            self.status = "error"
            return False
    
    def stop(self) -> None:
        """Stop the server."""
        if not self.is_running:
            self.logger.warning("Server is not running")
            return
        
        try:
            self.is_running = False
            self.status = "stopped"
            
            # Server thread should terminate on its own when is_running is False
            self.logger.info("Stopped server")
            
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current server status.
        
        Returns:
            A dictionary containing server status information
        """
        status_info = {
            "status": self.status,
            "address": self.server_address,
            "num_rounds": self.num_rounds,
            "min_clients": self.min_clients,
            "registered_clients": len(self.clients),
            "is_running": self.is_running
        }
        
        # Add metrics
        status_info.update(self.metrics)
        
        return status_info
    
    def register_client(self, client_id: str, client_info: Dict[str, Any]) -> bool:
        """
        Register a client with the server.
        
        Args:
            client_id: Unique identifier for the client
            client_info: Information about the client
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            self.clients[client_id] = {
                "info": client_info,
                "registered_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
            
            self.logger.info(f"Registered client {client_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering client {client_id}: {e}")
            return False
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the server.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configured successfully, False otherwise
        """
        try:
            # Update configuration
            self.config.update(config)
            
            # Update server properties from config
            if "server_address" in config:
                self.server_address = config["server_address"]
            
            if "num_rounds" in config:
                self.num_rounds = config["num_rounds"]
            
            if "min_clients" in config:
                self.min_clients = config["min_clients"]
            
            if "fraction_fit" in config:
                self.fraction_fit = config["fraction_fit"]
            
            self.logger.info("Server configured")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring server: {e}")
            return False
    
    def _run_server(self) -> None:
        """Run the server in a thread."""
        self.logger.info("Server thread started")
        
        try:
            # Simulate server loop
            round_id = 0
            
            while self.is_running and round_id < self.num_rounds:
                # Simulate a round of federated learning
                self.logger.info(f"Starting round {round_id + 1}/{self.num_rounds}")
                
                # Check if we have enough clients
                if len(self.clients) < self.min_clients:
                    self.logger.warning(
                        f"Not enough clients: {len(self.clients)} < {self.min_clients}"
                    )
                    import time
                    time.sleep(5)  # Wait and try again
                    continue
                
                # Select clients for this round
                selected_clients = self._select_clients()
                
                if len(selected_clients) < self.min_clients:
                    self.logger.warning(
                        f"Not enough clients selected: {len(selected_clients)} < {self.min_clients}"
                    )
                    import time
                    time.sleep(5)  # Wait and try again
                    continue
                
                self.logger.info(f"Selected {len(selected_clients)} clients for round {round_id + 1}")
                
                # Simulate client training and aggregation
                self._simulate_round(round_id, selected_clients)
                
                # Update metrics
                self.metrics["rounds_completed"] = round_id + 1
                self.metrics["clients_participated"] += len(selected_clients)
                
                # Random metrics for simulation
                import random
                self.metrics["global_accuracy"] = 0.5 + (0.5 * (round_id + 1) / self.num_rounds) * random.uniform(0.8, 1.0)
                self.metrics["global_loss"] = 1.0 - self.metrics["global_accuracy"]
                
                round_id += 1
                
                # Simulate round time
                import time
                time.sleep(2)
            
            # Training complete
            if round_id >= self.num_rounds:
                self.logger.info("Federated learning complete")
                self.status = "completed"
            
        except Exception as e:
            self.logger.error(f"Error in server thread: {e}")
            self.status = "error"
        
        # Set running status to false
        self.is_running = False
    
    def _select_clients(self) -> List[str]:
        """
        Select clients for the current round.
        
        Returns:
            List of selected client IDs
        """
        available_clients = list(self.clients.keys())
        
        # Use policy engine if available
        if self.policy_engine:
            context = {
                "available_clients": available_clients,
                "client_properties": {
                    client_id: client_data["info"]
                    for client_id, client_data in self.clients.items()
                }
            }
            
            policy_results = self.policy_engine.evaluate_policies(context)
            
            # Look for client selection policy result
            for result in policy_results:
                if result.get("policy_name") == "client_selection":
                    selected_clients = result.get("selected_clients", [])
                    if selected_clients:
                        return selected_clients
        
        # Fallback to random selection
        import random
        num_to_select = max(
            self.min_clients, 
            min(len(available_clients), int(self.fraction_fit * len(available_clients)))
        )
        
        selected_clients = random.sample(
            available_clients, 
            min(num_to_select, len(available_clients))
        )
        
        return selected_clients
    
    def _simulate_round(self, round_id: int, selected_clients: List[str]) -> None:
        """
        Simulate a round of federated learning.
        
        Args:
            round_id: Current round ID
            selected_clients: List of selected client IDs
        """
        self.logger.info(f"Simulating round {round_id + 1} with {len(selected_clients)} clients")
        
        # Update client last_active timestamps
        for client_id in selected_clients:
            if client_id in self.clients:
                self.clients[client_id]["last_active"] = datetime.now().isoformat()
        
        # No actual training happens in this simulation 