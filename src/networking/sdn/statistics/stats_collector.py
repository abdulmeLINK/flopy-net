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
SDN Statistics Collector

This module handles collection and processing of SDN statistics including
port statistics, flow statistics, and performance metrics.
"""

import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class StatsCollector:
    """Collects and processes SDN statistics from OpenFlow switches."""
    
    def __init__(self, session, base_url: str, timeout: int = 30):
        """
        Initialize the StatsCollector.
        
        Args:
            session: HTTP session for API requests
            base_url: Base URL for the Ryu REST API
            timeout: Request timeout in seconds
        """
        self.session = session
        self.base_url = base_url
        self.timeout = timeout
        self.logger = logger
        
        # Statistics caches
        self.port_stats_cache = {}
        self.flow_stats_cache = {}
        self.last_stats_collection = 0
        self.stats_collection_interval = 10
    
    def get_port_statistics(self, dpid: str = None, get_switches_func=None) -> Dict[str, Any]:
        """
        Get real port statistics from OpenFlow switches.
        
        Args:
            dpid: Switch DPID (hex string). If None, get stats from all switches.
            get_switches_func: Function to get list of switches
            
        Returns:
            Dict containing port statistics with bandwidth calculations
        """
        try:
            current_time = time.time()
            port_stats = {}
            
            # Get switches to query
            if dpid:
                switches_to_query = [dpid]
            elif get_switches_func:
                switches_to_query = [sw.get('dpid', sw.get('id')) for sw in get_switches_func()]
            else:
                return {}
            
            for switch_dpid in switches_to_query:
                if not switch_dpid:
                    continue
                    
                # Query port stats from Ryu REST API
                url = f"{self.base_url}/stats/port/{switch_dpid}"
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    switch_port_stats = response.json().get(str(switch_dpid), [])
                    
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

    def get_flow_statistics(self, dpid: str = None, get_switches_func=None) -> Dict[str, Any]:
        """
        Get real flow statistics from OpenFlow switches.
        
        Args:
            dpid: Switch DPID (hex string). If None, get stats from all switches.
            get_switches_func: Function to get list of switches
            
        Returns:
            Dict containing flow statistics with proper match fields and actions
        """
        try:
            current_time = time.time()
            flow_stats = {}
            
            # Get switches to query
            if dpid:
                switches_to_query = [dpid]
            elif get_switches_func:
                switches_to_query = [sw.get('dpid', sw.get('id')) for sw in get_switches_func()]
            else:
                return {}
            
            for switch_dpid in switches_to_query:
                if not switch_dpid:
                    continue
                    
                # Query flow stats from Ryu REST API
                url = f"{self.base_url}/stats/flow/{switch_dpid}"
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    switch_flow_stats = response.json().get(str(switch_dpid), [])
                    
                    # Process each flow entry
                    processed_flows = []
                    for flow_entry in switch_flow_stats:
                        processed_flow = self.process_flow_entry(flow_entry)
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

    def process_flow_entry(self, flow_entry: Dict[str, Any]) -> Dict[str, Any]:
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

    def get_performance_metrics(self, get_switches_func=None) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics including bandwidth, latency estimates, and flow counts.
        
        Args:
            get_switches_func: Function to get list of switches
            
        Returns:
            Dict containing performance metrics
        """
        try:
            current_time = time.time()
            
            # Collect fresh statistics if needed
            if current_time - self.last_stats_collection > self.stats_collection_interval:
                port_stats = self.get_port_statistics(get_switches_func=get_switches_func)
                flow_stats = self.get_flow_statistics(get_switches_func=get_switches_func)
            else:
                # Use cached data
                port_stats = {}
                flow_stats = {}
                if get_switches_func:
                    for dpid in [sw.get('dpid', sw.get('id')) for sw in get_switches_func()]:
                        if f"{dpid}_1" in self.port_stats_cache:
                            switch_ports = []
                            for key, cached_stats in self.port_stats_cache.items():
                                if key.startswith(f"{dpid}_"):
                                    port_no = key.split('_')[1]
                                    switch_ports.append({
                                        'port_no': int(port_no),
                                        'rx_mbps': 0,
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
            total_switches = len(get_switches_func()) if get_switches_func else 0
            
            # Calculate bandwidth metrics from port statistics
            for dpid, ports in port_stats.items():
                for port in ports:
                    port_bandwidth = port.get('total_mbps', 0)
                    total_bandwidth += port_bandwidth
                    max_bandwidth = max(max_bandwidth, port_bandwidth)
            
            # Count active flows
            for dpid, flows in flow_stats.items():
                active_flows += len([f for f in flows if f.get('packet_count', 0) > 0])
            
            # Calculate average bandwidth
            non_zero_ports = sum(1 for dpid, ports in port_stats.items() 
                               for port in ports if port.get('total_mbps', 0) > 0)
            avg_bandwidth = total_bandwidth / non_zero_ports if non_zero_ports > 0 else 0
            
            # Estimate latency based on flow processing
            avg_latency = 0.0
            if active_flows > 0:
                avg_latency = min(5 + (active_flows * 0.1), 100)
            
            metrics = {
                "timestamp": current_time,
                "bandwidth": {
                    "total_mbps": round(total_bandwidth, 4),
                    "average_mbps": round(avg_bandwidth, 4),
                    "max_mbps": round(max_bandwidth, 4)
                },
                "latency": {
                    "average_ms": round(avg_latency, 2),
                    "estimated": True
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
    
    def get_network_statistics(self, get_switches_func=None) -> Dict[str, Any]:
        """
        Get comprehensive network statistics including performance metrics.
        
        Args:
            get_switches_func: Function to get list of switches
            
        Returns:
            Dict containing network statistics with real performance data
        """
        try:
            # Collect real-time statistics
            switches = get_switches_func() if get_switches_func else []
            port_stats = self.get_port_statistics(get_switches_func=get_switches_func)
            flow_stats = self.get_flow_statistics(get_switches_func=get_switches_func)
            performance_metrics = self.get_performance_metrics(get_switches_func=get_switches_func)
            
            # Calculate network-wide statistics
            total_switches = len(switches)
            total_ports = sum(len(switch.get('ports', [])) for switch in switches)
            total_flows = sum(len(flows) for flows in flow_stats.values())
            
            # Calculate active flows
            active_flows = 0
            for dpid, flows in flow_stats.items():
                active_flows += len([f for f in flows if f.get('packet_count', 0) > 0])
            
            # Build comprehensive statistics
            stats = {
                "timestamp": time.time(),
                "switches": {
                    "total": total_switches,
                    "details": [{"dpid": sw.get('dpid', sw.get('id')), 
                                "ports": len(sw.get('ports', []))} for sw in switches]
                },
                "ports": {
                    "total": total_ports
                },
                "flows": {
                    "total": total_flows,
                    "active": active_flows
                },
                "performance": performance_metrics,
                "port_statistics": port_stats,
                "flow_statistics": flow_stats
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting network statistics: {e}")
            return {"error": str(e)}
