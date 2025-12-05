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
Policy Engine - Metrics Routes Blueprint

This module contains Flask routes for policy metrics, health checks, and monitoring.
"""

import logging
import time
import datetime
from flask import Blueprint, request, jsonify, g, current_app

logger = logging.getLogger(__name__)

# Create Blueprint
metrics_bp = Blueprint('metrics', __name__)

# Module-level reference to policy engine (set by init_metrics_routes)
_policy_engine = None


def init_metrics_routes(policy_engine):
    """
    Initialize metrics routes with a PolicyEngine instance.
    
    Args:
        policy_engine: The PolicyEngine instance to use for metrics operations
    """
    global _policy_engine
    _policy_engine = policy_engine
    logger.info("Metrics routes initialized")


def _get_policy_engine():
    """Get the policy engine instance from global or Flask g context."""
    pe = _policy_engine
    if pe is None:
        pe = g.get("policy_engine")
    return pe


# ============================================================================
# Health Check Routes
# ============================================================================

@metrics_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    pe = _get_policy_engine()
    return jsonify({
        "status": "ok",
        "version": pe.policy_version if pe else 0
    })


# ============================================================================
# Metrics Routes
# ============================================================================

@metrics_bp.route('/api/v1/metrics', methods=['GET'])
def get_metrics():
    """Return operational metrics for the Policy Engine."""
    pe = _get_policy_engine()
    if pe is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
        
    try:
        # Access policy engine state
        num_policies = len(pe.policies)
        num_enabled = sum(1 for p in pe.policies.values() if p.get('enabled', False))
        history_count = len(pe.policy_history)
        
        # Calculate hourly decision metrics
        current_time = time.time()
        one_hour_ago = current_time - 3600  # 1 hour ago
        
        # Get decisions from the last hour
        decisions_last_hour = [
            d for d in getattr(pe, 'decisions_history', [])
            if d.get('timestamp', 0) >= one_hour_ago
        ]
        
        # Count allowed vs denied decisions in last hour
        allowed_last_hour = sum(1 for d in decisions_last_hour if d.get('result', False))
        denied_last_hour = sum(1 for d in decisions_last_hour if not d.get('result', False))
        
        # Calculate average decision time
        decision_times = [d.get('execution_time', 0) for d in decisions_last_hour if d.get('execution_time')]
        avg_decision_time = sum(decision_times) / len(decision_times) if decision_times else 0.0

        # Get policy application stats with fallback
        app_stats = getattr(pe, 'policy_application_stats', {
            "total_checks": 0,
            "allowed_checks": 0,
            "denied_checks": 0
        })

        metrics = {
            "policy_count": num_policies,
            "enabled_policy_count": num_enabled,
            "policy_version": pe.policy_version,
            "history_event_count": history_count,
            "function_count": len(pe.function_manager.functions),
            "uptime_seconds": time.time() - current_app.start_time if hasattr(current_app, 'start_time') else -1,
            # Add decision metrics for dashboard
            "policy_checks_total": app_stats.get("total_checks", 0),
            "policy_checks_allowed": app_stats.get("allowed_checks", 0),
            "policy_checks_denied": app_stats.get("denied_checks", 0),
            # Add hourly metrics for overview page
            "decisions_last_hour_total": len(decisions_last_hour),
            "decisions_last_hour_allowed": allowed_last_hour,
            "decisions_last_hour_denied": denied_last_hour,
            "avg_decision_time_ms": avg_decision_time,
            "decisions_history_count": len(getattr(pe, 'decisions_history', []))
        }
        logger.debug(f"Returning metrics: {metrics}")
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        # Return basic metrics if there's an error
        return jsonify({
            "policy_count": len(pe.policies) if pe else 0,
            "enabled_policy_count": 0,
            "policy_version": 0,
            "history_event_count": 0,
            "function_count": 0,
            "uptime_seconds": time.time() - current_app.start_time if hasattr(current_app, 'start_time') else -1,
            "policy_checks_total": 0,
            "policy_checks_allowed": 0,
            "policy_checks_denied": 0,
            "decisions_last_hour_total": 0,
            "decisions_last_hour_allowed": 0,
            "decisions_last_hour_denied": 0,
            "avg_decision_time_ms": 0.0,
            "decisions_history_count": 0,
            "error": str(e)
        }), 200


@metrics_bp.route('/metrics', methods=['GET'])
def metrics():
    """Get policy engine metrics with detailed statistics."""
    try:
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
            
        # Basic metrics plus detailed application stats
        metrics_data = {
            "version": "1.0.0",
            "uptime_seconds": time.time() - current_app.start_time if hasattr(current_app, 'start_time') else 0,
            "policy_count": len(pe.policies),
            "enabled_policy_count": sum(1 for p in pe.policies.values() if p.get('enabled', True)),
            "policy_version": pe.policy_version,
            "policy_history_count": len(pe.policy_history),
            "policy_applications_count": len(pe.policy_applications),
            "policy_checks_total": pe.policy_application_stats["total_checks"],
            "policy_checks_allowed": pe.policy_application_stats["allowed_checks"],
            "policy_checks_denied": pe.policy_application_stats["denied_checks"],
            "policy_components": list(pe.policy_application_stats["by_component"].keys()),
            "policy_types": list(pe.policy_application_stats["by_policy_type"].keys()),
            "policy_requesters": list(pe.policy_application_stats["by_requester"].keys()),
            "latest_application_timestamp": pe.policy_applications[-1]["timestamp"] if pe.policy_applications else 0
        }
        
        return jsonify(metrics_data)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500


@metrics_bp.route('/api/v1/policy_metrics', methods=['GET'])
def get_policy_metrics():
    """Get policy metrics for dashboard charts."""
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        pe = _get_policy_engine()
        if pe is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Generate time-series metrics
        metrics = []
        current_time = time.time()
        
        # Parse time range
        if start_time and end_time:
            try:
                start_ts = float(start_time)
                end_ts = float(end_time)
            except (ValueError, TypeError):
                start_ts = current_time - 24 * 3600
                end_ts = current_time
        else:
            start_ts = current_time - 24 * 3600
            end_ts = current_time
        
        # Get actual policy applications from the policy engine
        policy_applications = getattr(pe, 'policy_applications', [])
        
        # Generate hourly metrics based on real data
        interval = 3600  # 1 hour
        timestamp = start_ts
        
        while timestamp <= end_ts:
            hour_start = timestamp
            hour_end = timestamp + interval
            
            hour_applications = [
                app for app in policy_applications
                if hour_start <= app.get('timestamp', 0) < hour_end
            ]
            
            total_evaluations = len(hour_applications)
            allowed_count = sum(1 for app in hour_applications if app.get('result', False))
            denied_count = total_evaluations - allowed_count
            
            eval_times = [app.get('evaluation_time_ms', 0) for app in hour_applications if app.get('evaluation_time_ms')]
            avg_evaluation_time = sum(eval_times) / len(eval_times) if eval_times else 0.0
            
            unique_requesters = len(set(app.get('requester_id', 'unknown') for app in hour_applications))
            
            hour_metrics = {
                "timestamp": timestamp,
                "iso_time": datetime.datetime.fromtimestamp(timestamp).isoformat(),
                "metric_type": "policy_count",
                "metric_name": "active_policies", 
                "metric_value": len([p for p in pe.policies.values() if p.get('enabled', True)]),
                "unit": "count"
            }
            metrics.append(hour_metrics)
            
            if total_evaluations > 0:
                decision_metrics = {
                    "timestamp": timestamp,
                    "iso_time": datetime.datetime.fromtimestamp(timestamp).isoformat(),
                    "metric_type": "decision_count",
                    "metric_name": "total_decisions",
                    "metric_value": total_evaluations,
                    "allowed_count": allowed_count,
                    "denied_count": denied_count,
                    "denial_rate": round(denied_count / total_evaluations * 100, 2) if total_evaluations > 0 else 0,
                    "avg_evaluation_time_ms": round(avg_evaluation_time, 2),
                    "unique_requesters": unique_requesters,
                    "unit": "count"
                }
                metrics.append(decision_metrics)
            
            timestamp += interval
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error generating policy metrics: {e}")
        return jsonify({"error": f"Failed to generate metrics: {str(e)}"}), 500
