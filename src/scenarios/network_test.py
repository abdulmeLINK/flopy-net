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
Network Test Utility for GNS3 projects.

This script connects to a running GNS3 server and project, and performs network tests
between nodes to verify connectivity.
"""

import os
import sys
import json
import logging
import argparse
import time
import traceback

# Add the project root directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import GNS3 modules
from src.networking.gns3.core.api import GNS3API

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load a config file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def ping_test(api, project_id, source_node_id, target_ip, count=3):
    """Run a ping test from one node to another."""
    ping_cmd = f"ping -c {count} {target_ip}"
    logger.info(f"Running ping test from node {source_node_id} to {target_ip}")
    
    try:
        success, output = api.execute_command_on_node(
            project_id,
            source_node_id,
            ping_cmd,
            timeout=30
        )
        if success:
            logger.info(f"Ping test successful")
            logger.debug(f"Output: {output}")
            return True, output
        else:
            logger.error(f"Ping test failed")
            logger.error(f"Output: {output}")
            return False, output
    except Exception as e:
        logger.error(f"Error running ping test: {e}")
        return False, str(e)

def get_node_ip(api, project_id, node_id):
    """Get a node's IP address."""
    # Try to get IP address using ip addr command
    try:
        success, output = api.execute_command_on_node(
            project_id,
            node_id,
            "ip addr",
            timeout=30
        )
        if success:
            # Parse output to find IPv4 address
            # This is a simple parser for demonstration, might need refinement
            lines = output.split('\n')
            for line in lines:
                if 'inet ' in line and 'scope global' in line:
                    parts = line.strip().split()
                    for part in parts:
                        if '/' in part and part.startswith('1'):
                            return part.split('/')[0]
            
            logger.warning(f"Could not find IPv4 address in output")
            return None
        else:
            logger.error(f"Failed to get IP address: {output}")
            return None
    except Exception as e:
        logger.error(f"Error getting IP address: {e}")
        return None

def test_network_connectivity(gns3_server, project_id):
    """Test network connectivity between nodes in a GNS3 project."""
    try:
        # Initialize API client
        api = GNS3API(f"http://{gns3_server}/v2")
        
        # Get project
        success, project = api._make_request('GET', f'/projects/{project_id}')
        if not success:
            logger.error(f"Failed to get project: {project}")
            return False
        
        logger.info(f"Connected to project: {project.get('name')}")
        
        # Get nodes
        success, nodes = api._make_request('GET', f'/projects/{project_id}/nodes')
        if not success:
            logger.error(f"Failed to get nodes: {nodes}")
            return False
        
        logger.info(f"Found {len(nodes)} nodes in project")
        
        # Filter out for only Docker nodes
        docker_nodes = [n for n in nodes if n.get('node_type') == 'docker']
        logger.info(f"Found {len(docker_nodes)} Docker nodes")
        
        # Define known IPs for testing - these match our static IP assignments
        KNOWN_IPS = {
            "fl_server": "172.17.0.2",
            "policy_engine": "172.17.0.3", 
            "metric_collector": "172.17.0.4"
        }

        # Prepare tests
        test_results = []
        
        # For each docker node, test connectivity to others
        for source_node in docker_nodes:
            source_id = source_node.get('node_id')
            source_name = source_node.get('name')
            
            logger.info(f"Testing connectivity from {source_name} ({source_id})")
            
            # Check if node has a known IP
            if source_name in KNOWN_IPS:
                logger.info(f"Using known IP {KNOWN_IPS[source_name]} for {source_name}")
                source_ip = KNOWN_IPS[source_name]
            else:
                # Try to get IP from interface
                source_ip = get_node_ip(api, project_id, source_id)
                if not source_ip:
                    logger.warning(f"Could not determine IP for {source_name}, using fallback")
                    # For client nodes try to determine from name
                    if "client" in source_name.lower():
                        client_num = 1
                        try:
                            # Try to extract client number from name
                            parts = source_name.split('_')
                            if len(parts) > 3:
                                client_num = int(parts[3])
                        except:
                            pass
                        source_ip = f"172.17.0.{10 + client_num}"
                        logger.info(f"Using fallback IP {source_ip} for client {source_name}")
            
            # Get network data from node
            try:
                logger.info(f"Getting network info for {source_name}")
                success, ifconfig = api.execute_command_on_node(
                    project_id, source_id, "ip addr", timeout=30
                )
                if success:
                    logger.info(f"Network info for {source_name}:\n{ifconfig}")
                else:
                    logger.error(f"Failed to get network info for {source_name}: {ifconfig}")
            except Exception as e:
                logger.error(f"Error getting network info: {e}")
            
            # For each target node, run ping test
            for target_node in docker_nodes:
                # Skip self
                if target_node.get('node_id') == source_id:
                    continue
                    
                target_name = target_node.get('name')
                
                # Check if target has a known IP
                if target_name in KNOWN_IPS:
                    target_ip = KNOWN_IPS[target_name]
                else:
                    # For client nodes try to determine from name
                    if "client" in target_name.lower():
                        client_num = 1
                        try:
                            # Try to extract client number from name
                            parts = target_name.split('_')
                            if len(parts) > 3:
                                client_num = int(parts[3])
                        except:
                            pass
                        target_ip = f"172.17.0.{10 + client_num}"
                    else:
                        logger.warning(f"Could not determine IP for {target_name}, skipping")
                        continue
                
                logger.info(f"Testing {source_name} -> {target_name} ({target_ip})")
                
                # Run ping test
                success, output = ping_test(api, project_id, source_id, target_ip, count=2)
                
                # Store result
                test_results.append({
                    "source": source_name,
                    "target": target_name,
                    "target_ip": target_ip,
                    "success": success,
                    "output": output if isinstance(output, str) else str(output)
                })
                
                if success:
                    logger.info(f"Ping {source_name} -> {target_name} SUCCESS")
                else:
                    logger.error(f"Ping {source_name} -> {target_name} FAILED")
        
        # Print summary
        logger.info("=== Connectivity Test Summary ===")
        success_count = sum(1 for r in test_results if r['success'])
        logger.info(f"Total tests: {len(test_results)}")
        logger.info(f"Successful tests: {success_count}")
        logger.info(f"Failed tests: {len(test_results) - success_count}")
        
        # Print detailed results
        logger.info("=== Detailed Results ===")
        for result in test_results:
            status = "SUCCESS" if result['success'] else "FAILED"
            logger.info(f"{result['source']} -> {result['target']} ({result['target_ip']}): {status}")
            
        return test_results
    except Exception as e:
        logger.error(f"Error testing network connectivity: {e}")
        logger.error(traceback.format_exc())
        return None

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Network Test for FL")
    parser.add_argument("--gns3-server", type=str, default="192.168.141.128:80",
                       help="GNS3 server (host:port)")
    parser.add_argument("--project-id", type=str, required=True,
                       help="GNS3 project ID")
    parser.add_argument("--config", type=str, default="config/scenarios/basic_gns3_full.json",
                       help="Path to GNS3 configuration file")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config if provided
    config = None
    if args.config:
        config = load_config(args.config)
        if config and 'network' in config and 'gns3' in config['network']:
            gns3_config = config['network']['gns3']
            gns3_server = f"{gns3_config.get('host')}:{gns3_config.get('port', 80)}"
            args.gns3_server = gns3_server
            logger.info(f"Using GNS3 server from config: {gns3_server}")
    
    # Test network connectivity
    results = test_network_connectivity(args.gns3_server, args.project_id)
    
    # Exit with status code based on results
    if results is None:
        sys.exit(2)  # Error during tests
    elif all(r['success'] for r in results):
        sys.exit(0)  # All tests passed
    else:
        sys.exit(1)  # Some tests failed

if __name__ == "__main__":
    main() 