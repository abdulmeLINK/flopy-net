"""
Ryu SDN Controller Integration Module.

This module provides integration with the Ryu SDN controller for network management
and flow control in federated learning scenarios.
"""

import os
import json
import time
import logging
import subprocess
import requests
import socket
import netifaces
from typing import Dict, List, Any, Optional, Tuple, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.common.logger import LoggerMixin
from src.networking.interfaces.sdn_controller import ISDNController
from src.networking.sdn.config_loader import load_sdn_config
from ryu.ofproto import ofproto_v1_3

class RyuController(LoggerMixin, ISDNController):
    """
    Ryu SDN Controller implementation for network management in federated learning.
    
    This class provides integration with the Ryu SDN controller, allowing for
    flow management, topology discovery, and QoS policies in federated learning networks.
    """
    
    # Define supported OpenFlow versions
    OF_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # Use OpenFlow 1.3 (0x04)
    
    def __init__(self, host='localhost', port=8080, api_url_prefix='/stats',
                 timeout=5, protocol='http', ofp_version='OpenFlow13'):
        """
        Initialize RyuController.
        
        Args:
            host: RyuController REST API host
            port: RyuController REST API port
            api_url_prefix: API URL prefix
            timeout: Request timeout in seconds
            protocol: HTTP protocol (http/https)
            ofp_version: OpenFlow protocol version to use
        """
        self.host = host
        self.port = port
        self.api_url_prefix = api_url_prefix
        self.timeout = 30  # Increased timeout from 5 to 30 seconds to avoid timeouts
        self.protocol = protocol
        self.ofp_version = ofp_version
        self.base_url = f"{protocol}://{host}:{port}"
        self.session = requests.Session()
        
        # Add retry mechanism for API requests
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504, 408],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Verify connection to controller
        self.verify_connection()
        
        # No need to manually setup logger as LoggerMixin handles this automatically
        # when the logger property is accessed
        
        # Define supported OpenFlow versions
        self.OF_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # Use OpenFlow 1.3 (0x04)
        
        # Setup REST API URLs
        self.switches_url = f"{self.base_url}/stats/switches"
        
        # Set up network topology tracking
        self.switches = []
        self.links = []
        self.hosts = []
        self.connected = False
        
        # Initialize statistics tracking for real performance metrics
        self.port_stats_cache = {}  # Cache for port statistics
        self.flow_stats_cache = {}  # Cache for flow statistics
        self.last_stats_collection = 0  # Timestamp of last collection
        self.stats_collection_interval = 10  # Collect stats every 10 seconds

        # Initialize connection
        self.logger.info(f"Initialized Ryu controller interface at {self.host}:{self.port}")
    
    def verify_connection(self):
        """
        Verify connection to the controller.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            self.logger.info(f"Verifying connection to RyuController at {self.base_url}")
            response = self.session.get(f"{self.base_url}", timeout=self.timeout)
            if response.status_code == 200:
                self.logger.info("Successfully connected to RyuController")
                return True
            else:
                self.logger.warning(f"Failed to connect to RyuController: Status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to connect to RyuController: {e}")
            return False
    
    def _setup_northbound_interface(self):
        """
        Configure the northbound interface for policy engine communication.
        
        This method checks if the specified northbound interface exists and
        configures it for communication with the policy engine.
        """
        try:
            # Check if interface exists
            if_ip = self._get_interface_ip(self.northbound_interface)
            
            if if_ip:
                self.logger.info(f"Northbound interface {self.northbound_interface} found with IP {if_ip}")
                # Store the IP for use in API requests to policy engine
                self.northbound_ip = if_ip
            else:
                self.logger.warning(f"Northbound interface {self.northbound_interface} not found or has no IP address")
                self.logger.info("Will use default route for policy engine communication")
                self.northbound_ip = None
                
                # Try to get any available IP as fallback
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # Doesn't need to be reachable
                    s.connect(('10.255.255.255', 1))
                    fallback_ip = s.getsockname()[0]
                    self.logger.info(f"Using fallback IP {fallback_ip} for policy engine communication")
                    self.northbound_ip = fallback_ip
                except Exception:
                    self.logger.warning("Could not determine fallback IP, using loopback")
                    self.northbound_ip = '127.0.0.1'
                finally:
                    s.close()
        except Exception as e:
            self.logger.error(f"Error setting up northbound interface: {e}")
            self.northbound_ip = None
    
    def _get_interface_ip(self, interface_name: str) -> Optional[str]:
        """Get the IP address of a specific network interface."""
        try:
            if interface_name in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface_name)
                if netifaces.AF_INET in addrs:
                    return addrs[netifaces.AF_INET][0]['addr']
                self.logger.warning(f"No IPv4 address found for interface {interface_name}")
                return None
            else:
                available_ifaces = ', '.join(netifaces.interfaces())
                self.logger.warning(f"Interface {interface_name} not found. Available interfaces: {available_ifaces}")
                # Log more network diagnostics when northbound interface is missing
                if interface_name == self.northbound_interface:
                    self.logger.info("Missing northbound interface. Logging current network config:")
                    self.logger.info(f"Network interfaces: {available_ifaces}")
                    for iface in netifaces.interfaces():
                        if iface != 'lo':  # Skip loopback
                            try:
                                iface_info = netifaces.ifaddresses(iface)
                                self.logger.info(f"Interface {iface} details: {json.dumps(iface_info)}")
                            except Exception as e:
                                self.logger.warning(f"Could not get details for {iface}: {e}")
                    self.logger.info("Will use default route for policy engine communication")
                return None
        except Exception as e:
            self.logger.error(f"Error getting IP for interface {interface_name}: {e}")
            return None
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check if the action is allowed by the policy engine.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with policy decision and metadata
        """
        try:
            # Get the IP address of the northbound interface to bind to
            northbound_ip = getattr(self, 'northbound_ip', None)
            if not northbound_ip:
                # Try to ensure the northbound interface is available
                if not self._ensure_northbound_interface():
                    self.logger.warning(f"Could not find or create northbound interface, will use default route")
                northbound_ip = getattr(self, 'northbound_ip', None)
            
            # Setup request data
            headers = {'Content-Type': 'application/json'}
            payload = {
                'policy_type': policy_type,
                'context': context
            }
            max_retries = 3
            retry_delay = 1  # seconds
            
            original_create_conn = None
            try:
                if northbound_ip and northbound_ip != '127.0.0.1':
                    self.logger.info(f"Using northbound IP {northbound_ip} to connect to policy engine")
                    
                    # Configure the local socket to bind to the northbound interface
                    original_create_conn = socket.create_connection
                    
                    def patched_create_connection(address, *args, **kwargs):
                        """Patched socket creation to bind to the northbound interface."""
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.bind((northbound_ip, 0))
                        sock.connect(address)
                        return sock
                    
                    # Replace the socket.create_connection function temporarily
                    socket.create_connection = patched_create_connection
                else:
                    self.logger.info(f"No valid northbound IP available, using default network route")
                
                # Try the v1 API with retries
                for attempt in range(max_retries):
                    try:
                        self.logger.debug(f"Policy check attempt {attempt+1}/{max_retries} to {self.policy_engine_url}/api/v1/check")
                        response = requests.post(
                            f"{self.policy_engine_url}/api/v1/check",
                            headers=headers,
                            json=payload,
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            self.logger.info(f"Policy check result from v1 API: {result}")
                            return result
                        else:
                            self.logger.warning(f"Policy check failed with status {response.status_code}: {response.text}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                    except requests.exceptions.RequestException as e:
                        self.logger.warning(f"Error connecting to v1 policy API (attempt {attempt+1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                
                # Fall back to legacy endpoint with retries
                self.logger.info("Falling back to legacy policy endpoint")
                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            f"{self.policy_engine_url}/api/check_policy",
                            headers=headers,
                            json=payload,
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            self.logger.info(f"Policy check result from legacy API: {result}")
                            return result
                        else:
                            self.logger.warning(f"Legacy policy check failed: {response.status_code}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                    except requests.exceptions.RequestException as e:
                        self.logger.warning(f"Error connecting to legacy policy API (attempt {attempt+1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                
                # If all attempts fail, provide fallback policy
                self.logger.warning("All policy engine connection attempts failed, using fallback policy")
                return {"allowed": True, "reason": "Policy engine unavailable, using fallback"}
            
            finally:
                # Restore original socket.create_connection function
                if northbound_ip and original_create_conn:
                    socket.create_connection = original_create_conn
                
        except Exception as e:
            self.logger.error(f"Error checking policy: {e}")
            # Default to allowing if policy engine is unreachable
            return {"allowed": True, "reason": f"Error checking policy: {e}"}
    
    def start(self) -> bool:
        """
        Start the Ryu controller if app_path is provided.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.app_path:
            self.logger.warning("No app_path provided, cannot start controller")
            return False
        
        try:
            # Check if Ryu is installed
            try:
                import ryu
                self.logger.info("Ryu is installed")
            except ImportError:
                self.logger.error("Ryu is not installed")
                return False
            
            # Start Ryu controller as a subprocess
            cmd = f"ryu-manager --ofp-tcp-listen-port {self.port} {self.app_path}"
            self.process = subprocess.Popen(
                cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for controller to initialize
            time.sleep(5)
            
            # Check if process is running
            if self.process.poll() is not None:
                self.logger.error(f"Failed to start Ryu controller, return code: {self.process.returncode}")
                return False
            
            self.logger.info(f"Started Ryu controller with app: {self.app_path}")
            return self.connect()
            
        except Exception as e:
            self.logger.error(f"Error starting Ryu controller: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Connect to the Ryu controller's REST API.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Attempt to connect to the Ryu controller's REST API
            self.logger.info(f"RyuController: Attempting to connect to Ryu REST API at {self.base_url}/stats/switches with timeout {self.timeout}s")
            
            # Use the session object for connection
            response = self.session.get(f"{self.base_url}/stats/switches", timeout=self.timeout)
            
            # Log the status
            self.logger.info(f"RyuController: Connection attempt to {self.base_url}/stats/switches - Status: {response.status_code}")
            
            if response.status_code == 200:
                self.connected = True
                self.logger.info(f"RyuController: Successfully connected to Ryu controller REST API at {self.base_url}")
                # Refresh topology information
                self.refresh_topology()
                return True
            else:
                self.logger.error(f"RyuController: Failed to connect to Ryu controller REST API: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"RyuController: Connection error: {e}")
            self.connected = False
            return False
            
        except Exception as e:
            self.logger.error(f"RyuController: Unknown error during connection: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the Ryu controller.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        try:
            self.connected = False
            
            if self.process:
                self.process.terminate()
                self.process = None
                self.logger.info("Terminated Ryu controller process")
            
            self.logger.info("Disconnected from Ryu controller")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from Ryu controller: {e}")
            return False
    
    def refresh_topology(self) -> None:
        """
        Refresh the network topology information from the controller.
        
        Fetches updated information about switches, links, and hosts.
        """
        try:
            # Get switches
            switches = self.get_switches()
            
            # Try to get links (might not be available in all Ryu apps)
            try:
                response = self.session.get(f"{self.base_url}/topology/links", timeout=self.timeout)
                if response.status_code == 200:
                    self.links = response.json()
                else:
                    self.logger.info(f"RyuController: Topology links endpoint ({self.base_url}/topology/links) not found ({response.status_code}). Link information will be unavailable.")
                    self.links = []
            except Exception as e:
                self.logger.info(f"RyuController: Topology links endpoint ({self.base_url}/topology/links) not available: {e}")
                self.links = []
            
            # Try to get hosts (might not be available in all Ryu apps)
            try:
                response = self.session.get(f"{self.base_url}/topology/hosts", timeout=self.timeout)
                if response.status_code == 200:
                    self.hosts = response.json()
                else:
                    self.logger.info(f"RyuController: Topology hosts endpoint ({self.base_url}/topology/hosts) not found ({response.status_code}). Host information will be unavailable.")
                    self.hosts = []
            except Exception as e:
                self.logger.info(f"RyuController: Topology hosts endpoint ({self.base_url}/topology/hosts) not available: {e}")
                self.hosts = []
            
            self.logger.info(f"RyuController: Topology refreshed: {len(switches)} switches, {len(self.links)} links, {len(self.hosts)} hosts.")
            
        except Exception as e:
            self.logger.error(f"RyuController: Error refreshing topology: {e}")
    
    def get_topology(self) -> Dict[str, Any]:
        """
        Get the current network topology.
        
        Returns:
            Dict containing the network topology
        """
        if not self.connected:
            self.refresh_topology()
        
        return {
            "switches": self.switches,
            "links": self.links,
            "hosts": self.hosts
        }
    
    def add_flow(self, switch, priority, match, actions, idle_timeout=0, hard_timeout=0):
        """
        Add a flow rule to an OpenFlow switch.
        
        Args:
            switch: Switch ID or object
            priority: Flow priority
            match: Match criteria dictionary
            actions: List of action dictionaries
            idle_timeout: Idle timeout in seconds
            hard_timeout: Hard timeout in seconds
            
        Returns:
            bool: True if flow was added successfully
        """
        try:
            # Extract switch DPID
            dpid_value = None
            dpid_original = None
            
            if isinstance(switch, dict):
                # If switch is a dictionary, try to get 'id' first (which should be integer) 
                # then fall back to 'dpid' (which might be a hex string)
                dpid_original = switch.get('id', switch.get('dpid', ''))
            else:
                # If switch is not a dictionary, use it directly
                dpid_original = switch
                
            # Log the original DPID for debugging
            self.logger.debug(f"RyuController: Extracting DPID from: {dpid_original} of type {type(dpid_original)}")
            
            # Convert to integer DPID value based on type
            if isinstance(dpid_original, int):
                # Already an integer
                dpid_value = dpid_original
            elif isinstance(dpid_original, str):
                if dpid_original.startswith('0x'):
                    # Explicit hex format with 0x prefix
                    dpid_value = int(dpid_original, 16)
                elif all(c in '0123456789abcdefABCDEF' for c in dpid_original):
                    # Looks like a hex string without 0x prefix (like '000072935aa3324a')
                    dpid_value = int(dpid_original, 16)
                else:
                    # Try as decimal string
                    try:
                        dpid_value = int(dpid_original)
                    except ValueError:
                        self.logger.error(f"Invalid DPID format: {dpid_original}")
                        return False
            else:
                self.logger.error(f"DPID must be string or integer, got {type(dpid_original)}: {dpid_original}")
                return False
            
            # Log the converted DPID
            self.logger.debug(f"RyuController: Converted DPID to integer value: {dpid_value} (original: {dpid_original})")
            
            # Translate OpenFlow port names to values understood by Ryu
            modified_actions = []
            
            # Port name to numeric value mapping
            port_map = {
                'NORMAL': 0xfffffffa,    # OFPP_NORMAL value in OpenFlow
                'CONTROLLER': 0xfffffffd, # OFPP_CONTROLLER value
                'ALL': 0xffffffff,       # OFPP_ALL value
                'LOCAL': 0xfffffffe,     # OFPP_LOCAL value
                'IN_PORT': 0xfffffff8,   # OFPP_IN_PORT value
            }
            
            for action in actions:
                new_action = dict(action)  # Create a copy
                
                # Convert port names to appropriate values for Ryu
                if action.get('type') == 'OUTPUT' and isinstance(action.get('port'), str):
                    port_name = action.get('port').upper()
                    
                    if port_name in port_map:
                        new_action['port'] = port_map[port_name]
                        self.logger.info(f"Converting port name '{port_name}' to hex value {hex(port_map[port_name])}")
                    else:
                        # Try to convert to an integer if it's not a special name
                        try:
                            new_action['port'] = int(port_name)
                            self.logger.info(f"Converting port name '{port_name}' to integer {new_action['port']}")
                        except ValueError:
                            self.logger.warning(f"Unknown port name '{port_name}', keeping as is")
                
                modified_actions.append(new_action)
                
            # Construct URL
            url = f"{self.base_url}/stats/flowentry/add"
            
            # Construct data payload
            data = {
                'dpid': dpid_value,
                'priority': priority,
                'match': match,
                'actions': modified_actions,
                'flags': 0,
                'version': self.OF_VERSIONS[0],  # Use OpenFlow 1.3 version number
                'type': 'OFPT_FLOW_MOD'  # Explicitly set message type for flow modification
            }
            
            # Add timeouts if provided
            if idle_timeout > 0:
                data['idle_timeout'] = idle_timeout
            if hard_timeout > 0:
                data['hard_timeout'] = hard_timeout
                
            # Send request
            self.logger.info(f"Adding flow to switch {dpid_value} (original: {dpid_original})")
            self.logger.info(f"Match: {match}")
            self.logger.info(f"Actions: {modified_actions}")
            
            response = self.session.post(url, json=data, timeout=self.timeout)
            
            if response.status_code == 200:
                self.logger.info(f"Successfully added flow to switch {dpid_value}")
                return True
            else:
                self.logger.error(f"Failed to add flow: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                self.logger.error(f"Request URL: {url}")
                self.logger.error(f"Request Data: {data}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding flow: {e}", exc_info=True)
            return False
    
    def _validate_flow_rule(self, match, actions):
        """Validate flow rule and log potential issues"""
        # Check match dict for common issues
        if match:
            # Check for incomplete layer specifications
            if 'ip_proto' in match and 'eth_type' not in match:
                self.logger.warning("Match includes ip_proto but missing eth_type (should be 0x0800 for IPv4)")
            
            if ('tcp_src' in match or 'tcp_dst' in match) and 'ip_proto' not in match:
                self.logger.warning("Match includes TCP ports but missing ip_proto (should be 6 for TCP)")
            
            if ('udp_src' in match or 'udp_dst' in match) and 'ip_proto' not in match:
                self.logger.warning("Match includes UDP ports but missing ip_proto (should be 17 for UDP)")
            
            # Check for invalid field types
            for field, value in match.items():
                if field == 'eth_type' and not isinstance(value, int):
                    self.logger.warning(f"eth_type should be an integer (e.g., 0x0800), got {type(value)}: {value}")
                
                if field in ('ip_proto', 'tcp_src', 'tcp_dst', 'udp_src', 'udp_dst') and not isinstance(value, int):
                    self.logger.warning(f"{field} should be an integer, got {type(value)}: {value}")
        
        # Check actions list for common issues
        if actions:
            for action in actions:
                if not isinstance(action, dict):
                    self.logger.warning(f"Action should be a dictionary, got {type(action)}: {action}")
                    continue
                
                if 'type' not in action:
                    self.logger.warning(f"Action missing 'type' field: {action}")
                
                # Check for OUTPUT vs FORWARD confusion
                if action.get('type') == 'FORWARD':
                    self.logger.warning("'FORWARD' is not a standard OpenFlow action type, should use 'OUTPUT' instead")
                
                # Check for NORMAL as port in OUTPUT actions
                if action.get('type') == 'OUTPUT' and action.get('port') == 'NORMAL':
                    self.logger.warning("Using 'NORMAL' as port for OUTPUT action may not be supported; try 'CONTROLLER' or a specific port number")
    
    def remove_flow(self, switch_id: Union[str, int], match: Dict[str, Any] = None, priority: Optional[int] = None) -> bool:
        """
        Delete flow entries from a switch.
        
        Args:
            switch_id: Switch ID
            match: Flow match criteria (None to delete all flows)
            priority: Priority of the flow to delete (optional, requires match)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return False
        
        try:
            if match:
                # Delete specific flow
                flow_url = f"{self.base_url}/stats/flowentry/delete"
                
                flow_data = {
                    "dpid": int(switch_id) if isinstance(switch_id, str) and switch_id.isdigit() else switch_id,
                    "match": match
                }
                if priority is not None:
                     flow_data["priority"] = priority
                
                self.logger.debug(f"RyuController: Deleting flow on {switch_id} with payload: {json.dumps(flow_data)}")
                response = requests.post(flow_url, json=flow_data)
            else:
                # Delete all flows (cannot specify match or priority)
                if priority is not None:
                     self.logger.warning("Cannot specify priority when deleting all flows. Ignoring priority.")
                flow_url = f"{self.base_url}/stats/flowentry/clear/{switch_id}"
                self.logger.debug(f"RyuController: Clearing all flows on {switch_id}")
                response = requests.delete(flow_url)
            
            if response.status_code == 200:
                self.logger.info(f"Deleted flows from switch {switch_id}")
                return True
            
            self.logger.error(f"Failed to delete flows: {response.status_code} {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting flows: {e}")
            return False
    
    def get_flows(self, switch_id: Union[str, int]) -> List[Dict[str, Any]]:
        """
        Get all flow entries from a switch.
        
        Args:
            switch_id: Switch ID
            
        Returns:
            List of flow entries
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return []
        
        try:
            flow_url = f"{self.base_url}/stats/flow/{switch_id}"
            response = requests.get(flow_url)
            
            if response.status_code == 200:
                flows = response.json().get(str(switch_id), [])
                self.logger.info(f"Got {len(flows)} flows from switch {switch_id}")
                return flows
            
            self.logger.error(f"Failed to get flows: {response.status_code} {response.text}")
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting flows: {e}")
            return []
    
    def get_flow_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all flows in the network.
        
        Returns:
            Dict containing flow statistics
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return {}
        
        try:
            flow_stats = {}
            
            for switch_id in self.switches.keys():
                flows = self.get_flows(switch_id)
                flow_stats[switch_id] = flows
            
            return flow_stats
            
        except Exception as e:
            self.logger.error(f"Error getting flow statistics: {e}")
            return {}
    
    def get_port_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all ports in the network.
        
        Returns:
            Dict containing port statistics
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return {}
        
        try:
            port_stats = {}
            
            for switch_id in self.switches.keys():
                port_url = f"{self.base_url}/stats/port/{switch_id}"
                response = requests.get(port_url)
                
                if response.status_code == 200:
                    port_stats[switch_id] = response.json().get(str(switch_id), [])
            
            return port_stats
            
        except Exception as e:
            self.logger.error(f"Error getting port statistics: {e}")
            return {}
    
    def create_qos_policy(self, switch_id: Union[str, int], policy_name: str, 
                         policy_type: str, policy_params: Dict[str, Any]) -> bool:
        """
        Create a QoS policy on a switch.
        
        Args:
            switch_id: Switch ID
            policy_name: Name of the policy
            policy_type: Type of QoS policy
            policy_params: Parameters for the policy
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return False
        
        try:
            qos_url = f"{self.base_url}/qos/rules/{switch_id}"
            
            qos_data = {
                "type": policy_type,
                "name": policy_name,
                "params": policy_params
            }
            
            response = requests.post(qos_url, json=qos_data)
            
            if response.status_code == 200:
                self.logger.info(f"Created QoS policy {policy_name} on switch {switch_id}")
                return True
            
            self.logger.error(f"Failed to create QoS policy: {response.status_code} {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error creating QoS policy: {e}")
            return False
    
    def create_qos_queue(self, switch_id: Union[str, int], port: int, 
                        queue_config: Dict[str, Any]) -> bool:
        """
        Create a QoS queue on a switch port.
        
        Args:
            switch_id: Switch ID
            port: Port number
            queue_config: Queue configuration parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return False
        
        try:
            queue_url = f"{self.base_url}/qos/queue/{switch_id}/{port}"
            
            # Ensure queue_config has required fields
            if "type" not in queue_config:
                queue_config["type"] = "min-rate"
            
            response = requests.post(queue_url, json=queue_config)
            
            if response.status_code == 200:
                self.logger.info(f"Created QoS queue on switch {switch_id} port {port}")
                return True
            
            self.logger.error(f"Failed to create QoS queue: {response.status_code} {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error creating QoS queue: {e}")
            return False
    
    def add_meter(self, switch_id: Union[str, int], meter_config: Dict[str, Any]) -> bool:
        """
        Add a meter for rate limiting on a switch.
        
        Args:
            switch_id: Switch ID
            meter_config: Meter configuration with meter_id, flags, and bands
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return False
        
        try:
            meter_url = f"{self.base_url}/stats/meterentry/add"
            
            # Ensure meter_config has required fields
            required_fields = ["meter_id", "flags", "bands"]
            for field in required_fields:
                if field not in meter_config:
                    self.logger.error(f"Missing required field for meter: {field}")
                    return False
            
            # Add dpid to meter_config
            meter_data = {
                "dpid": switch_id if isinstance(switch_id, int) else int(switch_id),
                "meter_id": meter_config["meter_id"],
                "flags": meter_config["flags"],
                "bands": meter_config["bands"]
            }
            
            response = requests.post(meter_url, json=meter_data)
            
            if response.status_code == 200:
                self.logger.info(f"Added meter {meter_config['meter_id']} to switch {switch_id}")
                return True
            
            self.logger.error(f"Failed to add meter: {response.status_code} {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error adding meter: {e}")
            return False
    
    def create_path(self, src_ip: str, dst_ip: str, path_nodes: List[str], 
                   priority: int = 150, match_criteria: Dict[str, Any] = None) -> bool:
        """
        Create a specific path for traffic between source and destination IPs.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            path_nodes: List of switch IDs that form the path
            priority: Priority for the flow rules
            match_criteria: Additional match criteria beyond src/dst IPs
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return False
        
        try:
            # Validate path
            if len(path_nodes) < 2:
                self.logger.error("Path must include at least two nodes")
                return False
            
            # Check if switches exist
            for node in path_nodes:
                if node not in self.switches:
                    self.logger.error(f"Switch {node} does not exist in the topology")
                    return False
            
            # Find the links between path nodes
            path_links = []
            for i in range(len(path_nodes) - 1):
                current_node = path_nodes[i]
                next_node = path_nodes[i + 1]
                
                # Find link between current_node and next_node
                link_found = False
                for link in self.links:
                    if (link["src"]["dpid"] == current_node and link["dst"]["dpid"] == next_node) or \
                       (link["src"]["dpid"] == next_node and link["dst"]["dpid"] == current_node):
                        path_links.append(link)
                        link_found = True
                        break
                
                if not link_found:
                    self.logger.error(f"No link found between {current_node} and {next_node}")
                    return False
            
            success = True
            
            # Create basic match if none provided
            if match_criteria is None:
                match_criteria = {}
            
            # Add src/dst IP to match criteria
            match_criteria["ipv4_src"] = src_ip
            match_criteria["ipv4_dst"] = dst_ip
            
            # Add flow entries to each switch in the path
            for i, node in enumerate(path_nodes):
                # Skip last node if it's a host and not a switch
                if i == len(path_nodes) - 1 and node not in self.switches:
                    continue
                    
                # Get input and output ports
                if i == 0:
                    # First node
                    in_port = 0  # Will be determined by packet-in
                    next_link = path_links[i]
                    if next_link["src"]["dpid"] == node:
                        out_port = next_link["src"]["port"]
                    else:
                        out_port = next_link["dst"]["port"]
                elif i == len(path_nodes) - 1:
                    # Last node
                    prev_link = path_links[i - 1]
                    if prev_link["src"]["dpid"] == node:
                        in_port = prev_link["src"]["port"]
                    else:
                        in_port = prev_link["dst"]["port"]
                    out_port = 0  # Will be determined by destination
                else:
                    # Middle node
                    prev_link = path_links[i - 1]
                    next_link = path_links[i]
                    
                    if prev_link["src"]["dpid"] == node:
                        in_port = prev_link["src"]["port"]
                    else:
                        in_port = prev_link["dst"]["port"]
                        
                    if next_link["src"]["dpid"] == node:
                        out_port = next_link["src"]["port"]
                    else:
                        out_port = next_link["dst"]["port"]
                
                # Add in_port to match criteria if it's not 0
                node_match = dict(match_criteria)
                if in_port > 0:
                    node_match["in_port"] = in_port
                
                # Create actions - output to specific port
                if out_port > 0:
                    actions = [{"type": "OUTPUT", "port": out_port}]
                else:
                    # Let controller determine output port based on destination
                    actions = [{"type": "OUTPUT", "port": "NORMAL"}]
                
                # Add flow rule
                flow_success = self.add_flow(
                    node,
                    priority=priority,
                    match=node_match,
                    actions=actions,
                    idle_timeout=0,
                    hard_timeout=0
                )
                
                if not flow_success:
                    self.logger.error(f"Failed to add flow rule to switch {node}")
                    success = False
            
            if success:
                self.logger.info(f"Created path from {src_ip} to {dst_ip} through {path_nodes}")
            else:
                self.logger.warning(f"Partially created path from {src_ip} to {dst_ip}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error creating path: {e}")
            return False
    
    def get_qos_policies(self, switch_id: Union[str, int]) -> List[Dict[str, Any]]:
        """
        Get all QoS policies from a switch.
        
        Args:
            switch_id: Switch ID
            
        Returns:
            List of QoS policies
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return []
        
        try:
            qos_url = f"{self.base_url}/qos/rules/{switch_id}"
            response = requests.get(qos_url)
            
            if response.status_code == 200:
                policies = response.json().get("rules", [])
                self.logger.info(f"Got {len(policies)} QoS policies from switch {switch_id}")
                return policies
            
            self.logger.error(f"Failed to get QoS policies: {response.status_code} {response.text}")
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting QoS policies: {e}")
            return []
    
    def get_switch_ports(self, dpid: int) -> List[Dict[str, Any]]:
        """
        Get port details for a specific switch.

        Args:
            dpid: Datapath ID of the switch.

        Returns:
            List of ports, each with details.
        """
        try:
            self.logger.debug(f"RyuController: Retrieving port description for switch {dpid}")
            port_url = f"{self.base_url}/stats/portdesc/{dpid}"
            response = self.session.get(port_url, timeout=self.timeout)

            if response.status_code == 200:
                ports_data = response.json()
                if str(dpid) in ports_data:
                    return ports_data[str(dpid)]
                else:
                    self.logger.warning(f"No port data found for DPID {dpid} in response: {ports_data}")
                    return []
            else:
                self.logger.error(f"RyuController: Failed to get port description for switch {dpid}. Status: {response.status_code}, Response: {response.text}")
                return []
        except requests.exceptions.Timeout:
            self.logger.error(f"RyuController: Request timed out when retrieving port description for switch {dpid}")
            return []
        except requests.exceptions.ConnectionError:
            self.logger.error(f"RyuController: Connection error when retrieving port description for switch {dpid}")
            return []
        except Exception as e:
            self.logger.error(f"RyuController: Error retrieving port description for switch {dpid}: {e}")
            return []

    def get_switches(self):
        """
        Get list of connected switches.
        
        Returns:
            List of switches, each with id, ports, etc.
        """
        try:
            self.logger.info("RyuController: Retrieving connected switches")
            response = self.session.get(f"{self.base_url}/stats/switches", timeout=self.timeout)
            
            if response.status_code != 200:
                self.logger.error(f"RyuController: Failed to get switches. Status: {response.status_code}")
                return []
            
            switch_data_from_api = response.json()
            self.logger.debug(f"RyuController: Found switch data from API (raw): {switch_data_from_api}")

            if not isinstance(switch_data_from_api, list):
                self.logger.error(f"RyuController: Unexpected format for switch data from API. Expected list, got {type(switch_data_from_api)}. Data: {switch_data_from_api}")
                return []

            switches = []
            for item in switch_data_from_api:
                dpid_int = None
                raw_dpid_for_api_calls = None

                if isinstance(item, int):
                    dpid_int = item
                    raw_dpid_for_api_calls = item
                    self.logger.debug(f"RyuController: Processing DPID as integer: {dpid_int}")
                elif isinstance(item, dict):
                    self.logger.debug(f"RyuController: Processing item as dictionary: {item}")
                    if 'dpid' in item:
                        val = item['dpid']
                        if isinstance(val, int):
                            dpid_int = val
                            raw_dpid_for_api_calls = val
                        elif isinstance(val, str):
                            try:
                                dpid_int = int(val, 16)
                                raw_dpid_for_api_calls = dpid_int
                                self.logger.debug(f"RyuController: Extracted DPID string '{val}', converted to int {dpid_int}")
                            except ValueError:
                                self.logger.error(f"RyuController: Could not convert DPID string '{val}' to integer. Skipping this switch.")
                                continue
                        else:
                            self.logger.error(f"RyuController: DPID value in dict is neither int nor string: {val}. Skipping.")
                            continue
                    elif 'id' in item and isinstance(item['id'], int):
                        dpid_int = item['id']
                        raw_dpid_for_api_calls = item['id']
                        self.logger.debug(f"RyuController: Extracted DPID from 'id' field: {dpid_int}")
                    else:
                        self.logger.error(f"RyuController: Dictionary item {item} does not contain a usable 'dpid' or 'id' field. Skipping.")
                        continue
                else:
                    self.logger.error(f"RyuController: Unexpected item type in switch data: {type(item)}. Item: {item}. Skipping.")
                    continue
                
                if dpid_int is None:
                    self.logger.error(f"RyuController: Failed to extract a valid integer DPID from item: {item}. Skipping.")
                    continue

                try:
                    formatted_dpid_str = f"{dpid_int:016x}"
                    self.logger.debug(f"RyuController: Processing DPID - int: {dpid_int}, hex_str: {formatted_dpid_str}, raw_for_api: {raw_dpid_for_api_calls}")

                    switch_info = {
                        'dpid': formatted_dpid_str,
                        'id': dpid_int, 
                        'ports': self.get_switch_ports(raw_dpid_for_api_calls)
                    }
                    
                    try:
                        desc_response = self.session.get(f"{self.base_url}/stats/desc/{raw_dpid_for_api_calls}", timeout=self.timeout)
                        if desc_response.status_code == 200:
                            desc_data = desc_response.json().get(str(raw_dpid_for_api_calls), {})
                            if desc_data:
                                switch_info.update({
                                    'manufacturer': desc_data.get('mfr_desc', ''),
                                    'hardware': desc_data.get('hw_desc', ''),
                                    'software': desc_data.get('sw_desc', ''),
                                    'serial': desc_data.get('serial_num', ''),
                                    'description': desc_data.get('dp_desc', '')
                                })
                        else:
                            self.logger.warning(f"Failed to get switch description for DPID {raw_dpid_for_api_calls}. Status: {desc_response.status_code}")
                    except Exception as e:
                        self.logger.warning(f"Failed to get switch description for DPID {raw_dpid_for_api_calls}: {e}")
                    
                    switches.append(switch_info)
                except Exception as e:
                    self.logger.error(f"Error processing data for resolved DPID_INT {dpid_int} (from item {item}): {e}", exc_info=True)
            
            self.logger.info(f"RyuController: Processed {len(switches)} switches")
            return switches
            
        except requests.exceptions.Timeout:
            self.logger.error("RyuController: Request timed out when retrieving switches")
            return []
        except requests.exceptions.ConnectionError:
            self.logger.error("RyuController: Connection error when retrieving switches")
            return []
        except Exception as e:
            self.logger.error(f"RyuController: Error retrieving switches: {e}")
            return []

    def get_links(self) -> List[Dict[str, Any]]:
        """
        Get all links in the network.
        
        Returns:
            List of links
        """
        return self.links
    
    def get_hosts(self) -> List[Dict[str, Any]]:
        """
        Get all hosts in the network.
        
        Returns:
            List of hosts
        """
        return list(self.hosts.values()) if isinstance(self.hosts, dict) else self.hosts
    
    def get_controller_info(self) -> Dict[str, Any]:
        """
        Get information about the controller.
        
        Returns:
            Dict containing controller information
        """
        return {
            "type": "ryu",
            "host": self.host,
            "port": self.port,
            "connected": self.connected
        }
    
    def optimize_network(self) -> bool:
        """
        Optimize the network for federated learning traffic.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to controller")
            return False
        
        try:
            # Check policy before optimizing network
            policy_context = {
                "operation": "optimize_network"
            }
            
            policy_result = self.check_policy("network_qos", policy_context)
            
            if not policy_result.get("allowed", True):
                self.logger.error(f"Policy violation: {policy_result.get('reason', 'Unknown reason')}")
                if "violations" in policy_result:
                    for violation in policy_result["violations"]:
                        self.logger.error(f"Violation: {violation}")
                return False
                
            # Refresh topology to get latest network state
            self.refresh_topology()
            
            # Identify switches and hosts
            switches = self.get_switches()
            hosts = self.get_hosts()
            
            if not switches or not hosts:
                self.logger.warning("Not enough network elements to optimize")
                return False
            
            # Optimization logic:
            # 1. Clear all flows on all switches
            for switch in switches:
                switch_id = switch.get("id")
                self.remove_flow(switch_id)
            
            # 2. Create basic connectivity flows for all hosts
            for host in hosts:
                if isinstance(host, dict):
                    mac = host.get("mac")
                    switch_id = host.get("port", {}).get("dpid")
                    port_no = host.get("port", {}).get("port_no")
                    
                    if not mac or not switch_id or not port_no:
                        continue
                    
                    # Flow to the host
                    self.add_flow(
                        switch_id,
                        100,
                        {"dl_dst": mac},
                        [{"type": "OUTPUT", "port": port_no}]
                    )
                    
                    # Flow from the host
                    self.add_flow(
                        switch_id,
                        100,
                        {"dl_src": mac, "in_port": port_no},
                        [{"type": "OUTPUT", "port": "FLOOD"}]
                    )
            
            # 3. Create QoS policies for federated learning traffic
            for switch in switches:
                switch_id = switch.get("id")
                
                # Create a QoS policy to prioritize federated learning traffic
                # This assumes certain ports (e.g., 8080) are used for FL traffic
                self.create_qos_policy(
                    switch_id,
                    "federated_learning",
                    "priority",
                    {
                        "tcp_dst": 8080,
                        "priority": 2  # High priority
                    }
                )
            
            self.logger.info("Network optimized for federated learning")
            return True
            
        except Exception as e:
            self.logger.error(f"Error optimizing network: {e}")
            return False

    def initialize(self) -> bool:
        """Initialize the controller. Required abstract method implementation.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            self.logger.info("Initializing RyuController")
            return self.connect()
        except Exception as e:
            self.logger.error(f"Failed to initialize RyuController: {str(e)}")
            return False

    def stop(self) -> bool:
        """Stop the controller. Required abstract method implementation.

        Returns:
            bool: True if controller was stopped successfully, False otherwise
        """
        try:
            self.logger.info("Stopping RyuController")
            return self.disconnect()
        except Exception as e:
            self.logger.error(f"Failed to stop RyuController: {str(e)}")
            return False

    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        """Apply a network policy. Required abstract method implementation.

        Args:
            policy: The policy configuration to apply

        Returns:
            bool: True if policy was applied successfully, False otherwise
        """
        try:
            self.logger.info(f"Applying policy: {policy.get('name', 'Unnamed policy')}")
            policy_type = policy.get('type', policy.get('policy_type', 'unknown'))

            if policy_type == 'qos':
                # Apply QoS policy
                switch_id = policy.get('switch_id')
                policy_name = policy.get('name', 'qos_policy')
                policy_params = {
                    'type': policy.get('qos_type', 'rate_limit'),
                    'rate': policy.get('rate', 1000000),  # Default to 1Mbps
                    'burst_size': policy.get('burst_size', 100000),
                    'priority': policy.get('priority', 100)
                }
                return self.create_qos_policy(switch_id, policy_name, policy_params['type'], policy_params)
            
            elif policy_type == 'path':
                # Apply path-based policy
                src_ip = policy.get('src_ip')
                dst_ip = policy.get('dst_ip')
                path_nodes = policy.get('path', [])
                priority = policy.get('priority', 100)
                return self.create_path(src_ip, dst_ip, path_nodes, priority)
            
            elif policy_type == 'security':
                # Apply security policy - typically block rules
                match = policy.get('match', {})
                switch_id = policy.get('switch_id', '*')
                return self.remove_flow(switch_id, match)
                
            elif policy_type == 'network_security':
                # Apply network security policy through the policy_switch app
                policy_id = policy.get('id', f"policy_{int(time.time())}")
                
                # Create a dictionary with this single policy
                network_policies = {policy_id: policy}
                
                # Call the REST API of the policy_switch app
                try:
                    url = f"{self.base_url}/network/policies/update"
                    response = requests.post(url, json=network_policies, timeout=10)
                    
                    if response.status_code == 200:
                        result = response.json()
                        self.logger.info(f"Successfully applied network security policy: {result.get('flows_installed', 0)} flows installed")
                        return True
                    else:
                        self.logger.error(f"Failed to apply network security policy: {response.status_code} - {response.text}")
                        return False
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error applying network security policy: {e}")
                    return False
            
            else:
                self.logger.warning(f"Unsupported policy type: {policy_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to apply policy: {str(e)}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current controller status. Required abstract method implementation.

        Returns:
            Dict[str, Any]: Status information
        """
        try:
            status = {
                "controller": self.get_controller_info(),
                "switches": self.get_switches(),
                "links": self.get_links(),
                "hosts": self.get_hosts(),
                "uptime": time.time() - self._start_time if hasattr(self, '_start_time') else 0
            }
            return status
        except Exception as e:
            self.logger.error(f"Failed to get controller status: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from the controller. Required abstract method implementation.

        Returns:
            Dict[str, Any]: Controller metrics
        """
        try:
            metrics = {
                "flow_stats": self.get_flow_stats(),
                "port_stats": self.get_port_stats(),
                "timestamp": time.time()
            }
            return metrics
        except Exception as e:
            self.logger.error(f"Failed to get controller metrics: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _ensure_northbound_interface(self):
        """
        Ensure the northbound interface is available.
        
        This method tries to set up the northbound interface if it doesn't exist,
        or falls back gracefully if it can't be created.
        
        Returns:
            bool: True if the interface is available, False otherwise
        """
        try:
            # If we already have a northbound IP, it's already set up
            if hasattr(self, 'northbound_ip') and self.northbound_ip:
                self.logger.debug(f"Northbound interface already configured with IP {self.northbound_ip}")
                return True
                
            # Check if the interface exists
            if_ip = self._get_interface_ip(self.northbound_interface)
            if if_ip:
                self.logger.info(f"Northbound interface {self.northbound_interface} exists with IP {if_ip}")
                self.northbound_ip = if_ip
                return True
                
            # Interface doesn't exist
            self.logger.warning(f"Northbound interface {self.northbound_interface} doesn't exist")
            
            # Try to find a fallback interface
            try:
                # Get a list of all network interfaces
                import netifaces
                interfaces = netifaces.interfaces()
                for iface in interfaces:
                    if iface != 'lo':  # Skip loopback
                        ip = self._get_interface_ip(iface)
                        if ip:
                            self.logger.info(f"Using fallback interface {iface} with IP {ip}")
                            self.northbound_interface = iface
                            self.northbound_ip = ip
                            return True
            except ImportError:
                self.logger.warning("netifaces module not available, can't enumerate interfaces")
            
            # If all else fails, use a dummy connection approach
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Doesn't need to be reachable
                s.connect(('10.255.255.255', 1))
                ip = s.getsockname()[0]
                self.logger.info(f"Using default route interface with IP {ip}")
                self.northbound_ip = ip
                return True
            except Exception as e:
                self.logger.error(f"Failed to find any usable network interface: {e}")
                self.northbound_ip = '127.0.0.1'  # Last resort
                return False
            finally:
                s.close()
        except Exception as e:
            self.logger.error(f"Error ensuring northbound interface: {e}")
            self.northbound_ip = None
            return False
    
    def get_port_statistics(self, dpid: str = None) -> Dict[str, Any]:
        """
        Get real port statistics from OpenFlow switches.
        
        Args:
            dpid: Switch DPID (hex string). If None, get stats from all switches.
            
        Returns:
            Dict containing port statistics with bandwidth calculations
        """
        if not self.connected:
            self.logger.warning("Not connected to Ryu controller")
            return {}
            
        try:
            current_time = time.time()
            port_stats = {}
            
            # Get switches to query
            switches_to_query = [dpid] if dpid else [sw.get('dpid', sw.get('id')) for sw in self.get_switches()]
            
            for switch_dpid in switches_to_query:
                if not switch_dpid:
                    continue
                    
                # Query port stats from Ryu REST API
                url = f"{self.base_url}/stats/port/{switch_dpid}"
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    switch_port_stats = response.json().get(switch_dpid, [])
                    
                    # Calculate bandwidth for each port
                    for port_stat in switch_port_stats:
                        port_no = port_stat.get('port_no')
                        cache_key = f"{switch_dpid}_{port_no}"
                        
                        # Get previous stats for bandwidth calculation
                        prev_stats = self.port_stats_cache.get(cache_key)
                        
                        if prev_stats and current_time > prev_stats['timestamp']:
                            time_delta = current_time - prev_stats['timestamp']
                            
                            # Calculate byte deltas
                            rx_bytes_delta = port_stat.get('rx_bytes', 0) - prev_stats.get('rx_bytes', 0)
                            tx_bytes_delta = port_stat.get('tx_bytes', 0) - prev_stats.get('tx_bytes', 0)
                            
                            # Calculate bandwidth in Mbps
                            rx_mbps = (rx_bytes_delta * 8) / (time_delta * 1_000_000) if time_delta > 0 else 0
                            tx_mbps = (tx_bytes_delta * 8) / (time_delta * 1_000_000) if time_delta > 0 else 0
                            
                            port_stat['rx_mbps'] = round(max(0, rx_mbps), 4)
                            port_stat['tx_mbps'] = round(max(0, tx_mbps), 4)
                            port_stat['total_mbps'] = round(port_stat['rx_mbps'] + port_stat['tx_mbps'], 4)
                        else:
                            # First collection, no bandwidth calculation possible
                            port_stat['rx_mbps'] = 0.0
                            port_stat['tx_mbps'] = 0.0
                            port_stat['total_mbps'] = 0.0
                        
                        # Cache current stats for next calculation
                        self.port_stats_cache[cache_key] = {
                            'timestamp': current_time,
                            'rx_bytes': port_stat.get('rx_bytes', 0),
                            'tx_bytes': port_stat.get('tx_bytes', 0)
                        }
                    
                    port_stats[switch_dpid] = switch_port_stats
                else:
                    self.logger.warning(f"Failed to get port stats for switch {switch_dpid}: {response.status_code}")
            
            self.last_stats_collection = current_time
            self.logger.debug(f"Collected port statistics for {len(port_stats)} switches")
            return port_stats
            
        except Exception as e:
            self.logger.error(f"Error collecting port statistics: {e}")
            return {}

    def get_flow_statistics(self, dpid: str = None) -> Dict[str, Any]:
        """
        Get real flow statistics from OpenFlow switches.
        
        Args:
            dpid: Switch DPID (hex string). If None, get stats from all switches.
            
        Returns:
            Dict containing flow statistics with proper match fields and actions
        """
        if not self.connected:
            self.logger.warning("Not connected to Ryu controller")
            return {}
            
        try:
            current_time = time.time()
            flow_stats = {}
            
            # Get switches to query
            switches_to_query = [dpid] if dpid else [sw.get('dpid', sw.get('id')) for sw in self.get_switches()]
            
            for switch_dpid in switches_to_query:
                if not switch_dpid:
                    continue
                    
                # Query flow stats from Ryu REST API
                url = f"{self.base_url}/stats/flow/{switch_dpid}"
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    switch_flow_stats = response.json().get(switch_dpid, [])
                    
                    # Process and enhance flow stats
                    processed_flows = []
                    for flow_stat in switch_flow_stats:
                        processed_flow = self._process_flow_entry(flow_stat)
                        processed_flows.append(processed_flow)
                    
                    flow_stats[switch_dpid] = processed_flows
                    
                    # Cache flow stats
                    self.flow_stats_cache[switch_dpid] = {
                        'timestamp': current_time,
                        'flows': processed_flows
                    }
                else:
                    self.logger.warning(f"Failed to get flow stats for switch {switch_dpid}: {response.status_code}")
            
            self.logger.debug(f"Collected flow statistics for {len(flow_stats)} switches")
            return flow_stats
            
        except Exception as e:
            self.logger.error(f"Error collecting flow statistics: {e}")
            return {}

    def _process_flow_entry(self, flow_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a flow entry to extract meaningful match criteria and actions.
        
        Args:
            flow_entry: Raw flow entry from OpenFlow
            
        Returns:
            Processed flow entry with readable match and action descriptions
        """
        processed = flow_entry.copy()
        
        # Process match fields
        match = flow_entry.get('match', {})
        match_description = []
        
        # Common match fields
        if 'in_port' in match:
            match_description.append(f"in_port={match['in_port']}")
        if 'eth_src' in match:
            match_description.append(f"eth_src={match['eth_src']}")
        if 'eth_dst' in match:
            match_description.append(f"eth_dst={match['eth_dst']}")
        if 'eth_type' in match:
            eth_type = match['eth_type']
            if eth_type == 0x0800:
                match_description.append("eth_type=IPv4")
            elif eth_type == 0x0806:
                match_description.append("eth_type=ARP")
            else:
                match_description.append(f"eth_type=0x{eth_type:04x}")
        if 'ipv4_src' in match:
            match_description.append(f"ipv4_src={match['ipv4_src']}")
        if 'ipv4_dst' in match:
            match_description.append(f"ipv4_dst={match['ipv4_dst']}")
        if 'tcp_src' in match:
            match_description.append(f"tcp_src={match['tcp_src']}")
        if 'tcp_dst' in match:
            match_description.append(f"tcp_dst={match['tcp_dst']}")
        if 'udp_src' in match:
            match_description.append(f"udp_src={match['udp_src']}")
        if 'udp_dst' in match:
            match_description.append(f"udp_dst={match['udp_dst']}")
        
        processed['match_description'] = ', '.join(match_description) if match_description else "any"
        
        # Process actions
        instructions = flow_entry.get('instructions', [])
        action_descriptions = []
        
        for instruction in instructions:
            if instruction.get('type') == 'APPLY_ACTIONS':
                actions = instruction.get('actions', [])
                for action in actions:
                    action_type = action.get('type', 'unknown')
                    if action_type == 'OUTPUT':
                        port = action.get('port', 'unknown')
                        if port == 'CONTROLLER':
                            action_descriptions.append("send_to_controller")
                        elif port == 'FLOOD':
                            action_descriptions.append("flood")
                        elif port == 'NORMAL':
                            action_descriptions.append("normal_processing")
                        else:
                            action_descriptions.append(f"output_port_{port}")
                    elif action_type == 'SET_FIELD':
                        field = action.get('field', 'unknown')
                        value = action.get('value', 'unknown')
                        action_descriptions.append(f"set_{field}={value}")
                    elif action_type == 'DROP':
                        action_descriptions.append("drop")
                    else:
                        action_descriptions.append(action_type.lower())
        
        processed['action_description'] = ', '.join(action_descriptions) if action_descriptions else "unknown"
        
        return processed

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics including bandwidth, latency estimates, and flow counts.
        
        Returns:
            Dict containing performance metrics
        """
        if not self.connected:
            return {"error": "Not connected to SDN controller"}
        
        try:
            current_time = time.time()
            
            # Collect fresh statistics if needed
            if current_time - self.last_stats_collection > self.stats_collection_interval:
                port_stats = self.get_port_statistics()
                flow_stats = self.get_flow_statistics()
            else:
                # Use cached data
                port_stats = {}
                flow_stats = {}
                for dpid in [sw.get('dpid', sw.get('id')) for sw in self.get_switches()]:
                    if f"{dpid}_1" in self.port_stats_cache:  # Check if we have cached port stats
                        # Reconstruct port stats from cache
                        switch_ports = []
                        for key, cached_stats in self.port_stats_cache.items():
                            if key.startswith(f"{dpid}_"):
                                port_no = key.split('_')[1]
                                switch_ports.append({
                                    'port_no': int(port_no),
                                    'rx_mbps': 0,  # No real-time calculation from cache
                                    'tx_mbps': 0,
                                    'total_mbps': 0
                                })
                        if switch_ports:
                            port_stats[dpid] = switch_ports
                    
                    if dpid in self.flow_stats_cache:
                        flow_stats[dpid] = self.flow_stats_cache[dpid]['flows']
            
            # Aggregate metrics
            total_bandwidth = 0.0
            max_bandwidth = 0.0
            active_flows = 0
            total_switches = len(self.get_switches())
            
            # Calculate bandwidth metrics from port statistics
            for dpid, ports in port_stats.items():
                for port in ports:
                    port_bandwidth = port.get('total_mbps', 0)
                    total_bandwidth += port_bandwidth
                    max_bandwidth = max(max_bandwidth, port_bandwidth)
            
            # Count active flows
            for dpid, flows in flow_stats.items():
                active_flows += len([f for f in flows if f.get('packet_count', 0) > 0])
            
            # Calculate average bandwidth (non-zero aggregation)
            non_zero_ports = sum(1 for dpid, ports in port_stats.items() 
                               for port in ports if port.get('total_mbps', 0) > 0)
            avg_bandwidth = total_bandwidth / non_zero_ports if non_zero_ports > 0 else 0
            
            # Estimate latency based on flow processing (simplified heuristic)
            avg_latency = 0.0
            if active_flows > 0:
                # Simple heuristic: more flows = higher processing latency
                avg_latency = min(5 + (active_flows * 0.1), 100)  # Cap at 100ms
            
            metrics = {
                "timestamp": current_time,
                "bandwidth": {
                    "total_mbps": round(total_bandwidth, 4),
                    "average_mbps": round(avg_bandwidth, 4),
                    "max_mbps": round(max_bandwidth, 4)
                },
                "latency": {
                    "average_ms": round(avg_latency, 2),
                    "estimated": True  # Indicate this is estimated, not measured
                },
                "flows": {
                    "total_active": active_flows,
                    "per_switch_avg": round(active_flows / total_switches, 1) if total_switches > 0 else 0
                },
                "switches": {
                    "total": total_switches,
                    "with_traffic": len([dpid for dpid, ports in port_stats.items() 
                                       if any(p.get('total_mbps', 0) > 0 for p in ports)])
                }
            }
            
            self.logger.debug(f"Generated performance metrics: {metrics}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive network statistics including performance metrics.
        
        Returns:
            Dict containing network statistics with real performance data
        """
        if not self.connected:
            return {"error": "Not connected to SDN controller"}
        
        try:
            # Collect real-time statistics
            switches = self.get_switches()
            port_stats = self.get_port_statistics()
            flow_stats = self.get_flow_statistics()
            performance_metrics = self.get_performance_metrics()
            
            # Calculate network-wide statistics
            total_switches = len(switches)
            total_ports = sum(len(switch.get('ports', [])) for switch in switches)
            total_flows = sum(len(flows) for flows in flow_stats.values())
            
            # Calculate active flows (flows with packet count > 0)
            active_flows = 0
            for switch_flows in flow_stats.values():
                active_flows += len([f for f in switch_flows if f.get('packet_count', 0) > 0])
            
            statistics = {
                "timestamp": time.time(),
                "controller": {
                    "type": "Ryu",
                    "host": self.host,
                    "port": self.port,
                    "connected": self.connected
                },
                "topology": {
                    "switches": total_switches,
                    "ports": total_ports,
                    "flows": {
                        "total": total_flows,
                        "active": active_flows,
                        "efficiency": round((active_flows / max(total_flows, 1)) * 100, 2)
                    }
                },
                "performance": performance_metrics,
                "detailed_stats": {
                    "switches": switches,
                    "port_statistics": port_stats,
                    "flow_statistics": flow_stats
                }
            }
            
            self.logger.debug(f"Generated network statistics: {total_switches} switches, {total_flows} flows")
            return statistics
            
        except Exception as e:
            self.logger.error(f"Error getting network statistics: {e}")
            return {"error": str(e)}