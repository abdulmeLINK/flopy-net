"""
Federated Learning Client Use Case

This module provides use cases for federated learning client operations.
"""
from typing import Dict, List, Any, Optional
import logging

from src.domain.interfaces.fl_client import IFLClient
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.entities.fl_model import FLModel


class FLClientUseCase:
    """
    Use case for federated learning client operations.
    
    This class orchestrates the interactions between the client,
    local data, and training processes.
    """
    
    def __init__(self,
                 client: IFLClient,
                 policy_engine: Optional[IPolicyEngine] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the use case.
        
        Args:
            client: Federated learning client implementation
            policy_engine: Policy engine for applying policies
            logger: Optional logger
        """
        self.client = client
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
    
    def start_client(self, config: Dict[str, Any]) -> bool:
        """
        Start the client with the given configuration.
        
        Args:
            config: Client configuration
            
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Start policy engine if available
            if self.policy_engine:
                self.policy_engine.start()
                
                # Register default policies if specified in config
                if 'policies' in config:
                    for policy_name, policy_config in config['policies'].items():
                        self.policy_engine.register_policy(policy_name, policy_config)
                
                # Add data privacy runtime rules
                self._add_data_privacy_runtime_rules()
                
                # Add resource optimization runtime rules
                self._add_resource_optimization_runtime_rules()
            
            # Start the client
            result = self.client.start(config)
            if result:
                self.logger.info("Client started successfully")
            else:
                self.logger.error("Failed to start client")
                
                # Stop policy engine if it was started
                if self.policy_engine:
                    self.policy_engine.stop()
            
            return result
        except Exception as e:
            self.logger.error(f"Error starting client: {e}")
            return False
    
    def stop_client(self) -> None:
        """Stop the client."""
        try:
            self.client.stop()
            
            # Stop policy engine if available
            if self.policy_engine:
                self.policy_engine.stop()
                
            self.logger.info("Client stopped")
        except Exception as e:
            self.logger.error(f"Error stopping client: {e}")
    
    def register_with_server(self, server_url: str, client_id: str, properties: Dict[str, Any] = None) -> bool:
        """
        Register the client with a federated learning server.
        
        Args:
            server_url: URL of the server
            client_id: Client ID
            properties: Client properties
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            # Apply runtime rules to client properties if policy engine is available
            modified_properties = properties or {}
            
            if self.policy_engine:
                context = {
                    'operation': 'register_with_server',
                    'client_id': client_id,
                    'server_url': server_url,
                    'properties': modified_properties
                }
                
                # Apply runtime rules
                modified_context = self.policy_engine.enforce_runtime_rules(context)
                
                # Extract possibly modified properties
                if 'properties' in modified_context:
                    modified_properties = modified_context['properties']
            
            # Register with server
            result = self.client.register(server_url, client_id, modified_properties)
            
            if result:
                self.logger.info(f"Registered with server at {server_url} with ID {client_id}")
            else:
                self.logger.warning(f"Failed to register with server at {server_url}")
            
            return result
        except Exception as e:
            self.logger.error(f"Error registering with server: {e}")
            return False
    
    def train(self, model: FLModel, config: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Train a model on local data.
        
        Args:
            model: Model to train
            config: Training configuration
            
        Returns:
            Training result including updated parameters and metrics
        """
        try:
            training_config = config or {}
            
            # Apply policies and runtime rules if policy engine is available
            if self.policy_engine:
                # Create context for policy evaluation
                context = {
                    'operation': 'train',
                    'batch_size': training_config.get('batch_size', 32),
                    'epochs': training_config.get('epochs', 1),
                    'learning_rate': training_config.get('learning_rate', 0.01),
                    'model_size_mb': model.get_size_mb(),
                    'data_size': self.client.get_data_size(),
                    'battery_level': self.client.get_battery_level() if hasattr(self.client, 'get_battery_level') else 100
                }
                
                # Evaluate policies
                policy_results = self.policy_engine.evaluate_policies(context)
                
                # Apply modifications from policies
                for result in policy_results:
                    modifications = result.get('modifications', {})
                    for key, value in modifications.items():
                        if key in training_config:
                            training_config[key] = value
                
                # Apply runtime rules
                modified_context = self.policy_engine.enforce_runtime_rules(context)
                
                # Update training config with modified values
                for key in ['batch_size', 'epochs', 'learning_rate']:
                    if key in modified_context and key in training_config:
                        training_config[key] = modified_context[key]
            
            # Train the model
            result = self.client.train(model.parameters, training_config)
            
            if result:
                self.logger.info("Model training completed successfully")
                return result
            else:
                self.logger.warning("Model training failed")
                return None
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            return None
    
    def evaluate(self, model: FLModel) -> Optional[Dict[str, Any]]:
        """
        Evaluate a model on local data.
        
        Args:
            model: Model to evaluate
            
        Returns:
            Evaluation metrics
        """
        try:
            # Evaluate the model
            metrics = self.client.evaluate(model.parameters)
            
            if metrics:
                self.logger.info("Model evaluation completed successfully")
                return metrics
            else:
                self.logger.warning("Model evaluation failed")
                return None
        except Exception as e:
            self.logger.error(f"Error evaluating model: {e}")
            return None
    
    def _add_data_privacy_runtime_rules(self) -> None:
        """Add data privacy runtime rules to the policy engine."""
        if not self.policy_engine:
            return
        
        # Minimum batch size rule
        def min_batch_size_condition(context: Dict[str, Any]) -> bool:
            return (
                context.get('operation') == 'train' and
                context.get('batch_size', 0) < 16
            )
        
        def min_batch_size_action(context: Dict[str, Any]) -> Dict[str, Any]:
            modified_context = context.copy()
            modified_context['batch_size'] = 16
            self.logger.info("Applied min_batch_size rule: increased batch size to 16")
            return modified_context
        
        self.policy_engine.add_runtime_rule(
            "min_batch_size", min_batch_size_condition, min_batch_size_action)
        
        self.logger.debug("Added data privacy runtime rules")
    
    def _add_resource_optimization_runtime_rules(self) -> None:
        """Add resource optimization runtime rules to the policy engine."""
        if not self.policy_engine:
            return
        
        # Low battery rule
        def low_battery_condition(context: Dict[str, Any]) -> bool:
            return (
                context.get('operation') == 'train' and
                context.get('battery_level', 100) < 15
            )
        
        def low_battery_action(context: Dict[str, Any]) -> Dict[str, Any]:
            modified_context = context.copy()
            modified_context['epochs'] = 1
            modified_context['low_power_mode'] = True
            self.logger.info("Applied low_battery rule: reduced epochs to 1 and enabled low power mode")
            return modified_context
        
        self.policy_engine.add_runtime_rule(
            "low_battery", low_battery_condition, low_battery_action)
        
        # Large model rule
        def large_model_condition(context: Dict[str, Any]) -> bool:
            return (
                context.get('operation') == 'train' and
                context.get('model_size_mb', 0) > 50
            )
        
        def large_model_action(context: Dict[str, Any]) -> Dict[str, Any]:
            modified_context = context.copy()
            modified_context['learning_rate'] = context.get('learning_rate', 0.01) * 0.5
            self.logger.info("Applied large_model rule: reduced learning rate by 50%")
            return modified_context
        
        self.policy_engine.add_runtime_rule(
            "large_model", large_model_condition, large_model_action)
        
        self.logger.debug("Added resource optimization runtime rules") 