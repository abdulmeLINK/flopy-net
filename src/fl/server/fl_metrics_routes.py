# Copyright 2025 flopy-net Contributors (abdulmeLINK)
# SPDX-License-Identifier: Apache-2.0
"""
FL Server Metrics Routes Module.

Extracted from fl_server.py to reduce file size.
Provides Flask route setup for FL server metrics API.
"""
import datetime
import logging
import threading
import time
from flask import jsonify, request

logger = logging.getLogger(__name__)


class FLMetricsRouteSetup:
    """
    Sets up Flask routes for FL server metrics API.
    
    This class encapsulates all the Flask route definitions that were
    previously inline in FLServer._setup_metrics_routes().
    """
    
    def __init__(self, fl_server):
        """
        Initialize with reference to the FL server.
        
        Args:
            fl_server: The FLServer instance to set up routes for
        """
        self.fl_server = fl_server
        
    def setup_routes(self):
        """Set up all metrics routes on the Flask app."""
        app = self.fl_server.metrics_app
        
        # Register all routes
        self._setup_index_route(app)
        self._setup_metrics_route(app)
        self._setup_health_route(app)
        self._setup_events_route(app)
        self._setup_rounds_routes(app)
        self._setup_training_control_routes(app)
        self._setup_status_route(app)
        
    def _setup_index_route(self, app):
        """Set up the index route."""
        @app.route('/', methods=['GET'])
        def index():
            """Basic index route."""
            return jsonify({"status": "running", "endpoints": ["/health", "/metrics", "/events"]})
    
    def _setup_metrics_route(self, app):
        """Set up the /metrics route."""
        from src.fl.server.fl_server import metrics_lock, global_metrics
        
        @app.route('/metrics', methods=['GET'])
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
    
    def _setup_health_route(self, app):
        """Set up the /health route."""
        @app.route('/health', methods=['GET'])
        def health_check():
            """Basic health check for the metrics server itself."""
            return jsonify({"status": "healthy", "timestamp": time.time()})
    
    def _setup_events_route(self, app):
        """Set up the /events route."""
        fl_server = self.fl_server
        
        @app.route('/events', methods=['GET'])
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
                with fl_server.buffer_lock:
                    # Make a snapshot to work with
                    current_events = list(fl_server.event_buffer)
                    
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
    
    def _setup_rounds_routes(self, app):
        """Set up the /rounds and /rounds/latest routes."""
        from src.fl.server.fl_server import fl_round_storage
        
        @app.route('/rounds', methods=['GET'])
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
        
        @app.route('/rounds/latest', methods=['GET'])
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
    
    def _setup_training_control_routes(self, app):
        """Set up the /restart, /pause, and /resume routes."""
        from src.fl.server.fl_server import metrics_lock, global_metrics
        fl_server = self.fl_server
        
        @app.route('/restart', methods=['POST'])
        def restart_training():
            """Manually restart training if it was stopped by policy or completed."""
            try:
                with metrics_lock:
                    training_stopped = global_metrics.get("training_stopped_by_policy", False)
                    current_round = global_metrics.get("current_round", 0)
                    training_active = global_metrics.get("training_active", False)
                
                # Allow restart if training was stopped by policy OR if training completed but hasn't reached max rounds
                can_restart = training_stopped or (not training_active and current_round < fl_server.rounds)
                
                if not can_restart:
                    return jsonify({
                        "success": False,
                        "message": f"Training cannot be restarted. Current round: {current_round}, Max rounds: {fl_server.rounds}, Training active: {training_active}, Stopped by policy: {training_stopped}"
                    }), 400
                
                # Check if restart is allowed by policy
                restart_allowed = fl_server._check_training_restart_policy()
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
                if fl_server.training_paused:
                    fl_server.resume_training("Manual restart requested via API")
                
                # Log manual restart
                fl_server._log_event("TRAINING_MANUALLY_RESTARTED", {
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
                        fl_server._start_training_loop()
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
        
        @app.route('/pause', methods=['POST'])
        def pause_training_endpoint():
            """Manually pause training."""
            try:
                if fl_server.training_paused:
                    return jsonify({
                        "success": True,
                        "message": "Training is already paused",
                        "training_paused": True,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }), 200
                
                fl_server.pause_training("Manual pause requested via API")
                return jsonify({
                    "success": True,
                    "message": "Training paused successfully",
                    "training_paused": True,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }), 200
                
            except Exception as e:
                logger.error(f"Error pausing training: {e}")
                return jsonify({"error": str(e)}), 500
        
        @app.route('/resume', methods=['POST'])
        def resume_training_endpoint():
            """Manually resume training."""
            try:
                if not fl_server.training_paused:
                    return jsonify({
                        "success": True,
                        "message": "Training is not paused",
                        "training_paused": False,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }), 200
                
                fl_server.resume_training("Manual resume requested via API")
                return jsonify({
                    "success": True,
                    "message": "Training resumed successfully",
                    "training_paused": False,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }), 200
                
            except Exception as e:
                logger.error(f"Error resuming training: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _setup_status_route(self, app):
        """Set up the /status route."""
        from src.fl.server.fl_server import metrics_lock, global_metrics
        fl_server = self.fl_server
        
        @app.route('/status', methods=['GET'])
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
                    restart_allowed = fl_server._check_training_restart_policy()
                
                # Determine more detailed status
                # Use global_metrics server_status if available, fallback to self.server_status
                global_server_status = global_metrics.get("server_status", fl_server.server_status)
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
                    "training_paused": fl_server.training_paused,
                    "pause_reason": global_metrics.get("pause_reason"),
                    "stop_reason": stop_reason,
                    "current_round": current_round,
                    "max_rounds": fl_server.rounds,
                    "restart_allowed": restart_allowed,
                    "connected_clients": connected_clients,
                    "training_active": is_training_active,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error getting training status: {e}")
                return jsonify({"error": str(e)}), 500


def setup_metrics_routes(fl_server):
    """
    Set up metrics routes for an FL server.
    
    This is a convenience function that creates an FLMetricsRouteSetup
    instance and calls setup_routes().
    
    Args:
        fl_server: The FLServer instance to set up routes for
    """
    route_setup = FLMetricsRouteSetup(fl_server)
    route_setup.setup_routes()
