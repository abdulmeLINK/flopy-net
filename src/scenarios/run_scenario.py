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
Run a specific federated learning scenario with configuration.
"""

import os
import sys
import argparse
import logging
import json
import uuid
import time
from typing import Dict, Any, List, Optional
import importlib
from datetime import datetime
import threading

# Add the project root to Python path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import scenario discovery and loading functionality
try:
    # First try relative import if running as a package
    from .common import SCENARIOS, load_scenario
except ImportError:
    # Otherwise try absolute import
    from src.scenarios.common import SCENARIOS, load_scenario

# Import metrics service
try:
    from src.metrics.metrics_service import MetricsService
    metrics_service = MetricsService()
except ImportError:
    metrics_service = None
    print("Warning: MetricsService not available")

# Import serialization helper
try:
    # First try relative import if running as a package
    from .serialization_helper import make_scenario_serializable, make_all_scenarios_serializable
except ImportError:
    # Otherwise try absolute import
    from src.scenarios.serialization_helper import make_scenario_serializable, make_all_scenarios_serializable

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dictionary to store running scenarios status
_running_scenarios = {}

def get_all_scenario_statuses() -> Dict[str, Dict[str, Any]]:
    """
    Get the status of all running scenarios.
    
    Returns:
        Dict mapping scenario IDs to their status information
    """
    # Use the serialization helper to make all scenarios serializable
    return make_all_scenarios_serializable(_running_scenarios)

def get_scenario_status(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a specific scenario.
    
    Args:
        scenario_id: The unique ID of the scenario
        
    Returns:
        Status information or None if the scenario is not found
    """
    if scenario_id not in _running_scenarios:
        return None
        
    # Use the serialization helper to make the scenario serializable
    return make_scenario_serializable(_running_scenarios.get(scenario_id))

def real_scenario_runner(scenario_id: str, scenario_type: str, config_file: str, results_dir: str) -> None:
    """
    Actually run the scenario using the proper scenario implementation.
    
    Args:
        scenario_id: Unique ID for the scenario run
        scenario_type: Type of scenario to run
        config_file: Path to configuration file
        results_dir: Directory to store results
    """
    try:
        # Update status to running
        _running_scenarios[scenario_id]["status"] = "running"
        
        if metrics_service:
            metrics_service.record_metric("scenarios", f"{scenario_id}.status", "running")
        
        # Load and instantiate the scenario
        scenario = load_scenario(scenario_type, config_file, results_dir)
        
        # Store scenario instance in running scenarios
        _running_scenarios[scenario_id]["instance"] = scenario
        
        # Record scenario config 
        if hasattr(scenario, 'config'):
            _running_scenarios[scenario_id]["config"] = scenario.config
            
            # Check if GNS3 simulator is explicitly requested
            network_config = scenario.config.get("network", {})
            simulator_type = network_config.get("simulator", "")
            using_gns3 = simulator_type.lower() == "gns3"
            
            if using_gns3:
                logger.info(f"GNS3 simulator explicitly requested for scenario {scenario_id}")
            
            if metrics_service:
                # Record configuration details as metrics for visibility
                for key, value in scenario.config.items():
                    if isinstance(value, (int, float, str, bool)):
                        metrics_service.record_metric("scenarios", f"{scenario_id}.config.{key}", value)
        
        # Run the scenario
        logger.info(f"Starting scenario {scenario_type} with ID {scenario_id}")
        success = scenario.run()
        
        # Update status based on result
        if success:
            _running_scenarios[scenario_id]["status"] = "completed"
            _running_scenarios[scenario_id]["end_time"] = datetime.now().isoformat()
            
            # Get results from the scenario if available
            if hasattr(scenario, 'results'):
                _running_scenarios[scenario_id]["results"] = scenario.results
            else:
                _running_scenarios[scenario_id]["results"] = {"completed": True}
            
            if metrics_service:
                metrics_service.record_metric("scenarios", f"{scenario_id}.status", "completed")
                metrics_service.record_metric("scenarios", f"{scenario_id}.end_time", datetime.now().isoformat())
                
                # Record final metrics if available in scenario
                if hasattr(scenario, 'metrics') and scenario.metrics:
                    metrics = scenario.metrics.get_latest_metrics()
                    if metrics and isinstance(metrics, dict):
                        for category, cat_metrics in metrics.items():
                            for key, value in cat_metrics.items():
                                if isinstance(value, dict) and "current" in value:
                                    metrics_service.record_metric(category, key, value["current"])
                                elif isinstance(value, (int, float, str, bool)):
                                    metrics_service.record_metric(category, key, value)
                
                # Record scenario completion event
                metrics_service.record_event("scenarios", "scenario_completed", {
                    "scenario_id": scenario_id,
                    "scenario_type": scenario_type,
                    "success": True
                })
        else:
            _running_scenarios[scenario_id]["status"] = "failed"
            _running_scenarios[scenario_id]["end_time"] = datetime.now().isoformat()
            
            if metrics_service:
                metrics_service.record_metric("scenarios", f"{scenario_id}.status", "failed")
                metrics_service.record_metric("scenarios", f"{scenario_id}.end_time", datetime.now().isoformat())
                
                # Record failure event
                metrics_service.record_event("scenarios", "scenario_failed", {
                    "scenario_id": scenario_id,
                    "scenario_type": scenario_type
                })
    
    except RuntimeError as e:
        # Special handling for RuntimeError which is used for GNS3 failures
        error_message = str(e)
        
        # Check if this is a GNS3-specific error
        if 'gns3' in error_message.lower():
            logger.error(f"GNS3 ERROR in scenario {scenario_id}: {e}", exc_info=True)
            print(f"\n\n!!! GNS3 CRITICAL ERROR: {e} !!!\n")
            print("GNS3 failures are not allowed to fall back to mock data as per configuration.\n")
        else:
            logger.error(f"Error in scenario {scenario_id}: {e}", exc_info=True)
            
        if scenario_id in _running_scenarios:
            _running_scenarios[scenario_id]["status"] = "error"
            _running_scenarios[scenario_id]["error"] = error_message
            _running_scenarios[scenario_id]["end_time"] = datetime.now().isoformat()
            
            if metrics_service:
                metrics_service.record_metric("scenarios", f"{scenario_id}.status", "error")
                metrics_service.record_metric("scenarios", f"{scenario_id}.error", error_message)
                metrics_service.record_metric("scenarios", f"{scenario_id}.end_time", datetime.now().isoformat())
                
                # Record error event with additional context for GNS3 errors
                event_details = {
                    "scenario_id": scenario_id,
                    "scenario_type": scenario_type,
                    "error": error_message
                }
                
                if 'gns3' in error_message.lower():
                    event_details["error_type"] = "gns3_error"
                    event_details["critical"] = True
                
                metrics_service.record_event("scenarios", "scenario_error", event_details)
    
    except Exception as e:
        logger.error(f"Error in scenario {scenario_id}: {e}", exc_info=True)
        if scenario_id in _running_scenarios:
            _running_scenarios[scenario_id]["status"] = "error"
            _running_scenarios[scenario_id]["error"] = str(e)
            _running_scenarios[scenario_id]["end_time"] = datetime.now().isoformat()
            
            if metrics_service:
                metrics_service.record_metric("scenarios", f"{scenario_id}.status", "error")
                metrics_service.record_metric("scenarios", f"{scenario_id}.error", str(e))
                metrics_service.record_metric("scenarios", f"{scenario_id}.end_time", datetime.now().isoformat())
                
                # Record error event
                metrics_service.record_event("scenarios", "scenario_error", {
                    "scenario_id": scenario_id,
                    "scenario_type": scenario_type,
                    "error": str(e)
                })

def start_scenario(scenario_type: str, config_file: str = None, results_dir: str = "./results") -> Optional[str]:
    """
    Start a scenario with the given configuration.
    
    Args:
        scenario_type: Type of scenario to run (e.g., "basic")
        config_file: Path to configuration file (optional)
        results_dir: Directory to store results (default: "./results")
        
    Returns:
        Unique ID for the scenario execution or None if failed
    """
    if scenario_type not in SCENARIOS:
        logger.error(f"Unknown scenario type: {scenario_type}")
        return None
    
    # Generate a unique ID for this execution
    execution_id = str(uuid.uuid4())
    
    # Get scenario information
    scenario_path = SCENARIOS[scenario_type]
    
    # Record the start of scenario execution in metrics
    if metrics_service:
        metrics_service.record_event("scenarios", "scenario_started", {
            "scenario_id": execution_id,
            "scenario_type": scenario_type,
            "config_file": config_file,
            "results_dir": results_dir
        })
        
        # Record initial metrics
        metrics_service.record_metric("scenarios", f"{execution_id}.status", "initializing")
        metrics_service.record_metric("scenarios", f"{execution_id}.type", scenario_type)
        metrics_service.record_metric("scenarios", f"{execution_id}.start_time", datetime.now().isoformat())
    
    # Initialize running scenario record
    _running_scenarios[execution_id] = {
        "id": execution_id,
        "type": scenario_type,
        "status": "initializing",
        "start_time": datetime.now().isoformat(),
        "config_file": config_file,
        "results_dir": results_dir,
        "results": None
    }
    
    # Run the scenario in the foreground
    real_scenario_runner(execution_id, scenario_type, config_file, results_dir)
    
    return execution_id

def stop_scenario(scenario_id: str) -> bool:
    """
    Stop a running scenario.
    
    Args:
        scenario_id: The unique ID of the scenario to stop
        
    Returns:
        True if the scenario was stopped, False otherwise
    """
    if scenario_id not in _running_scenarios:
        logger.error(f"Scenario {scenario_id} not found")
        return False
    
    # Get the scenario instance
    scenario_instance = _running_scenarios[scenario_id].get("instance")
    
    # If we have a real scenario instance, try to stop it properly
    if scenario_instance and hasattr(scenario_instance, 'stop'):
        try:
            # Call the stop method of the scenario
            scenario_instance.stop()
        except Exception as e:
            logger.error(f"Error stopping scenario {scenario_id}: {e}")
    
    # Mark as stopped
    _running_scenarios[scenario_id]["status"] = "stopped"
    _running_scenarios[scenario_id]["end_time"] = datetime.now().isoformat()
    
    if metrics_service:
        metrics_service.record_metric("scenarios", f"{scenario_id}.status", "stopped")
        metrics_service.record_metric("scenarios", f"{scenario_id}.end_time", datetime.now().isoformat())
        
        # Record stop event
        metrics_service.record_event("scenarios", "scenario_stopped", {
            "scenario_id": scenario_id,
            "scenario_type": _running_scenarios[scenario_id]["type"]
        })
    
    return True

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If the file cannot be read or parsed
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise ValueError(f"Error loading configuration from {config_path}: {e}")

def list_available_scenarios() -> None:
    """
    Print a list of available scenarios to the console.
    """
    print("\nAvailable scenarios:")
    print("--------------------")
    for i, (scenario_name, module_path) in enumerate(SCENARIOS.items(), 1):
        module_path, class_name = module_path.split(":")
        print(f"{i}. {scenario_name} - {class_name} in {module_path}")
    print()

def main() -> int:
    """Main entry point for the scenario runner."""
    parser = argparse.ArgumentParser(description='Run a federated learning scenario')
    parser.add_argument('--scenario', choices=list(SCENARIOS.keys()), 
                        help='Scenario to run')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to configuration file')
    parser.add_argument('--results-dir', type=str, default='./results',
                        help='Directory to store results')
    parser.add_argument('--list', action='store_true',
                        help='List available scenarios')
    parser.add_argument('--debug', action='store_true', 
                        help='Enable debug logging')

    args = parser.parse_args()
    
    # Set up debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # Set all loggers to DEBUG level
        for log_name, log_obj in logging.Logger.manager.loggerDict.items():
            if isinstance(log_obj, logging.Logger):
                log_obj.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Force debug logging for key components
    logging.getLogger('src.scenarios').setLevel(logging.DEBUG)
    
    # Print startup information
    print(f"==== FL Scenario Runner ====")
    print(f"Available scenarios: {', '.join(SCENARIOS.keys())}")
    print(f"Working directory: {os.getcwd()}")
    
    if args.list:
        list_available_scenarios()
        return 0
        
    if not args.scenario:
        parser.error("Either --scenario or --list is required")
        return 1
    
    # Configure results directory
    results_dir = args.results_dir
    os.makedirs(results_dir, exist_ok=True)
    
    print(f"Scenario selected: {args.scenario}")
    print(f"Config file: {args.config}")
    print(f"Results directory: {results_dir}")
    
    try:
        # Special case for basic scenario - run directly
        if args.scenario == 'basic':
            print("Executing basic scenario directly")
            from src.scenarios.basic.scenario import BasicScenario
            
            # Load config
            if args.config:
                # Create and execute scenario with the config file path
                scenario = BasicScenario(config_file=args.config)
                
                # Execute the scenario correctly by calling setup() and run()
                if scenario.setup():
                    success = scenario.run()
                    scenario.cleanup()  # Make sure to clean up resources
                    
                    if success:
                        logger.info("Basic scenario completed successfully")
                        return 0
                    else:
                        logger.error("Basic scenario failed during execution")
                        return 1
                else:
                    logger.error("Basic scenario setup failed")
                    scenario.cleanup()  # Clean up even if setup fails
                    return 1
            else:
                logger.error("Config file is required for basic scenario")
                return 1
        
        # For other scenarios, use the standard start_scenario function
        scenario_id = start_scenario(args.scenario, args.config, results_dir)
        
        if not scenario_id:
            logger.error(f"Failed to start scenario {args.scenario}")
            return 1
            
        logger.info(f"Started scenario {args.scenario} with ID {scenario_id}")
        
        # Wait for the scenario to complete
        while True:
            status = get_scenario_status(scenario_id)
            if not status:
                logger.error(f"Scenario {scenario_id} not found")
                return 1
                
            if status["status"] in ["completed", "failed", "error"]:
                break
                
            logger.info(f"Scenario {scenario_id} status: {status['status']}")
            time.sleep(5)
        
        # Check final status
        final_status = get_scenario_status(scenario_id)
        if final_status["status"] == "completed":
            logger.info(f"Scenario {scenario_id} completed successfully")
            return 0
        else:
            logger.error(f"Scenario {scenario_id} failed with status {final_status['status']}")
            if "error" in final_status:
                logger.error(f"Error: {final_status['error']}")
            return 1
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 