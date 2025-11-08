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
Policy Engine Integration Module

This module handles communication with the Policy Engine and policy enforcement
for the PolicySwitch controller.
"""

import time
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union

LOG = logging.getLogger('ryu.app.policy_switch.policy')


class PolicyEngineMixin:
    """Mixin class that provides Policy Engine integration functionality."""
    
    def _check_policy(self, src_ip, dst_ip, ip_proto=None, src_port=None, dst_port=None):
        """Check if traffic is allowed by current policies."""
        if not self.current_policies:
            return True  # Default allow if no policies
        
        LOG.debug(f"Checking policies for {src_ip} -> {dst_ip}")
        
        # Check each policy
        for policy_id, policy in self.current_policies.items():
            rules = policy.get('rules', policy.get('conditions', []))
            for rule in rules:
                if self._condition_matches(rule, src_ip, dst_ip, ip_proto, src_port, dst_port):
                    action = rule.get('action', 'allow')
                    LOG.debug(f"Policy {policy_id} rule matched: {action}")
                    
                    if action == 'deny':
                        return False
                    elif action == 'allow':
                        return True
                    # Continue checking other rules for deny/allow decisions
        
        return True  # Default allow if no matching policies
    
    def _condition_matches(self, condition, src_ip, dst_ip, ip_proto=None, src_port=None, dst_port=None):
        """Check if a condition matches the traffic parameters."""
        # Handle different condition formats
        if 'field' in condition:
            # Field-based condition format
            field = condition['field']
            value = condition['value']
            
            if field == 'src_ip' and src_ip:
                return self._ip_matches(src_ip, value)
            elif field == 'dst_ip' and dst_ip:
                return self._ip_matches(dst_ip, value)
            elif field == 'protocol' and ip_proto is not None:
                return self._protocol_matches(ip_proto, value)
            elif field == 'src_port' and src_port is not None:
                return self._port_matches(src_port, value)
            elif field == 'dst_port' and dst_port is not None:
                return self._port_matches(dst_port, value)
        
        elif 'match' in condition:
            # Match-based condition format
            match = condition['match']
            
            # Check source IP
            if 'src_ip' in match or 'ipv4_src' in match:
                rule_src = match.get('src_ip', match.get('ipv4_src'))
                if not self._ip_matches(src_ip, rule_src):
                    return False
            
            # Check destination IP
            if 'dst_ip' in match or 'ipv4_dst' in match:
                rule_dst = match.get('dst_ip', match.get('ipv4_dst'))
                if not self._ip_matches(dst_ip, rule_dst):
                    return False
            
            # Check protocol
            if 'protocol' in match or 'ip_proto' in match:
                rule_proto = match.get('protocol', match.get('ip_proto'))
                if not self._protocol_matches(ip_proto, rule_proto):
                    return False
            
            # Check source port
            if 'src_port' in match:
                if not self._port_matches(src_port, match['src_port']):
                    return False
            
            # Check destination port
            if 'dst_port' in match:
                if not self._port_matches(dst_port, match['dst_port']):
                    return False
            
            return True  # All checks passed
        
        return False
    
    def _ip_matches(self, ip, rule_ip):
        """Check if an IP address matches a rule (CIDR or exact)."""
        if rule_ip is None or rule_ip.lower() == 'any':
            return True
        if ip is None:
            return False
            
        try:
            # Try CIDR notation first
            import ipaddress
            if '/' in rule_ip:
                network = ipaddress.ip_network(rule_ip, strict=False)
                return ipaddress.ip_address(ip) in network
            else:
                return ip == rule_ip
        except ValueError:
            return ip == rule_ip

    def _port_matches(self, port: int, rule_port: Union[str, int]) -> bool:
        """Check if a port matches a rule (exact, range, or any)."""
        if rule_port == 'any' or rule_port is None:
            return True
        if port is None:
            return False
        
        try:
            if isinstance(rule_port, str):
                if '-' in rule_port:
                    # Port range
                    start, end = map(int, rule_port.split('-'))
                    return start <= port <= end
                elif rule_port.isdigit():
                    return port == int(rule_port)
                else:
                    return False
            else:
                return port == rule_port
        except (ValueError, TypeError) as e:
            LOG.warning(f"Error parsing port rule {rule_port}: {e}")
            return False

    def _protocol_matches(self, ip_proto, rule_proto):
        """Check if protocol matches a rule."""
        if rule_proto is None or str(rule_proto).lower() == 'any':
            return True
        
        if ip_proto is None:
            return False

        proto_map = {'tcp': 6, 'udp': 17, 'icmp': 1}
        
        rule_proto_num = None
        if isinstance(rule_proto, str):
            rule_proto_num = proto_map.get(rule_proto.lower())
            if rule_proto_num is None and rule_proto.isdigit():
                rule_proto_num = int(rule_proto)

        if rule_proto_num is None:
            return False
        
        return ip_proto == rule_proto_num
    def _policy_poll_loop(self):
        """Periodically poll Policy Engine for updates."""
        while True:
            try:
                self._fetch_and_apply_policies()
            except Exception as e:
                LOG.error(f"Error in policy polling loop: {e}")
            
            # Sleep for the configured interval
            time.sleep(self.policy_poll_interval)
    
    def _fetch_and_apply_policies(self):
        """Fetch policies from Policy Engine and apply them."""
        try:
            # Use the correct API endpoint format for the Policy Engine
            response = requests.get(f"{self.policy_engine_url}/api/v1/policies", timeout=10)
            if response.status_code == 200:
                policies_data = response.json()
                
                # Policy Engine returns policies directly or in a wrapper
                if isinstance(policies_data, list):
                    # Direct list of policies
                    new_policies = {p.get('policy_id', p.get('id', str(i))): p for i, p in enumerate(policies_data)}
                elif isinstance(policies_data, dict):
                    if 'policies' in policies_data:
                        # Wrapped in policies key
                        policy_list = policies_data['policies']
                        new_policies = {p.get('policy_id', p.get('id', str(i))): p for i, p in enumerate(policy_list)}
                    else:
                        # Assume it's a single policy or policies dict
                        new_policies = policies_data
                else:
                    new_policies = {}
                
                # Update current policies
                old_count = len(self.current_policies)
                self.current_policies = new_policies
                new_count = len(self.current_policies)
                
                if old_count != new_count:
                    LOG.info(f"Updated policies: {old_count} -> {new_count}")
                    for policy_id, policy in new_policies.items():
                        LOG.debug(f"Policy {policy_id}: {policy.get('name', 'Unknown')} - {policy.get('enabled', False)}")
                
                # Apply policies to all connected switches
                self._apply_policies_to_all_switches()
                
                self.policy_engine_available = True
                
        except requests.exceptions.RequestException as e:
            if self.policy_engine_available:
                LOG.warning(f"Policy Engine unavailable: {e}")
                self.policy_engine_available = False
        except Exception as e:
            LOG.error(f"Error fetching policies: {e}")
            self.policy_engine_available = False
    def _apply_policies_to_all_switches(self):
        """Apply policies to all connected switches."""
        if not self.switches:
            LOG.warning("No switches connected, policies not applied")
            return
        
        LOG.info(f"Applying {len(self.current_policies)} policies to {len(self.switches)} switches")
        for dpid in self.switches:
            self._apply_policies_to_switch(dpid)

    def _apply_policies_to_switch(self, dpid):
        """Apply policies to a specific switch."""
        if dpid not in self.switches:
            LOG.warning(f"Switch {dpid} not found, policies not applied")
            return
        
        datapath = self.switches[dpid]['datapath']
        
        # Clear existing policy flows first
        self._clear_policy_flows(datapath)
        
        # Install new policy flows
        for policy_id, policy in self.current_policies.items():
            if policy.get('enabled', True):
                self._install_policy_flows(datapath, policy)
        
        LOG.info(f"Applied {len(self.current_policies)} policies to switch {dpid}")

    def _clear_policy_flows(self, datapath):
        """Clear existing policy flows from the switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Delete flows with our policy table ID (table 1)
        mod = parser.OFPFlowMod(
            datapath=datapath,
            table_id=1,  # Policy table
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY
        )
        datapath.send_msg(mod)
        
        LOG.debug(f"Cleared policy flows from switch {datapath.id}")

    def _install_policy_flows(self, datapath, policy):
        """Install OpenFlow rules for a policy."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        policy_id = policy.get('policy_id', policy.get('id', 'unknown'))
        policy_name = policy.get('name', 'Unknown Policy')
        
        LOG.debug(f"Installing flows for policy: {policy_name} ({policy_id})")
        
        # Process policy conditions to create match criteria
        conditions = policy.get('conditions', [])
        actions = policy.get('actions', [])
        priority = policy.get('priority', 100)
        
        # Convert conditions to OpenFlow match
        match_fields = {}
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            # Map policy conditions to OpenFlow match fields
            if field == 'src_ip' and operator == '==':
                match_fields['ipv4_src'] = value
            elif field == 'dst_ip' and operator == '==':
                match_fields['ipv4_dst'] = value
            elif field == 'src_port' and operator == '==':
                if isinstance(value, int):
                    match_fields['tcp_src'] = value
            elif field == 'dst_port' and operator == '==':
                if isinstance(value, int):
                    match_fields['tcp_dst'] = value
            elif field == 'protocol' and operator == '==':
                if value.lower() == 'tcp':
                    match_fields['ip_proto'] = 6
                elif value.lower() == 'udp':
                    match_fields['ip_proto'] = 17
            elif field == 'latency' or field == 'bandwidth':
                # These require runtime measurement, skip for static flow rules
                continue
        
        # Create match object
        if match_fields:
            # Ensure ethernet type is set for IP matches
            if any(k.startswith('ipv4_') for k in match_fields):
                match_fields['eth_type'] = 0x0800  # IPv4
            if any(k in ['tcp_src', 'tcp_dst'] for k in match_fields):
                match_fields['ip_proto'] = 6  # TCP
                
            match = parser.OFPMatch(**match_fields)
        else:
            # Default match all if no specific conditions
            match = parser.OFPMatch()
        
        # Process policy actions to create OpenFlow actions
        flow_actions = []
        for action in actions:
            action_type = action.get('type')
            target = action.get('target')
            parameters = action.get('parameters', {})
            
            if action_type == 'sdn':
                if target == 'drop':
                    # Drop action - no output actions
                    flow_actions = []
                    break
                elif target == 'reroute':
                    # Reroute to specific port if specified
                    new_port = parameters.get('port')
                    if new_port:
                        flow_actions.append(parser.OFPActionOutput(new_port))
                    else:
                        # Default to normal processing
                        flow_actions.append(parser.OFPActionOutput(ofproto.OFPP_NORMAL))
                elif target == 'prioritize':
                    # Set DSCP field for QoS prioritization
                    dscp = parameters.get('dscp', 46)  # Default to EF (Expedited Forwarding)
                    flow_actions.append(parser.OFPActionSetField(ip_dscp=dscp))
                    flow_actions.append(parser.OFPActionOutput(ofproto.OFPP_NORMAL))
                elif target == 'mirror':
                    # Mirror traffic to specified port
                    mirror_port = parameters.get('port')
                    if mirror_port:
                        flow_actions.append(parser.OFPActionOutput(mirror_port))
                    flow_actions.append(parser.OFPActionOutput(ofproto.OFPP_NORMAL))
            elif action_type == 'qos':
                # QoS actions
                if target == 'set_priority':
                    priority_val = parameters.get('priority', 0)
                    flow_actions.append(parser.OFPActionSetField(vlan_pcp=priority_val))
                flow_actions.append(parser.OFPActionOutput(ofproto.OFPP_NORMAL))
        
        # Default action if none specified
        if not flow_actions:
            flow_actions.append(parser.OFPActionOutput(ofproto.OFPP_NORMAL))
        
        # Create flow mod instruction
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, flow_actions)]
        
        # Install the flow
        mod = parser.OFPFlowMod(
            datapath=datapath,
            table_id=1,  # Policy table
            priority=priority + 1000,  # Higher priority for policies
            match=match,
            instructions=instructions,
            idle_timeout=300,  # 5 minutes
            hard_timeout=0,    # No hard timeout
            flags=ofproto.OFPFF_SEND_FLOW_REM
        )
        
        datapath.send_msg(mod)
        LOG.debug(f"Installed flow for policy {policy_name} on switch {datapath.id}")

    # ...existing code...
