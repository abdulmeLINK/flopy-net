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

"""
Main entry point for the federated learning application.

This module serves as the entry point for the federated learning system,
providing a command-line interface for running different components.
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
from pathlib import Path

# Set up logging
def setup_logging(level=logging.INFO):
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "federated_learning.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("federated_learning")

# Main logger
logger = setup_logging()

# Import scenarios from common module
from src.scenarios.common import SCENARIOS

def start_api_server(host, port, debug=False):
    """Start the API server with WebSocket support"""
    logger.info(f"Starting API server on {host}:{port} (debug={debug})")
    from src.presentation.rest.app import create_app
    import uvicorn
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="debug" if debug else "info")

def start_dashboard(host, port, debug=False):
    """Start the dashboard server"""
    logger.info(f"Starting dashboard on {host}:{port} (debug={debug})")
    from src.dashboard.run_dashboard import run_dashboard
    # Note: run_dashboard doesn't accept host parameter, only port and debug
    run_dashboard(port=port, debug=debug)

def run_scenario(scenario_id, config=None):
    """Run a specific federated learning scenario"""
    logger.info(f"Running scenario {scenario_id} with config: {config}")
    from src.scenarios.run_scenario import run_scenario
    run_scenario(scenario_id, config)

def handle_run_command(args):
    """Handle the 'run' command to start services"""
    services = []
    threads = []
    
    # Set debug mode if requested
    if args.debug:
        setup_logging(level=logging.DEBUG)
        logger.debug("Debug mode enabled")
        logger.debug(f"Command arguments: {args}")
    
    # Start API server if requested
    if args.api:
        # For the API, we'll create a separate process instead of a thread
        # to avoid issues with signal handling in Uvicorn
        import subprocess
        
        cmd = [sys.executable, "-m", "src.presentation.rest.app"]
        if args.debug:
            cmd.append("--debug")
        
        api_process = subprocess.Popen(
            cmd,
            env=os.environ.copy()
        )
        
        services.append(f"API server on {args.host}:{args.api_port}")
        
        # Print helpful information for testing        
        if args.debug:
            logger.info("API Debug Info:")
            logger.info("- API Endpoints: http://localhost:5000 (Flask routes, no automatic docs)")
            logger.info("- Health Check: http://localhost:5000/health")
            logger.info("- Metrics: http://localhost:5000/api/metrics")
            logger.info("- Generate Test Metrics: POST http://localhost:5000/api/metrics/generate-test")
            logger.info("- Scenarios: http://localhost:5000/api/scenarios")
            logger.info("- Metric History: http://localhost:5000/api/metrics/history/{category}/{metric_name}")
    
    # Start dashboard if requested
    if args.dashboard:
        dashboard_thread = threading.Thread(
            target=start_dashboard,
            args=(args.host, args.dashboard_port),
            kwargs={"debug": args.debug},
            daemon=True
        )
        threads.append(dashboard_thread)
        services.append(f"Dashboard on {args.host}:{args.dashboard_port}")
        
        # Print helpful information for dashboard
        if args.debug:
            logger.info("Dashboard Debug Info:")
            logger.info(f"- Dashboard URL: http://localhost:{args.dashboard_port}")
    
    # Start scenario if requested
    if args.scenario:
        config = {}
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Error loading scenario config: {e}")
                sys.exit(1)
        
        scenario_thread = threading.Thread(
            target=run_scenario,
            args=(args.scenario, config),
            daemon=True
        )
        threads.append(scenario_thread)
        services.append(f"Scenario {args.scenario}")
    
    # If no services specified, show help
    if not services:
        logger.warning("No services specified to run. Use --api, --dashboard, or --scenario")
        return
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    logger.info(f"Started services: {', '.join(services)}")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
            
            # Check if any threads died
            for thread in threads[:]:
                if not thread.is_alive():
                    logger.error(f"A service thread has died. Shutting down...")
                    if args.api and 'api_process' in locals():
                        api_process.terminate()
                    sys.exit(1)
                    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        # Terminate the API process if it was started
        if args.api and 'api_process' in locals():
            api_process.terminate()
        sys.exit(0)

def handle_scenario_command(args):
    """Handle the 'scenario' command to manage scenarios"""
    if args.list:
        from src.scenarios.run_scenario import SCENARIOS
        print("\n=== Available Scenarios ===")
        for scenario_id, info in SCENARIOS.items():
            print(f"- {scenario_id}: {info.get('name', 'Unnamed')}")
            if info.get('description'):
                print(f"  {info.get('description')}")
        print()
    elif args.run:
        config = {}
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Error loading scenario config: {e}")
                sys.exit(1)
        
        run_scenario(args.run, config)

def main():
    """Main entry point for federated learning system"""
    parser = argparse.ArgumentParser(
        description="Federated Learning System with API and Dashboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Add common arguments
    parser.add_argument('--debug', action='store_true', help="Enable debug mode", default=False)
    parser.add_argument('--host', type=str, default="localhost", help="Host to bind services to")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # 'run' command
    run_parser = subparsers.add_parser('run', help='Run one or more services')
    run_parser.add_argument('--api', action='store_true', help="Start the API server")
    run_parser.add_argument('--api-port', type=int, default=5000, help="Port for the API server")
    run_parser.add_argument('--dashboard', action='store_true', help="Start the dashboard")
    run_parser.add_argument('--dashboard-port', type=int, default=8050, help="Port for the dashboard")
    run_parser.add_argument('--scenario', type=str, help="Run a specific scenario")
    run_parser.add_argument('--config', type=str, help="Configuration file for the scenario")
    run_parser.add_argument('--debug', action='store_true', help="Enable debug mode", default=False)
    
    # 'scenario' command
    scenario_parser = subparsers.add_parser('scenario', help='Manage scenarios')
    scenario_parser.add_argument('--list', action='store_true', help="List available scenarios")
    scenario_parser.add_argument('--run', type=str, help="Run a specific scenario")
    scenario_parser.add_argument('--config', type=str, help="Configuration file for the scenario")
    scenario_parser.add_argument('--debug', action='store_true', help="Enable debug mode", default=False)
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command specified, default to 'run'
    if not args.command:
        args.command = 'run'
        args.api = True
        args.dashboard = True
    
    # Set debug mode if requested at either level
    if args.debug:
        setup_logging(level=logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Handle commands
    if args.command == 'run':
        handle_run_command(args)
    elif args.command == 'scenario':
        handle_scenario_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()