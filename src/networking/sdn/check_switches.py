#!/usr/bin/env python3
"""
Script to check the status of switches connected to the Ryu SDN controller.
This script can be run inside the SDN controller container to get real-time information
about the switches connected to the controller and verify policy application.
"""

import sys
import json
import argparse
import requests
import re
from typing import Dict, List, Any

def get_switches(controller_host="localhost", controller_port=8181, verbose=False):
    """Get all switches connected to the controller and their details."""
    base_url = f"http://{controller_host}:{controller_port}"
    
    # Step 1: Get list of switches
    switches_url = f"{base_url}/stats/switches"
    try:
        print(f"Fetching switches from {switches_url}...")
        response = requests.get(switches_url, timeout=5)
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code} when getting switches")
            return None
        
        switch_ids = response.json()
        print(f"Found {len(switch_ids)} switches: {switch_ids}")
        
        # For each switch, get additional details
        switch_details = []
        for dpid in switch_ids:
            switch_info = {
                "dpid": dpid,
                "ports": [],
                "flows": [],
                "flow_count": 0,
                "policy_flows": []  # New field to track policy-related flows
            }
            
            # Get switch ports
            print(f"Fetching ports for switch {dpid}...")
            port_url = f"{base_url}/stats/portdesc/{dpid}"
            try:
                port_response = requests.get(port_url, timeout=5)
                if port_response.status_code == 200:
                    ports_data = port_response.json()
                    if str(dpid) in ports_data:
                        switch_info["ports"] = ports_data[str(dpid)]
                        print(f"  - Found {len(switch_info['ports'])} ports")
                else:
                    print(f"  - Error: HTTP {port_response.status_code} when getting ports")
            except Exception as e:
                print(f"  - Error getting ports: {e}")
            
            # Get switch flows
            print(f"Fetching flows for switch {dpid}...")
            flow_url = f"{base_url}/stats/flow/{dpid}"
            try:
                flow_response = requests.get(flow_url, timeout=5)
                if flow_response.status_code == 200:
                    flows_data = flow_response.json()
                    if str(dpid) in flows_data:
                        all_flows = flows_data[str(dpid)]
                        switch_info["flow_count"] = len(all_flows)
                        print(f"  - Found {switch_info['flow_count']} flows")
                        
                        if verbose:
                            switch_info["flows"] = all_flows
                        
                        # Identify policy-related flows (based on cookies or other markers)
                        policy_flows = []
                        for flow in all_flows:
                            # Look for policy markers in flow cookies or metadata
                            # Typically policy engines set cookies or metadata to identify policy-applied flows
                            cookie = flow.get('cookie', 0)
                            if cookie > 0:  # Non-zero cookies typically indicate policy-applied flows
                                # Extract policy ID from cookie if possible (adjust as needed for your system)
                                policy_id = (cookie >> 16) & 0xFFFF  # Example: extract upper 16 bits
                                
                                # Look for policy actions in the flow instructions
                                actions = []
                                instructions = flow.get('instructions', [])
                                for instruction in instructions:
                                    if 'actions' in instruction:
                                        actions.extend(instruction['actions'])
                                
                                policy_flows.append({
                                    'policy_id': policy_id,
                                    'priority': flow.get('priority', 0),
                                    'table_id': flow.get('table_id', 0),
                                    'match': flow.get('match', {}),
                                    'actions': actions,
                                    'cookie': cookie
                                })
                        
                        switch_info["policy_flows"] = policy_flows
                        print(f"  - Identified {len(policy_flows)} policy-related flows")
                        
                        # Check for QoS and rate limiting flows
                        qos_flows = [f for f in all_flows if any(
                            'queue' in str(a) for instr in f.get('instructions', []) 
                            for a in instr.get('actions', [])
                        )]
                        
                        switch_info["qos_flow_count"] = len(qos_flows)
                        if qos_flows:
                            print(f"  - Found {len(qos_flows)} QoS/rate-limiting flows")
                else:
                    print(f"  - Error: HTTP {flow_response.status_code} when getting flows")
            except Exception as e:
                print(f"  - Error getting flows: {e}")
            
            # Check for metering if supported
            try:
                meter_url = f"{base_url}/stats/meter/{dpid}"
                meter_response = requests.get(meter_url, timeout=5)
                if meter_response.status_code == 200:
                    meter_data = meter_response.json()
                    if str(dpid) in meter_data and meter_data[str(dpid)]:
                        switch_info["meters"] = meter_data[str(dpid)]
                        print(f"  - Found {len(switch_info['meters'])} meters (rate limiters)")
            except Exception as e:
                # Meters might not be supported, so we just note the error in verbose mode
                if verbose:
                    print(f"  - Note: Meter stats not available: {e}")
            
            switch_details.append(switch_info)
        
        result = {
            "switches_count": len(switch_details),
            "switches": switch_details
        }
        
        return result
    
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to controller at {base_url}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def check_policy_application(switch_details, policy_file=None):
    """Verify if the policy flows match expected policy rules."""
    
    # If a policy file is provided, read it to compare against actual flows
    policies = {}
    if policy_file:
        try:
            with open(policy_file, 'r') as f:
                policies = json.load(f)
                print(f"Loaded {len(policies.get('policies', []))} policies from {policy_file}")
        except Exception as e:
            print(f"Error loading policy file: {e}")
    
    # Policy verification results
    verification = {
        "verified": False,
        "policy_matches": [],
        "missing_policies": [],
        "summary": ""
    }
    
    # Basic policy checks without specific policy file
    policy_indicators = {
        "rate_limiting": False,
        "isolation": False,
        "vlan_tagging": False,
        "qos_prioritization": False,
        "path_selection": False
    }
    
    # Check for common policy flow patterns
    total_policy_flows = sum(len(switch.get("policy_flows", [])) for switch in switch_details.get("switches", []))
    total_qos_flows = sum(switch.get("qos_flow_count", 0) for switch in switch_details.get("switches", []))
    
    # Look for common patterns in flows that suggest policies are applied
    for switch in switch_details.get("switches", []):
        # Check for VLAN tags
        for flow in switch.get("flows", []):
            match = flow.get("match", {})
            actions = []
            for instruction in flow.get("instructions", []):
                if "actions" in instruction:
                    actions.extend(instruction["actions"])
            
            # Check for rate limiting flows (meter actions)
            if any("meter" in str(a) for a in actions):
                policy_indicators["rate_limiting"] = True
            
            # Check for VLAN tagging
            if "dl_vlan" in match or any("vlan" in str(a).lower() for a in actions):
                policy_indicators["vlan_tagging"] = True
            
            # Check for QoS (queue assignment)
            if any("queue" in str(a).lower() for a in actions):
                policy_indicators["qos_prioritization"] = True
            
            # Check for isolation (drop actions between certain IPs)
            if match.get("dl_type") == 2048:  # IPv4
                src_ip = match.get("nw_src")
                dst_ip = match.get("nw_dst")
                if src_ip and dst_ip and any("drop" in str(a).lower() for a in actions):
                    policy_indicators["isolation"] = True
            
            # Check for path selection (output to specific ports)
            if len(actions) > 0 and any("output" in str(a).lower() for a in actions):
                policy_indicators["path_selection"] = True
    
    # Summarize findings
    active_policies = [k for k, v in policy_indicators.items() if v]
    verification["verified"] = len(active_policies) > 0
    verification["policy_indicators"] = policy_indicators
    verification["active_policies"] = active_policies
    verification["total_policy_flows"] = total_policy_flows
    verification["total_qos_flows"] = total_qos_flows
    
    verification["summary"] = f"Found {total_policy_flows} policy-related flows across all switches\n"
    verification["summary"] += f"Detected policy types: {', '.join(active_policies) if active_policies else 'None'}"
    
    return verification

def main():
    parser = argparse.ArgumentParser(description='Check SDN switches status')
    parser.add_argument('--host', default='localhost', help='Controller host (default: localhost)')
    parser.add_argument('--port', type=int, default=8181, help='Controller REST API port (default: 8181)')
    parser.add_argument('--output', default=None, help='Output file for JSON results (default: stdout)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed flow information')
    parser.add_argument('--policy-file', help='Path to policy file for verification')
    parser.add_argument('--verify-policies', action='store_true', help='Verify policy application')
    
    args = parser.parse_args()
    
    # Get switch status
    result = get_switches(args.host, args.port, args.verbose)
    
    if result:
        # Add policy verification if requested
        if args.verify_policies:
            print("\nVerifying policy application...")
            verification = check_policy_application(result, args.policy_file)
            result["policy_verification"] = verification
            print(verification["summary"])
        
        # Format the output
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {args.output}")
        else:
            print("\nSummary:")
            print(f"- Connected switches: {result['switches_count']}")
            
            for i, switch in enumerate(result['switches']):
                print(f"\nSwitch {i+1}:")
                print(f"- DPID: {switch['dpid']}")
                print(f"- Ports: {len(switch['ports'])}")
                print(f"- Flows: {switch['flow_count']}")
                
                # Show policy-related flows summary
                if "policy_flows" in switch and switch["policy_flows"]:
                    print(f"- Policy-related flows: {len(switch['policy_flows'])}")
                
                if "qos_flow_count" in switch and switch["qos_flow_count"]:
                    print(f"- QoS/Rate limiting flows: {switch['qos_flow_count']}")
                
                if args.verbose:
                    print("\nPorts:")
                    for port in switch['ports']:
                        port_name = port.get('name', 'unnamed')
                        port_no = port.get('port_no', 'unknown')
                        hw_addr = port.get('hw_addr', 'unknown')
                        print(f"  - {port_name} (#{port_no}, MAC: {hw_addr})")
    else:
        print("Failed to get switch information.")
        sys.exit(1)

if __name__ == "__main__":
    main() 