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
REST Network Client Implementation

This module provides a REST-based implementation of the network client interface.
"""
import logging
import requests
import json
from typing import Dict, Any, Optional, Callable
from threading import Thread
import time
from flask import Flask, request, jsonify

from src.core.interfaces.network_client import INetworkClient
from src.core.interfaces.policy_engine import IPolicyEngine


class RestNetworkClient(INetworkClient):
    """
    REST implementation of the network client interface.
    
    This class uses HTTP REST calls for network communication between components.
    It also includes a built-in REST server for receiving messages.
    """
    
    def __init__(self, 
                 component_name: str, 
                 policy_engine: Optional[IPolicyEngine] = None,
                 host: str = "0.0.0.0", 
                 port: int = 0,
                 config: Dict[str, Any] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the REST network client.
        
        Args:
            component_name: Name of the component using this client
            policy_engine: Optional policy engine to check policies
            host: Host to listen on
            port: Port to listen on (0 for random port)
            config: Configuration dictionary
            logger: Optional logger
        """
        self.component_name = component_name
        self.policy_engine = policy_engine
        self.host = host
        self.port = port
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        
        self.server_app = Flask(f"{component_name}_network_client")
        self.server_thread = None
        self.handlers = {}
        self.endpoints = {}
        self.connected = False
        self.is_running = False
        self.session = requests.Session()
        
        # Initialize the server
        self._init_server()
    
    def _init_server(self) -> None:
        """Initialize the REST server for receiving messages."""
        @self.server_app.route('/api/message', methods=['POST'])
        def handle_message():
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                message_type = data.get('message_type')
                if not message_type:
                    return jsonify({"error": "No message type provided"}), 400
                
                if message_type not in self.handlers:
                    return jsonify({"error": f"No handler for message type: {message_type}"}), 404
                
                # Check policy if policy engine is available
                if self.policy_engine:
                    policy_result = self.policy_engine.evaluate_policy(
                        'message_handling', 
                        {
                            'component': self.component_name,
                            'message_type': message_type,
                            'source': data.get('source', 'unknown'),
                            'timestamp': time.time()
                        }
                    )
                    
                    if not policy_result.get('allowed', True):
                        return jsonify({
                            "error": "Message rejected by policy",
                            "reason": policy_result.get('reason', 'Unknown policy violation')
                        }), 403
                
                # Handle the message
                handler = self.handlers[message_type]
                result = handler(data.get('payload', {}))
                
                return jsonify({
                    "success": True,
                    "response": result
                })
                
            except Exception as e:
                self.logger.error(f"Error handling message: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.server_app.route('/api/status', methods=['GET'])
        def get_status():
            return jsonify(self.get_status())
    
    def _start_server(self) -> None:
        """Start the REST server in a separate thread."""
        def run_server():
            self.server_app.run(host=self.host, port=self.port, debug=False)
        
        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        self.logger.info(f"Network client server started on {self.host}:{self.port}")
    
    def connect(self, endpoint: str, auth_token: Optional[str] = None) -> bool:
        """
        Connect to a remote endpoint.
        
        Args:
            endpoint: The endpoint to connect to (URL or address)
            auth_token: Optional authentication token
            
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Start the server if it's not running
            if not self.is_running:
                self._start_server()
            
            # Add the endpoint to our known endpoints
            parsed_endpoint = endpoint.strip('/')
            if '://' not in parsed_endpoint:
                parsed_endpoint = f"http://{parsed_endpoint}"
            
            # Test the connection
            headers = {}
            if auth_token:
                headers['Authorization'] = f"Bearer {auth_token}"
            
            response = self.session.get(f"{parsed_endpoint}/api/status", headers=headers, timeout=5)
            
            if response.status_code == 200:
                self.endpoints['policy_engine'] = parsed_endpoint
                self.connected = True
                self.logger.info(f"Connected to endpoint: {endpoint}")
                return True
            else:
                self.logger.error(f"Failed to connect to endpoint {endpoint}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to endpoint {endpoint}: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the remote endpoint.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        self.connected = False
        self.endpoints = {}
        return True
    
    def send_message(self, destination: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to a destination.
        
        Args:
            destination: Destination identifier (component name, URL, etc.)
            message_type: Type of message being sent
            payload: Message payload
            
        Returns:
            Response from the destination
        """
        try:
            # Get the endpoint for the destination
            endpoint = self.endpoints.get(destination)
            if not endpoint and destination in self.config.get('endpoints', {}):
                endpoint = self.config['endpoints'][destination]
            
            if not endpoint:
                self.logger.error(f"Unknown destination: {destination}")
                return {"error": f"Unknown destination: {destination}"}
            
            # Prepare the message
            message = {
                'source': self.component_name,
                'message_type': message_type,
                'payload': payload,
                'timestamp': time.time()
            }
            
            # Check policy if policy engine is available
            if self.policy_engine:
                policy_result = self.policy_engine.evaluate_policy(
                    'message_sending', 
                    {
                        'component': self.component_name,
                        'destination': destination,
                        'message_type': message_type,
                        'timestamp': time.time()
                    }
                )
                
                if not policy_result.get('allowed', True):
                    self.logger.warning(f"Message to {destination} rejected by policy: {policy_result.get('reason', 'Unknown policy violation')}")
                    return {
                        "error": "Message rejected by policy",
                        "reason": policy_result.get('reason', 'Unknown policy violation')
                    }
            
            # Send the message
            response = self.session.post(
                f"{endpoint}/api/message",
                json=message,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('response', {})
            else:
                self.logger.error(f"Error sending message to {destination}: {response.status_code}")
                return {"error": f"Failed to send message: {response.status_code}"}
                
        except Exception as e:
            self.logger.error(f"Error sending message to {destination}: {e}")
            return {"error": str(e)}
    
    def register_handler(self, message_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Register a message handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Function to call when a message of this type is received
            
        Returns:
            True if registered successfully, False otherwise
        """
        self.handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")
        return True
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check with the policy engine if an action is allowed.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Policy evaluation result
        """
        if not self.policy_engine:
            self.logger.warning("No policy engine available to check policy")
            return {"allowed": True}
        
        # Add component information to context
        context['component'] = self.component_name
        context['timestamp'] = time.time()
        
        # Evaluate the policy
        return self.policy_engine.evaluate_policy(policy_type, context)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the network client.
        
        Returns:
            Dictionary containing status information
        """
        return {
            "component": self.component_name,
            "connected": self.connected,
            "server_running": self.is_running,
            "handlers": list(self.handlers.keys()),
            "endpoints": self.endpoints
        } 