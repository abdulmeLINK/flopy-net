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

# --- Import persistent storage from extracted module ---
from src.fl.server.storage import FLRoundStorage

# --- Import strategies from extracted module ---
from src.fl.server.strategies import MetricsTrackingStrategy, StopTrainingPolicySignal

# --- Import shared policy client ---
from src.fl.common.policy_client import PolicyClient, PolicyEnforcementError

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

# Note: StopTrainingPolicySignal and MetricsTrackingStrategy are now imported from
# src.fl.server.strategies module. See src/fl/server/strategies/metrics_tracking.py

def create_metrics_tracking_strategy(*args, server_instance=None, **kwargs) -> MetricsTrackingStrategy:
    """Factory function to create a MetricsTrackingStrategy with module-level globals.
    
    This function creates a MetricsTrackingStrategy instance pre-configured with
    the module-level global_metrics, metrics_lock, and fl_round_storage references.
    
    Args:
        *args: Arguments passed to MetricsTrackingStrategy
        server_instance: Reference to the FLServer instance
        **kwargs: Keyword arguments passed to MetricsTrackingStrategy
        
    Returns:
        Configured MetricsTrackingStrategy instance
    """
    return MetricsTrackingStrategy(
        *args,
        server_instance=server_instance,
        global_metrics=global_metrics,
        metrics_lock=metrics_lock,
        fl_round_storage=fl_round_storage,
        **kwargs
    )


# Import training control mixin
from src.fl.server.fl_training_control import TrainingControlMixin
from src.fl.server.fl_policy_enforcement import PolicyEnforcementMixin


class FLServer(TrainingControlMixin, PolicyEnforcementMixin):
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
        self.policy_timeout = config.get("policy_timeout", 10)
        self.policy_max_retries = config.get("policy_max_retries", 3)
        self.policy_retry_delay = config.get("policy_retry_delay", 2)
        self.policy_engine_wait_time = config.get("policy_engine_wait_time", 60)
        
        # Policy file paths
        self.policy_file_path = config.get("policy_file", os.path.join("config", "policies", "policies.json"))
        self.default_policy_file_path = config.get("default_policy_file", os.path.join("config", "policies", "default_policies.json"))
        
        # Policy mode configuration
        self.policy_cache_ttl = config.get("policy_cache_ttl", 10)
        self.strict_policy_mode = config.get("strict_policy_mode", True)
        
        # Initialize shared policy client
        self.policy_client = PolicyClient(
            policy_engine_url=self.policy_engine_url,
            auth_token=self.policy_auth_token,
            timeout=self.policy_timeout,
            max_retries=self.policy_max_retries,
            retry_delay=self.policy_retry_delay,
            strict_mode=self.strict_policy_mode,
            cache_ttl=self.policy_cache_ttl
        )
        
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
    
    # Policy enforcement methods (check_policy, verify_policy_result, calculate_model_size,
    # _get_fallback_model_size, client_filter, evaluate_clients) are provided via PolicyEnforcementMixin
    # --- Metrics API Setup --- 
    def _setup_metrics_routes(self):
        """Set up routes for the metrics API (delegated to fl_metrics_routes module)."""
        from src.fl.server.fl_metrics_routes import setup_metrics_routes
        setup_metrics_routes(self)

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
                
            # Use factory function to create strategy with module-level globals
            self.strategy = create_metrics_tracking_strategy(
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
                                
                                # Exit stay-alive loop first
                                self.is_running = False
                                
                                # Use the proper restart method which handles full cleanup
                                logger.info("Calling _restart_training() for proper state reset and restart")
                                self._restart_training()
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

    # Training control methods are provided by TrainingControlMixin:
    # - _check_training_restart_policy
    # - _restart_training
    # - _monitor_policy_for_training_approval
    # - _save_model_checkpoint
    # - _load_model_checkpoint
    # - pause_training
    # - resume_training
    # - wait_if_paused

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