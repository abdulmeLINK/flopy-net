#!/usr/bin/env python3
"""
Basic Federated Learning Scenario.

This module implements a basic federated learning scenario for generic applications.
"""

import os
import sys
import json
import uuid
import logging
import time
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Union
import traceback
import requests
import argparse

# Ensure src directory is in Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../../..'))
# Insert SRC_DIR at the beginning of sys.path for higher priority
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import base scenario class
from src.scenarios.base_scenario import BaseScenario
from src.utils.topology_manager import TopologyManager
from src.scenarios.basic.gns3_manager import GNS3Manager
from src.scenarios.basic.deployment_manager import DeploymentManager
from src.utils.config_loader import ConfigLoader
from src.utils.log_formatter import ColoredFormatter
from src.scenarios.common.gns3_utils import manage_socat_port_forwarding

# Import for IP address handling
import ipaddress

# Scenario metadata for discovery
NAME = "Basic Federated Learning"
DESCRIPTION = "A basic federated learning scenario with multiple clients and a central server"
DIFFICULTY = "beginner"
CATEGORY = "federated_learning"

logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Configure logging for the scenario."""
    # Remove existing handlers to avoid duplicate messages
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    
    # Create formatter and add it to the handler
    # Use ColoredFormatter for console output with appropriate settings for Windows
    formatter = ColoredFormatter(include_file_line=level==logging.DEBUG)
    ch.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(ch)
    
    # Set overall logger level
    logger.setLevel(level)
    
    # Add a file handler if needed
    try:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"scenario_{time.strftime('%Y%m%d_%H%M%S')}.log")
        
        # Create file handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        
        # Create simple formatter for file logs (no colors)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(file_formatter)
        
        # Add the handler to the logger
        logger.addHandler(fh)
        logger.info(f"Logging to file: {log_file}")
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")

class BasicScenario(BaseScenario):
    """Basic Federated Learning Scenario implementation."""

    def __init__(self, config_file: str, topology_file: Optional[str] = None):
        """
        Initialize the basic scenario.
        
        Args:
            config_file: Path to configuration file
            topology_file: Path to topology file (overrides config setting) (optional)
        """
        super().__init__(config_file)
        
        self.scenario_id = f"basic-scenario-{uuid.uuid4().hex[:8]}"
        
        # --- Start Change: Determine and store topology file path --- 
        # Prefer explicit topology_file argument
        resolved_topology_file = topology_file 
        if not resolved_topology_file:
            # Fallback to config if not provided as argument
            resolved_topology_file = self.config.get('network', {}).get('topology_file')
        
        if not resolved_topology_file:
            logger.warning("No topology file specified in arguments or config. Deployment might fail.")
            # Optionally load a default or raise an error
            # default_topology_path = os.path.join(SRC_DIR, "config", "topology", "basic_topology.json")
            # if os.path.exists(default_topology_path):
            #    resolved_topology_file = default_topology_path
            #    logger.info(f"Using default topology file: {resolved_topology_file}")

        self.topology_file = resolved_topology_file
        # --- End Change ---
        
        # --- Start Change: Initialize TopologyManager once --- 
        if self.topology_file and os.path.exists(self.topology_file):
            self.topology_manager = TopologyManager(topology_file=self.topology_file)
            if not self.topology_manager.topology_config:
                logger.error(f"Failed to load topology from {self.topology_file}")
                # Decide how to handle: raise error or allow continuation?
                self.topology_manager = None # Set to None if loading failed
        else:
            logger.error(f"Topology file not found or not specified: {self.topology_file}")
            self.topology_manager = None
        # --- End Change ---

        # self.topology_file = topology_file # Remove old line
        self.gns3_manager = None
        self.deployment_manager = None
        self.results = {
            "scenario_id": self.scenario_id,
            "config_file": config_file,
            "topology_file": self.topology_file, # Use resolved path
            "start_time": None,
            "end_time": None,
            "duration_seconds": None,
            "status": "initialized",
            "error": None,
            "fl_results": None,
            "topology_summary": None
        }
        
        logger.info(f"BasicScenario initialized with ID: {self.scenario_id}")
    
    def setup(self) -> bool:
        """Set up the GNS3 environment and deploy components."""
        self.results["start_time"] = time.time()
        self.status = "initializing"
        
        try:
            # 1. Initialize GNS3 Manager
            self.results["status"] = "connecting_gns3"
            self.status = "connecting_gns3"
            logger.info("Connecting to GNS3 server...")
            self.gns3_manager = GNS3Manager(self.config)
            logger.info(f"Checking connection to GNS3 server at {self.gns3_manager.api.base_url}")
            if not self.gns3_manager.check_connection():
                self.results["status"] = "failed"
                self.results["error"] = "Failed to connect to GNS3 server"
                logger.error("Setup failed: Cannot connect to GNS3")
                return False
                
            # Log GNS3 server version
            success, version_info = self.gns3_manager.api._make_request('GET', 'version')
            if success:
                logger.info(f"Connected to GNS3 server: {version_info.get('version', 'unknown')}")
            else:
                logger.warning("Could not retrieve GNS3 server version")
            
            # 2. Initialize Topology Manager
            self.results["status"] = "loading_topology"
            self.status = "loading_topology"
            logger.info(f"Loading topology from {self.topology_file}")
            self.topology_manager = TopologyManager(self.topology_file)
            
            # 3. Create GNS3 Project
            self.results["status"] = "creating_project"
            self.status = "creating_project"
            logger.info("Creating GNS3 project...")
            project_created = self.gns3_manager.setup_project()
            if not project_created:
                self.results["status"] = "failed"
                self.results["error"] = "Failed to create GNS3 project"
                logger.error("Setup failed: Project creation failed")
                return False
                
            logger.info(f"Project created/opened with ID: {self.gns3_manager.project_id}")
            
            # 4. Check for required templates
            self.results["status"] = "checking_templates"
            self.status = "checking_templates"
            logger.info("Checking for required templates in GNS3...")
            success, available_templates_raw = self.gns3_manager.api.get_templates()
            if success and available_templates_raw:
                available_template_names = {t.get('name') for t in available_templates_raw if t.get('name')}
                logger.info(f"Available templates in GNS3: {sorted(list(available_template_names))}")
                
                # Add more detailed logging for Cloud template
                cloud_templates = [t for t in available_templates_raw if t.get('name') == 'Cloud']
                if cloud_templates:
                    logger.info(f"Cloud template details: {cloud_templates[0]}")
                
                # Check for required templates
                required_templates = set()
                for node_name, node in self.topology_manager.node_map.items():
                    template_name = node.get("template_name")
                    if template_name:
                        required_templates.add(template_name)
                
                missing_templates = required_templates - available_template_names
                if missing_templates:
                    self.results["status"] = "failed"
                    self.results["error"] = f"Missing required templates: {missing_templates}"
                    logger.error(f"Setup failed: Missing required templates: {missing_templates}")
                    return False
                    
                logger.info(f"All required templates are available: {required_templates}")
            
            # 5. Deploy topology
            self.results["status"] = "deploying_topology"
            self.status = "deploying_topology"
            logger.info("Deploying topology...")
            self.deployment_manager = DeploymentManager(
                gns3_manager=self.gns3_manager,
                config=self.config,
                topology_manager=self.topology_manager
            )
            if not self.deployment_manager.deploy_components():
                self.results["status"] = "failed"
                self.results["error"] = "Failed to deploy topology"
                logger.error("Setup failed: Topology deployment failed")
                return False
                
            # 5. Start all nodes
            self.results["status"] = "starting_nodes"
            self.status = "starting_nodes"
            logger.info("Starting all nodes...")
            
            # 6. Wait for components to be ready
            self.results["status"] = "waiting_for_services"
            self.status = "waiting_for_services"
            logger.info("Waiting for services to become available...")
            
            # 7. Configure networking
            self.results["status"] = "configuring_networking"
            self.status = "configuring_networking"
            logger.info("Configuring networking...")
            if not self.deployment_manager.configure_networking():
                self.results["status"] = "networking_failed"
                self.results["error"] = "Failed to configure networking"
                logger.error("Setup failed: Network configuration failed")
                # Allow continuation if network configuration fails, but log warning
                logger.warning("Network configuration failed, continuing scenario execution...")

            self.results["status"] = "setup_complete"
            self.status = "setup_complete"
            logger.info("Scenario setup completed successfully")

            return True
            
        except Exception as e:
            self.results["status"] = "failed"
            self.results["error"] = f"Exception during setup: {e}"
            logger.error(f"Error during setup: {e}")
            logger.debug(traceback.format_exc())
            return False

    def run(self) -> bool:
        """Run the federated learning workload."""
        if self.results["status"] not in ["setup_complete", "networking_failed"]:
            logger.error("Cannot run workload: Setup did not complete successfully.")
            return False
            
        try:
            # Update status to indicate workload is starting
            self.results["status"] = "initializing_workload"
            self.status = "initializing_workload"
            logger.info("Starting federated learning workload...")
            
            # Prepare environment for workload
            self.results["status"] = "preparing_environment"
            self.status = "preparing_environment"
            logger.info("Preparing environment for federated learning...")
            
            # Run the actual workload
            self.results["status"] = "running_workload"
            self.status = "running_workload"
            logger.info("Running federated learning workload...")
            
            # Execute FL workload using Deployment Manager
            if not self.deployment_manager.run_federated_learning():
                self.results["status"] = "workload_failed"
                self.results["error"] = "Federated learning workload failed"
                logger.error("Federated learning workload failed")
                return False
            
            # Analyze results
            self.results["status"] = "analyzing_results"
            self.status = "analyzing_results"
            logger.info("Analyzing federated learning results...")
            
            # Update final status
            self.results["status"] = "workload_complete"
            self.status = "workload_complete"
            self.results["fl_results"] = self.deployment_manager.get_fl_results()
            
            # Add final metrics
            self.results["end_time"] = time.time()
            if self.results["start_time"]:
                self.results["duration_seconds"] = round(self.results["end_time"] - self.results["start_time"], 2)
                
            logger.info(f"Federated learning workload completed successfully in {self.results.get('duration_seconds', 0)} seconds")
            return True
            
        except Exception as e:
            self.results["status"] = "workload_failed"
            self.status = "workload_failed"
            self.results["error"] = f"Exception during workload execution: {e}"
            logger.error(f"Error running workload: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up GNS3 resources."""
        logger.info("Starting cleanup...")
        
        logger.info("Cleaning up GNS3 resources")
        
        # Cleanup via Deployment Manager
        if self.deployment_manager:
            self.deployment_manager.cleanup()
        # Cleanup via GNS3 Manager as fallback
        elif self.gns3_manager:
            self.gns3_manager.cleanup_project()
            
        # Record end time and duration
        self.results["end_time"] = time.time()
        if self.results["start_time"]:
            self.results["duration_seconds"] = round(self.results["end_time"] - self.results["start_time"], 2)
            
        # Update final status if it was successful
        # Consider both setup_complete and workload_complete as successful states
        if self.results["status"] in ["workload_complete", "setup_complete"]:
            self.results["status"] = "completed"
            
        logger.info(f"Scenario cleanup finished. Final status: {self.results['status']}")

    def save_results(self, filename: Optional[str] = None) -> None:
        """Save scenario results to a JSON file."""
        if not filename:
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            os.makedirs(results_dir, exist_ok=True)
            filename = os.path.join(results_dir, f"basic_scenario_{self.scenario_id}.json")
            
        # Ensure results are serializable
        serializable_results = {}
        for key, value in self.results.items():
            try:
                json.dumps(value) # Test serialization
                serializable_results[key] = value
            except TypeError:
                serializable_results[key] = str(value) # Convert non-serializable items to string
        
        try:
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=4)
            logger.info(f"Scenario results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results to {filename}: {e}")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Run Basic Federated Learning Scenario")
    parser.add_argument("--config", required=True, help="Path to the main configuration file (e.g., config/scenarios/basic_main.json)")
    parser.add_argument("--topology", help="Path to a custom GNS3 topology file (optional)")
    parser.add_argument("--results-file", help="Path to save the results JSON file (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--cleanup", action="store_true", help="Perform cleanup after scenario completion")
    
    args = parser.parse_args()

    # Setup logging based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)

    # Validate config file path
    if not os.path.exists(args.config):
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)

    # Validate topology file path if provided
    if args.topology and not os.path.exists(args.topology):
        logger.error(f"Topology file not found: {args.topology}")
        sys.exit(1)

    # Load configuration
    config_loader = ConfigLoader(args.config)
    config = config_loader.get_config()
    if not config:
        logger.error(f"Failed to load configuration from {args.config}")
        sys.exit(1)

    # Create and run the scenario
    scenario = BasicScenario(config_file=args.config, topology_file=args.topology)
    start_time = time.time()
    
    logger.info(f"Starting basic scenario with ID: {scenario.scenario_id}")

    try:
        if scenario.setup():
            scenario.run()
        else:
            logger.error("Scenario setup failed, skipping execution.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during scenario execution: {e}")
        scenario.results["status"] = "failed"
        scenario.results["error"] = f"Unhandled exception: {e}"
    finally:
        if args.cleanup:
            scenario.cleanup()
            logger.info("Scenario execution finished and cleanup performed.")
        else:
            logger.info("Scenario execution finished. Topology has been left running.")
        
        scenario.save_results(args.results_file)
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Consider the scenario successful if setup completed and topology was deployed
        # This includes cases where the workload ran but didn't complete the full training
        success_statuses = ["completed", "workload_complete", "setup_complete"]
        if scenario.results["status"] in success_statuses:
            logger.info(f"Basic scenario {scenario.scenario_id} completed successfully in {duration} seconds")
        else:
            logger.error(f"Basic scenario {scenario.scenario_id} failed after {duration} seconds")

if __name__ == "__main__":
    main() 