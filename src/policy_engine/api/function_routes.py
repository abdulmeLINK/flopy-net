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
Policy Engine - Function Routes Blueprint

This module contains Flask routes for policy function management.
"""

import logging
from flask import Blueprint, request, jsonify, g

logger = logging.getLogger(__name__)

# Create Blueprint
function_bp = Blueprint('functions', __name__)

# Module-level reference to policy engine (set by init_function_routes)
_policy_engine = None


def init_function_routes(policy_engine):
    """
    Initialize function routes with a PolicyEngine instance.
    
    Args:
        policy_engine: The PolicyEngine instance to use for function operations
    """
    global _policy_engine
    _policy_engine = policy_engine
    logger.info("Function routes initialized")


def _get_policy_engine():
    """Get the policy engine instance from global or Flask g context."""
    pe = _policy_engine
    if pe is None:
        pe = g.get("policy_engine")
    return pe


# ============================================================================
# Function CRUD Routes
# ============================================================================

@function_bp.route('/api/v1/functions', methods=['GET'])
def list_functions():
    """List all policy functions."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        functions = pe.function_manager.list_functions()
        return jsonify(functions)
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        return jsonify({"error": str(e)}), 500


@function_bp.route('/api/v1/functions/<function_id>', methods=['GET'])
def get_function(function_id):
    """Get a policy function by ID."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        function = pe.function_manager.get_function(function_id)
        return jsonify(function.to_dict())
    except Exception as e:
        logger.error(f"Error getting function {function_id}: {e}")
        return jsonify({"error": str(e)}), 404


@function_bp.route('/api/v1/functions', methods=['POST'])
def create_function():
    """Create a new policy function."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get('name')
    code = data.get('code')
    description = data.get('description', '')
    metadata = data.get('metadata', {})
    
    if not name or not code:
        return jsonify({"error": "Missing required fields: name, code"}), 400
    
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        function = pe.create_policy_function(name, code, description, metadata)
        return jsonify(function), 201
    except Exception as e:
        logger.error(f"Error creating function: {e}")
        return jsonify({"error": str(e)}), 500


@function_bp.route('/api/v1/functions/<function_id>', methods=['PUT'])
def update_function(function_id):
    """Update a policy function."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
            
        function = pe.function_manager.update_function(
            function_id=function_id,
            name=data.get('name'),
            code=data.get('code'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        return jsonify(function.to_dict())
    except Exception as e:
        logger.error(f"Error updating function {function_id}: {e}")
        return jsonify({"error": str(e)}), 500


@function_bp.route('/api/v1/functions/<function_id>', methods=['DELETE'])
def delete_function(function_id):
    """Delete a policy function."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
            
        success = pe.function_manager.delete_function(function_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error deleting function {function_id}: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Function Validation and Testing Routes
# ============================================================================

@function_bp.route('/api/v1/functions/validate', methods=['POST'])
def validate_function():
    """Validate function code."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    code = data.get('code')
    
    if not code:
        return jsonify({"error": "Missing required field: code"}), 400
    
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
            
        result = pe.validate_function_code(code)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error validating function: {e}")
        return jsonify({"error": str(e)}), 500


@function_bp.route('/api/v1/functions/test', methods=['POST'])
def test_function():
    """Test function code with the given context."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    code = data.get('code')
    context = data.get('context', {})
    
    if not code:
        return jsonify({"error": "Missing required field: code"}), 400
    
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
            
        result = pe.test_function(code, context)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing function: {e}")
        return jsonify({"error": str(e)}), 500
