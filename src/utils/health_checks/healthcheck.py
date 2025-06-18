#!/usr/bin/env python3
"""
Generic HTTP server for basic health checks.
Responds with 200 OK and {"status": "healthy"} to GET /health.

This server can be used as a lightweight health check for Docker containers.
Other components in this project sometimes use minimal Flask apps for health checks
(e.g., src/utils/health_checks/policy_engine_health.py). Consideration should be
given to standardizing the health check approach for consistency and to minimize
unnecessary dependencies (like Flask for a very simple health endpoint) where this
generic server would suffice.
"""
import http.server
import socketserver
import os
import sys
import logging
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("healthcheck")

# Get port from environment or use default
PORT = int(os.environ.get("HEALTH_PORT", 8082))
HOST = os.environ.get("HOST", "0.0.0.0")

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
            logger.info(f"Health check request from {self.client_address[0]}")
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
            
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        if "/health" in args[0]:
            return
        http.server.SimpleHTTPRequestHandler.log_message(self, format, *args)

def run_server():
    """Run the health check server"""
    try:
        with socketserver.TCPServer((HOST, PORT), HealthCheckHandler) as httpd:
            logger.info(f"Health check server started at {HOST}:{PORT}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Health check server stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting health check server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server() 