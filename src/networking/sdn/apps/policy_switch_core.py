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
Core PolicySwitch Module - Main Controller Logic

This module contains the core PolicySwitch implementation split from the large policy_switch.py
to improve maintainability and readability.
"""

import os
import json
import time
import logging
import requests
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
import ipaddress

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, tcp, udp, icmp
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import WSGIApplication, ControllerBase, route, Response
from ryu.lib import dpid as dpid_lib
from ryu.controller.dpset import DPSet
from ryu.lib import hub

from src.networking.sdn.apps.sdn_stats_manager import (
    CumulativeStats,
    PerformanceMetricsCalculator,
    FlowStatisticsCalculator,
    PortStatsProcessor,
    FlowStatsProcessor
)

# Set up logging
LOG = logging.getLogger('ryu.app.policy_switch')


class PolicySwitchCore(app_manager.RyuApp):
    """
    Core Policy-aware switch controller that enforces network security policies.
    
    This Ryu application implements a comprehensive SDN controller that:
    - Integrates with the Policy Engine for policy enforcement
    - Provides network topology discovery and management
    - Implements learning switch functionality with policy awareness
    """
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]    
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'dpset': DPSet
    }

    def __init__(self, *args, **kwargs):
        """Initialize the Policy Switch Controller."""
        super(PolicySwitchCore, self).__init__(*args, **kwargs)
        
        # Get context objects for managing switches
        self.dpset = kwargs['dpset']
        
        # Track start time for uptime calculation
        self.start_time = time.time()
        
        # Network state tracking
        self.switches = {}  # dpid -> switch info
        self.links = []     # list of link objects
        self.hosts = {}     # mac -> (dpid, port, ip) mapping
        self.flows = {}     # flow tracking
          # Policy Engine integration
        policy_engine_host = os.environ.get("POLICY_ENGINE_HOST", "policy-engine")
        policy_engine_port = os.environ.get("POLICY_ENGINE_PORT", "5000")
        self.policy_engine_url = f"http://{policy_engine_host}:{policy_engine_port}"
        self.policy_poll_interval = int(os.environ.get("POLICY_POLL_INTERVAL", "30"))
        self.current_policies = {}
        self.policy_engine_available = False
        
        # Cumulative network statistics (using extracted class)
        self.cumulative_stats = CumulativeStats()
        
        # Statistics processors (using extracted classes)
        self.port_stats_processor = PortStatsProcessor(self.cumulative_stats)
        self.flow_stats_processor = FlowStatsProcessor(self.cumulative_stats)
        self.performance_calculator = PerformanceMetricsCalculator(
            self.cumulative_stats, self.start_time
        )
        self.flow_stats_calculator = FlowStatisticsCalculator()
        
        # Statistics collection frequency (seconds)
        self.stats_request_interval = 2  # More frequent for better charts
        
        # Flow priority values
        self.priority = {
            'default': 0,
            'icmp': 40,
            'drop': 30,
            'allow': 20,
            'learning': 10,
        }
        
        # Start topology discovery
        hub.spawn(self._topology_discovery_loop)
        
        # Start statistics collection
        hub.spawn(self._stats_collection_loop)
        
        LOG.info("Policy Switch Controller initialized")
        LOG.info(f"Policy Engine URL: {self.policy_engine_url}")
        LOG.info(f"Policy poll interval: {self.policy_poll_interval} seconds")
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch features reply to install initial flows."""
        datapath = ev.msg.datapath
        dpid = datapath.id
        
        LOG.info(f"Switch connected: {dpid}")
        
        # Store switch information
        self.switches[dpid] = {
            'datapath': datapath,
            'ports': {},
            'connected_time': time.time()
        }
        
        # Install default flows for basic connectivity
        self._install_default_flows(datapath)
        
        # Apply current policies to this switch
        if self.current_policies:
            self._apply_policies_to_switch(datapath)
    
    def _install_default_flows(self, datapath):
        """Install default flows for basic connectivity."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        LOG.info(f"Installing default flows for switch {dpid}")
        
        # Table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, self.priority['default'], match, actions)
        
        # Allow ICMP for connectivity testing
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=1)
        actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, self.priority['icmp'], match, actions)
        
        # Protect controller traffic
        controller_ip = os.environ.get('NODE_IP_SDN_CONTROLLER')
        if controller_ip:
            # Traffic to controller
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=controller_ip)
            actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath, 1000, match, actions)
            
            # Traffic from controller
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=controller_ip)
            actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath, 1000, match, actions)
    
    def add_flow(self, datapath, priority, match, actions, 
                buffer_id=None, idle_timeout=0, hard_timeout=0, table_id=0):
        """Add a flow entry to a switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        if actions:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        else:
            inst = []  # No actions means drop
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match,
                                  instructions=inst, idle_timeout=idle_timeout,
                                  hard_timeout=hard_timeout, table_id=table_id)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst,
                                  idle_timeout=idle_timeout,
                                  hard_timeout=hard_timeout, table_id=table_id)
        
        datapath.send_msg(mod)
        
        # Store flow information
        flow_key = f"{datapath.id}_{priority}_{hash(str(match))}"
        self.flows[flow_key] = {
            'datapath_id': datapath.id,
            'priority': priority,
            'match': self._serialize_match(match),
            'actions': self._serialize_actions(actions),
            'idle_timeout': idle_timeout,
            'hard_timeout': hard_timeout,
            'timestamp': time.time()
        }
        
        LOG.debug(f"Added flow: priority={priority}, dpid={datapath.id}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Handle packet in events with policy checking."""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        # Important: Don't ignore LLDP packets - let Ryu topology app handle them
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            LOG.debug(f"LLDP packet received on switch {dpid} port {in_port}")
            return  # Let the topology app handle LLDP
            
        # Ignore IPv6 packets for now
        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            return
        
        dst_mac = eth.dst
        src_mac = eth.src
        
        # Get IP information
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        ip_src = ip_pkt.src if ip_pkt else None
        ip_dst = ip_pkt.dst if ip_pkt else None
        
        # Get protocol information
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        
        src_port = None
        dst_port = None
        ip_proto = None
        
        if tcp_pkt:
            src_port = tcp_pkt.src_port
            dst_port = tcp_pkt.dst_port
            ip_proto = 6
        elif udp_pkt:
            src_port = udp_pkt.src_port
            dst_port = udp_pkt.dst_port
            ip_proto = 17
        elif icmp_pkt:
            ip_proto = 1
        elif ip_pkt:
            ip_proto = ip_pkt.proto
        
        # Learn source host
        self._learn_host(dpid, src_mac, in_port, ip_src)
        
        # Check policy for IP traffic
        policy_decision = None
        if ip_src and ip_dst:
            policy_decision = self._check_policy(ip_src, ip_dst, ip_proto, src_port, dst_port)
            
            if policy_decision is False:
                # Policy denies this traffic - drop and install drop flow
                LOG.info(f"POLICY DENY: Dropping {ip_src} -> {ip_dst}")
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_src=ip_src,
                    ipv4_dst=ip_dst
                )
                if ip_proto:
                    match.append_field('ip_proto', ip_proto)
                self.add_flow(datapath, self.priority['drop'], match, [], idle_timeout=30)
                return
        
        # Normal learning switch behavior
        out_port = self._get_out_port(dpid, dst_mac)
        
        # Install flow if destination is known
        if out_port != ofproto.OFPP_FLOOD:
            if ip_src and ip_dst and policy_decision is True:
                # IP-specific flow with policy approval
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_src=ip_src,
                    ipv4_dst=ip_dst
                )
                if ip_proto:
                    match.append_field('ip_proto', ip_proto)
                priority = self.priority['allow']
            else:
                # MAC-based flow for non-IP or no policy decision
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
                priority = self.priority['learning']
            
            actions = [parser.OFPActionOutput(out_port)]
            
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, priority, match, actions, 
                             buffer_id=msg.buffer_id, idle_timeout=300)
                return
            else:
                self.add_flow(datapath, priority, match, actions, idle_timeout=300)
        
        # Send packet out
        actions = [parser.OFPActionOutput(out_port)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
            
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
    
    def _learn_host(self, dpid, mac, port, ip=None):
        """Learn a host's location and IP."""
        if mac in self.hosts:
            old_host = self.hosts[mac]
            # Handle both old tuple format and new dict format for backward compatibility
            if isinstance(old_host, tuple):
                old_dpid, old_port, old_ip = old_host
            else:
                old_dpid = old_host.get('dpid')
                old_port = old_host.get('port')
                old_ip = old_host.get('ip')
                
            if old_dpid != dpid or old_port != port or (ip and old_ip != ip):
                LOG.info(f"Host {mac} moved from {old_dpid}:{old_port} to {dpid}:{port}")
        else:
            LOG.info(f"Learned new host {mac} at {dpid}:{port}" + (f" IP: {ip}" if ip else ""))
        
        # Store in dictionary format for consistency
        self.hosts[mac] = {
            'dpid': dpid,
            'port': port,
            'ip': ip,
            'last_seen': time.time()
        }
    
    def _get_out_port(self, dpid, dst_mac):
        """Get output port for destination MAC."""
        if dst_mac in self.hosts:
            host_data = self.hosts[dst_mac]
            # Handle both old tuple format and new dict format
            if isinstance(host_data, tuple):
                host_dpid, host_port, _ = host_data
            else:
                host_dpid = host_data.get('dpid')
                host_port = host_data.get('port')
                
            if host_dpid == dpid:
                return host_port
        
        return self.switches[dpid]['datapath'].ofproto.OFPP_FLOOD
    
    # Topology event handlers
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """Handle switch entering the topology."""
        switch = ev.switch
        dpid = switch.dp.id
        LOG.info(f"Switch {dpid} entered topology")
        self._update_topology()
    
    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        """Handle switch leaving the topology."""
        switch = ev.switch
        dpid = switch.dp.id
        LOG.info(f"Switch {dpid} left topology")
        if dpid in self.switches:
            del self.switches[dpid]
        self._update_topology()
    
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """Handle link addition."""
        link = ev.link
        LOG.info(f"Link added: {link.src.dpid}:{link.src.port_no} -> {link.dst.dpid}:{link.dst.port_no}")
        self._update_topology()
    
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        """Handle link deletion."""
        link = ev.link
        LOG.info(f"Link deleted: {link.src.dpid}:{link.src.port_no} -> {link.dst.dpid}:{link.dst.port_no}")
        self._update_topology()
    
    def _topology_discovery_loop(self):
        """Periodically update topology information."""
        LOG.info("Starting topology discovery loop")
        while True:
            hub.sleep(10)  # Update every 10 seconds
            try:
                LOG.debug("Running periodic topology update")
                self._update_topology()
            except Exception as e:
                LOG.error(f"Error in topology discovery: {e}")
    
    def _update_topology(self):
        """Update internal topology representation."""
        try:
            # Get current topology from Ryu
            switch_list = get_switch(self)
            link_list = get_link(self)
            
            LOG.info(f"Topology discovery: {len(switch_list)} switches, {len(link_list)} links found")
            
            # Log raw link data for debugging
            for i, link in enumerate(link_list):
                LOG.info(f"Raw link {i}: src={link.src.dpid}:{link.src.port_no} -> dst={link.dst.dpid}:{link.dst.port_no}")
            
            LOG.debug(f"Raw topology data: {len(switch_list)} switches, {len(link_list)} links")
            
            # Update switches info
            current_switches = {}
            for switch in switch_list:
                dpid = switch.dp.id
                ports = {}
                for port in switch.ports:
                    # Port object attributes in Ryu topology API
                    port_info = {
                        'port_no': port.port_no,
                        'hw_addr': port.hw_addr,
                        'name': getattr(port, 'name', ''),
                    }
                    # Add state information if available
                    if hasattr(port, 'state'):
                        port_info['state'] = port.state
                    elif hasattr(port, 'config'):
                        port_info['config'] = port.config
                    
                    ports[port.port_no] = port_info
                
                current_switches[dpid] = {
                    'dpid': dpid,
                    'ports': ports
                }
                
                # Keep datapath if we have it
                if dpid in self.switches and 'datapath' in self.switches[dpid]:
                    current_switches[dpid]['datapath'] = self.switches[dpid]['datapath']
                    current_switches[dpid]['connected_time'] = self.switches[dpid].get('connected_time', time.time())
            
            # Update internal switches dict
            self.switches.update(current_switches)
            
            # Update links
            self.links = []
            for link in link_list:
                link_data = {
                    'src': {
                        'dpid': link.src.dpid,
                        'port_no': link.src.port_no
                    },
                    'dst': {
                        'dpid': link.dst.dpid,
                        'port_no': link.dst.port_no
                    }
                }
                self.links.append(link_data)
                LOG.debug(f"Found link: {link.src.dpid}:{link.src.port_no} -> {link.dst.dpid}:{link.dst.port_no}")
            
            LOG.debug(f"Topology updated: {len(current_switches)} switches, {len(self.links)} links")
        
        except Exception as e:
            LOG.error(f"Failed to update topology: {e}")
    
    def _request_stats(self):
        """Request statistics from all switches."""
        try:
            for dpid, switch_info in self.switches.items():
                datapath = switch_info.get('datapath')
                if datapath:
                    self._request_port_stats(datapath)
                    self._request_flow_stats(datapath)
        except Exception as e:
            LOG.error(f"Error requesting stats: {e}")
    
    def _request_port_stats(self, datapath):
        """Request port statistics from a switch."""
        try:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
            datapath.send_msg(req)
        except Exception as e:
            LOG.error(f"Error requesting port stats: {e}")
    
    def _request_flow_stats(self, datapath):
        """Request flow statistics from a switch."""
        try:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            req = parser.OFPFlowStatsRequest(datapath)
            datapath.send_msg(req)
        except Exception as e:
            LOG.error(f"Error requesting flow stats: {e}")
    
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        """Handle port statistics reply with enhanced bandwidth calculation."""
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        if dpid not in self.switches:
            return
        
        # Delegate to port stats processor
        self.port_stats_processor.process(body, dpid, self.switches)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        """Handle flow statistics reply with cumulative tracking."""
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        # Delegate to flow stats processor
        self.flow_stats_processor.process(
            body, dpid, self.flows,
            self._serialize_match, self._serialize_actions
        )

    # Utility methods for serialization
    def _serialize_match(self, match):
        """Convert OFPMatch to serializable format."""
        try:
            if hasattr(match, 'to_jsondict'):
                return match.to_jsondict()
            else:
                # Fallback for older versions
                return str(match)        
        except Exception:
            return {}

    def _serialize_actions(self, actions_or_instructions):
        """Convert actions or instructions to serializable format."""
        try:
            serialized = []
            
            # Handle both raw actions and OpenFlow 1.3 instructions
            for item in actions_or_instructions:
                # Check if this is an instruction (OpenFlow 1.3)
                if hasattr(item, 'type') and hasattr(item, 'actions'):
                    # This is an OFPInstructionActions - extract the actions
                    for action in item.actions:
                        serialized.append(self._serialize_single_action(action))
                else:
                    # This is a direct action
                    serialized.append(self._serialize_single_action(item))
            
            return serialized
        except Exception as e:
            LOG.warning(f"Error serializing actions: {e}")
            return []
    
    def _serialize_single_action(self, action):
        """Serialize a single OpenFlow action."""
        try:
            if hasattr(action, 'to_jsondict'):
                action_dict = action.to_jsondict()
                
                # Enhance the serialization with more readable information
                action_class = action.__class__.__name__
                
                if action_class == 'OFPActionOutput':
                    return {
                        'type': 'OUTPUT',
                        'port': getattr(action, 'port', None),
                        'max_len': getattr(action, 'max_len', None),
                        'description': f"Output to port {getattr(action, 'port', 'unknown')}"
                    }
                elif action_class == 'OFPActionSetField':
                    field_name = getattr(action.field, 'name', 'unknown_field') if hasattr(action, 'field') else 'unknown_field'
                    field_value = getattr(action.field, 'value', 'unknown_value') if hasattr(action, 'field') else 'unknown_value'
                    return {
                        'type': 'SET_FIELD',
                        'field': field_name,
                        'value': field_value,
                        'description': f"Set {field_name} to {field_value}"
                    }
                elif action_class == 'OFPActionSetQueue':
                    return {
                        'type': 'SET_QUEUE',
                        'queue_id': getattr(action, 'queue_id', None),
                        'description': f"Set queue {getattr(action, 'queue_id', 'unknown')}"
                    }
                elif action_class == 'OFPActionGroup':
                    return {
                        'type': 'GROUP',
                        'group_id': getattr(action, 'group_id', None),
                        'description': f"Execute group {getattr(action, 'group_id', 'unknown')}"
                    }
                elif action_class == 'OFPActionPushVlan':
                    return {
                        'type': 'PUSH_VLAN',
                        'ethertype': getattr(action, 'ethertype', None),
                        'description': f"Push VLAN tag"
                    }
                elif action_class == 'OFPActionPopVlan':
                    return {
                        'type': 'POP_VLAN',
                        'description': "Pop VLAN tag"
                    }
                else:
                    # Generic fallback
                    return {
                        'type': action_class.replace('OFPAction', '').upper(),
                        'description': f"Action: {action_class}",
                        'raw': action_dict
                    }
            else:
                # Fallback for actions without to_jsondict
                action_class = action.__class__.__name__
                return {
                    'type': action_class.replace('OFPAction', '').upper(),
                    'port': getattr(action, 'port', None),
                    'description': f"Action: {action_class}"
                }
        except Exception as e:
            LOG.warning(f"Error serializing single action: {e}")
            return {
                'type': 'UNKNOWN',
                'description': 'Unknown action',
                'error': str(e)
            }
    
    # Data access methods
    def get_switches(self):
        """Get switches in topology format."""
        switches = []
        for dpid, switch_data in self.switches.items():
            switch_info = {
                'dpid': dpid_lib.dpid_to_str(dpid),
                'ports': list(switch_data.get('ports', {}).values())
            }
            switches.append(switch_info)
        return switches
    
    def get_links(self):
        """Get links in topology format."""
        LOG.info(f"get_links() called: returning {len(self.links)} links")
        for i, link in enumerate(self.links):
            LOG.info(f"Link {i}: {link}")
        return self.links
    
    def get_hosts(self):
        """Get learned hosts with IP addresses."""
        hosts = []
        
        # Try to get hosts from Ryu topology API first for IP discovery
        try:
            from ryu.topology.api import get_host
            ryu_hosts = get_host(self)
            
            # Create a mapping of MAC to IP from Ryu topology data
            mac_to_ips = {}
            for host in ryu_hosts:
                if hasattr(host, 'mac') and hasattr(host, 'ipv4'):
                    mac_to_ips[host.mac] = list(host.ipv4) if host.ipv4 else []
        except Exception as e:
            LOG.debug(f"Could not get Ryu topology hosts: {e}")
            mac_to_ips = {}
        
        # Build host list from our learned hosts
        for mac, host_data in self.hosts.items():
            # Handle both old (tuple) and new (dict) format
            if isinstance(host_data, tuple):
                dpid, port, learned_ip = host_data
            else:
                dpid = host_data.get('dpid')
                port = host_data.get('port')
                learned_ip = host_data.get('ip')
            
            # Use learned IP if available, otherwise try Ryu topology IP
            ipv4_list = []
            if learned_ip:
                ipv4_list = [learned_ip]
            elif mac in mac_to_ips:
                ipv4_list = mac_to_ips[mac]
            
            host_info = {
                'mac': mac,
                'ipv4': ipv4_list,
                'port': {
                    'dpid': dpid_lib.dpid_to_str(dpid),
                    'port_no': port
                }
            }
            hosts.append(host_info)
        
        return hosts
    
    def get_flows(self):
        """Get current flows."""
        return self.flows
    
    def get_policies(self):
        """Get current policies."""
        return self.current_policies
    
    def get_network_status(self):
        """Get comprehensive network status."""
        switches_list = list(self.switches.keys())
        return {
            'switches_count': len(self.switches),
            'switches': switches_list,
            'links_count': len(self.links),
            'hosts_count': len(self.hosts),
            'flows_count': len(self.flows),
            'policies_count': len(self.current_policies),
            'policy_engine_available': self.policy_engine_available,
            'policy_engine_url': self.policy_engine_url,
            'timestamp': time.time()
        }

    def get_performance_metrics(self):
        """Get real-time performance metrics with smart aggregation and total statistics."""
        return self.performance_calculator.calculate(self.switches, self.flows)

    def get_flow_statistics(self):
        """Get comprehensive flow statistics with efficiency calculations."""
        return self.flow_stats_calculator.calculate(self.flows, self.switches)
        
    def _stats_collection_loop(self):
        """Periodically collect statistics from switches with frequent updates for charts."""
        while True:
            try:
                # Use the configured interval (2 seconds for better chart data)
                hub.sleep(self.stats_request_interval)
                self._request_stats()
            except Exception as e:
                LOG.error(f"Error in stats collection loop: {e}")
                # Wait longer on error to avoid spam
                hub.sleep(max(self.stats_request_interval * 3, 10))
    
    def _request_stats(self):
        """Request statistics from all connected switches."""
        for dpid, switch_data in self.switches.items():
            datapath = switch_data.get('datapath')
            if datapath:
                self._request_port_stats(datapath)
                self._request_flow_stats(datapath)
    
    def _request_port_stats(self, datapath):
        """Request port statistics from a switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)
    
    def _request_flow_stats(self, datapath):
        """Request flow statistics from a switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
    
    # Utility methods for DPID conversion and data consistency
    @staticmethod
    def dpid_to_int(dpid):
        """Convert DPID from various formats to integer."""
        if isinstance(dpid, int):
            return dpid
        elif isinstance(dpid, str):
            try:
                # Remove any 0x prefix and colons, then convert from hex
                clean_dpid = dpid.replace('0x', '').replace(':', '')
                return int(clean_dpid, 16)
            except ValueError:
                # If hex conversion fails, try decimal
                return int(dpid)
        else:
            return int(dpid)
    
    @staticmethod
    def dpid_to_str(dpid):
        """Convert DPID to standard hex string format."""
        if isinstance(dpid, str):
            return dpid
        return dpid_lib.dpid_to_str(dpid)
