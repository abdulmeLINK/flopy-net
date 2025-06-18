"""
Common definitions for scenarios.

This module contains common definitions and constants shared across scenario modules.
"""

import os
import importlib
import inspect
import logging
import importlib.util
from pathlib import Path
from typing import Dict, Any, Type

# Configure logger
logger = logging.getLogger(__name__)

def discover_scenarios() -> Dict[str, str]:
    """
    Dynamically discover available scenario modules from subdirectories.
    
    Each scenario should be in its own subdirectory with a scenario.py file
    that contains a class ending with 'Scenario'.
    
    Returns:
        Dictionary mapping scenario IDs to their module:class paths
    """
    scenarios = {}
    
    # Check for scenario modules in the scenarios directory
    scenarios_dir = Path(__file__).parent
    
    # Focus only on subdirectories for full implementations
    subdirs = [d for d in scenarios_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
    
    for subdir in subdirs:
        scenario_name = subdir.name.lower()
        scenario_file = subdir / "scenario.py"
        
        if scenario_file.exists():
            try:
                module_path = f"src.scenarios.{subdir.name}.scenario"
                module = importlib.import_module(module_path)
                
                # Find scenario class in the module (should end with 'Scenario')
                for attr_name in dir(module):
                    if attr_name.endswith("Scenario"):
                        scenarios[scenario_name] = f"{module_path}:{attr_name}"
                        logger.info(f"Found scenario implementation: {scenario_name} -> {attr_name}")
                        break
            except Exception as e:
                logger.warning(f"Error importing scenario {scenario_name}: {e}")
    
    if not scenarios:
        # Instead of using fallback values, just log an error since no scenarios were found
        logger.error("No scenarios discovered! Please ensure that scenario directories exist with proper implementation files.")
        logger.info("Each scenario should be in a subdirectory of src/scenarios/ with a scenario.py file containing a class ending with 'Scenario'")
    
    logger.info(f"Discovered scenarios: {list(scenarios.keys())}")
    return scenarios

# Get available scenarios
SCENARIOS = discover_scenarios()

def load_scenario(scenario_name: str, config_file: str = None, results_dir: str = "./results") -> Any:
    """
    Load and instantiate a scenario by name.
    
    Args:
        scenario_name: Name of the scenario to load
        config_file: Path to the configuration file (if None, uses scenario default)
        results_dir: Directory to store results
        
    Returns:
        Instantiated scenario object
        
    Raises:
        ValueError: If the scenario is not found
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Scenario '{scenario_name}' not found. Available scenarios: {list(SCENARIOS.keys())}")
        
    # Parse module path and class name
    module_path, class_name = SCENARIOS[scenario_name].split(":")
    
    try:
        # Import module
        module = importlib.import_module(module_path)
        # Get scenario class
        scenario_class = getattr(module, class_name)
        
        # Create scenario instance with config
        if config_file:
            return scenario_class(config_file=config_file, results_dir=results_dir)
        else:
            return scenario_class(results_dir=results_dir)
            
    except Exception as e:
        logger.error(f"Error loading scenario '{scenario_name}': {e}")
        raise 