#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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
Helper module to ensure Python can import from the src directory.
"""
import sys
import os
import logging

logger = logging.getLogger(__name__)

def setup_imports():
    """
    Ensure that the src directory is in the Python path.
    This should only be needed for development environments,
    as the Docker container will have the correct PYTHONPATH.
    """
    # Get the absolute path to the dashboard directory
    dashboard_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..')
    )
    
    # Get the absolute path to the src directory
    src_dir = os.path.abspath(
        os.path.join(dashboard_dir, '..', 'src')
    )
    
    # Check if the src directory exists
    if not os.path.isdir(src_dir):
        # In Docker, the src directory might be at /app/src
        docker_src_dir = '/app/src'
        if os.path.isdir(docker_src_dir):
            src_dir = docker_src_dir
            logger.info(f"Using Docker src directory at {src_dir}")
        else:
            logger.warning(f"src directory not found at {src_dir} or {docker_src_dir}")
            return False
      # Add the parent directory of src to the path if not already there
    if src_dir not in sys.path:
        # Add src directory directly to sys.path
        sys.path.insert(0, src_dir)
        logger.info(f"Added {src_dir} to Python path")
        
        # Also add parent directory to support 'from src.x import y' style imports
        parent_dir = os.path.dirname(src_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            logger.info(f"Added {parent_dir} to Python path")
      # Verify we can import from src
    try:
        import src
        logger.info(f"Successfully imported 'src' module")
        
        # Also check if scenarios directory is accessible
        scenarios_path = os.path.join(src_dir, 'scenarios')
        if os.path.isdir(scenarios_path):
            logger.info(f"Located scenarios directory at {scenarios_path}")
            # Check for subdirectories that should contain scenario implementations
            scenario_subdirs = [d for d in os.listdir(scenarios_path) 
                               if os.path.isdir(os.path.join(scenarios_path, d)) and not d.startswith('__')]
            logger.info(f"Found potential scenario directories: {scenario_subdirs}")
        else:
            logger.warning(f"Scenarios directory not found at {scenarios_path}")
        return True
    except ImportError as e:
        logger.error(f"Failed to import 'src' module: {e}")
        logger.error(f"Current sys.path: {sys.path}")
        return False

def debug_imports():
    """
    Print debug information about the Python path and available imports.
    Useful for troubleshooting import issues in different environments.
    """
    logger.info("=== Python Import Debug Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info("Python path:")
    for p in sys.path:
        logger.info(f"  - {p}")
    
    # Try common imports that might be needed
    try:
        import src
        logger.info("✓ 'src' module can be imported")
        try:
            from src import scenarios
            logger.info("✓ 'src.scenarios' module can be imported")
        except ImportError as e:
            logger.error(f"✗ Failed to import 'src.scenarios': {e}")
    except ImportError as e:
        logger.error(f"✗ Failed to import 'src' module: {e}")
    
    # Try to import collector modules
    try:
        import src.collector
        logger.info("✓ 'src.collector' module can be imported")
    except ImportError as e:
        logger.error(f"✗ Failed to import 'src.collector': {e}")
    
    # Try to import networking modules
    try:
        import src.networking
        logger.info("✓ 'src.networking' module can be imported")
    except ImportError as e:
        logger.error(f"✗ Failed to import 'src.networking': {e}")
        
    logger.info("=== End of Import Debug ===")
    return True
