# Copyright 2025 flopy-net Contributors (abdulmeLINK)
# SPDX-License-Identifier: Apache-2.0
"""
Network Routes Module for Collector API.

Extracted from server.py to reduce file size.
Provides Flask routes for network topology, flows, and performance metrics.
"""
import json
import logging
import time
import requests
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Create blueprint for network routes
network_bp = Blueprint('network', __name__, url_prefix='/network')


def init_network_routes(storage, requires_auth):
    """
    Initialize network routes with storage and auth decorator.
    
    Args:
        storage: MetricsStorage instance
        requires_auth: Authentication decorator
    
    Returns:
        Blueprint with registered routes
    """
    
    @network_bp.route('/topology', methods=['GET'])
    @requires_auth
    def get_network_topology():
        """
        Get detailed network topology data from GNS3 and SDN controller.
        
        This endpoint provides comprehensive topology information including:
        - GNS3 nodes and links
        - SDN switches, ports, and flows
        - Host discovery from SDN controller
        - Link bandwidth and latency metrics
        """
        try:
            # Get query parameters
            source = request.args.get('source', 'all')  # 'all', 'gns3', 'sdn'
            include_metrics = request.args.get('include_metrics', 'true').lower() == 'true'
            format_type = request.args.get('format', 'detailed')  # 'detailed', 'summary'
            
            # Get latest network metrics containing topology data
            latest_network = storage.load_metrics(
                type_filter='network',
                limit=1,
                sort_desc=True
            )
            
            # If no stored network data, try to get live data directly from network monitor
            if not latest_network:
                logger.warning("No stored network data found, attempting to collect live topology data")
                
                # Try to access network monitor for live collection
                if hasattr(storage, 'network_monitor') and storage.network_monitor:
                    try:
                        topology = storage.network_monitor.get_live_topology()
                        
                        # Create minimal network data structure
                        network_data = {
                            "status": "live_collection",
                            "project_name": "unknown",
                            "project_id": "unknown",
                            "project_status": "unknown",
                            "topology": topology,
                            "collection_timestamp": time.time()
                        }
                        
                    except Exception as e:
                        logger.error(f"Failed to collect live topology data: {e}")
                        return _empty_topology_response('Network monitoring not available - empty topology returned')
                else:
                    return _empty_topology_response('Network monitor not available - empty topology returned')
            else:
                network_data = latest_network[0].get('data', {})
            
            topology = network_data.get('topology', {})
            
            # If no topology data in stored metrics, still try to return a valid structure
            if not topology:
                logger.warning("No topology data in stored network metrics")
                topology = {
                    "nodes": [],
                    "links": [],
                    "switches": [],
                    "hosts": [],
                    "timestamp": time.time()
                }
            
            # Filter data based on source parameter
            result = {
                'timestamp': topology.get('timestamp', time.time()),
                'collection_time': network_data.get('collection_timestamp', time.time()),
                'project_info': {
                    'name': network_data.get('project_name', 'unknown'),
                    'id': network_data.get('project_id', 'unknown'),
                    'status': network_data.get('project_status', 'unknown')
                }
            }
            
            if source in ['all', 'gns3']:
                result['nodes'] = topology.get('nodes', [])
                result['links'] = [link for link in topology.get('links', []) 
                                 if link.get('source') == 'gns3' or source == 'gns3']
            
            if source in ['all', 'sdn']:
                result['switches'] = topology.get('switches', [])
                result['hosts'] = topology.get('hosts', [])
                if source == 'sdn':
                    result['links'] = [link for link in topology.get('links', []) 
                                     if link.get('source') == 'sdn']
                elif source == 'all':
                    if 'links' not in result:
                        result['links'] = []
                    result['links'].extend([link for link in topology.get('links', []) 
                                          if link.get('source') == 'sdn'])
            
            # Add summary statistics
            result['statistics'] = {
                'total_nodes': len(result.get('nodes', [])),
                'total_links': len(result.get('links', [])),
                'total_switches': len(result.get('switches', [])),
                'total_hosts': len(result.get('hosts', [])),
                'gns3_links': len([l for l in result.get('links', []) if l.get('source') == 'gns3']),
                'sdn_links': len([l for l in result.get('links', []) if l.get('source') == 'sdn'])
            }
            
            # Include network performance metrics if requested
            if include_metrics:
                result['metrics'] = {
                    'sdn_status': network_data.get('sdn_status', 'unknown'),
                    'switches_count': network_data.get('switches_count', 0),
                    'total_flows': network_data.get('total_flows', 0),
                    'total_ports': network_data.get('total_ports', 0),
                    'avg_latency_ms': network_data.get('avg_latency_ms', 0),
                    'packet_loss_percent': network_data.get('packet_loss_percent', 0),
                    'bandwidth_utilization_percent': network_data.get('bandwidth_utilization_percent', 0)
                }
            
            # Format output based on format_type
            if format_type == 'summary':
                # Return simplified version for overview displays
                return jsonify({
                    'summary': result['statistics'],
                    'status': {
                        'gns3_connected': network_data.get('status') == 'connected',
                        'sdn_connected': network_data.get('sdn_status') == 'connected',
                        'project_name': result['project_info']['name']
                    },
                    'timestamp': result['timestamp']
                })
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error getting network topology: {e}")
            return jsonify({
                'error': str(e),
                'message': 'Failed to retrieve network topology data'
            }), 500

    @network_bp.route('/topology/live', methods=['GET'])
    @requires_auth
    def get_live_network_topology():
        """
        Get live network topology data by directly querying network monitor.
        This bypasses storage for real-time topology updates.
        """
        try:
            # Access the network monitor if available
            if hasattr(storage, 'network_monitor') and storage.network_monitor:
                network_monitor = storage.network_monitor
                
                # Trigger fresh topology collection
                topology_data = network_monitor.get_live_topology()
                
                return jsonify({
                    'topology': topology_data,
                    'timestamp': time.time(),
                    'source': 'live_query',
                    'statistics': {
                        'total_nodes': len(topology_data.get('nodes', [])),
                        'total_links': len(topology_data.get('links', [])),
                        'total_switches': len(topology_data.get('switches', [])),
                        'total_hosts': len(topology_data.get('hosts', []))
                    }
                })
            else:
                return jsonify({
                    'topology': {
                        'nodes': [],
                        'links': [],
                        'switches': [],
                        'hosts': [],
                        'timestamp': time.time()
                    },
                    'timestamp': time.time(),
                    'source': 'no_monitor',
                    'statistics': {
                        'total_nodes': 0,
                        'total_links': 0,
                        'total_switches': 0,
                        'total_hosts': 0
                    },
                    'message': 'Network monitor not available - empty topology returned'
                })
                
        except Exception as e:
            logger.error(f"Error getting live network topology: {e}")
            return jsonify({
                'error': str(e),
                'message': 'Failed to retrieve live network topology'
            }), 500

    @network_bp.route('/flows', methods=['GET'])
    @requires_auth
    def get_network_flows():
        """
        Get OpenFlow flows from all switches in the network.
        This endpoint queries the SDN controller directly for flow data.
        """
        try:
            # Get SDN controller URL from network monitor
            if hasattr(storage, 'network_monitor') and storage.network_monitor:
                sdn_controller_url = storage.network_monitor.sdn_controller_url
            else:
                sdn_controller_url = "http://localhost:8181"
            
            all_flows = []
            
            try:
                # Get all flows from Ryu SDN controller
                flows_response = requests.get(f"{sdn_controller_url}/stats/flows", timeout=10)
                
                if flows_response.status_code == 200:
                    flows_data = flows_response.json()
                    logger.info(f"Retrieved {len(flows_data)} flows from SDN controller")
                    
                    # Process flows
                    for flow_id, flow_data in flows_data.items():
                        datapath_id = flow_data.get("datapath_id")
                        
                        if datapath_id:
                            switch_dpid_str = f"{datapath_id:016x}"
                        else:
                            switch_dpid_str = "unknown"
                        
                        enhanced_flow = flow_data.copy()
                        enhanced_flow["flow_id"] = flow_id
                        enhanced_flow["switch_dpid"] = switch_dpid_str
                        all_flows.append(enhanced_flow)
                        
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not get flows from SDN controller: {e}")
            
            return jsonify({
                'flows': all_flows,
                'count': len(all_flows),
                'timestamp': time.time(),
                'source': 'sdn_controller'
            })
            
        except Exception as e:
            logger.error(f"Error getting network flows: {e}")
            return jsonify({
                'error': str(e),
                'message': 'Failed to retrieve network flows'
            }), 500

    @network_bp.route('/performance', methods=['GET'])
    @requires_auth
    def get_performance_metrics():
        """
        Get network performance metrics including bandwidth, latency, and packet loss.
        """
        try:
            # Get SDN controller URL
            if hasattr(storage, 'network_monitor') and storage.network_monitor:
                sdn_controller_url = storage.network_monitor.sdn_controller_url
            else:
                sdn_controller_url = "http://localhost:8181"
            
            performance_data = {
                'timestamp': time.time(),
                'switches': [],
                'aggregate': {
                    'total_rx_bytes': 0,
                    'total_tx_bytes': 0,
                    'total_rx_packets': 0,
                    'total_tx_packets': 0,
                    'total_rx_errors': 0,
                    'total_tx_errors': 0,
                    'total_rx_dropped': 0,
                    'total_tx_dropped': 0
                }
            }
            
            try:
                # Get port statistics from SDN controller
                port_stats_response = requests.get(f"{sdn_controller_url}/stats/port", timeout=10)
                
                if port_stats_response.status_code == 200:
                    port_stats = port_stats_response.json()
                    
                    for dpid, ports in port_stats.items():
                        switch_stats = {
                            'dpid': dpid,
                            'ports': []
                        }
                        
                        for port in ports:
                            port_data = {
                                'port_no': port.get('port_no'),
                                'rx_bytes': port.get('rx_bytes', 0),
                                'tx_bytes': port.get('tx_bytes', 0),
                                'rx_packets': port.get('rx_packets', 0),
                                'tx_packets': port.get('tx_packets', 0),
                                'rx_errors': port.get('rx_errors', 0),
                                'tx_errors': port.get('tx_errors', 0),
                                'rx_dropped': port.get('rx_dropped', 0),
                                'tx_dropped': port.get('tx_dropped', 0)
                            }
                            switch_stats['ports'].append(port_data)
                            
                            # Aggregate stats
                            performance_data['aggregate']['total_rx_bytes'] += port_data['rx_bytes']
                            performance_data['aggregate']['total_tx_bytes'] += port_data['tx_bytes']
                            performance_data['aggregate']['total_rx_packets'] += port_data['rx_packets']
                            performance_data['aggregate']['total_tx_packets'] += port_data['tx_packets']
                            performance_data['aggregate']['total_rx_errors'] += port_data['rx_errors']
                            performance_data['aggregate']['total_tx_errors'] += port_data['tx_errors']
                            performance_data['aggregate']['total_rx_dropped'] += port_data['rx_dropped']
                            performance_data['aggregate']['total_tx_dropped'] += port_data['tx_dropped']
                        
                        performance_data['switches'].append(switch_stats)
                        
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not get port stats from SDN controller: {e}")
                performance_data['error'] = str(e)
            
            return jsonify(performance_data)
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return jsonify({
                'error': str(e),
                'message': 'Failed to retrieve performance metrics'
            }), 500

    @network_bp.route('/flow-statistics', methods=['GET'])
    @requires_auth
    def get_flow_statistics():
        """
        Get detailed flow statistics from the SDN controller.
        """
        try:
            # Get SDN controller URL
            if hasattr(storage, 'network_monitor') and storage.network_monitor:
                sdn_controller_url = storage.network_monitor.sdn_controller_url
            else:
                sdn_controller_url = "http://localhost:8181"
            
            flow_stats = {
                'timestamp': time.time(),
                'switches': [],
                'summary': {
                    'total_flows': 0,
                    'total_packet_count': 0,
                    'total_byte_count': 0
                }
            }
            
            try:
                # Get flow statistics from SDN controller
                stats_response = requests.get(f"{sdn_controller_url}/stats/flow", timeout=10)
                
                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    
                    for dpid, flows in stats_data.items():
                        switch_flow_stats = {
                            'dpid': dpid,
                            'flow_count': len(flows),
                            'flows': []
                        }
                        
                        for flow in flows:
                            flow_info = {
                                'priority': flow.get('priority', 0),
                                'packet_count': flow.get('packet_count', 0),
                                'byte_count': flow.get('byte_count', 0),
                                'duration_sec': flow.get('duration_sec', 0),
                                'match': flow.get('match', {}),
                                'actions': flow.get('actions', [])
                            }
                            switch_flow_stats['flows'].append(flow_info)
                            
                            # Update summary
                            flow_stats['summary']['total_packet_count'] += flow_info['packet_count']
                            flow_stats['summary']['total_byte_count'] += flow_info['byte_count']
                        
                        flow_stats['switches'].append(switch_flow_stats)
                        flow_stats['summary']['total_flows'] += len(flows)
                        
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not get flow stats from SDN controller: {e}")
                flow_stats['error'] = str(e)
            
            return jsonify(flow_stats)
            
        except Exception as e:
            logger.error(f"Error getting flow statistics: {e}")
            return jsonify({
                'error': str(e),
                'message': 'Failed to retrieve flow statistics'
            }), 500

    return network_bp


def _empty_topology_response(message: str):
    """Return an empty topology response with a message."""
    return jsonify({
        'nodes': [],
        'links': [],
        'switches': [],
        'hosts': [],
        'statistics': {
            'total_nodes': 0,
            'total_links': 0,
            'total_switches': 0,
            'total_hosts': 0,
            'gns3_links': 0,
            'sdn_links': 0
        },
        'project_info': {
            'name': 'no_project',
            'id': 'unknown',
            'status': 'disconnected'
        },
        'timestamp': time.time(),
        'collection_time': time.time(),
        'message': message
    })
