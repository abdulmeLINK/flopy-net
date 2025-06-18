#!/usr/bin/env python3
"""
Topology-based Network Configuration Demo Script.

This script demonstrates how to use the topology-based network configuration
approach with GNS3 and existing scenarios.
"""

import os
import sys
import json
import argparse
import logging
import time
from typing import Dict, Any, Optional

# Add the project root directory to Python path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import required modules
from src.utils.topology_manager import TopologyManager
from src.scenarios.basic.gns3_manager import GNS3Manager
from src.scenarios.basic.deployment_manager import DeploymentManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_topology_test(config_file: str, topology_file: str) -> bool:
    """
    Run a test using the topology-based network configuration.
    
    Args:
        config_file: Path to scenario configuration file
        topology_file: Path to network topology configuration file
        
    Returns:
        bool: True if test was successful, False otherwise
    """
    try:
        # Load configuration
        if not os.path.exists(config_file):
            logger.error(f"Configuration file not found: {config_file}")
            return False
            
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        # Load topology
        if not os.path.exists(topology_file):
            logger.error(f"Topology file not found: {topology_file}")
            return False
            
        # Add topology file to config
        config.setdefault('network', {})['topology_file'] = topology_file
        
        # Initialize the topology manager
        topology_manager = TopologyManager(topology_file=topology_file)
        
        # Validate the topology
        is_valid, errors = topology_manager.validate_topology()
        if not is_valid:
            logger.error("Topology validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
            
        logger.info("Topology validation successful")
        
        # Initialize GNS3 manager
        gns3_manager = GNS3Manager(config)
        
        # Check GNS3 connection
        if not gns3_manager.check_connection():
            logger.error("Failed to connect to GNS3 server")
            return False
            
        # Set up GNS3 project
        if not gns3_manager.setup_project():
            logger.error("Failed to set up GNS3 project")
            return False
            
        # Create deployment manager
        deployment_manager = DeploymentManager(gns3_manager, config)
        
        # Deploy components
        logger.info("Deploying components...")
        if not deployment_manager.deploy_components():
            logger.error("Failed to deploy components")
            return False
            
        # Configure networking
        logger.info("Configuring networking...")
        if not deployment_manager.configure_networking():
            logger.warning("Network configuration had issues, but continuing")
            
        # Run federated learning
        logger.info("Running federated learning...")
        if not deployment_manager.run_federated_learning():
            logger.error("Failed to run federated learning")
            return False
            
        # Get results
        results = deployment_manager.get_fl_results()
        if results:
            logger.info(f"Federated learning results: {json.dumps(results, indent=2)}")
        else:
            logger.warning("No federated learning results available")
            
        # Success
        logger.info("Topology test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running topology test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="GNS3 Topology Test")
    parser.add_argument("--config", type=str, default="config/scenarios/basic_main.json",
                        help="Path to configuration file")
    parser.add_argument("--topology", type=str, default="config/topology/basic_topology.json",
                        help="Path to topology file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Run test
    success = run_topology_test(args.config, args.topology)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
    
if __name__ == "__main__":
    main() 