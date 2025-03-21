"""
API Application

This module provides a Flask application for the federated learning REST API.
"""
import logging
from typing import Dict, Any
from flask import Flask, jsonify
from flask_cors import CORS

from src.application.services.server_service import ServerService
from src.application.services.client_service import ClientService
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.presentation.rest.server_controller import ServerController
from src.presentation.rest.client_controller import ClientController
from src.presentation.rest.policy_controller import PolicyController


class ApiApp:
    """
    Flask application for the federated learning REST API.
    
    This class sets up and manages the Flask application with all
    necessary controllers for the federated learning system.
    """
    
    def __init__(self, 
                 server_use_case: FLServerUseCase = None,
                 client_use_case: FLClientUseCase = None,
                 policy_engine: IPolicyEngine = None,
                 logger: logging.Logger = None):
        """
        Initialize the API application.
        
        Args:
            server_use_case: Server use case
            client_use_case: Client use case
            policy_engine: Policy engine
            logger: Logger
        """
        self.app = Flask(__name__)
        self.logger = logger or logging.getLogger(__name__)
        self.server_use_case = server_use_case
        self.client_use_case = client_use_case
        self.policy_engine = policy_engine
        
        # Enable CORS
        CORS(self.app)
        
        # Add error handlers
        self._add_error_handlers()
        
        # Register controllers
        self._register_controllers()
        
        # Add API info route
        self.app.route('/api/info')(self.get_api_info)
    
    def _add_error_handlers(self) -> None:
        """Add error handlers to the Flask app."""
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"error": "Not found"}), 404
        
        @self.app.errorhandler(500)
        def server_error(error):
            return jsonify({"error": "Internal server error"}), 500
    
    def _register_controllers(self) -> None:
        """Register all controllers with the Flask app."""
        # Register server controller if server use case is available
        if self.server_use_case:
            server_controller = ServerController(self.server_use_case, self.logger)
            server_controller.register_blueprint(self.app)
            self.logger.info("Registered server controller")
        
        # Register client controller if client use case is available
        if self.client_use_case:
            client_controller = ClientController(self.client_use_case, self.logger)
            client_controller.register_blueprint(self.app)
            self.logger.info("Registered client controller")
        
        # Register policy controller if policy engine is available
        if self.policy_engine:
            policy_controller = PolicyController(self.policy_engine, self.logger)
            policy_controller.register_blueprint(self.app)
            self.logger.info("Registered policy controller")
    
    def get_api_info(self):
        """
        Get API information.
        
        Returns:
            JSON response with API information
        """
        api_info = {
            "name": "Federated Learning System API",
            "version": "1.0.0",
            "description": "REST API for federated learning system",
            "components": {
                "server": self.server_use_case is not None,
                "client": self.client_use_case is not None,
                "policy_engine": self.policy_engine is not None
            }
        }
        return jsonify(api_info)
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False, **kwargs) -> None:
        """
        Run the Flask application.
        
        Args:
            host: Host to run on
            port: Port to run on
            debug: Whether to run in debug mode
            **kwargs: Additional kwargs to pass to app.run()
        """
        self.logger.info(f"Starting API server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, **kwargs)
    
    def get_app(self) -> Flask:
        """
        Get the Flask application instance.
        
        Returns:
            Flask application
        """
        return self.app 