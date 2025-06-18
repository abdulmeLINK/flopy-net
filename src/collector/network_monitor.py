import logging
import os
import time
import requests
from typing import Dict, Any, Optional, List
import json

from .storage import MetricsStorage

logger = logging.getLogger(__name__)

class NetworkMonitor:
    """Monitors the network topology via an SDN controller."""

    def __init__(self, storage: MetricsStorage, sdn_controller_url: str):
        """Initialize the NetworkMonitor.

        Args:
            storage: The MetricsStorage instance for saving metrics.
            sdn_controller_url: The URL of the SDN controller REST API (e.g., "http://localhost:8181").
        """
        if not sdn_controller_url:
            raise ValueError("sdn_controller_url is required for NetworkMonitor")

        self.storage = storage
        self.sdn_controller_url = sdn_controller_url.rstrip('/')
        self.logger = logger
        logger.info(f"NetworkMonitor initialized with SDN controller URL: {self.sdn_controller_url}")
        # State for bandwidth calculation
        self.previous_port_stats: Dict[str, Dict] = {}
        self.last_stats_timestamp: Optional[float] = None
        # Track known switch DPIDs for change detection
        self._last_known_dpids: List[str] = []

    def _get_sdn_port_stats(self, dpid: str) -> List[Dict[str, Any]]:
        """Get port stats from the SDN controller for a specific switch."""
        try:
            # Validate DPID format before making request
            if not dpid or dpid == '0':
                logger.warning(f"Invalid DPID provided: {dpid}")
                return []
            
            # This endpoint is provided by ryu.app.ofctl_rest
            url = f"{self.sdn_controller_url}/stats/port/{dpid}"
            logger.debug(f"Requesting port stats for switch {dpid} from {url}")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            stats = response.json()
            port_stats = stats.get(dpid, [])
            logger.debug(f"Retrieved {len(port_stats)} port stats for switch {dpid}")
            return port_stats
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get port stats for switch {dpid}: {e}")
            return []
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON for port stats from {url}")
            return []

    def _get_sdn_switches(self) -> List[Dict[str, Any]]:
        """Get switches from the SDN controller."""
        try:
            # Use Ryu REST topology endpoint which has real data
            url = f"{self.sdn_controller_url}/v1.0/topology/switches"
            logger.debug(f"Requesting switches from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            switch_data = response.json()
            
            switches = []
            current_dpids = []
            for switch in switch_data:
                # Handle Ryu topology format
                if isinstance(switch, dict):
                    # Ryu topology format: switch object with dpid and ports
                    dpid = switch.get('dpid', '0')
                    switches.append({
                        'dpid': dpid, 
                        'id': dpid, 
                        'type': 'switch',
                        'ports': switch.get('ports', [])
                    })
                    current_dpids.append(dpid)
                else:
                    # Simple format, just dpid
                    dpid = str(switch)
                    switches.append({'dpid': dpid, 'id': dpid, 'type': 'switch'})
                    current_dpids.append(dpid)
            
            # Log switch changes for debugging
            if hasattr(self, '_last_known_dpids'):
                new_dpids = set(current_dpids) - set(self._last_known_dpids)
                removed_dpids = set(self._last_known_dpids) - set(current_dpids)
                
                if new_dpids:
                    logger.info(f"New switches detected: {new_dpids}")
                if removed_dpids:
                    logger.info(f"Switches disconnected: {removed_dpids}")
                    # Clear stats for disconnected switches
                    for removed_dpid in removed_dpids:
                        keys_to_remove = [key for key in self.previous_port_stats.keys() if key.startswith(f"{removed_dpid}-")]
                        for key in keys_to_remove:
                            del self.previous_port_stats[key]
            
            self._last_known_dpids = current_dpids
            logger.debug(f"Discovered {len(switches)} switches: {current_dpids}")
            return switches
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get switches from SDN controller: {e}")
            return []
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON from {url}")
            return []

    def _get_sdn_links(self) -> List[Dict[str, Any]]:
        """Get links from the SDN controller."""
        try:
            # This endpoint is provided by ryu.app.rest_topology
            url = f"{self.sdn_controller_url}/v1.0/topology/links"
            logger.debug(f"Requesting links from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            # The API returns a list of link objects.
            # We need to format them for our topology view.
            raw_links = response.json()
            links = []
            for link in raw_links:
                links.append({
                    'source': link['src']['dpid'],
                    'target': link['dst']['dpid'],
                    'sport': link['src']['port_no'],
                    'dport': link['dst']['port_no'],
                })
            return links
        except requests.exceptions.RequestException as e:
            # Fallback to policy_switch endpoint
            try:
                url = f"{self.sdn_controller_url}/stats/links"
                logger.debug(f"Requesting links from fallback endpoint {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e_fallback:
                logger.warning(f"Failed to get links from both primary and fallback SDN endpoints: {e} and {e_fallback}")
                return []
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON from {url}")
            return []

    def _get_sdn_hosts(self) -> List[Dict[str, Any]]:
        """Get hosts from the SDN controller."""
        try:
            # Use Ryu REST topology endpoint which has real data
            url = f"{self.sdn_controller_url}/v1.0/topology/hosts"
            logger.debug(f"Requesting hosts from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            raw_hosts = response.json()
            hosts = []
            
            if isinstance(raw_hosts, list):
                # New format: array of host objects from Ryu topology
                for host in raw_hosts:
                    # Handle Ryu topology host format
                    # Extract IP address from ipv4 list - handle different formats
                    ip_addr = 'unknown'
                    if host.get('ipv4'):
                        ipv4_list = host.get('ipv4', [])
                        if ipv4_list:
                            # Handle both string format and dict format
                            first_ip = ipv4_list[0]
                            if isinstance(first_ip, str):
                                ip_addr = first_ip
                            elif isinstance(first_ip, dict):
                                ip_addr = first_ip.get('address', 'unknown')
                    
                    host_data = {
                        'id': host.get('mac', 'unknown'),
                        'mac': host.get('mac', 'unknown'),
                        'dpid': host.get('port', {}).get('dpid', '0'),
                        'port': host.get('port', {}).get('port_no', 0),
                        'ip': ip_addr,
                        'type': 'host'
                    }
                    hosts.append(host_data)
            elif isinstance(raw_hosts, dict):
                # Fallback format: dict of {mac: [dpid, port, ip]}
                for mac, details in raw_hosts.items():
                    hosts.append({
                        'id': mac,
                        'mac': mac,
                        'dpid': hex(details[0]) if isinstance(details[0], int) else str(details[0]),
                        'port': details[1],
                        'ip': details[2],
                        'type': 'host'
                    })
            
            return hosts
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get hosts from SDN controller at {url}: {e}")
            return []
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON from {url}")
            return []


    def get_live_topology(self) -> Dict[str, Any]:
        """Get live topology data directly from the SDN controller."""
        logger.info("Fetching live network topology from SDN controller.")
        
        live_topology = {
            "timestamp": time.time(),
            "nodes": [],
            "links": [],
            "switches": [],
            "hosts": [],
            "source": "sdn_controller"
        }
        try:
            # Get switches data from SDN controller using improved method
            switches_data = self._get_sdn_switches()
            self.logger.info(f"Switches discovered via improved method: {len(switches_data)} switches")
            for switch_data in switches_data:
                live_topology['switches'].append(switch_data)
                live_topology['nodes'].append(switch_data)
        except Exception as e:
            self.logger.error(f"Error getting switches from SDN controller: {e}")
            # Try fallback method if main discovery fails
            try:
                response = requests.get(f"{self.sdn_controller_url}/api/switches", timeout=10)
                if response.status_code == 200:
                    api_data = response.json()
                    for switch in api_data.get('switches', []):
                        dpid = switch.get('dpid', '0')
                        switch_data = {
                            'dpid': dpid,
                            'id': dpid,
                            'type': 'switch',
                            'address': switch.get('address', '')
                        }
                        live_topology['switches'].append(switch_data)
                        live_topology['nodes'].append(switch_data)
            except Exception as fallback_e:
                self.logger.error(f"Fallback switch API also failed: {fallback_e}")

        try:
            # Get topology data from SDN controller
            response = requests.get(f"{self.sdn_controller_url}/v1.0/topology/links", timeout=10)
            if response.status_code == 200:
                links_data = response.json()
                self.logger.info(f"Raw links data from SDN controller: {links_data}")
                if links_data:
                    for link in links_data:
                        try:
                            self.logger.info(f"Processing link: {link}")
                            # Handle different possible data structures
                            if isinstance(link.get('src'), dict):
                                src_dpid = link['src'].get('dpid', '0')
                            else:
                                src_dpid = str(link.get('src', '0'))
                            
                            if isinstance(link.get('dst'), dict):
                                dst_dpid = link['dst'].get('dpid', '0')
                            else:
                                dst_dpid = str(link.get('dst', '0'))
                                
                            live_topology['links'].append({
                                'source': src_dpid,
                                'target': dst_dpid,
                                'type': 'direct'
                            })
                        except Exception as link_error:
                            self.logger.error(f"Error processing link {link}: {link_error}")
                            continue
            else:
                self.logger.error(f"Failed to get topology links: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error getting topology from SDN controller: {e}")

        try:
            # Get hosts data from SDN controller using Ryu REST topology
            response = requests.get(f"{self.sdn_controller_url}/v1.0/topology/hosts", timeout=10)
            if response.status_code == 200:
                hosts_data = response.json()
                self.logger.info(f"Raw hosts data from SDN controller: {hosts_data}")
                if isinstance(hosts_data, list):
                    # Ryu REST topology format: array of host objects
                    for host in hosts_data:
                        try:
                            # Handle Ryu topology host format
                            port_info = host.get('port', {})
                            ipv4_list = host.get('ipv4', [])
                            ip_addr = ipv4_list[0] if ipv4_list else 'unknown'
                            
                            host_data = {
                                'id': host.get('mac', 'unknown'),
                                'mac': host.get('mac', 'unknown'),
                                'dpid': port_info.get('dpid', '0'),
                                'port': port_info.get('port_no', 0),
                                'ip': ip_addr,
                                'type': 'host'
                            }
                            live_topology['hosts'].append(host_data)
                            live_topology['nodes'].append(host_data)
                        except Exception as host_error:
                            self.logger.error(f"Error processing host {host}: {host_error}")
                            continue
                elif isinstance(hosts_data, dict):
                    # Old format: dict of {mac: [dpid, port, ip]}
                    for mac, details in hosts_data.items():
                        try:
                            host_data = {
                                'id': mac,
                                'mac': mac,
                                'dpid': hex(details[0]) if isinstance(details[0], int) else str(details[0]),
                                'port': details[1],
                                'ip': details[2],
                                'type': 'host'
                            }
                            live_topology['hosts'].append(host_data)
                            live_topology['nodes'].append(host_data)
                        except Exception as host_error:
                            self.logger.error(f"Error processing host {mac}: {host_error}")
                            continue
            else:
                self.logger.error(f"Failed to get hosts: {response.status_code}")
                # Try fallback to alternative endpoint
                try:
                    # Some Ryu versions might use different endpoint
                    response = requests.get(f"{self.sdn_controller_url}/stats/hosts", timeout=10)
                    if response.status_code == 200:
                        hosts_data = response.json()
                        # Process as before...
                        if isinstance(hosts_data, dict):
                            for mac, details in hosts_data.items():
                                try:
                                    host_data = {
                                        'id': mac,
                                        'mac': mac,
                                        'dpid': hex(details[0]) if isinstance(details[0], int) else str(details[0]),
                                        'port': details[1],
                                        'ip': details[2],
                                        'type': 'host'
                                    }
                                    live_topology['hosts'].append(host_data)
                                    live_topology['nodes'].append(host_data)
                                except Exception as host_error:
                                    self.logger.error(f"Error processing host {mac}: {host_error}")
                                    continue
                except Exception as fallback_e:
                    self.logger.warning(f"Fallback hosts endpoint also failed: {fallback_e}")
        except Exception as e:
            self.logger.error(f"Error getting hosts from SDN controller: {e}")

        return live_topology


    def collect_metrics(self):
        """Collect network topology metrics from SDN controller."""
        logger.debug("Attempting to collect network metrics from SDN controller.")
        
        topology_data = self.get_live_topology()
        current_timestamp = topology_data.get("timestamp", time.time())

        # Collect real performance metrics from SDN controller
        performance_metrics = self._get_sdn_performance_metrics()
        flow_statistics = self._get_sdn_flow_statistics()
        
        # Calculate bandwidth and other port-level metrics
        all_port_metrics = {}
        if self.last_stats_timestamp is not None:
            time_delta = current_timestamp - self.last_stats_timestamp
            if time_delta > 0:
                # Always refresh switch discovery before collecting port stats
                current_switches = self._get_sdn_switches()
                
                for switch in current_switches:
                    if switch.get('type') == 'switch':
                        dpid = switch.get('dpid') or switch.get('id')
                        # The DPID from get_switches is already a hex string
                        current_stats_list = self._get_sdn_port_stats(dpid)
                        
                        switch_port_metrics = {}
                        for port_stat in current_stats_list:
                            port_no = port_stat.get("port_no")
                            stat_key = f"{dpid}-{port_no}"
                            
                            prev_stat = self.previous_port_stats.get(stat_key)
                            if prev_stat:
                                # Calculate bytes delta
                                rx_bytes_delta = port_stat.get("rx_bytes", 0) - prev_stat.get("rx_bytes", 0)
                                tx_bytes_delta = port_stat.get("tx_bytes", 0) - prev_stat.get("tx_bytes", 0)
                                
                                # Calculate bandwidth in Mbps (ensure positive values)
                                rx_mbps = max(0, (rx_bytes_delta * 8) / (time_delta * 1_000_000))
                                tx_mbps = max(0, (tx_bytes_delta * 8) / (time_delta * 1_000_000))
                                
                                switch_port_metrics[port_no] = {
                                    "rx_mbps": round(rx_mbps, 4),
                                    "tx_mbps": round(tx_mbps, 4),
                                    "total_mbps": round(rx_mbps + tx_mbps, 4),
                                    "rx_packets": port_stat.get("rx_packets", 0),
                                    "tx_packets": port_stat.get("tx_packets", 0),
                                    "rx_errors": port_stat.get("rx_errors", 0),
                                    "tx_errors": port_stat.get("tx_errors", 0)
                                }
                        
                        if switch_port_metrics:
                            all_port_metrics[dpid] = switch_port_metrics
                        
                        # Update previous stats for the next run
                        for port_stat in current_stats_list:
                             self.previous_port_stats[f"{dpid}-{port_stat.get('port_no')}"] = port_stat

        self.last_stats_timestamp = current_timestamp

        switches_count = len([n for n in topology_data.get("nodes", []) if n.get('type') == 'switch'])
        
        # Determine SDN status based on connectivity
        sdn_status = "connected" if switches_count > 0 else "disconnected"
        
        # Calculate aggregated performance metrics (non-zero aggregation)
        total_flows = sum(len(flows) for flows in flow_statistics.values())
        active_flows = sum(
            len([f for f in flows if f.get('packet_count', 0) > 0])
            for flows in flow_statistics.values()
        )
        
        # Calculate smart bandwidth aggregation
        total_bandwidth = 0.0
        max_bandwidth = 0.0
        active_ports = 0
        
        for dpid_metrics in all_port_metrics.values():
            for port_metrics in dpid_metrics.values():
                port_bw = port_metrics.get('total_mbps', 0)
                if port_bw > 0:  # Only count active ports
                    total_bandwidth += port_bw
                    max_bandwidth = max(max_bandwidth, port_bw)
                    active_ports += 1
        
        avg_bandwidth = total_bandwidth / active_ports if active_ports > 0 else 0

        metrics = {
            "timestamp": topology_data["timestamp"],
            "status": "ok" if sdn_status == "connected" else "error",
            "switches_count": switches_count,
            "hosts_count": len([n for n in topology_data.get("nodes", []) if n.get('type') == 'host']),
            "links_count": len(topology_data.get("links", [])),
            "topology": topology_data,
            "port_metrics": all_port_metrics,
            "sdn_status": sdn_status,
            "performance_metrics": {
                "bandwidth": {
                    "total_mbps": round(total_bandwidth, 4),
                    "average_mbps": round(avg_bandwidth, 4),
                    "max_mbps": round(max_bandwidth, 4),
                    "active_ports": active_ports
                },
                "flows": {
                    "total": total_flows,
                    "active": active_flows,
                    "per_switch_avg": round(total_flows / switches_count, 1) if switches_count > 0 else 0
                },
                "latency": performance_metrics.get("latency", {"average_ms": 0.0, "estimated": True})
            },
            "flow_statistics": flow_statistics
        }
        
        self.storage.store_metric("network", metrics)
        logger.info(f"Network metrics collected: {switches_count} switches, {total_flows} flows, {round(total_bandwidth, 2)} Mbps total bandwidth")
        return metrics

    def get_network_health_score(self) -> Dict[str, Any]:
        """Calculate overall network health score based on various metrics."""
        try:
            # Get latest network metrics
            latest_metrics = self.storage.get_latest_metrics("network")
            if not latest_metrics:
                return {"health_score": 0, "status": "unknown", "details": "No metrics available"}
            
            metrics = latest_metrics.get("metrics", {})
            
            # Calculate health score (0-100)
            score = 100
            issues = []
            
            # Check SDN metrics
            sdn_status = metrics.get("sdn_status")
            if sdn_status != "connected":
                score -= 50
                issues.append("SDN controller unavailable")
            else:
                if metrics.get("switches_count", 0) == 0:
                    score -= 20
                    issues.append("No switches detected")
                if metrics.get("links_count", 0) == 0:
                    score -= 10
                    issues.append("No links detected")

            score = max(0, round(score))
            
            # Determine status
            if score >= 90:
                status = "excellent"
            elif score >= 75:
                status = "good"
            elif score >= 50:
                status = "fair"
            elif score >= 25:
                status = "poor"
            else:
                status = "critical"
            
            return {
                "health_score": score,
                "status": status,
                "issues": issues,
                "last_updated": metrics.get("timestamp", time.time())
            }
            
        except Exception as e:
            logger.error(f"Error calculating network health score: {e}")
            return {"health_score": 0, "status": "error", "details": str(e)}

    def _get_sdn_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from the SDN controller."""
        try:
            # Try to get performance metrics from custom controller endpoint
            url = f"{self.sdn_controller_url}/api/performance/metrics"
            logger.debug(f"Requesting performance metrics from {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.debug(f"Performance metrics endpoint not available: {response.status_code}")
                # Return basic estimated metrics
                return {
                    "latency": {
                        "average_ms": 5.0,  # Default estimate
                        "estimated": True
                    },
                    "bandwidth": {
                        "total_mbps": 0.0,
                        "average_mbps": 0.0,
                        "max_mbps": 0.0
                    }
                }
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to get performance metrics: {e}")
            return {
                "latency": {"average_ms": 5.0, "estimated": True},
                "bandwidth": {"total_mbps": 0.0, "average_mbps": 0.0, "max_mbps": 0.0}
            }

    def _get_sdn_flow_statistics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get flow statistics from the SDN controller."""
        try:
            flow_stats = {}
            
            # Get switches first
            switches = self._get_sdn_switches()
            
            for switch in switches:
                dpid = switch.get('dpid') or switch.get('id')
                if not dpid:
                    continue
                    
                # Get flow stats for this switch
                url = f"{self.sdn_controller_url}/stats/flow/{dpid}"
                logger.debug(f"Requesting flow stats for switch {dpid} from {url}")
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    switch_flows = response.json().get(dpid, [])
                    processed_flows = []
                    
                    for flow in switch_flows:
                        # Process flow to extract meaningful information
                        processed_flow = {
                            'priority': flow.get('priority', 0),
                            'table_id': flow.get('table_id', 0),
                            'duration_sec': flow.get('duration_sec', 0),
                            'packet_count': flow.get('packet_count', 0),
                            'byte_count': flow.get('byte_count', 0),
                            'idle_timeout': flow.get('idle_timeout', 0),
                            'hard_timeout': flow.get('hard_timeout', 0),
                            'cookie': flow.get('cookie', 0)
                        }
                        
                        # Process match criteria
                        match = flow.get('match', {})
                        match_desc = []
                        if 'in_port' in match:
                            match_desc.append(f"in_port={match['in_port']}")
                        if 'eth_type' in match:
                            eth_type = match['eth_type']
                            if eth_type == 0x0800:
                                match_desc.append("IPv4")
                            elif eth_type == 0x0806:
                                match_desc.append("ARP")
                            else:
                                match_desc.append(f"eth_type=0x{eth_type:04x}")
                        if 'ipv4_src' in match:
                            match_desc.append(f"src={match['ipv4_src']}")
                        if 'ipv4_dst' in match:
                            match_desc.append(f"dst={match['ipv4_dst']}")
                        
                        processed_flow['match_description'] = ', '.join(match_desc) if match_desc else "any"
                        
                        # Process actions
                        instructions = flow.get('instructions', [])
                        action_desc = []
                        for instruction in instructions:
                            if instruction.get('type') == 'APPLY_ACTIONS':
                                actions = instruction.get('actions', [])
                                for action in actions:
                                    action_type = action.get('type', 'unknown')
                                    if action_type == 'OUTPUT':
                                        port = action.get('port', 'unknown')
                                        if port == 'CONTROLLER':
                                            action_desc.append("controller")
                                        elif port == 'FLOOD':
                                            action_desc.append("flood")
                                        else:
                                            action_desc.append(f"port_{port}")
                                    else:
                                        action_desc.append(action_type.lower())
                        
                        processed_flow['action_description'] = ', '.join(action_desc) if action_desc else "unknown"
                        processed_flows.append(processed_flow)
                    
                    flow_stats[dpid] = processed_flows
                    logger.debug(f"Collected {len(processed_flows)} flows for switch {dpid}")
                else:
                    logger.warning(f"Failed to get flow stats for switch {dpid}: {response.status_code}")
                    flow_stats[dpid] = []
            
            return flow_stats
            
        except Exception as e:
            logger.error(f"Error collecting flow statistics: {e}")
            return {}