"""
Server REST API Controller

This module provides REST API endpoints for server management.
"""
import logging
from typing import Dict, Any, List, Optional
from http import HTTPStatus
from flask import Blueprint, request, jsonify

from src.application.services.server_service import ServerService


class ServerController:
    """
    REST API Controller for server operations.
    
    This controller provides endpoints for managing federated learning servers,
    including client management, model aggregation, and training round management.
    """
    
    def __init__(self, server_use_case: ServerService, logger: logging.Logger = None):
        """
        Initialize the server controller.
        
        Args:
            server_use_case: Server use case instance
            logger: Logger instance
        """
        self.server_use_case = server_use_case
        self.logger = logger or logging.getLogger(__name__)
        self.blueprint = Blueprint('server', __name__, url_prefix='/api/server')
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register all routes with the blueprint."""
        self.blueprint.route('/status', methods=['GET'])(self.get_status)
        self.blueprint.route('/clients', methods=['GET'])(self.list_clients)
        self.blueprint.route('/clients/<client_id>', methods=['GET'])(self.get_client)
        self.blueprint.route('/models', methods=['GET'])(self.list_models)
        self.blueprint.route('/models/current', methods=['GET'])(self.get_current_model)
        self.blueprint.route('/models/<model_id>', methods=['GET'])(self.get_model)
        self.blueprint.route('/rounds', methods=['GET'])(self.list_rounds)
        self.blueprint.route('/rounds/current', methods=['GET'])(self.get_current_round)
        self.blueprint.route('/rounds/start', methods=['POST'])(self.start_round)
        self.blueprint.route('/rounds/aggregate', methods=['POST'])(self.aggregate_updates)
        self.blueprint.route('/clients/select', methods=['POST'])(self.select_clients)
    
    def register_blueprint(self, app) -> None:
        """
        Register the blueprint with the Flask app.
        
        Args:
            app: Flask application
        """
        app.register_blueprint(self.blueprint)
    
    def get_status(self):
        """
        Get the server status.
        
        Returns:
            JSON response with server status
        """
        try:
            self.logger.info("Getting server status")
            status = self.server_use_case.get_status()
            
            self.logger.info(f"Server status: {status}")
            return jsonify(status), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error getting server status: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def list_clients(self):
        """
        List all registered clients.
        
        Returns:
            JSON response with list of clients
        """
        try:
            self.logger.info("Listing all clients")
            clients = self.server_use_case.list_clients()
            
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
    
    def get_client(self, client_id: str):
        """
        Get information about a specific client.
        
        Args:
            client_id: Client ID
        
        Returns:
            JSON response with client information
        """
        try:
            self.logger.info(f"Getting client: {client_id}")
            client = self.server_use_case.get_client(client_id)
            
            if not client:
                self.logger.warning(f"Client not found: {client_id}")
                return jsonify({"error": "Client not found"}), HTTPStatus.NOT_FOUND
            
            client_info = {
                "client_id": client.client_id,
                "status": client.status,
                "capabilities": client.capabilities,
                "last_seen": client.last_seen,
                "participation_history": client.participation_history,
                "metrics": client.metrics
            }
            
            self.logger.info(f"Found client: {client_id}")
            return jsonify(client_info), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error getting client: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def list_models(self):
        """
        List all models in the model repository.
        
        Returns:
            JSON response with list of models
        """
        try:
            self.logger.info("Listing all models")
            models = self.server_use_case.list_models()
            
            model_list = [
                {
                    "model_id": model.model_id,
                    "name": model.name,
                    "version": model.version,
                    "created_at": model.created_at,
                    "metrics": model.metrics
                }
                for model in models
            ]
            
            self.logger.info(f"Found {len(model_list)} models")
            return jsonify({"models": model_list}), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def get_current_model(self):
        """
        Get the current global model.
        
        Returns:
            JSON response with current model information
        """
        try:
            self.logger.info("Getting current model")
            model = self.server_use_case.get_current_model()
            
            if not model:
                self.logger.warning("No current model available")
                return jsonify({"error": "No current model available"}), HTTPStatus.NOT_FOUND
            
            model_info = {
                "model_id": model.model_id,
                "name": model.name,
                "version": model.version,
                "created_at": model.created_at,
                "metrics": model.metrics
            }
            
            self.logger.info(f"Current model: {model.model_id}")
            return jsonify(model_info), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error getting current model: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def get_model(self, model_id: str):
        """
        Get information about a specific model.
        
        Args:
            model_id: Model ID
        
        Returns:
            JSON response with model information
        """
        try:
            self.logger.info(f"Getting model: {model_id}")
            model = self.server_use_case.get_model(model_id)
            
            if not model:
                self.logger.warning(f"Model not found: {model_id}")
                return jsonify({"error": "Model not found"}), HTTPStatus.NOT_FOUND
            
            model_info = {
                "model_id": model.model_id,
                "name": model.name,
                "version": model.version,
                "created_at": model.created_at,
                "metrics": model.metrics,
                "parameters": model.parameters if hasattr(model, 'parameters') else None
            }
            
            self.logger.info(f"Found model: {model_id}")
            return jsonify(model_info), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error getting model: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def list_rounds(self):
        """
        List all training rounds.
        
        Returns:
            JSON response with list of rounds
        """
        try:
            self.logger.info("Listing all rounds")
            rounds = self.server_use_case.list_rounds()
            
            round_list = [
                {
                    "round_id": round_info.round_id,
                    "status": round_info.status,
                    "start_time": round_info.start_time,
                    "end_time": round_info.end_time,
                    "client_count": len(round_info.selected_clients),
                    "metrics": round_info.metrics
                }
                for round_info in rounds
            ]
            
            self.logger.info(f"Found {len(round_list)} rounds")
            return jsonify({"rounds": round_list}), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error listing rounds: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def get_current_round(self):
        """
        Get information about the current training round.
        
        Returns:
            JSON response with current round information
        """
        try:
            self.logger.info("Getting current round")
            round_info = self.server_use_case.get_current_round()
            
            if not round_info:
                self.logger.warning("No current round available")
                return jsonify({"error": "No current round available"}), HTTPStatus.NOT_FOUND
            
            round_data = {
                "round_id": round_info.round_id,
                "status": round_info.status,
                "start_time": round_info.start_time,
                "end_time": round_info.end_time,
                "selected_clients": round_info.selected_clients,
                "completed_clients": round_info.completed_clients,
                "metrics": round_info.metrics
            }
            
            self.logger.info(f"Current round: {round_info.round_id}")
            return jsonify(round_data), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error getting current round: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def start_round(self):
        """
        Start a new training round.
        
        Returns:
            JSON response with round information
        """
        try:
            params = request.json or {}
            
            self.logger.info(f"Starting new round with params: {params}")
            round_info = self.server_use_case.start_round(params)
            
            if not round_info:
                self.logger.warning("Failed to start new round")
                return jsonify({"error": "Failed to start new round"}), HTTPStatus.INTERNAL_SERVER_ERROR
            
            round_data = {
                "round_id": round_info.round_id,
                "status": round_info.status,
                "start_time": round_info.start_time,
                "selected_clients": round_info.selected_clients
            }
            
            self.logger.info(f"Started round: {round_info.round_id}")
            return jsonify(round_data), HTTPStatus.CREATED
        
        except Exception as e:
            self.logger.error(f"Error starting round: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def aggregate_updates(self):
        """
        Aggregate model updates for the current round.
        
        Returns:
            JSON response with aggregation result
        """
        try:
            params = request.json or {}
            
            self.logger.info("Aggregating updates for current round")
            result = self.server_use_case.aggregate_updates(params)
            
            if not result:
                self.logger.warning("Failed to aggregate updates")
                return jsonify({"error": "Failed to aggregate updates"}), HTTPStatus.INTERNAL_SERVER_ERROR
            
            self.logger.info(f"Updates aggregated successfully: {result}")
            return jsonify({
                "status": "success",
                "new_model_id": result.get("new_model_id"),
                "metrics": result.get("metrics", {})
            }), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error aggregating updates: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def select_clients(self):
        """
        Select clients for the next round.
        
        Returns:
            JSON response with selected clients
        """
        try:
            params = request.json or {}
            count = params.get("count", 10)
            criteria = params.get("criteria", {})
            
            self.logger.info(f"Selecting {count} clients with criteria: {criteria}")
            selected_clients = self.server_use_case.select_clients(count, criteria)
            
            if not selected_clients:
                self.logger.warning("No clients selected")
                return jsonify({"error": "No clients selected"}), HTTPStatus.BAD_REQUEST
            
            self.logger.info(f"Selected {len(selected_clients)} clients")
            return jsonify({
                "selected_clients": selected_clients
            }), HTTPStatus.OK
        
        except Exception as e:
            self.logger.error(f"Error selecting clients: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR 