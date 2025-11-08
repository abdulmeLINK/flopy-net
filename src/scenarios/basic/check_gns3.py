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
Check GNS3 connectivity and code for basic scenario.
"""
import os
import sys
import json
import logging
import argparse
import time
import socket
import traceback
import requests

# Add the project root directory to Python path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.networking.gns3 import GNS3API
from src.scenarios.basic.scenario import BasicScenario, load_config, logger

def check_gns3_connection(host, port, project_name=None):
    """Test GNS3 server connectivity."""
    logger.info(f"Testing connection to GNS3 server at http://{host}:{port}/v2")
    
    try:
        # Initialize API client
        api = GNS3API(f"http://{host}:{port}/v2")
        
        # Check version to verify connectivity with timeout
        socket.setdefaulttimeout(30)  # Increase timeout for GNS3 operations
        
        try:
            version_info = api.get_version()
            if not version_info:
                logger.error("Failed to connect to GNS3 server or get version information")
                return False
                
            logger.info(f"Successfully connected to GNS3 server version: {version_info.get('version', 'unknown')}")
        except (socket.timeout, socket.error) as e:
            logger.error(f"Socket error or timeout connecting to GNS3 server: {str(e)}")
            logger.error(f"Check if the GNS3 server is running at {host}:{port}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: Unable to connect to GNS3 server at {host}:{port}")
            logger.error("Check if the GNS3 server is running and network connectivity")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error: GNS3 server at {host}:{port} did not respond in time")
            logger.error("The server might be busy or experiencing issues")
            return False
        except Exception as e:
            logger.error(f"Error connecting to GNS3 server: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        
        # Check if we need to verify a specific project
        if project_name:
            logger.info(f"Checking for project: {project_name}")
            try:
                success, projects = api._make_request('GET', '/projects', timeout=30)
                
                if not success:
                    logger.error("Failed to get projects from GNS3 server")
                    return False
                    
                project_exists = False
                for project in projects:
                    if project.get('name') == project_name:
                        logger.info(f"Found project: {project_name} (ID: {project.get('project_id')})")
                        project_exists = True
                        break
                        
                if not project_exists:
                    logger.info(f"Project {project_name} does not exist yet - would be created by scenario")
            except Exception as e:
                logger.error(f"Error getting projects from GNS3 server: {str(e)}")
                logger.error(traceback.format_exc())
                return False
        
        # Check for available templates
        try:
            success, templates = api._make_request('GET', '/templates', timeout=30)
            if success:
                logger.info(f"Successfully retrieved {len(templates)} templates from GNS3 server")
                # Log some template names for debugging
                if templates:
                    template_names = [t.get('name') for t in templates[:5]]
                    logger.info(f"Sample templates: {', '.join(template_names)}")
                    if len(templates) > 5:
                        logger.info(f"... and {len(templates) - 5} more templates")
            else:
                logger.warning("Failed to retrieve templates from GNS3 server")
        except Exception as e:
            logger.warning(f"Error retrieving templates: {str(e)}")
            # Don't fail the check just because we couldn't get templates
        
        return True
    except Exception as e:
        logger.error(f"Unexpected error checking GNS3 connection: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def check_code_only(config):
    """Check if the scenario code compiles and initializes without any GNS3 connection."""
    logger.info("Running in code-only verification mode (no GNS3 connection required)")
    
    # Extract and display the most important configuration parts
    network_config = config.get('network', {})
    gns3_config = network_config.get('gns3', {})
    template_config = config.get('templates', {})
    client_types = config.get('clients', {}).get('types', [])
    
    logger.info(f"Configuration contains:")
    logger.info(f"  - GNS3 host: {gns3_config.get('host')}")
    logger.info(f"  - GNS3 port: {gns3_config.get('port')}")
    logger.info(f"  - Project name: {gns3_config.get('project_name')}")
    logger.info(f"  - Server template: {template_config.get('server_template')}")
    logger.info(f"  - Client template: {template_config.get('client_template')}")
    logger.info(f"  - Switch template: {template_config.get('switch_template')}")
    logger.info(f"  - Client types: {len(client_types)} types configured")
    
    # Check if the refactored modules exist
    try:
        # Check if the needed modules are importable
        from src.scenarios.basic.gns3_manager import GNS3Manager
        from src.scenarios.basic.deployment_manager import DeploymentManager
        logger.info("Successfully imported refactored modules")
        
        # Check for critical classes/methods
        in_deploy_manager = False
        try:
            from inspect import getsource
            deploy_components_source = getsource(DeploymentManager.deploy_components)
            in_deploy_manager = True
            logger.info("Found deploy_components method in DeploymentManager class")
        except Exception:
            logger.warning("Could not inspect DeploymentManager.deploy_components")
            
        # Check for key logging statements in deployment manager
        if in_deploy_manager:
            critical_logging_statements = [
                "Creating switch node",
                "Creating server node", 
                "Creating client node",
                "Starting all nodes",
                "Connecting server to switch",
                "Connected client"
            ]
            
            for statement in critical_logging_statements:
                if statement in deploy_components_source:
                    logger.info(f"  - Found logging statement: '{statement}...'")
                else:
                    logger.warning(f"  - Missing expected logging statement: '{statement}...'")
        
        # Check GNS3Manager methods
        try:
            from inspect import getsource
            create_switch_node_source = getsource(GNS3Manager.create_switch_node)
            logger.info("Found create_switch_node method in GNS3Manager class")
            create_docker_node_source = getsource(GNS3Manager.create_docker_node)
            logger.info("Found create_docker_node method in GNS3Manager class")
        except Exception as e:
            logger.warning(f"Could not inspect GNS3Manager methods: {e}")
        
        # Create an instance to verify it initializes
        logger.info("Creating BasicScenario instance to verify imports...")
        scenario = BasicScenario(config=config)
        logger.info("BasicScenario instance created successfully")
        
        logger.info("Code verification successful!")
        return True
        
    except Exception as e:
        logger.error(f"Error during code verification: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Check GNS3 connectivity for basic scenario')
    parser.add_argument('--config', type=str, default='config/scenarios/basic_gns3_full.json',
                       help='Path to config file')
    parser.add_argument('--code-only', action='store_true',
                       help='Only verify code without checking GNS3 connection')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    args = parser.parse_args()
    
    try:
        # Configure logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Load configuration
        config = load_config(args.config)
        
        # If code-only mode is enabled, just verify the code
        if args.code_only:
            if check_code_only(config):
                logger.info("Code verification successful!")
                return 0
            else:
                logger.error("Code verification failed.")
                return 1
                
        # Extract GNS3 connection information
        gns3_host = "localhost"
        gns3_port = "3080"
        project_name = None
        
        if config:
            # Get from network.gns3 config if available
            network_config = config.get('network', {})
            gns3_network_config = network_config.get('gns3', {})
            
            if gns3_network_config:
                gns3_host = gns3_network_config.get('host', gns3_host)
                gns3_port = gns3_network_config.get('port', gns3_port)
                
            # Check for gns3 section as well
            gns3_config = config.get('gns3', {})
            if gns3_config:
                if 'server_url' in gns3_config:
                    # Parse the server URL
                    url = gns3_config.get('server_url', '')
                    if url:
                        # Remove http:// if present
                        url = url.replace('http://', '')
                        # Split host and port if port is included
                        if ':' in url:
                            gns3_host, gns3_port = url.split(':')
                
                # Get project name
                project_name = gns3_config.get('project_name', None)
        
        logger.info("Creating BasicScenario instance to verify imports...")
        scenario = BasicScenario(config=config)
        logger.info("BasicScenario instance created successfully. Code is valid.")
        
        # Check connectivity to GNS3 server
        if check_gns3_connection(gns3_host, gns3_port, project_name):
            logger.info("GNS3 connection successful!")
            return 0
        else:
            logger.error("GNS3 connection failed.")
            return 1
            
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 