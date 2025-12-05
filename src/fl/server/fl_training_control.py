# Copyright 2025 flopy-net Contributors (abdulmeLINK)
# SPDX-License-Identifier: Apache-2.0
"""
FL Server Training Control Module.

Extracted from fl_server.py to reduce file size.
Provides training lifecycle control (pause, resume, restart, checkpoint).
"""
import datetime
import logging
import os
import pickle
import time
import traceback

logger = logging.getLogger(__name__)


class TrainingControlMixin:
    """
    Mixin class for FLServer that provides training control methods.
    
    This mixin handles:
    - Training pause/resume
    - Training restart after policy stop
    - Policy monitoring for training approval
    - Model checkpoint save/load
    """
    
    def _check_training_restart_policy(self) -> bool:
        """
        Check if training can be restarted based on current policy conditions.
        
        Returns:
            True if training is allowed to restart, False otherwise
        """
        from src.fl.server.fl_server import global_metrics
        
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
        
        This method ensures a complete state reset before restarting:
        1. Cleans up any previous server instance
        2. Resets all state flags
        3. Creates a fresh strategy instance
        4. Starts the training loop
        
        Note: The Flower server binds to a port, so we must ensure the previous
        instance is fully stopped before attempting to restart.
        """
        from src.fl.server.fl_server import metrics_lock, global_metrics
        
        try:
            stopped_round = global_metrics.get("current_round", 0)
            logger.info(f"Restarting FL training from round {stopped_round}...")
            
            # CRITICAL: Clean up previous server instance completely
            if hasattr(self, 'server') and self.server is not None:
                logger.info("Cleaning up previous Flower server instance")
                self.server = None
            
            # Reset strategy to ensure fresh state
            if hasattr(self, 'strategy') and self.strategy is not None:
                logger.info("Resetting strategy instance")
                self.strategy = None
            
            # Reset ALL state flags - this is critical for proper restart
            with metrics_lock:
                global_metrics["training_stopped_by_policy"] = False
                global_metrics["stop_reason"] = None
                global_metrics["training_active"] = False  # Will be set to True when training starts
                global_metrics["training_paused"] = False
                global_metrics["server_status"] = "restarting"
                # Preserve the current round - don't reset to 0
                if "current_round" not in global_metrics:
                    global_metrics["current_round"] = stopped_round
            
            # Reset instance-level flags
            self.server_status = "running"
            self.training_paused = False
            
            # Ensure pause/resume state is reset
            with self.pause_lock:
                self.training_paused = False
            self.resume_event.set()  # Ensure we're not paused
            
            # Ensure server stays alive for restart
            self.stay_alive_after_training = True
            
            # Wait a moment to ensure any previous server instance releases the port
            # This is important because the gRPC server needs time to release the socket
            logger.info("Waiting for port release before restart...")
            time.sleep(3)
            
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
            # Don't leave in a bad state - reset flags
            with metrics_lock:
                global_metrics["training_stopped_by_policy"] = False
                global_metrics["stop_reason"] = f"Restart failed: {str(e)}"

    def _monitor_policy_for_training_approval(self):
        """
        Monitor the policy engine for changes that might allow training.
        
        Returns:
            True if policy allows training, False otherwise
        """
        from src.fl.server.fl_server import global_metrics
        
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
        from src.fl.server.fl_server import metrics_lock, global_metrics
        
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
        from src.fl.server.fl_server import metrics_lock, global_metrics
        
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
