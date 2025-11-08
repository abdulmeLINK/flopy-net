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
Common functions for working with scenarios.
This file provides functionality to discover and interact with scenario modules.
"""
import importlib
import os
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def discover_scenarios(scenarios_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover all available scenarios in the scenarios directory.
    
    Args:
        scenarios_path: Path to the scenarios directory. If None, uses the default location.
        
    Returns:
        Dictionary of scenario ID to scenario module
    """
    scenarios = {}
    
    # If no path is provided, use the default location (current directory)
    if scenarios_path is None:
        scenarios_path = os.path.abspath(os.path.dirname(__file__))
    
    logger.info(f"Searching for scenarios in {scenarios_path}")
    
    # Ensure the scenarios path exists in the Python path
    if scenarios_path not in sys.path:
        sys.path.insert(0, scenarios_path)
    
    # Get all subdirectories in the scenarios directory
    subdirs = [d for d in os.listdir(scenarios_path) 
              if os.path.isdir(os.path.join(scenarios_path, d)) and 
              not d.startswith('__') and not d.startswith('.')]
    
    for subdir in subdirs:
        # Skip the common directory
        if subdir == "common":
            continue
            
        # Try to import the scenario module (load __init__.py first, then fallback to scenario.py)
        try:
            scenario_path = os.path.join(scenarios_path, subdir)
            
            # First try to load the package (__init__.py) which contains the run function
            if os.path.exists(os.path.join(scenario_path, "__init__.py")):
                try:
                    module_name = f"src.scenarios.{subdir}"
                    scenario_module = importlib.import_module(module_name)
                    scenarios[subdir] = scenario_module
                    logger.info(f"Successfully loaded scenario: {subdir}")
                    continue
                except ImportError as e:
                    logger.debug(f"Failed to import {module_name}: {e}, trying alternative approaches")
            
            # Fallback: try scenario.py if __init__.py fails or doesn't exist
            if os.path.exists(os.path.join(scenario_path, "scenario.py")):
                # Import the module using the directory name
                module_name = f"scenarios.{subdir}.scenario"
                try:
                    scenario_module = importlib.import_module(module_name)
                    scenarios[subdir] = scenario_module
                    logger.info(f"Successfully loaded scenario: {subdir}")
                except ImportError as e:
                    # Try with direct path
                    try:
                        spec = importlib.util.spec_from_file_location(
                            f"{subdir}_scenario", 
                            os.path.join(scenario_path, "scenario.py")
                        )
                        scenario_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(scenario_module)
                        scenarios[subdir] = scenario_module
                        logger.info(f"Successfully loaded scenario with direct path: {subdir}")
                    except Exception as inner_e:
                        logger.error(f"Failed to import scenario {subdir}: {inner_e}")
        except Exception as e:
            logger.error(f"Error processing scenario directory {subdir}: {e}")
    
    if not scenarios:
        logger.warning("No scenarios were discovered. Check src/scenarios directory structure.")
        
    return scenarios

def load_scenario(scenario_id: str, scenarios_path: Optional[str] = None) -> Optional[Any]:
    """
    Load a specific scenario by ID.
    
    Args:
        scenario_id: ID of the scenario to load
        scenarios_path: Path to the scenarios directory. If None, uses the default location.
        
    Returns:
        Scenario module if found, None otherwise
    """
    scenarios = discover_scenarios(scenarios_path)
    return scenarios.get(scenario_id)

def list_scenarios(scenarios_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all available scenarios with metadata.
    
    Args:
        scenarios_path: Path to the scenarios directory. If None, uses the default location.
        
    Returns:
        List of scenario metadata dictionaries
    """
    scenarios = discover_scenarios(scenarios_path)
    result = []
    
    for scenario_id, module in scenarios.items():
        scenario_info = {
            "id": scenario_id,
            "name": getattr(module, "NAME", scenario_id),
            "description": getattr(module, "DESCRIPTION", "No description available"),
            "difficulty": getattr(module, "DIFFICULTY", "medium"),
            "category": getattr(module, "CATEGORY", "general"),
        }
        result.append(scenario_info)
    
    return result
