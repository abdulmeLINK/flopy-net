#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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

"
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