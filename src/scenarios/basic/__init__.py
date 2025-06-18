"""
Basic Federated Learning Scenario.

This package implements a basic federated learning scenario
with minimal configuration for testing and demonstration purposes.
"""

from src.scenarios.basic.scenario import BasicScenario
import os
import logging

__all__ = ['BasicScenario', 'run'] 

logger = logging.getLogger(__name__)

def run():
    """
    Run the basic scenario with default configuration.
    This function is called when the scenario is executed from the dashboard.
    """
    try:
        logger.info("Starting basic scenario execution...")
        
        # Use default configuration files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, "..", "..", "..", "config")
        
        config_file = os.path.join(config_dir, "scenarios", "basic_main.json")
        topology_file = os.path.join(config_dir, "topology", "basic_topology.json")
        
        # Check if config files exist
        if not os.path.exists(config_file):
            logger.error(f"Configuration file not found: {config_file}")
            return False
            
        if not os.path.exists(topology_file):
            logger.error(f"Topology file not found: {topology_file}")
            return False
        
        # Create and run the scenario
        scenario = BasicScenario(config_file, topology_file)
        
        logger.info("Setting up scenario...")
        if not scenario.setup():
            logger.error("Failed to setup scenario")
            return False
        
        logger.info("Running scenario...")
        success = scenario.run()
        
        if success:
            logger.info("Scenario completed successfully")
        else:
            logger.error("Scenario execution failed")
            
        # Don't clean up - leave topology running as per user request
        # scenario.cleanup()  # This line is removed to match CLI behavior
        
        # Add clear status message for the dashboard
        logger.info("Scenario execution finished. Topology has been left running.")
        
        # Save results to file
        scenario.save_results()
        
        return success
        
    except Exception as e:
        logger.error(f"Error running basic scenario: {e}")
        return False 