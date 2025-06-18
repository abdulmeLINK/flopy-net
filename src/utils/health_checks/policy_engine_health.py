#!/usr/bin/env python
"""
Health check service for the policy engine.
"""

import os
import sys
import logging
import time
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Return a health status response."""
    return jsonify({"status": "OK", "service": "policy-engine-health"}), 200

if __name__ == '__main__':
    # Use a different port for health check (5001 instead of 5000)
    port = int(os.environ.get('HEALTH_CHECK_PORT', 5001))
    
    # Start Flask app
    app.run(host='0.0.0.0', port=port, debug=False) 