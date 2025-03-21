#!/usr/bin/env python
"""
Test Real Metrics Access

This script tests the ability to access real metrics from a running FL system via the API.
It can be used to verify that the metrics API is properly collecting and exposing real simulation data.
"""

import sys
import time
import argparse
import logging
import requests
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src directory to path
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

def test_metrics_api(base_url="http://localhost:5000", wait_time=10, check_interval=1):
    """
    Test the metrics API by checking for real metrics.
    
    Args:
        base_url: Base URL of the metrics API
        wait_time: Maximum time to wait for real metrics
        check_interval: Interval between checks
    
    Returns:
        True if real metrics were found, False otherwise
    """
    logger.info(f"Testing metrics API at {base_url}")
    
    # Try to connect to the API
    try:
        response = requests.get(base_url)
        if response.status_code != 200:
            logger.error(f"Failed to connect to API: {response.status_code}")
            return False
        logger.info("Connected to API successfully")
    except requests.RequestException as e:
        logger.error(f"Error connecting to API: {e}")
        return False
    
    # Wait for real metrics to appear
    start_time = time.time()
    real_metrics_found = False
    
    while time.time() - start_time < wait_time:
        try:
            # Check current metrics
            response = requests.get(f"{base_url}/metrics/current")
            if response.status_code == 200:
                metrics = response.json()
                if metrics and 'accuracy' in metrics:
                    logger.info(f"Found metrics: {metrics}")
                    real_metrics_found = True
                    break
            
            # Also check system status
            response = requests.get(f"{base_url}/system")
            if response.status_code == 200:
                system = response.json()
                logger.info(f"System status: {system}")
                
                # If the system is running and has completed rounds, consider metrics real
                if system.get('status') == 'running' and system.get('current_round', 0) > 0:
                    logger.info("System is running and has completed rounds")
                    real_metrics_found = True
                    break
            
            # Wait before checking again
            logger.info(f"Waiting for real metrics ({check_interval}s)...")
            time.sleep(check_interval)
            
        except requests.RequestException as e:
            logger.error(f"Error checking metrics: {e}")
            time.sleep(check_interval)
    
    if real_metrics_found:
        logger.info("Successfully found real metrics!")
        
        # Get all metrics and print a summary
        try:
            response = requests.get(f"{base_url}/all")
            if response.status_code == 200:
                all_metrics = response.json()
                
                # Print summary
                print("\n=== Metrics API Summary ===")
                print(f"System Status: {all_metrics.get('system', {}).get('status')}")
                print(f"Current Round: {all_metrics.get('system', {}).get('current_round')}/{all_metrics.get('system', {}).get('total_rounds')}")
                print(f"Active Clients: {len(all_metrics.get('clients', {}))}")
                print(f"Historical Metrics: {len(all_metrics.get('history', []))}")
                
                # Print current metrics if available
                if 'current' in all_metrics and all_metrics['current']:
                    print("\nCurrent Metrics:")
                    for key, value in all_metrics['current'].items():
                        print(f"  {key}: {value}")
                
                # Print active challenges if any
                if 'active_challenges' in all_metrics and all_metrics['active_challenges']:
                    print("\nActive Challenges:")
                    for challenge in all_metrics['active_challenges']:
                        print(f"  {challenge.get('name')}: {challenge.get('intensity', 0)}")
                
                print("\n=== End of Summary ===\n")
                
        except requests.RequestException as e:
            logger.error(f"Error getting all metrics: {e}")
    
    else:
        logger.warning(f"No real metrics found after waiting {wait_time} seconds")
    
    return real_metrics_found


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test access to real metrics via the API")
    parser.add_argument("--api-url", default="http://localhost:5000",
                      help="URL of the metrics API server")
    parser.add_argument("--wait-time", type=int, default=30,
                      help="Maximum time to wait for real metrics (seconds)")
    parser.add_argument("--check-interval", type=float, default=1.0,
                      help="Interval between checks (seconds)")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Test the metrics API
    success = test_metrics_api(
        base_url=args.api_url,
        wait_time=args.wait_time,
        check_interval=args.check_interval
    )
    
    # Exit with appropriate code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 