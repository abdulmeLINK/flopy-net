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
MetricsTrackingStrategy - Custom Flower FedAvg strategy with metrics tracking and policy integration.

This module provides a custom FL strategy that:
- Tracks detailed round metrics (timing, accuracy, loss)
- Integrates with the policy engine for training control
- Supports pause/resume based on policy decisions
- Persists round data to storage
"""

import logging
import time
import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

import flwr as fl
from flwr.server.strategy import FedAvg
from flwr.common import Parameters

logger = logging.getLogger(__name__)


class StopTrainingPolicySignal(Exception):
    """Signal exception to stop training based on policy."""
    pass


class MetricsTrackingStrategy(FedAvg):
    """Custom strategy that tracks detailed metrics and integrates with policy engine.
    
    This strategy extends FedAvg to provide:
    - Per-round timing metrics (configuration, aggregation, evaluation)
    - Client training/evaluation duration tracking
    - Policy checks before each round
    - Automatic pause/resume based on policy decisions
    - Persistent storage of round data
    
    Attributes:
        server_instance: Reference to the FLServer instance for callbacks
        round_start_time: Timestamp when current round started
        aggregation_start_time: Timestamp when aggregation phase started
        evaluation_start_time: Timestamp when evaluation phase started
    """
    
    def __init__(self, *args, server_instance=None, global_metrics=None, 
                 metrics_lock=None, fl_round_storage=None, **kwargs):
        """Initialize the metrics tracking strategy.
        
        Args:
            *args: Arguments passed to FedAvg
            server_instance: Reference to the FLServer instance
            global_metrics: Shared metrics dictionary (from fl_server module)
            metrics_lock: Threading lock for metrics access
            fl_round_storage: FLRoundStorage instance for persistence
            **kwargs: Keyword arguments passed to FedAvg
        """
        super().__init__(*args, **kwargs)
        self.server_instance = server_instance
        self.round_start_time = None
        self.aggregation_start_time = None
        self.evaluation_start_time = None
        
        # Store references to shared state
        self._global_metrics = global_metrics
        self._metrics_lock = metrics_lock
        self._fl_round_storage = fl_round_storage

    def configure_fit(self, server_round: int, parameters: Parameters, 
                      client_manager: fl.server.client_manager.ClientManager
                      ) -> List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitIns]]:
        """Configure the fit round with policy checks.
        
        Args:
            server_round: Current round number
            parameters: Current model parameters
            client_manager: Flower client manager
            
        Returns:
            List of client-configuration tuples for training
            
        Raises:
            StopTrainingPolicySignal: If training should be stopped by policy
        """
        if self.server_instance:
            # Check if training was stopped by policy in previous round
            with self._metrics_lock:
                if self._global_metrics.get("training_stopped_by_policy", False):
                    reason = self._global_metrics.get("stop_reason", "Training stopped by policy")
                    logger.warning(f"Training was stopped by policy, terminating at round {server_round}")
                    raise StopTrainingPolicySignal(f"Training stopped by policy: {reason}")
            
            # Wait if training is currently paused
            self.server_instance.wait_if_paused(f"Round {server_round} configuration")
            
            # CRITICAL: Check client training policy IMMEDIATELY before allowing round to start
            # Get fresh time information for each round to handle dynamic time-based policies
            current_time = time.localtime()
            training_policy_context = {
                "operation": "model_training",
                "server_id": self.server_instance.config.get("server_id", "default-server"),
                "current_round": int(server_round),
                "server_round": int(server_round),
                "model": self.server_instance.model_name,
                "dataset": self.server_instance.dataset,
                "available_clients": int(client_manager.num_available()),
                "timestamp": time.time(),
                # Dynamic time evaluation - get fresh current hour for each round
                "current_hour": int(current_time.tm_hour),
                "current_minute": int(current_time.tm_min),
                "current_day_of_week": int(current_time.tm_wday),  # 0 = Monday
                "current_timestamp": time.time()
            }
            
            # Check fl_client_training policy BEFORE allowing any training
            while True:
                client_training_policy_result = self.server_instance.check_policy(
                    "fl_client_training", training_policy_context)
                if client_training_policy_result.get("allowed", True):
                    logger.info(f"Policy allows round {server_round} to proceed")
                    break
                else:
                    reason = client_training_policy_result.get("reason", "Client training denied by policy")
                    logger.warning(f"Round {server_round} PAUSED: {reason}")
                    
                    # Log policy denial
                    self.server_instance._log_event("TRAINING_PAUSED_BY_POLICY", {
                        "round": server_round,
                        "reason": reason,
                        "policy_type": "fl_client_training",
                        "policy_result": client_training_policy_result,
                        "current_hour": training_policy_context["current_hour"],
                        "timestamp": time.time()
                    })
                    
                    # Pause training instead of stopping
                    self.server_instance.pause_training(f"Round {server_round}: {reason}")
                    
                    # Wait and re-check policy
                    logger.info(f"Waiting for policy to allow round {server_round}...")
                    time.sleep(10)  # Check every 10 seconds
                    
                    # Update time context for re-check
                    current_time = time.localtime()
                    training_policy_context.update({
                        "current_hour": int(current_time.tm_hour),
                        "current_minute": int(current_time.tm_min),
                        "current_timestamp": time.time(),
                        "timestamp": time.time()
                    })
            
            # Resume training if it was paused
            if self.server_instance.training_paused:
                self.server_instance.resume_training(f"Policy now allows round {server_round}")
            
            # Record round start time for duration tracking
            self.round_start_time = time.time()
            
            # Set training active status
            with self._metrics_lock:
                self._global_metrics["training_active"] = True
                self._global_metrics["connected_clients"] = client_manager.num_available()
            
            # Policy check with enhanced context - using client_selection policy type for round configuration
            policy_context = {
                "operation": "configure_round",
                "server_id": self.server_instance.config.get("server_id", "fl_server"),
                "server_round": int(server_round),
                "current_round": int(server_round),
                "total_clients": int(client_manager.num_available()),
                "available_clients": int(client_manager.num_available()),
                "min_clients": int(self.min_available_clients),
                "round_start_time": self.round_start_time,
                "current_parameters_size": len(parameters.tensors) if parameters and parameters.tensors else 0,
                "model": self.server_instance.model_name if self.server_instance else "unknown",
                "dataset": self.server_instance.dataset if self.server_instance else "unknown",
                "timestamp": time.time()
            }
            
            # Check policy before proceeding with round - use a different policy type for round configuration
            policy_result = self.server_instance.check_policy("fl_client_selection", policy_context)
            
            if not policy_result.get("allowed", True):
                reason = policy_result.get("reason", "Policy denied training round")
                logger.warning(f"Round {server_round} denied by policy: {reason}")
                
                # Log policy denial event
                self.server_instance._log_event("ROUND_POLICY_DENIED", {
                    "round": server_round,
                    "reason": reason,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "policy_result": policy_result
                })
                
                # Check if we should stop training entirely
                if policy_result.get("action") == "stop_training":
                    logger.error(f"Policy engine requested training termination at round {server_round}")
                    raise StopTrainingPolicySignal(f"Training stopped by policy: {reason}")
                
                # Return empty configuration to skip this round
                return []
        
        # Record round configuration start time
        config_start_time = time.time()
        
        # Call parent implementation to get the standard configuration
        fit_ins_list = super().configure_fit(server_round, parameters, client_manager)
        
        # Log round configuration time
        config_duration = time.time() - config_start_time
        logger.info(f"Round {server_round} configuration took {config_duration:.2f}s")
        
        if self.server_instance:
            # Log round start event with timing details
            self.server_instance._log_event("ROUND_STARTED", {
                "round": server_round,
                "total_clients": client_manager.num_available(),
                "selected_clients": len(fit_ins_list),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "round_start_time": self.round_start_time,
                "config_duration": config_duration,
                "parameters_size": len(parameters.tensors) if parameters and parameters.tensors else 0
            })

        return fit_ins_list

    def aggregate_fit(self, server_round: int, 
                      results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes]], 
                      failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes], BaseException]]
                      ) -> Tuple[Optional[Parameters], Dict[str, Any]]:
        """Aggregate fit results with enhanced metrics tracking.
        
        Args:
            server_round: Current round number
            results: Successful client results
            failures: Failed client attempts
            
        Returns:
            Tuple of aggregated parameters and metrics dictionary
        """
        # Record aggregation start time
        self.aggregation_start_time = time.time()
        
        logger.info(f"Round {server_round}: Starting aggregation with {len(results)} client results and {len(failures)} failures")
        
        # Enhanced failure logging
        if failures:
            logger.warning(f"Round {server_round}: {len(failures)} clients failed during training")
            for i, failure in enumerate(failures):
                if isinstance(failure, tuple) and len(failure) >= 2:
                    client_proxy, fit_res = failure
                    logger.warning(f"Failure {i+1}: Client {client_proxy.cid if hasattr(client_proxy, 'cid') else 'unknown'}")
                else:
                    logger.warning(f"Failure {i+1}: {str(failure)}")
        
        # Collect enhanced client metrics
        client_training_durations = []
        client_model_types = []
        client_datasets = []
        total_client_training_time = 0.0
        
        for client_proxy, fit_res in results:
            if hasattr(fit_res, 'metrics') and fit_res.metrics:
                # Extract enhanced metrics from client training
                training_duration = fit_res.metrics.get('training_duration', 0.0)
                if training_duration > 0:
                    client_training_durations.append(training_duration)
                    total_client_training_time += training_duration
                
                # Extract model information
                model_type = fit_res.metrics.get('model_type', 'unknown')
                dataset = fit_res.metrics.get('dataset', 'unknown')
                client_model_types.append(model_type)
                client_datasets.append(dataset)
                
                logger.info(f"Client {client_proxy.cid if hasattr(client_proxy, 'cid') else 'unknown'}: "
                           f"training_duration={training_duration:.2f}s, model={model_type}, dataset={dataset}")
        
        # Call the base strategy to get the aggregation results
        aggregated_parameters, aggregated_metrics = super().aggregate_fit(server_round, results, failures)
        
        # Calculate aggregation duration
        aggregation_duration = time.time() - self.aggregation_start_time
        
        # Calculate round duration (if we have round start time)
        round_duration = None
        if self.round_start_time:
            round_duration = time.time() - self.round_start_time
        
        # Enhanced metrics collection with detailed timing
        enhanced_metrics = {
            "round": server_round,
            "successful_clients": len(results),
            "failed_clients": len(failures),
            "total_clients": len(results) + len(failures),
            "aggregation_duration": aggregation_duration,
            "round_duration_partial": round_duration,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "aggregated_metrics": aggregated_metrics,
            # Enhanced client timing metrics
            "client_training_durations": client_training_durations,
            "total_client_training_time": total_client_training_time,
            "average_client_training_time": sum(client_training_durations) / len(client_training_durations) if client_training_durations else 0.0,
            "min_client_training_time": min(client_training_durations) if client_training_durations else 0.0,
            "max_client_training_time": max(client_training_durations) if client_training_durations else 0.0,
            # Model diversity metrics
            "unique_model_types": list(set(client_model_types)) if client_model_types else [],
            "unique_datasets": list(set(client_datasets)) if client_datasets else [],
            "model_type_distribution": {model_type: client_model_types.count(model_type) for model_type in set(client_model_types)} if client_model_types else {},
            "dataset_distribution": {dataset: client_datasets.count(dataset) for dataset in set(client_datasets)} if client_datasets else {}
        }
        
        # Add model size calculation
        if aggregated_parameters and self.server_instance:
            model_size_mb = self.server_instance.calculate_model_size(aggregated_parameters) / (1024 * 1024)
            enhanced_metrics["model_size_mb"] = model_size_mb
            logger.info(f"Round {server_round}: Aggregated model size: {model_size_mb:.2f} MB")
        
        # Store enhanced metrics in server instance
        if self.server_instance:
            # Update global metrics with aggregation info
            with self._metrics_lock:
                self._global_metrics.update({
                    "current_round": server_round,
                    "current_parameters": aggregated_parameters,
                    "last_aggregation_duration": aggregation_duration,
                    "last_round_partial_duration": round_duration,
                    "aggregation_timestamp": enhanced_metrics["timestamp"],
                    "last_client_training_stats": {
                        "total_time": total_client_training_time,
                        "average_time": enhanced_metrics["average_client_training_time"],
                        "min_time": enhanced_metrics["min_client_training_time"],
                        "max_time": enhanced_metrics["max_client_training_time"],
                        "count": len(client_training_durations)
                    }
                })
            
            # Log aggregation completion event with enhanced details
            self.server_instance._log_event("AGGREGATION_COMPLETED", enhanced_metrics)

        logger.info(f"Round {server_round}: Aggregation completed in {aggregation_duration:.2f}s "
                   f"(avg client training: {enhanced_metrics['average_client_training_time']:.2f}s)")
        
        # Store aggregation duration for use in evaluation phase
        self._last_aggregation_duration = aggregation_duration
        
        # Return enhanced metrics along with aggregated parameters
        if aggregated_metrics:
            aggregated_metrics.update(enhanced_metrics)
        else:
            aggregated_metrics = enhanced_metrics
            
        return aggregated_parameters, aggregated_metrics

    def aggregate_evaluate(self, server_round: int, 
                           results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes]], 
                           failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes], BaseException]]
                           ) -> Tuple[Optional[float], Dict[str, Any]]:
        """Aggregate evaluation results with metrics and policy checks.
        
        Args:
            server_round: Current round number
            results: Successful client evaluation results
            failures: Failed client evaluation attempts
            
        Returns:
            Tuple of aggregated loss and metrics dictionary
            
        Raises:
            StopTrainingPolicySignal: If training should be stopped by policy
        """
        # Record evaluation start time
        self.evaluation_start_time = time.time()
        
        logger.info(f"Round {server_round}: Starting evaluation with {len(results)} client results")
        
        # Collect enhanced client evaluation metrics
        client_evaluation_durations = []
        client_model_types = []
        client_datasets = []
        total_client_evaluation_time = 0.0
        
        for client_proxy, evaluate_res in results:
            if hasattr(evaluate_res, 'metrics') and evaluate_res.metrics:
                # Extract enhanced metrics from client evaluation
                evaluation_duration = evaluate_res.metrics.get('evaluation_duration', 0.0)
                if evaluation_duration > 0:
                    client_evaluation_durations.append(evaluation_duration)
                    total_client_evaluation_time += evaluation_duration
                
                # Extract model information
                model_type = evaluate_res.metrics.get('model_type', 'unknown')
                dataset = evaluate_res.metrics.get('dataset', 'unknown')
                client_model_types.append(model_type)
                client_datasets.append(dataset)
                
                logger.info(f"Client {client_proxy.cid if hasattr(client_proxy, 'cid') else 'unknown'}: "
                           f"evaluation_duration={evaluation_duration:.2f}s, model={model_type}, dataset={dataset}")
        
        # Call the base strategy to get the evaluation results
        aggregated_loss, aggregated_metrics = super().aggregate_evaluate(server_round, results, failures)
        
        # Calculate evaluation duration
        evaluation_duration = time.time() - self.evaluation_start_time
        
        # Calculate total round duration
        total_round_duration = None
        if self.round_start_time:
            total_round_duration = time.time() - self.round_start_time
        
        # Calculate individual phase durations
        aggregation_duration = getattr(self, '_last_aggregation_duration', 0)
        
        # Extract accuracy from evaluation results
        accuracy = 0.0
        loss = aggregated_loss or 0.0
        
        # Try to extract accuracy from the evaluation results
        if results:
            # Calculate weighted average accuracy from client results
            total_examples = 0
            weighted_accuracy = 0.0
            
            for client_proxy, evaluate_res in results:
                if hasattr(evaluate_res, 'metrics') and evaluate_res.metrics:
                    client_accuracy = evaluate_res.metrics.get('accuracy', 0.0)
                    num_examples = evaluate_res.num_examples
                    
                    weighted_accuracy += client_accuracy * num_examples
                    total_examples += num_examples
            
            if total_examples > 0:
                accuracy = weighted_accuracy / total_examples
        
        # Enhanced metrics with detailed timing
        enhanced_metrics = {
            "round": server_round,
            "accuracy": accuracy,
            "loss": loss,
            "evaluation_duration": evaluation_duration,
            "total_round_duration": total_round_duration,
            "successful_evaluations": len(results),
            "failed_evaluations": len(failures),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            # Enhanced client evaluation timing metrics
            "client_evaluation_durations": client_evaluation_durations,
            "total_client_evaluation_time": total_client_evaluation_time,
            "average_client_evaluation_time": sum(client_evaluation_durations) / len(client_evaluation_durations) if client_evaluation_durations else 0.0,
            "min_client_evaluation_time": min(client_evaluation_durations) if client_evaluation_durations else 0.0,
            "max_client_evaluation_time": max(client_evaluation_durations) if client_evaluation_durations else 0.0,
            # Model diversity metrics for evaluation
            "eval_unique_model_types": list(set(client_model_types)) if client_model_types else [],
            "eval_unique_datasets": list(set(client_datasets)) if client_datasets else [],
            "eval_model_type_distribution": {model_type: client_model_types.count(model_type) for model_type in set(client_model_types)} if client_model_types else {},
            "eval_dataset_distribution": {dataset: client_datasets.count(dataset) for dataset in set(client_datasets)} if client_datasets else {}
        }
        
        # Add aggregation duration if available
        if hasattr(self, '_last_aggregation_duration'):
            enhanced_metrics["aggregation_duration"] = self._last_aggregation_duration
        
        # Carry over model size from aggregation phase if available
        with self._metrics_lock:
            if "model_size_mb" in self._global_metrics and self._global_metrics["model_size_mb"] > 0:
                enhanced_metrics["model_size_mb"] = self._global_metrics["model_size_mb"]
                logger.info(f"Round {server_round}: Carried over model size from aggregation: {enhanced_metrics['model_size_mb']:.3f} MB")
        
        # Store comprehensive round data in persistent storage
        if self.server_instance and self._fl_round_storage:
            # Ensure we have a proper model size
            model_size_mb = enhanced_metrics.get("model_size_mb", 0)
            if model_size_mb == 0:
                model_size_mb = self._calculate_or_fallback_model_size(server_round)
                enhanced_metrics["model_size_mb"] = model_size_mb
            
            round_data = {
                "round": server_round,
                "timestamp": enhanced_metrics["timestamp"],
                "status": "complete",
                "accuracy": accuracy,
                "loss": loss,
                "training_duration": total_round_duration or 0,
                "aggregation_duration": enhanced_metrics.get("aggregation_duration", 0),
                "evaluation_duration": evaluation_duration,
                "clients": len(results) + len(failures),
                "successful_clients": len(results),
                "failed_clients": len(failures),
                "model_size_mb": model_size_mb,
                "raw_metrics": {
                    "aggregated_loss": aggregated_loss,
                    "aggregated_metrics": aggregated_metrics,
                    "evaluation_results_count": len(results),
                    "round_start_time": self.round_start_time,
                    "aggregation_start_time": self.aggregation_start_time,
                    "evaluation_start_time": self.evaluation_start_time,
                    "phase_durations": {
                        "total": total_round_duration,
                        "aggregation": enhanced_metrics.get("aggregation_duration", 0),
                        "evaluation": evaluation_duration
                    },
                    "client_timing_stats": {
                        "training": getattr(self, '_last_client_training_stats', {}),
                        "evaluation": {
                            "total_time": total_client_evaluation_time,
                            "average_time": enhanced_metrics["average_client_evaluation_time"],
                            "min_time": enhanced_metrics["min_client_evaluation_time"],
                            "max_time": enhanced_metrics["max_client_evaluation_time"],
                            "count": len(client_evaluation_durations)
                        }
                    }
                }
            }
            
            # Store round data persistently
            self._fl_round_storage.store_round(round_data)
            logger.info(f"Round {server_round} data stored persistently: accuracy={accuracy:.4f}, "
                       f"loss={loss:.4f}, duration={total_round_duration:.2f}s, model_size={model_size_mb:.3f}MB")
        
        # Update global metrics with final round results
        if self.server_instance:
            with self._metrics_lock:
                self._global_metrics.update({
                    "current_round": server_round,
                    "last_round_metrics": enhanced_metrics,
                    "last_evaluation_duration": evaluation_duration,
                    "last_round_total_duration": total_round_duration,
                    "last_round_accuracy": accuracy,
                    "last_round_loss": loss,
                    "model_size_mb": enhanced_metrics.get("model_size_mb", 0),
                    "evaluation_timestamp": enhanced_metrics["timestamp"],
                    "last_client_evaluation_stats": {
                        "total_time": total_client_evaluation_time,
                        "average_time": enhanced_metrics["average_client_evaluation_time"],
                        "min_time": enhanced_metrics["min_client_evaluation_time"],
                        "max_time": enhanced_metrics["max_client_evaluation_time"],
                        "count": len(client_evaluation_durations)
                    }
                })
            
            # Log evaluation completion
            self.server_instance._log_event("EVALUATION_COMPLETED", enhanced_metrics)
            
            # Log round completion with comprehensive metrics
            self.server_instance._log_event("ROUND_COMPLETED", {
                **enhanced_metrics,
                "phase_breakdown": {
                    "aggregation_duration": enhanced_metrics.get("aggregation_duration", 0),
                    "evaluation_duration": evaluation_duration,
                    "total_duration": total_round_duration
                }
            })
            
            # Save model checkpoint after successful round completion
            self._save_checkpoint_if_available(server_round)
        
        # --- CRITICAL: Check server control policy after EACH round ---
        logger.info(f"Round {server_round}: Evaluation completed in {evaluation_duration:.2f}s, "
                   f"total round: {total_round_duration:.2f}s "
                   f"(avg client eval: {enhanced_metrics['average_client_evaluation_time']:.2f}s)")
        
        # Policy check for decide_next_round after round completion
        if self.server_instance:
            self._check_next_round_policy(server_round, accuracy, loss, results, failures)
        
        # Store client training stats for next round's logging
        if hasattr(self, '_last_aggregation_duration'):
            self._last_avg_client_training_time = getattr(self, '_last_avg_client_training_time', 0.0)
        
        # Reset timing variables for next round
        self.round_start_time = None
        self.aggregation_start_time = None
        self.evaluation_start_time = None
        
        # Return enhanced metrics
        if aggregated_metrics:
            aggregated_metrics.update(enhanced_metrics)
        else:
            aggregated_metrics = enhanced_metrics
            
        return aggregated_loss, aggregated_metrics

    def _calculate_or_fallback_model_size(self, server_round: int) -> float:
        """Calculate model size from current parameters or use fallback.
        
        Args:
            server_round: Current round number for logging
            
        Returns:
            Model size in MB
        """
        try:
            with self._metrics_lock:
                current_parameters = self._global_metrics.get("current_parameters")
            
            if current_parameters and self.server_instance:
                model_size_bytes = self.server_instance.calculate_model_size(current_parameters)
                model_size_mb = model_size_bytes / (1024 * 1024)
                logger.info(f"Round {server_round}: Calculated model size from current parameters: {model_size_mb:.3f} MB")
                return model_size_mb
            else:
                model_size_bytes = self.server_instance._get_fallback_model_size()
                model_size_mb = model_size_bytes / (1024 * 1024)
                logger.info(f"Round {server_round}: Using fallback model size: {model_size_mb:.3f} MB")
                return model_size_mb
        except Exception as e:
            logger.warning(f"Round {server_round}: Error calculating model size, using fallback: {e}")
            return 1.74  # ~1.74 MB for SimpleCNN

    def _save_checkpoint_if_available(self, server_round: int) -> None:
        """Save model checkpoint after successful round completion.
        
        Args:
            server_round: Current round number
        """
        try:
            with self._metrics_lock:
                current_parameters = self._global_metrics.get("current_parameters")
            
            if current_parameters and hasattr(self.server_instance, '_save_model_checkpoint'):
                self.server_instance._save_model_checkpoint(current_parameters, server_round)
            else:
                logger.debug(f"Round {server_round}: No parameters available for checkpoint saving")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint for round {server_round}: {e}")

    def _check_next_round_policy(self, server_round: int, accuracy: float, loss: float,
                                  results: list, failures: list) -> None:
        """Check policy for next round decision.
        
        Args:
            server_round: Current round number
            accuracy: Current round accuracy
            loss: Current round loss
            results: Successful client results
            failures: Failed client attempts
            
        Raises:
            StopTrainingPolicySignal: If training should be stopped by policy
        """
        # Get current metrics for policy context
        with self._metrics_lock:
            previous_accuracy = self._global_metrics.get("last_round_accuracy", 0.0)
            available_clients_count = self._global_metrics.get("available_clients", len(results))
        
        # Calculate accuracy improvement
        accuracy_improvement = accuracy - previous_accuracy
        
        # Create context for decide_next_round policy check
        decide_context = {
            "server_id": self.server_instance.config.get("server_id", "default-server"),
            "operation": "decide_next_round",
            "current_round": int(server_round),
            "max_rounds": int(self.server_instance.rounds),
            "accuracy": float(accuracy),
            "loss": float(loss),
            "accuracy_improvement": float(accuracy_improvement),
            "available_clients": int(available_clients_count),
            "successful_clients": int(len(results)),
            "failed_clients": int(len(failures)),
            "model": self.server_instance.model_name,
            "dataset": self.server_instance.dataset,
            "timestamp": time.time()
        }
        
        # Check policy for next round decision
        policy_result = self.server_instance.check_policy("fl_server_control", decide_context)
        logger.info(f"Policy check result from v1 API: {policy_result}")
        
        # Handle policy result
        if not policy_result.get("allowed", True):
            reason = policy_result.get("reason", "Policy denied next round")
            logger.warning(f"Policy denied continuing to round {server_round + 1}: {reason}")
            
            # Log policy decision
            self.server_instance._log_event("TRAINING_STOPPED_BY_POLICY", {
                "stopped_after_round": server_round,
                "reason": reason,
                "policy_result": policy_result,
                "final_metrics": {
                    "accuracy": accuracy,
                    "loss": loss,
                    "round": server_round
                }
            })
            
            # CRITICAL FIX: Immediately stop training when policy denies next round
            logger.error(f"STOPPING TRAINING: Policy engine denied continuing after round {server_round}")
            with self._metrics_lock:
                self._global_metrics["training_stopped_by_policy"] = True
                self._global_metrics["stop_reason"] = reason
                
            # Raise exception to immediately stop training instead of just setting flags
            raise StopTrainingPolicySignal(f"Training stopped by policy after round {server_round}: {reason}")
