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
Federated Learning Server implementation.

This module provides the server implementation for federated learning.
"""

import os
import sys
import logging
import argparse
import json
import hashlib
import time
import requests
import traceback
import collections
import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
import threading # Added for metrics server

# --- Add project root to path for absolute imports --- 
# This assumes fl_server.py is in src/fl/server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import flwr as fl
from flwr.server.strategy import FedAvg
from flwr.common import Parameters, Metrics
from flwr.server.server import Server
from flwr.server.client_manager import SimpleClientManager

# --- Flask for Metrics Endpoint --- 
from flask import Flask, jsonify

# --- Werkzeug for metrics server ---
from werkzeug.serving import run_simple

# --- Control gRPC logging ---
import grpc

# --- Add persistent storage ---
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Suppress verbose gRPC logs by default ---
def configure_grpc_logging(enable_verbose=False):
    """Configure gRPC logging level to reduce noise."""
    if not enable_verbose:
        # Set gRPC logger to ERROR level to suppress verbose connection logs
        grpc_logger = logging.getLogger('grpc')
        grpc_logger.setLevel(logging.ERROR)
        
        # Also set GRPC_VERBOSITY environment variable 
        os.environ['GRPC_VERBOSITY'] = 'ERROR'
    else:
        # Enable verbose logging if requested
        grpc_logger = logging.getLogger('grpc')
        grpc_logger.setLevel(logging.DEBUG)
        os.environ['GRPC_VERBOSITY'] = 'DEBUG'

# --- Persistent Storage for FL Rounds ---
class FLRoundStorage:
    """Persistent storage for FL rounds using SQLite."""
    
    def __init__(self, db_path: str = "./fl_rounds.db"):
        """Initialize the FL rounds storage."""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fl_rounds (
                    round_number INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'complete',
                    accuracy REAL DEFAULT 0.0,
                    loss REAL DEFAULT 0.0,
                    training_duration REAL DEFAULT 0.0,
                    model_size_mb REAL DEFAULT 0.0,
                    clients INTEGER DEFAULT 0,
                    raw_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_round_number ON fl_rounds(round_number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON fl_rounds(timestamp)')
            conn.commit()
    
    def store_round(self, round_data: Dict[str, Any]):
        """Store a round's data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO fl_rounds 
                    (round_number, timestamp, status, accuracy, loss, training_duration, 
                     model_size_mb, clients, raw_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    round_data.get('round', 0),
                    round_data.get('timestamp', datetime.datetime.now(datetime.timezone.utc).isoformat()),
                    round_data.get('status', 'complete'),
                    round_data.get('accuracy', 0.0),
                    round_data.get('loss', 0.0),
                    round_data.get('training_duration', 0.0),
                    round_data.get('model_size_mb', 0.0),
                    round_data.get('clients', 0),
                    json.dumps(round_data.get('raw_metrics', {}))
                ))
                conn.commit()
                logger.debug(f"Stored round {round_data.get('round', 0)} to persistent storage")
        except Exception as e:
            logger.error(f"Error storing round data: {e}")
    
    def get_rounds(self, start_round: int = 1, end_round: Optional[int] = None, 
                   limit: int = 1000, offset: int = 0, 
                   min_accuracy: Optional[float] = None, max_accuracy: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get rounds with filtering and limiting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query with filters
                where_clauses = ["round_number >= ?"]
                params = [start_round]
                
                if end_round is not None:
                    where_clauses.append("round_number <= ?")
                    params.append(end_round)
                
                if min_accuracy is not None:
                    where_clauses.append("accuracy >= ?")
                    params.append(min_accuracy)
                
                if max_accuracy is not None:
                    where_clauses.append("accuracy <= ?")
                    params.append(max_accuracy)
                
                where_clause = " AND ".join(where_clauses)
                
                query = f'''
                    SELECT round_number as round, timestamp, status, accuracy, loss, 
                           training_duration, model_size_mb, clients, raw_metrics
                    FROM fl_rounds 
                    WHERE {where_clause}
                    ORDER BY round_number ASC
                    LIMIT ? OFFSET ?
                '''
                
                params.extend([limit, offset])
                cursor = conn.execute(query, params)
                
                rounds = []
                for row in cursor.fetchall():
                    round_data = dict(row)
                    # Parse raw_metrics back to dict
                    try:
                        round_data['raw_metrics'] = json.loads(round_data.get('raw_metrics', '{}'))
                    except:
                        round_data['raw_metrics'] = {}
                    rounds.append(round_data)
                
                return rounds
        except Exception as e:
            logger.error(f"Error getting rounds: {e}")
            return []
    
    def get_round_count(self, start_round: int = 1, end_round: Optional[int] = None,
                       min_accuracy: Optional[float] = None, max_accuracy: Optional[float] = None) -> int:
        """Get total count of rounds matching criteria."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                where_clauses = ["round_number >= ?"]
                params = [start_round]
                
                if end_round is not None:
                    where_clauses.append("round_number <= ?")
                    params.append(end_round)
                
                if min_accuracy is not None:
                    where_clauses.append("accuracy >= ?")
                    params.append(min_accuracy)
                
                if max_accuracy is not None:
                    where_clauses.append("accuracy <= ?")
                    params.append(max_accuracy)
                
                where_clause = " AND ".join(where_clauses)
                query = f"SELECT COUNT(*) FROM fl_rounds WHERE {where_clause}"
                
                cursor = conn.execute(query, params)
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting round count: {e}")
            return 0
    
    def get_latest_round_number(self) -> int:
        """Get the latest round number."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT MAX(round_number) FROM fl_rounds")
                result = cursor.fetchone()[0]
                return result if result is not None else 0
        except Exception as e:
            logger.error(f"Error getting latest round: {e}")
            return 0

# --- Global state for metrics (simpler for this context) ---
global_metrics = {
    "start_time": time.time(),
    "current_round": 0,
    "connected_clients": 0,
    "aggregate_fit_count": 0,
    "aggregate_evaluate_count": 0,
    "last_round_metrics": {},
    "policy_checks_performed": 0,
    "policy_checks_allowed": 0,
    "policy_checks_denied": 0,
    "training_complete": False,
    "training_end_time": None,
    "total_training_duration": 0.0,
    "rounds_history": [],  # Primary history tracking field
    "data_state": "initializing", # Add data_state field
    "model_size_mb": 0.0,  # Added for model size tracking
    "max_rounds": 0  # Add max_rounds for training completion detection
}
metrics_lock = threading.Lock()

# Global persistent storage instance
fl_round_storage = None

class PolicyEnforcementError(Exception):
    """Exception raised when policy enforcement fails."""
    pass

class StopTrainingPolicySignal(Exception):
    """Signal exception to stop training based on policy."""
    pass

# --- Custom Strategy to Track Metrics ---
class MetricsTrackingStrategy(FedAvg):
    """Custom strategy that tracks detailed metrics and integrates with policy engine."""
    
    def __init__(self, *args, server_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_instance = server_instance
        self.round_start_time = None
        self.aggregation_start_time = None
        self.evaluation_start_time = None

    def configure_fit(self, server_round: int, parameters: Parameters, client_manager: fl.server.client_manager.ClientManager) -> List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitIns]]:
        """Configure the fit round with policy checks."""
        if self.server_instance:
            # Check if training was stopped by policy in previous round
            with metrics_lock:
                if global_metrics.get("training_stopped_by_policy", False):
                    reason = global_metrics.get("stop_reason", "Training stopped by policy")
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
                client_training_policy_result = self.server_instance.check_policy("fl_client_training", training_policy_context)
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
            with metrics_lock:
                global_metrics["training_active"] = True
                global_metrics["connected_clients"] = client_manager.num_available()
            
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

    def aggregate_fit(self, server_round: int, results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes]], failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes], BaseException]]) -> Tuple[Optional[Parameters], Dict[str, Any]]:
        """Aggregate fit results with enhanced metrics tracking."""
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
        client_model_sizes = []
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
        
        # Note: Policy checks for round decisions are handled in aggregate_evaluate
        # Aggregation itself should generally proceed unless there are severe issues
        
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
            "round_duration_partial": round_duration,  # Partial because we haven't done evaluation yet
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
            
            # Log model size details
            logger.info(f"Round {server_round}: Aggregated model size: {model_size_mb:.2f} MB")
        
        # Store enhanced metrics in server instance
        if self.server_instance:
            # Update global metrics with aggregation info
            with metrics_lock:
                global_metrics.update({
                    "current_round": server_round,
                    "current_parameters": aggregated_parameters,  # Store parameters for checkpoint saving
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

    def aggregate_evaluate(self, server_round: int, results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes]], failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.EvaluateRes], BaseException]]) -> Tuple[Optional[float], Dict[str, Any]]:
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
        if hasattr(self, 'aggregation_start_time') and self.aggregation_start_time:
            if hasattr(self, '_last_aggregation_duration'):
                enhanced_metrics["aggregation_duration"] = self._last_aggregation_duration
        
        # Carry over model size from aggregation phase if available
        with metrics_lock:
            if "model_size_mb" in global_metrics and global_metrics["model_size_mb"] > 0:
                enhanced_metrics["model_size_mb"] = global_metrics["model_size_mb"]
                logger.info(f"Round {server_round}: Carried over model size from aggregation: {enhanced_metrics['model_size_mb']:.3f} MB")
        
        # Store comprehensive round data in persistent storage
        if self.server_instance and fl_round_storage:
            # Ensure we have a proper model size - calculate it if not available
            model_size_mb = enhanced_metrics.get("model_size_mb", 0)
            if model_size_mb == 0:
                # Try to calculate model size from current parameters if available
                try:
                    # Get the latest model parameters from global metrics or server state
                    with metrics_lock:
                        current_parameters = global_metrics.get("current_parameters")
                    
                    if current_parameters and self.server_instance:
                        model_size_bytes = self.server_instance.calculate_model_size(current_parameters)
                        model_size_mb = model_size_bytes / (1024 * 1024)
                        enhanced_metrics["model_size_mb"] = model_size_mb
                        logger.info(f"Round {server_round}: Calculated model size from current parameters: {model_size_mb:.3f} MB")
                    else:
                        # Use fallback model size calculation
                        model_size_bytes = self.server_instance._get_fallback_model_size()
                        model_size_mb = model_size_bytes / (1024 * 1024)
                        enhanced_metrics["model_size_mb"] = model_size_mb
                        logger.info(f"Round {server_round}: Using fallback model size: {model_size_mb:.3f} MB")
                except Exception as e:
                    logger.warning(f"Round {server_round}: Error calculating model size, using fallback: {e}")
                    # Final fallback - use a reasonable default
                    model_size_mb = 1.74  # ~1.74 MB for SimpleCNN
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
                "model_size_mb": model_size_mb,  # Use the ensured model size
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
            fl_round_storage.store_round(round_data)
            logger.info(f"Round {server_round} data stored persistently: accuracy={accuracy:.4f}, loss={loss:.4f}, duration={total_round_duration:.2f}s, model_size={model_size_mb:.3f}MB")
        
        # Update global metrics with final round results
        if self.server_instance:
            with metrics_lock:
                global_metrics.update({
                    "current_round": server_round,
                    "last_round_metrics": enhanced_metrics,
                    "last_evaluation_duration": evaluation_duration,
                    "last_round_total_duration": total_round_duration,
                    "last_round_accuracy": accuracy,
                    "last_round_loss": loss,
                    "model_size_mb": enhanced_metrics.get("model_size_mb", 0),  # Include model size in global metrics
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
            try:
                # Get current parameters from global metrics if available
                with metrics_lock:
                    current_parameters = global_metrics.get("current_parameters")
                
                if current_parameters and hasattr(self.server_instance, '_save_model_checkpoint'):
                    self.server_instance._save_model_checkpoint(current_parameters, server_round)
                else:
                    logger.debug(f"Round {server_round}: No parameters available for checkpoint saving")
            except Exception as e:
                logger.warning(f"Failed to save checkpoint for round {server_round}: {e}")
        
        # --- CRITICAL: Check server control policy after EACH round ---

        logger.info(f"Round {server_round}: Evaluation completed in {evaluation_duration:.2f}s, total round: {total_round_duration:.2f}s "
                   f"(avg client eval: {enhanced_metrics['average_client_evaluation_time']:.2f}s)")
        
        # Policy check for decide_next_round after round completion
        if self.server_instance:
            # Get current metrics for policy context
            with metrics_lock:
                previous_accuracy = global_metrics.get("last_round_accuracy", 0.0)
                available_clients_count = global_metrics.get("available_clients", len(results))
            
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
                    "final_metrics": enhanced_metrics
                })
                
                # CRITICAL FIX: Immediately stop training when policy denies next round
                logger.error(f"STOPPING TRAINING: Policy engine denied continuing after round {server_round}")
                with metrics_lock:
                    global_metrics["training_stopped_by_policy"] = True
                    global_metrics["stop_reason"] = reason
                    
                # Raise exception to immediately stop training instead of just setting flags
                raise StopTrainingPolicySignal(f"Training stopped by policy after round {server_round}: {reason}")
        
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

class FLServer:
    """Federated Learning Server implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the FL server with configuration."""
        self.config = config
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 8080)
        self.rounds = config.get("rounds", 3)
        self.min_clients = config.get("min_clients", 1)
        self.min_available_clients = config.get("min_available_clients", self.min_clients)
        self.model_name = config.get("model", "unknown")
        self.dataset = config.get("dataset", "unknown")
        self.server_status = "initializing"
        self.is_running = False
        self.server = None
        self.metrics_thread = None
        self.stay_alive_after_training = config.get("stay_alive_after_training", False)
        
        # Results and metrics configuration
        self.results_dir = config.get("results_dir", "./results")
        self.metrics_host = config.get("metrics_host", "0.0.0.0")
        self.metrics_port = config.get("metrics_port", 8081)
        
        # Model parameters persistence
        self.model_checkpoint_file = config.get("model_checkpoint_file", "./last_model_checkpoint.pkl")
        self.saved_parameters = None
        
        # Initialize global metrics with server configuration
        global_metrics["start_time"] = time.time()
        global_metrics["current_round"] = 0
        global_metrics["connected_clients"] = 0
        global_metrics["aggregate_fit_count"] = 0
        global_metrics["aggregate_evaluate_count"] = 0
        global_metrics["last_round_metrics"] = {}
        global_metrics["policy_checks_performed"] = 0
        global_metrics["policy_checks_allowed"] = 0
        global_metrics["policy_checks_denied"] = 0
        global_metrics["training_complete"] = False
        global_metrics["training_end_time"] = None
        global_metrics["total_training_duration"] = 0.0
        global_metrics["rounds_history"] = []
        global_metrics["data_state"] = "initializing"
        global_metrics["model_size_mb"] = 0.0
        global_metrics["max_rounds"] = 0
        
        # Initialize event buffer and lock
        self.event_buffer = collections.deque(maxlen=1000)  # Store up to 1000 recent events
        self.buffer_lock = threading.Lock()
        
        # Restart control flag
        self._restart_requested = False
        
        # Policy engine integration
        self.policy_engine_url = config.get("policy_engine_url", "http://localhost:5000")
        self.policy_auth_token = config.get("policy_auth_token", None)
        self.policy_timeout = config.get("policy_timeout", 10)  # Timeout in seconds for policy requests
        self.policy_max_retries = config.get("policy_max_retries", 3)  # Maximum retry attempts for policy requests
        self.policy_retry_delay = config.get("policy_retry_delay", 2)  # Seconds to wait between retries
        self.policy_engine_wait_time = config.get("policy_engine_wait_time", 60)  # Maximum time to wait for policy engine (seconds)
        
        # Policy file paths
        self.policy_file_path = config.get("policy_file", os.path.join("config", "policies", "policies.json"))
        self.default_policy_file_path = config.get("default_policy_file", os.path.join("config", "policies", "default_policies.json"))
        
        # Verification features to prevent bypassing
        self.policy_check_signatures = {}
        self.last_policy_check_time = None
        self.policy_cache_ttl = config.get("policy_cache_ttl", 10)  # seconds
        self.strict_policy_mode = config.get("strict_policy_mode", True)
        
        # Policy versioning and cache invalidation
        self.cached_policy_version = 0
        self.last_policy_version_check = 0
        self.policy_version_check_interval = config.get("policy_version_check_interval", 30)  # Check every 30 seconds
        
        # Create results directory if it doesn't exist
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Configure gRPC logging
        enable_grpc_verbose = config.get("enable_grpc_verbose", False)
        configure_grpc_logging(enable_grpc_verbose)
        
        # Configure logging
        log_level = config.get("log_level", "INFO")
        log_file = config.get("log_file", None)
        self._setup_logging(log_level, log_file)
        
        # Server state
        self.strategy = None # Store strategy
        self.metrics_app = Flask(__name__)
        
        # Initialize persistent round storage
        storage_dir = config.get("storage_dir", "./fl_storage")
        os.makedirs(storage_dir, exist_ok=True)
        db_path = os.path.join(storage_dir, "fl_rounds.db")
        
        global fl_round_storage
        fl_round_storage = FLRoundStorage(db_path)
        logger.info(f"FL round storage initialized at {db_path}")
        
        # Setup metrics routes
        self._setup_metrics_routes()
        
        # Check policy for rounds and other training parameters
        if self.policy_engine_url:
            try:
                # Check training parameters policy for round count
                context = {
                    "server_id": config.get("server_id", "default-server"),
                    "operation": "training_configuration",
                    "model": self.model_name,
                    "dataset": self.dataset
                }
                
                policy_result = self.check_policy("fl_training_parameters", context)
                logger.info(f"Raw policy result for fl_training_parameters: {policy_result}")
                
                # Check if parameters were returned by the policy, instead of checking 'allowed'
                parameters = policy_result.get("parameters", {})
                if parameters:
                    # Update rounds if provided in policy
                    if "total_rounds" in parameters and isinstance(parameters["total_rounds"], (int, float)):
                        new_rounds = int(parameters["total_rounds"])
                        logger.info(f"Updating rounds from fl_training_parameters policy: {new_rounds} (was: {self.rounds})")
                        self.rounds = new_rounds
                        self.config["rounds"] = self.rounds  # Update config for consistency
                        # Update global_metrics with the new max_rounds value
                        with metrics_lock:
                            global_metrics["max_rounds"] = self.rounds
                
                # Also check server control policy for max_rounds
                context = {
                    "server_id": config.get("server_id", "default-server"),
                    "operation": "decide_next_round",
                    "current_round": int(0),  # We're just starting
                    "max_rounds": int(self.rounds),
                    "accuracy": float(0.0),  # Starting accuracy
                    "loss": float(0.0),  # Starting loss
                    "accuracy_improvement": float(0.0),  # No improvement yet
                    "available_clients": int(0),  # No clients connected yet
                    "successful_clients": int(0),
                    "failed_clients": int(0),
                    "model": self.model_name,
                    "dataset": self.dataset,
                    "timestamp": time.time()
                }
                
                policy_result = self.check_policy("fl_server_control", context)
                logger.info(f"Raw policy result for fl_server_control: {policy_result}")
                
                # Look for parameters regardless of 'allowed' status
                parameters = policy_result.get("parameters", {})
                if "max_rounds" in parameters and isinstance(parameters["max_rounds"], (int, float)):
                    max_rounds = int(parameters["max_rounds"])
                    if max_rounds > 0 and (self.rounds > max_rounds or self.rounds == 3):  # Only override if policy is stricter or we're using default
                        logger.info(f"Updating rounds from fl_server_control policy: {max_rounds} (was: {self.rounds})")
                        self.rounds = max_rounds
                        self.config["rounds"] = self.rounds  # Update config for consistency
                        # Update global_metrics with the new max_rounds value
                        with metrics_lock:
                            global_metrics["max_rounds"] = self.rounds
            except Exception as e:
                logger.warning(f"Error checking policy for rounds: {e}")
                if self.strict_policy_mode:
                    logger.error("Strict policy mode is enabled and policy check failed")
                    raise PolicyEnforcementError(f"Could not check policy for rounds: {e}")
        
        # Update global_metrics with the final max_rounds value for collector/dashboard access
        with metrics_lock:
            global_metrics["max_rounds"] = self.rounds
        logger.info(f"FL Server max_rounds set to {self.rounds} and updated in global_metrics")
        
        logger.info(f"FL Server initialized with config: {json.dumps(config, indent=2)}")
        
        # Log server start event
        self._log_event("SERVER_START", {
            "host": self.host,
            "port": self.port
        })
        
        # Log config loaded event
        self._log_event("CONFIG_LOADED", {
            "config_summary": {
                "model": self.model_name,
                "dataset": self.dataset,
                "rounds": self.rounds,
                "min_clients": self.min_clients,
                "min_available_clients": self.min_available_clients,
                "stay_alive_after_training": self.stay_alive_after_training
            }
        })
        
        # Pause/Resume mechanism
        self.training_paused = False
        self.pause_lock = threading.Lock()
        self.resume_event = threading.Event()
        self.resume_event.set()  # Start with training allowed
    
    def _log_event(self, event_type: str, details: Dict[str, Any]):
        """
        Log an event to the event buffer.
        
        Args:
            event_type: Type of event (see event schema)
            details: Event-specific details dictionary
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_component": "FL_SERVER",
            "event_type": event_type,
            "details": details
        }
        
        with self.buffer_lock:
            self.event_buffer.append(event)
        
        logger.debug(f"Logged event: {event['event_id']} - {event_type}")
    
    def _setup_logging(self, log_level: str, log_file: Optional[str]) -> None:
        """
        Set up logging configuration.
        
        Note: This method configures the root logger. For better modularity and consistency
        across the FlopyNet project, consider replacing this custom setup with a call to
        `src.utils.logging_utils.setup_logging`.
        The utility function offers more features like:
        - Configuration of specific loggers (not root).
        - `ColoredFormatter` for console output.
        - `RotatingFileHandler` for log files.
        - Optional integration with dashboard logging.

        Example usage if refactoring:
        ```
        from src.utils.logging_utils import setup_logging
        # In FLServer.__init__ or a similar setup method:
        # self.logger = setup_logging(
        #     log_level=config.get("log_level", "INFO"), 
        #     log_to_file=True, # Or based on config
        #     log_dir=os.path.join(self.results_dir, "logs"), # Example log directory
        #     app_name=f"FLServer-{self.config.get('server_id', 'default')}"
        # )
        # logger = self.logger # Then use self.logger throughout the class
        ```
        
        Args:
            log_level: Logging level
            log_file: Path to log file (if None, logs to stdout)
        """
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        # --- Create formatter ---
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        # --- Get root logger ---
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # --- Clear existing handlers (if any) ---
        if root_logger.hasHandlers():
            root_logger.handlers.clear()
        
        # --- Setup file handler (if log_file provided) ---
        if log_file:
            # Ensure directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(log_formatter)
            root_logger.addHandler(file_handler)
            
        # --- Setup console handler (always add this) ---
        console_handler = logging.StreamHandler(sys.stdout) # Use stdout or stderr
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)
        
        # Remove basicConfig call
        # logging.basicConfig(**logging_config)
        
        logger.info(f"Logging configured: level={log_level}, file={log_file or 'stdout'}, console=True")
    
    def create_policy_signature(self, policy_type: str, context: Dict[str, Any]) -> str:
        """
        Create a unique signature for the policy check to prevent replay attacks.
        
        Args:
            policy_type: Type of policy check
            context: Context for policy check
            
        Returns:
            Unique signature string
        """
        # Create a deterministic string from the policy type and context
        context_str = json.dumps(context, sort_keys=True)
        data = f"{policy_type}:{context_str}:{time.time()}"
        
        # Create a hash of the data
        return hashlib.sha256(data.encode()).hexdigest()
    
    def check_policy_version_and_refresh(self) -> bool:
        """
        Check if policy version has changed and refresh if needed.
        
        Returns:
            True if policies were refreshed, False otherwise
        """
        current_time = time.time()
        
        # Only check version periodically to avoid overwhelming the policy engine
        if current_time - self.last_policy_version_check < self.policy_version_check_interval:
            return False
        
        try:
            # Get current policy version from policy engine
            version_url = f"{self.policy_engine_url}/api/v1/policy_version"
            response = requests.get(version_url, timeout=self.policy_timeout)
            
            if response.status_code == 200:
                version_data = response.json()
                current_version = version_data.get("policy_version", 0)
                
                self.last_policy_version_check = current_time
                
                # Check if policy version has changed
                if current_version > self.cached_policy_version:
                    logger.info(f"Policy version changed from {self.cached_policy_version} to {current_version}, refreshing cache")
                    self.cached_policy_version = current_version
                    
                    # Clear any local policy caches if we had them
                    self.policy_check_signatures = {}
                    
                    # Don't reset training stop flag automatically when policy updates
                    # If training was stopped by policy, it should stay stopped unless manually restarted
                    with metrics_lock:
                        if global_metrics.get("training_stopped_by_policy", False):
                            logger.info("Policy version updated but training remains stopped by previous policy decision")
                            # Keep the flag set to maintain the stop state
                    
                    self._log_event("POLICY_VERSION_UPDATED", {
                        "old_version": self.cached_policy_version,
                        "new_version": current_version,
                        "timestamp": current_time
                    })
                    
                    return True
                    
        except Exception as e:
            logger.warning(f"Failed to check policy version: {e}")
            # Don't fail if version check fails, just continue with existing version
            
        return False

    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if the action is allowed by the policy engine.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with policy decision and metadata
        """
        # Check for policy version updates before checking policy
        self.check_policy_version_and_refresh()
        
        # --- Metrics Tracking --- 
        with metrics_lock:
             global_metrics["policy_checks_performed"] += 1
        # --- End Metrics --- 
        try:
            # Add timestamp to prevent replay attacks
            context["timestamp"] = time.time()
            
            # Create signature for verification
            signature = self.create_policy_signature(policy_type, context)
            context["signature"] = signature
            
            # Store signature for later verification
            self.policy_check_signatures[signature] = {
                "policy_type": policy_type,
                "timestamp": context["timestamp"]
            }
            
            # Record check time
            self.last_policy_check_time = time.time()
            
            # Call policy engine API
            headers = {'Content-Type': 'application/json'}
            if self.policy_auth_token:
                headers['Authorization'] = f"Bearer {self.policy_auth_token}"
                
            payload = {
                'policy_type': policy_type,
                'context': context
            }
            
            # Setup retry mechanism
            retries = 0
            last_error = None
            
            while retries <= self.policy_max_retries:
                if retries > 0:
                    logger.warning(f"Retrying policy check ({retries}/{self.policy_max_retries})")
                    time.sleep(self.policy_retry_delay)
                
                # Try the v1 API first
                try:
                    response = requests.post(
                        f"{self.policy_engine_url}/api/v1/check",
                        headers=headers,
                        json=payload,
                        timeout=self.policy_timeout
                    )
                    response.raise_for_status() # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
                    
                    # No need to check response.status_code == 200 if raise_for_status() is used and doesn't raise
                    result = response.json()
                    logger.info(f"Policy check result from v1 API: {result}")
                    
                    # Add signature to the result for verification
                    result["signature"] = signature
                    
                    # --- Metrics Tracking --- 
                    if result and result.get('allowed'):
                         with metrics_lock:
                              global_metrics["policy_checks_allowed"] += 1
                    else:
                         with metrics_lock:
                              global_metrics["policy_checks_denied"] += 1
                    # --- End Metrics --- 
                    
                    return result
                except requests.exceptions.HTTPError as http_err:
                    logger.warning(f"HTTP error using v1 policy API ({http_err.response.status_code}): {http_err}. Trying legacy endpoint.")
                    last_error = http_err
                except requests.exceptions.Timeout as timeout_err:
                    logger.warning(f"Timeout error using v1 policy API: {timeout_err}. Trying legacy endpoint.")
                    last_error = timeout_err
                except requests.exceptions.ConnectionError as conn_err:
                    logger.warning(f"Connection error using v1 policy API: {conn_err}. Trying legacy endpoint.")
                    last_error = conn_err
                except requests.exceptions.JSONDecodeError as json_err: # If server returns non-JSON on 200 OK for some reason
                    logger.warning(f"JSON decode error from v1 policy API: {json_err}. Raw response: {response.text[:200] if response else 'N/A'}. Trying legacy endpoint.")
                    last_error = json_err
                except requests.exceptions.RequestException as req_err: # Catch other requests library specific errors
                    logger.warning(f"General request exception using v1 policy API: {req_err}. Trying legacy endpoint.")
                    last_error = req_err
                except Exception as e_v1_unexpected: # Catch any other truly unexpected errors
                    logger.error(f"Unexpected error using v1 policy API: {e_v1_unexpected}. Trying legacy endpoint.", exc_info=True)
                    last_error = e_v1_unexpected
                
                # Try the legacy endpoint
                logger.debug("Attempting to use legacy policy API endpoint.")
                try:
                    response = requests.post(
                        f"{self.policy_engine_url}/api/check_policy",
                        headers=headers,
                        json=payload,
                        timeout=self.policy_timeout
                    )
                    response.raise_for_status() # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
                    
                    # No need to check response.status_code == 200 if raise_for_status() is used and doesn't raise
                    result = response.json()
                    logger.info(f"Policy check result from legacy API: {result}")
                    
                    # Add signature to the result for verification
                    result["signature"] = signature
                    
                    # --- Metrics Tracking --- 
                    if result and result.get('allowed'):
                         with metrics_lock:
                              global_metrics["policy_checks_allowed"] += 1
                    else:
                         with metrics_lock:
                              global_metrics["policy_checks_denied"] += 1
                    # --- End Metrics --- 
                    
                    return result
                except requests.exceptions.HTTPError as http_err_legacy:
                    logger.warning(f"HTTP error using legacy policy API ({http_err_legacy.response.status_code}): {http_err_legacy}. All attempts failed for this retry.")
                    last_error = http_err_legacy
                except requests.exceptions.Timeout as timeout_err_legacy:
                    logger.warning(f"Timeout error using legacy policy API: {timeout_err_legacy}. All attempts failed for this retry.")
                    last_error = timeout_err_legacy
                except requests.exceptions.ConnectionError as conn_err_legacy:
                    logger.warning(f"Connection error using legacy policy API: {conn_err_legacy}. All attempts failed for this retry.")
                    last_error = conn_err_legacy
                except requests.exceptions.JSONDecodeError as json_err_legacy: # If server returns non-JSON on 200 OK
                    logger.warning(f"JSON decode error from legacy policy API: {json_err_legacy}. Raw response: {response.text[:200] if response else 'N/A'}. All attempts failed for this retry.")
                    last_error = json_err_legacy
                except requests.exceptions.RequestException as req_err_legacy: # Catch other requests library specific errors
                    logger.warning(f"General request exception using legacy policy API: {req_err_legacy}. All attempts failed for this retry.")
                    last_error = req_err_legacy
                except Exception as e_legacy_unexpected: # Catch any other truly unexpected errors
                    logger.error(f"Unexpected error using legacy policy API: {e_legacy_unexpected}. All attempts failed for this retry.", exc_info=True)
                    last_error = e_legacy_unexpected
                
                retries += 1
            
            # If we get here, all retries failed
            logger.error(f"Policy check failed after {retries} retries: {last_error}")
            
            # In strict mode, fail if policy check fails
            if self.strict_policy_mode:
                raise PolicyEnforcementError(f"Policy check failed after {retries} retries: {last_error}")
            
            # Default to allowing if policy engine is unreachable
            return {"allowed": True, "reason": f"Policy engine unavailable after {retries} retries: {last_error}", "signature": signature}
                
        except Exception as e:
            logger.error(f"Error checking policy: {e}")
            
            # --- Metrics Tracking --- 
            with metrics_lock:
                global_metrics["policy_checks_denied"] += 1 # Count errors as denials for metrics
            # --- End Metrics --- 

            # In strict mode, fail if policy check fails
            if self.strict_policy_mode:
                raise PolicyEnforcementError(f"Policy check error: {str(e)}")
            
            # Default to allowing if policy engine is unreachable
            return {"allowed": True, "reason": f"Error checking policy: {e}", "signature": "error"}
    
    def verify_policy_result(self, result: Dict[str, Any]) -> bool:
        """
        Verify that a policy result is valid and hasn't been tampered with.
        
        Args:
            result: Policy check result including signature
            
        Returns:
            True if valid, False otherwise
        """
        if "signature" not in result:
            logger.error("Policy result missing signature")
            return False
        
        signature = result["signature"]
        
        # Check if signature exists in our records
        if signature not in self.policy_check_signatures:
            logger.error(f"Unknown policy signature: {signature}")
            return False
        
        # Get the recorded information
        check_info = self.policy_check_signatures[signature]
        
        # Verify that check was recent (within last 60 seconds)
        if time.time() - check_info["timestamp"] > 60:
            logger.error(f"Policy check expired: {signature}")
            return False
        
        return True
    
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
            # Return a realistic fallback model size for common FL models
            return self._get_fallback_model_size()
            
        # Calculate total bytes
        import numpy as np
        from flwr.common import parameters_to_ndarrays
        
        try:
            # If parameters is a Parameters object, convert it to a list of NumPy arrays
            if hasattr(parameters, 'tensors'):
                param_arrays = parameters_to_ndarrays(parameters)
                logger.debug(f"Model size calculation: Converted Parameters object to {len(param_arrays)} arrays")
            else:
                param_arrays = parameters
                logger.debug(f"Model size calculation: Using parameters directly as arrays ({len(param_arrays) if hasattr(parameters, '__len__') else 'unknown'} arrays)")
                
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
            logger.error(f"Parameters type: {type(parameters)}, hasattr tensors: {hasattr(parameters, 'tensors') if parameters else 'N/A'}")
            # Return fallback size on error
            return self._get_fallback_model_size()
    
    def _get_fallback_model_size(self) -> int:
        """
        Get a realistic fallback model size based on common FL models.
        
        Returns:
            Model size in bytes
        """
        # Get model type from config or use default
        model_type = getattr(self, 'model', 'cnn')
        dataset = getattr(self, 'dataset', 'mnist')
        
        # Calculate realistic model sizes for common FL models
        if model_type.lower() in ['cnn', 'simple_cnn']:
            # SimpleCNN for MNIST: ~32*1*25 + 32 + 64*32*25 + 64 + 128*3136 + 128 + 10*128 + 10
            # ≈ 800 + 51,264 + 401,536 + 1,290 = ~454,890 parameters
            total_params = 454890
        elif model_type.lower() in ['mlp', 'simple_mlp']:
            # SimpleMLP: 784*128 + 128 + 128*64 + 64 + 64*10 + 10
            # ≈ 100,480 + 8,256 + 650 = ~109,386 parameters
            total_params = 109386
        else:
            # Default medium-sized model
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
            
            # Default to allowing if there's an error
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
            
            # Default to returning original results if there's an error
            return clients_results
    
    # --- Metrics API Setup --- 
    def _setup_metrics_routes(self):
        """Set up routes for the metrics API."""
        from flask import request
        
        @self.metrics_app.route('/', methods=['GET'])
        def index():
            """Basic index route."""
            return jsonify({"status": "running", "endpoints": ["/health", "/metrics", "/events"]})
        
        @self.metrics_app.route('/metrics', methods=['GET'])
        def get_metrics():
            """Get current metrics as JSON."""
            with metrics_lock:
                # Create a copy to avoid modifying the original
                response = {**global_metrics}
                
                # Remove any non-serializable objects (bytes, etc.)
                # Specifically handle model parameters which might be bytes
                if "current_parameters" in response:
                    del response["current_parameters"]  # Remove non-serializable parameters
                
                # Don't add redundant rounds if they're identical to rounds_history
                # Only add rounds for backwards compatibility if explicitly requested
                if request.args.get('include_rounds', 'false').lower() == 'true':
                    if "rounds_history" in response and isinstance(response["rounds_history"], list):
                        response["rounds"] = response["rounds_history"]
                elif "rounds" in response:
                    # Remove rounds to avoid duplication
                    del response["rounds"]
                
                # Ensure data_state is consistently set
                if "data_state" not in response or not response["data_state"]:
                    if response.get("training_complete", False):
                        response["data_state"] = "training_complete"
                    elif response.get("current_round", 0) > 0:
                        response["data_state"] = "training"
                    else:
                        response["data_state"] = "initializing"
                
            return jsonify(response)
            
        @self.metrics_app.route('/health', methods=['GET'])
        def health_check():
            """Basic health check for the metrics server itself."""
            return jsonify({"status": "healthy", "timestamp": time.time()})
        
        @self.metrics_app.route('/events', methods=['GET'])
        def get_events():
            """
            Get events from the event buffer.
            
            Query parameters:
                since_event_id: Optional event ID to get events after this ID
                limit: Maximum number of events to return (default: 1000)
            """
            try:
                # Parse query parameters
                since_event_id = request.args.get('since_event_id')
                limit = int(request.args.get('limit', 1000))  # No hard maximum limit
                
                logger.debug(f"Events endpoint called with since_event_id={since_event_id}, limit={limit}")
                
                # Lock the buffer while making a copy
                with self.buffer_lock:
                    # Make a snapshot to work with
                    current_events = list(self.event_buffer)
                    
                    if not current_events:
                        logger.debug("Event buffer is empty")
                        return jsonify({"events": [], "last_event_id": None})
                    
                    last_event_id = current_events[-1]["event_id"] if current_events else None
                    logger.debug(f"Found {len(current_events)} events in buffer, last_event_id={last_event_id}")
                    
                    # Filter events after since_event_id if provided
                    start_index = 0
                    if since_event_id:
                        # Find the index of the event *after* since_event_id
                        found = False
                        for i, event in enumerate(current_events):
                            if event["event_id"] == since_event_id:
                                start_index = i + 1
                                found = True
                                logger.debug(f"Found event at index {i}, returning events starting from index {start_index}")
                                break
                                
                        # If since_event_id not found, return all events
                        if not found:
                            logger.debug(f"Event ID {since_event_id} not found, returning all events")
                            start_index = 0
                    
                    # Slice the list based on start_index and limit
                    results = current_events[start_index : start_index + limit]
                    logger.debug(f"Returning {len(results)} events")
                
                return jsonify({
                    "events": results,
                    "last_event_id": last_event_id
                })
            except Exception as e:
                logger.error(f"Error in /events endpoint: {str(e)}", exc_info=True)
                return jsonify({"error": str(e), "events": [], "last_event_id": None}), 500
        
        @self.metrics_app.route('/rounds', methods=['GET'])
        def get_rounds():
            """
            Get FL rounds from persistent storage with filtering and limiting.
            
            Query parameters:
                start_round: Start round number (default: 1)
                end_round: End round number (default: all)
                limit: Maximum number of rounds to return (default: 1000)
                offset: Number of rounds to skip (default: 0)
                min_accuracy: Minimum accuracy filter (default: no filter)
                max_accuracy: Maximum accuracy filter (default: no filter)
            """
            try:
                # Parse query parameters
                start_round = int(request.args.get('start_round', 1))
                end_round = request.args.get('end_round')
                end_round = int(end_round) if end_round else None
                limit = min(int(request.args.get('limit', 1000)), 10000)  # Cap at 10k
                offset = int(request.args.get('offset', 0))
                min_accuracy = request.args.get('min_accuracy', type=float)
                max_accuracy = request.args.get('max_accuracy', type=float)
                
                if not fl_round_storage:
                    return jsonify({"error": "Round storage not initialized", "rounds": []}), 500
                
                # Get rounds from persistent storage
                rounds = fl_round_storage.get_rounds(
                    start_round=start_round,
                    end_round=end_round,
                    limit=limit,
                    offset=offset,
                    min_accuracy=min_accuracy,
                    max_accuracy=max_accuracy
                )
                
                # Get total count for pagination
                total_count = fl_round_storage.get_round_count(
                    start_round=start_round,
                    end_round=end_round,
                    min_accuracy=min_accuracy,
                    max_accuracy=max_accuracy
                )
                
                # Get latest round number
                latest_round = fl_round_storage.get_latest_round_number()
                
                return jsonify({
                    "rounds": rounds,
                    "total_rounds": total_count,
                    "returned_rounds": len(rounds),
                    "latest_round": latest_round,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + len(rounds) < total_count
                    },
                    "filters": {
                        "start_round": start_round,
                        "end_round": end_round,
                        "min_accuracy": min_accuracy,
                        "max_accuracy": max_accuracy
                    }
                })
            except Exception as e:
                logger.error(f"Error in /rounds endpoint: {str(e)}", exc_info=True)
                return jsonify({"error": str(e), "rounds": []}), 500
        
        @self.metrics_app.route('/rounds/latest', methods=['GET'])
        def get_latest_rounds():
            """Get the latest rounds (convenience endpoint)."""
            try:
                limit = min(int(request.args.get('limit', 50)), 1000)
                
                if not fl_round_storage:
                    return jsonify({"error": "Round storage not initialized", "rounds": []}), 500
                
                latest_round_number = fl_round_storage.get_latest_round_number()
                if latest_round_number == 0:
                    return jsonify({"rounds": [], "latest_round": 0})
                
                # Get the latest rounds
                start_round = max(1, latest_round_number - limit + 1)
                rounds = fl_round_storage.get_rounds(
                    start_round=start_round,
                    end_round=latest_round_number,
                    limit=limit
                )
                
                return jsonify({
                    "rounds": rounds,
                    "latest_round": latest_round_number,
                    "returned_rounds": len(rounds)
                })
            except Exception as e:
                logger.error(f"Error in /rounds/latest endpoint: {str(e)}", exc_info=True)
                return jsonify({"error": str(e), "rounds": []}), 500
        
        @self.metrics_app.route('/restart', methods=['POST'])
        def restart_training():
            """Manually restart training if it was stopped by policy or completed."""
            try:
                with metrics_lock:
                    training_stopped = global_metrics.get("training_stopped_by_policy", False)
                    current_round = global_metrics.get("current_round", 0)
                    training_active = global_metrics.get("training_active", False)
                
                # Allow restart if training was stopped by policy OR if training completed but hasn't reached max rounds
                can_restart = training_stopped or (not training_active and current_round < self.rounds)
                
                if not can_restart:
                    return jsonify({
                        "success": False,
                        "message": f"Training cannot be restarted. Current round: {current_round}, Max rounds: {self.rounds}, Training active: {training_active}, Stopped by policy: {training_stopped}"
                    }), 400
                
                # Check if restart is allowed by policy
                restart_allowed = self._check_training_restart_policy()
                if not restart_allowed:
                    return jsonify({
                        "success": False,
                        "message": "Policy does not currently allow training restart"
                    }), 403
                
                # Reset the stop flag and resume training
                with metrics_lock:
                    global_metrics["training_stopped_by_policy"] = False
                    global_metrics["stop_reason"] = None
                    global_metrics["server_status"] = "restarting"
                
                # Resume training if paused
                if self.training_paused:
                    self.resume_training("Manual restart requested via API")
                
                # Log manual restart
                self._log_event("TRAINING_MANUALLY_RESTARTED", {
                    "reason": "Manual restart via API",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "restart_from_round": current_round
                })
                
                logger.info(f"Training restart triggered manually via API from round {current_round}")
                
                # Start a new training loop in a separate thread to avoid blocking the API
                def restart_training_async():
                    try:
                        time.sleep(1)  # Brief delay to allow API response
                        logger.info("Starting new FL training session for manual restart")
                        self._start_training_loop()
                    except Exception as e:
                        logger.error(f"Error in async training restart: {e}")
                        with metrics_lock:
                            global_metrics["server_status"] = "error"
                
                restart_thread = threading.Thread(target=restart_training_async, daemon=True)
                restart_thread.start()
                
                return jsonify({
                    "success": True,
                    "message": f"Training restart initiated from round {current_round}"
                })
                
            except Exception as e:
                logger.error(f"Error restarting training: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.metrics_app.route('/pause', methods=['POST'])
        def pause_training_endpoint():
            """Manually pause training."""
            try:
                if self.training_paused:
                    return jsonify({
                        "success": True,
                        "message": "Training is already paused",
                        "training_paused": True,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }), 200
                
                self.pause_training("Manual pause requested via API")
                return jsonify({
                    "success": True,
                    "message": "Training paused successfully",
                    "training_paused": True,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }), 200
                
            except Exception as e:
                logger.error(f"Error pausing training: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.metrics_app.route('/resume', methods=['POST'])
        def resume_training_endpoint():
            """Manually resume training."""
            try:
                if not self.training_paused:
                    return jsonify({
                        "success": True,
                        "message": "Training is not paused",
                        "training_paused": False,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }), 200
                
                self.resume_training("Manual resume requested via API")
                return jsonify({
                    "success": True,
                    "message": "Training resumed successfully",
                    "training_paused": False,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }), 200
                
            except Exception as e:
                logger.error(f"Error resuming training: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.metrics_app.route('/status', methods=['GET'])
        def get_training_status():
            """Get current training status and restart eligibility."""
            try:
                with metrics_lock:
                    training_stopped = global_metrics.get("training_stopped_by_policy", False)
                    stop_reason = global_metrics.get("stop_reason", None)
                    current_round = global_metrics.get("current_round", 0)
                    connected_clients = global_metrics.get("connected_clients", 0)
                    is_training_active = global_metrics.get("training_active", False)
                
                restart_allowed = False
                if training_stopped:
                    restart_allowed = self._check_training_restart_policy()
                
                # Determine more detailed status
                # Use global_metrics server_status if available, fallback to self.server_status
                global_server_status = global_metrics.get("server_status", self.server_status)
                detailed_status = global_server_status
                
                if global_server_status in ["running", "training"]:
                    if is_training_active and current_round > 0:
                        detailed_status = "training"
                    elif connected_clients == 0:
                        detailed_status = "waiting_for_clients"
                    else:
                        detailed_status = "ready"
                elif global_server_status == "initializing" and is_training_active:
                    # Handle case where training started but status wasn't updated
                    detailed_status = "training"
                
                return jsonify({
                    "server_status": detailed_status,
                    "training_stopped_by_policy": training_stopped,
                    "training_paused": self.training_paused,
                    "pause_reason": global_metrics.get("pause_reason"),
                    "stop_reason": stop_reason,
                    "current_round": current_round,
                    "max_rounds": self.rounds,
                    "restart_allowed": restart_allowed,
                    "connected_clients": connected_clients,
                    "training_active": is_training_active,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error getting training status: {e}")
                return jsonify({"error": str(e)}), 500

    def _run_metrics_server(self):
        """Runs the Flask metrics server in a separate thread."""
        try:
            logger.info(f"Starting metrics API server on {self.metrics_host}:{self.metrics_port}")
            # Try to verify if the port is free before starting
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind((self.metrics_host, self.metrics_port))
                s.close()
                logger.info(f"Port {self.metrics_port} is available for metrics server")
            except socket.error as e:
                logger.warning(f"Port {self.metrics_port} may not be available: {e}")
                
            # Use werkzeug server, disable reloader for thread compatibility
            
            # Add a proper error handler for 404 errors
            @self.metrics_app.errorhandler(404)
            def page_not_found(e):
                return jsonify({"error": "Endpoint not found", "available_endpoints": ["/", "/health", "/metrics", "/events"]}), 404
                
            run_simple(self.metrics_host, self.metrics_port, self.metrics_app, use_reloader=False, use_debugger=False)
            logger.info(f"Metrics API server started successfully on {self.metrics_host}:{self.metrics_port}")
        except Exception as e:
            logger.error(f"Metrics API server failed: {e}", exc_info=True)

    def start(self) -> bool:
        """
        Start the FL server.
        
        Returns:
            True if the server started successfully, False otherwise
        """
        try:
            logger.info("Starting FL server...")
            
            # Start metrics API server in a separate thread
            if not self.metrics_thread:
                self.metrics_thread = threading.Thread(target=self._run_metrics_server)
                self.metrics_thread.daemon = True  # Make thread exit when main thread exits
                self.metrics_thread.start()
                
                # Wait a moment for the metrics thread to start
                time.sleep(0.5)
                
                # Check if metrics server is up by attempting to access health endpoint
                try:
                    response = requests.get(f"http://{self.metrics_host}:{self.metrics_port}/health", timeout=2)
                    if response.status_code == 200:
                        metrics_data = response.json()
                        logger.info(f"Metrics API server health check successful: {metrics_data}")
                except Exception as e:
                    logger.warning(f"Failed to confirm metrics API server startup: {e}")
            
            # Check connectivity to policy engine if configured
            policy_engine_available = False
            if self.policy_engine_url:
                logger.info(f"Checking connectivity to policy engine at {self.policy_engine_url}")
                try:
                    response = requests.get(f"{self.policy_engine_url}/health", timeout=self.policy_timeout)
                    if response.status_code == 200:
                        logger.info(f"Policy engine is available at {self.policy_engine_url}/health")
                        policy_engine_available = True
                    else:
                        logger.warning(f"Policy engine returned status code {response.status_code}")
                except Exception as e:
                    logger.warning(f"Could not connect to policy engine: {e}")
                    if self.strict_policy_mode:
                        logger.error("Strict policy mode is enabled and policy engine is not available")
                        return False
                    
                # If policy engine is available, check for training parameter settings
                if policy_engine_available:
                    logger.info("Policy engine is available, checking for training parameters")
                    
                    # Check for rounds setting in training parameters policy
                    try:
                        context = {
                            "server_id": self.config.get("server_id", "default-server"),
                            "operation": "training_configuration",
                            "current_round": 0,  # We're just starting
                            "model": self.model_name,
                            "dataset": self.dataset,
                            "timestamp": time.time()
                        }
                        
                        policy_result = self.check_policy("fl_training_parameters", context)
                        logger.info(f"Raw policy result for fl_training_parameters: {policy_result}")
                        
                        # Check if parameters were returned by the policy, instead of checking 'allowed'
                        parameters = policy_result.get("parameters", {})
                        if parameters:
                            # Update rounds if provided in policy
                            if "total_rounds" in parameters and isinstance(parameters["total_rounds"], (int, float)):
                                new_rounds = int(parameters["total_rounds"])
                                logger.info(f"Updating rounds from fl_training_parameters policy: {new_rounds} (was: {self.rounds})")
                                self.rounds = new_rounds
                                self.config["rounds"] = self.rounds  # Update config for consistency
                                # Update global_metrics with the new max_rounds value
                                with metrics_lock:
                                    global_metrics["max_rounds"] = self.rounds
                    except Exception as e:
                        logger.warning(f"Error checking fl_training_parameters policy: {e}")
                    
                    # Also check server control policy for max_rounds
                    try:
                        context = {
                            "server_id": self.config.get("server_id", "default-server"),
                            "operation": "decide_next_round",
                            "current_round": int(0),  # We're just starting
                            "max_rounds": int(self.rounds),
                            "accuracy": float(0.0),  # Starting accuracy
                            "loss": float(0.0),  # Starting loss
                            "accuracy_improvement": float(0.0),  # No improvement yet
                            "available_clients": int(0),  # No clients connected yet
                            "successful_clients": int(0),
                            "failed_clients": int(0),
                            "model": self.model_name,
                            "dataset": self.dataset,
                            "timestamp": time.time()
                        }
                        
                        policy_result = self.check_policy("fl_server_control", context)
                        logger.info(f"Raw policy result for fl_server_control: {policy_result}")
                        
                        # Look for parameters regardless of 'allowed' status
                        parameters = policy_result.get("parameters", {})
                        if "max_rounds" in parameters and isinstance(parameters["max_rounds"], (int, float)):
                            max_rounds = int(parameters["max_rounds"])
                            if max_rounds > 0 and (self.rounds > max_rounds or self.rounds == 3):  # Only override if policy is stricter or we're using default
                                logger.info(f"Updating rounds from fl_server_control policy: {max_rounds} (was: {self.rounds})")
                                self.rounds = max_rounds
                                self.config["rounds"] = self.rounds  # Update config for consistency
                                # Update global_metrics with the new max_rounds value
                                with metrics_lock:
                                    global_metrics["max_rounds"] = self.rounds
                    except Exception as e:
                        logger.warning(f"Error checking fl_server_control policy: {e}")
                
                # Check policy for permission to start
                # Note: We create a context with server configuration
                context = {
                    "operation": "server_start",  # Add the missing operation field
                    "server_id": self.config.get("server_id", "default-server"),
                    "current_round": int(0),  # Starting round
                    "max_rounds": int(self.rounds),
                    "accuracy": float(0.0),  # Starting accuracy
                    "loss": float(0.0),  # Starting loss
                    "accuracy_improvement": float(0.0),  # No improvement yet
                    "available_clients": int(0),  # No clients connected yet
                    "successful_clients": int(0),
                    "failed_clients": int(0),
                    "model": self.model_name,
                    "dataset": self.dataset,
                    "rounds": int(self.rounds),  # Ensure it's an integer
                    "min_clients": int(self.min_clients),  # Ensure it's an integer
                    "timestamp": time.time()
                }
                
                policy_result = self.check_policy("fl_server_control", context)
                
                # Check if the policy allows the server to start
                if not policy_result.get("allowed", False):
                    reason = policy_result.get("reason", "Policy denied")
                    logger.error(f"Policy check failed: {reason}")
                    
                    # Instead of just raising an error, enter a monitoring loop
                    # to check for policy changes that might allow training
                    logger.info("Entering policy monitoring loop to wait for policy changes...")
                    if self._monitor_policy_for_training_approval():
                        logger.info("Policy now allows training, proceeding with FL server startup")
                    else:
                        raise PolicyEnforcementError(f"Cannot start FL server: {reason}")
                
                logger.info("Policy check successful, starting FL server")
            else:
                logger.warning("Policy engine URL not configured, skipping policy check")

            # --- Use MetricsTrackingStrategy --- 
            # Try to load saved parameters for restart capability
            initial_parameters = None
            if hasattr(self, '_load_model_checkpoint'):
                initial_parameters = self._load_model_checkpoint()
                if initial_parameters:
                    logger.info("Loaded model parameters from checkpoint for server restart")
                
            self.strategy = MetricsTrackingStrategy(
                server_instance=self,  # Pass server instance to strategy
                min_fit_clients=self.min_clients,
                min_available_clients=self.min_available_clients,
                min_evaluate_clients=self.min_clients,
                initial_parameters=initial_parameters  # Provide saved parameters if available
            )
            # --- End Strategy --- 

            # Add immediate confirmation that server is initializing - this will trigger the entrypoint detection
            logger.info("FL server is running")
            
            # Log the final configuration before starting training
            logger.info(f"Starting training with final configuration:")
            logger.info(f"  Rounds: {self.rounds}")
            logger.info(f"  Min clients: {self.min_clients}")
            logger.info(f"  Min available clients: {self.min_available_clients}")
            logger.info(f"  Model: {self.model_name}")
            logger.info(f"  Dataset: {self.dataset}")
            logger.info(f"  Stay alive after training: {self.stay_alive_after_training}")
            
            self._start_training_loop()
            return True
        except Exception as e:
            logger.error(f"Error during FL server startup: {e}")
            logger.debug(traceback.format_exc())
            return False
        
    def _start_training_loop(self):
        """
        Starts the FL training loop with Flower backend.
        """
        try:
            # Set the server address from host and port
            self.server_address = f"{self.host}:{self.port}"
            
            # Get the final rounds from self.rounds, which should have been updated by policy
            final_rounds = self.rounds
            current_round = global_metrics.get("current_round", 0)
            
            # If we're resuming from a previous session, adjust the rounds
            if current_round > 0:
                remaining_rounds = max(1, final_rounds - current_round)
                logger.info(f"Resuming training from round {current_round}, {remaining_rounds} rounds remaining (total: {final_rounds})")
                server_config = fl.server.ServerConfig(num_rounds=remaining_rounds)
            else:
                logger.info(f"Starting new training session with {final_rounds} rounds")
                server_config = fl.server.ServerConfig(num_rounds=final_rounds)
            
            logger.info(f"Stay alive after training: {self.stay_alive_after_training}")

            logger.info(f"Flower server config: {server_config}")
            logger.info("Starting Flower server...")

            # Set training as active before starting the server
            with metrics_lock:
                global_metrics["training_active"] = True
                global_metrics["server_status"] = "training"
            
            # Also update instance status
            self.server_status = "running"
            
            # Start the Flower server
            # Note: grpc_options parameter is not supported in Flower 1.0.0
            # Server-side gRPC configuration needs to be handled differently
            history = fl.server.start_server(
                server_address=self.server_address,
                strategy=self.strategy,
                config=server_config
            )
            
            # If training completes successfully, set server status
            self.server_status = "completed"
            logger.info("Training completed successfully")
            
            # Update final round count and ensure training was NOT stopped by policy
            with metrics_lock:
                if current_round > 0:
                    # Update the current round to reflect completion
                    global_metrics["current_round"] = final_rounds
                global_metrics["training_active"] = False
                # Clear any policy stop flags since this was a normal completion
                global_metrics["training_stopped_by_policy"] = False
                global_metrics["stop_reason"] = None
            
            # After training completes, decide if we should continue or exit
            if self.stay_alive_after_training:
                logger.info("Server will stay alive after training as configured")
                self._enter_stay_alive_loop()
            else:
                logger.info("Server will shut down as stay_alive_after_training is False")
        except StopTrainingPolicySignal as e:
            self.server_status = "paused_by_policy"
            logger.info(f"Training paused by policy: {e}")
            
            # Pause training instead of stopping completely
            self.pause_training(f"Policy signal: {str(e)}")
            
            # Log policy pause event
            self._log_event("TRAINING_PAUSED_BY_SIGNAL", {
                "reason": str(e),
                "paused_by": "policy_engine",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            
            # Automatically enable stay alive when paused by policy
            self.stay_alive_after_training = True
            logger.info("Enabling stay-alive mode to monitor for policy changes")
            
            # Set the flag to indicate training was stopped by policy
            with metrics_lock:
                global_metrics["training_stopped_by_policy"] = True
                global_metrics["stop_reason"] = str(e)
            
            self._enter_stay_alive_loop()
        except Exception as e:
            self.server_status = "error"
            logger.error(f"Error during training: {e}")
            logger.debug(traceback.format_exc())
            
            # Clear training active status
            with metrics_lock:
                global_metrics["training_active"] = False

    def stop(self) -> bool:
        """
        Stop the FL server.
        
        Returns:
            True if server stopped successfully, False otherwise
        """
        logger.info("Stopping FL server...")
        if self.server:
            # Flower server doesn't have an explicit stop method in this setup
            # It runs until rounds are complete or interrupted.
            # We rely on the process being terminated.
            logger.warning("Flower server stop initiated (process termination required).")
            # If metrics server is running in a thread, we might need to signal it
            # but daemon=True should handle this on main thread exit.
            pass
        self.is_running = False
        logger.info("FL Server stopped")
        return True

    def _enter_stay_alive_loop(self):
        """
        Enter a loop that keeps the server alive until policy indicates it should
        terminate or the server is explicitly stopped. If training was stopped by
        policy, periodically check if it can be restarted.
        """
        logger.info("Entering stay-alive loop after training completion")
        self.is_running = True
        
        # Check if we're in stay-alive because training was stopped by policy
        training_stopped_by_policy = False
        with metrics_lock:
            training_stopped_by_policy = global_metrics.get("training_stopped_by_policy", False)
        
        if training_stopped_by_policy:
            logger.info("Training was stopped by policy - will check periodically if it can be restarted")
        
        try:
            # Loop until explicitly stopped
            while self.is_running:
                # Check if we should terminate based on policy
                if self.policy_engine_url:
                    try:
                        context = {
                            "server_id": self.config.get("server_id", "default-server"),
                            "operation": "server_stay_alive",
                            "current_round": int(global_metrics.get("current_round", 0)),
                            "max_rounds": int(self.rounds),
                            "accuracy": float(global_metrics.get("last_round_accuracy", 0.0)),
                            "loss": float(global_metrics.get("last_round_loss", 0.0)),
                            "accuracy_improvement": float(0.0),  # Not relevant for stay-alive
                            "available_clients": int(global_metrics.get("available_clients", 0)),
                            "successful_clients": int(0),  # Not relevant for stay-alive
                            "failed_clients": int(0),  # Not relevant for stay-alive
                            "model": self.model_name,
                            "dataset": self.dataset,
                            "uptime_seconds": time.time() - global_metrics["start_time"],
                            "timestamp": time.time()
                        }
                        
                        policy_result = self.check_policy("fl_server_control", context)
                        
                        if not policy_result.get("allowed", True):
                            reason = policy_result.get("reason", "Policy denied")
                            logger.info(f"Policy indicates server should shut down: {reason}")
                            self.is_running = False
                            break
                        
                        # If training was stopped by policy, check if it can be restarted
                        with metrics_lock:
                            training_stopped_by_policy = global_metrics.get("training_stopped_by_policy", False)
                            current_round = global_metrics.get("current_round", 0)
                            max_rounds = self.rounds
                        
                        # Only attempt restart if:
                        # 1. Training was actually stopped by policy, AND
                        # 2. We haven't reached the maximum rounds yet
                        if training_stopped_by_policy and current_round < max_rounds:
                            logger.debug(f"Checking if training can be restarted from round {current_round}/{max_rounds}...")
                            restart_allowed = self._check_training_restart_policy()
                            if restart_allowed:
                                logger.info(f"Policy now allows training to restart - restarting FL server from round {current_round}")
                                with metrics_lock:
                                    global_metrics["training_stopped_by_policy"] = False
                                    global_metrics["stop_reason"] = None
                                    global_metrics["training_active"] = True  # Set active before restart
                                    global_metrics["server_status"] = "restarting"
                                
                                # Resume training flag
                                self.resume_training("Policy conditions changed to allow training")
                                
                                # Exit stay-alive loop and restart the training loop completely
                                logger.info("Exiting stay-alive loop to restart FL training with new Flower server instance")
                                self.is_running = False
                                
                                # Restart the training loop with a new Flower server instance
                                logger.info("Starting new FL training session to allow client reconnections")
                                self._start_training_loop()
                                return  # Exit the stay-alive function completely
                        elif training_stopped_by_policy and current_round >= max_rounds:
                            logger.info(f"Training was stopped by policy but max rounds ({max_rounds}) already reached - clearing policy stop flag")
                            with metrics_lock:
                                global_metrics["training_stopped_by_policy"] = False
                                global_metrics["stop_reason"] = None
                        
                        # Get wait time from policy, default to 60 seconds
                        parameters = policy_result.get("parameters", {})
                        wait_time = parameters.get("wait_time", self.policy_engine_wait_time)
                        
                        logger.debug(f"Stay-alive policy check passed, sleeping for {wait_time} seconds")
                        
                    except Exception as e:
                        logger.warning(f"Error checking stay-alive policy: {e}")
                        # Default wait time if policy check fails
                        wait_time = self.policy_engine_wait_time
                else:
                    # No policy engine, use default wait time
                    wait_time = 60
                    logger.debug(f"No policy engine configured, sleeping for {wait_time} seconds")
                
                # Sleep for the specified wait time
                # Use small intervals to allow for faster response to stop requests
                for _ in range(int(wait_time * 2)):
                    if not self.is_running:
                        break
                    time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Error in stay-alive loop: {e}")
            logger.debug(traceback.format_exc())
        finally:
            logger.info("Exiting stay-alive loop")
            self.is_running = False

    def _check_training_restart_policy(self) -> bool:
        """
        Check if training can be restarted based on current policy conditions.
        
        Returns:
            True if training is allowed to restart, False otherwise
        """
        try:
            # Get current time for time-based policies
            current_time = time.localtime()
            
            # Check both client training policy (for time restrictions) and server control policy
            # Use the ACTUAL current round where training was stopped, not 0
            stopped_round = global_metrics.get("current_round", 0)
            
            # First check if we're outside peak hours (client training policy)
            client_training_context = {
                "operation": "model_training",
                "server_id": self.config.get("server_id", "default-server"),
                "current_round": int(stopped_round),  # Use stopped round, not 0
                "server_round": int(stopped_round),
                "model": self.model_name,
                "dataset": self.dataset,
                "available_clients": int(0),  # Use 0 since we're checking restart conditions
                "timestamp": time.time(),
                "current_hour": int(current_time.tm_hour),
                "current_minute": int(current_time.tm_min),
                "current_day_of_week": int(current_time.tm_wday),
                "current_timestamp": time.time()
            }
            
            client_policy_result = self.check_policy("fl_client_training", client_training_context)
            if not client_policy_result.get("allowed", True):
                logger.debug(f"Client training policy denies restart: {client_policy_result.get('reason', 'Unknown')}")
                return False
            
            # For server control policy, check if we can continue from current round
            # Use current state instead of starting fresh
            current_accuracy = global_metrics.get("last_round_accuracy", 0.0)
            current_loss = global_metrics.get("last_round_loss", 0.0)
            
            server_control_context = {
                "server_id": self.config.get("server_id", "default-server"),
                "operation": "decide_next_round",
                "current_round": int(stopped_round),  # Continue from where we stopped
                "max_rounds": int(self.rounds),
                "accuracy": float(current_accuracy),
                "loss": float(current_loss),
                "accuracy_improvement": float(0.0),  # Could calculate this properly
                "available_clients": int(self.min_clients),  # Assume minimum clients will be available
                "successful_clients": int(self.min_clients),
                "failed_clients": int(0),
                "model": self.model_name,
                "dataset": self.dataset,
                "timestamp": time.time()
            }
            
            server_policy_result = self.check_policy("fl_server_control", server_control_context)
            if not server_policy_result.get("allowed", True):
                logger.debug(f"Server control policy denies restart: {server_policy_result.get('reason', 'Unknown')}")
                return False
            
            logger.info(f"All policies allow training to restart from round {stopped_round}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking training restart policy: {e}")
            return False
    
    def _restart_training(self):
        """
        Restart training after it was stopped by policy.
        Continue from where we left off instead of starting fresh.
        """
        try:
            stopped_round = global_metrics.get("current_round", 0)
            logger.info(f"Restarting FL training from round {stopped_round}...")
            
            # Reset server status but preserve training state
            self.server_status = "running"
            
            # Ensure server stays alive for restart
            self.stay_alive_after_training = True
            
            # Wait a moment to ensure any previous server instance is fully stopped
            time.sleep(2)
            
            # Reset any server instance references
            self.server = None
            
            # Update global metrics to indicate we're resuming
            with metrics_lock:
                global_metrics["training_stopped_by_policy"] = False
                global_metrics["stop_reason"] = None
                global_metrics["server_status"] = "running"
                # Preserve the current round - don't reset to 0
                if "current_round" not in global_metrics:
                    global_metrics["current_round"] = 0
            
            # Log restart event with state preservation info
            self._log_event("TRAINING_RESUMED", {
                "reason": "Policy conditions changed to allow training",
                "resuming_from_round": stopped_round,
                "max_rounds": self.rounds,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            
            # Restart the training loop - this will continue from current round
            self._start_training_loop()
            
        except Exception as e:
            logger.error(f"Error restarting training: {e}")
            logger.debug(traceback.format_exc())
            self.server_status = "error"

    def _monitor_policy_for_training_approval(self):
        """
        Monitor the policy engine for changes that might allow training.
        
        Returns:
            True if policy allows training, False otherwise
        """
        logger.info("Starting policy monitoring loop, checking every 30 seconds for policy changes...")
        max_wait_time = 300  # Maximum 5 minutes of waiting
        wait_interval = 30  # Check every 30 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                # Check policy version periodically
                if self.check_policy_version_and_refresh():
                    logger.info("Policy version updated, checking if training is now allowed...")
                else:
                    logger.debug("Policy version unchanged, checking anyway...")
                    
                # Check policy again 
                context = {
                    "server_id": self.config.get("server_id", "default-server"),
                    "operation": "decide_next_round",
                    "current_round": int(global_metrics.get("current_round", 0)),  # Use actual current round
                    "max_rounds": int(self.rounds),
                    "accuracy": float(global_metrics.get("last_round_accuracy", 0.0)),  # Use actual accuracy
                    "loss": float(global_metrics.get("last_round_loss", 0.0)),  # Use actual loss
                    "accuracy_improvement": float(0.0),  # No improvement yet
                    "available_clients": int(0),  # No clients connected yet
                    "successful_clients": int(0),
                    "failed_clients": int(0),
                    "model": self.model_name,
                    "dataset": self.dataset,
                    "rounds": int(self.rounds),  # Ensure it's an integer
                    "min_clients": int(self.min_clients),  # Ensure it's an integer
                    "timestamp": time.time()
                }
                
                policy_result = self.check_policy("fl_server_control", context)
                
                if policy_result.get("allowed", False):
                    logger.info("Policy now allows training, proceeding with FL server startup")
                    return True
                else:
                    reason = policy_result.get("reason", "Policy denied")
                    logger.info(f"Policy still denies training: {reason}. Waiting {wait_interval} seconds before next check...")
                    
            except Exception as e:
                logger.warning(f"Error checking policy during monitoring: {e}")
                
            # Wait before next check
            time.sleep(wait_interval)
            elapsed_time += wait_interval
            
        logger.warning(f"Policy monitoring timeout after {max_wait_time} seconds. Training will not start.")
        return False

    def _save_model_checkpoint(self, parameters, round_num: int):
        """Save model parameters to checkpoint file for restart capability."""
        try:
            import pickle
            checkpoint_data = {
                "parameters": parameters,
                "round": round_num,
                "timestamp": time.time(),
                "model_name": self.model_name,
                "dataset": self.dataset
            }
            
            with open(self.model_checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
                
            logger.info(f"Saved model checkpoint for round {round_num} to {self.model_checkpoint_file}")
            self.saved_parameters = parameters
            
        except Exception as e:
            logger.warning(f"Failed to save model checkpoint: {e}")
    
    def _load_model_checkpoint(self):
        """Load model parameters from checkpoint file if available."""
        try:
            import pickle
            import os
            
            if not os.path.exists(self.model_checkpoint_file):
                logger.info("No model checkpoint file found")
                return None
                
            with open(self.model_checkpoint_file, 'rb') as f:
                checkpoint_data = pickle.load(f)
                
            parameters = checkpoint_data.get("parameters")
            round_num = checkpoint_data.get("round", 0)
            model_name = checkpoint_data.get("model_name", "unknown")
            dataset = checkpoint_data.get("dataset", "unknown")
            
            if model_name == self.model_name and dataset == self.dataset:
                logger.info(f"Loaded model checkpoint from round {round_num}")
                self.saved_parameters = parameters
                return parameters
            else:
                logger.warning(f"Checkpoint model mismatch: saved {model_name}/{dataset}, current {self.model_name}/{self.dataset}")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to load model checkpoint: {e}")
            return None

    def pause_training(self, reason: str = "Policy denied"):
        """
        Pause the FL training without disconnecting clients.
        
        Args:
            reason: The reason for pausing training
        """
        with self.pause_lock:
            if not self.training_paused:
                self.training_paused = True
                self.resume_event.clear()
                
                logger.info(f"Training paused: {reason}")
                
                # Update global metrics
                with metrics_lock:
                    global_metrics["training_paused"] = True
                    global_metrics["pause_reason"] = reason
                    global_metrics["server_status"] = "paused"
                
                # Log pause event
                self._log_event("TRAINING_PAUSED", {
                    "reason": reason,
                    "paused_at_round": global_metrics.get("current_round", 0),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
    
    def resume_training(self, reason: str = "Policy now allows training"):
        """
        Resume the FL training from where it was paused.
        
        Args:
            reason: The reason for resuming training
        """
        with self.pause_lock:
            if self.training_paused:
                self.training_paused = False
                self.resume_event.set()
                
                logger.info(f"Training resumed: {reason}")
                
                # Update global metrics
                with metrics_lock:
                    global_metrics["training_paused"] = False
                    global_metrics["pause_reason"] = None
                    global_metrics["server_status"] = "running"
                
                # Log resume event
                self._log_event("TRAINING_RESUMED", {
                    "reason": reason,
                    "resumed_at_round": global_metrics.get("current_round", 0),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
    
    def wait_if_paused(self, context: str = "training"):
        """
        Wait if training is currently paused. This method blocks until training is resumed.
        
        Args:
            context: Description of what is waiting (for logging)
        """
        if self.training_paused:
            logger.info(f"{context} is waiting - training is paused")
            self.resume_event.wait()  # Block until training is resumed
            logger.info(f"{context} continuing - training resumed")

# Command line interface
def main():
    """Main entry point for the FL server."""
    parser = argparse.ArgumentParser(description="Federated Learning Server")
    parser.add_argument("--config", type=str, default="config/server_config.json", 
                        help="Path to server configuration file")
    parser.add_argument("--log-file", type=str, help="Path to log file")
    # Add direct overrides for common config values if needed
    parser.add_argument("--host", type=str, help="Server host address")
    parser.add_argument("--port", type=int, help="Server port")
    parser.add_argument("--rounds", type=int, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, help="Minimum clients for training")
    
    # Policy engine related arguments
    parser.add_argument("--policy-engine-url", type=str, help="Policy Engine URL")
    parser.add_argument("--policy-timeout", type=int, help="Timeout for policy requests (seconds)")
    parser.add_argument("--policy-retries", type=int, help="Maximum retry attempts for policy checks")
    parser.add_argument("--policy-retry-delay", type=int, help="Delay between policy check retries (seconds)")
    parser.add_argument("--policy-engine-wait-time", type=int, help="Maximum time to wait for policy engine (seconds)")
    parser.add_argument("--strict-policy-mode", type=bool, help="Whether to fail if policy engine is unavailable")
    
    # Add gRPC logging control
    parser.add_argument("--enable-grpc-verbose", action="store_true", help="Enable verbose gRPC logging (default: disabled)")
    
    # Add option to stay alive after training completes
    parser.add_argument("--stay-alive-after-training", action="store_true", help="Keep server alive after training completes")
    
    args = parser.parse_args()
    
    # Load configuration from file
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in configuration file: {args.config}")
        sys.exit(1)

    # Override config with command-line arguments if provided
    if args.log_file:
        config["log_file"] = args.log_file
    if args.host:
        config["host"] = args.host
    if args.port:
        config["port"] = args.port
    if args.rounds:
        config["rounds"] = args.rounds
    if args.min_clients:
        config["min_clients"] = args.min_clients
        config["min_available_clients"] = max(config.get("min_available_clients", 0), args.min_clients) # Ensure min_available >= min_clients
    
    # Policy engine related overrides
    if args.policy_engine_url:
        config["policy_engine_url"] = args.policy_engine_url
    if args.policy_timeout:
        config["policy_timeout"] = args.policy_timeout
    if args.policy_retries:
        config["policy_max_retries"] = args.policy_retries
    if args.policy_retry_delay:
        config["policy_retry_delay"] = args.policy_retry_delay
    if args.policy_engine_wait_time:
        config["policy_engine_wait_time"] = args.policy_engine_wait_time
    if args.strict_policy_mode is not None:
        config["strict_policy_mode"] = args.strict_policy_mode
        
    # Add gRPC logging option
    config["enable_grpc_verbose"] = args.enable_grpc_verbose
    
    # --- Correctly determine stay_alive_after_training --- 
    # Priority: Command-line > Environment Variable > Config File > Default (False)
    stay_alive = False # Default
    if "stay_alive_after_training" in config:
        stay_alive = config.get("stay_alive_after_training", False)
    if os.environ.get("STAY_ALIVE_AFTER_TRAINING") is not None:
        stay_alive = os.environ.get("STAY_ALIVE_AFTER_TRAINING").lower() in ("true", "1", "yes")
        logger.info(f"Using stay alive setting from environment: {stay_alive}")
    if args.stay_alive_after_training: # Command-line flag overrides others
        stay_alive = True
        logger.info(f"Using stay alive setting from command-line flag: {stay_alive}")
    config["stay_alive_after_training"] = stay_alive
    # --- End stay_alive logic ---
        
    # Initialize and start the server
    fl_server = FLServer(config=config)
    
    try:
        success = fl_server.start()
        if not success:
            logger.error("Server startup failed")
            sys.exit(1)
            
        # If we should stay alive after training, keep the main thread running
        if fl_server.stay_alive_after_training:  # Use the server instance flag, which may have been updated by policy
            logger.info("Training completed, but server is configured to stay alive")
            try:
                # Keep the main thread running
                while True:
                    time.sleep(60)  # Sleep for a minute at a time
                    logger.debug("Server still alive, waiting for external termination")
                    
                    # Optionally check policy periodically to see if we should exit
                    # This allows remote policy changes to eventually terminate the server
                    if fl_server.policy_engine_url:
                        try:
                            context = {
                                "server_id": config.get("server_id", "default-server"),
                                "operation": "server_stay_alive",
                                "current_round": int(global_metrics.get("current_round", 0)),
                                "max_rounds": int(fl_server.rounds),
                                "accuracy": float(global_metrics.get("last_round_accuracy", 0.0)),
                                "loss": float(global_metrics.get("last_round_loss", 0.0)),
                                "accuracy_improvement": float(0.0),  # Not relevant for stay-alive
                                "available_clients": int(global_metrics.get("available_clients", 0)),
                                "successful_clients": int(0),  # Not relevant for stay-alive
                                "failed_clients": int(0),  # Not relevant for stay-alive
                                "model": fl_server.model_name,
                                "dataset": fl_server.dataset,
                                "uptime_seconds": time.time() - global_metrics["start_time"],
                                "timestamp": time.time()
                            }
                            
                            policy_result = fl_server.check_policy("fl_server_control", context)
                            
                            if not policy_result.get("allowed", True):
                                reason = policy_result.get("reason", "Policy requires server shutdown")
                                logger.info(f"Policy now requires server to shut down: {reason}")
                                break
                        except Exception as e:
                            logger.warning(f"Error checking stay-alive policy: {e}")
                            # Continue running even with policy check errors
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down")
            except Exception as e:
                logger.error(f"Error in stay-alive loop: {e}")
            finally:
                fl_server.stop()
        else:
            # Only call stop if we're not trying to stay alive
            fl_server.stop()
            logger.info("FL Server process finished.")
            
    except PolicyEnforcementError as e:
        logger.error(f"Server startup failed due to policy: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during server startup: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 