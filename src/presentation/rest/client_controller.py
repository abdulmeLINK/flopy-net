"""
Client REST API Controller

This module provides REST API endpoints for client management.
"""
import logging
from typing import Dict, Any, List, Optional
from http import HTTPStatus
from flask import Blueprint, request, jsonify

from src.application.services.client_service import ClientService


class ClientController:
    """
    REST API Controller for client operations.
    
    This controller provides endpoints for managing federated learning clients,
    including registration, model updates, and training operations.
    """
    
    def __init__(self, client_use_case: FLClientUseCase, logger: logging.Logger = None):
        """
        Initialize the client controller.
        
        Args:
            client_use_case: Client use case instance
            logger: Logger instance
        """
        self.client_use_case = client_use_case
        self.logger = logger or logging.getLogger(__name__)
        self.blueprint = Blueprint('client', __name__, url_prefix='/api/client')
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register all routes with the blueprint."""
        self.blueprint.route('/register', methods=['POST'])(self.register_client)
        self.blueprint.route('/status/<client_id>', methods=['GET'])(self.get_client_status)
        self.blueprint.route('/list', methods=['GET'])(self.list_clients)
        self.blueprint.route('/<client_id>/download_model', methods=['GET'])(self.download_model)
        self.blueprint.route('/<client_id>/upload_update', methods=['POST'])(self.upload_update)
        self.blueprint.route('/<client_id>/train', methods=['POST'])(self.train)
        self.blueprint.route('/<client_id>/evaluate', methods=['POST'])(self.evaluate)
    
    def register_blueprint(self, app) -> None:
        """
        Register the blueprint with the Flask app.
        
        Args:
            app: Flask application
        """
        app.register_blueprint(self.blueprint)
    
    def register_client(self):
        """
        Register a new client.
        
        Returns:
            JSON response with client ID
        """
        try:
            client_info = request.json
            if not client_info:
                return jsonify({"error": "Missing client information"}), HTTPStatus.BAD_REQUEST
            
            self.logger.info(f"Registering client with info: {client_info}")
            client_id = self.client_use_case.register_client(client_info)
            
            self.logger.info(f"Client registered with ID: {client_id}")
            return jsonify({"client_id": client_id}), HTTPStatus.CREATED
        
        except Exception as e:
            self.logger.error(f"Error registering client: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def get_client_status(self, client_id: str):
        """
        Get the status of a client.
        
        Args:
            client_id: Client ID
        
        Returns:
            JSON response with client status
        """
        try:
            self.logger.info(f"Getting status for client: {client_id}")
            client = self.client_use_case.get_client(client_id)
            
            if not client:
                self.logger.warning(f"Client not found: {client_id}")
                return jsonify({"error": "Client not found"}), HTTPStatus.NOT_FOUND
            
            status = self.client_use_case.get_client_status(client_id)
            self.logger.info(f"Retrieved status for client {client_id}: {status}")
            
            return jsonify(status), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error getting client status: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def list_clients(self):
        """
        List all registered clients.
        
        Returns:
            JSON response with list of clients
        """
        try:
            self.logger.info("Listing all clients")
            clients = self.client_use_case.list_clients()
            
            client_list = [
                {
                    "client_id": client.client_id,
                    "status": client.status,
                    "capabilities": client.capabilities,
                    "last_seen": client.last_seen,
                }
                for client in clients
            ]
            
            self.logger.info(f"Found {len(client_list)} clients")
            return jsonify({"clients": client_list}), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error listing clients: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def download_model(self, client_id: str):
        """
        Download the current global model.
        
        Args:
            client_id: Client ID
        
        Returns:
            JSON response with model data
        """
        try:
            self.logger.info(f"Client {client_id} requesting model download")
            
            if not self.client_use_case.client_exists(client_id):
                self.logger.warning(f"Client not found: {client_id}")
                return jsonify({"error": "Client not found"}), HTTPStatus.NOT_FOUND
            
            model_data = self.client_use_case.get_current_model(client_id)
            
            if not model_data:
                self.logger.warning("No global model available")
                return jsonify({"error": "No global model available"}), HTTPStatus.NOT_FOUND
            
            self.logger.info(f"Model successfully provided to client {client_id}")
            return jsonify({"model": model_data}), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error downloading model: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def upload_update(self, client_id: str):
        """
        Upload a model update from a client.
        
        Args:
            client_id: Client ID
        
        Returns:
            JSON response with success status
        """
        try:
            update_data = request.json
            if not update_data:
                return jsonify({"error": "Missing update data"}), HTTPStatus.BAD_REQUEST
            
            self.logger.info(f"Received model update from client {client_id}")
            
            if not self.client_use_case.client_exists(client_id):
                self.logger.warning(f"Client not found: {client_id}")
                return jsonify({"error": "Client not found"}), HTTPStatus.NOT_FOUND
            
            success = self.client_use_case.submit_update(client_id, update_data)
            
            if success:
                self.logger.info(f"Update from client {client_id} accepted")
                return jsonify({"status": "Update accepted"}), HTTPStatus.OK
            else:
                self.logger.warning(f"Update from client {client_id} rejected")
                return jsonify({"status": "Update rejected"}), HTTPStatus.BAD_REQUEST
        
        except Exception as e:
            self.logger.error(f"Error uploading update: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def train(self, client_id: str):
        """
        Trigger training on a client.
        
        Args:
            client_id: Client ID
        
        Returns:
            JSON response with training status
        """
        try:
            training_params = request.json or {}
            
            self.logger.info(f"Triggering training for client {client_id}")
            
            if not self.client_use_case.client_exists(client_id):
                self.logger.warning(f"Client not found: {client_id}")
                return jsonify({"error": "Client not found"}), HTTPStatus.NOT_FOUND
            
            training_job = self.client_use_case.start_training(client_id, training_params)
            
            self.logger.info(f"Training started for client {client_id}: {training_job}")
            return jsonify({
                "status": "Training started",
                "training_job": training_job
            }), HTTPStatus.ACCEPTED
        
        except Exception as e:
            self.logger.error(f"Error starting training: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def evaluate(self, client_id: str):
        """
        Trigger evaluation on a client.
        
        Args:
            client_id: Client ID
        
        Returns:
            JSON response with evaluation results
        """
        try:
            eval_params = request.json or {}
            
            self.logger.info(f"Triggering evaluation for client {client_id}")
            
            if not self.client_use_case.client_exists(client_id):
                self.logger.warning(f"Client not found: {client_id}")
                return jsonify({"error": "Client not found"}), HTTPStatus.NOT_FOUND
            
            eval_results = self.client_use_case.evaluate_model(client_id, eval_params)
            
            self.logger.info(f"Evaluation completed for client {client_id}")
            return jsonify({
                "status": "Evaluation completed",
                "results": eval_results
            }), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error during evaluation: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR 