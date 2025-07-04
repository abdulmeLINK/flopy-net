"""
Event monitor for the collector.

This module collects events from the various components of the system.
"""
import logging
import time
import json
import os
import requests
import datetime
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dateutil import parser

logger = logging.getLogger(__name__)

class EventMonitor:
    """
    Collects events from the FL Server, Policy Engine, and SDN Controller.
    """
    
    def __init__(self, storage, fl_server_url: str, policy_engine_url: str, 
                 network_monitor=None, 
                 sdn_controller_host: Optional[str] = None, 
                 sdn_controller_port: Optional[int] = None):
        """
        Initialize the EventMonitor.
        
        Args:
            storage: The storage instance for persisting events
            fl_server_url: URL of the FL Server
            policy_engine_url: URL of the Policy Engine
            network_monitor: Optional NetworkMonitor instance for SDN status tracking
            sdn_controller_host: Host of the SDN Controller (e.g., Ryu REST API)
            sdn_controller_port: Port of the SDN Controller REST API
        """
        self.storage = storage
        self.fl_server_url = fl_server_url
        self.policy_engine_url = policy_engine_url
        self.network_monitor = network_monitor

        # Initialize FL Server session and API base URL
        self.fl_server_api_base_url = fl_server_url
        self.fl_session = requests.Session()

        # Initialize SDN Controller settings
        self.sdn_controller_api_base_url: Optional[str] = None
        self.sdn_controller_session = None

        if sdn_controller_host and sdn_controller_port:
            self.sdn_controller_api_base_url = f"http://{sdn_controller_host}:{sdn_controller_port}"
            self.sdn_controller_session = requests.Session()
            logger.info(f"SDN Controller API base URL set to: {self.sdn_controller_api_base_url}")
            try:
                response = self.sdn_controller_session.get(self.sdn_controller_api_base_url + "/stats", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Successfully connected to SDN Controller at {self.sdn_controller_api_base_url}")
                else:
                    logger.warning(f"Failed to verify connection to SDN Controller at {self.sdn_controller_api_base_url} (status: {response.status_code}).")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error connecting to SDN Controller during init: {e}")
        elif sdn_controller_host:
             logger.warning("SDN Controller host provided, but port is missing. SDN event collection disabled.")

        # State tracking
        self.last_event_ids = {
            "FL_SERVER": None,
            "POLICY_ENGINE": None
        }
        
        # Previous network states for change detection
        self.previous_nodes: Dict[str, Any] = {}
        self.previous_links: Dict[str, Any] = {}
        
        logger.info("EventMonitor initialized.")
        
        self._log_collector_event("COLLECTOR_START", {
            "poll_interval_server_sec": int(os.getenv("FL_INTERVAL_SEC", "60")),
            "poll_interval_policy_sec": int(os.getenv("POLICY_INTERVAL_SEC", "30")),
            "poll_interval_network_sec": int(os.getenv("NETWORK_INTERVAL_SEC", "120"))
        })
    
    def _log_collector_event(self, event_type: str, details: Dict[str, Any]):
        """
        Log an event generated by the collector itself.
        
        Args:
            event_type: Type of event
            details: Event details
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_component": "COLLECTOR",
            "component": "COLLECTOR",  # Add for dashboard compatibility
            "event_type": event_type,
            "type": event_type,  # Add for dashboard compatibility
            "event_level": "INFO",  # Default level
            "level": "INFO",  # Add for dashboard compatibility
            "details": details
        }
        
        # Store event in the same format as collected events
        self.storage.store_event(event)
        logger.debug(f"Logged collector event: {event_type}")
    
    def collect_fl_server_events(self) -> Tuple[int, Optional[str]]:
        """
        Collect events from FL Server via HTTP API.
        
        Returns:
            Tuple of (events_count, error_message)
        """
        start_time = time.time()
        events_collected_count = 0
        error_message = None
        
        try:
            # Get training events first
            response = self.fl_session.get(f"{self.fl_server_api_base_url}/events", timeout=10)
            
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get("events", [])
                
                logger.debug(f"Retrieved {len(events)} events from FL server")
                
                # Store each event with normalized field names
                for event in events:
                    # Ensure 'component' and 'source_component' are set
                    original_component = event.get("component") or event.get("source_component")
                    event["component"] = original_component or "FL_SERVER"
                    event["source_component"] = original_component or "FL_SERVER"

                    # Ensure dashboard compatibility with field names
                    if "source_component" in event and event.get("component") != event["source_component"]:
                        event["component"] = event["source_component"]
                    elif "component" in event and event.get("source_component") != event["component"]:
                        event["source_component"] = event["component"]

                    if "event_type" in event and "type" not in event:
                        event["type"] = event["event_type"]
                    elif "type" in event and "event_type" not in event:
                        event["event_type"] = event["type"]
                        
                    # Enhanced event level assignment based on event type and content
                    original_event_level = event.get("level") or event.get("event_level")
                    
                    # Assign levels based on event type and conditions
                    if not original_event_level:
                        event_type = event.get("event_type", "").upper()
                        event_details = event.get("details", {})
                        
                        if "ERROR" in event_type or "FAIL" in event_type or "EXCEPTION" in event_type:
                            event_level = "ERROR"
                        elif "WARNING" in event_type or "WARN" in event_type:
                            event_level = "WARNING"
                        elif event_type in ["CLIENT_DISCONNECTED", "ROUND_FAILED", "AGGREGATION_FAILED"]:
                            event_level = "WARNING"
                        elif event_type in ["CLIENT_TIMEOUT", "SLOW_CLIENT", "LOW_ACCURACY"]:
                            event_level = "WARNING"
                        elif "ROUND_COMPLETED" in event_type:
                            # Check accuracy for warning level
                            accuracy = event_details.get("accuracy", 1.0)
                            if accuracy < 0.3:  # Low accuracy warning
                                event_level = "WARNING"
                            else:
                                event_level = "INFO"
                        else:
                            event_level = "INFO"
                    else:
                        event_level = original_event_level
                    
                    event["level"] = event_level
                    event["event_level"] = event_level
                    
                    # Add message field for dashboard compatibility
                    if "message" not in event:
                        event_type = event.get("event_type", "Unknown event")
                        if event.get("details"):
                            try:
                                details_str = json.dumps(event["details"]) if isinstance(event["details"], dict) else str(event["details"])
                                event["message"] = f"{event_type}: {details_str[:200]}..."
                            except:
                                event["message"] = event_type
                        else:
                            event["message"] = event_type

                    self.storage.store_event(event)
                    events_collected_count += 1

                # Generate synthetic events based on FL server status for better event diversity
                try:
                    status_response = self.fl_session.get(f"{self.fl_server_api_base_url}/status", timeout=5)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        
                        # Generate events based on status conditions
                        connected_clients = status_data.get("connected_clients", 0)
                        current_round = status_data.get("current_round", 0)
                        training_complete = status_data.get("training_complete", False)
                        
                        # Low client count warning
                        if current_round > 0 and connected_clients < 2:
                            warning_event = {
                                "event_id": str(uuid.uuid4()),
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "source_component": "FL_SERVER",
                                "component": "FL_SERVER",
                                "event_type": "LOW_CLIENT_COUNT",
                                "type": "LOW_CLIENT_COUNT",
                                "event_level": "WARNING",
                                "level": "WARNING",
                                "details": {
                                    "connected_clients": connected_clients,
                                    "current_round": current_round,
                                    "recommended_minimum": 2
                                },
                                "message": f"Low client count: {connected_clients} clients connected in round {current_round}"
                            }
                            self.storage.store_event(warning_event)
                            events_collected_count += 1
                        
                        # Training completion event
                        if training_complete and not hasattr(self, '_training_complete_logged'):
                            completion_event = {
                                "event_id": str(uuid.uuid4()),
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "source_component": "FL_SERVER",
                                "component": "FL_SERVER",
                                "event_type": "TRAINING_COMPLETED",
                                "type": "TRAINING_COMPLETED",
                                "event_level": "INFO",
                                "level": "INFO",
                                "details": {
                                    "total_rounds": current_round,
                                    "final_client_count": connected_clients
                                },
                                "message": f"Federated learning training completed after {current_round} rounds"
                            }
                            self.storage.store_event(completion_event)
                            events_collected_count += 1
                            self._training_complete_logged = True
                
                except Exception as e:
                    logger.debug(f"Error generating synthetic events from FL server status: {e}")
                    # Don't let this fail the whole event collection
                    pass

            # Log execution time
            end_time = time.time()
            logger.debug(f"FL server event collection finished in {end_time - start_time:.2f} seconds")
            
            self._log_collector_event("POLL_TARGET_SUCCESS", {
                "target_component": "FL_SERVER",
                "endpoint": "/events, /status",
                "duration_ms": (end_time - start_time) * 1000
            })

            return events_collected_count, None

        except requests.exceptions.RequestException as e:
            error_message = f"Error connecting to FL Server at {self.fl_server_api_base_url}: {e}"
            logger.warning(error_message)
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "FL_SERVER",
                "error_message": error_message,
                "duration_ms": (end_time - start_time) * 1000
            })
            return 0, error_message
        except json.JSONDecodeError as e:
            error_message = f"Error decoding JSON from FL Server events endpoint: {e}"
            logger.warning(error_message)
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "FL_SERVER",
                "error_message": error_message,
                "duration_ms": (end_time - start_time) * 1000
            })
            return 0, error_message
        except Exception as e:
            error_message = f"An unexpected error occurred during FL server event collection: {e}"
            logger.error(error_message, exc_info=True)
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "FL_SERVER",
                "error_message": error_message,
                "duration_ms": (end_time - start_time) * 1000
            })
            return 0, error_message
    
    def collect_policy_engine_events(self) -> Tuple[int, Optional[str]]:
        """
        Collect events from Policy Engine via HTTP API.
        
        Returns:
            Tuple of (events_count, error_message)
        """
        start_time = time.time()
        error_message = None
        url = f"{self.policy_engine_url}/events"
        
        if self.last_event_ids["POLICY_ENGINE"]:
            url += f"?since_event_id={self.last_event_ids['POLICY_ENGINE']}"
        
        self._log_collector_event("POLL_CYCLE_START", {
            "target_components": ["POLICY_ENGINE"]
        })
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                
                # Update last_event_id if provided
                if data.get("last_event_id"):
                    self.last_event_ids["POLICY_ENGINE"] = data["last_event_id"]
                
                # Store each event with normalized field names
                for event in events:
                    # Ensure 'component' and 'source_component' are set, defaulting to "POLICY_ENGINE"
                    # if the event from POLICY_ENGINE doesn't specify its origin.
                    original_component = event.get("component") or event.get("source_component")

                    event["component"] = original_component or "POLICY_ENGINE"
                    event["source_component"] = original_component or "POLICY_ENGINE"

                    # Ensure dashboard compatibility with field names
                    if "source_component" in event and event.get("component") != event["source_component"]:
                        event["component"] = event["source_component"]
                    elif "component" in event and event.get("source_component") != event["component"]:
                        event["source_component"] = event["component"]

                    if "event_type" in event and "type" not in event:
                        event["type"] = event["event_type"]
                    elif "type" in event and "event_type" not in event:
                        event["event_type"] = event["type"]
                        
                    # Enhanced event level assignment based on policy decisions and content
                    original_event_level = event.get("level") or event.get("event_level")
                    
                    if not original_event_level:
                        event_type = event.get("event_type", "").upper()
                        event_details = event.get("details", {})
                        
                        # Assign levels based on policy engine specific patterns
                        if "ERROR" in event_type or "FAIL" in event_type or "EXCEPTION" in event_type:
                            event_level = "ERROR"
                        elif "WARNING" in event_type or "WARN" in event_type:
                            event_level = "WARNING"
                        elif event_type in ["POLICY_VIOLATION", "ACCESS_DENIED", "UNAUTHORIZED"]:
                            event_level = "WARNING"
                        elif event_type in ["POLICY_CHANGED", "CONFIG_UPDATED", "RULE_MODIFIED"]:
                            event_level = "INFO"
                        elif "DECISION" in event_type:
                            # Check if policy decision was denied
                            allowed = event_details.get("allowed", True)
                            decision = event_details.get("decision", "allow")
                            if not allowed or decision == "deny":
                                event_level = "WARNING"
                            else:
                                event_level = "INFO"
                        else:
                            event_level = "INFO"
                    else:
                        event_level = original_event_level
                    
                    event["level"] = event_level
                    event["event_level"] = event_level
                    
                    # Add message field for dashboard compatibility if not present
                    if "message" not in event:
                        event_type = event.get("event_type", "Unknown policy event")
                        if event.get("details"):
                            try:
                                details_str = json.dumps(event["details"]) if isinstance(event["details"], dict) else str(event["details"])
                                event["message"] = f"{event_type}: {details_str[:200]}..."
                            except:
                                event["message"] = event_type
                        else:
                            event["message"] = event_type
                    
                    # Ensure timestamp exists and is in ISO format (UTC)
                    if not event.get("timestamp"):
                        event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    elif not isinstance(event.get("timestamp"), str) or 'T' not in event.get("timestamp", ""):
                        # Attempt to parse and reformat if it's not a string or looks like a non-ISO format
                        try:
                            # Common case: Unix timestamp (seconds or milliseconds)
                            if isinstance(event["timestamp"], (int, float)):
                                # Assuming seconds for fromtimestamp. If it's ms, divide by 1000.
                                # This needs to be confirmed based on actual data from Policy Engine.
                                dt_object = datetime.datetime.fromtimestamp(event["timestamp"], tz=datetime.timezone.utc)
                            else: # Assume it might be a parsable date string but not ISO
                                dt_object = parser.parse(str(event["timestamp"]))
                                if dt_object.tzinfo is None:
                                    dt_object = dt_object.replace(tzinfo=datetime.timezone.utc) # Assume UTC if no tz
                            event["timestamp"] = dt_object.isoformat()
                        except Exception as ts_parse_error:
                            logger.warning(f"Could not parse timestamp '{event['timestamp']}' for event from {event['source_component']}. Defaulting. Error: {ts_parse_error}")
                            event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    
                    self.storage.store_event(event)
                
                duration_ms = (time.time() - start_time) * 1000
                self._log_collector_event("POLL_TARGET_SUCCESS", {
                    "target_component": "POLICY_ENGINE",
                    "endpoint": "/events",
                    "duration_ms": duration_ms
                })
                
                self._log_collector_event("EVENT_FETCH_SUCCESS", {
                    "target_component": "POLICY_ENGINE",
                    "event_count": len(events),
                    "last_event_id_fetched": self.last_event_ids["POLICY_ENGINE"],
                    "duration_ms": duration_ms
                })
                
                return len(events), None
            else:
                error_message = f"Failed to collect Policy Engine events: {response.status_code}"
                logger.error(error_message)
                
                self._log_collector_event("POLL_TARGET_FAILURE", {
                    "target_component": "POLICY_ENGINE",
                    "endpoint": "/events",
                    "error_message": error_message,
                    "status_code": response.status_code,
                    "duration_ms": (time.time() - start_time) * 1000
                })
                
                return 0, error_message
                
        except requests.exceptions.RequestException as e:
            error_message = f"Error connecting to Policy Engine: {str(e)}"
            logger.error(error_message)
            
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "POLICY_ENGINE",
                "endpoint": "/events",
                "error_message": error_message,
                "duration_ms": (time.time() - start_time) * 1000
            })
            
            return 0, error_message
    
    def collect_network_events(self) -> Tuple[int, Optional[str]]:
        """
        Collect events from the network by observing topology changes from the SDN controller.
        """
        if not self.network_monitor:
            return 0, "NetworkMonitor not available"
            
        events_collected_count = 0
        error_message = None
        
        try:
            live_topo = self.network_monitor.get_live_topology()
            current_nodes = {node['id']: node for node in live_topo.get('nodes', [])}
            current_links = {f"{link.get('source', '')}-{link.get('target', '')}": link for link in live_topo.get('links', [])}

            # Detect new nodes
            for node_id, node in current_nodes.items():
                if node_id not in self.previous_nodes:
                    self._log_network_event("NODE_CONNECTED", node, "INFO")
                    events_collected_count += 1
            
            # Detect removed nodes
            for node_id in self.previous_nodes:
                if node_id not in current_nodes:
                    self._log_network_event("NODE_DISCONNECTED", self.previous_nodes[node_id], "WARNING")
                    events_collected_count += 1
            
            # Detect new links
            for link_id, link in current_links.items():
                if link_id not in self.previous_links:
                    self._log_network_event("LINK_ADDED", link, "INFO")
                    events_collected_count += 1
            
            # Detect removed links
            for link_id in self.previous_links:
                if link_id not in current_links:
                    self._log_network_event("LINK_REMOVED", self.previous_links[link_id], "WARNING")
                    events_collected_count += 1

            self.previous_nodes = current_nodes
            self.previous_links = current_links

        except Exception as e:
            error_message = f"Error collecting network events: {e}"
            logger.error(error_message, exc_info=True)
            
        return events_collected_count, error_message

    def _log_network_event(self, event_type: str, details: Dict[str, Any], level: str):
        """Helper to log network topology events."""
        node_id = details.get('id') or f"{details.get('source')}-{details.get('target')}"
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_component": "SDN_CONTROLLER",
            "component": "NETWORK",
            "event_type": event_type,
            "type": event_type,
            "event_level": level,
            "level": level,
            "details": details,
            "message": f"{event_type}: {node_id}"
        }
        self.storage.store_event(event)
        logger.debug(f"Logged network event: {event_type} for {node_id}")

    def collect_sdn_controller_events(self) -> Tuple[int, Optional[str]]:
        """
        Collect topology and potentially other events from the SDN Controller (Ryu) via REST API.

        Returns:
            Tuple of (events_count, error_message)
        """
        if not self.sdn_controller_api_base_url or not self.sdn_controller_session:
            logger.debug("SDN Controller API base URL not configured. Skipping SDN event collection.")
            return 0, "SDN Controller API not configured"

        start_time = time.time()
        events_collected_count = 0
        error_message = None
        
        switches = []
        links = []
        hosts = []
        controller_info = {"type": "RYU", "url": self.sdn_controller_api_base_url, "status": "unknown"}

        try:
            logger.debug(f"Attempting to collect SDN controller topology from {self.sdn_controller_api_base_url}")

            # 1. Get Switches
            try:
                switches_response = self.sdn_controller_session.get(f"{self.sdn_controller_api_base_url}/stats/switches", timeout=10)
                if switches_response.status_code == 200:
                    switches = switches_response.json()
                    logger.debug(f"Retrieved {len(switches)} switches from SDN controller.")
                    
                    # Generate events based on switch status
                    if len(switches) == 0:
                        warning_event = {
                            "event_id": str(uuid.uuid4()),
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "source_component": "RYU_CONTROLLER",
                            "component": "RYU_CONTROLLER",
                            "event_type": "NO_SWITCHES_DETECTED",
                            "type": "NO_SWITCHES_DETECTED",
                            "event_level": "WARNING",
                            "level": "WARNING",
                            "details": {"switches_count": 0},
                            "message": "No OpenFlow switches detected in the network"
                        }
                        self.storage.store_event(warning_event)
                        events_collected_count += 1
                    elif len(switches) != getattr(self, '_last_switch_count', len(switches)):
                        # Switch count changed
                        info_event = {
                            "event_id": str(uuid.uuid4()),
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "source_component": "RYU_CONTROLLER",
                            "component": "RYU_CONTROLLER",
                            "event_type": "SWITCH_COUNT_CHANGED",
                            "type": "SWITCH_COUNT_CHANGED",
                            "event_level": "INFO",
                            "level": "INFO",
                            "details": {
                                "current_switches": len(switches),
                                "previous_switches": getattr(self, '_last_switch_count', 0),
                                "switch_ids": switches
                            },
                            "message": f"Switch count changed from {getattr(self, '_last_switch_count', 0)} to {len(switches)}"
                        }
                        self.storage.store_event(info_event)
                        events_collected_count += 1
                        
                    self._last_switch_count = len(switches)
                else:
                    logger.warning(f"Failed to get switches from SDN controller: {switches_response.status_code}")
                    # Generate error event for failed switch query
                    error_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "source_component": "RYU_CONTROLLER",
                        "component": "RYU_CONTROLLER",
                        "event_type": "SWITCH_QUERY_FAILED",
                        "type": "SWITCH_QUERY_FAILED",
                        "event_level": "ERROR",
                        "level": "ERROR",
                        "details": {"status_code": switches_response.status_code},
                        "message": f"Failed to query switches: HTTP {switches_response.status_code}"
                    }
                    self.storage.store_event(error_event)
                    events_collected_count += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching switches from SDN controller: {e}")
                error_event = {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source_component": "RYU_CONTROLLER",
                    "component": "RYU_CONTROLLER",
                    "event_type": "SWITCH_CONNECTION_ERROR",
                    "type": "SWITCH_CONNECTION_ERROR",
                    "event_level": "ERROR",
                    "level": "ERROR",
                    "details": {"error": str(e)},
                    "message": f"Error connecting to switches endpoint: {str(e)}"
                }
                self.storage.store_event(error_event)
                events_collected_count += 1

            # 2. Get Links (Optional, Ryu apps might not expose /topology/links)
            try:
                links_response = self.sdn_controller_session.get(f"{self.sdn_controller_api_base_url}/topology/links", timeout=10)
                if links_response.status_code == 200:
                    links_data = links_response.json()
                    if isinstance(links_data, list): # Ensure it's a list
                         links = links_data
                    logger.debug(f"Retrieved {len(links)} links from SDN controller.")
                elif links_response.status_code == 404:
                    logger.info("SDN controller does not have a /topology/links endpoint. Link information will be unavailable.")
                    # Generate info event for missing endpoint
                    info_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "source_component": "RYU_CONTROLLER",
                        "component": "RYU_CONTROLLER",
                        "event_type": "LINKS_ENDPOINT_UNAVAILABLE",
                        "type": "LINKS_ENDPOINT_UNAVAILABLE",
                        "event_level": "INFO",
                        "level": "INFO",
                        "details": {"endpoint": "/topology/links"},
                        "message": "Links topology endpoint not available on this controller"
                    }
                    self.storage.store_event(info_event)
                    events_collected_count += 1
                else:
                    logger.warning(f"Failed to get links from SDN controller: {links_response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching links from SDN controller: {e}")

            # 3. Get Hosts (Optional, Ryu apps might not expose /topology/hosts)
            try:
                hosts_response = self.sdn_controller_session.get(f"{self.sdn_controller_api_base_url}/topology/hosts", timeout=10)
                if hosts_response.status_code == 200:
                    hosts_data = hosts_response.json()
                    if isinstance(hosts_data, list): # Ensure it's a list
                        hosts = hosts_data
                    logger.debug(f"Retrieved {len(hosts)} hosts from SDN controller.")
                elif hosts_response.status_code == 404:
                    logger.info("SDN controller does not have a /topology/hosts endpoint. Host information will be unavailable.")
                else:
                    logger.warning(f"Failed to get hosts from SDN controller: {hosts_response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching hosts from SDN controller: {e}")

            controller_info["status"] = "responsive" # If we got this far without a major connection error

            # Create a single event for the topology snapshot
            event_details = {
                "switches": switches,
                "links": links,
                "hosts": hosts,
                "controller_info": controller_info 
            }
            
            # Determine event level based on topology health
            if len(switches) == 0:
                event_level = "WARNING"
                message = f"SDN Topology Warning: No switches found, {len(links)} links, {len(hosts)} hosts"
            elif len(switches) >= 1:
                event_level = "INFO"
                message = f"SDN Topology: {len(switches)} switches, {len(links)} links, {len(hosts)} hosts"
            else:
                event_level = "INFO"
                message = f"SDN Topology: {len(switches)} switches, {len(links)} links, {len(hosts)} hosts"
            
            sdn_event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "source_component": "RYU_CONTROLLER", 
                "component": "RYU_CONTROLLER",
                "event_type": "TOPOLOGY_SNAPSHOT",
                "type": "TOPOLOGY_SNAPSHOT", 
                "event_level": event_level,
                "level": event_level, 
                "details": event_details,
                "message": message
            }
            self.storage.store_event(sdn_event)
            events_collected_count += 1
            
            logger.info(f"Collected SDN topology snapshot: {sdn_event['message']}")

            self._log_collector_event("POLL_TARGET_SUCCESS", {
                "target_component": "RYU_CONTROLLER",
                "endpoint": "/stats/switches, /topology/links, /topology/hosts", 
                "duration_ms": (time.time() - start_time) * 1000
            })

        except requests.exceptions.ConnectionError as e: # More specific for initial connection issues
            error_message = f"Connection error to SDN Controller API at {self.sdn_controller_api_base_url}: {str(e)}"
            logger.error(error_message)
            controller_info["status"] = "unreachable"
            
            # Generate connection error event
            connection_error_event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "source_component": "RYU_CONTROLLER",
                "component": "RYU_CONTROLLER",
                "event_type": "CONTROLLER_UNREACHABLE",
                "type": "CONTROLLER_UNREACHABLE",
                "event_level": "ERROR",
                "level": "ERROR",
                "details": {"error": str(e), "url": self.sdn_controller_api_base_url},
                "message": f"SDN Controller unreachable: {str(e)}"
            }
            self.storage.store_event(connection_error_event)
            events_collected_count += 1
            
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "RYU_CONTROLLER",
                "error_message": error_message,
                "duration_ms": (time.time() - start_time) * 1000
            })
            return events_collected_count, error_message
        except requests.exceptions.RequestException as e: # Catch other request-related errors
            error_message = f"Error querying SDN Controller API {self.sdn_controller_api_base_url}: {str(e)}"
            logger.error(error_message)
            controller_info["status"] = "error"
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "RYU_CONTROLLER",
                "error_message": error_message,
                "duration_ms": (time.time() - start_time) * 1000
            })
            return events_collected_count, error_message
        except Exception as e:
            error_message = f"Unexpected error collecting SDN Controller events: {str(e)}"
            logger.error(error_message, exc_info=True) 
            controller_info["status"] = "error"
            self._log_collector_event("POLL_TARGET_FAILURE", {
                "target_component": "RYU_CONTROLLER",
                "error_message": error_message,
                "duration_ms": (time.time() - start_time) * 1000
            })
            return events_collected_count, error_message
            
        return events_collected_count, error_message

    def collect_metrics(self):
        """Collect all events from the different components."""
        start_time = time.time()
        total_events = 0
        errors = []

        # Collect events from FL Server, Policy Engine, SDN Controller, and Network
        sources = {
            "FL Server": self.collect_fl_server_events,
            "Policy Engine": self.collect_policy_engine_events,
            "SDN Controller": self.collect_sdn_controller_events,
            "Network": self.collect_network_events,
        }

        for source_name, collect_func in sources.items():
            try:
                num_events, error = collect_func()
                total_events += num_events
                if error:
                    errors.append(f"{source_name}: {error}")
            except Exception as e:
                logger.error(f"Exception in {source_name} event collection: {e}", exc_info=True)
                errors.append(f"{source_name}: Collection failed with exception")

        if errors:
            logger.warning(f"Event collection completed with errors: {'. '.join(errors)}")
        
        end_time = time.time()
        logger.info(f"Collected {total_events} events in {end_time - start_time:.2f} seconds.")
        return {"events_collected": total_events, "errors": len(errors)} 