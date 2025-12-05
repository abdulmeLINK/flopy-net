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
Policy Engine - Policy Routes Blueprint

This module contains Flask routes for policy CRUD operations and policy checks.
"""

import logging
import time
import datetime
from typing import Optional
from flask import Blueprint, request, jsonify, g

from src.policy_engine.policies import PolicyEvaluationError
from src.policy_engine.utils.event_buffer import log_event

logger = logging.getLogger(__name__)

# Create Blueprint
policy_bp = Blueprint('policies', __name__)

# Module-level reference to policy engine (set by init_policy_routes)
_policy_engine = None


def init_policy_routes(policy_engine):
    """
    Initialize policy routes with a PolicyEngine instance.
    
    Args:
        policy_engine: The PolicyEngine instance to use for policy operations
    """
    global _policy_engine
    _policy_engine = policy_engine
    logger.info("Policy routes initialized")


def _get_policy_engine():
    """Get the policy engine instance from global or Flask g context."""
    pe = _policy_engine
    if pe is None:
        pe = g.get("policy_engine")
    return pe


# ============================================================================
# Policy CRUD Routes
# ============================================================================

@policy_bp.route('/api/v1/policies', methods=['GET'])
def list_policies():
    """List all policies."""
    try:
        policy_type = request.args.get('type')
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        policies = pe.list_policies(policy_type)
        return jsonify(policies)
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        return jsonify({"error": str(e)}), 500


@policy_bp.route('/api/v1/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    """Get a policy by ID."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        policy = pe.get_policy(policy_id)
        if policy:
            return jsonify(policy)
        else:
            return jsonify({"error": "Policy not found"}), 404
    except Exception as e:
        logger.error(f"Error getting policy {policy_id}: {e}")
        return jsonify({"error": str(e)}), 500


@policy_bp.route('/api/v1/policies', methods=['POST'])
def create_policy():
    """Create a new policy."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    policy_type = data.get('type')
    policy_data = data.get('data')
    
    if not policy_type or not policy_data:
        return jsonify({"error": "Missing required fields: type, data"}), 400
    
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        policy_id = pe.create_policy(policy_type, policy_data)
        return jsonify({"id": policy_id}), 201
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        return jsonify({"error": str(e)}), 500


@policy_bp.route('/api/v1/policies/<policy_id>', methods=['PUT'])
def update_policy(policy_id):
    """Update a policy."""
    policy_data = request.json
    if not policy_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        pe = _get_policy_engine()
        if not pe:
            raise RuntimeError("Policy Engine instance not found in request context")
             
        success = pe.update_policy(policy_id, policy_data)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Policy not found or update failed"}), 404
            
    except PolicyEvaluationError as e:
        logger.error(f"Policy update error for {policy_id}: {str(e)}")
        return jsonify({"error": f"Policy update error: {str(e)}"}), 400
    except Exception as e:
        logger.exception(f"Unexpected error updating policy {policy_id}: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@policy_bp.route('/api/v1/policies/<policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    """Delete a policy."""
    try:
        pe = _get_policy_engine()
        if not pe:
            raise RuntimeError("Policy Engine instance not found in request context")
             
        success = pe.delete_policy(policy_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Policy not found or delete failed"}), 404
            
    except Exception as e:
        logger.exception(f"Unexpected error deleting policy {policy_id}: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@policy_bp.route('/api/v1/policies/<policy_id>/enable', methods=['POST'])
def enable_policy(policy_id):
    """Enable a policy."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        success = pe.enable_policy(policy_id)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Policy not found"}), 404
    except Exception as e:
        logger.error(f"Error enabling policy {policy_id}: {e}")
        return jsonify({"error": str(e)}), 500


@policy_bp.route('/api/v1/policies/<policy_id>/disable', methods=['POST'])
def disable_policy(policy_id):
    """Disable a policy."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        success = pe.disable_policy(policy_id)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Policy not found"}), 404
    except Exception as e:
        logger.error(f"Error disabling policy {policy_id}: {e}")
        return jsonify({"error": str(e)}), 500


@policy_bp.route('/api/v1/policies/validate', methods=['POST'])
def validate_policy():
    """Validate a policy without creating it."""
    try:
        req_data = request.get_json()
        
        if not req_data:
            return jsonify({"error": "Invalid request: No JSON data"}), 400
        
        policy_data = req_data.get("policy_data") or req_data.get("data")
        if not policy_data:
            return jsonify({"error": "Missing policy_data"}), 400
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        validation_result = pe.validate_policy_data(policy_data)
        
        return jsonify({
            "valid": validation_result["valid"],
            "issues": validation_result["issues"],
            "warnings": validation_result["warnings"]
        }), 200
        
    except Exception as e:
        logger.exception(f"Error validating policy: {str(e)}")
        return jsonify({"error": f"Validation error: {str(e)}"}), 500


# ============================================================================
# Policy Check Routes
# ============================================================================

@policy_bp.route('/api/v1/check', methods=['POST'])
def check_policy():
    """Check if an action is allowed by policies."""
    try:
        req_data = request.get_json()
        
        if not req_data:
            return jsonify({"error": "Invalid request: No JSON data"}), 400
            
        policy_type = req_data.get("policy_type")
        context = req_data.get("context", {})
        
        if not policy_type:
            return jsonify({"error": "Invalid request: Missing policy_type"}), 400
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        try:
            result = pe.check_policy(policy_type, context)
            return jsonify(result), 200
        except Exception as e:
            logger.exception(f"Error checking policy: {str(e)}")
            return jsonify({"error": f"Error checking policy: {str(e)}"}), 500
    except Exception as e:
        logger.exception(f"Exception in check_policy: {str(e)}")
        return jsonify({"error": f"Exception: {str(e)}"}), 500


@policy_bp.route('/check', methods=['GET'])
def simple_check():
    """Simple policy check endpoint."""
    component = request.args.get('component', '')
    action = request.args.get('action', '')
    
    logger.info(f"Received policy check request for {component} to {action}")
    
    # Always allow for now
    return jsonify({
        "allowed": True,
        "reason": "Default allow policy"
    })


# ============================================================================
# Policy History Routes
# ============================================================================

@policy_bp.route('/api/v1/policy_applications', methods=['GET'])
def get_policy_applications():
    """Get history of policy applications with filtering options."""
    pe = _get_policy_engine()
    if pe is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
        
    policy_type = request.args.get('policy_type')
    component = request.args.get('component')
    requester_id = request.args.get('requester_id')
    result = request.args.get('result')
    limit = request.args.get('limit', 100, type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    # Convert result string to boolean if provided
    if result is not None:
        result = result.lower() == 'true' or result.lower() == 'allowed'
    
    applications = pe.get_policy_applications(
        policy_type=policy_type,
        component=component,
        requester_id=requester_id,
        result=result,
        limit=limit,
        start_time=start_time,
        end_time=end_time
    )
    
    return jsonify(applications)


@policy_bp.route('/api/v1/policy_statistics', methods=['GET'])
def get_policy_statistics():
    """Get aggregated statistics about policy applications."""
    pe = _get_policy_engine()
    if pe is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
    return jsonify(pe.policy_application_stats)


@policy_bp.route('/api/v1/policy_decisions', methods=['GET'])
def get_policy_decisions():
    """Get policy decisions with filtering options."""
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        policy_id = request.args.get('policy_id')
        component = request.args.get('component')
        result = request.args.get('result')
        limit = int(request.args.get('limit', 100))
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        decisions = getattr(pe, 'decisions_history', [])
        
        # Apply filters
        if start_time:
            try:
                start_timestamp = float(start_time)
                decisions = [d for d in decisions if d.get('timestamp', 0) >= start_timestamp]
            except (ValueError, TypeError):
                pass
                
        if end_time:
            try:
                end_timestamp = float(end_time)
                decisions = [d for d in decisions if d.get('timestamp', 0) <= end_timestamp]
            except (ValueError, TypeError):
                pass
                
        if policy_id:
            decisions = [d for d in decisions if d.get('policy_id') == policy_id]
            
        if component:
            decisions = [d for d in decisions if d.get('component') == component]
            
        if result:
            result_bool = result.lower() in ['true', '1', 'allow', 'allowed']
            decisions = [d for d in decisions if d.get('result') == result_bool]
        
        decisions = sorted(decisions, key=lambda x: x.get('timestamp', 0), reverse=True)[:limit]
        
        return jsonify(decisions)
        
    except Exception as e:
        logger.error(f"Error getting policy decisions: {e}")
        return jsonify({"error": str(e)}), 500


@policy_bp.route('/api/v1/policy_history', methods=['GET'])
def get_policy_history():
    """
    Get policy modification history.
    
    Query parameters:
        policy_id: Filter by specific policy ID
        action: Filter by action type (create, update, delete, enable, disable)
        limit: Maximum number of history entries to return (default: 100)
        offset: Number of entries to skip (default: 0)
    """
    try:
        policy_id = request.args.get('policy_id')
        action = request.args.get('action')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        history = pe.policy_history.copy()
        
        if policy_id:
            history = [h for h in history if h.get('policy_id') == policy_id]
        
        if action:
            history = [h for h in history if h.get('action') == action]
        
        history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        total_count = len(history)
        paginated_history = history[offset:offset + limit]
        
        for entry in paginated_history:
            if 'timestamp' in entry:
                entry['timestamp_readable'] = datetime.datetime.fromtimestamp(entry['timestamp']).isoformat()
            
            if 'policy_id' in entry and entry['policy_id'] in pe.policies:
                policy = pe.policies[entry['policy_id']]
                entry['policy_name'] = policy.get('name', entry['policy_id'])
                entry['policy_type'] = policy.get('type', 'unknown')
        
        return jsonify({
            "history": paginated_history,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_count
        })
        
    except Exception as e:
        logger.error(f"Error getting policy history: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Policy Version/Cache Routes
# ============================================================================

@policy_bp.route('/api/v1/policy_version', methods=['GET'])
def get_policy_version():
    """Get current policy version for cache validation."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        return jsonify({
            "policy_version": pe.policy_version,
            "last_updated": max([p.get("updated_at", 0) for p in pe.policies.values()] + [0]),
            "total_policies": len(pe.policies),
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting policy version: {e}")
        return jsonify({"error": f"Failed to get policy version: {str(e)}"}), 500


@policy_bp.route('/api/v1/policy_cache_check', methods=['POST'])
def check_policy_cache_validity():
    """Check if client's cached policy version is still valid."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        client_version = data.get("policy_version", 0)
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        is_valid = client_version >= pe.policy_version
        
        response = {
            "cache_valid": is_valid,
            "current_version": pe.policy_version,
            "client_version": client_version,
            "needs_refresh": not is_valid,
            "timestamp": time.time()
        }
        
        if not is_valid:
            response["message"] = f"Client cache is outdated. Current version: {pe.policy_version}, Client version: {client_version}"
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error checking policy cache validity: {e}")
        return jsonify({"error": f"Failed to check cache validity: {str(e)}"}), 500


@policy_bp.route('/api/v1/notify_policy_update', methods=['POST'])
def notify_policy_update():
    """Notify all connected clients about policy updates (webhook-style notification)."""
    try:
        data = request.get_json()
        policy_id = data.get("policy_id") if data else None
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        log_event("POLICY_UPDATE_NOTIFICATION", {
            "policy_id": policy_id,
            "policy_version": pe.policy_version,
            "timestamp": time.time(),
            "notified_by": request.remote_addr
        })
        
        return jsonify({
            "success": True,
            "policy_version": pe.policy_version,
            "message": f"Policy update notification sent for policy: {policy_id}"
        })
        
    except Exception as e:
        logger.error(f"Error sending policy update notification: {e}")
        return jsonify({"error": f"Failed to send notification: {str(e)}"}), 500


# ============================================================================
# Legacy API Routes (for backward compatibility)
# ============================================================================

@policy_bp.route('/api/check_policy', methods=['POST'])
def legacy_check_policy():
    """Legacy endpoint for checking policies."""
    try:
        req_data = request.get_json()
        
        if not req_data:
            return jsonify({"error": "Invalid request: No JSON data"}), 400
            
        # Handle legacy format
        if "policy_type" not in req_data and "type" in req_data:
            req_data["policy_type"] = req_data["type"]
            
        # Route to main check_policy implementation
        return check_policy()
    except Exception as e:
        logger.exception(f"Exception in legacy_check_policy: {str(e)}")
        return jsonify({"error": f"Exception: {str(e)}"}), 500


@policy_bp.route('/api/policies', methods=['GET'])
def legacy_list_policies():
    """Legacy endpoint for listing policies."""
    pe = _get_policy_engine()
    if pe is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
    policy_type = request.args.get('type')
    policies = pe.list_policies(policy_type)
    return jsonify(policies)


@policy_bp.route('/api/policies', methods=['POST'])
def legacy_create_policy():
    """Legacy endpoint for creating policies."""
    return create_policy()
