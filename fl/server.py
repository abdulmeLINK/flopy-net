"""
Federated Learning Server

This module provides a simple FL server implementation for demonstration purposes.
"""

import logging
import sys
import os
from typing import Dict, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default settings
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8080))
POLICY_ENGINE_URL = os.environ.get("POLICY_ENGINE_URL", "http://localhost:8000")
SDN_CONTROLLER_URL = os.environ.get("SDN_CONTROLLER_URL", "http://localhost:8181")


class FlowerServer:
    """Simple FL server for demonstration."""
    
    def __init__(self):
        self.rounds = 0
        self.status = "idle"
        self.clients = []
        self.metrics = {
            "accuracy": [],
            "loss": [],
        }
    
    def start_training(self):
        """Start a simulated training process."""
        self.status = "training"
        
        # Start training in a separate thread
        threading.Thread(target=self._training_loop, daemon=True).start()
    
    def _training_loop(self):
        """Simulated training loop."""
        for _ in range(10):  # Simulate 10 rounds
            self.rounds += 1
            logger.info(f"Training round {self.rounds}")
            
            # Simulate metrics
            accuracy = 0.5 + (self.rounds / 20)  # Increases over time
            loss = 1.0 - (self.rounds / 15)  # Decreases over time
            
            self.metrics["accuracy"].append(accuracy)
            self.metrics["loss"].append(loss)
            
            # Sleep to simulate training time
            time.sleep(2)
        
        self.status = "completed"


class FLHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for FL server API."""
    
    # Create server instance
    flower_server = FlowerServer()
    
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
        self.wfile.write(b"{}")
    
    def do_GET(self):
        if self.path == "/":
            self._set_headers()
            response = {
                "message": "FL Server API",
                "version": "1.0.0",
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/status":
            self._set_headers()
            response = {
                "status": self.flower_server.status,
                "rounds": self.flower_server.rounds,
                "clients": len(self.flower_server.clients),
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/metrics":
            self._set_headers()
            self.wfile.write(json.dumps(self.flower_server.metrics).encode())
        
        elif self.path == "/clients":
            self._set_headers()
            self.wfile.write(json.dumps(self.flower_server.clients).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
    
    def do_POST(self):
        if self.path == "/start":
            self._set_headers()
            self.flower_server.start_training()
            response = {"message": "Training started"}
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/register":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            client_data = json.loads(post_data.decode())
            
            # Add client to list
            self.flower_server.clients.append(client_data)
            
            self._set_headers()
            response = {"message": "Client registered", "client_id": len(self.flower_server.clients)}
            self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def run_server():
    """Run the FL server."""
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, FLHTTPHandler)
    logger.info(f"Starting FL server on {HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server() 