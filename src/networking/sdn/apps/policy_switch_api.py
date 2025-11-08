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
REST API Module for PolicySwitch

This module provides REST API endpoints for monitoring and controlling
the PolicySwitch controller.
"""

import json
import time
import logging
from ryu.app.wsgi import ControllerBase, route, Response

LOG = logging.getLogger('ryu.app.policy_switch.api')


def safe_json_serialize(obj):
    """Safely serialize objects that may contain bytes to JSON."""
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, dict):
        return {key: safe_json_serialize(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(safe_json_serialize(item) for item in obj)
    else:
        return obj


class PolicySwitchRESTController(ControllerBase):
    """REST API controller for Policy Switch."""
    
    def __init__(self, req, link, data, **config):
        super(PolicySwitchRESTController, self).__init__(req, link, data, **config)
        self.policy_switch_app = data['policy_switch_app']
    
    # Standard Ryu topology endpoints for collector compatibility
    @route('policy_switch', '/v1.0/topology/switches', methods=['GET'])
    def get_topology_switches(self, req, **kwargs):
        """Get topology switches (Ryu standard format)."""
        switches = self.policy_switch_app.get_switches()
        safe_switches = safe_json_serialize(switches)
        return Response(content_type='application/json', body=json.dumps(safe_switches))
    
    @route('policy_switch', '/v1.0/topology/links', methods=['GET'])
    def get_topology_links(self, req, **kwargs):
        """Get topology links (Ryu standard format)."""
        links = self.policy_switch_app.get_links()
        safe_links = safe_json_serialize(links)
        return Response(content_type='application/json', body=json.dumps(safe_links))
    
    @route('policy_switch', '/v1.0/topology/hosts', methods=['GET'])
    def get_topology_hosts(self, req, **kwargs):
        """Get topology hosts (Ryu standard format)."""
        hosts = self.policy_switch_app.get_hosts()
        safe_hosts = safe_json_serialize(hosts)
        return Response(content_type='application/json', body=json.dumps(safe_hosts))
    
    # Additional stats endpoints
    @route('policy_switch', '/stats/switches', methods=['GET'])
    def get_switches_stats(self, req, **kwargs):
        """Get switches statistics."""
        switches = self.policy_switch_app.get_switches()
        safe_switches = safe_json_serialize(switches)
        return Response(content_type='application/json', body=json.dumps(safe_switches))
    
    @route('policy_switch', '/stats/links', methods=['GET'])
    def get_links_stats(self, req, **kwargs):
        """Get links statistics."""
        links = self.policy_switch_app.get_links()
        safe_links = safe_json_serialize(links)
        return Response(content_type='application/json', body=json.dumps(safe_links))
    
    @route('policy_switch', '/stats/hosts', methods=['GET'])
    def get_hosts_stats(self, req, **kwargs):
        """Get hosts statistics."""
        hosts = self.policy_switch_app.get_hosts()
        safe_hosts = safe_json_serialize(hosts)
        return Response(content_type='application/json', body=json.dumps(safe_hosts))
    
    @route('policy_switch', '/stats/flows', methods=['GET'])
    def get_flows_stats(self, req, **kwargs):
        """Get flows statistics."""
        flows = self.policy_switch_app.get_flows()
        safe_flows = safe_json_serialize(flows)
        return Response(content_type='application/json', body=json.dumps(safe_flows))
    
    # Performance metrics endpoints
    @route('policy_switch', '/api/performance/metrics', methods=['GET'])
    def get_performance_metrics(self, req, **kwargs):
        """Get real-time performance metrics."""
        try:
            # Check if the PolicySwitch app has the get_performance_metrics method
            if hasattr(self.policy_switch_app, 'get_performance_metrics'):
                metrics = self.policy_switch_app.get_performance_metrics()
                safe_metrics = safe_json_serialize(metrics)
                return Response(content_type='application/json', body=json.dumps(safe_metrics))
            else:
                # Fallback to basic metrics if method doesn't exist
                basic_metrics = {
                    'bandwidth': {'total': 0, 'average': 0, 'non_zero_count': 0},
                    'latency': {'average': 0, 'min': 0, 'max': 0},
                    'packet_loss': 0,
                    'flows': {'total': len(self.policy_switch_app.flows), 'active': 0},
                    'ports': {'total': 0, 'up': 0, 'errors': 0},
                    'health_score': 85  # Default health score
                }
                return Response(content_type='application/json', body=json.dumps(basic_metrics))
        except Exception as e:
            LOG.error(f"Error getting performance metrics: {e}")
            return Response(status=500, content_type='application/json',
                          body=json.dumps({'error': str(e)}))
    
    @route('policy_switch', '/stats/flow/', methods=['GET']) 
    def get_flow_statistics(self, req, **kwargs):
        """Get comprehensive flow statistics."""
        try:
            # Check if the PolicySwitch app has the get_flow_statistics method
            if hasattr(self.policy_switch_app, 'get_flow_statistics'):
                flow_stats = self.policy_switch_app.get_flow_statistics()
                safe_flow_stats = safe_json_serialize(flow_stats)
                return Response(content_type='application/json', body=json.dumps(safe_flow_stats))
            else:
                # Fallback to basic flow statistics
                flows = self.policy_switch_app.get_flows()
                flow_count_by_switch = {}
                for flow_key, flow_data in flows.items():
                    dpid = flow_data.get('datapath_id', 'unknown')
                    if dpid not in flow_count_by_switch:
                        flow_count_by_switch[dpid] = 0
                    flow_count_by_switch[dpid] += 1
                
                basic_flow_stats = {
                    'total_flows': len(flows),
                    'flows_by_switch': flow_count_by_switch,
                    'efficiency_score': 75,  # Default efficiency score
                    'utilization': 0.6,  # Default utilization
                    'timestamp': time.time()
                }
                return Response(content_type='application/json', body=json.dumps(basic_flow_stats))
        except Exception as e:
            LOG.error(f"Error getting flow statistics: {e}")
            return Response(status=500, content_type='application/json',
                          body=json.dumps({'error': str(e)}))

    # Policy management endpoints
    @route('policy_switch', '/network/policies', methods=['GET'])
    def get_policies(self, req, **kwargs):
        """Get current policies."""
        policies = self.policy_switch_app.get_policies()
        safe_policies = safe_json_serialize(policies)
        return Response(content_type='application/json', body=json.dumps(safe_policies))
    
    @route('policy_switch', '/network/policies/update', methods=['POST'])
    def update_policies(self, req, **kwargs):
        """Update policies via REST API."""
        try:
            body = req.body.decode('utf-8')
            data = json.loads(body)
            
            # Trigger policy fetch from Policy Engine
            self.policy_switch_app._fetch_and_apply_policies()
            
            return Response(content_type='application/json', 
                          body=json.dumps({'status': 'success', 'message': 'Policies updated'}))
            
        except json.JSONDecodeError as e:
            return Response(status=400, content_type='application/json', 
                          body=json.dumps({'error': f'Invalid JSON: {e}'}))
        except Exception as e:
            return Response(status=500, content_type='application/json', 
                          body=json.dumps({'error': str(e)}))
    
    # Status endpoint
    @route('policy_switch', '/status', methods=['GET'])
    def get_status(self, req, **kwargs):
        """Get controller status."""
        status = {
            'switches_connected': len(self.policy_switch_app.switches),
            'hosts_learned': len(self.policy_switch_app.hosts),
            'links_discovered': len(self.policy_switch_app.links),
            'policies_active': len(self.policy_switch_app.current_policies),
            'policy_engine_available': self.policy_switch_app.policy_engine_available,
            'policy_engine_url': self.policy_switch_app.policy_engine_url,
            'timestamp': time.time()
        }
        return Response(content_type='application/json', body=json.dumps(status))

    @route('policy_switch', '/health', methods=['GET'])
    def get_health(self, req, **kwargs):
        """Health check endpoint for the SDN controller."""
        try:
            health_status = {
                'status': 'healthy',
                'uptime_seconds': time.time() - self.policy_switch_app.start_time,
                'switches': len(self.policy_switch_app.switches),
                'policy_engine_connected': self.policy_switch_app.policy_engine_available,
                'timestamp': time.time()
            }
            
            return Response(content_type='application/json', body=json.dumps(health_status))
        
        except Exception as e:
            error_response = {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
            return Response(status=500, content_type='application/json', 
                          body=json.dumps(error_response))
    # Network status endpoint for debugging
    @route('policy_switch', '/network/status', methods=['GET'])
    def get_network_status_endpoint(self, req, **kwargs):
        """Get network status for debugging."""
        status = self.policy_switch_app.get_network_status()
        return Response(content_type='application/json', body=json.dumps(status))

    # Additional REST endpoints that collector might need    
    @route('policy_switch', '/stats/port/{dpid}', methods=['GET'])
    def get_port_stats(self, req, **kwargs):
        """Get port statistics for a specific switch (collector endpoint)."""
        dpid = kwargs.get('dpid')
        LOG.info(f"Port stats request for DPID: {dpid}")
        
        if not dpid:
            return Response(status=400, content_type='application/json',
                          body=json.dumps({'error': 'DPID is required'}))
        try:
            # Convert dpid string to int - handle both hex string and int formats
            if isinstance(dpid, str):
                # Handle both hex string (00002696755cbe4a) and int string (42427655962186) formats
                try:
                    # Try parsing as hex first - check if it looks like hex
                    clean_dpid = dpid.replace('0x', '').replace(':', '').strip()
                    # Check if all characters are valid hex digits
                    if all(c in '0123456789abcdefABCDEF' for c in clean_dpid):
                        dpid_int = int(clean_dpid, 16)
                    else:
                        # Not valid hex, try as decimal
                        dpid_int = int(dpid)
                except ValueError:
                    # If hex parsing fails, try as decimal integer
                    dpid_int = int(dpid)
            else:
                dpid_int = int(dpid)
            
            LOG.info(f"Converted DPID {dpid} to int: {dpid_int}")
            LOG.info(f"Available switches: {list(self.policy_switch_app.switches.keys())}")
                            
            # Check if we have this switch
            if dpid_int not in self.policy_switch_app.switches:
                return Response(status=404, content_type='application/json', 
                              body=json.dumps({'error': f'Switch {dpid} not found'}))
            
            # Get datapath for this switch
            switch_data = self.policy_switch_app.switches[dpid_int]
            datapath = switch_data.get('datapath')
            
            if not datapath:
                return Response(status=404, content_type='application/json', 
                              body=json.dumps({'error': f'Switch {dpid} datapath not available'}))
            
            LOG.info(f"Switch data keys: {list(switch_data.keys())}")
            
            # Build port statistics from collected data
            port_stats = []
            port_stats_data = switch_data.get('port_stats', {})
            
            LOG.info(f"Port stats data: {port_stats_data}")
            LOG.info(f"Ports data: {switch_data.get('ports', {})}")
            
            for port_no, port_info in switch_data.get('ports', {}).items():
                # Get actual stats if available, otherwise use defaults
                actual_stats = port_stats_data.get(port_no, {})
                
                port_stat = {
                    'port_no': port_no,
                    'rx_packets': actual_stats.get('rx_packets', 0),
                    'tx_packets': actual_stats.get('tx_packets', 0),
                    'rx_bytes': actual_stats.get('rx_bytes', 0),
                    'tx_bytes': actual_stats.get('tx_bytes', 0),
                    'rx_dropped': actual_stats.get('rx_dropped', 0),
                    'tx_dropped': actual_stats.get('tx_dropped', 0),
                    'rx_errors': actual_stats.get('rx_errors', 0),
                    'tx_errors': actual_stats.get('tx_errors', 0),
                    'rx_frame_err': 0,  # Not available in OpenFlow 1.3
                    'rx_over_err': 0,   # Not available in OpenFlow 1.3
                    'rx_crc_err': 0,    # Not available in OpenFlow 1.3
                    'collisions': 0,    # Not available in OpenFlow 1.3
                    'duration_sec': int(time.time() - switch_data.get('connected_time', time.time())),
                    'duration_nsec': 0,
                    # Add bandwidth information for collector
                    'rx_bps': actual_stats.get('rx_bps', 0),
                    'tx_bps': actual_stats.get('tx_bps', 0)
                }
                port_stats.append(port_stat)
              # Return in the format expected by collector
            response_data = {dpid: port_stats}
            safe_response_data = safe_json_serialize(response_data)
            return Response(content_type='application/json', body=json.dumps(safe_response_data))
            
        except (ValueError, TypeError) as e:
            return Response(status=400, content_type='application/json', 
                          body=json.dumps({'error': f'Invalid DPID format: {e}'}))
        except Exception as e:
            LOG.error(f"Error getting port stats for {dpid}: {e}")
            return Response(status=500, content_type='application/json', 
                          body=json.dumps({'error': str(e)}))
    
    @route('policy_switch', '/stats/flowentry/{dpid}', methods=['GET'])
    def get_flow_entry_stats(self, req, **kwargs):
        """Get flow entry statistics for a specific switch (collector endpoint)."""
        dpid = kwargs.get('dpid')        
        if not dpid:
            return Response(status=400, content_type='application/json', 
                          body=json.dumps({'error': 'DPID is required'}))
        
        try:
            # Convert dpid string to int - handle both hex string and int formats
            if isinstance(dpid, str):
                try:
                    # Try parsing as hex first - check if it looks like hex
                    clean_dpid = dpid.replace('0x', '').replace(':', '').strip()
                    # Check if all characters are valid hex digits
                    if all(c in '0123456789abcdefABCDEF' for c in clean_dpid):
                        dpid_int = int(clean_dpid, 16)
                    else:
                        # Not valid hex, try as decimal
                        dpid_int = int(dpid)
                except ValueError:
                    # If hex parsing fails, try as decimal integer
                    dpid_int = int(dpid)            
            else:
                dpid_int = int(dpid)
            
            # Filter flows for this switch
            switch_flows = []
            for flow_key, flow_data in self.policy_switch_app.flows.items():
                if flow_data['datapath_id'] == dpid_int:
                    # Convert flow data to JSON-serializable format
                    serializable_flow = {}
                    for key, value in flow_data.items():
                        if isinstance(value, bytes):
                            serializable_flow[key] = value.hex()
                        elif hasattr(value, 'to_jsondict'):
                            serializable_flow[key] = value.to_jsondict()
                        else:
                            try:
                                json.dumps(value)  # Test if serializable
                                serializable_flow[key] = value
                            except (TypeError, ValueError):
                                serializable_flow[key] = str(value)
                    switch_flows.append(serializable_flow)
              # Return in the format expected by collector
            response_data = {str(dpid_int): switch_flows}
            safe_response_data = safe_json_serialize(response_data)
            return Response(content_type='application/json', body=json.dumps(safe_response_data))
            
        except (ValueError, TypeError) as e:
            return Response(status=400, content_type='application/json', 
                          body=json.dumps({'error': f'Invalid DPID format: {e}'}))
        except Exception as e:
            LOG.error(f"Error getting flow stats for {dpid}: {e}")
            return Response(status=500, content_type='application/json', 
                          body=json.dumps({'error': str(e)}))
    
    @route('policy_switch', '/topology', methods=['GET'])
    def get_topology_summary(self, req, **kwargs):
        """Get overall topology summary (dashboard endpoint)."""
        try:
            topology = {
                'switches': self.policy_switch_app.get_switches(),
                'links': self.policy_switch_app.get_links(),
                'hosts': self.policy_switch_app.get_hosts(),
                'timestamp': time.time(),
                'controller': 'policy_switch'
            }
            safe_topology = safe_json_serialize(topology)
            return Response(content_type='application/json', body=json.dumps(safe_topology, default=str))
        except Exception as e:
            LOG.error(f"Error getting topology summary: {e}")
            return Response(status=500, content_type='application/json', 
                          body=json.dumps({'error': str(e)}))    
    # Comprehensive network status endpoint      
    @route('policy_switch', '/network/full_status', methods=['GET'])
    def get_full_network_status(self, req, **kwargs):
        """Get comprehensive network status with all topology and statistics."""
        try:
            # Get all the network data
            switches = self.policy_switch_app.get_switches()
            links = self.policy_switch_app.get_links()
            hosts = self.policy_switch_app.get_hosts()
            flows = self.policy_switch_app.get_flows()
            policies = self.policy_switch_app.get_policies()
            
            # Debug logging for IPv4 issue
            LOG.info(f"Full status: found {len(hosts)} hosts")
            for i, host in enumerate(hosts):
                LOG.info(f"Host {i}: MAC={host.get('mac')}, IPv4={host.get('ipv4', [])}")
            
            # Convert flows to JSON-serializable format
            serializable_flows = {}
            for flow_key, flow_data in flows.items():
                serializable_flow = {}
                for key, value in flow_data.items():
                    if isinstance(value, bytes):
                        serializable_flow[key] = value.hex()
                    elif hasattr(value, 'to_jsondict'):
                        serializable_flow[key] = value.to_jsondict()
                    else:
                        try:
                            json.dumps(value)  # Test if serializable
                            serializable_flow[key] = value
                        except (TypeError, ValueError):
                            serializable_flow[key] = str(value)
                serializable_flows[flow_key] = serializable_flow
            
            # Add collector-compatible formats
            # Convert links to collector expected format
            collector_links = []
            for link in links:
                collector_links.append({
                    'source': link['src']['dpid'],
                    'target': link['dst']['dpid'],
                    'sport': link['src']['port_no'],
                    'dport': link['dst']['port_no'],
                    'src': link['src'],  # Keep original for compatibility
                    'dst': link['dst']
                })
            
            # Convert switches to collector expected format
            collector_switches = []
            for switch in switches:
                collector_switches.append({
                    'dpid': switch['dpid'],
                    'id': switch['dpid'],
                    'type': 'switch',
                    'ports': switch['ports']
                })
            
            # Convert hosts to collector expected format
            collector_hosts = []
            for host in hosts:
                collector_hosts.append({
                    'id': host['mac'],
                    'mac': host['mac'],
                    'dpid': host['port']['dpid'],
                    'port': host['port']['port_no'],
                    'ip': host['ipv4'][0] if host['ipv4'] else 'unknown',
                    'type': 'host'
                })
            
            full_status = {
                'ryu_format': {
                    'switches': switches,
                    'links': links,
                    'hosts': hosts
                },
                'collector_format': {
                    'switches': collector_switches,
                    'links': collector_links,
                    'hosts': collector_hosts
                },
                'statistics': {
                    'flows': serializable_flows,
                    'policies': policies,
                    'network_status': self.policy_switch_app.get_network_status()
                },
                'metadata': {
                    'timestamp': time.time(),
                    'controller_type': 'policy_switch',
                    'api_version': 'v1.0.0',
                    'policy_engine_available': self.policy_switch_app.policy_engine_available,
                    'policy_engine_url': self.policy_switch_app.policy_engine_url                }
            }

            safe_full_status = safe_json_serialize(full_status)
            return Response(content_type='application/json', body=json.dumps(safe_full_status, default=str))
            
        except Exception as e:
            LOG.error(f"Error getting full network status: {e}")
            return Response(status=500, content_type='application/json', 
                          body=json.dumps({'error': str(e)}))
    
    # Debug endpoints for troubleshooting    @route('policy_switch', '/debug/topology_raw', methods=['GET'])
    def get_raw_topology_data(self, req, **kwargs):
        """Get raw topology data for debugging."""
        debug_data = {
            'switches_raw': dict(self.policy_switch_app.switches),
            'links_raw': [str(link) for link in self.policy_switch_app.links],
            'hosts_raw': dict(self.policy_switch_app.hosts),
            'flows_raw': dict(self.policy_switch_app.flows),
            'dpset_switches': [str(dp) for dp in self.policy_switch_app.dpset.dps.keys()],
            'topology_discovery_method': 'ryu.topology.api',
            'timestamp': time.time()
        }
        
        # Also try to get Ryu topology API data for comparison
        try:
            from ryu.topology.api import get_host, get_switch, get_link
            ryu_hosts = get_host(self.policy_switch_app)
            ryu_switches = get_switch(self.policy_switch_app)
            ryu_links = get_link(self.policy_switch_app)
            
            debug_data['ryu_topology_hosts'] = []
            for host in ryu_hosts:
                host_data = {
                    'mac': getattr(host, 'mac', None),
                    'ipv4': getattr(host, 'ipv4', []),
                    'ipv6': getattr(host, 'ipv6', []),
                    'port': {
                        'dpid': getattr(host.port, 'dpid', None),
                        'port_no': getattr(host.port, 'port_no', None)
                    } if hasattr(host, 'port') else None
                }
                debug_data['ryu_topology_hosts'].append(host_data)
        except Exception as e:
            debug_data['ryu_topology_error'] = str(e)
            
        safe_debug_data = safe_json_serialize(debug_data)
        return Response(content_type='application/json', body=json.dumps(safe_debug_data, default=str))
    
    @route('policy_switch', '/debug/topology_status', methods=['GET'])
    def get_topology_status(self, req, **kwargs):
        """Get comprehensive topology status for debugging."""
        status = {
            'timestamp': time.time(),
            'switches': {
                'count': len(self.policy_switch_app.switches),
                'dpids': list(self.policy_switch_app.switches.keys()),
                'dpids_hex': [hex(dpid) for dpid in self.policy_switch_app.switches.keys()]
            },
            'links': {
                'count': len(self.policy_switch_app.links),
                'links': self.policy_switch_app.links
            },
            'hosts': {
                'count': len(self.policy_switch_app.hosts),
                'macs': list(self.policy_switch_app.hosts.keys())
            },
            'topology_apps': [],
            'link_discovery_status': 'unknown'
        }
        
        # Check what topology-related apps are running
        try:
            for app_name, app_instance in self.policy_switch_app._CONTEXTS.items():
                if 'topology' in app_name.lower() or 'discovery' in app_name.lower():
                    status['topology_apps'].append(app_name)
                    
            # Check if we have access to topology apps
            app_manager_instance = self.policy_switch_app
            if hasattr(app_manager_instance, 'topology_api_app'):
                status['has_topology_api'] = True
            else:
                status['has_topology_api'] = False
                
        except Exception as e:
            status['topology_check_error'] = str(e)
            
        # Manual link discovery check
        try:
            from ryu.topology.api import get_link
            manual_links = get_link(self.policy_switch_app)
            status['manual_link_discovery'] = {
                'count': len(manual_links),
                'links': []
            }
            
            for link in manual_links:
                link_info = {
                    'src_dpid': link.src.dpid,
                    'src_port': link.src.port_no,
                    'dst_dpid': link.dst.dpid,
                    'dst_port': link.dst.port_no
                }
                status['manual_link_discovery']['links'].append(link_info)
        except Exception as e:
            status['manual_link_discovery_error'] = str(e)
            
        safe_status = safe_json_serialize(status)
        return Response(content_type='application/json', body=json.dumps(safe_status, default=str))

    @route('policy_switch', '/debug/ryu_topology', methods=['GET'])
    def get_ryu_topology_debug(self, req, **kwargs):
        """Get raw Ryu topology data for debugging link discovery."""
        debug_data = {
            'timestamp': time.time()
        }
        
        try:
            from ryu.topology.api import get_host, get_switch, get_link
            
            # Get raw Ryu data
            ryu_hosts = get_host(self.policy_switch_app)
            ryu_switches = get_switch(self.policy_switch_app) 
            ryu_links = get_link(self.policy_switch_app)
            
            debug_data['ryu_switches_count'] = len(ryu_switches)
            debug_data['ryu_links_count'] = len(ryu_links)
            debug_data['ryu_hosts_count'] = len(ryu_hosts)
            
            # Process switches
            debug_data['ryu_switches'] = []
            for switch in ryu_switches:
                switch_data = {
                    'dpid': switch.dp.id,
                    'dpid_str': hex(switch.dp.id),
                    'ports_count': len(switch.ports)
                }
                debug_data['ryu_switches'].append(switch_data)
            
            # Process links - this is the important part
            debug_data['ryu_links'] = []
            for link in ryu_links:
                link_data = {
                    'src_dpid': link.src.dpid,
                    'src_dpid_str': hex(link.src.dpid),
                    'src_port_no': link.src.port_no,
                    'dst_dpid': link.dst.dpid,
                    'dst_dpid_str': hex(link.dst.dpid),
                    'dst_port_no': link.dst.port_no
                }
                debug_data['ryu_links'].append(link_data)
            
            # Process hosts
            debug_data['ryu_hosts'] = []
            for host in ryu_hosts:
                host_data = {
                    'mac': getattr(host, 'mac', None),
                    'ipv4': getattr(host, 'ipv4', []),
                    'ipv6': getattr(host, 'ipv6', []),
                    'port_dpid': getattr(host.port, 'dpid', None) if hasattr(host, 'port') else None,
                    'port_no': getattr(host.port, 'port_no', None) if hasattr(host, 'port') else None
                }
                debug_data['ryu_hosts'].append(host_data)
                
            # Compare with our internal data
            debug_data['internal_switches_count'] = len(self.policy_switch_app.switches)
            debug_data['internal_links_count'] = len(self.policy_switch_app.links)
            debug_data['internal_hosts_count'] = len(self.policy_switch_app.hosts)
            
            debug_data['internal_links'] = self.policy_switch_app.links
        except Exception as e:
            debug_data['error'] = str(e)
            LOG.error(f"Error in ryu topology debug: {e}")
            safe_debug_data = safe_json_serialize(debug_data)
            return Response(content_type='application/json', body=json.dumps(safe_debug_data, default=str))

    @route('policy_switch', '/debug/force_topology_update', methods=['POST'])
    def force_topology_update(self, req, **kwargs):
        """Force an immediate topology update."""
        try:
            LOG.info("Manual topology update triggered via API")
            self.policy_switch_app._update_topology()
            
            result = {
                'status': 'success',
                'message': 'Topology update triggered',
                'switches_count': len(self.policy_switch_app.switches),
                'links_count': len(self.policy_switch_app.links),
                'hosts_count': len(self.policy_switch_app.hosts),
                'timestamp': time.time()
            }
            
            return Response(content_type='application/json', body=json.dumps(result))
            
        except Exception as e:
            LOG.error(f"Error in manual topology update: {e}")
            return Response(status=500, content_type='application/json',
                          body=json.dumps({'error': str(e)}))

    @route('policy_switch', '/debug/policy_engine', methods=['GET'])
    def get_policy_engine_debug(self, req, **kwargs):
        """Get Policy Engine debug information."""
        debug_data = {
            'policy_engine_url': self.policy_switch_app.policy_engine_url,
            'policy_engine_available': self.policy_switch_app.policy_engine_available,
            'current_policies_count': len(self.policy_switch_app.current_policies),
            'policy_poll_interval': self.policy_switch_app.policy_poll_interval,
            'policies': self.policy_switch_app.current_policies,
            'timestamp': time.time()        }
        safe_debug_data = safe_json_serialize(debug_data)
        return Response(content_type='application/json', body=json.dumps(safe_debug_data))