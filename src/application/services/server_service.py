"""
Server Service

This module handles the federated learning server operations, including model
aggregation, client selection, and training coordination.
"""
import logging
from typing import Dict, Any, List, Optional, Callable

from src.domain.interfaces.fl_server import IFLServer
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.interfaces.model_aggregator import IModelAggregator
from src.domain.interfaces.client_repository import IClientRepository
from src.domain.interfaces.fl_model_repository import IFLModelRepository


class ServerService:
    """
    Server Service coordinates federated learning operations on the server side.
    
    This class is responsible for:
    1. Managing the federated learning server lifecycle
    2. Coordinating model training rounds
    3. Selecting clients using policies
    4. Aggregating client models
    5. Managing model persistence and distribution
    """
    
    def __init__(
        self,
        client_repository: IClientRepository,
        model_repository: IFLModelRepository,
        policy_engine: IPolicyEngine,
        fl_server: Optional[IFLServer] = None,
        model_aggregator: Optional[IModelAggregator] = None,
        config: Dict[str, Any] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Server Service.
        
        Args:
            client_repository: Client repository for storing client information
            model_repository: Model repository for storing models
            policy_engine: Policy engine for client selection
            fl_server: Federated learning server implementation (optional)
            model_aggregator: Model aggregation strategy (optional)
            config: Configuration dictionary
            logger: Logger instance
        """
        self.client_repository = client_repository
        self.model_repository = model_repository
        self.policy_engine = policy_engine
        self.fl_server = fl_server
        self.model_aggregator = model_aggregator
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.callbacks = {}
        
        # Register callbacks if fl_server is provided
        if self.fl_server:
            self.fl_server.register_callback("round_completed", self._on_round_completed)
            self.fl_server.register_callback("client_connected", self._on_client_connected)
            self.fl_server.register_callback("client_update_received", self._on_client_update_received)
        
        self.logger.info("Server Service initialized")
    
    def start(self) -> bool:
        """
        Start the federated learning server.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Initialize policy engine
            if not self.policy_engine.is_running():
                self.policy_engine.start()
                
                # Register client selection policy
                self.policy_engine.register_policy("client_selection")
                self.logger.info("Registered client selection policy")
            
            # Start FL server if available
            if self.fl_server:
                return self.fl_server.start()
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error starting Server Service: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the federated learning server.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            # Stop policy engine
            if self.policy_engine.is_running():
                self.policy_engine.stop()
            
            # Stop FL server if available
            if self.fl_server:
                return self.fl_server.stop()
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error stopping Server Service: {e}")
            return False
    
    def start_training(self, training_config: Dict[str, Any] = None) -> bool:
        """
        Start federated learning training.
        
        Args:
            training_config: Training configuration dictionary
            
        Returns:
            True if training started successfully, False otherwise
        """
        try:
            # Use provided config or default
            config = training_config or self.config.get("training", {})
            
            # Start training
            if self.fl_server.start_training(config):
                self.logger.info("Started federated learning training")
                self._trigger_callback("training_started", {"config": config})
                return True
            else:
                self.logger.error("Failed to start training")
                return False
        
        except Exception as e:
            self.logger.error(f"Error starting training: {e}")
            return False
    
    def stop_training(self) -> bool:
        """
        Stop federated learning training.
        
        Returns:
            True if training stopped successfully, False otherwise
        """
        try:
            if self.fl_server.stop_training():
                self.logger.info("Stopped federated learning training")
                self._trigger_callback("training_stopped", {})
                return True
            else:
                self.logger.error("Failed to stop training")
                return False
        
        except Exception as e:
            self.logger.error(f"Error stopping training: {e}")
            return False
    
    def select_clients(self, client_pool: List[Dict[str, Any]], count: int) -> List[str]:
        """
        Select clients for training using policies.
        
        Args:
            client_pool: List of available clients
            count: Number of clients to select
            
        Returns:
            List of selected client IDs
        """
        # Create context for policy evaluation
        context = {
            "available_clients": client_pool,
            "client_count": count,
            "current_round": self.fl_server.get_current_round(),
            "max_rounds": self.fl_server.get_max_rounds(),
            "model_metrics": self.fl_server.get_model_metrics()
        }
        
        # Evaluate client selection policy
        results = self.policy_engine.evaluate_policies(context)
        
        # Find client selection policy result
        for result in results:
            if result.get("policy_name") == "client_selection":
                selected_clients = result.get("selected_clients", [])
                self.logger.info(f"Selected {len(selected_clients)} clients for training")
                return selected_clients
        
        # Fallback: simple random selection
        import random
        client_ids = [client["id"] for client in client_pool]
        selected_ids = random.sample(client_ids, min(count, len(client_ids)))
        self.logger.info(f"Selected {len(selected_ids)} clients using fallback method")
        return selected_ids
    
    def aggregate_models(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate client models using the model aggregator.
        
        Args:
            client_updates: List of client model updates
            
        Returns:
            Aggregated model
        """
        try:
            # Get current global model
            global_model = self.fl_server.get_global_model()
            
            # Perform aggregation
            aggregated_model = self.model_aggregator.aggregate(
                global_model,
                client_updates
            )
            
            self.logger.info(f"Aggregated {len(client_updates)} client models")
            return aggregated_model
        
        except Exception as e:
            self.logger.error(f"Error aggregating models: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get server status information.
        
        Returns:
            Dictionary containing server status
        """
        status = self.fl_server.get_status()
        status["policy_engine_status"] = self.policy_engine.get_status()
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get server metrics.
        
        Returns:
            Dictionary containing server metrics
        """
        return self.fl_server.get_metrics()
    
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
                    self.logger.error(f"Error in server callback: {e}")
    
    def _on_round_completed(self, event_data: Dict[str, Any]) -> None:
        """
        Handle round completed event from FL server.
        
        Args:
            event_data: Event data
        """
        self.logger.info(f"Round {event_data.get('round', 0)}/{event_data.get('max_rounds', 0)} completed")
        
        # Trigger our own event
        self._trigger_callback("round_completed", event_data)
    
    def _on_client_connected(self, event_data: Dict[str, Any]) -> None:
        """
        Handle client connected event from FL server.
        
        Args:
            event_data: Event data
        """
        client_id = event_data.get("client_id", "unknown")
        self.logger.info(f"Client connected: {client_id}")
        
        # Trigger our own event
        self._trigger_callback("client_connected", event_data)
    
    def _on_client_update_received(self, event_data: Dict[str, Any]) -> None:
        """
        Handle client update received event from FL server.
        
        Args:
            event_data: Event data
        """
        client_id = event_data.get("client_id", "unknown")
        round_num = event_data.get("round", 0)
        metrics = event_data.get("metrics", {})
        
        self.logger.info(f"Update received from client {client_id} for round {round_num}")
        
        # Trigger our own event
        self._trigger_callback("client_update_received", event_data) 