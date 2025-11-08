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
REST API for the SDN controller to expose policy and switch status.
This module provides REST endpoints to check switch status, 
flow tables, and policy application status.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib.packet import packet, ethernet, ipv4

# Local imports
from src.networking.sdn.check_switches import get_switches, check_policy_application

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("sdn_rest_api")

# URL paths for the REST API
REST_SWITCHES = '/api/switches'
REST_SWITCH_DETAIL = '/api/switches/{dpid}'
REST_FLOWS = '/api/flows/{dpid}'
REST_POLICY_STATUS = '/api/policy/status'
REST_POLICY_VERIFICATION = '/api/policy/verify'
REST_STATISTICS = '/api/statistics/{dpid}'

class RestApi(app_manager.RyuApp):
    """
    REST API application for SDN controller.
    """
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}
    
    def __init__(self, *args, **kwargs):
        super(RestApi, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        mapper = wsgi.mapper
        
        wsgi.register(RestController, {'rest_api': self})
        
        # Register routes
        mapper.connect('switches', REST_SWITCHES, 
                      controller=RestController, action='list_switches',
                      conditions=dict(method=['GET']))
        
        mapper.connect('switch_detail', REST_SWITCH_DETAIL, 
                      controller=RestController, action='get_switch_detail',
                      conditions=dict(method=['GET']))
        
        mapper.connect('flows', REST_FLOWS, 
                      controller=RestController, action='get_flows',
                      conditions=dict(method=['GET']))
        
        mapper.connect('policy_status', REST_POLICY_STATUS, 
                      controller=RestController, action='get_policy_status',
                      conditions=dict(method=['GET']))
        
        mapper.connect('policy_verification', REST_POLICY_VERIFICATION, 
                      controller=RestController, action='verify_policies',
                      conditions=dict(method=['GET']))
        
        mapper.connect('statistics', REST_STATISTICS, 
                      controller=RestController, action='get_statistics',
                      conditions=dict(method=['GET']))
        
        self.switches = {}
        self.policy_engine_url = os.environ.get('POLICY_ENGINE_URL', 'http://policy-engine:5000')
        self.policy_file = os.environ.get('DEFAULT_POLICY_FILE', 'config/policies/network_security_policy.json')
        
        # Load policies for verification
        self.policies = self._load_policies()
        
        logger.info("REST API initialized")
    
    def _load_policies(self) -> Dict[str, Any]:
        """Load policies from file."""
        try:
            if os.path.exists(self.policy_file):
                logger.info(f"Loading policies from {self.policy_file}")
                with open(self.policy_file, 'r') as f:
                    policies = json.load(f)
                logger.info(f"Loaded {len(policies.get('policies', []))} policies")
                return policies
            else:
                logger.warning(f"Policy file not found: {self.policy_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            return {}
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, MAIN_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Handle switch features event.
        """
        datapath = ev.msg.datapath
        dpid = datapath.id
        self.switches[dpid] = datapath
        logger.info(f"Switch connected: {dpid}")
    
    def get_switches(self) -> List[Dict[str, Any]]:
        """
        Get list of connected switches.
        """
        switches = []
        for dpid, datapath in self.switches.items():
            switch_info = {
                'dpid': dpid,
                'address': datapath.address,
                'connected_since': datapath.connection.time.isoformat()
            }
            switches.append(switch_info)
        return switches
    
    def get_switch_detail(self, dpid: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a switch.
        """
        if dpid not in self.switches:
            return None
        
        datapath = self.switches[dpid]
        
        # Get switch details via REST API
        switch_data = get_switches('localhost', 8181, True)
        if not switch_data:
            return {
                'dpid': dpid,
                'address': datapath.address,
                'error': 'Could not fetch detailed information'
            }
        
        # Find the switch in the response
        for switch in switch_data.get('switches', []):
            if switch.get('dpid') == dpid:
                # Add basic info
                switch['address'] = datapath.address
                switch['ofp_version'] = datapath.ofproto.OFP_VERSION
                return switch
        
        # If switch not found in detail data
        return {
            'dpid': dpid,
            'address': datapath.address,
            'error': 'Switch details not available'
        }
    
    def get_flows(self, dpid: int) -> List[Dict[str, Any]]:
        """
        Get flows for a specific switch.
        """
        if dpid not in self.switches:
            return []
        
        # Get switch flows via REST API
        switch_data = get_switches('localhost', 8181, True)
        if not switch_data:
            return []
        
        # Find the switch in the response
        for switch in switch_data.get('switches', []):
            if switch.get('dpid') == dpid:
                return switch.get('flows', [])
        
        return []
    
    def get_policy_status(self) -> Dict[str, Any]:
        """
        Get status of policy application.
        """
        # Get switch data
        switch_data = get_switches('localhost', 8181, True)
        if not switch_data:
            return {
                'status': 'error',
                'message': 'Could not fetch switch data'
            }
        
        # Count policy-related flows
        total_flows = 0
        policy_flows = 0
        qos_flows = 0
        switches_with_policies = 0
        
        for switch in switch_data.get('switches', []):
            total_flows += switch.get('flow_count', 0)
            
            # Count policy flows
            switch_policy_flows = len(switch.get('policy_flows', []))
            policy_flows += switch_policy_flows
            
            # Count QoS flows
            switch_qos_flows = switch.get('qos_flow_count', 0)
            qos_flows += switch_qos_flows
            
            if switch_policy_flows > 0 or switch_qos_flows > 0:
                switches_with_policies += 1
        
        return {
            'status': 'ok',
            'total_switches': len(switch_data.get('switches', [])),
            'switches_with_policies': switches_with_policies,
            'total_flows': total_flows,
            'policy_flows': policy_flows,
            'qos_flows': qos_flows,
            'policy_coverage_percent': round(policy_flows / total_flows * 100, 2) if total_flows > 0 else 0
        }
    
    def verify_policies(self) -> Dict[str, Any]:
        """
        Verify that policies are correctly applied.
        """
        # Get switch data
        switch_data = get_switches('localhost', 8181, True)
        if not switch_data:
            return {
                'status': 'error',
                'message': 'Could not fetch switch data'
            }
        
        # Check policy application
        verification = check_policy_application(switch_data, self.policy_file)
        
        return {
            'status': 'ok',
            'verification': verification
        }
    
    def get_statistics(self, dpid: int) -> Dict[str, Any]:
        """
        Get statistics for a specific switch.
        """
        if dpid not in self.switches:
            return {
                'status': 'error',
                'message': f'Switch {dpid} not found'
            }
        
        datapath = self.switches[dpid]
        
        # This would normally call statistics collection methods
        # For now, return placeholders
        return {
            'dpid': dpid,
            'port_stats': [],  # Would be populated with actual port statistics
            'flow_stats': [],  # Would be populated with actual flow statistics
            'message': 'Statistics collection not fully implemented'
        }


class RestController(ControllerBase):
    """
    REST API controller.
    """
    def __init__(self, req, link, data, **config):
        super(RestController, self).__init__(req, link, data, **config)
        self.rest_api = data['rest_api']
    
    @route('switches', REST_SWITCHES)
    def list_switches(self, req, **kwargs):
        """
        List all connected switches.
        """
        switches = self.rest_api.get_switches()
        body = {'switches': switches}
        return self._make_response(body)
    
    @route('switch_detail', REST_SWITCH_DETAIL)
    def get_switch_detail(self, req, **kwargs):
        """
        Get detailed information about a switch.
        """
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        switch = self.rest_api.get_switch_detail(dpid)
        
        if switch:
            return self._make_response(switch)
        else:
            return self._make_error_response(f'Switch {dpid} not found', 404)
    
    @route('flows', REST_FLOWS)
    def get_flows(self, req, **kwargs):
        """
        Get flows for a specific switch.
        """
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        flows = self.rest_api.get_flows(dpid)
        body = {'dpid': dpid, 'flows': flows}
        return self._make_response(body)
    
    @route('policy_status', REST_POLICY_STATUS)
    def get_policy_status(self, req, **kwargs):
        """
        Get status of policy application.
        """
        status = self.rest_api.get_policy_status()
        return self._make_response(status)
    
    @route('policy_verification', REST_POLICY_VERIFICATION)
    def verify_policies(self, req, **kwargs):
        """
        Verify that policies are correctly applied.
        """
        verification = self.rest_api.verify_policies()
        return self._make_response(verification)
    
    @route('statistics', REST_STATISTICS)
    def get_statistics(self, req, **kwargs):
        """
        Get statistics for a specific switch.
        """
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        stats = self.rest_api.get_statistics(dpid)
        return self._make_response(stats)
    
    def _make_response(self, body):
        """
        Create a JSON response.
        """
        return json.dumps(body)
    
    def _make_error_response(self, message, status=400):
        """
        Create an error response.
        """
        body = {'error': message}
        self.set_status(status)
        return json.dumps(body) 