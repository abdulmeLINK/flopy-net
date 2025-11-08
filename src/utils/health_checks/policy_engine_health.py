"""
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