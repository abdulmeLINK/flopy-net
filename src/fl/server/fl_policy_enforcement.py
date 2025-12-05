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
Policy Enforcement Mixin for FL Server.

This module provides policy checking and enforcement methods for the FL server,
including client filtering, model size calculation, and client evaluation.
"""

import time
import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.fl.server.protocols import PolicyEnforcementHost

logger = logging.getLogger(__name__)


class PolicyEnforcementMixin:
    """
    Mixin class providing policy enforcement methods for FL server.
    
    This mixin expects the host class to implement PolicyEnforcementHost protocol:
    - config: Dict[str, Any]
    - policy_client: PolicyClientProtocol instance
    - strict_policy_mode: bool
    - model: str (model name)
    - dataset: str (dataset name)
    - rounds: int
    
    See src/fl/server/protocols.py for the formal protocol definition.
    """
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if the action is allowed by the policy engine.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with policy decision and metadata
        """
        from src.fl.server.fl_server import global_metrics, metrics_lock
        
        # Track metrics
        with metrics_lock:
            global_metrics["policy_checks_performed"] += 1
        
        try:
            result = self.policy_client.check_policy(policy_type, context)
            
            # Track allowed/denied metrics
            if result.get('allowed'):
                with metrics_lock:
                    global_metrics["policy_checks_allowed"] += 1
            else:
                with metrics_lock:
                    global_metrics["policy_checks_denied"] += 1
            
            return result
            
        except Exception as e:
            with metrics_lock:
                global_metrics["policy_checks_denied"] += 1
            raise
    
    def verify_policy_result(self, result: Dict[str, Any]) -> bool:
        """
        Verify that a policy result is valid and hasn't been tampered with.
        
        Args:
            result: Policy check result including signature
            
        Returns:
            True if valid, False otherwise
        """
        return self.policy_client.verify_result(result)
    
    def calculate_model_size(self, parameters) -> int:
        """
        Calculate the model size in bytes.
        
        Args:
            parameters: Model parameters
            
        Returns:
            Model size in bytes
        """
        if not parameters:
            logger.warning("Model size calculation: parameters is None or empty")
            return self._get_fallback_model_size()
            
        import numpy as np
        from flwr.common import parameters_to_ndarrays
        
        try:
            # If parameters is a Parameters object, convert it to a list of NumPy arrays
            if hasattr(parameters, 'tensors'):
                param_arrays = parameters_to_ndarrays(parameters)
                logger.debug(f"Model size calculation: Converted Parameters object to {len(param_arrays)} arrays")
            else:
                param_arrays = parameters
                logger.debug(f"Model size calculation: Using parameters directly as arrays")
                
            total_bytes = sum(param.nbytes for param in param_arrays)
            
            # If calculated size is 0, use fallback
            if total_bytes == 0:
                logger.warning("Model size calculation resulted in 0 bytes, using fallback")
                total_bytes = self._get_fallback_model_size()
            
            total_mb = total_bytes / (1024 * 1024)
            logger.info(f"Model size calculation: {total_bytes} bytes = {total_mb:.3f} MB")
            return total_bytes
        except Exception as e:
            logger.error(f"Error calculating model size: {e}")
            return self._get_fallback_model_size()
    
    def _get_fallback_model_size(self) -> int:
        """
        Get a realistic fallback model size based on common FL models.
        
        Returns:
            Model size in bytes
        """
        model_type = getattr(self, 'model', 'cnn')
        dataset = getattr(self, 'dataset', 'mnist')
        
        # Calculate realistic model sizes for common FL models
        if model_type.lower() in ['cnn', 'simple_cnn']:
            total_params = 454890
        elif model_type.lower() in ['mlp', 'simple_mlp']:
            total_params = 109386
        else:
            total_params = 250000
        
        # Convert to bytes (float32 = 4 bytes per parameter)
        size_bytes = total_params * 4
        
        logger.info(f"Using fallback model size: {total_params:,} parameters = {size_bytes / (1024 * 1024):.3f} MB")
        return size_bytes
    
    def client_filter(self, client_properties: Dict[str, Any]) -> bool:
        """
        Filter clients based on policy rules.
        This function is used by Flower to determine which clients can join.
        
        Args:
            client_properties: Properties of the client
            
        Returns:
            True if client should be allowed to join, False otherwise
        """
        try:
            logger.info(f"Checking client properties for filtering: {client_properties}")
            
            # Check policy
            policy_context = {
                "operation": "client_filter",
                "server_id": self.config.get("server_id", "default-server"),
                "client_id": client_properties.get("client_id", "unknown"),
                "client_ip": client_properties.get("client_ip", "unknown"),
                "model": client_properties.get("model", "unknown"),
                "dataset": client_properties.get("dataset", "unknown"),
                "properties": client_properties,
                "timestamp": time.time()
            }
            
            policy_result = self.check_policy("fl_server_client_filter", policy_context)
            
            # Verify policy result
            if not self.verify_policy_result(policy_result):
                logger.error("Policy verification failed for client filter")
                if self.strict_policy_mode:
                    return False
            
            # If not allowed, reject the client
            if not policy_result.get("allowed", True):
                logger.warning(f"Policy violation for client: {policy_result.get('reason', 'Unknown reason')}")
                if "violations" in policy_result:
                    for violation in policy_result["violations"]:
                        logger.warning(f"Violation: {violation}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in client filter: {e}")
            
            # In strict mode, reject client if error occurs
            if self.strict_policy_mode:
                return False
            
            return True
    
    def evaluate_clients(self, clients_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate clients results and check policies before aggregation.
        
        Args:
            clients_results: Results from clients
            
        Returns:
            Filtered client results
        """
        try:
            filtered_results = {}
            
            for client_id, result in clients_results.items():
                # Extract model parameters and metrics
                parameters = result.get("parameters", None)
                metrics = result.get("metrics", {})
                
                # Calculate model size
                model_size = self.calculate_model_size(parameters)
                
                # Check policy
                policy_context = {
                    "operation": "evaluate_client",
                    "server_id": self.config.get("server_id", "default-server"),
                    "client_id": client_id,
                    "model_size": int(model_size),
                    "metrics": metrics,
                    "server_rounds": int(self.rounds),
                    "total_rounds": int(self.rounds),
                    "timestamp": time.time()
                }
                
                policy_result = self.check_policy("fl_server_aggregation", policy_context)
                
                # Verify policy result
                if not self.verify_policy_result(policy_result):
                    logger.error(f"Policy verification failed for client {client_id}")
                    if self.strict_policy_mode:
                        continue
                
                # If not allowed, skip this client
                if not policy_result.get("allowed", True):
                    logger.warning(f"Policy violation for client {client_id}: {policy_result.get('reason', 'Unknown reason')}")
                    continue
                
                # Add to filtered results
                filtered_results[client_id] = result
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error evaluating clients: {e}")
            
            # In strict mode, return empty results if error occurs
            if self.strict_policy_mode:
                return {}
            
            return clients_results
