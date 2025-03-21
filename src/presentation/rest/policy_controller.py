"""
Policy REST API Controller

This module provides REST API endpoints for policy management.
"""
import logging
from typing import Dict, Any, List, Optional
from http import HTTPStatus
from flask import Blueprint, request, jsonify

from src.domain.interfaces.policy_engine import IPolicyEngine


class PolicyController:
    """
    REST API controller for policy management.
    
    This controller provides endpoints for managing policies,
    strategies, and runtime rules.
    """
    
    def __init__(self, policy_engine: IPolicyEngine, logger: Optional[logging.Logger] = None):
        """
        Initialize the controller.
        
        Args:
            policy_engine: Policy engine
            logger: Optional logger
        """
        self.policy_engine = policy_engine
        self.logger = logger or logging.getLogger(__name__)
        self.blueprint = Blueprint('policy', __name__, url_prefix='/api/policy')
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register all routes with the blueprint."""
        self.blueprint.route('/status', methods=['GET'])(self.get_status)
        self.blueprint.route('/policies', methods=['GET'])(self.list_policies)
        self.blueprint.route('/policies/<policy_name>', methods=['POST'])(self.register_policy)
        self.blueprint.route('/strategies', methods=['GET'])(self.list_strategies)
        self.blueprint.route('/strategies/<strategy_name>', methods=['POST'])(self.set_strategy)
        self.blueprint.route('/evaluate', methods=['POST'])(self.evaluate_policies)
    
    def register_blueprint(self, app) -> None:
        """
        Register the blueprint with the Flask app.
        
        Args:
            app: Flask application
        """
        app.register_blueprint(self.blueprint)
        self.logger.info("Registered policy controller blueprint")
    
    def get_status(self):
        """
        Get policy engine status.
        
        Returns:
            JSON response with policy engine status
        """
        try:
            status = {
                "enabled": self.policy_engine.enabled,
                "active_strategy": self.policy_engine.get_active_strategy(),
                "policies_count": len(self.policy_engine.policies),
                "runtime_rules_count": len(self.policy_engine.runtime_rules)
            }
            return jsonify(status), HTTPStatus.OK
        except Exception as e:
            self.logger.error(f"Error getting policy engine status: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def list_policies(self):
        """
        List all registered policies.
        
        Returns:
            JSON response with policy list
        """
        try:
            from src.application.policy.registry import list_policies
            
            policies = list_policies()
            return jsonify({"policies": policies}), HTTPStatus.OK
        except Exception as e:
            self.logger.error(f"Error listing policies: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def register_policy(self, policy_name):
        """
        Register a policy with the policy engine.
        
        Args:
            policy_name: Name of the policy to register
            
        Returns:
            JSON response with registration result
        """
        try:
            policy_config = request.json or {}
            
            result = self.policy_engine.register_policy(policy_name, policy_config)
            
            if result:
                return jsonify({"status": "registered", "policy_name": policy_name}), HTTPStatus.OK
            else:
                return jsonify({"status": "error", "message": f"Failed to register policy {policy_name}"}), HTTPStatus.BAD_REQUEST
        except Exception as e:
            self.logger.error(f"Error registering policy: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def list_strategies(self):
        """
        List all available strategies.
        
        Returns:
            JSON response with strategy list
        """
        try:
            from src.application.fl_strategies.registry import list_strategies
            
            strategies = list_strategies()
            return jsonify({"strategies": strategies}), HTTPStatus.OK
        except Exception as e:
            self.logger.error(f"Error listing strategies: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def set_strategy(self, strategy_name):
        """
        Set the active strategy.
        
        Args:
            strategy_name: Name of the strategy to set
            
        Returns:
            JSON response with set result
        """
        try:
            strategy_config = request.json or {}
            
            result = self.policy_engine.set_strategy(strategy_name, strategy_config)
            
            if result:
                return jsonify({"status": "set", "strategy_name": strategy_name}), HTTPStatus.OK
            else:
                return jsonify({"status": "error", "message": f"Failed to set strategy {strategy_name}"}), HTTPStatus.BAD_REQUEST
        except Exception as e:
            self.logger.error(f"Error setting strategy: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    def evaluate_policies(self):
        """
        Evaluate all registered policies with the given context.
        
        Returns:
            JSON response with policy evaluation results
        """
        try:
            context = request.json
            
            if not context:
                return jsonify({"error": "Context is required"}), HTTPStatus.BAD_REQUEST
            
            results = self.policy_engine.evaluate_policies(context)
            
            return jsonify({"results": results}), HTTPStatus.OK
        except Exception as e:
            self.logger.error(f"Error evaluating policies: {e}")
            return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR 