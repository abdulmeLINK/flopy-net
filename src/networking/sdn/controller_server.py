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
SDN Controller Server for Federated Learning Network with Policy Engine Integration.

This script runs a Ryu SDN controller that integrates with the Policy Engine
to enforce network security policies for federated learning scenarios.
"""

import os
import sys
import time
import logging
import requests
import argparse
import json
import threading
import socket
# import netifaces  # Comment out netifaces import as it's causing installation issues
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("sdn_controller")

# Constants
DEFAULT_POLICY_TYPE = "network_security"
DEFAULT_POLICY_POLL_INTERVAL = 15  # seconds
DEFAULT_RYU_APPS = [
    # "ryu.app.ofctl_rest",   # REMOVED: Conflicts with our custom PolicySwitch API that provides /stats/* endpoints
    "ryu.topology.switches",  # Required by rest_topology for topology discovery
    "ryu.app.rest_topology",  # Provides /v1.0/topology/* endpoints for switches, links, hosts
    "src.networking.sdn.apps.policy_switch"  # Our comprehensive policy-aware switch with policy integration and fixed DPID conversion
]  # Essential Ryu apps plus our comprehensive policy switch with integrated policy engine

class SDNControllerServer:
    """
    SDN Controller Server that integrates with the Policy Engine.
    
    This class starts a Ryu controller with our custom application and
    periodically polls the Policy Engine for network security policies.
    """
    
    def __init__(self,
                policy_engine_url: Optional[str] = None,
                policy_poll_interval: int = DEFAULT_POLICY_POLL_INTERVAL,
                policy_type: str = DEFAULT_POLICY_TYPE,
                ryu_apps: Optional[List[str]] = None,
                ryu_rest_port: int = 8181,  # Changed default port from 8080 to 8181
                ryu_of_port: int = 6633,
                default_policy_file: Optional[str] = None,
                enable_fallback: bool = True,
                northbound_interface: Optional[str] = None,
                debug: bool = False):
        """
        Initialize the SDN Controller Server.
        
        Args:
            policy_engine_url: URL to the Policy Engine API
            policy_poll_interval: Time between policy polls (seconds)
            policy_type: Type of policy to fetch from Policy Engine
            ryu_apps: List of Ryu application modules to load
            ryu_rest_port: REST API port for Ryu
            ryu_of_port: OpenFlow port for Ryu
            default_policy_file: Path to default policy file to use when policy engine is unavailable
            enable_fallback: Whether to enable fallback to default policies when policy engine is unavailable
            northbound_interface: Network interface to use for policy engine communication
            debug: Enable debug logging
        """
        # Configure logging
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Set attributes
        self.policy_engine_url = policy_engine_url or os.environ.get("POLICY_ENGINE_URL", "http://policy-engine:5000")
        self.policy_poll_interval = policy_poll_interval
        self.policy_type = policy_type
        self.ryu_apps = ryu_apps or DEFAULT_RYU_APPS
        # Use REST_PORT from environment or default to 8181
        self.ryu_rest_port = int(os.environ.get("REST_PORT", str(ryu_rest_port)))
        self.ryu_of_port = ryu_of_port
        self.default_policy_file = default_policy_file or os.environ.get("DEFAULT_POLICY_FILE")
        self.enable_fallback = enable_fallback or (os.environ.get("POLICY_FALLBACK_ENABLED", "").lower() == "true")
        self.northbound_interface = northbound_interface or os.environ.get("NORTHBOUND_INTERFACE", "eth0")
        self.fallback_to_defaults = self.enable_fallback
        
        # Initialize components
        self.stop_event = threading.Event()
        self.ryu_process = None
        self.current_policies = {}
        self.policy_engine_available = False
        self.consecutive_failures = 0
        self.max_failures_before_fallback = 3
        
        # These are simplified since policy integration app handles the work
        self.flow_manager = None
        self.sdn_controller = None
        self.policy_engine_client = None
        
        logger.info(f"Initializing SDN Controller Server with Policy Engine URL: {self.policy_engine_url}")
        logger.info(f"Using northbound interface: {self.northbound_interface}")
        logger.info(f"Ryu applications: {', '.join(self.ryu_apps)}")
        logger.info(f"Ryu REST API port: {self.ryu_rest_port}")
        logger.info("Policy Engine integration handled by policy_integration Ryu app")
        
        # Load default policies if provided (for reference)
        self.default_policies = self._load_default_policies()
    
    def _load_default_policies(self) -> Dict[str, Any]:
        """Load default policies from file."""
        if not self.default_policy_file or not self.enable_fallback:
            return {}
            
        try:
            if os.path.exists(self.default_policy_file):
                logger.info(f"Loading default policies from {self.default_policy_file}")
                with open(self.default_policy_file, 'r') as f:
                    policies = json.load(f)
                logger.info(f"Default policies loaded successfully: {len(policies.get('policies', []))} policies")
                return policies
            else:
                logger.warning(f"Default policy file not found: {self.default_policy_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading default policies: {e}")
            return {}
    
    def start(self):
        """Start the SDN Controller Server."""
        logger.info("Starting SDN Controller Server...")
        
        # Start the Ryu controller with our policy integration app
        self._start_ryu_controller()
        
        logger.info("SDN Controller Server started successfully")
        logger.info(f"Policy Engine integration running at: {self.policy_engine_url}")
        logger.info(f"Ryu REST API available at: http://localhost:{self.ryu_rest_port}")
        logger.info(f"OpenFlow controller listening on port: {self.ryu_of_port}")
        
        try:
            # Keep the main thread alive
            while not self.stop_event.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def stop(self):
        """Stop the SDN Controller Server."""
        logger.info("Stopping SDN Controller Server")
        self.stop_event.set()
        
        if self.ryu_process:
            try:
                self.ryu_process.terminate()
                self.ryu_process.wait(timeout=5)
                logger.info("Ryu controller stopped")
            except Exception as e:
                logger.error(f"Error stopping Ryu controller: {e}")
    
    def _get_interface_ip(self, interface_name: str) -> Optional[str]:
        """Get the IP address of a specific network interface."""
        try:
            # Simple alternative implementation that doesn't rely on netifaces
            import socket
            import subprocess
            import re
            
            if sys.platform == 'win32':
                # On Windows, use ipconfig
                try:
                    output = subprocess.check_output(['ipconfig'], universal_newlines=True)
                    for line in output.split('\n'):
                        if interface_name in line:
                            # Look for IPv4 address in the next few lines
                            for i in range(5):  # Check next 5 lines
                                if i + 1 >= len(output.split('\n')):
                                    break
                                ipv4_line = output.split('\n')[output.split('\n').index(line) + i + 1]
                                if 'IPv4' in ipv4_line:
                                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ipv4_line)
                                    if match:
                                        return match.group(1)
                except Exception as e:
                    logger.error(f"Error getting IP via ipconfig: {e}")
                    return None
            else:
                # On Linux/Mac, use ifconfig or ip addr
                try:
                    if sys.platform.startswith('linux'):
                        cmd = ['ip', 'addr', 'show', interface_name]
                    else:
                        cmd = ['ifconfig', interface_name]
                    
                    output = subprocess.check_output(cmd, universal_newlines=True)
                    match = re.search(r'inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)', output)
                    if match:
                        return match.group(1)
                except Exception as e:
                    logger.error(f"Error getting IP via {cmd[0]}: {e}")
                    return None
            
            # Fallback: Try to get any IP address
            logger.warning(f"Could not find specific interface {interface_name}, using fallback method")
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Doesn't need to be reachable
                s.connect(('10.255.255.255', 1))
                IP = s.getsockname()[0]
            except Exception:
                IP = '127.0.0.1'
            finally:
                s.close()
            return IP
        except Exception as e:
            logger.error(f"Error getting IP for interface {interface_name}: {e}")
            return None
    
    def _start_ryu_controller(self):
        """Start the Ryu controller process."""
        import subprocess
        
        try:
            # Check if Ryu is installed
            try:
                import ryu
                logger.info("Ryu framework is installed")
            except ImportError:
                logger.error("Ryu framework is not installed. Please install it with 'pip install ryu'")
                sys.exit(1)
            
            # Build Ryu command
            cmd = [
                "ryu-manager",
                "--ofp-tcp-listen-port", str(self.ryu_of_port),
                "--wsapi-port", str(self.ryu_rest_port),
                "--verbose"
            ]
            
            # Add all Ryu applications
            cmd.extend(self.ryu_apps)
            
            logger.info(f"Starting Ryu controller with command: {' '.join(cmd)}")
            
            # Set environment variables for policy integration app
            env = os.environ.copy()
            env["POLICY_ENGINE_URL"] = self.policy_engine_url
            env["POLICY_POLL_INTERVAL"] = str(self.policy_poll_interval)
            
            # Start Ryu as a subprocess
            self.ryu_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env
            )
            
            # Check if process started successfully
            if self.ryu_process.poll() is not None:
                raise Exception(f"Ryu process exited with code {self.ryu_process.returncode}")
            
            # Give it a moment to start
            logger.info("Waiting for Ryu controller to initialize...")
            # Wait for Ryu REST API to become available
            api_check_url = f"http://localhost:{self.ryu_rest_port}/stats/switches"
            max_wait_time = 60 # seconds
            wait_interval = 1 # seconds
            start_time = time.time()

            logger.info(f"Waiting for Ryu REST API to be available at {api_check_url}...")

            while True:
                if time.time() - start_time > max_wait_time:
                    raise Exception(f"Ryu REST API did not become available at {api_check_url} within {max_wait_time} seconds.")
                
                try:
                    # Use a short timeout for the check itself
                    response = requests.get(api_check_url, timeout=2)
                    if response.status_code == 200:
                        logger.info("Ryu REST API is available.")
                        break # API is ready
                    elif response.status_code == 404:
                        # If /stats/switches is not found, but the server is up, Ryu is likely running
                        logger.warning(f"Ryu REST API returned 404 for {api_check_url}. API is likely up, but endpoint not found. Proceeding.")
                        break
                except requests.exceptions.ConnectionError:
                    logger.debug("Ryu REST API not yet reachable, retrying...")
                except Exception as e:
                    logger.warning(f"Error checking Ryu REST API: {e}. Retrying...")
                
                # Check if Ryu process has exited prematurely
                if self.ryu_process.poll() is not None:
                    stderr = self.ryu_process.stderr.read()
                    raise Exception(f"Ryu process exited prematurely with code {self.ryu_process.returncode}: {stderr}")
                    
                time.sleep(wait_interval)
            
            # Verify Ryu is running
            if self.ryu_process.poll() is not None:
                stderr = self.ryu_process.stderr.read()
                raise Exception(f"Ryu controller failed to start: {stderr}")
                
            logger.info("Ryu controller started successfully")
            
            # Start a thread to log Ryu output
            threading.Thread(target=self._log_ryu_output, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start Ryu controller: {e}")
            if self.ryu_process:
                self.ryu_process.terminate()
            sys.exit(1)
    
    def _log_ryu_output(self):
        """Log output from the Ryu controller process."""
        def log_stream(stream, log_level):
            """Read from a stream and log each line with the specified log level."""
            try:
                for line in iter(stream.readline, ""):
                    if log_level == "ERROR":
                        logger.error(f"Ryu error: {line.strip()}")
                    else:
                        logger.debug(f"Ryu: {line.strip()}")
            except Exception as e:
                logger.error(f"Error reading from Ryu {log_level.lower()} stream: {e}")
        
        # Start separate threads for stdout and stderr to prevent blocking
        stdout_thread = threading.Thread(
            target=log_stream,
            args=(self.ryu_process.stdout, "DEBUG"),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=log_stream,
            args=(self.ryu_process.stderr, "ERROR"),
            daemon=True
        )
        
        stdout_thread.start()
        stderr_thread.start()
    
    def get_switch_status(self):
        """
        Get status of all connected switches.
        
        Returns:
            Dict containing switch information and status
        """
        if not self.sdn_controller:
            logger.warning("Cannot get switch status: SDN controller not initialized")
            return {"error": "SDN controller not initialized", "switches": []}
        
        try:
            # Simplified version that uses Ryu API
            switches = []
            url = f"http://localhost:{self.ryu_rest_port}/stats/switches"
            
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    # Get list of switch DPIDs
                    switch_ids = response.json()
                    
                    for dpid in switch_ids:
                        # Get switch details
                        switch_info = {
                            "dpid": dpid,
                            "ports": [],
                            "flows": []
                        }
                        
                        # Get switch ports
                        port_url = f"http://localhost:{self.ryu_rest_port}/stats/portdesc/{dpid}"
                        try:
                            port_response = requests.get(port_url, timeout=15)
                            if port_response.status_code == 200:
                                ports_data = port_response.json()
                                if str(dpid) in ports_data:
                                    switch_info["ports"] = ports_data[str(dpid)]
                        except Exception as e:
                            logger.error(f"Error getting ports for switch {dpid}: {e}")
                        
                        # Get switch flows
                        flow_url = f"http://localhost:{self.ryu_rest_port}/stats/flow/{dpid}"
                        try:
                            flow_response = requests.get(flow_url, timeout=15)
                            if flow_response.status_code == 200:
                                flows_data = flow_response.json()
                                if str(dpid) in flows_data:
                                    switch_info["flows"] = flows_data[str(dpid)]
                        except Exception as e:
                            logger.error(f"Error getting flows for switch {dpid}: {e}")
                        
                        switches.append(switch_info)
                    
                    logger.info(f"Retrieved status for {len(switches)} switches")
                    
                    # Return detailed information
                    return {
                        "switches_count": len(switches),
                        "switches": switches
                    }
                else:
                    logger.error(f"Error getting switches: HTTP {response.status_code}")
                    return {"error": f"HTTP {response.status_code}", "switches": []}
            except Exception as e:
                logger.error(f"Error querying Ryu REST API: {e}")
                return {"error": str(e), "switches": []}
        except Exception as e:
            logger.error(f"Error getting switch status: {e}")
            return {"error": str(e), "switches": []}


def main():
    """Run the SDN controller server."""
    parser = argparse.ArgumentParser(description='SDN Controller Server')
    parser.add_argument('--policy-engine-url', help='URL to the Policy Engine API')
    parser.add_argument('--policy-poll-interval', type=int, default=DEFAULT_POLICY_POLL_INTERVAL,
                       help='Time between policy polls in seconds')
    parser.add_argument('--ryu-rest-port', type=int, default=8181,
                       help='REST API port for Ryu')
    parser.add_argument('--ryu-of-port', type=int, default=6633,
                       help='OpenFlow port for Ryu')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--config', help='Path to JSON config file')
    parser.add_argument('--default-policy-file', help='Path to default policy file')
    parser.add_argument('--enable-fallback', action='store_true', 
                       help='Enable fallback to default policies when policy engine is unavailable')
    parser.add_argument('--northbound-interface', help='Network interface to use for policy engine communication')
    parser.add_argument('--show-switches', action='store_true',
                       help='Show connected switches and their status')
    
    args = parser.parse_args()
    
    # Load config from file if provided
    config = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Create and start the controller server
    server = SDNControllerServer(
        policy_engine_url=args.policy_engine_url or config.get('policy_engine_url'),
        policy_poll_interval=args.policy_poll_interval or config.get('policy_poll_interval', DEFAULT_POLICY_POLL_INTERVAL),
        ryu_rest_port=args.ryu_rest_port or config.get('ryu_rest_port', 8181),
        ryu_of_port=args.ryu_of_port or config.get('ryu_of_port', 6633),
        default_policy_file=args.default_policy_file or config.get('default_policy_file'),
        enable_fallback=args.enable_fallback or config.get('enable_fallback', True),
        northbound_interface=args.northbound_interface or config.get('northbound_interface'),
        debug=args.debug or config.get('debug', False)
    )
    
    # If show-switches flag is set, just print switch status and exit
    if args.show_switches:
        server._start_ryu_controller()
        time.sleep(5)  # Give controller time to connect to switches
        
        # Initialize the controller components
        from src.networking.sdn.ryu_controller import RyuController
        server.sdn_controller = RyuController(
            host="localhost", 
            port=server.ryu_rest_port,
            api_url_prefix='/stats',
            protocol='http',
            timeout=30,
            ofp_version='OpenFlow13'
        )
        
        # Get and print switch status
        switch_status = server.get_switch_status()
        print(json.dumps(switch_status, indent=2))
        
        # Stop the controller
        server.stop()
        return
    
    server.start()


if __name__ == "__main__":
    main() 