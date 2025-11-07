#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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

import requests
import logging
import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

from .storage import MetricsStorage

logger = logging.getLogger(__name__)

class FLMonitor:
    """Event-based monitor for Federated Learning metrics that tracks FL server events and rounds."""
    
    def __init__(self, fl_server_url: str, storage_instance, collection_interval: int = 60, training_mode: str = "production"):
        """
        Initialize the FLMonitor with event-based collection.
        
        Args:
            fl_server_url: URL of the FL server to monitor
            storage_instance: Storage instance for metrics
            collection_interval: Check interval for new events (reduced importance with event-based collection)
            training_mode: 'mock'/'development' for faster checks, 'production' for optimized checks
        """
        self.fl_server_url = fl_server_url
        self.storage = storage_instance
        self.training_mode = training_mode.lower()
        
        # Event-based collection reduces the importance of interval timing
        if self.training_mode in ["mock", "development"]:
            self.collection_interval = min(collection_interval, 5)  # Check every 5s for new events
            logger.info(f"FL Monitor configured for {self.training_mode} mode with {self.collection_interval}s event check interval")
        else:
            self.collection_interval = max(collection_interval, 10)  # Check every 10s for new events  
            logger.info(f"FL Monitor configured for production mode with {self.collection_interval}s event check interval")
        
        self.running = False
        self._monitor_thread = None
        self._error_count = 0
        self._max_errors = 10 if self.training_mode in ["mock", "development"] else 5
        
        # Event-based tracking state
        self._last_event_id = None  # Track last processed FL server event
        self._known_rounds: Set[int] = set()  # Track processed rounds to avoid duplicates
        self._last_round_check = 0  # Last round number we checked
        self._training_complete = False
        
        # Remove trailing slash for consistent endpoint URLs
        if self.fl_server_url.endswith('/'):
            self.fl_server_url = self.fl_server_url[:-1]
        
        # FL server endpoints
        self.health_endpoint = f"{self.fl_server_url}/health"
        self.events_endpoint = f"{self.fl_server_url}/events"
        self.rounds_endpoint = f"{self.fl_server_url}/rounds"
        self.rounds_latest_endpoint = f"{self.fl_server_url}/rounds/latest"
        self.status_endpoint = f"{self.fl_server_url}/status"
        
        # HTTP session for connection reuse
        self.session = requests.Session()
        self.session.timeout = 10
        
        logger.info(f"FL Monitor initialized for event-based collection from {fl_server_url}")

    def start_monitoring(self):
        """Start the event-based FL monitoring in a separate thread."""
        if self.running:
            logger.warning("FL monitoring is already running")
            return
            
        self.running = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("FL event-based monitoring started")

    def stop_monitoring(self):
        """Stop the FL monitoring."""
        self.running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("FL monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop that checks for new events and rounds."""
        logger.info("FL Monitor: Starting event-based monitoring loop")
        
        while self.running:
            try:
                # First check FL server health
                if not self._check_server_health():
                    logger.debug("FL server not available, skipping this cycle")
                    time.sleep(self.collection_interval)
                    continue
                
                # Collect new events from FL server
                events_collected = self._collect_fl_events()
                
                # Collect new/updated rounds from FL server
                rounds_collected = self._collect_fl_rounds()
                
                # Reset error count on successful collection
                if events_collected >= 0 or rounds_collected >= 0:
                    self._error_count = 0
                
                logger.debug(f"FL Monitor: Collected {events_collected} events, {rounds_collected} rounds")
                
            except Exception as e:
                self._error_count += 1
                logger.error(f"FL Monitor: Error in monitoring loop: {e}")
                
                if self._error_count >= self._max_errors:
                    logger.error(f"FL Monitor: Too many errors ({self._error_count}), stopping monitoring")
                    self.running = False
                    break
                    
            # Sleep before next check
            if self.running:
                time.sleep(self.collection_interval)
        
        logger.info("FL Monitor: Monitoring loop ended")

    def _check_server_health(self) -> bool:
        """Quick health check of FL server."""
        try:
            response = self.session.get(self.health_endpoint, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _collect_fl_events(self) -> int:
        """
        Collect new events from FL server.
        
        Returns:
            Number of events collected, -1 on error
        """
        try:
            # Build events URL with since_event_id parameter if we have it
            url = self.events_endpoint
            params = {"limit": 100}  # Reasonable batch size
            
            if self._last_event_id:
                params["since_event_id"] = self._last_event_id
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"FL events endpoint returned {response.status_code}")
                return -1
            
            data = response.json()
            events = data.get("events", [])
            last_event_id = data.get("last_event_id")
            
            # Process and store events
            events_stored = 0
            for event in events:
                if self._process_fl_event(event):
                    events_stored += 1
            
            # Update last event ID
            if last_event_id:
                self._last_event_id = last_event_id
            
            logger.debug(f"FL Monitor: Processed {events_stored}/{len(events)} FL events")
            return events_stored
            
        except Exception as e:
            logger.error(f"FL Monitor: Error collecting FL events: {e}")
            return -1

    def _process_fl_event(self, event: Dict[str, Any]) -> bool:
        """
        Process a single FL server event and extract relevant training information.
        
        Args:
            event: FL server event data
            
        Returns:
            True if event was processed and stored, False otherwise
        """
        try:
            event_type = event.get("event_type", "")
            details = event.get("details", {})
            
            # Store FL server events for audit trail and debugging
            logger.info(f"FL Monitor: Raw event details received: {details}")
            self.storage.store_event({
                "event_id": event.get("event_id"),
                "timestamp": event.get("timestamp"),
                "source_component": "FL_SERVER",
                "component": "FL_SERVER",
                "event_type": event_type,
                "type": event_type,
                "event_level": "INFO",
                "level": "INFO", 
                "details": details,
                "fl_monitor_processed": True
            })
            
            # Process training-relevant events for additional metrics
            if event_type in ["ROUND_START", "ROUND_END", "AGGREGATION_END", "TRAINING_COMPLETE"]:
                round_num = details.get("round_number", 0)
                
                if event_type == "ROUND_END" and round_num > 0:
                    # Extract round completion metrics if available
                    round_metrics = {
                        "timestamp": event.get("timestamp"),
                        "round": round_num,
                        "status": "complete",
                        "event_source": "fl_server_event",
                        "global_metrics": details.get("global_metrics", {}),
                        "model_version": details.get("model_version", f"round_{round_num}")
                    }
                    
                    # Store as individual round metric
                    self.storage.store_metric(f"fl_round_{round_num}_event", round_metrics)
                    logger.debug(f"FL Monitor: Stored round {round_num} completion event")
                
                elif event_type == "TRAINING_COMPLETE":
                    self._training_complete = True
                    # Store training completion metric
                    completion_metrics = {
                        "timestamp": event.get("timestamp"),
                        "status": "training_complete",
                        "event_source": "fl_server_event",
                        "total_rounds": details.get("total_rounds", 0),
                        "total_duration_sec": details.get("total_duration_sec", 0),
                        "final_metrics": details.get("final_metrics", {})
                    }
                    self.storage.store_metric("fl_training_completion", completion_metrics)
                    logger.info("FL Monitor: Training completion detected via events")
            
            return True
            
        except Exception as e:
            logger.error(f"FL Monitor: Error processing FL event: {e}")
            return False

    def _collect_fl_rounds(self) -> int:
        """
        Collect new/updated rounds from FL server's rounds endpoint.
        
        Returns:
            Number of rounds collected, -1 on error
        """
        try:
            # First, check what's the latest round available
            latest_response = self.session.get(self.rounds_latest_endpoint, params={"limit": 1}, timeout=10)
            
            if latest_response.status_code != 200:
                logger.debug(f"FL rounds/latest endpoint returned {latest_response.status_code}")
                return 0  # Not critical, FL server might not have rounds yet
            
            latest_data = latest_response.json()
            latest_rounds = latest_data.get("rounds", [])
            latest_round_number = latest_data.get("latest_round", 0)
            
            if not latest_rounds or latest_round_number <= self._last_round_check:
                logger.debug(f"FL Monitor: No new rounds (latest: {latest_round_number}, last checked: {self._last_round_check})")
                return 0
            
            # Get new rounds since our last check
            start_round = max(1, self._last_round_check + 1)
            params = {
                "start_round": start_round,
                "end_round": latest_round_number,
                "limit": latest_round_number - start_round + 1
            }
            
            rounds_response = self.session.get(self.rounds_endpoint, params=params, timeout=15)
            
            if rounds_response.status_code != 200:
                logger.warning(f"FL rounds endpoint returned {rounds_response.status_code}")
                return -1
            
            rounds_data = rounds_response.json()
            rounds = rounds_data.get("rounds", [])
            
            # Process new rounds
            rounds_stored = 0
            for round_data in rounds:
                round_num = round_data.get("round", 0)
                
                # Skip already processed rounds
                if round_num in self._known_rounds:
                    continue
                
                if self._process_fl_round(round_data):
                    rounds_stored += 1
                    self._known_rounds.add(round_num)
            
            # Update our tracking
            self._last_round_check = latest_round_number
            
            logger.debug(f"FL Monitor: Processed {rounds_stored} new rounds (latest: {latest_round_number})")
            return rounds_stored
            
        except Exception as e:
            logger.error(f"FL Monitor: Error collecting FL rounds: {e}")
            return -1

    def _process_fl_round(self, round_data: Dict[str, Any]) -> bool:
        """
        Process a single FL round and store comprehensive metrics.
        
        Args:
            round_data: FL round data from server
            
        Returns:
            True if round was processed and stored, False otherwise
        """
        try:
            round_num = round_data.get("round", 0)
            
            if round_num <= 0:
                return False
            
            logger.info(f"FL Monitor: Raw round_data received for round {round_num}: {round_data}")
            
            # Extract model size with detailed logging and proper conversion
            model_size_mb = round_data.get("model_size_mb", 0.0)
            
            # Ensure model_size_mb is properly converted to float
            try:
                if model_size_mb is None:
                    model_size_mb = 0.0
                elif isinstance(model_size_mb, str):
                    model_size_mb = float(model_size_mb) if model_size_mb else 0.0
                else:
                    model_size_mb = float(model_size_mb)
            except (ValueError, TypeError):
                logger.warning(f"FL Monitor: Invalid model_size_mb value '{model_size_mb}' for round {round_num}, using 0.0")
                model_size_mb = 0.0
                
            logger.info(f"FL Monitor: Round {round_num} model_size_mb extracted: {model_size_mb} (type: {type(model_size_mb)})")
            
            # Extract training duration properly
            training_duration = round_data.get("training_duration", 0.0)
            try:
                training_duration = float(training_duration) if training_duration is not None else 0.0
            except (ValueError, TypeError):
                training_duration = 0.0
            
            # Extract clients count properly 
            clients_count = round_data.get("clients", round_data.get("clients_connected", 0))
            try:
                clients_count = int(clients_count) if clients_count is not None else 0
            except (ValueError, TypeError):
                clients_count = 0
            
            # Determine proper status based on training state
            status = "complete"  # Default to complete for finished rounds
            if not self._training_complete and round_num == self._last_round_check:
                status = "training"  # Only current round should show as training
            
            # Store detailed round metrics - FIXED: Only store once per round
            processed_round = {
                "timestamp": round_data.get("timestamp", datetime.now().isoformat()),
                "round": round_num,
                "status": status,
                "accuracy": round_data.get("accuracy", 0.0),
                "loss": round_data.get("loss", 0.0),
                "training_duration": training_duration,
                "model_size_mb": model_size_mb,
                "clients": clients_count,
                "clients_connected": clients_count,  # Ensure both fields are set
                "data_source": "fl_server_rounds",
                "raw_metrics": round_data.get("raw_metrics", {}),
                "training_complete": self._training_complete
            }
            
            logger.info(f"FL Monitor: Processed round {round_num} - model_size_mb: {processed_round['model_size_mb']}, clients: {clients_count}, status: {status}")
            
            # Store as individual round metric with unique key
            self.storage.store_metric(f"fl_round_{round_num}", processed_round)
            
            logger.debug(f"FL Monitor: Stored round {round_num} (accuracy: {processed_round['accuracy']:.4f}, loss: {processed_round['loss']:.4f}, model_size: {model_size_mb:.6f} MB, clients: {clients_count})")
            return True
            
        except Exception as e:
            logger.error(f"FL Monitor: Error processing FL round: {e}")
            return False

    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect current FL metrics for immediate dashboard requests.
        This provides a snapshot of current state for synchronous API calls.
        """
        try:
            # Get current FL server status
            health_response = self.session.get(self.health_endpoint, timeout=5)
            
            if health_response.status_code != 200:
                return {
                    "status": "unavailable",
                    "timestamp": time.time(),
                    "error": f"FL server health check failed: {health_response.status_code}",
                    "data_source": "fl_monitor_event_based"
                }
            
            # Get detailed status from FL server's /status endpoint
            status_response = self.session.get(self.status_endpoint, timeout=5)
            server_status_data = {}
            if status_response.status_code == 200:
                server_status_data = status_response.json()

            # Get latest rounds for current state
            latest_response = self.session.get(self.rounds_latest_endpoint, params={"limit": 5}, timeout=10)
            
            if latest_response.status_code == 200:
                latest_data = latest_response.json()
                rounds = latest_data.get("rounds", [])
                latest_round_number = latest_data.get("latest_round", 0)
                
                # Determine detailed status
                fl_status = server_status_data.get("server_status", "training")
                if server_status_data.get("training_stopped_by_policy"):
                    fl_status = "stopped_by_policy"
                elif server_status_data.get("training_paused"):
                    fl_status = "paused"
                elif self._training_complete:
                    fl_status = "training_complete"

                # Build current state from latest rounds
                current_metrics = {
                    "status": fl_status,
                    "timestamp": time.time(),
                    "current_round": latest_round_number,
                    "connected_clients": 0,
                    "training_complete": self._training_complete,
                    "data_state": fl_status, # Use the more detailed status
                    "data_source": "fl_monitor_event_based",
                    "rounds_history": rounds,
                    "server_status_details": server_status_data
                }
                
                # Extract metrics from latest completed round
                if rounds:
                    latest_round = rounds[0]  # rounds are returned latest first
                    current_metrics.update({
                        "accuracy": latest_round.get("accuracy", 0.0),
                        "loss": latest_round.get("loss", 0.0),
                        "connected_clients": latest_round.get("clients", 0),
                        "model_size_mb": latest_round.get("model_size_mb", 0.0),
                        "last_round_metrics": {
                            "round": latest_round.get("round", 0),
                            "accuracy": latest_round.get("accuracy", 0.0),
                            "loss": latest_round.get("loss", 0.0),
                            "training_duration": latest_round.get("training_duration", 0.0),
                            "timestamp": latest_round.get("timestamp")
                        }
                    })
                
                # If no rounds, get client count from status
                if not rounds and "connected_clients" in server_status_data:
                    current_metrics["connected_clients"] = server_status_data["connected_clients"]

                # Calculate training stats if we have multiple rounds
                if len(rounds) > 1:
                    accuracies = [r.get("accuracy", 0) for r in rounds if r.get("accuracy", 0) > 0]
                    if accuracies:
                        current_metrics["training_stats"] = {
                            "total_completed_rounds": len(accuracies),
                            "best_accuracy": max(accuracies),
                            "latest_accuracy": accuracies[0] if accuracies else 0,
                            "average_accuracy": sum(accuracies) / len(accuracies)
                        }
                
                logger.debug(f"FL Monitor: Current metrics - Round {latest_round_number}, Status: {fl_status}")
                return current_metrics
            
            else:
                return {
                    "status": "available",
                    "timestamp": time.time(),
                    "current_round": 0,
                    "training_complete": False,
                    "data_state": "initializing",
                    "error": f"Rounds endpoint returned {latest_response.status_code}",
                    "data_source": "fl_monitor_event_based",
                    "server_status_details": server_status_data
                }
                
        except Exception as e:
            logger.warning(f"FL Monitor: Error collecting current metrics: {e}")
            return {
                "status": "error",
                "timestamp": time.time(),
                "error": f"Collection error: {str(e)}",
                "data_source": "fl_monitor_event_based"
            }

    def check_server_health(self) -> bool:
        """Public method to check if the FL server is healthy."""
        return self._check_server_health()

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        return {
            "running": self.running,
            "training_mode": self.training_mode,
            "collection_interval": self.collection_interval,
            "error_count": self._error_count,
            "last_event_id": self._last_event_id,
            "known_rounds_count": len(self._known_rounds),
            "last_round_check": self._last_round_check,
            "training_complete": self._training_complete,
            "fl_server_url": self.fl_server_url
        }