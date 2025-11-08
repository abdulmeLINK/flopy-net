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

from fastapi import APIRouter, HTTPException, Request, Depends
import importlib
import sys
import os
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional
import asyncio
import threading
import json
import io
from contextlib import redirect_stdout, redirect_stderr

# Configure FastAPI router without redirects
router = APIRouter(redirect_slashes=False)
logger = logging.getLogger(__name__)

# Import function to ensure proper import paths are set up
from app.core.imports import setup_imports
from app.core.config import settings

# Setup imports at module load time
setup_imports()

# Dictionary to store discovered scenarios
SCENARIOS = {}
IMPORT_TIME_STR = time.strftime("%Y-%m-%dT%H:%M:%S")

# Dictionary to track running scenarios
RUNNING_SCENARIOS: Dict[str, Dict] = {}

# Dictionary to store scenario logs
SCENARIO_LOGS: Dict[str, List[str]] = {}

def discover_fallback_scenarios():
    """
    Discover placeholder/fallback scenarios when real scenarios can't be loaded.
    This provides a basic list of expected scenarios for development/testing.
    """
    fallback_scenarios = {
        "basic": {
            "name": "basic",
            "description": "Basic federated learning scenario (placeholder)",
            "status": "idle",
            "has_config": False,
            "has_topology": False
        },
        "advanced": {
            "name": "advanced", 
            "description": "Advanced federated learning scenario (placeholder)",
            "status": "idle",
            "has_config": False,
            "has_topology": False
        },
        "demo": {
            "name": "demo",
            "description": "Demo scenario for testing (placeholder)", 
            "status": "idle",
            "has_config": False,
            "has_topology": False
        }
    }
    return fallback_scenarios

def _check_scenario_config_exists(scenario_name: str) -> bool:
    """Check if scenario configuration file exists."""
    config_path = os.path.join("config", "scenarios", f"{scenario_name}_main.json")
    return os.path.exists(config_path)

def _check_scenario_topology_exists(scenario_name: str) -> bool:
    """Check if scenario topology file exists."""
    topology_path = os.path.join("config", "topology", f"{scenario_name}_topology.json")
    return os.path.exists(topology_path)

@router.get("")
@router.get("/")
async def get_scenarios_list():
    """Get list of all available scenarios with their status and metadata."""
    try:
        # Get scenarios (either real or fallback)
        from src.scenarios.common_functions import discover_scenarios
        
        scenarios = discover_scenarios()
        
        # If no real scenarios found, use fallback scenarios
        if not scenarios:
            logger.warning("No real scenarios found, using fallback scenarios")
            scenarios = discover_fallback_scenarios()
        
        # Convert to list format with additional metadata
        scenarios_list = []
        for scenario_id, scenario_module in scenarios.items():
            # Get current status from running scenarios
            current_status = RUNNING_SCENARIOS.get(scenario_id, {})
            
            scenario_info = {
                "name": scenario_id,
                "description": getattr(scenario_module, "DESCRIPTION", f"Scenario: {scenario_id}"),
                "status": current_status.get("status", "idle"),
                "started_at": current_status.get("started_at"),
                "message": current_status.get("message"),
                "has_config": _check_scenario_config_exists(scenario_id),
                "has_topology": _check_scenario_topology_exists(scenario_id)
            }
            scenarios_list.append(scenario_info)
        
        logger.info(f"Successfully loaded {len(scenarios_list)} scenarios: {[s['name'] for s in scenarios_list]}")
        return scenarios_list
        
    except Exception as e:
        logger.error(f"Error loading scenarios: {e}")
        # Return fallback scenarios on error
        fallback_scenarios = discover_fallback_scenarios()
        scenarios_list = []
        for scenario_id, scenario_data in fallback_scenarios.items():
            scenarios_list.append({
                **scenario_data,
                "has_config": _check_scenario_config_exists(scenario_id),
                "has_topology": _check_scenario_topology_exists(scenario_id)
            })
        return scenarios_list

@router.get("/{scenario_name}/config")
async def get_scenario_config(scenario_name: str):
    """Get scenario configuration."""
    try:
        config_path = os.path.join("config", "scenarios", f"{scenario_name}_main.json")
        
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail=f"Configuration file not found for scenario '{scenario_name}'")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        return {
            "scenario_name": scenario_name,
            "config_file": config_path,
            "config": config
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        logger.error(f"Error reading scenario config: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading configuration: {e}")

@router.get("/{scenario_name}/topology")
async def get_scenario_topology(scenario_name: str):
    """Get scenario topology configuration."""
    try:
        topology_path = os.path.join("config", "topology", f"{scenario_name}_topology.json")
        
        if not os.path.exists(topology_path):
            raise HTTPException(status_code=404, detail=f"Topology file not found for scenario '{scenario_name}'")
        
        with open(topology_path, 'r') as f:
            topology = json.load(f)
            
        return {
            "scenario_name": scenario_name,
            "topology_file": topology_path,
            "topology": topology
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in topology file: {e}")
    except Exception as e:
        logger.error(f"Error reading scenario topology: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading topology: {e}")

@router.get("/{scenario_name}/status")
async def get_scenario_status(scenario_name: str):
    """Get status of a specific scenario."""
    if scenario_name not in RUNNING_SCENARIOS:
        return {
            "scenario_name": scenario_name,
            "status": "idle",
            "message": "Scenario is not currently running"
        }
    
    return {
        "scenario_name": scenario_name,
        **RUNNING_SCENARIOS[scenario_name]
    }

@router.get("/{scenario_name}/logs")
async def get_scenario_logs(scenario_name: str, lines: int = 100):
    """Get logs for a specific scenario."""
    try:
        if scenario_name not in SCENARIO_LOGS:
            return {
                "scenario_name": scenario_name,
                "logs": [],
                "message": "No logs available for this scenario"
            }
        
        logs = SCENARIO_LOGS[scenario_name]
        # Return the last 'lines' number of log entries
        return {
            "scenario_name": scenario_name,
            "logs": logs[-lines:] if len(logs) > lines else logs,
            "total_lines": len(logs)
        }
    except Exception as e:
        logger.error(f"Error getting scenario logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading logs: {e}")

class ScenarioLogHandler(logging.Handler):
    """Custom log handler to capture scenario logs."""
    
    def __init__(self, scenario_name: str):
        super().__init__()
        self.scenario_name = scenario_name
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    def emit(self, record):
        try:
            log_entry = self.format(record)
            if self.scenario_name not in SCENARIO_LOGS:
                SCENARIO_LOGS[self.scenario_name] = []
            
            # Keep only last 1000 log entries to prevent memory issues
            if len(SCENARIO_LOGS[self.scenario_name]) >= 1000:
                SCENARIO_LOGS[self.scenario_name] = SCENARIO_LOGS[self.scenario_name][-500:]
            
            SCENARIO_LOGS[self.scenario_name].append(log_entry)
        except Exception:
            # Ignore errors in logging to prevent recursion
            pass

def _run_scenario_thread(scenario_name: str, scenario_module):
    """Run scenario in a separate thread with proper status tracking and logging."""
    # Set up log capture for this scenario
    scenario_logger = logging.getLogger(f"scenario.{scenario_name}")
    log_handler = ScenarioLogHandler(scenario_name)
    scenario_logger.addHandler(log_handler)
    scenario_logger.setLevel(logging.INFO)
    
    # Initialize logs list
    if scenario_name not in SCENARIO_LOGS:
        SCENARIO_LOGS[scenario_name] = []
    
    try:
        # Update status to running
        RUNNING_SCENARIOS[scenario_name] = {
            "status": "running",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "message": "Scenario is running..."
        }
        
        scenario_logger.info(f"Starting scenario execution: {scenario_name}")
        logger.info(f"Starting scenario thread for: {scenario_name}")
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Call the scenario's run function with output capture
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = scenario_module.run()
        
        # Add captured output to logs
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()
        
        if stdout_content:
            for line in stdout_content.strip().split('\n'):
                scenario_logger.info(f"STDOUT: {line}")
        
        if stderr_content:
            for line in stderr_content.strip().split('\n'):
                scenario_logger.error(f"STDERR: {line}")
        
        # Check logs for "Topology has been left running"
        topology_running = False
        for log in SCENARIO_LOGS.get(scenario_name, []):
            if "Topology has been left running" in log:
                topology_running = True
                break
        
        # Update status based on result
        if result:
            # If we detect the topology is left running, use "running" status instead of "completed"
            if topology_running:
                RUNNING_SCENARIOS[scenario_name].update({
                    "status": "running",
                    "message": "Scenario completed successfully. Topology is still running."
                })
                scenario_logger.info(f"Scenario '{scenario_name}' completed with topology still running")
                logger.info(f"Scenario '{scenario_name}' completed with topology still running")
            else:
                RUNNING_SCENARIOS[scenario_name].update({
                    "status": "completed",
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "message": "Scenario completed successfully"
                })
                scenario_logger.info(f"Scenario '{scenario_name}' completed successfully")
                logger.info(f"Scenario '{scenario_name}' completed successfully")
        else:
            RUNNING_SCENARIOS[scenario_name].update({
                "status": "failed",
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "message": "Scenario execution failed"
            })
            scenario_logger.error(f"Scenario '{scenario_name}' execution failed")
            logger.error(f"Scenario '{scenario_name}' execution failed")
            
    except Exception as e:
        RUNNING_SCENARIOS[scenario_name].update({
            "status": "error",
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "message": f"Scenario error: {str(e)}"
        })
        scenario_logger.error(f"Error in scenario execution: {e}")
        logger.error(f"Error in scenario thread for '{scenario_name}': {e}")
    finally:
        # Clean up log handler
        scenario_logger.removeHandler(log_handler)

@router.post("/{scenario_name}/run")
async def run_scenario(scenario_name: str, request: Request):
    """Run a specific scenario by name."""
    try:
        # Check if scenario is already running
        if scenario_name in RUNNING_SCENARIOS and RUNNING_SCENARIOS[scenario_name].get("status") == "running":
            return {
                "message": f"Scenario '{scenario_name}' is already running",
                "status": "already_running",
                "scenario_status": RUNNING_SCENARIOS[scenario_name]
            }
        
        # Get scenarios (either real or fallback)
        from src.scenarios.common_functions import discover_scenarios, load_scenario
        
        # Try to load the actual scenario module
        scenario_module = load_scenario(scenario_name)

        if scenario_module is None:
            # Try to see if it's a fallback scenario name if module not found
            fallback_scenarios_map = discover_fallback_scenarios()
            if scenario_name in fallback_scenarios_map:
                logger.info(f"Running fallback scenario placeholder for {scenario_name}")
                # For fallbacks, we don't execute, just acknowledge
                return {"message": f"Fallback scenario '{scenario_name}' acknowledged. No execution for placeholders.", "status": "acknowledged_fallback"}
            else:
                # Discover available scenarios to list them in the error
                all_scenarios = discover_scenarios()
                if not all_scenarios: # If discovery fails, use fallbacks for listing
                    all_scenarios = discover_fallback_scenarios()
                
                raise HTTPException(
                    status_code=404, 
                    detail=f"Scenario '{scenario_name}' not found. Available scenarios: {list(all_scenarios.keys())}"
                )

        if hasattr(scenario_module, "run") and callable(scenario_module.run):
            logger.info(f"Attempting to run scenario: {scenario_name}")
            
            # Initialize status
            RUNNING_SCENARIOS[scenario_name] = {
                "status": "starting",
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "message": "Scenario is starting..."
            }
            
            # Clear previous logs
            SCENARIO_LOGS[scenario_name] = []
            
            # Run the scenario's run() function in a separate thread
            thread = threading.Thread(
                target=_run_scenario_thread, 
                args=(scenario_name, scenario_module),
                name=f"scenario-{scenario_name}"
            )
            thread.start()
            
            logger.info(f"Scenario '{scenario_name}' started in a background thread.")
            return {
                "message": f"Scenario '{scenario_name}' has been started.",
                "status": "started",
                "scenario_status": RUNNING_SCENARIOS[scenario_name]
            }
        else:
            logger.warning(f"Scenario module '{scenario_name}' does not have a callable 'run' function.")
            return {"message": f"Scenario '{scenario_name}' is recognized but has no 'run' method to execute.", "status": "no_run_method"}
            
    except HTTPException:
        raise  # Re-raise HTTPException directly
    except ImportError as e:
        logger.error(f"ImportError when trying to load or run scenario '{scenario_name}': {e}")
        # Check if it's a fallback scenario after import error
        fallback_scenarios_map = discover_fallback_scenarios()
        if scenario_name in fallback_scenarios_map:
            logger.info(f"Acknowledging fallback scenario for {scenario_name} due to import error during run.")
            return {"message": f"Fallback scenario '{scenario_name}' acknowledged. No execution for placeholders.", "status": "acknowledged_fallback_due_to_error", "detail": str(e)}
        
        all_scenarios = discover_scenarios()
        if not all_scenarios:
            all_scenarios = discover_fallback_scenarios()
        raise HTTPException(status_code=500, detail=f"Could not load scenario '{scenario_name}' due to import error: {e}. Available: {list(all_scenarios.keys())}")
    except Exception as e:
        logger.error(f"Error running scenario '{scenario_name}': {e}", exc_info=True)
        # Try to provide a more specific error if possible
        return {"error": str(e), "status": "failed", "type": type(e).__name__}

@router.post("/{scenario_name}/stop")
async def stop_scenario(scenario_name: str):
    """Stop a running scenario."""
    if scenario_name not in RUNNING_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' is not running")
    
    # Update status to stopped
    RUNNING_SCENARIOS[scenario_name].update({
        "status": "stopped",
        "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "message": "Scenario was stopped by user"
    })
    
    logger.info(f"Scenario '{scenario_name}' was stopped")
    
    return {
        "message": f"Scenario '{scenario_name}' has been stopped",
        "status": "stopped",
        "scenario_status": RUNNING_SCENARIOS[scenario_name]
    }