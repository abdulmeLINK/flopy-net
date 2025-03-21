"""
Client Service

This module provides services for federated learning client operations.
"""
from typing import Dict, List, Any, Optional
import logging

from src.domain.interfaces.fl_client import IFLClient
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.entities.fl_model import FLModel


class ClientService:
    """
    Client Service for federated learning operations.
    
    This class orchestrates the interactions between the client,
    local data, and training processes.
    """
    
    def __init__(self,
                 client: IFLClient,
                 policy_engine: Optional[IPolicyEngine] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the client service.
        
        Args:
            client: Federated learning client implementation
            policy_engine: Policy engine for enforcing data and resource policies
            logger: Logger instance
        """
        self.client = client
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
        
        # Set up runtime policy rules
        if self.policy_engine:
            self._add_data_privacy_runtime_rules()
            self._add_resource_optimization_runtime_rules()
    
    def start_client(self, config: Dict[str, Any]) -> bool:
        """
        Start the federated learning client.
        
        Args:
            config: Client configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Starting federated learning client")
            
            # Initialize client with configuration
            if not self.client.initialize(config):
                self.logger.error("Failed to initialize client")
                return False
            
            # If policy engine is available, start it
            if self.policy_engine and not self.policy_engine.is_running():
                self.policy_engine.start()
                self.logger.info("Policy engine started")
            
            # Start client
            if not self.client.start():
                self.logger.error("Failed to start client")
                return False
            
            self.logger.info("Federated learning client started successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error starting client: {e}")
            return False
    
    def stop_client(self) -> None:
        """Stop the federated learning client."""
        try:
            # Stop client and policy engine
            self.client.stop()
            
            if self.policy_engine and self.policy_engine.is_running():
                self.policy_engine.stop()
                self.logger.info("Policy engine stopped")
            
            self.logger.info("Federated learning client stopped")
        
        except Exception as e:
            self.logger.error(f"Error stopping client: {e}")
    
    def register_with_server(self, server_url: str, client_id: str, properties: Dict[str, Any] = None) -> bool:
        """
        Register the client with the federated learning server.
        
        Args:
            server_url: URL of the federated learning server
            client_id: Unique identifier for this client
            properties: Client properties to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            self.logger.info(f"Registering client {client_id} with server at {server_url}")
            
            # Check if policy engine allows registration
            if self.policy_engine:
                registration_context = {
                    "client_id": client_id,
                    "server_url": server_url,
                    "properties": properties or {}
                }
                
                if not self.policy_engine.evaluate_policy("registration", registration_context):
                    self.logger.warning("Client registration blocked by policy")
                    return False
            
            # Register with server
            if not self.client.register(server_url, client_id, properties or {}):
                self.logger.error("Failed to register with server")
                return False
            
            self.logger.info(f"Client {client_id} registered successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error during registration: {e}")
            return False
    
    def train(self, model: FLModel, config: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Train the model with local data.
        
        Args:
            model: Federated learning model
            config: Training configuration
            
        Returns:
            Dictionary with training results and model update, or None if training failed
        """
        try:
            # Check policies for training
            if self.policy_engine:
                training_context = {
                    "model": {
                        "size": model.get_size(),
                        "type": model.get_type()
                    },
                    "config": config or {},
                    "client_resources": self.client.get_resources()
                }
                
                policy_result = self.policy_engine.evaluate_policy("training", training_context)
                
                if not policy_result.get("allowed", True):
                    self.logger.warning("Training blocked by policy")
                    return None
                
                # Get modified training configuration from policy
                modified_config = policy_result.get("modified_config")
                if modified_config:
                    self.logger.info("Training configuration modified by policy")
                    config = modified_config
            
            # Perform model training
            self.logger.info("Starting model training")
            training_result = self.client.train(model, config or {})
            
            if not training_result:
                self.logger.error("Training failed")
                return None
            
            self.logger.info("Training completed successfully")
            return training_result
        
        except Exception as e:
            self.logger.error(f"Error during training: {e}")
            return None
    
    def evaluate(self, model: FLModel) -> Optional[Dict[str, Any]]:
        """
        Evaluate the model with local validation data.
        
        Args:
            model: Federated learning model
            
        Returns:
            Dictionary with evaluation metrics, or None if evaluation failed
        """
        try:
            self.logger.info("Starting model evaluation")
            evaluation_result = self.client.evaluate(model)
            
            if not evaluation_result:
                self.logger.error("Evaluation failed")
                return None
            
            self.logger.info("Evaluation completed successfully")
            return evaluation_result
        
        except Exception as e:
            self.logger.error(f"Error during evaluation: {e}")
            return None
    
    def _add_data_privacy_runtime_rules(self) -> None:
        """Add runtime rules for data privacy."""
        if not self.policy_engine:
            return
        
        def min_batch_size_condition(context: Dict[str, Any]) -> bool:
            """Check if batch size is below minimum threshold."""
            return context.get("config", {}).get("batch_size", 0) < 8
        
        def min_batch_size_action(context: Dict[str, Any]) -> Dict[str, Any]:
            """Increase batch size to safe minimum."""
            modified_config = context.get("config", {}).copy()
            modified_config["batch_size"] = 8
            self.logger.warning("Increased batch size to 8 for privacy protection")
            return {"allowed": True, "modified_config": modified_config}
        
        # Register runtime rules
        self.policy_engine.add_rule("training", min_batch_size_condition, min_batch_size_action)
    
    def _add_resource_optimization_runtime_rules(self) -> None:
        """Add runtime rules for resource optimization."""
        if not self.policy_engine:
            return
        
        def low_battery_condition(context: Dict[str, Any]) -> bool:
            """Check if device has low battery."""
            return context.get("client_resources", {}).get("battery_level", 100) < 20
        
        def low_battery_action(context: Dict[str, Any]) -> Dict[str, Any]:
            """Reduce training epochs for low battery."""
            modified_config = context.get("config", {}).copy()
            modified_config["epochs"] = min(modified_config.get("epochs", 1), 1)
            self.logger.warning("Reduced training epochs due to low battery")
            return {"allowed": True, "modified_config": modified_config}
        
        def large_model_condition(context: Dict[str, Any]) -> bool:
            """Check if model is too large for device."""
            return context.get("model", {}).get("size", 0) > context.get("client_resources", {}).get("available_memory", float("inf"))
        
        def large_model_action(context: Dict[str, Any]) -> Dict[str, Any]:
            """Block training for too large models."""
            self.logger.warning("Model too large for device resources, training blocked")
            return {"allowed": False}
        
        # Register runtime rules
        self.policy_engine.add_rule("training", low_battery_condition, low_battery_action)
        self.policy_engine.add_rule("training", large_model_condition, large_model_action) 