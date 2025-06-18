import os
import sys
import time
import logging
import signal
import requests
import json
import threading
from datetime import datetime
import argparse

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure src is in the path if running directly
if __name__ == "__main__":
    # Adjust path based on where the script is run from relative to src
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.collector.storage import MetricsStorage
from src.collector.policy_monitor import PolicyMonitor
from src.collector.fl_monitor import FLMonitor
from src.collector.network_monitor import NetworkMonitor
from src.collector.event_monitor import EventMonitor

# --- Configuration --- 
# Load .env file if it exists (for local development)
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Log to stdout for container logs
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration Loading Function ---
def load_config(config_path):
    """Load configuration from a JSON file."""
    config = {}
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            
            # Handle nested config structure if present
            if "policy_engine" in config and isinstance(config["policy_engine"], dict):
                policy_engine_config = config["policy_engine"]
                if "url" in policy_engine_config:
                    config["policy_engine_url"] = policy_engine_config["url"]
                    
            if "fl_server" in config and isinstance(config["fl_server"], dict):
                fl_server_config = config["fl_server"]
                if "url" in fl_server_config:
                    config["fl_server_url"] = fl_server_config["url"]
                    
            if "storage" in config and isinstance(config["storage"], dict):
                storage_config = config["storage"]
                if "metrics_output_dir" in storage_config:
                    config["storage_dir"] = storage_config["metrics_output_dir"]
                    
            if "logging" in config and isinstance(config["logging"], dict):
                logging_config = config["logging"]
                if "level" in logging_config:
                    config["log_level"] = logging_config["level"]
                    
            if "features" in config and isinstance(config["features"], dict):
                features = config["features"]
                for feature, enabled in features.items():
                    if feature.endswith("_enabled"):
                        config[feature] = enabled
                        
            if "intervals" in config and isinstance(config["intervals"], dict):
                intervals = config["intervals"]
                for interval, value in intervals.items():
                    if interval.endswith("_sec") or interval.endswith("_min"):
                        config[interval] = value
                        
            if "api" in config and isinstance(config["api"], dict):
                api_config = config["api"]
                if "enabled" in api_config:
                    config["api_enabled"] = api_config["enabled"]
                if "port" in api_config:
                    config["api_port"] = api_config["port"]
            
            logger.info(f"Processed configuration with {len(config)} keys")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
    else:
        logger.warning(f"Config file not found at {config_path}, using environment variables or defaults.")
    return config

# --- Environment Variable Loading / Default Configuration ---
def get_env_bool(var_name, default=False):
    """Helper to get boolean env var."""
    value = os.getenv(var_name, str(default)).lower()
    return value in ('true', '1', 't')

# --- Service URL Determination (will be updated after loading config) ---
# Default values, might be overridden by config or environment variables later
POLICY_ENGINE_URL_DEFAULT = "http://localhost:5000"
FL_SERVER_URL_DEFAULT = "http://localhost:8081" # Update default port to match FL server's actual metrics port

# --- Collector Class ---
class Collector:
    """Orchestrates metric collection from various monitors."""

    def __init__(self, config_path: str = None):
        logger.info("Initializing Collector...")
        
        # Load configuration
        self.config = load_config(config_path)
        
        # Determine Service URLs: Config -> Env Var -> Default
        policy_host = self.config.get("node_ips", {}).get("policy-engine", None)
        policy_port = self.config.get("policy_engine_port", 5000) # Assume default port if not in config
        if policy_host:
            policy_engine_url_from_config = f"http://{policy_host}:{policy_port}"
        else:
            policy_engine_url_from_config = None

        fl_server_host = self.config.get("node_ips", {}).get("fl-server", None)
        # Use FL_SERVER_PORT from environment or fl_server_port from config or default
        fl_server_port = int(os.getenv("FL_SERVER_PORT", self.config.get("fl_server_port", 8081)))
        logger.info(f"Using FL server port from environment/config: {fl_server_port}")
        
        if fl_server_host:
            fl_server_url_from_config = f"http://{fl_server_host}:{fl_server_port}"
            logger.info(f"Using FL server URL from config: {fl_server_url_from_config}")
        else:
            fl_server_url_from_config = None

        self.policy_engine_url = policy_engine_url_from_config or os.getenv("POLICY_ENGINE_URL", POLICY_ENGINE_URL_DEFAULT)
        self.fl_server_url = fl_server_url_from_config or os.getenv("FL_SERVER_URL", FL_SERVER_URL_DEFAULT)
        
        # Get other configurations, prioritizing config file then environment variables/defaults
        self.metrics_output_dir = self.config.get("storage_dir", os.getenv("METRICS_OUTPUT_DIR", "./logs"))
        self.log_level = self.config.get("log_level", os.getenv("LOG_LEVEL", "INFO")).upper() # Update logger level if needed
        
        self.check_policy_enabled = get_env_bool("CHECK_POLICY_ENABLED", self.config.get("check_policy_enabled", True)) # Allow config override
        self.policy_monitor_enabled = get_env_bool("POLICY_MONITOR_ENABLED", self.config.get("policy_monitor_enabled", True))
        self.fl_monitor_enabled = get_env_bool("FL_MONITOR_ENABLED", self.config.get("fl_monitor_enabled", True))
        self.network_monitor_enabled = get_env_bool("NETWORK_MONITOR_ENABLED", self.config.get("network_monitor_enabled", True))
        self.event_monitor_enabled = get_env_bool("EVENT_MONITOR_ENABLED", self.config.get("event_monitor_enabled", True))

        # FL intervals optimized for different training modes
        training_mode = self.config.get("training_mode", os.getenv("TRAINING_MODE", "production")).lower()
        
        if training_mode == "mock" or training_mode == "development":
            # Faster intervals for mock/development training
            self.policy_interval_sec = int(self.config.get("policy_interval_sec", os.getenv("POLICY_INTERVAL_SEC", "15")))  # 15s for mock
            self.fl_interval_sec = int(self.config.get("fl_interval_sec", os.getenv("FL_INTERVAL_SEC", "10")))  # 10s for mock training
            self.network_interval_sec = int(self.config.get("network_interval_sec", os.getenv("NETWORK_INTERVAL_SEC", "30")))  # 30s for mock
            self.event_interval_sec = int(self.config.get("event_interval_sec", os.getenv("EVENT_INTERVAL_SEC", "20")))  # 20s for mock
            logger.info(f"Using mock/development training mode with faster collection intervals")
        else:
            # Production intervals (SQLite optimized)
            self.policy_interval_sec = int(self.config.get("policy_interval_sec", os.getenv("POLICY_INTERVAL_SEC", "60")))  # 60s for production
            self.fl_interval_sec = int(self.config.get("fl_interval_sec", os.getenv("FL_INTERVAL_SEC", "60")))  # 60s for production
            self.network_interval_sec = int(self.config.get("network_interval_sec", os.getenv("NETWORK_INTERVAL_SEC", "180")))  # 180s for production
            self.event_interval_sec = int(self.config.get("event_interval_sec", os.getenv("EVENT_INTERVAL_SEC", "120")))  # 120s for production
            logger.info(f"Using production training mode with optimized collection intervals")
        
        self.training_mode = training_mode

        self.strict_policy_mode = get_env_bool("STRICT_POLICY_MODE", self.config.get("strict_policy_mode", False))

        self.api_enabled = get_env_bool("API_ENABLED", self.config.get("api_enabled", True))
        self.api_host = os.getenv("API_HOST", "0.0.0.0")  # Host to bind the API server
        
        # Get API port from config - prioritize explicit api.port setting
        # Use METRICS_API_PORT to align with server.py, fallback to API_PORT for backwards compatibility
        if 'api' in self.config and isinstance(self.config["api"], dict) and "port" in self.config["api"]:
            self.api_port = int(self.config["api"]["port"])
        else:
            # Check both METRICS_API_PORT (used by server.py) and API_PORT for backwards compatibility
            self.api_port = int(os.getenv("METRICS_API_PORT", os.getenv("API_PORT", "8000")))
            
        logger.info(f"API port set to: {self.api_port}")
        
        # Set METRICS_API_PORT environment variable for consistency with server.py
        os.environ["METRICS_API_PORT"] = str(self.api_port)
        
        # Update logger level based on final config
        logging.getLogger().setLevel(self.log_level)
        logger.info(f"Log level set to {self.log_level}")
        
        logger.info(f"Policy Engine URL set to: {self.policy_engine_url}")
        logger.info(f"FL Server URL set to: {self.fl_server_url}")
        
        # Initialize storage with SQLite optimization settings
        self.storage = MetricsStorage(
            output_dir=self.metrics_output_dir,
            db_name="metrics.db",         # SQLite database file
            max_age_days=14,              # Keep data for 2 weeks (increased for dashboard charts)
            cleanup_interval_hours=12     # Cleanup twice daily
        )
        self.scheduler = BlockingScheduler(timezone="UTC")
        self.policy_monitor = None
        self.fl_monitor = None
        self.network_monitor = None
        self.event_monitor = None
        
        # API app
        self.api_app = None
        self.api_thread = None

        self._setup_monitors()
        self._setup_scheduler()
        
        if self.api_enabled:
            self._setup_api()

    def _setup_monitors(self):
        """Set up monitors for different components with SQLite optimizations."""
        logger.info("Setting up monitors...")
        
        if self.policy_monitor_enabled:
            self.policy_monitor = PolicyMonitor(self.policy_engine_url, self.storage)
            logger.info("Policy monitor initialized")
        
        if self.fl_monitor_enabled:
            # Use SQLite optimized FL monitor with configured interval
            self.fl_monitor = FLMonitor(
                self.fl_server_url, 
                self.storage,
                collection_interval=self.fl_interval_sec,
                training_mode=self.training_mode  # Pass training mode for adaptive behavior
            )
            logger.info(f"FL monitor initialized with {self.fl_interval_sec}s interval for {self.training_mode} mode")
        
        if self.network_monitor_enabled:
            # Get SDN controller URL from config file or environment variable
            sdn_controller_url = self.config.get("sdn_controller_url", os.getenv("SDN_CONTROLLER_URL"))
            if not sdn_controller_url:
                # Fallback for docker-compose environment from service name
                sdn_controller_host = os.getenv("SDN_CONTROLLER_HOST", "sdn-controller")
                sdn_controller_port = os.getenv("SDN_CONTROLLER_PORT", "8181")
                sdn_controller_url = f"http://{sdn_controller_host}:{sdn_controller_port}"
            
            try:
                self.network_monitor = NetworkMonitor(
                    storage=self.storage,
                    sdn_controller_url=sdn_controller_url
                )
                logger.info(f"Network monitor initialized with SDN Controller at {sdn_controller_url}")
            except ValueError as e:
                logger.error(f"Network monitor initialization failed: {e}")
                self.network_monitor_enabled = False
                self.network_monitor = None
        
        if self.event_monitor_enabled:
            # Get SDN controller configuration for event monitoring
            sdn_controller_host = self.config.get("sdn_controller_host", os.getenv("SDN_CONTROLLER_HOST", "sdn-controller"))
            sdn_controller_port = self.config.get("sdn_controller_port", int(os.getenv("SDN_CONTROLLER_PORT", "8181")))
            
            if not sdn_controller_host or sdn_controller_host == "sdn-controller":
                node_ip_sdn = os.getenv("NODE_IP_SDN_CONTROLLER")
                if node_ip_sdn:
                    sdn_controller_host = node_ip_sdn
                    logger.info(f"Using SDN controller IP from NODE_IP_SDN_CONTROLLER: {sdn_controller_host}")
            
            self.event_monitor = EventMonitor(
                storage=self.storage,
                fl_server_url=self.fl_server_url,
                policy_engine_url=self.policy_engine_url,
                network_monitor=self.network_monitor, # Pass the network monitor instead of gns3_monitor
                sdn_controller_host=sdn_controller_host,
                sdn_controller_port=sdn_controller_port
            )
            logger.info(f"Event monitor initialized with SDN controller at {sdn_controller_host}:{sdn_controller_port}")
        
        logger.info("All enabled monitors initialized with SQLite optimizations")

    def _setup_api(self):
        """Set up the collector API."""
        logger.info(f"Setting up collector API on {self.api_host}:{self.api_port}...")
        
        # Import and use the existing API server from server.py instead of creating a new Flask app
        try:
            from src.collector.api.server import api_bp, storage as api_storage
            
            # Update the API storage to use our configured storage
            api_storage.output_dir = self.metrics_output_dir
            
            # Pass network monitor reference to API storage for live topology queries
            if self.network_monitor_enabled and self.network_monitor:
                api_storage.network_monitor = self.network_monitor
                logger.info("Network monitor reference passed to API server")
            
            logger.info("Successfully imported API blueprint from server.py")
            
            # Create minimal Flask app to run the imported blueprint
            app = Flask(__name__)
            
            # Add CORS support if needed
            CORS(app, origins="*")
            
            # Register the comprehensive API blueprint
            app.register_blueprint(api_bp, url_prefix='/api')
            
            # Add a few collector-specific endpoints
            @app.route('/health', methods=['GET'])
            def health_check():
                """Health check endpoint."""
                return jsonify({
                    'status': 'ok', 
                    'timestamp': datetime.now().isoformat(),
                    'collector_version': 'v1.0.0',
                    'monitors': {
                        'policy': self.policy_monitor_enabled,
                        'fl': self.fl_monitor_enabled,
                        'network': self.network_monitor_enabled,
                        'events': self.event_monitor_enabled
                    }
                })
            
            @app.route('/status', methods=['GET'])
            def collector_status():
                """Collector status endpoint."""
                return jsonify({
                    'collector_running': True,
                    'api_port': self.api_port,
                    'storage_dir': self.metrics_output_dir,
                    'training_mode': self.training_mode,
                    'intervals': {
                        'policy_sec': self.policy_interval_sec if self.policy_monitor_enabled else None,
                        'fl_sec': self.fl_interval_sec if self.fl_monitor_enabled else None,
                        'network_sec': self.network_interval_sec if self.network_monitor_enabled else None,
                        'event_sec': self.event_interval_sec if self.event_monitor_enabled else None
                    },
                    'urls': {
                        'policy_engine': self.policy_engine_url if self.policy_monitor_enabled else None,
                        'fl_server': self.fl_server_url if self.fl_monitor_enabled else None
                    }
                })
            
            self.api_app = app
            
            # Start API in a separate thread
            def run_api():
                try:
                    app.run(host=self.api_host, port=self.api_port, debug=False, use_reloader=False, threaded=True)
                except Exception as e:
                    logger.error(f"Error running API server: {e}")
            
            self.api_thread = threading.Thread(target=run_api, daemon=True)
            self.api_thread.start()
            logger.info(f"Collector API server started in background thread on {self.api_host}:{self.api_port}")
            
        except ImportError as e:
            logger.error(f"Failed to import API blueprint: {e}")
            logger.info("Falling back to basic API setup...")
            
            # Fallback to basic API if server.py import fails
            app = Flask(__name__)
            
            @app.route('/health', methods=['GET'])
            def health_check():
                return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})
                
            @app.route('/api/metrics/fl/status', methods=['GET'])
            def fl_status():
                if self.fl_monitor:
                    try:
                        status = self.fl_monitor.get_training_status()
                        return jsonify(status)
                    except Exception as e:
                        return jsonify({'error': str(e)}), 500
                return jsonify({'error': 'FL monitor not enabled'}), 503
            
            self.api_app = app
            
            def run_api():
                try:
                    app.run(host=self.api_host, port=self.api_port, debug=False, use_reloader=False)
                except Exception as e:
                    logger.error(f"Error running fallback API server: {e}")
            
            self.api_thread = threading.Thread(target=run_api, daemon=True)
            self.api_thread.start()
            logger.info(f"Fallback collector API started on {self.api_host}:{self.api_port}")
            
        except Exception as e:
            logger.error(f"Error setting up collector API: {e}")
            logger.warning("Collector will run without API")

    def _scheduler_listener(self, event):
        """Listen for scheduler events (errors)."""
        if event.exception:
            job = self.scheduler.get_job(event.job_id)
            logger.error(f"Job '{job.name}' raised an exception: {event.exception}")
            # Potentially add logic here to handle repeated job failures
        # else:
        #     logger.debug(f"Job '{event.job_id}' executed successfully")

    def _setup_scheduler(self):
        """Set up the APScheduler for metric collection with event-based FL monitoring."""
        logger.info("Setting up scheduler...")
        
        # Set up a listener for job events
        self.scheduler.add_listener(self._scheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Schedule policy metrics collection
        if self.policy_monitor_enabled and self.policy_monitor:
            self.scheduler.add_job(
                func=self._collect_policy_metrics, 
                trigger="interval", 
                seconds=self.policy_interval_sec,
                id="policy_metrics"
            )
            logger.info(f"Policy metrics collection scheduled every {self.policy_interval_sec} seconds")
        
        # Start event-based FL metrics monitoring (no scheduler needed)
        if self.fl_monitor_enabled and self.fl_monitor:
            # Start the FL monitor's internal event-based monitoring thread
            self.fl_monitor.start_monitoring()
            logger.info(f"FL event-based monitoring started (replaces scheduled collection)")
        
        # Schedule network metrics collection (less frequent for resource optimization)
        if self.network_monitor_enabled and self.network_monitor:
            self.scheduler.add_job(
                func=self._collect_network_metrics, 
                trigger="interval", 
                seconds=self.network_interval_sec,
                id="network_metrics"
            )
            logger.info(f"Network metrics collection scheduled every {self.network_interval_sec} seconds")
        
        # Schedule event collection (less frequent for resource optimization)
        if self.event_monitor_enabled and self.event_monitor:
            self.scheduler.add_job(
                func=self._collect_events, 
                trigger="interval", 
                seconds=self.event_interval_sec,
                id="event_collection"
            )
            logger.info(f"Event collection scheduled every {self.event_interval_sec} seconds")
        
        logger.info("Scheduler setup completed with event-based FL monitoring")

    def _collect_policy_metrics(self):
        """Collect policy metrics and store them."""
        if self.policy_monitor:
            try:
                metrics = self.policy_monitor.collect_metrics()
                self.storage.store_metric("policy_engine", metrics)
                logger.debug("Policy metrics collection completed successfully")
            except Exception as e:
                logger.error(f"Error collecting policy metrics: {e}")
                # Store error state
                self.storage.store_metric("policy_engine", {
                    "status": "error",
                    "timestamp": time.time(),
                    "error": str(e)
                })

    def _collect_network_metrics(self):
        """Collect network metrics and store them."""
        if self.network_monitor:
            try:
                metrics = self.network_monitor.collect_metrics()
                self.storage.store_metric("network", metrics)
                logger.debug("Network metrics collection completed successfully")
            except Exception as e:
                logger.error(f"Error collecting network metrics: {e}")
                # Store error state
                self.storage.store_metric("network", {
                    "status": "error",
                    "timestamp": time.time(),
                    "error": str(e)
                })

    def _collect_events(self):
        """Collect events from various components."""
        if self.event_monitor:
            try:
                self.event_monitor.collect_metrics()
                logger.debug("Event collection completed successfully")
            except Exception as e:
                logger.error(f"Error collecting events: {e}")
                # Store error event
                error_event = {
                    "event_id": str(time.time()),
                    "timestamp": datetime.now().isoformat(),
                    "source_component": "COLLECTOR",
                    "component": "COLLECTOR",
                    "event_type": "ERROR",
                    "type": "ERROR",
                    "event_level": "ERROR",
                    "level": "ERROR",
                    "details": {"error": str(e), "context": "event_collection"}
                }
                self.storage.store_event(error_event)

    def check_policy(self) -> bool:
        """Check with the Policy Engine if collection is allowed."""
        if not self.check_policy_enabled:
            logger.info("Policy checks disabled. Proceeding with collection.")
            return True
        
        try:
            check_url = f"{self.policy_engine_url}/check"
            logger.info(f"Performing policy check against {check_url}...")
            params = {
                "component": "collector",
                "action": "collect_metrics"
            }
            
            response = requests.get(
                check_url, 
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("allowed", False):
                    logger.info(f"Policy check successful: {result.get('reason', 'No reason provided')}")
                    return True
                else:
                    logger.warning(f"Policy check denied: {result.get('reason', 'No reason provided')}")
                    return False
            else:
                logger.error(f"Policy check failed. Status code: {response.status_code}")
                if self.check_policy_enabled and self.strict_policy_mode:
                    logger.error("Strict policy mode enabled. Aborting collection due to policy check failure.")
                    return False
                else:
                    logger.warning("Bypassing policy check due to error response from Policy Engine")
                    return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Policy Engine for policy check at {self.policy_engine_url}/check: {e}")
            logger.warning("Bypassing policy check due to connection error to Policy Engine")
            return True
        except Exception as e:
            logger.error(f"Unexpected error during policy check: {e}")
            logger.warning("Bypassing policy check due to unexpected error")
            return True

    def run(self):
        """Start the collector and the scheduler."""
        logger.info("Starting Collector...")
        
        # Check policy before starting scheduler
        if not self.check_policy():
             logger.error("Collector startup aborted due to policy denial or check failure.")
             self.shutdown()
             return # Exit if not allowed

        # Add signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        try:
            logger.info("Starting metric collection scheduler. Press Ctrl+C to exit.")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler interrupted.")
        finally:
            self.shutdown()

    def _handle_signal(self, signum, frame):
        """Handle termination signals gracefully."""
        logger.warning(f"Received signal {signum}. Shutting down...")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False) # Don't wait for running jobs
        # No explicit sys.exit needed, shutdown() handles cleanup

    def shutdown(self):
        """Shutdown the collector and release resources."""
        logger.info("Shutting down collector...")
        
        # Stop FL monitoring if running
        if self.fl_monitor_enabled and self.fl_monitor:
            try:
                self.fl_monitor.stop_monitoring()
                logger.info("FL monitoring stopped.")
            except Exception as e:
                logger.error(f"Error stopping FL monitoring: {e}")
        
        try:
            self.storage.close()
            logger.info("Storage connections closed.")
        except Exception as e:
            logger.error(f"Error while closing storage: {e}")
            
        logger.info("Collector shutdown complete.")

# --- Main Execution --- 
def main():
    """Main entry point for the collector service."""
    parser = argparse.ArgumentParser(description="Metrics Collector Service")
    parser.add_argument("--config", help="Path to the JSON configuration file")
    args = parser.parse_args()

    logger.info("Starting Metrics Collector...")
    collector = Collector(config_path=args.config) # Pass config path to constructor
    
    # Setup signal handling for graceful shutdown
    signal.signal(signal.SIGINT, collector._handle_signal)
    signal.signal(signal.SIGTERM, collector._handle_signal)

    try:
        collector.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
        collector.shutdown()
    except Exception as e:
        logger.critical(f"Unhandled exception in collector main loop: {e}", exc_info=True)
        collector.shutdown()
        sys.exit(1)
    
    logger.info("Collector shutdown complete.")
    sys.exit(0)

if __name__ == "__main__":
    main() 