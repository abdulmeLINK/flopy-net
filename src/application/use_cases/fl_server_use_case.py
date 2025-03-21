"""
Federated Learning Server Use Case

This module provides use cases for federated learning server operations.
"""
from typing import Dict, List, Any, Optional, Tuple
import logging

from src.domain.interfaces.fl_server import IFLServer
from src.domain.interfaces.fl_model_repository import IFLModelRepository
from src.domain.interfaces.client_repository import IClientRepository
from src.domain.interfaces.aggregation_strategy import IAggregationStrategy
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.entities.fl_model import FLModel
from src.domain.entities.client import Client


class FLServerUseCase:
    """
    Use case for federated learning server operations.
    
    This class orchestrates the interactions between the server,
    repositories, and strategies.
    """
    
    def __init__(self,
                 server: IFLServer,
                 model_repository: IFLModelRepository,
                 client_repository: IClientRepository,
                 aggregation_strategy: IAggregationStrategy,
                 policy_engine: Optional[IPolicyEngine] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the use case.
        
        Args:
            server: Federated learning server implementation
            model_repository: Model repository
            client_repository: Client repository
            aggregation_strategy: Aggregation strategy
            policy_engine: Policy engine for applying policies and strategies
            logger: Optional logger
        """
        self.server = server
        self.model_repository = model_repository
        self.client_repository = client_repository
        self.aggregation_strategy = aggregation_strategy
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
    
    def start_server(self, config: Dict[str, Any]) -> bool:
        """
        Start the server with the given configuration.
        
        Args:
            config: Server configuration
            
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
                        
                # Set active strategy if specified in config
                if 'strategy' in config:
                    strategy_name = config['strategy'].get('name', 'fedavg')
                    strategy_config = config['strategy'].get('config', {})
                    self.policy_engine.set_strategy(strategy_name, strategy_config)
                    self.logger.info(f"Set active strategy to {strategy_name}")
            
            # Load initial model if specified
            if 'model' in config and 'name' in config['model']:
                model_name = config['model']['name']
                self.logger.info(f"Loading initial model: {model_name}")
                initial_model = self.model_repository.get_model(model_name)
                if initial_model:
                    self.server.set_model(initial_model)
                else:
                    self.logger.warning(f"Model {model_name} not found in repository")
            
            # Start the server
            result = self.server.start(config)
            if result:
                self.logger.info("Server started successfully")
            else:
                self.logger.error("Failed to start server")
                
                # Stop policy engine if it was started
                if self.policy_engine and self.policy_engine.get_active_strategy():
                    self.policy_engine.stop()
            
            return result
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            return False
    
    def stop_server(self) -> None:
        """Stop the server."""
        try:
            self.server.stop()
            
            # Stop policy engine if available
            if self.policy_engine:
                self.policy_engine.stop()
                
            self.logger.info("Server stopped")
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
    
    def register_client(self, client: Client) -> bool:
        """
        Register a client with the server.
        
        Args:
            client: Client to register
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            # Check if policy engine is available for client admission
            if self.policy_engine:
                # Create context for policy evaluation
                context = {
                    'client': client.to_dict(),
                    'operation': 'register_client',
                    'registered_clients': len(self.client_repository.get_all_clients())
                }
                
                # Evaluate policies
                policy_results = self.policy_engine.evaluate_policies(context)
                
                # Check if any policy denies registration
                for result in policy_results:
                    action = result.get('action', 'allow')
                    if action == 'deny':
                        self.logger.warning(f"Client {client.client_id} registration denied by policy: {result.get('policy_name')}")
                        return False
                    
                # Apply any modifications from policies
                for result in policy_results:
                    modifications = result.get('modifications', {})
                    if modifications and 'client' in modifications:
                        client_dict = modifications['client']
                        # Update client properties from policy modifications
                        if 'properties' in client_dict:
                            for key, value in client_dict['properties'].items():
                                client.properties[key] = value
            
            # Register client in repository
            result = self.client_repository.add_client(client)
            if result:
                self.logger.info(f"Client {client.client_id} registered successfully")
            else:
                self.logger.warning(f"Failed to register client {client.client_id}")
            
            return result
        except Exception as e:
            self.logger.error(f"Error registering client: {e}")
            return False
    
    def select_clients_for_round(self, round_id: int, num_clients: int) -> List[str]:
        """
        Select clients to participate in a round.
        
        Args:
            round_id: Current round ID
            num_clients: Number of clients to select
            
        Returns:
            List of selected client IDs
        """
        try:
            # Get all available clients
            all_clients = self.client_repository.get_all_clients()
            available_client_ids = [client.client_id for client in all_clients]
            
            if not available_client_ids:
                self.logger.warning("No clients available for selection")
                return []
            
            # Prepare client properties dict for selection
            client_properties = {}
            for client in all_clients:
                client_properties[client.client_id] = client.properties
            
            selected_clients = []
            
            # Use policy engine if available for client selection
            if self.policy_engine:
                # Get the active strategy
                active_strategy = self.policy_engine.get_active_strategy()
                if active_strategy:
                    try:
                        from src.application.fl_strategies.registry import create_strategy
                        
                        # Create strategy instance
                        strategy_config = {'max_clients': num_clients, 'round_id': round_id}
                        strategy = create_strategy(active_strategy, strategy_config)
                        
                        # Use strategy for client selection
                        selected_clients = strategy.client_selection(available_client_ids, client_properties)
                        self.logger.info(f"Selected {len(selected_clients)} clients using {active_strategy} strategy")
                    except Exception as e:
                        self.logger.error(f"Error using strategy for client selection: {e}")
                        # Fall back to policy-based selection
                
                # If strategy didn't select clients or failed, use policy-based selection
                if not selected_clients:
                    # Create context for policy evaluation
                    context = {
                        'round_id': round_id,
                        'available_clients': available_client_ids,
                        'client_properties': client_properties,
                        'max_clients': num_clients
                    }
                    
                    # Evaluate policies
                    policy_results = self.policy_engine.evaluate_policies(context)
                    
                    # Look for client selection policy result
                    for result in policy_results:
                        if result.get('policy_name') == 'client_selection' and 'selected_clients' in result:
                            selected_clients = result['selected_clients']
                            self.logger.info(f"Selected {len(selected_clients)} clients using client_selection policy")
                            break
            
            # If no clients selected yet, use default aggregation strategy
            if not selected_clients:
                # Use the default aggregation strategy as fallback
                selected_clients = self.aggregation_strategy.select_clients(
                    available_client_ids, 
                    client_properties, 
                    min(num_clients, len(available_client_ids))
                )
                self.logger.info(f"Selected {len(selected_clients)} clients using default aggregation strategy")
            
            return selected_clients
        except Exception as e:
            self.logger.error(f"Error selecting clients: {e}")
            return []
    
    def aggregate_results(self, client_results: List[Tuple[List[Any], int, Dict[str, Any]]],
                          model_name: str) -> Optional[FLModel]:
        """
        Aggregate results from multiple clients.
        
        Args:
            client_results: List of (parameters, data_size, metrics) tuples from clients
            model_name: Name of the model to update
            
        Returns:
            Updated model, or None if aggregation failed
        """
        try:
            if not client_results:
                self.logger.warning("No client results to aggregate")
                return None
            
            # Extract parameters and weights
            parameters_list = [r[0] for r in client_results]
            weights = [r[1] for r in client_results]
            
            # Calculate overall metrics
            metrics = self._calculate_metrics(client_results)
            
            # Convert parameters to format expected by aggregation
            model_updates = []
            for params in parameters_list:
                # Convert parameters to dictionary format
                param_dict = {}
                for i, param in enumerate(params):
                    param_dict[f"param_{i}"] = param
                model_updates.append(param_dict)
            
            aggregated_parameters = None
            
            # Use policy engine if available for aggregation
            if self.policy_engine:
                # Get the active strategy
                active_strategy = self.policy_engine.get_active_strategy()
                if active_strategy:
                    try:
                        from src.application.fl_strategies.registry import create_strategy
                        
                        # Create strategy instance
                        strategy_config = {}
                        strategy = create_strategy(active_strategy, strategy_config)
                        
                        # Use strategy for aggregation
                        aggregated_update = strategy.aggregate(model_updates, weights)
                        
                        # Convert back to list format
                        if aggregated_update:
                            aggregated_parameters = []
                            for i in range(len(parameters_list[0])):
                                param_name = f"param_{i}"
                                if param_name in aggregated_update:
                                    aggregated_parameters.append(aggregated_update[param_name])
                            
                            self.logger.info(f"Aggregated parameters using {active_strategy} strategy")
                    except Exception as e:
                        self.logger.error(f"Error using strategy for aggregation: {e}")
                        # Fall back to default aggregation
            
            # If aggregation didn't happen via strategy, use default aggregation
            if aggregated_parameters is None:
                aggregated_parameters = self.aggregation_strategy.aggregate(parameters_list, weights)
                self.logger.info("Aggregated parameters using default aggregation strategy")
                
            # Create updated model
            updated_model = FLModel(
                model_name=model_name,
                parameters=aggregated_parameters,
                metrics=metrics
            )
            
            # Save model to repository
            self.model_repository.save_model(updated_model)
            
            return updated_model
        except Exception as e:
            self.logger.error(f"Error aggregating results: {e}")
            return None
    
    def _calculate_metrics(self, client_results: List[Tuple[List[Any], int, Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Calculate aggregated metrics from client results.
        
        Args:
            client_results: List of (parameters, data_size, metrics) tuples from clients
            
        Returns:
            Aggregated metrics
        """
        try:
            if not client_results:
                return {}
                
            # Extract metrics and weights (data sizes)
            metrics_list = [r[2] for r in client_results]
            weights = [r[1] for r in client_results]
            total_weight = sum(weights)
            
            if total_weight == 0:
                return {}
                
            # Calculate weighted average for each metric
            aggregated_metrics = {}
            
            # Find all unique metric keys
            all_keys = set()
            for metrics in metrics_list:
                all_keys.update(metrics.keys())
                
            # Calculate weighted average for each metric
            for key in all_keys:
                # Only aggregate numerical metrics
                values = [metrics.get(key, 0) for metrics in metrics_list]
                if all(isinstance(v, (int, float)) for v in values):
                    # Calculate weighted average
                    weighted_sum = sum(w * v for w, v in zip(weights, values))
                    aggregated_metrics[key] = weighted_sum / total_weight
            
            return aggregated_metrics
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            return {} 