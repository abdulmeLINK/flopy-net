#!/usr/bin/env python
"""
GNS3 Connectivity Checker

This script checks connectivity to a GNS3 server and verifies the existence of
required templates and projects for a scenario.
"""

import sys
import os
import json
import logging
import argparse
import requests
from typing import Dict, Any, List, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_gns3_connection(host: str = 'localhost', port: int = 3080) -> bool:
    """
    Check if the GNS3 server is accessible.
    
    Args:
        host: The GNS3 server hostname or IP
        port: The GNS3 server API port
        
    Returns:
        bool: True if the server is accessible, False otherwise
    """
    url = f"http://{host}:{port}/v2/version"
    logger.info(f"Checking GNS3 server connection at {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            version = response.json().get('version', 'unknown')
            logger.info(f"GNS3 server is accessible (version: {version})")
            return True
        else:
            logger.error(f"GNS3 server returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: Unable to connect to GNS3 server at {host}:{port}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error: GNS3 server at {host}:{port} did not respond in time")
        return False
    except Exception as e:
        logger.error(f"Error checking GNS3 server connection: {e}")
        return False

def get_templates(host: str = 'localhost', port: int = 3080) -> List[Dict[str, Any]]:
    """
    Get the list of available templates from the GNS3 server.
    
    Args:
        host: The GNS3 server hostname or IP
        port: The GNS3 server API port
        
    Returns:
        List of template dictionaries
    """
    url = f"http://{host}:{port}/v2/templates"
    logger.debug(f"Getting templates from {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            templates = response.json()
            logger.debug(f"Found {len(templates)} templates")
            return templates
        else:
            logger.error(f"Failed to get templates: status code {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return []

def check_template_exists(template_name: str, host: str = 'localhost', port: int = 3080) -> bool:
    """
    Check if a template exists on the GNS3 server.
    
    Args:
        template_name: The name of the template to check
        host: The GNS3 server hostname or IP
        port: The GNS3 server API port
        
    Returns:
        bool: True if the template exists, False otherwise
    """
    templates = get_templates(host, port)
    
    for template in templates:
        if template.get('name') == template_name:
            logger.info(f"Template '{template_name}' exists on GNS3 server")
            return True
            
    logger.warning(f"Template '{template_name}' does not exist on GNS3 server")
    return False

def check_all_templates(template_names: List[str], host: str = 'localhost', port: int = 3080) -> Dict[str, bool]:
    """
    Check if multiple templates exist on the GNS3 server.
    
    Args:
        template_names: List of template names to check
        host: The GNS3 server hostname or IP
        port: The GNS3 server API port
        
    Returns:
        Dict mapping template names to existence status (True/False)
    """
    templates = get_templates(host, port)
    template_map = {template.get('name'): template for template in templates}
    
    results = {}
    for template_name in template_names:
        exists = template_name in template_map
        results[template_name] = exists
        
        if exists:
            logger.info(f"Template '{template_name}' exists on GNS3 server")
        else:
            logger.warning(f"Template '{template_name}' does not exist on GNS3 server")
            
    return results

def get_projects(host: str = 'localhost', port: int = 3080) -> List[Dict[str, Any]]:
    """
    Get the list of projects from the GNS3 server.
    
    Args:
        host: The GNS3 server hostname or IP
        port: The GNS3 server API port
        
    Returns:
        List of project dictionaries
    """
    url = f"http://{host}:{port}/v2/projects"
    logger.debug(f"Getting projects from {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            projects = response.json()
            logger.debug(f"Found {len(projects)} projects")
            return projects
        else:
            logger.error(f"Failed to get projects: status code {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return []

def check_project_exists(project_name: str, host: str = 'localhost', port: int = 3080) -> Tuple[bool, Optional[str]]:
    """
    Check if a project exists on the GNS3 server.
    
    Args:
        project_name: The name of the project to check
        host: The GNS3 server hostname or IP
        port: The GNS3 server API port
        
    Returns:
        Tuple of (exists: bool, project_id: Optional[str])
    """
    projects = get_projects(host, port)
    
    for project in projects:
        if project.get('name') == project_name:
            project_id = project.get('project_id')
            logger.info(f"Project '{project_name}' exists with ID: {project_id}")
            return True, project_id
            
    logger.warning(f"Project '{project_name}' does not exist on GNS3 server")
    return False, None

def check_gns3_environment(config: Dict[str, Any]) -> bool:
    """
    Check if the GNS3 environment matches the requirements in the configuration.
    
    Args:
        config: A dictionary containing the GNS3 configuration with:
               - server: dict with host and port
               - templates: list of required template names
               - project: optional project name to check
               
    Returns:
        bool: True if all checks pass, False otherwise
    """
    # Extract configuration
    server_config = config.get('server', {})
    host = server_config.get('host', 'localhost')
    port = server_config.get('port', 3080)
    
    # Check server connection
    logger.info(f"Checking GNS3 environment with host={host}, port={port}")
    if not check_gns3_connection(host, port):
        logger.error("GNS3 server connection check failed")
        return False
    
    # Check templates if provided
    templates = config.get('templates', [])
    if templates:
        logger.info(f"Checking for required templates: {templates}")
        template_results = check_all_templates(templates, host, port)
        if not all(template_results.values()):
            missing_templates = [name for name, exists in template_results.items() if not exists]
            logger.error(f"Missing required templates: {missing_templates}")
            return False
    
    # Check project if provided
    project_name = config.get('project', {}).get('name')
    if project_name:
        logger.info(f"Checking for project: {project_name}")
        exists, _ = check_project_exists(project_name, host, port)
        if not exists and config.get('project', {}).get('required', False):
            logger.error(f"Required project '{project_name}' does not exist")
            return False
    
    logger.info("All GNS3 environment checks passed")
    return True

def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load a configuration from a JSON file.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Dict containing the configuration
    """
    logger.info(f"Loading configuration from {config_file}")
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def main():
    """Main function to run the GNS3 connectivity check."""
    parser = argparse.ArgumentParser(description='Check GNS3 connectivity and required templates')
    parser.add_argument('--host', default='localhost', help='GNS3 server hostname or IP')
    parser.add_argument('--port', type=int, default=3080, help='GNS3 server API port')
    parser.add_argument('--templates', nargs='+', help='List of required templates')
    parser.add_argument('--project-name', help='Project name to check')
    parser.add_argument('--config', help='Path to a configuration JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Process configuration
    config = {}
    if args.config:
        config = load_config(args.config)
    
    # Override config with command-line arguments
    if args.host:
        config.setdefault('server', {})['host'] = args.host
    if args.port:
        config.setdefault('server', {})['port'] = args.port
    if args.templates:
        config['templates'] = args.templates
    if args.project_name:
        config.setdefault('project', {})['name'] = args.project_name
    
    # Check GNS3 environment
    if check_gns3_environment(config):
        logger.info("GNS3 environment check passed")
        sys.exit(0)
    else:
        logger.error("GNS3 environment check failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 