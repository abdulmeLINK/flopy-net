"""
Dashboard Runner

This module runs the dashboard application.
"""

import os
import sys
import argparse
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_dash_app():
    """Run the Dash web application."""
    from dashboard.app import app
    
    port = int(os.environ.get("DASH_PORT", 8050))
    logger.info(f"Starting Dash app on port {port}")
    app.run_server(host="0.0.0.0", port=port, debug=False)


def run_api():
    """Run the FastAPI application."""
    import uvicorn
    from dashboard.api import app
    
    port = int(os.environ.get("API_PORT", 8051))
    logger.info(f"Starting API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run the dashboard application")
    parser.add_argument("--dash-only", action="store_true", help="Run only the Dash app")
    parser.add_argument("--api-only", action="store_true", help="Run only the API")
    args = parser.parse_args()
    
    if args.dash_only:
        run_dash_app()
    elif args.api_only:
        run_api()
    else:
        # Run both in separate threads
        dash_thread = threading.Thread(target=run_dash_app, daemon=True)
        api_thread = threading.Thread(target=run_api, daemon=True)
        
        dash_thread.start()
        api_thread.start()
        
        # Wait for both threads to complete
        dash_thread.join()
        api_thread.join()


if __name__ == "__main__":
    main() 