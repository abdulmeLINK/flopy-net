"""
Configuration Loader

Provides utility functions for loading and merging configurations from files.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Import the global config manager
from src.core.config.config_manager import config_manager

logger = logging.getLogger(__name__)

def get_config_path(config_name: str) -> str:
    """
    Get the path to a configuration file.
    
    Args:
        config_name: Name of the configuration file
        
    Returns:
        str: Path to the configuration file
    """
    # Try to find config in standard locations
    config_dirs = [
        os.path.join(os.getcwd(), 'config'),
        os.path.join(os.getcwd(), 'configs'),
        os.path.join(os.getcwd(), 'configuration'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config'),
        '/app/config',  # For Docker
    ]
    
    # If config_manager has a valid config_dir, add that too
    if hasattr(config_manager, 'config_dir') and config_manager.config_dir:
        config_dirs.insert(0, config_manager.config_dir)  # Highest priority
    
    # For each potential directory, check if the config file exists
    for dir_path in config_dirs:
        config_path = os.path.join(dir_path, config_name)
        if os.path.exists(config_path):
            logger.debug(f"Found configuration at: {config_path}")
            return config_path
    
    # If not found, return the default path (for creation)
    default_dir = config_dirs[0] if config_dirs else os.path.join(os.getcwd(), 'config')
    os.makedirs(default_dir, exist_ok=True)
    default_path = os.path.join(default_dir, config_name)
    logger.warning(f"Configuration file not found, using default path: {default_path}")
    return default_path

def init_config(main_config: str = "main", scenario: Optional[str] = None) -> bool:
    """
    Initialize configuration by loading the main config and optionally a scenario config.
    
    Args:
        main_config: Name of the main configuration file (default: "main")
        scenario: Name of the scenario to load (default: None)
        
    Returns:
        bool: Success flag
    """
    # First, load the main configuration
    success = config_manager.load_config(main_config)
    if not success:
        logger.error(f"Failed to load main configuration: {main_config}")
        return False
        
    # Load environment variables
    config_manager.load_environment_variables(prefix='FL_')
    
    # If a scenario is specified, load it
    if scenario:
        scenario_path = f"scenarios/{scenario}"
        success = config_manager.load_config(scenario_path)
        if not success:
            logger.warning(f"Failed to load scenario configuration: {scenario}")
            # Continue anyway, as the main config should have defaults
    
    return True

def get_scenario_config(scenario_name: str) -> Dict[str, Any]:
    """
    Get the configuration for a specific scenario.
    
    This merges the base configuration with scenario-specific settings.
    
    Args:
        scenario_name: Name of the scenario
        
    Returns:
        Dict[str, Any]: Configuration for the scenario
    """
    # First, ensure we have loaded the main config
    if not config_manager.get("general"):
        init_config()
    
    # Try to get the scenario config from the already loaded configuration
    scenario_config = config_manager.get(f"scenarios.{scenario_name}")
    
    # If not found in the main config, try to load it directly
    if not scenario_config:
        scenario_path = f"scenarios/{scenario_name}"
        config_manager.load_config(scenario_path)
        
        # Now try to get directly from the configuration manager
        scenario_config = config_manager.get(scenario_name)
        
        # If still not found, load the file directly as a fallback
        if not scenario_config:
            try:
                scenario_file = os.path.join(config_manager.config_dir, f"scenarios/{scenario_name}.json")
                logger.debug(f"Trying to load scenario config directly from: {scenario_file}")
                
                if os.path.exists(scenario_file):
                    with open(scenario_file, 'r') as f:
                        scenario_config = json.load(f)
                        logger.info(f"Loaded scenario config directly from: {scenario_file}")
            except Exception as e:
                logger.error(f"Error loading scenario config directly: {e}")
    
    # If still no scenario config, return an empty dict
    return scenario_config or {}

def get_available_scenarios() -> List[str]:
    """
    Get a list of available scenarios based on configuration files.
    
    Returns:
        List[str]: List of available scenario names
    """
    # First, check if we have a scenarios list in the main config
    enabled_scenarios = config_manager.get("scenarios.enabled", [])
    if enabled_scenarios:
        return enabled_scenarios
    
    # Otherwise, check the file system
    scenarios_dir = os.path.join(config_manager.config_dir, "scenarios")
    if not os.path.exists(scenarios_dir):
        return []
    
    # List JSON files in the scenarios directory
    scenarios = []
    for filename in os.listdir(scenarios_dir):
        if filename.endswith(".json"):
            scenario_name = filename.split(".")[0]
            scenarios.append(scenario_name)
    
    return scenarios

def get_full_config(scenario_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the full configuration including scenario-specific settings.
    
    Args:
        scenario_name: Name of the scenario to include (default: from main config)
        
    Returns:
        Dict[str, Any]: Complete configuration
    """
    # Ensure main config is loaded
    if not config_manager.get("general"):
        init_config()
    
    # Get the current config
    config = config_manager.get_all()
    
    # If no scenario specified, use the default from main config
    if not scenario_name:
        scenario_name = config.get("scenarios", {}).get("default_scenario")
    
    # If still no scenario, return the current config
    if not scenario_name:
        return config
    
    # Load the scenario config
    scenario_config = get_scenario_config(scenario_name)
    
    # Return the merged config
    return config

def load_config_file(config_path: str) -> Dict[str, Any]:
    """
    Load a configuration from a specific file path.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict[str, Any]: Configuration from the file
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        return {} 