"""
Runner for the FL-SDN Dashboard

This module provides a CLI for running the FL-SDN dashboard (API and Web UI).
It supports running both components together or individually.
"""

import os
import time
import logging
import argparse
import threading
import uvicorn
from multiprocessing import Process
import dash
import dash_bootstrap_components as dbc

from .api import app as api_app
from .app import app as dash_app
from .scenarios import scenario_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard-runner")

# Default ports
DASH_PORT = int(os.environ.get("DASH_PORT", 8050))
API_PORT = int(os.environ.get("API_PORT", 8051))

def run_dash(port=DASH_PORT, debug=False):
    """Run the Dash web application."""
    logger.info(f"Starting Dash web application on port {port}")
    dash_app.run_server(host="0.0.0.0", port=port, debug=debug)

def run_api(port=API_PORT, debug=False):
    """Run the FastAPI application."""
    logger.info(f"Starting API server on port {port}")
    uvicorn.run(api_app, host="0.0.0.0", port=port, log_level="info")

def run_data_refresh():
    """Run a background thread to refresh scenario data."""
    logger.info("Starting data refresh thread")
    while True:
        try:
            scenario_manager.refresh_data()
            time.sleep(5)  # Refresh every 5 seconds
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            time.sleep(10)  # Wait longer if there's an error

def main():
    """Main entry point for the dashboard runner."""
    parser = argparse.ArgumentParser(description="Run the FL-SDN Dashboard")
    parser.add_argument("--dash-only", action="store_true", help="Run only the Dash web application")
    parser.add_argument("--api-only", action="store_true", help="Run only the API server")
    parser.add_argument("--dash-port", type=int, default=DASH_PORT, help=f"Port for Dash app (default: {DASH_PORT})")
    parser.add_argument("--api-port", type=int, default=API_PORT, help=f"Port for API server (default: {API_PORT})")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    # Set up refresh thread
    refresh_thread = threading.Thread(target=run_data_refresh, daemon=True)
    refresh_thread.start()

    # If both are requested, or neither is specified, run both
    run_both = not (args.dash_only or args.api_only)

    if args.dash_only or run_both:
        dash_process = Process(target=run_dash, args=(args.dash_port, args.debug))
        dash_process.start()
        logger.info(f"Dash web application running at http://localhost:{args.dash_port}")

    if args.api_only or run_both:
        api_process = Process(target=run_api, args=(args.api_port, args.debug))
        api_process.start()
        logger.info(f"API server running at http://localhost:{args.api_port}")

    try:
        # Keep the main thread alive
        while run_both or args.dash_only or args.api_only:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if run_both or args.dash_only:
            dash_process.terminate()
        if run_both or args.api_only:
            api_process.terminate()

if __name__ == "__main__":
    main() 