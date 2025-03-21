#!/usr/bin/env python3
"""
Metrics API Example

This script demonstrates how to use the Federated Learning Metrics API client
to retrieve and process system metrics.
"""

import sys
import json
import time
import logging
from pathlib import Path
import argparse

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

# Import the client
from api.client import FLMetricsClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_metrics(metrics, indent=0):
    """Print metrics in a readable format."""
    if not metrics:
        print(" " * indent + "No metrics available")
        return
    
    for key, value in metrics.items():
        if isinstance(value, dict):
            print(" " * indent + f"{key}:")
            print_metrics(value, indent + 2)
        elif isinstance(value, list):
            print(" " * indent + f"{key}: [list with {len(value)} items]")
        else:
            print(" " * indent + f"{key}: {value}")


def monitor_metrics(client, interval=5, max_iterations=None):
    """
    Monitor metrics in real-time.
    
    Args:
        client: The metrics API client
        interval: Update interval in seconds
        max_iterations: Maximum number of iterations (None for infinite)
    """
    iteration = 0
    try:
        while max_iterations is None or iteration < max_iterations:
            # Get current metrics
            metrics = client.get_current_metrics()
            
            # Get system status
            system = client.get_system_status()
            
            # Clear screen (platform independent)
            print("\033c", end="")
            
            # Print header
            print("=" * 50)
            print(f"FL System Metrics - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            
            # Print system status
            print("\nSystem Status:")
            print(f"  Status: {system.get('status', 'unknown')}")
            print(f"  Current round: {system.get('current_round', 0)}")
            print(f"  Total rounds: {system.get('total_rounds', 0)}")
            
            # Print current metrics
            print("\nCurrent Metrics:")
            if metrics:
                for key, value in metrics.items():
                    if key in ["accuracy", "loss", "latency", "bandwidth"]:
                        print(f"  {key}: {value}")
            else:
                print("  No metrics available")
            
            # Get active challenges
            challenges = client.get_challenges()
            active_challenges = challenges.get("active_challenges", [])
            
            # Print active challenges
            print("\nActive Challenges:")
            if active_challenges:
                for challenge in active_challenges:
                    name = challenge.get("name", "Unknown")
                    intensity = challenge.get("intensity", 0)
                    print(f"  {name} (intensity: {intensity})")
            else:
                print("  No active challenges")
            
            # Get client information
            clients = client.get_clients()
            
            # Print client information
            print("\nClients:")
            if clients:
                for client_id, client_info in clients.items():
                    status = client_info.get("status", "unknown")
                    print(f"  Client {client_id}: {status}")
            else:
                print("  No client information available")
            
            # Increment iteration counter
            iteration += 1
            
            # Wait for next update
            if max_iterations is None or iteration < max_iterations:
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")


def export_metrics_to_json(client, filepath):
    """
    Export all metrics to a JSON file.
    
    Args:
        client: The metrics API client
        filepath: Path to save the JSON file
    """
    try:
        # Get all metrics
        metrics = client.get_all_metrics()
        
        # Save to JSON file
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Exported metrics to {filepath}")
    
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")


def send_commands_example(client):
    """
    Demonstrate how to send commands to the API.
    
    Args:
        client: The metrics API client
    """
    try:
        # Get available scenarios
        scenarios = client.get_challenges()
        available_scenarios = scenarios.get("available_scenarios", {})
        
        if not available_scenarios:
            print("No scenarios available")
            return
        
        # Print available scenarios
        print("Available scenarios:")
        for name, info in available_scenarios.items():
            description = info.get("description", "No description")
            print(f"  {name}: {description}")
        
        # Select a scenario
        selected_scenario = next(iter(available_scenarios.keys()))
        print(f"\nSetting scenario to: {selected_scenario}")
        
        # Send command to set scenario
        response = client.set_challenge_scenario(selected_scenario)
        print(f"Response: {response}")
        
        # Wait a moment
        time.sleep(2)
        
        # Get active challenges
        challenges = client.get_challenges()
        active_challenges = challenges.get("active_challenges", [])
        
        print("\nActive challenges after setting scenario:")
        if active_challenges:
            for challenge in active_challenges:
                name = challenge.get("name", "Unknown")
                intensity = challenge.get("intensity", 0)
                print(f"  {name} (intensity: {intensity})")
        else:
            print("  No active challenges")
    
    except Exception as e:
        logger.error(f"Error sending commands: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Metrics API example")
    parser.add_argument("--api-url", default="http://localhost:5000",
                      help="URL of the metrics API server")
    parser.add_argument("--monitor", action="store_true",
                      help="Monitor metrics in real-time")
    parser.add_argument("--interval", type=int, default=5,
                      help="Update interval for monitoring (seconds)")
    parser.add_argument("--export", help="Export metrics to JSON file")
    parser.add_argument("--commands", action="store_true",
                      help="Demonstrate sending commands to the API")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Create client
    client = FLMetricsClient(args.api_url)
    
    try:
        # Test connection
        system = client.get_system_status()
        logger.info(f"Connected to metrics API at {args.api_url}")
        logger.info(f"System status: {system.get('status', 'unknown')}")
        
        # Process commands based on arguments
        if args.export:
            export_metrics_to_json(client, args.export)
        
        if args.commands:
            send_commands_example(client)
        
        if args.monitor:
            monitor_metrics(client, interval=args.interval)
        
        # If no specific command, print current metrics once
        if not (args.export or args.commands or args.monitor):
            metrics = client.get_all_metrics()
            print("\nAll metrics:")
            print_metrics(metrics)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 