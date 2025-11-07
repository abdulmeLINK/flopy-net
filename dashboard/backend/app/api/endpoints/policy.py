#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List, Dict, Any, Optional
import logging
import httpx
import json
from datetime import datetime, timedelta
from pydantic import BaseModel

# Configure router without redirects
router = APIRouter(redirect_slashes=False)
logger = logging.getLogger(__name__)



# Policy models for validation
class PolicyRule(BaseModel):
    action: str
    description: str
    match: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None

class PolicyRequest(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    description: str
    priority: int
    rules: List[PolicyRule]

class PolicyValidationRequest(BaseModel):
    policy: Dict[str, Any]

# Dependency to get policy engine client
async def get_policy_client(request: Request):
    """Dependency to get the policy client from app state."""
    if not hasattr(request.app.state, 'policy_client') or request.app.state.policy_client is None:
        from app.services.policy_client import AsyncPolicyEngineClient
        request.app.state.policy_client = AsyncPolicyEngineClient()
    return request.app.state.policy_client

async def get_policy_engine_url(request: Request) -> str:
    """Get the policy engine URL from app settings."""
    policy_client = await get_policy_client(request)
    return policy_client.base_url

@router.get("/status")
@router.get("/status/")
async def get_policy_status_summary(
    request: Request
):
    """Get policy status summary for overview page."""
    try:
        policy_client = await get_policy_client(request)
        
        # Get metrics directly from policy engine
        metrics = await policy_client.get_metrics()
        
        # Get active policies count
        policies = await policy_client.get_policies()
        active_policies = len([p for p in policies if p.get("enabled", True)])
        
        # Get policy decisions from last hour from policy engine
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        decision_params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": 1000
        }
        
        decisions = await policy_client.get_policy_decisions(decision_params)
        
        # Calculate metrics from decisions
        allow_count = len([d for d in decisions if d.get("decision") == "allow" or d.get("result", True)])
        deny_count = len([d for d in decisions if d.get("decision") == "deny" or not d.get("result", True)])
        
        # Calculate average execution time
        execution_times = [d.get("execution_time", 0) for d in decisions if d.get("execution_time")]
        avg_decision_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Get policy engine status
        try:
            engine_status = await policy_client.get_status()
            status = "active" if engine_status.get("status") == "ok" else "error"
        except:
            status = "error"
        
        return {
            "connected": True,
            "active_policies": active_policies,
            "decisions_last_hour": allow_count + deny_count,
            "allow_count_last_hour": allow_count,
            "deny_count_last_hour": deny_count,
            "avg_decision_time_ms": avg_decision_time,
            "status": status,
            "policy_count": metrics.get("policy_count", active_policies),
            "total_evaluations": metrics.get("policy_checks_total", allow_count + deny_count)
        }
        
    except Exception as e:
        logger.error(f"Error fetching policy status summary: {str(e)}")
        # Return basic data to prevent OverviewPage from breaking
        return {
            "connected": False,
            "active_policies": 0,
            "decisions_last_hour": 0,
            "allow_count_last_hour": 0,
            "deny_count_last_hour": 0,
            "avg_decision_time_ms": 0,
            "status": "error",
            "error": str(e)
        }

@router.get("/metrics")
@router.get("/metrics/")
async def get_policy_engine_metrics_data(
    request: Request
):
    """Get metrics from the policy engine."""
    try:
        policy_client = await get_policy_client(request)
        metrics = await policy_client.get_metrics()
        return metrics
            
    except Exception as e:
        logger.error(f"Error fetching policy engine metrics: {str(e)}")
        return {
            "policy_count": 0,
            "enabled_policy_count": 0,
            "policy_version": 0,
            "policy_checks_total": 0,
            "policy_checks_allowed": 0,
            "policy_checks_denied": 0,
            "status": "disconnected",
            "error": str(e)
        }

@router.get("/decisions")
@router.get("/decisions/")
async def get_policy_decisions_data(
    request: Request,
    policy_id: Optional[str] = None,
    component: Optional[str] = None,
    result: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = 100,
    include_details: Optional[bool] = True
):
    """Get policy decisions with optional filtering and enhanced details."""
    try:
        policy_client = await get_policy_client(request)
        
        params = {}
        if policy_id:
            params["policy_id"] = policy_id
        if component:
            params["component"] = component
        if result:
            params["result"] = result
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        
        decisions = await policy_client.get_policy_decisions(params)
        
        # Enhance decisions with additional metadata for dashboard
        enhanced_decisions = []
        for decision in decisions:
            enhanced_decision = {
                **decision,
                # Ensure consistent field names
                "id": decision.get("id", decision.get("request_id", str(hash(str(decision))))),
                "policy_name": decision.get("policy_name", decision.get("policy_id", "Unknown")),
                "timestamp": decision.get("timestamp", decision.get("created_at")),
                "decision": decision.get("decision", "allow" if decision.get("allowed", True) else "deny"),
                "result": decision.get("result", decision.get("allowed", True)),
                
                # Add enhanced fields from new policy engine
                "rule_evaluations": decision.get("rule_evaluations", []),
                "applied_actions": decision.get("applied_actions", []),
                "decision_path": decision.get("decision_path", []),
                "evaluation_details": decision.get("evaluation_details", {}),
                "match_details": decision.get("match_details", []),
                
                # Calculate summary statistics
                "total_rules_evaluated": len(decision.get("rule_evaluations", [])),
                "matched_rules_count": sum(len(policy.get("matched_rules", [])) for policy in decision.get("rule_evaluations", [])),
                "policies_involved": len(decision.get("rule_evaluations", [])),
                "actions_count": len(decision.get("applied_actions", [])),
                
                # Categorize decision complexity with more nuanced logic
                "complexity": _calculate_decision_complexity(decision),
                
                # Extract primary action
                "primary_action": decision.get("applied_actions", [{}])[0].get("action", "unknown") if decision.get("applied_actions") else "none"
            }
            
            # Add violation summary
            violations = decision.get("violations", [])
            if violations:
                enhanced_decision["violation_summary"] = {
                    "count": len(violations),
                    "primary_violation": violations[0] if violations else None,
                    "violation_types": list(set(v.get("rule_type", "unknown") for v in violations))
                }
            
            enhanced_decisions.append(enhanced_decision)
        
        return enhanced_decisions
            
    except Exception as e:
        logger.error(f"Error fetching policy decisions: {str(e)}")
        # NO FALLBACKS - let the error surface so we can debug properly
        raise HTTPException(status_code=502, detail=f"Failed to fetch policy decisions: {str(e)}")

@router.get("/decisions/{decision_id}")
async def get_policy_decision_details(
    decision_id: str,
    request: Request
):
    """Get detailed information about a specific policy decision."""
    try:
        policy_client = await get_policy_client(request)
        
        decision = await policy_client.get_policy_decision_details(decision_id)
        
        # Enhance with detailed analysis
        enhanced_decision = {
            **decision,
            "analysis": {
                "decision_complexity": _analyze_decision_complexity(decision),
                "rule_analysis": _analyze_rule_evaluations(decision.get("rule_evaluations", [])),
                "action_analysis": _analyze_applied_actions(decision.get("applied_actions", [])),
                "performance_metrics": _extract_performance_metrics(decision)
            }
        }
        
        return enhanced_decision
            
    except Exception as e:
        logger.error(f"Error fetching policy decision {decision_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/rule-performance")
@router.get("/analytics/rule-performance/")
async def get_rule_performance_analytics(
    request: Request,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    policy_id: Optional[str] = None
):
    """Get analytics on rule performance and effectiveness."""
    try:
        policy_client = await get_policy_client(request)
        
        params = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if policy_id:
            params["policy_id"] = policy_id
            
        analytics = await policy_client.get_rule_performance_analytics(params)
        return analytics
            
    except Exception as e:
        logger.error(f"Error fetching rule performance analytics: {str(e)}")
        # NO FALLBACKS - let the error surface so we can debug properly
        raise HTTPException(status_code=502, detail=f"Failed to fetch rule performance analytics: {str(e)}")

@router.get("/analytics/decision-patterns")
@router.get("/analytics/decision-patterns/")
async def get_decision_pattern_analytics(
    request: Request,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get analytics on decision patterns and trends."""
    try:
        policy_client = await get_policy_client(request)
        
        params = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
            
        analytics = await policy_client.get_decision_pattern_analytics(params)
        return analytics
            
    except Exception as e:
        logger.error(f"Error fetching decision pattern analytics: {str(e)}")
        # NO FALLBACKS - let the error surface so we can debug properly
        raise HTTPException(status_code=502, detail=f"Failed to fetch decision pattern analytics: {str(e)}")

# Helper functions for decision analysis
def _calculate_decision_complexity(decision: Dict[str, Any]) -> str:
    """Calculate decision complexity based on multiple factors."""
    rule_evaluations = decision.get("rule_evaluations", [])
    applied_actions = decision.get("applied_actions", [])
    evaluation_details = decision.get("evaluation_details", {})
    
    # Count total rules evaluated across all policies
    total_rules = evaluation_details.get("evaluated_rules", 0)
    if total_rules == 0:
        total_rules = sum(len(policy.get("rules_evaluated", [])) for policy in rule_evaluations)
    
    # Count matched rules
    matched_rules = evaluation_details.get("matched_rules", 0)
    if matched_rules == 0:
        matched_rules = sum(len(policy.get("matched_rules", [])) for policy in rule_evaluations)
    
    # Calculate complexity score
    complexity_score = 0
    
    # Factor 1: Number of policies involved
    policies_count = len(rule_evaluations)
    if policies_count > 5:
        complexity_score += 3
    elif policies_count > 2:
        complexity_score += 2
    elif policies_count > 1:
        complexity_score += 1
    
    # Factor 2: Total rules evaluated
    if total_rules > 20:
        complexity_score += 3
    elif total_rules > 10:
        complexity_score += 2
    elif total_rules > 5:
        complexity_score += 1
    
    # Factor 3: Number of matched rules (indicates conflicts/violations)
    if matched_rules > 10:
        complexity_score += 3
    elif matched_rules > 5:
        complexity_score += 2
    elif matched_rules > 2:
        complexity_score += 1
    
    # Factor 4: Number of applied actions
    actions_count = len(applied_actions)
    if actions_count > 10:
        complexity_score += 2
    elif actions_count > 5:
        complexity_score += 1
    
    # Factor 5: Evaluation time (if available)
    evaluation_time = decision.get("evaluation_time", 0)
    if evaluation_time > 1000:  # > 1 second
        complexity_score += 2
    elif evaluation_time > 100:  # > 100ms
        complexity_score += 1
    
    # Factor 6: Presence of violations
    violations = decision.get("violations", [])
    if len(violations) > 5:
        complexity_score += 2
    elif len(violations) > 0:
        complexity_score += 1
    
    # Determine complexity level
    if complexity_score >= 10:
        return "very_complex"
    elif complexity_score >= 6:
        return "complex"
    elif complexity_score >= 3:
        return "moderate"
    else:
        return "simple"

def _analyze_decision_complexity(decision: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the complexity of a policy decision."""
    rule_evaluations = decision.get("rule_evaluations", [])
    applied_actions = decision.get("applied_actions", [])
    
    total_rules = sum(len(policy.get("rules_evaluated", [])) for policy in rule_evaluations)
    matched_rules = sum(len(policy.get("matched_rules", [])) for policy in rule_evaluations)
    
    complexity_score = 0
    if total_rules > 10:
        complexity_score += 3
    elif total_rules > 5:
        complexity_score += 2
    elif total_rules > 1:
        complexity_score += 1
    
    if len(rule_evaluations) > 3:
        complexity_score += 2
    elif len(rule_evaluations) > 1:
        complexity_score += 1
    
    if len(applied_actions) > 5:
        complexity_score += 2
    elif len(applied_actions) > 2:
        complexity_score += 1
    
    complexity_level = "simple"
    if complexity_score >= 6:
        complexity_level = "very_complex"
    elif complexity_score >= 4:
        complexity_level = "complex"
    elif complexity_score >= 2:
        complexity_level = "moderate"
    
    return {
        "complexity_score": complexity_score,
        "complexity_level": complexity_level,
        "total_rules_evaluated": total_rules,
        "matched_rules": matched_rules,
        "policies_involved": len(rule_evaluations),
        "actions_applied": len(applied_actions)
    }

def _analyze_rule_evaluations(rule_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze rule evaluation patterns."""
    if not rule_evaluations:
        return {"total_policies": 0, "rule_statistics": {}}
    
    rule_stats = {
        "total_policies": len(rule_evaluations),
        "total_rules": 0,
        "matched_rules": 0,
        "rule_types": {},
        "evaluation_times": [],
        "policy_priorities": []
    }
    
    for policy_eval in rule_evaluations:
        rules_evaluated = policy_eval.get("rules_evaluated", [])
        matched_rules = policy_eval.get("matched_rules", [])
        
        rule_stats["total_rules"] += len(rules_evaluated)
        rule_stats["matched_rules"] += len(matched_rules)
        rule_stats["evaluation_times"].append(policy_eval.get("evaluation_time_ms", 0))
        rule_stats["policy_priorities"].append(policy_eval.get("priority", 0))
        
        for rule in rules_evaluated:
            rule_type = rule.get("rule_type", "unknown")
            if rule_type not in rule_stats["rule_types"]:
                rule_stats["rule_types"][rule_type] = {"total": 0, "matched": 0}
            rule_stats["rule_types"][rule_type]["total"] += 1
            if rule.get("matched", False):
                rule_stats["rule_types"][rule_type]["matched"] += 1
    
    # Calculate averages
    if rule_stats["evaluation_times"]:
        rule_stats["average_evaluation_time"] = sum(rule_stats["evaluation_times"]) / len(rule_stats["evaluation_times"])
    
    return rule_stats

def _analyze_applied_actions(applied_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze applied actions patterns."""
    if not applied_actions:
        return {"total_actions": 0, "action_distribution": {}}
    
    action_stats = {
        "total_actions": len(applied_actions),
        "action_distribution": {},
        "policies_with_actions": set(),
        "action_categories": {
            "security": 0,
            "performance": 0,
            "compliance": 0,
            "operational": 0
        }
    }
    
    # Categorize actions
    security_actions = {"deny", "block", "quarantine", "isolate", "audit", "monitor"}
    performance_actions = {"throttle", "boost", "tune", "adjust", "scale", "optimize"}
    compliance_actions = {"validate", "record", "inspect", "authorize", "verify"}
    operational_actions = {"configure", "retry", "backup", "redirect", "fallback"}
    
    for action in applied_actions:
        action_type = action.get("action", "unknown")
        policy_id = action.get("policy_id")
        
        if action_type not in action_stats["action_distribution"]:
            action_stats["action_distribution"][action_type] = 0
        action_stats["action_distribution"][action_type] += 1
        
        if policy_id:
            action_stats["policies_with_actions"].add(policy_id)
        
        # Categorize action
        if action_type in security_actions:
            action_stats["action_categories"]["security"] += 1
        elif action_type in performance_actions:
            action_stats["action_categories"]["performance"] += 1
        elif action_type in compliance_actions:
            action_stats["action_categories"]["compliance"] += 1
        elif action_type in operational_actions:
            action_stats["action_categories"]["operational"] += 1
    
    action_stats["unique_policies_with_actions"] = len(action_stats["policies_with_actions"])
    action_stats["policies_with_actions"] = list(action_stats["policies_with_actions"])
    
    return action_stats

def _extract_performance_metrics(decision: Dict[str, Any]) -> Dict[str, Any]:
    """Extract performance metrics from decision."""
    evaluation_details = decision.get("evaluation_details", {})
    
    return {
        "total_evaluation_time": decision.get("evaluation_time", 0),
        "policies_evaluated": evaluation_details.get("total_policies", 0),
        "rules_evaluated": evaluation_details.get("evaluated_rules", 0),
        "matched_rules": evaluation_details.get("matched_rules", 0),
        "efficiency_ratio": (
            evaluation_details.get("matched_rules", 0) / max(evaluation_details.get("evaluated_rules", 1), 1)
        ),
        "decision_path_length": len(decision.get("decision_path", [])),
        "violations_count": len(decision.get("violations", []))
    }

@router.get("/metrics/timeseries")
@router.get("/metrics/timeseries/")
async def get_policy_metrics_timeseries(
    request: Request,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get policy metrics for charts from the collector."""
    try:
        # Import collector client
        from app.services.collector_client import CollectorApiClient
        
        collector = CollectorApiClient()
        
        # Build parameters for the collector request
        params = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
            
        # Get policy_count metrics from the collector
        policy_count_data = await collector.get_metrics(
            params={**params, "type": "policy_count"},
            limit=1000
        )
        
        # Get decision_count metrics from the collector  
        decision_count_data = await collector.get_metrics(
            params={**params, "type": "decision_count"},
            limit=1000
        )
        
        # Process and combine the metrics with proper metric_type fields
        all_metrics = []
        
        # Process policy_count metrics
        if policy_count_data and 'metrics' in policy_count_data:
            for metric in policy_count_data['metrics']:
                if isinstance(metric.get('data'), dict):
                    # Extract the actual time-series data from the 'data' field
                    metric_data = metric['data'].copy()
                    # Add the metric_type from the collector response
                    metric_data['metric_type'] = metric.get('metric_type', 'policy_count')
                    # Ensure we have the basic required fields
                    if 'timestamp' in metric_data:
                        all_metrics.append(metric_data)
        
        # Process decision_count metrics
        if decision_count_data and 'metrics' in decision_count_data:
            for metric in decision_count_data['metrics']:
                if isinstance(metric.get('data'), dict):
                    # Extract the actual time-series data from the 'data' field
                    metric_data = metric['data'].copy()
                    # Add the metric_type from the collector response
                    metric_data['metric_type'] = metric.get('metric_type', 'decision_count')
                    
                    # Normalize decision_count field names to match frontend expectations
                    if 'allowed' in metric_data and 'allowed_count' not in metric_data:
                        metric_data['allowed_count'] = metric_data['allowed']
                    if 'denied' in metric_data and 'denied_count' not in metric_data:
                        metric_data['denied_count'] = metric_data['denied']
                    if 'total' in metric_data and 'total_evaluations' not in metric_data:
                        metric_data['total_evaluations'] = metric_data['total']
                    
                    # Ensure we have the basic required fields
                    if 'timestamp' in metric_data:
                        all_metrics.append(metric_data)
        
        # Sort by timestamp (most recent first)
        all_metrics.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        logger.info(f"Returning {len(all_metrics)} metrics with metric_type fields")
        return all_metrics
        
    except Exception as e:
        logger.error(f"Error fetching policy metrics timeseries: {str(e)}")
        return []

@router.get("/policies")
@router.get("/policies/")
async def get_policies(
    request: Request,
    policy_type: Optional[str] = None
):
    """Get list of policies from policy engine."""
    try:
        policy_client = await get_policy_client(request)
        
        # Get all policies (the client doesn't filter by type currently)
        policies = await policy_client.get_policies()
        
        # Filter by type if specified
        if policy_type:
            policies = [p for p in policies if p.get("type") == policy_type]
        
        # Ensure proper field mapping for dashboard
        for policy in policies:
            if "created_at" not in policy and "timestamp" in policy:
                policy["created_at"] = policy["timestamp"]
            if "rule_type" not in policy and "type" in policy:
                policy["rule_type"] = policy["type"]
            if "status" not in policy:
                policy["status"] = "active" if policy.get("enabled", True) else "inactive"
                
        return policies
        
    except Exception as e:
        logger.error(f"Error fetching policies: {str(e)}")
        # NO FALLBACKS - let the error surface so we can debug properly
        raise HTTPException(status_code=502, detail=f"Failed to fetch policies: {str(e)}")

@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: str,
    request: Request
):
    """Get a specific policy by ID."""
    try:
        policy_client = await get_policy_client(request)
        
        policy = await policy_client.get_policy(policy_id)
        return policy
            
    except Exception as e:
        if "404" in str(e) or "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Policy not found")
        logger.error(f"Error fetching policy {policy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies")
async def create_policy(
    policy_request: PolicyRequest,
    request: Request
):
    """Create a new policy."""
    try:
        policy_client = await get_policy_client(request)
        
        # Convert pydantic model to dict and format for policy engine
        policy_data = {
            "type": policy_request.type,
            "data": {
                "id": policy_request.id or f"{policy_request.type}-{policy_request.name.lower().replace(' ', '-')}",
                "name": policy_request.name,
                "type": policy_request.type,
                "description": policy_request.description,
                "priority": policy_request.priority,
                "rules": [rule.dict() for rule in policy_request.rules]
            }
        }
        
        policy = await policy_client.create_policy(policy_data)
        return policy
            
    except Exception as e:
        logger.error(f"Error creating policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    policy_request: PolicyRequest,
    request: Request
):
    """Update an existing policy."""
    try:
        policy_client = await get_policy_client(request)
        
        # Convert pydantic model to dict for policy engine
        policy_data = {
            "id": policy_id,
            "name": policy_request.name,
            "type": policy_request.type,
            "description": policy_request.description,
            "priority": policy_request.priority,
            "rules": [rule.dict() for rule in policy_request.rules]
        }
        
        policy = await policy_client.update_policy(policy_id, policy_data)
        
        # Trigger policy refresh notification to all components
        try:
            await policy_client.notify_policy_update(policy_id)
            logger.info(f"Policy update notification sent for policy {policy_id}")
        except Exception as e:
            logger.warning(f"Failed to send policy update notification for {policy_id}: {e}")
            # Don't fail the update if notification fails
        
        return policy
            
    except Exception as e:
        logger.error(f"Error updating policy {policy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    request: Request
):
    """Delete a policy."""
    try:
        policy_client = await get_policy_client(request)
        
        await policy_client.delete_policy(policy_id)
        return {"success": True}
            
    except Exception as e:
        logger.error(f"Error deleting policy {policy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies/{policy_id}/enable")
async def enable_policy(
    policy_id: str,
    request: Request
):
    """Enable a policy."""
    try:
        policy_client = await get_policy_client(request)
        
        await policy_client.enable_policy(policy_id)
        return {"success": True}
            
    except Exception as e:
        logger.error(f"Error enabling policy {policy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies/{policy_id}/disable")
async def disable_policy(
    policy_id: str,
    request: Request
):
    """Disable a policy."""
    try:
        policy_client = await get_policy_client(request)
        
        await policy_client.disable_policy(policy_id)
        return {"success": True}
            
    except Exception as e:
        logger.error(f"Error disabling policy {policy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_policy(
    validation_request: PolicyValidationRequest,
    request: Request
):
    """Validate a policy structure."""
    try:
        # Basic validation
        policy = validation_request.policy
        errors = []
        
        # Required fields validation
        required_fields = ["name", "type", "description", "priority", "rules"]
        for field in required_fields:
            if field not in policy:
                errors.append(f"Missing required field: {field}")
        
        # Type validation
        if "priority" in policy and not isinstance(policy["priority"], (int, float)):
            errors.append("Priority must be a number")
            
        if "rules" in policy:
            if not isinstance(policy["rules"], list):
                errors.append("Rules must be an array")
            else:
                for i, rule in enumerate(policy["rules"]):
                    if not isinstance(rule, dict):
                        errors.append(f"Rule {i} must be an object")
                        continue
                    if "action" not in rule:
                        errors.append(f"Rule {i} missing required field: action")
                    if "match" not in rule:
                        errors.append(f"Rule {i} missing required field: match")
        
        # Return validation result
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []
        }
            
    except Exception as e:
        logger.error(f"Error validating policy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version")
async def get_policy_version(
    request: Request
):
    """Get current policy version for cache validation."""
    try:
        policy_client = await get_policy_client(request)
        version_info = await policy_client.get_policy_version()
        return version_info
    except Exception as e:
        logger.error(f"Error fetching policy version: {str(e)}")
        # Return a default version if policy engine doesn't support versioning
        return {
            "version": 1,
            "timestamp": "unknown"
        }

@router.post("/cache-check")
async def check_policy_cache_validity(
    request: Request,
    cache_request: dict
):
    """Check if client's cached policy version is still valid."""
    try:
        policy_client = await get_policy_client(request)
        client_version = cache_request.get("policy_version", 0)
        
        cache_check = await policy_client.check_policy_cache_validity(client_version)
        return cache_check
    except Exception as e:
        logger.error(f"Error checking policy cache validity: {str(e)}")
        # Return cache invalid to force refresh
        return {
            "valid": False,
            "current_version": 1,
            "client_version": client_version,
            "needs_refresh": True
        }

@router.get("/history")
@router.get("/history/")
async def get_policy_history(
    request: Request,
    policy_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0
):
    """Get policy modification history with optional filtering."""
    try:
        policy_client = await get_policy_client(request)
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if policy_id:
            params["policy_id"] = policy_id
        if action:
            params["action"] = action
        
        # Forward the request to the policy engine
        history = await policy_client.get_policy_history(params)
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching policy history: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch policy history: {str(e)}")