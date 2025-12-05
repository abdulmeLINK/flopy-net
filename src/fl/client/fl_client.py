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
Federated Learning Client implementation.

This module provides the client implementation for federated learning.
"""

import os
import sys
import logging
import argparse
import json
import hashlib
import time
import requests
import socket
import re
import uuid
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import flwr as fl
from flwr.common import NDArrays
import pkg_resources

# --- Control gRPC logging ---
import grpc

# --- Add this import to fix the ConfigurationError issue ---
from src.fl.common.model_handler import ModelHandler, ConfigurationError

# --- Import policy client for shared policy checking ---
from src.fl.common.policy_client import PolicyClient, PolicyEnforcementError

# --- Import minimal model interface for fallback training ---
from src.fl.client.models.minimal_model import MinimalModelInterface

# --- Import FlowerClient implementation ---
from src.fl.client.flower_client import FlowerClient

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

class FLClient:
    """Federated Learning Client implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the FL client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        
        # Check GNS3_IP_MAP first for server host
        server_host_from_config = config.get("server_host", "localhost")
        self.server_host = server_host_from_config
        
        # Try to get server IP from GNS3_IP_MAP environment variable
        gns3_ip_map = os.environ.get("GNS3_IP_MAP", "")
        if gns3_ip_map and "fl-server:" in gns3_ip_map:
            # Parse the GNS3_IP_MAP to find the server IP
            try:
                # Format is like "fl-server:192.168.100.10,fl-client-1:192.168.100.101"
                mapping_entries = gns3_ip_map.split(",")
                for entry in mapping_entries:
                    if entry.startswith("fl-server:"):
                        server_ip = entry.split(":")[1]
                        logger.info(f"Using server IP from GNS3_IP_MAP: {server_ip}")
                        self.server_host = server_ip
                        break
            except Exception as e:
                logger.warning(f"Error parsing GNS3_IP_MAP: {e}, using server_host from config")
        
        # Allow direct override from environment variables
        if os.environ.get("FL_SERVER_HOST"):
            self.server_host = os.environ.get("FL_SERVER_HOST")
            logger.info(f"Overriding server host from FL_SERVER_HOST env var: {self.server_host}")
        
        # Check NODE_IP_FL_SERVER environment variable (from GNS3 configuration)
        if os.environ.get("NODE_IP_FL_SERVER"):
            self.server_host = os.environ.get("NODE_IP_FL_SERVER")
            logger.info(f"Using server IP from NODE_IP_FL_SERVER: {self.server_host}")
        
        self.server_port = config.get("server_port", 8080)
        if os.environ.get("FL_SERVER_PORT"):
            try:
                self.server_port = int(os.environ.get("FL_SERVER_PORT"))
                logger.info(f"Overriding server port from FL_SERVER_PORT env var: {self.server_port}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid FL_SERVER_PORT env var: {e}, using config value: {self.server_port}")
        
        self.client_id = config.get("client_id", f"client_{os.getpid()}")
        if os.environ.get("FL_CLIENT_ID"):
            self.client_id = os.environ.get("FL_CLIENT_ID")
            logger.info(f"Overriding client ID from FL_CLIENT_ID env var: {self.client_id}")
        
        self.model_name = config.get("model", "cnn")
        if os.environ.get("FL_MODEL"):
            self.model_name = os.environ.get("FL_MODEL")
            logger.info(f"Overriding model name from FL_MODEL env var: {self.model_name}")
        
        self.dataset = config.get("dataset", "mnist")
        if os.environ.get("FL_DATASET"):
            self.dataset = os.environ.get("FL_DATASET")
            logger.info(f"Overriding dataset from FL_DATASET env var: {self.dataset}")
        
        self.local_epochs = config.get("local_epochs", 1)
        if os.environ.get("FL_LOCAL_EPOCHS"):
            try:
                self.local_epochs = int(os.environ.get("FL_LOCAL_EPOCHS"))
                logger.info(f"Overriding local epochs from FL_LOCAL_EPOCHS env var: {self.local_epochs}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid FL_LOCAL_EPOCHS env var: {e}, using config value: {self.local_epochs}")
        
        self.batch_size = config.get("batch_size", 32)
        self.learning_rate = config.get("learning_rate", 0.01)
        self.momentum = config.get("momentum", 0.9)
        
        # --- Model Definition and Classes --- 
        self.model_definition_module = config.get("model_definition_module", None)
        if os.environ.get("FL_MODEL_DEFINITION_MODULE"):
            self.model_definition_module = os.environ.get("FL_MODEL_DEFINITION_MODULE")
            logger.info(f"Overriding model definition module from FL_MODEL_DEFINITION_MODULE env var: {self.model_definition_module}")

        self.model_class_name = config.get("model_class_name", None)
        if os.environ.get("FL_MODEL_CLASS_NAME"):
            self.model_class_name = os.environ.get("FL_MODEL_CLASS_NAME")
            logger.info(f"Overriding model class name from FL_MODEL_CLASS_NAME env var: {self.model_class_name}")

        self.num_classes = config.get("num_classes", 10) # Default to 10, e.g., for MNIST/CIFAR
        if os.environ.get("FL_NUM_CLASSES"):
            try:
                self.num_classes = int(os.environ.get("FL_NUM_CLASSES"))
                logger.info(f"Overriding num_classes from FL_NUM_CLASSES env var: {self.num_classes}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid FL_NUM_CLASSES env var: {e}, using config/default value: {self.num_classes}")
        # --- End Model Definition --- 

        self.results_dir = config.get("results_dir", "./results")
        if os.environ.get("FL_RESULTS_DIR"):
            self.results_dir = os.environ.get("FL_RESULTS_DIR")
            logger.info(f"Overriding results directory from FL_RESULTS_DIR env var: {self.results_dir}")
        
        # Policy engine integration
        self.policy_engine_url = config.get("policy_engine_url", "http://localhost:5000")
        if os.environ.get("POLICY_ENGINE_URL"):
            self.policy_engine_url = os.environ.get("POLICY_ENGINE_URL")
            logger.info(f"Overriding policy engine URL from POLICY_ENGINE_URL env var: {self.policy_engine_url}")
        elif os.environ.get("NODE_IP_POLICY_ENGINE"):
            # If we have the policy engine IP from GNS3, use it with the default port
            policy_ip = os.environ.get("NODE_IP_POLICY_ENGINE")
            self.policy_engine_url = f"http://{policy_ip}:5000"
            logger.info(f"Using policy engine URL from NODE_IP_POLICY_ENGINE: {self.policy_engine_url}")
        
        self.policy_auth_token = config.get("policy_auth_token", None)
        if os.environ.get("POLICY_AUTH_TOKEN"):
            self.policy_auth_token = os.environ.get("POLICY_AUTH_TOKEN")
            logger.info("Using policy auth token from POLICY_AUTH_TOKEN env var")
        
        # Policy mode configuration
        self.strict_policy_mode = config.get("strict_policy_mode", True)
        if os.environ.get("STRICT_POLICY_MODE"):
            self.strict_policy_mode = os.environ.get("STRICT_POLICY_MODE").lower() in ("true", "1", "yes")
            logger.info(f"Overriding strict policy mode from STRICT_POLICY_MODE env var: {self.strict_policy_mode}")
        
        # Initialize shared policy client
        self.policy_client = PolicyClient(
            policy_engine_url=self.policy_engine_url,
            auth_token=self.policy_auth_token,
            timeout=5,
            max_retries=1,
            strict_mode=self.strict_policy_mode
        )
        
        # Create results directory if it doesn't exist
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Configure gRPC logging
        enable_grpc_verbose = config.get("enable_grpc_verbose", False)
        configure_grpc_logging(enable_grpc_verbose)
        
        # Stay alive after training flag
        self.stay_alive_after_training = config.get("stay_alive_after_training", False)
        if os.environ.get("STAY_ALIVE_AFTER_TRAINING"):
            self.stay_alive_after_training = os.environ.get("STAY_ALIVE_AFTER_TRAINING").lower() in ("true", "1", "yes")
            logger.info(f"Overriding stay alive setting from env var: {self.stay_alive_after_training}")
        
        # Configure logging
        log_level = config.get("log_level", "INFO")
        if os.environ.get("LOG_LEVEL"):
            log_level = os.environ.get("LOG_LEVEL")
            logger.info(f"Overriding log level from LOG_LEVEL env var: {log_level}")
        
        log_file = config.get("log_file", None)
        if os.environ.get("LOG_FILE"):
            log_file = os.environ.get("LOG_FILE")
            logger.info(f"Overriding log file from LOG_FILE env var: {log_file}")
            
        self._setup_logging(log_level, log_file)
        
        # Client state
        self.client = None
        self.is_running = False
        self.results = {}
        
        # Check policy for training parameters
        if self.policy_engine_url:
            try:
                # Check client training policy for parameters
                context = {
                    "client_id": self.client_id,
                    "operation": "model_training",
                    "model": self.model_name,
                    "dataset": self.dataset
                }
                
                policy_result = self.check_policy("fl_client_training", context)
                
                if policy_result.get("allowed", False):
                    # Extract training parameters from policy
                    parameters = policy_result.get("parameters", {})
                    
                    # Update local epochs if provided in policy
                    if "epochs" in parameters and isinstance(parameters["epochs"], (int, float)):
                        logger.info(f"Updating local_epochs from policy: {parameters['epochs']} (was: {self.local_epochs})")
                        self.local_epochs = int(parameters["epochs"])
                        self.config["local_epochs"] = self.local_epochs
                    
                    # Update batch size if provided in policy
                    if "batch_size" in parameters and isinstance(parameters["batch_size"], (int, float)):
                        logger.info(f"Updating batch_size from policy: {parameters['batch_size']} (was: {self.batch_size})")
                        self.batch_size = int(parameters["batch_size"])
                        self.config["batch_size"] = self.batch_size
                    
                    # Update learning rate if provided in policy
                    if "learning_rate" in parameters and isinstance(parameters["learning_rate"], (int, float)):
                        logger.info(f"Updating learning_rate from policy: {parameters['learning_rate']} (was: {self.learning_rate})")
                        self.learning_rate = float(parameters["learning_rate"])
                        self.config["learning_rate"] = self.learning_rate
                    
                    # Update momentum if provided in policy
                    if "momentum" in parameters and isinstance(parameters["momentum"], (int, float)):
                        logger.info(f"Updating momentum from policy: {parameters['momentum']} (was: {self.momentum})")
                        self.momentum = float(parameters["momentum"])
                        self.config["momentum"] = self.momentum
                
                # Check client evaluation policy for parameters
                context = {
                    "client_id": self.client_id,
                    "operation": "model_evaluation",
                    "model": self.model_name,
                    "dataset": self.dataset
                }
                
                policy_result = self.check_policy("fl_client_evaluation", context)
                
                if policy_result.get("allowed", False):
                    # Extract evaluation parameters from policy
                    parameters = policy_result.get("parameters", {})
                    
                    # Could update evaluation parameters here if needed
                    if "test_size" in parameters and isinstance(parameters["test_size"], (int, float)):
                        logger.info(f"Setting test_size from policy: {parameters['test_size']}")
                        self.config["test_size"] = float(parameters["test_size"])
                
            except Exception as e:
                logger.warning(f"Error checking policy for training parameters: {e}")
                if self.strict_policy_mode:
                    logger.error("Strict policy mode is enabled and policy check failed")
                    raise PolicyEnforcementError(f"Could not check policy for training parameters: {e}")
        
        # Log the full configuration for debugging
        logger.info(f"FL Client initialized with config: {json.dumps(config, indent=2)}")
        logger.info(f"Final effective configuration after policy and environment variable overrides:")
        logger.info(f"  Server Host: {self.server_host}")
        logger.info(f"  Server Port: {self.server_port}")
        logger.info(f"  Client ID: {self.client_id}")
        logger.info(f"  Model: {self.model_name}")
        logger.info(f"  Dataset: {self.dataset}")
        logger.info(f"  Local Epochs: {self.local_epochs}")
        logger.info(f"  Batch Size: {self.batch_size}")
        logger.info(f"  Learning Rate: {self.learning_rate}")
        logger.info(f"  Momentum: {self.momentum}")
        logger.info(f"  Results Dir: {self.results_dir}")
        logger.info(f"  Policy Engine URL: {self.policy_engine_url}")
        logger.info(f"  Strict Policy Mode: {self.strict_policy_mode}")
        logger.info(f"  Log Level: {log_level}")
        logger.info(f"  Log File: {log_file}")
        logger.info(f"  Enable gRPC verbose: {enable_grpc_verbose}")
        logger.info(f"  Stay alive after training: {self.stay_alive_after_training}")
    
    def _setup_logging(self, log_level: str, log_file: Optional[str]) -> None:
        """
        Set up logging configuration.
        
        Args:
            log_level: Logging level
            log_file: Path to log file (if None, logs to stdout)
        """
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        logging_config = {
            'level': numeric_level,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
        
        if log_file:
            # Ensure directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            logging_config['filename'] = log_file
            logging_config['filemode'] = 'a'
        
        logging.basicConfig(**logging_config)
        logger.info(f"Logging configured: level={log_level}, file={log_file or 'stdout'}")
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if the action is allowed by the policy engine.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with policy decision and metadata
        """
        # Add system metrics to context
        system_metrics = self.get_system_metrics()
        return self.policy_client.check_policy(policy_type, context, extra_context=system_metrics)
    
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
            return 0
            
        # Calculate total bytes
        import numpy as np
        from flwr.common import parameters_to_ndarrays
        
        try:
            # If parameters is a Parameters object, convert it to a list of NumPy arrays
            if hasattr(parameters, 'tensors'):
                param_arrays = parameters_to_ndarrays(parameters)
            else:
                param_arrays = parameters
                
            total_bytes = sum(param.nbytes for param in param_arrays)
            return total_bytes
        except Exception as e:
            logger.error(f"Error calculating model size: {e}")
            return 0
    
    def start(self) -> bool:
        """
        Start the FL client.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting FL client: {self.client_id} connecting to {self.server_host}:{self.server_port}")
            
            # Debug DNS resolution
            try:
                import socket
                # Only try DNS resolution if we're not already using an IP address
                if not self.server_host[0].isdigit():
                    server_ip = socket.gethostbyname(self.server_host)
                    logger.info(f"Resolved server host {self.server_host} to IP: {server_ip}")
                    self.server_host = server_ip
                else:
                    logger.info(f"Using direct IP address for server: {self.server_host}")
            except Exception as dns_e:
                logger.warning(f"Failed to resolve server host {self.server_host}: {dns_e}")
                # Don't use a fallback if we're already using an IP from GNS3_IP_MAP
                # This prevents overriding our IP from GNS3_IP_MAP with a potentially incorrect one
                if self.server_host == "fl-server" and "SERVER_IP" in os.environ:
                    logger.info("Using fallback IP from SERVER_IP environment variable")
                    self.server_host = os.environ.get("SERVER_IP")
                    logger.info(f"Fallback server IP: {self.server_host}")
            
            # Check policy before starting
            policy_context = {
                "client_id": self.client_id,
                "client_ip": os.environ.get("CLIENT_IP", "unknown"),
                "server_host": self.server_host,
                "server_port": self.server_port,
                "model": self.model_name,
                "dataset": self.dataset,
                "operation": "client_registration"
            }
            
            policy_result = self.check_policy("fl_client_start", policy_context)
            
            # Verify policy result before proceeding
            if not self.verify_policy_result(policy_result):
                logger.error("Policy verification failed")
                if self.strict_policy_mode:
                    raise PolicyEnforcementError("Policy verification failed")
                return False
            
            if not policy_result.get("allowed", True):
                logger.error(f"Policy violation: {policy_result.get('reason', 'Unknown reason')}")
                if "violations" in policy_result:
                    for violation in policy_result["violations"]:
                        logger.error(f"Violation: {violation}")
                return False
            
            # Create Flower client
            self.client = FlowerClient(self.client_id, self.model_name, self.dataset, self.local_epochs, self)
            
            # Test server connectivity before attempting to start the client
            import socket
            server_address = f"{self.server_host}:{self.server_port}"
            logger.info(f"Testing TCP connectivity to {server_address}")
            
            # Socket test
            s = None
            try:
                host, port = self.server_host, int(self.server_port)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((host, port))
                logger.info(f"Successfully connected to {host}:{port}")
                s.close()
            except Exception as e:
                logger.warning(f"Socket test failed: {e}")
                if s:
                    s.close()
            
            # Set up improved connection options for gRPC
            import grpc
            from concurrent import futures
            
            # Configure gRPC for better reconnect behavior and persistent connections
            # Note: Advanced gRPC options are handled internally by Flower 1.0.0
            # Enhanced persistent connection logic is implemented through reconnection cycles
            
            logger.info(f"Connecting to server at {self.server_host}:{self.server_port} with enhanced options")
            
            # Try to connect with retry logic
            max_retries = int(os.environ.get("MAX_RETRIES", "30"))
            retry_interval = int(os.environ.get("RETRY_INTERVAL", "5"))
            # Remove the reconnection limit for persistent connections
            # max_reconnect_attempts = int(os.environ.get("MAX_RECONNECT_ATTEMPTS", "10"))
            # Set to -1 for infinite reconnection attempts (truly persistent)
            max_reconnect_attempts = int(os.environ.get("MAX_RECONNECT_ATTEMPTS", "-1"))
            reconnect_attempt = 0
            success = False
            
            # Infinite reconnection loop for persistent connections
            while max_reconnect_attempts == -1 or reconnect_attempt <= max_reconnect_attempts:
                connection_attempt = 0
                current_retry_interval = retry_interval  # Reset retry interval for each reconnection cycle
                
                while connection_attempt < max_retries:
                    try:
                        # Start client with enhanced options
                        server_address = f"{self.server_host}:{self.server_port}"
                        if max_reconnect_attempts == -1:
                            logger.info(f"Connection attempt {connection_attempt+1}/{max_retries} (persistent reconnection #{reconnect_attempt+1}) to {server_address}")
                        else:
                            logger.info(f"Connection attempt {connection_attempt+1}/{max_retries} (reconnect {reconnect_attempt+1}/{max_reconnect_attempts}) to {server_address}")
                        
                        # Log connection details
                        logger.info(f"Connecting to {server_address} with client ID: {self.client_id}")
                        
                        # For Flower 1.0.0 compatibility - use grpc_max_message_length instead of grpc_options
                        logger.info("Using Flower 1.0.0 - simplified gRPC configuration")
                        
                        # Create FlowerClient instance for Flower 1.0.0 compatibility  
                        flower_client = FlowerClient(
                            client_id=self.client_id,
                            model_name=self.model_name, 
                            dataset=self.dataset,
                            local_epochs=self.local_epochs,
                            fl_client=self
                        )
                        
                        # Start the client with Flower 1.0.0 compatible parameters
                        fl.client.start_numpy_client(
                            server_address=server_address,
                            client=flower_client,
                            grpc_max_message_length=1024 * 1024 * 1024  # 1 GB for large model support
                        )
                        
                        # If we reach here, the client completed training or disconnected
                        # Check if the server is still accepting connections before reconnecting
                        if max_reconnect_attempts == -1:
                            logger.info(f"Client connection ended, checking server availability before persistent reconnection #{reconnect_attempt+1}")
                        else:
                            logger.info(f"Client connection ended, checking server availability before reconnect ({reconnect_attempt+1}/{max_reconnect_attempts})")
                        
                        # Wait a bit before checking server status
                        time.sleep(2)
                        
                        # Try to check server health to see if we should reconnect
                        try:
                            import requests
                            health_url = f"http://{self.server_host}:8081/health"  # Metrics port for health check
                            response = requests.get(health_url, timeout=5)
                            if response.status_code == 200:
                                health_data = response.json()
                                logger.info(f"Server health check passed: {health_data}")
                                
                                # Check server status to see if it's still training
                                status_url = f"http://{self.server_host}:8081/status"
                                status_response = requests.get(status_url, timeout=5)
                                if status_response.status_code == 200:
                                    status_data = status_response.json()
                                    server_status = status_data.get("server_status", "unknown")
                                    training_stopped = status_data.get("training_stopped_by_policy", False)
                                    
                                    logger.info(f"Server status: {server_status}, training stopped by policy: {training_stopped}")
                                    
                                    # For persistent connections, always try to reconnect unless explicitly stopped
                                    if server_status in ["running", "waiting_for_clients"] and not training_stopped:
                                        logger.info("Server is still training, attempting to reconnect")
                                        reconnect_attempt += 1
                                        # Break the inner connection retry loop since we successfully connected
                                        break
                                    elif server_status == "completed" and max_reconnect_attempts == -1:
                                        logger.info("Server training completed, but persistent mode enabled - continuing to monitor for restart")
                                        reconnect_attempt += 1
                                        break
                                    else:
                                        logger.info(f"Server is not accepting new connections (status: {server_status}), stopping client")
                                        return True  # Exit gracefully
                                else:
                                    logger.warning("Could not get server status, attempting reconnect anyway")
                                    reconnect_attempt += 1
                                    break
                            else:
                                logger.warning(f"Server health check failed with status {response.status_code}")
                                # Try reconnect anyway in case it's a temporary issue
                                reconnect_attempt += 1
                                break
                        except Exception as health_e:
                            logger.warning(f"Could not check server health: {health_e}, attempting reconnect anyway")
                            reconnect_attempt += 1
                            break
                        
                    except Exception as e:
                        logger.warning(f"Connection attempt {connection_attempt+1} failed: {e}")
                        connection_attempt += 1
                        if connection_attempt < max_retries:
                            logger.info(f"Retrying in {current_retry_interval} seconds...")
                            time.sleep(current_retry_interval)
                            # Implement exponential backoff for persistent connections
                            if max_reconnect_attempts == -1:
                                current_retry_interval = min(current_retry_interval * 1.5, 30)  # Cap at 30 seconds
                        else:
                            logger.error(f"Failed to connect after {max_retries} attempts")
                            # For persistent connections, don't raise exception - continue to next reconnection cycle
                            if max_reconnect_attempts == -1:
                                logger.info("Persistent mode enabled - will continue reconnection attempts")
                                break
                            else:
                                raise
                
                # If we've reached the maximum number of reconnection attempts (finite mode), stop trying
                if max_reconnect_attempts != -1 and reconnect_attempt >= max_reconnect_attempts:
                    logger.info(f"Reached maximum reconnection attempts ({max_reconnect_attempts})")
                    break
                
                # If we couldn't connect at all in the inner loop, stop the outer loop only in finite mode
                if connection_attempt >= max_retries and max_reconnect_attempts != -1:
                    break
                
                # For persistent connections, implement longer backoff between reconnection cycles
                if max_reconnect_attempts == -1:
                    backoff_time = min(retry_interval * (1 + reconnect_attempt * 0.1), 60)  # Cap at 1 minute
                    logger.info(f"Persistent mode: waiting {backoff_time:.1f} seconds before next reconnection cycle")
                    time.sleep(backoff_time)
                else:
                    # Wait before reconnecting in finite mode
                    time.sleep(retry_interval)
            
            # If we've successfully connected at least once, consider it a success
            if reconnect_attempt > 0:
                success = True
                if max_reconnect_attempts == -1:
                    logger.info(f"FL client ran in persistent mode with {reconnect_attempt} connection cycles")
                else:
                    logger.info(f"FL client participated in {reconnect_attempt} connection cycles")
            
            # For persistent mode, we only exit if explicitly stopped, so it's always a success
            if max_reconnect_attempts == -1:
                success = True
                logger.info("FL client exiting persistent mode")
            
            if success:
                self.is_running = True
                logger.info("FL client started successfully")
                return True
            else:
                logger.error("Failed to start FL client after all retry attempts")
                return False
            
        except PolicyEnforcementError as e:
            logger.error(f"Policy enforcement failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error starting FL client: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the FL client.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.client:
                # In a real implementation, we would stop the client
                logger.info("Stopping FL client")
                self.is_running = False
                self.client = None
                return True
            else:
                logger.warning("FL client not running")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping FL client: {e}")
            return False

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Collect current system metrics for policy evaluation.
        
        Returns:
            Dictionary containing system metrics
        """
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            available_memory = memory.available // (1024**2)  # MB
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Network IO (basic bandwidth estimation)
            net_io = psutil.net_io_counters()
            
            # Current time info
            now = datetime.now()
            current_hour = now.hour
            
            # Simulate client performance score based on system metrics
            # Better performance = lower CPU/memory usage
            performance_score = max(0.1, 1.0 - (cpu_usage / 100.0 + memory_usage / 100.0) / 2.0)
            
            # Simulate bandwidth (could be enhanced with actual network tests)
            # For now, use a base value modified by system load
            base_bandwidth = 100  # Mbps
            client_bandwidth = base_bandwidth * (1.0 - cpu_usage / 200.0)  # Reduce with high CPU
            
            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "available_memory": available_memory,
                "disk_usage": disk_usage,
                "current_hour": current_hour,
                "client_performance_score": performance_score,
                "client_bandwidth": client_bandwidth,
                "active_clients": 1,  # This client is active
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv
            }
        except Exception as e:
            logger.warning(f"Error collecting system metrics: {e}")
            # Return default/fallback values
            return {
                "cpu_usage": 25.0,
                "memory_usage": 50.0,
                "available_memory": 1024,
                "disk_usage": 30.0,
                "current_hour": datetime.now().hour,
                "client_performance_score": 0.7,
                "client_bandwidth": 50.0,
                "active_clients": 1,
                "bytes_sent": 0,
                "bytes_recv": 0
            }


# FlowerClient class has been moved to src/fl/client/flower_client.py
# and is imported at the top of this module


# Command line interface
def main():
    """Main entry point for the FL client."""
    parser = argparse.ArgumentParser(description="Federated Learning Client")
    parser.add_argument("--server-host", type=str, default=None, help="FL Server Host")
    parser.add_argument("--server-port", type=int, default=None, help="FL Server Port")
    parser.add_argument("--client-id", type=str, default=None, help="Unique Client ID (auto-generated if None)")
    parser.add_argument("--model", type=str, default=None, help="Model name")
    parser.add_argument("--dataset", type=str, default=None, help="Dataset name")
    parser.add_argument("--local-epochs", type=int, default=None, help="Number of local epochs")
    parser.add_argument("--config", type=str, default="./config/client_config.json", help="Path to config file")
    parser.add_argument("--log-level", type=str, default=None, help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--log-file", type=str, default=None, help="Path to log file (optional)")
    parser.add_argument("--policy-engine-url", type=str, default=None, help="Policy Engine URL (overrides config)")
    parser.add_argument("--strict-policy-mode", type=bool, default=None, help="Fail if policy engine unavailable")
    parser.add_argument("--results-dir", type=str, default=None, help="Directory to store results")
    parser.add_argument("--enable-grpc-verbose", action="store_true", help="Enable verbose gRPC logging")
    parser.add_argument("--stay-alive-after-training", action="store_true", help="Keep client alive after training")
    args = parser.parse_args()
    
    # Set up basic logging to see initial messages
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logger.info("Starting FL Client...")
    
    # Get config file path from environment variable if not provided
    config_path = args.config
    if os.environ.get("FL_CONFIG"):
        config_path = os.environ.get("FL_CONFIG")
        logger.info(f"Using config file from FL_CONFIG env var: {config_path}")
    
    # Load config from file
    config = {}
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults and command line args.")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from config file {config_path}. Using defaults.")
    except Exception as e:
        logger.error(f"Unexpected error loading config file: {e}")

    # --- Auto-generate client ID and log file if needed --- 
    client_id_to_use = args.client_id
    log_file_to_use = args.log_file
    
    # Try to get the client ID from environment variables first
    if os.environ.get("CLIENT_ID"):
        client_id_to_use = os.environ.get("CLIENT_ID")
        logger.info(f"Using client ID from CLIENT_ID env var: {client_id_to_use}")
    elif os.environ.get("FL_CLIENT_ID"):
        client_id_to_use = os.environ.get("FL_CLIENT_ID")
        logger.info(f"Using client ID from FL_CLIENT_ID env var: {client_id_to_use}")
    elif not client_id_to_use:
        # If no client ID was specified in environment variables or command line
        try:
            # Use hostname, remove potentially problematic characters
            hostname = socket.gethostname()
            safe_hostname = re.sub(r'[^a-zA-Z0-9_-]', '', hostname)
            client_id_to_use = f"client_{safe_hostname}_{os.getpid()}" 
            logger.info(f"No client ID provided, auto-generated: {client_id_to_use}")
        except Exception as e:
            logger.warning(f"Could not get hostname for auto client ID: {e}. Using random fallback.")
            client_id_to_use = f"client_{uuid.uuid4().hex[:6]}"

    # If log file wasn't specified, try to get it from environment variable
    if os.environ.get("LOG_FILE"):
        log_file_to_use = os.environ.get("LOG_FILE")
        logger.info(f"Using log file from LOG_FILE env var: {log_file_to_use}")
    # Auto-generate log file path if still not set
    elif not log_file_to_use:
        # First, try to determine results dir
        results_dir = args.results_dir or os.environ.get("FL_RESULTS_DIR") or config.get("results_dir", "./results")
        os.makedirs(results_dir, exist_ok=True)
        log_file_to_use = f"{results_dir}/{client_id_to_use}.log"
        logger.info(f"Auto-generating log file path: {log_file_to_use}")
    
    # --- End Auto-generation --- 

    # Build configuration with priority: ENV > command line > config file > defaults
    final_config = {}

    # Helper function to get value with priority
    def get_value(env_var, arg_val, config_key, default):
        if os.environ.get(env_var) is not None:
            return os.environ.get(env_var)
        if arg_val is not None:
            return arg_val
        return config.get(config_key, default)

    # Server host
    final_config["server_host"] = get_value("FL_SERVER_HOST", args.server_host, "server_host", "localhost")
    # Try alternative environment variables
    if final_config["server_host"] == "localhost" and os.environ.get("NODE_IP_FL_SERVER"):
        final_config["server_host"] = os.environ.get("NODE_IP_FL_SERVER")
    
    # Server port
    port_from_env = None
    if os.environ.get("FL_SERVER_PORT"):
        try:
            port_from_env = int(os.environ.get("FL_SERVER_PORT"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid FL_SERVER_PORT: {os.environ.get('FL_SERVER_PORT')}")
    
    final_config["server_port"] = port_from_env if port_from_env else args.server_port if args.server_port else config.get("server_port", 8080)
    
    # Add the rest of the configuration
    final_config["client_id"] = client_id_to_use
    final_config["model"] = get_value("FL_MODEL", args.model, "model", "cnn")
    final_config["dataset"] = get_value("FL_DATASET", args.dataset, "dataset", "mnist")
    
    # Local epochs
    epochs_from_env = None
    if os.environ.get("FL_LOCAL_EPOCHS"):
        try:
            epochs_from_env = int(os.environ.get("FL_LOCAL_EPOCHS"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid FL_LOCAL_EPOCHS: {os.environ.get('FL_LOCAL_EPOCHS')}")
    
    final_config["local_epochs"] = epochs_from_env if epochs_from_env else args.local_epochs if args.local_epochs is not None else config.get("local_epochs", 1)
    
    # Logging
    final_config["log_level"] = get_value("LOG_LEVEL", args.log_level, "log_level", "INFO")
    final_config["log_file"] = log_file_to_use
    
    # Policy engine
    final_config["policy_engine_url"] = get_value("POLICY_ENGINE_URL", args.policy_engine_url, "policy_engine_url", "http://localhost:5000")
    # If we have NODE_IP_POLICY_ENGINE and no specific policy URL, use it
    if final_config["policy_engine_url"] == "http://localhost:5000" and os.environ.get("NODE_IP_POLICY_ENGINE"):
        final_config["policy_engine_url"] = f"http://{os.environ.get('NODE_IP_POLICY_ENGINE')}:5000"
    
    # Get strict policy mode from env with proper boolean conversion
    strict_policy_from_env = None
    if os.environ.get("STRICT_POLICY_MODE"):
        strict_policy_from_env = os.environ.get("STRICT_POLICY_MODE").lower() in ("true", "1", "yes")
    
    final_config["strict_policy_mode"] = strict_policy_from_env if strict_policy_from_env is not None else args.strict_policy_mode if args.strict_policy_mode is not None else config.get("strict_policy_mode", True)
    
    # Results dir
    final_config["results_dir"] = get_value("FL_RESULTS_DIR", args.results_dir, "results_dir", "./results")
    
    # gRPC verbose logging setting
    enable_grpc_verbose_from_env = None
    if os.environ.get("ENABLE_GRPC_VERBOSE"):
        enable_grpc_verbose_from_env = os.environ.get("ENABLE_GRPC_VERBOSE").lower() in ("true", "1", "yes")
    
    final_config["enable_grpc_verbose"] = enable_grpc_verbose_from_env if enable_grpc_verbose_from_env is not None else args.enable_grpc_verbose if args.enable_grpc_verbose is not None else config.get("enable_grpc_verbose", False)
    
    # Stay alive after training
    stay_alive_from_env = None
    if os.environ.get("STAY_ALIVE_AFTER_TRAINING"):
        stay_alive_from_env = os.environ.get("STAY_ALIVE_AFTER_TRAINING").lower() in ("true", "1", "yes")
    
    final_config["stay_alive_after_training"] = stay_alive_from_env if stay_alive_from_env is not None else args.stay_alive_after_training if args.stay_alive_after_training is not None else config.get("stay_alive_after_training", False)

    # Add any additional configuration from environment variables with FL_CONFIG_ prefix
    for key, value in os.environ.items():
        if key.startswith("FL_CONFIG_"):
            config_key = key[10:].lower()  # Remove FL_CONFIG_ prefix and convert to lowercase
            logger.info(f"Adding configuration from environment: {config_key}={value}")
            
            # Try to convert numeric and boolean values
            if value.isdigit():
                final_config[config_key] = int(value)
            elif value.lower() in ("true", "false"):
                final_config[config_key] = value.lower() == "true"
            else:
                final_config[config_key] = value
    
    # Initialize and start client
    logger.info(f"Initializing FL client with final configuration: {json.dumps(final_config, indent=2)}")
    fl_client_instance = FLClient(final_config)
    if fl_client_instance.start():
        logger.info("Client finished successfully.")
        
        # Check if we should stay alive after training
        if fl_client_instance.stay_alive_after_training:
            logger.info("Training completed, but staying alive based on configuration.")
            try:
                while True:
                    time.sleep(60)  # Sleep to keep the process alive, checking every minute
                    # Optionally check for policy changes or other signals to terminate
                    logger.debug("Client still alive, waiting for external termination.")
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down.")
            except Exception as e:
                logger.error(f"Error in stay-alive loop: {e}")
    else:
        logger.error("Client failed to run.")
        sys.exit(1)  # Exit with error code for better container error handling


if __name__ == "__main__":
    main() 