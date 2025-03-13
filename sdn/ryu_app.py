"""
Ryu SDN Controller Application for Federated Learning

This module provides a Ryu SDN controller application with advanced features
for optimizing network conditions for Federated Learning, including:
- Dynamic traffic prioritization
- Bandwidth allocation
- Latency optimization
- QoS for FL traffic
"""

import json
import logging
import time
from typing import Dict, List, Set, Tuple, Optional

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, tcp, udp
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import WSGIApplication, ControllerBase, route

import networkx as nx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FLNetworkMonitor(app_manager.RyuApp):
    """
    Ryu application for Federated Learning network optimization.
    """
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}
    
    def __init__(self, *args, **kwargs):
        super(FLNetworkMonitor, self).__init__(*args, **kwargs)
        self.name = "fl_network_monitor"
        self.topology_api_app = self
        
        # Initialize network graph
        self.network = nx.DiGraph()
        
        # Track switches and hosts
        self.switches = {}  # dpid -> switch data
        self.hosts = {}  # mac -> host data
        self.host_ip_to_mac = {}  # ip -> mac
        
        # Track FL-related traffic
        self.fl_server_ips = set()  # Set of FL server IPs
        self.fl_client_ips = set()  # Set of FL client IPs
        
        # Flow tables
        self.fl_priority_flows = {}  # dpid -> list of FL prioritization flows
        self.qos_flows = {}  # dpid -> list of QoS flows
        
        # Performance metrics
        self.latency_stats = {}  # (src_ip, dst_ip) -> latency in ms
        self.bandwidth_usage = {}  # (src_ip, dst_ip) -> bandwidth in bps
        
        # REST API
        wsgi = kwargs['wsgi']
        wsgi.register(FLNetworkControllerAPI, {'fl_app': self})
        
        # Interval for periodic updates (in seconds)
        self.update_interval = 10
        self.monitor_thread = self.hub.spawn(self._monitor)
    
    def _monitor(self):
        """Periodic monitoring of network conditions."""
        while True:
            # Update latency measurements
            self._measure_latencies()
            
            # Update bandwidth usage
            self._measure_bandwidth()
            
            # Adjust flows based on current conditions
            self._optimize_network()
            
            # Wait for next monitoring cycle
            self.hub.sleep(self.update_interval)
    
    def _measure_latencies(self):
        """Measure latencies between FL nodes."""
        # In a real implementation, this would send probes or use OpenFlow stats
        # Here we just simulate with random values for demonstration
        import random
        
        for server_ip in self.fl_server_ips:
            for client_ip in self.fl_client_ips:
                # Simulated latency between 5-100ms
                latency = random.uniform(5, 100)
                self.latency_stats[(client_ip, server_ip)] = latency
    
    def _measure_bandwidth(self):
        """Measure bandwidth usage between FL nodes."""
        # In a real implementation, this would use OpenFlow stats
        # Here we simulate for demonstration
        import random
        
        for server_ip in self.fl_server_ips:
            for client_ip in self.fl_client_ips:
                # Simulated bandwidth between 1-100 Mbps
                bandwidth = random.uniform(1, 100) * 1000000  # Convert to bps
                self.bandwidth_usage[(client_ip, server_ip)] = bandwidth
    
    def _optimize_network(self):
        """Apply optimizations based on current network conditions."""
        # Check for high-latency links
        for (src_ip, dst_ip), latency in self.latency_stats.items():
            if latency > 50:  # If latency > 50ms
                # Find a better path
                self._find_better_path(src_ip, dst_ip)
        
        # Check for congested links
        for (src_ip, dst_ip), bandwidth in self.bandwidth_usage.items():
            if bandwidth > 80000000:  # If bandwidth > 80 Mbps
                # Apply QoS to prioritize FL traffic
                self._apply_qos(src_ip, dst_ip)
    
    def _find_better_path(self, src_ip, dst_ip):
        """Find and install a better path between two hosts."""
        # In a real implementation, this would compute paths using NetworkX
        # and install appropriate flows
        logger.info(f"Finding better path between {src_ip} and {dst_ip}")
        
        # Get MAC addresses
        if src_ip not in self.host_ip_to_mac or dst_ip not in self.host_ip_to_mac:
            logger.warning(f"MAC address not found for {src_ip} or {dst_ip}")
            return
        
        src_mac = self.host_ip_to_mac[src_ip]
        dst_mac = self.host_ip_to_mac[dst_ip]
        
        # Get host locations
        if src_mac not in self.hosts or dst_mac not in self.hosts:
            logger.warning(f"Host not found for {src_mac} or {dst_mac}")
            return
        
        src_dpid = self.hosts[src_mac]["dpid"]
        dst_dpid = self.hosts[dst_mac]["dpid"]
        
        # Find shortest path using NetworkX
        try:
            path = nx.shortest_path(self.network, src_dpid, dst_dpid, weight="latency")
            logger.info(f"Found path: {path}")
            
            # Install flows along the path
            self._install_path_flows(path, src_ip, dst_ip, src_mac, dst_mac)
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            logger.error(f"Cannot find path: {e}")
    
    def _install_path_flows(self, path, src_ip, dst_ip, src_mac, dst_mac):
        """Install flows along a path."""
        logger.info(f"Installing flows for path: {path}")
        
        # For each switch in the path
        for i in range(len(path) - 1):
            # Get current and next switch
            dpid = path[i]
            next_dpid = path[i + 1]
            
            # Get output port to next switch
            out_port = None
            for src, dst, data in self.network.edges(data=True):
                if src == dpid and dst == next_dpid:
                    out_port = data["port"]
                    break
            
            if out_port is None:
                logger.error(f"Output port not found from {dpid} to {next_dpid}")
                continue
            
            # Install flow
            if dpid in self.switches:
                datapath = self.switches[dpid]["datapath"]
                self._add_flow(
                    datapath,
                    priority=100,
                    match_fields={
                        "eth_type": ether_types.ETH_TYPE_IP,
                        "ipv4_src": src_ip,
                        "ipv4_dst": dst_ip
                    },
                    actions=[datapath.ofproto_parser.OFPActionOutput(out_port)],
                    idle_timeout=300  # 5 minutes
                )
    
    def _apply_qos(self, src_ip, dst_ip):
        """Apply QoS to prioritize FL traffic."""
        logger.info(f"Applying QoS for traffic between {src_ip} and {dst_ip}")
        
        # In a real implementation, this would install meters for rate limiting
        # and queue configuration for traffic prioritization
        
        # Get MAC addresses
        if src_ip not in self.host_ip_to_mac or dst_ip not in self.host_ip_to_mac:
            logger.warning(f"MAC address not found for {src_ip} or {dst_ip}")
            return
        
        src_mac = self.host_ip_to_mac[src_ip]
        dst_mac = self.host_ip_to_mac[dst_ip]
        
        # Get host locations
        if src_mac not in self.hosts or dst_mac not in self.hosts:
            logger.warning(f"Host not found for {src_mac} or {dst_mac}")
            return
        
        src_dpid = self.hosts[src_mac]["dpid"]
        
        # Apply QoS on the source switch
        if src_dpid in self.switches:
            datapath = self.switches[src_dpid]["datapath"]
            self._add_qos_flow(datapath, src_ip, dst_ip)
    
    def _add_qos_flow(self, datapath, src_ip, dst_ip):
        """Add a QoS flow to prioritize FL traffic."""
        # In a real implementation, this would configure meters and queues
        # Here we just set a high priority for FL traffic
        
        # Match TCP traffic on port 8080 (example FL server port)
        self._add_flow(
            datapath,
            priority=200,  # Higher priority
            match_fields={
                "eth_type": ether_types.ETH_TYPE_IP,
                "ip_proto": 6,  # TCP
                "ipv4_src": src_ip,
                "ipv4_dst": dst_ip,
                "tcp_dst": 8080
            },
            actions=[
                # Set DSCP to Expedited Forwarding (46)
                datapath.ofproto_parser.OFPActionSetField(ip_dscp=46),
                # Output to normal processing
                datapath.ofproto_parser.OFPActionOutput(datapath.ofproto.OFPP_NORMAL)
            ],
            idle_timeout=600  # 10 minutes
        )
        
        # Store the flow for tracking
        if datapath.id not in self.qos_flows:
            self.qos_flows[datapath.id] = []
        
        self.qos_flows[datapath.id].append((src_ip, dst_ip))
        logger.info(f"QoS flow added for {src_ip} -> {dst_ip} on switch {datapath.id}")
    
    def _add_flow(self, datapath, priority, match_fields, actions, idle_timeout=0, hard_timeout=0):
        """Add a flow entry to a switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Create match
        match = parser.OFPMatch(**match_fields)
        
        # Create instruction
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        # Create and send flow mod message
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        )
        datapath.send_msg(mod)
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection and install table-miss flow entry."""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Install table-miss flow entry (lowest priority)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, 0, match_fields={}, actions=actions)
        
        # Store switch info
        self.switches[datapath.id] = {
            "datapath": datapath,
            "ports": {}
        }
        
        logger.info(f"Switch connected: {datapath.id}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet-in events to learn hosts and track FL traffic."""
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        in_port = msg.match['in_port']
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        # Ignore LLDP packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        # Learn host location
        src_mac = eth.src
        self.hosts[src_mac] = {
            "dpid": dpid,
            "port": in_port,
            "last_seen": time.time()
        }
        
        # Track IP addresses
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            
            # Map IP to MAC
            self.host_ip_to_mac[src_ip] = src_mac
            
            # Check if this is FL traffic
            tcp_pkt = pkt.get_protocol(tcp.tcp)
            if tcp_pkt:
                # Example: Identify FL server by port 8080
                if tcp_pkt.dst_port == 8080:
                    self.fl_server_ips.add(dst_ip)
                    self.fl_client_ips.add(src_ip)
                    logger.info(f"Detected FL traffic: {src_ip} -> {dst_ip}")
        
        # Forward the packet if needed
        self._handle_packet(msg, eth, ip_pkt)
    
    def _handle_packet(self, msg, eth, ip_pkt):
        """Handle packet forwarding based on learned information."""
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        
        dst_mac = eth.dst
        
        # If destination is known, forward to the right port
        if dst_mac in self.hosts and self.hosts[dst_mac]["dpid"] == datapath.id:
            out_port = self.hosts[dst_mac]["port"]
            
            # Send packet out
            actions = [parser.OFPActionOutput(out_port)]
            data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
            
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=data
            )
            datapath.send_msg(out)
            
            # Install a flow for subsequent packets
            if ip_pkt:
                self._add_flow(
                    datapath,
                    priority=10,
                    match_fields={
                        "eth_type": ether_types.ETH_TYPE_IP,
                        "ipv4_src": ip_pkt.src,
                        "ipv4_dst": ip_pkt.dst
                    },
                    actions=actions,
                    idle_timeout=60  # 1 minute
                )
        else:
            # Flood if destination unknown
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
            
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=data
            )
            datapath.send_msg(out)
    
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        """Handle switch addition to update topology."""
        switch = ev.switch
        dpid = switch.dp.id
        
        # Update topology
        self._update_topology()
        
        logger.info(f"Switch added to topology: {dpid}")
    
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        """Handle link addition to update topology."""
        link = ev.link
        
        # Update topology
        self._update_topology()
        
        logger.info(f"Link added: {link.src.dpid} -> {link.dst.dpid}")
    
    def _update_topology(self):
        """Update network topology graph."""
        # Clear current graph
        self.network.clear()
        
        # Add switches as nodes
        switch_list = get_switch(self.topology_api_app, None)
        for switch in switch_list:
            dpid = switch.dp.id
            self.network.add_node(dpid)
        
        # Add links as edges
        link_list = get_link(self.topology_api_app, None)
        for link in link_list:
            src_dpid = link.src.dpid
            dst_dpid = link.dst.dpid
            src_port = link.src.port_no
            dst_port = link.dst.port_no
            
            # Add edge with port and default latency
            self.network.add_edge(
                src_dpid,
                dst_dpid,
                port=src_port,
                latency=10  # Default latency in ms
            )
            
            # Track port information
            if src_dpid in self.switches:
                self.switches[src_dpid]["ports"][src_port] = {"peer_dpid": dst_dpid, "peer_port": dst_port}
        
        logger.info(f"Topology updated: {len(self.network.nodes)} switches, {len(self.network.edges)} links")
    
    def register_fl_server(self, server_ip):
        """Register an FL server IP address for tracking."""
        self.fl_server_ips.add(server_ip)
        logger.info(f"Registered FL server: {server_ip}")
        return {"status": "success", "message": f"FL server {server_ip} registered"}
    
    def register_fl_client(self, client_ip):
        """Register an FL client IP address for tracking."""
        self.fl_client_ips.add(client_ip)
        logger.info(f"Registered FL client: {client_ip}")
        return {"status": "success", "message": f"FL client {client_ip} registered"}
    
    def prioritize_traffic(self, src_ip, dst_ip, priority=200, duration=600):
        """Prioritize traffic between two IP addresses."""
        logger.info(f"Prioritizing traffic from {src_ip} to {dst_ip}")
        
        # Find the switch connected to the source
        src_mac = self.host_ip_to_mac.get(src_ip)
        if not src_mac or src_mac not in self.hosts:
            return {"status": "error", "message": f"Source {src_ip} not found in network"}
        
        src_dpid = self.hosts[src_mac]["dpid"]
        
        # Apply high-priority flow
        if src_dpid in self.switches:
            datapath = self.switches[src_dpid]["datapath"]
            self._add_flow(
                datapath,
                priority=priority,
                match_fields={
                    "eth_type": ether_types.ETH_TYPE_IP,
                    "ipv4_src": src_ip,
                    "ipv4_dst": dst_ip
                },
                actions=[
                    # Set DSCP to Expedited Forwarding (46)
                    datapath.ofproto_parser.OFPActionSetField(ip_dscp=46),
                    # Output to normal processing
                    datapath.ofproto_parser.OFPActionOutput(datapath.ofproto.OFPP_NORMAL)
                ],
                idle_timeout=duration
            )
            
            # Track the prioritized flow
            if src_dpid not in self.fl_priority_flows:
                self.fl_priority_flows[src_dpid] = []
            
            self.fl_priority_flows[src_dpid].append((src_ip, dst_ip))
            
            return {
                "status": "success",
                "message": f"Traffic from {src_ip} to {dst_ip} prioritized for {duration} seconds"
            }
        else:
            return {"status": "error", "message": f"Switch for {src_ip} not found"}
    
    def get_network_stats(self):
        """Get current network statistics."""
        return {
            "switches": len(self.switches),
            "hosts": len(self.hosts),
            "fl_servers": len(self.fl_server_ips),
            "fl_clients": len(self.fl_client_ips),
            "latency_stats": self.latency_stats,
            "bandwidth_usage": self.bandwidth_usage,
            "prioritized_flows": sum(len(flows) for flows in self.fl_priority_flows.values()),
            "qos_flows": sum(len(flows) for flows in self.qos_flows.values())
        }


# REST API for the Ryu application
class FLNetworkControllerAPI(ControllerBase):
    """REST API for FL Network Controller."""
    
    def __init__(self, req, link, data, **config):
        super(FLNetworkControllerAPI, self).__init__(req, link, data, **config)
        self.fl_app = data['fl_app']
    
    @route('fl', '/fl/register/server', methods=['POST'])
    def register_fl_server(self, req, **kwargs):
        """Register an FL server IP address."""
        try:
            data = json.loads(req.body)
            server_ip = data.get('server_ip')
            
            if not server_ip:
                return json.dumps({"status": "error", "message": "server_ip is required"})
            
            result = self.fl_app.register_fl_server(server_ip)
            return json.dumps(result)
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @route('fl', '/fl/register/client', methods=['POST'])
    def register_fl_client(self, req, **kwargs):
        """Register an FL client IP address."""
        try:
            data = json.loads(req.body)
            client_ip = data.get('client_ip')
            
            if not client_ip:
                return json.dumps({"status": "error", "message": "client_ip is required"})
            
            result = self.fl_app.register_fl_client(client_ip)
            return json.dumps(result)
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @route('fl', '/fl/prioritize', methods=['POST'])
    def prioritize_traffic(self, req, **kwargs):
        """Prioritize traffic between two IP addresses."""
        try:
            data = json.loads(req.body)
            src_ip = data.get('src_ip')
            dst_ip = data.get('dst_ip')
            priority = data.get('priority', 200)
            duration = data.get('duration', 600)
            
            if not src_ip or not dst_ip:
                return json.dumps({"status": "error", "message": "src_ip and dst_ip are required"})
            
            result = self.fl_app.prioritize_traffic(src_ip, dst_ip, priority, duration)
            return json.dumps(result)
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @route('fl', '/fl/stats', methods=['GET'])
    def get_network_stats(self, req, **kwargs):
        """Get current network statistics."""
        try:
            stats = self.fl_app.get_network_stats()
            return json.dumps(stats)
        
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}) 