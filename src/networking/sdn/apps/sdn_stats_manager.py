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
SDN Statistics Manager - Handles statistics collection and performance metrics.

Extracted from policy_switch_core.py to improve maintainability and reduce file size.
Provides classes for:
- Statistics collection from switches
- Performance metrics calculation
- Flow statistics aggregation
"""

import time
import logging
from typing import Dict, Any, List, Optional

from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib

LOG = logging.getLogger('ryu.app.sdn_stats_manager')


class CumulativeStats:
    """
    Tracks cumulative network statistics over time.
    """
    
    def __init__(self):
        """Initialize cumulative stats."""
        self.total_bytes_transferred = 0
        self.total_packets_transferred = 0
        self.total_flows_created = 0
        self.start_time = time.time()
        self.last_reset = time.time()
        self.peak_bandwidth = 0
        self.total_errors = 0
    
    def add_bytes(self, bytes_count: int) -> None:
        """Add transferred bytes to cumulative count."""
        self.total_bytes_transferred += bytes_count
    
    def add_packets(self, packet_count: int) -> None:
        """Add transferred packets to cumulative count."""
        self.total_packets_transferred += packet_count
    
    def add_flow(self) -> None:
        """Increment flow count."""
        self.total_flows_created += 1
    
    def add_errors(self, error_count: int) -> None:
        """Add errors to cumulative count."""
        self.total_errors += error_count
    
    def update_peak_bandwidth(self, bandwidth: float) -> None:
        """Update peak bandwidth if current is higher."""
        if bandwidth > self.peak_bandwidth:
            self.peak_bandwidth = bandwidth
    
    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        uptime_seconds = self.get_uptime()
        total_mb = self.total_bytes_transferred / (1024 * 1024)
        total_gb = total_mb / 1024
        
        return {
            'bytes_transferred': self.total_bytes_transferred,
            'megabytes_transferred': round(total_mb, 2),
            'gigabytes_transferred': round(total_gb, 3),
            'packets_transferred': self.total_packets_transferred,
            'flows_created': self.total_flows_created,
            'total_errors': self.total_errors,
            'uptime_seconds': round(uptime_seconds, 1),
            'uptime_minutes': round(uptime_seconds / 60, 1),
            'uptime_hours': round(uptime_seconds / 3600, 2),
            'peak_bandwidth': self.peak_bandwidth
        }
    
    def get_rates(self) -> Dict[str, float]:
        """Get transfer rates."""
        uptime_seconds = self.get_uptime()
        if uptime_seconds <= 0:
            return {'bytes_per_second': 0, 'packets_per_second': 0, 'flows_per_hour': 0}
        
        return {
            'bytes_per_second': self.total_bytes_transferred / uptime_seconds,
            'packets_per_second': self.total_packets_transferred / uptime_seconds,
            'flows_per_hour': self.total_flows_created / (uptime_seconds / 3600)
        }


class PerformanceMetricsCalculator:
    """
    Calculates performance metrics from switch statistics.
    """
    
    def __init__(self, cumulative_stats: CumulativeStats, start_time: float):
        """
        Initialize the calculator.
        
        Args:
            cumulative_stats: CumulativeStats instance
            start_time: Controller start time
        """
        self.cumulative_stats = cumulative_stats
        self.start_time = start_time
    
    def calculate(self, switches: Dict[int, Dict], flows: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            switches: Dictionary of switch data
            flows: Dictionary of flow data
            
        Returns:
            Dictionary of performance metrics
        """
        try:
            # Collect port statistics from all switches
            total_bandwidth = 0
            bandwidth_values = []
            port_counts = {'total': 0, 'up': 0, 'errors': 0}
            latency_values = []
            
            for dpid, switch_data in switches.items():
                port_stats = switch_data.get('port_stats', {})
                ports_info = switch_data.get('ports', {})
                
                for port_no, port_info in ports_info.items():
                    port_counts['total'] += 1
                    
                    # Get port statistics
                    stats = port_stats.get(port_no, {})
                    rx_bps = stats.get('rx_bps', 0)
                    tx_bps = stats.get('tx_bps', 0)
                    
                    # Only count non-zero bandwidth values
                    if rx_bps > 0 or tx_bps > 0:
                        port_bandwidth = rx_bps + tx_bps
                        total_bandwidth += port_bandwidth
                        bandwidth_values.append(port_bandwidth)
                        port_counts['up'] += 1
                    
                    # Count ports with errors
                    if stats.get('rx_errors', 0) > 0 or stats.get('tx_errors', 0) > 0:
                        port_counts['errors'] += 1
                    
                    # Simulate latency measurements
                    if rx_bps > 0 or tx_bps > 0:
                        simulated_latency = max(5, min(100, 50 - (port_bandwidth / 1000000)))
                        latency_values.append(simulated_latency)
            
            # Calculate metrics
            bandwidth_metrics = self._calculate_bandwidth_metrics(
                total_bandwidth, bandwidth_values
            )
            latency_metrics = self._calculate_latency_metrics(latency_values)
            health_score = self._calculate_health_score(
                latency_metrics, port_counts
            )
            
            return {
                'bandwidth': bandwidth_metrics,
                'latency': latency_metrics,
                'packet_loss': 0,
                'flows': {
                    'total': len(flows),
                    'active': len([f for f in flows.values() if f.get('packet_count', 0) > 0])
                },
                'ports': port_counts,
                'health_score': health_score,
                'timestamp': time.time(),
                'totals': self.cumulative_stats.to_dict(),
                'rates': self.cumulative_stats.get_rates()
            }
            
        except Exception as e:
            LOG.error(f"Error collecting performance metrics: {e}")
            return self._get_fallback_metrics(flows)
    
    def _calculate_bandwidth_metrics(self, total_bandwidth: float,
                                     bandwidth_values: List[float]) -> Dict[str, float]:
        """Calculate bandwidth metrics."""
        return {
            'current_total_bps': total_bandwidth,
            'current_average_bps': sum(bandwidth_values) / len(bandwidth_values) if bandwidth_values else 0,
            'active_ports': len(bandwidth_values),
            'peak_bandwidth_bps': self.cumulative_stats.peak_bandwidth
        }
    
    def _calculate_latency_metrics(self, latency_values: List[float]) -> Dict[str, float]:
        """Calculate latency metrics."""
        if latency_values:
            return {
                'average_ms': sum(latency_values) / len(latency_values),
                'min_ms': min(latency_values),
                'max_ms': max(latency_values)
            }
        return {'average_ms': 0, 'min_ms': 0, 'max_ms': 0}
    
    def _calculate_health_score(self, latency_metrics: Dict[str, float],
                                port_counts: Dict[str, int]) -> int:
        """Calculate network health score (0-100)."""
        health_score = 100
        
        # Reduce score for high latency
        if latency_metrics['average_ms'] > 50:
            health_score -= 20
        elif latency_metrics['average_ms'] > 30:
            health_score -= 10
        
        # Reduce score for port errors
        if port_counts['errors'] > 0:
            error_ratio = port_counts['errors'] / max(port_counts['total'], 1)
            health_score -= int(error_ratio * 30)
        
        # Reduce score for low utilization
        if port_counts['up'] < port_counts['total'] * 0.8:
            health_score -= 15
        
        return max(0, min(100, health_score))
    
    def _get_fallback_metrics(self, flows: Dict[str, Dict]) -> Dict[str, Any]:
        """Get fallback metrics when calculation fails."""
        uptime_seconds = time.time() - self.start_time
        return {
            'bandwidth': {
                'current_total_bps': 0,
                'current_average_bps': 0,
                'active_ports': 0,
                'peak_bandwidth_bps': 0
            },
            'latency': {'average_ms': 0, 'min_ms': 0, 'max_ms': 0},
            'packet_loss': 0,
            'flows': {'total': len(flows), 'active': 0},
            'ports': {'total': 0, 'up': 0, 'errors': 0},
            'health_score': 50,
            'timestamp': time.time(),
            'totals': {
                'bytes_transferred': 0,
                'megabytes_transferred': 0,
                'gigabytes_transferred': 0,
                'packets_transferred': 0,
                'flows_created': 0,
                'total_errors': 0,
                'uptime_seconds': round(uptime_seconds, 1),
                'uptime_minutes': round(uptime_seconds / 60, 1),
                'uptime_hours': round(uptime_seconds / 3600, 2)
            },
            'rates': {
                'bytes_per_second': 0,
                'packets_per_second': 0,
                'flows_per_hour': 0
            }
        }


class FlowStatisticsCalculator:
    """
    Calculates flow statistics with efficiency metrics.
    """
    
    def calculate(self, flows: Dict[str, Dict], switches: Dict[int, Dict]) -> Dict[str, Any]:
        """
        Calculate comprehensive flow statistics.
        
        Args:
            flows: Dictionary of flow data
            switches: Dictionary of switch data
            
        Returns:
            Dictionary of flow statistics
        """
        try:
            flow_count_by_switch = {}
            total_packet_count = 0
            total_byte_count = 0
            active_flows = 0
            
            # Analyze flows by switch
            for flow_key, flow_data in flows.items():
                dpid = flow_data.get('datapath_id', 'unknown')
                if dpid not in flow_count_by_switch:
                    flow_count_by_switch[dpid] = {'count': 0, 'active': 0, 'bytes': 0, 'packets': 0}
                
                flow_count_by_switch[dpid]['count'] += 1
                
                # Check if flow is active
                packet_count = flow_data.get('packet_count', 0)
                byte_count = flow_data.get('byte_count', 0)
                
                if packet_count > 0:
                    active_flows += 1
                    flow_count_by_switch[dpid]['active'] += 1
                    flow_count_by_switch[dpid]['packets'] += packet_count
                    flow_count_by_switch[dpid]['bytes'] += byte_count
                    total_packet_count += packet_count
                    total_byte_count += byte_count
            
            # Calculate metrics
            total_flows = len(flows)
            efficiency_score = self._calculate_efficiency_score(
                total_flows, active_flows, flow_count_by_switch
            )
            utilization = self._calculate_utilization(total_byte_count, switches)
            
            return {
                'total_flows': total_flows,
                'active_flows': active_flows,
                'flows_by_switch': flow_count_by_switch,
                'total_packets': total_packet_count,
                'total_bytes': total_byte_count,
                'efficiency_score': efficiency_score,
                'utilization': utilization,
                'timestamp': time.time()
            }
            
        except Exception as e:
            LOG.error(f"Error collecting flow statistics: {e}")
            return {
                'total_flows': len(flows),
                'active_flows': 0,
                'flows_by_switch': {},
                'total_packets': 0,
                'total_bytes': 0,
                'efficiency_score': 50,
                'utilization': 0,
                'timestamp': time.time()
            }
    
    def _calculate_efficiency_score(self, total_flows: int, active_flows: int,
                                    flow_count_by_switch: Dict) -> int:
        """Calculate flow efficiency score."""
        if total_flows <= 0:
            return 0
        
        # Efficiency based on active flow ratio
        active_ratio = active_flows / total_flows
        efficiency_score = int(active_ratio * 70)
        
        # Bonus points for reasonable flow counts
        if total_flows < 100:
            efficiency_score += 20
        elif total_flows < 500:
            efficiency_score += 10
        
        # Bonus for balanced distribution
        if len(flow_count_by_switch) > 1:
            flows_per_switch = [data['count'] for data in flow_count_by_switch.values()]
            if max(flows_per_switch) - min(flows_per_switch) < max(flows_per_switch) * 0.5:
                efficiency_score += 10
        
        return min(100, max(0, efficiency_score))
    
    def _calculate_utilization(self, total_byte_count: int, switches: Dict) -> float:
        """Calculate network utilization."""
        if total_byte_count <= 0:
            return 0
        
        # Assume 1Gbps baseline capacity per switch
        estimated_capacity = len(switches) * 1000000000
        if estimated_capacity <= 0:
            return 0
        
        return min(1.0, total_byte_count / estimated_capacity)


class PortStatsProcessor:
    """
    Processes port statistics replies and updates cumulative stats.
    """
    
    def __init__(self, cumulative_stats: CumulativeStats):
        """
        Initialize the processor.
        
        Args:
            cumulative_stats: CumulativeStats instance to update
        """
        self.cumulative_stats = cumulative_stats
    
    def process(self, port_stats_body: list, dpid: int,
               switches: Dict[int, Dict]) -> None:
        """
        Process port statistics reply.
        
        Args:
            port_stats_body: Port statistics from switch
            dpid: Datapath ID
            switches: Switches dictionary to update
        """
        if dpid not in switches:
            return
        
        # Initialize port stats if needed
        if 'port_stats' not in switches[dpid]:
            switches[dpid]['port_stats'] = {}
        
        current_time = time.time()
        
        for stat in port_stats_body:
            port_no = stat.port_no
            if port_no < ofproto_v1_3.OFPP_MAX:
                old_stats = switches[dpid]['port_stats'].get(port_no, {})
                
                # Calculate bandwidth rates
                rx_bps, tx_bps = self._calculate_bandwidth(stat, old_stats, current_time)
                
                # Update cumulative statistics
                if old_stats and 'timestamp' in old_stats:
                    self._update_cumulative_stats(stat, old_stats, rx_bps, tx_bps)
                
                # Store current statistics
                switches[dpid]['port_stats'][port_no] = {
                    'port_no': port_no,
                    'rx_packets': stat.rx_packets,
                    'tx_packets': stat.tx_packets,
                    'rx_bytes': stat.rx_bytes,
                    'tx_bytes': stat.tx_bytes,
                    'rx_dropped': stat.rx_dropped,
                    'tx_dropped': stat.tx_dropped,
                    'rx_errors': stat.rx_errors,
                    'tx_errors': stat.tx_errors,
                    'timestamp': current_time,
                    'rx_bps': rx_bps,
                    'tx_bps': tx_bps,
                    'total_bps': rx_bps + tx_bps
                }
    
    def _calculate_bandwidth(self, stat, old_stats: Dict, current_time: float) -> tuple:
        """Calculate bandwidth from statistics."""
        rx_bps = 0
        tx_bps = 0
        
        if old_stats and 'timestamp' in old_stats:
            time_diff = current_time - old_stats['timestamp']
            if time_diff > 0:
                rx_byte_diff = stat.rx_bytes - old_stats.get('rx_bytes', 0)
                tx_byte_diff = stat.tx_bytes - old_stats.get('tx_bytes', 0)
                rx_bps = max(0, (rx_byte_diff * 8) / time_diff)
                tx_bps = max(0, (tx_byte_diff * 8) / time_diff)
        
        return rx_bps, tx_bps
    
    def _update_cumulative_stats(self, stat, old_stats: Dict,
                                  rx_bps: float, tx_bps: float) -> None:
        """Update cumulative statistics."""
        # Bytes transferred
        rx_byte_diff = stat.rx_bytes - old_stats.get('rx_bytes', 0)
        tx_byte_diff = stat.tx_bytes - old_stats.get('tx_bytes', 0)
        self.cumulative_stats.add_bytes(rx_byte_diff + tx_byte_diff)
        
        # Packets transferred
        packet_diff = (
            (stat.rx_packets - old_stats.get('rx_packets', 0)) +
            (stat.tx_packets - old_stats.get('tx_packets', 0))
        )
        self.cumulative_stats.add_packets(packet_diff)
        
        # Peak bandwidth
        current_bandwidth = rx_bps + tx_bps
        self.cumulative_stats.update_peak_bandwidth(current_bandwidth)
        
        # Errors
        error_diff = (
            (stat.rx_errors - old_stats.get('rx_errors', 0)) +
            (stat.tx_errors - old_stats.get('tx_errors', 0))
        )
        self.cumulative_stats.add_errors(error_diff)


class FlowStatsProcessor:
    """
    Processes flow statistics replies and updates cumulative stats.
    """
    
    def __init__(self, cumulative_stats: CumulativeStats):
        """
        Initialize the processor.
        
        Args:
            cumulative_stats: CumulativeStats instance to update
        """
        self.cumulative_stats = cumulative_stats
    
    def process(self, flow_stats_body: list, dpid: int,
               flows: Dict[str, Dict], serialize_match_func, 
               serialize_actions_func) -> None:
        """
        Process flow statistics reply.
        
        Args:
            flow_stats_body: Flow statistics from switch
            dpid: Datapath ID
            flows: Flows dictionary to update
            serialize_match_func: Function to serialize match
            serialize_actions_func: Function to serialize actions
        """
        for stat in flow_stats_body:
            flow_key = f"{dpid}_{stat.priority}_{hash(str(stat.match))}"
            
            if flow_key in flows:
                self._update_existing_flow(stat, flow_key, flows)
            else:
                self._add_new_flow(stat, dpid, flow_key, flows,
                                  serialize_match_func, serialize_actions_func)
    
    def _update_existing_flow(self, stat, flow_key: str,
                              flows: Dict[str, Dict]) -> None:
        """Update an existing flow with new statistics."""
        old_flow = flows[flow_key]
        old_packet_count = old_flow.get('packet_count', 0)
        old_byte_count = old_flow.get('byte_count', 0)
        
        # Update cumulative stats
        if stat.packet_count > old_packet_count or stat.byte_count > old_byte_count:
            self.cumulative_stats.add_packets(max(0, stat.packet_count - old_packet_count))
            self.cumulative_stats.add_bytes(max(0, stat.byte_count - old_byte_count))
        
        flows[flow_key].update({
            'packet_count': stat.packet_count,
            'byte_count': stat.byte_count,
            'duration_sec': stat.duration_sec,
            'duration_nsec': stat.duration_nsec,
            'last_updated': time.time()
        })
    
    def _add_new_flow(self, stat, dpid: int, flow_key: str,
                     flows: Dict[str, Dict], serialize_match_func,
                     serialize_actions_func) -> None:
        """Add a new flow to tracking."""
        self.cumulative_stats.add_flow()
        self.cumulative_stats.add_packets(stat.packet_count)
        self.cumulative_stats.add_bytes(stat.byte_count)
        
        flows[flow_key] = {
            'datapath_id': dpid,
            'table_id': stat.table_id,
            'priority': stat.priority,
            'idle_timeout': stat.idle_timeout,
            'hard_timeout': stat.hard_timeout,
            'packet_count': stat.packet_count,
            'byte_count': stat.byte_count,
            'match': serialize_match_func(stat.match),
            'instructions': serialize_actions_func(stat.instructions) if hasattr(stat, 'instructions') else [],
            'duration_sec': stat.duration_sec,
            'duration_nsec': stat.duration_nsec,
            'created_time': time.time()
        }
