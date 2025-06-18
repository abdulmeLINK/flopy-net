#!/usr/bin/env python3
"""
Policy Engine Main Module

This module provides the entry point for running the policy engine server.
"""

import os
import sys
import logging
import argparse
from .policy_engine_server import main

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

def run_server():
    """Run the policy engine server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Policy Engine Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to listen on')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--policy-file', type=str, help='Path to policy file')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--log-level', type=str, default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Call the main function from policy_engine_server with arguments
    main(args)

if __name__ == "__main__":
    run_server()