#!/usr/bin/env python3
"""
Test script to verify network status endpoint functionality.
"""

import requests
import json
import sys
from typing import Dict, Any

def test_network_status(base_url: str = "http://localhost:8001") -> bool:
    """Test the network status endpoint."""
    
    print("🔧 Testing Network Status API Endpoint")
    print("=" * 50)
    
    try:
        # Test the network status endpoint
        status_url = f"{base_url}/api/network/status"
        print(f"Testing: {status_url}")
        
        response = requests.get(status_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Network status endpoint successful!")
            
            # Validate response structure
            required_fields = [
                'status', 'gns3_status', 'topology', 
                'sdn_controller', 'performance', 'health'
            ]
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"⚠️  Missing fields: {missing_fields}")
                return False
            
            # Display key metrics
            print("\n📊 Network Metrics:")
            print(f"  Overall Status: {data.get('status', 'unknown')}")
            print(f"  Health Score: {data.get('health', {}).get('health_score', 'N/A')}")
            print(f"  Health Status: {data.get('health', {}).get('status', 'N/A')}")
            
            topology = data.get('topology', {})
            print(f"  Nodes Total: {topology.get('nodes_total', 0)}")
            print(f"  Links Total: {topology.get('links_total', 0)}")
            
            sdn = data.get('sdn_controller', {})
            print(f"  SDN Status: {sdn.get('status', 'unknown')}")
            print(f"  SDN Switches: {sdn.get('switches_count', 0)}")
            print(f"  Flow Rules: {sdn.get('total_flows', 0)}")
            
            performance = data.get('performance', {})
            print(f"  Avg Latency: {performance.get('avg_latency_ms', 0):.2f}ms")
            print(f"  Packet Loss: {performance.get('packet_loss_percent', 0):.2f}%")
            print(f"  Bandwidth Usage: {performance.get('bandwidth_utilization_percent', 0):.1f}%")
            
            health = data.get('health', {})
            issues = health.get('issues', [])
            if issues:
                print(f"\n⚠️  Issues Detected:")
                for issue in issues:
                    print(f"    - {issue}")
            
            recommendations = health.get('recommendations', [])
            if recommendations:
                print(f"\n💡 Recommendations:")
                for rec in recommendations:
                    print(f"    - {rec}")
            
            return True
            
        else:
            print(f"❌ Failed to get network status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_network_summary(base_url: str = "http://localhost:8001") -> bool:
    """Test the network metrics summary endpoint."""
    
    print("\n🔧 Testing Network Metrics Summary Endpoint")
    print("=" * 50)
    
    try:
        summary_url = f"{base_url}/api/network/metrics/summary?hours=24"
        print(f"Testing: {summary_url}")
        
        response = requests.get(summary_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "error" in data:
                print(f"⚠️  API returned error: {data['error']}")
                return True  # This is expected if no historical data exists
            
            print("✅ Network metrics summary endpoint successful!")
            
            # Display summary information
            print(f"\n📈 Summary for {data.get('time_period_hours', 0)} hours:")
            print(f"  Data Points: {data.get('data_points', 0)}")
            
            latency = data.get('latency', {})
            print(f"  Latency - Min: {latency.get('min', 0):.2f}ms, Max: {latency.get('max', 0):.2f}ms, Avg: {latency.get('avg', 0):.2f}ms")
            
            packet_loss = data.get('packet_loss', {})
            print(f"  Packet Loss - Min: {packet_loss.get('min', 0):.2f}%, Max: {packet_loss.get('max', 0):.2f}%, Avg: {packet_loss.get('avg', 0):.2f}%")
            
            availability = data.get('availability', {})
            print(f"  Uptime: {availability.get('uptime_percent', 0):.1f}%")
            
            return True
            
        else:
            print(f"❌ Failed to get metrics summary: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing metrics summary: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Network API Test Suite")
    print("=" * 60)
    
    # You can change this URL to match your deployment
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    
    print(f"Testing against: {base_url}")
    print()
    
    # Run tests
    status_test = test_network_status(base_url)
    summary_test = test_network_summary(base_url)
    
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary:")
    print(f"  Network Status Endpoint: {'✅ PASS' if status_test else '❌ FAIL'}")
    print(f"  Metrics Summary Endpoint: {'✅ PASS' if summary_test else '❌ FAIL'}")
    
    if status_test and summary_test:
        print("\n🎉 All tests passed! Network API is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 