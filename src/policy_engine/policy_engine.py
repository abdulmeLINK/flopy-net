"""
Policy Engine for federated learning.
"""

import os
import sys
import json
import time
import logging
import uuid
import datetime
import collections
import threading
from typing import Dict, List, Any, Optional, Union
import hashlib

# Temporarily comment out this import
# from core.interfaces.policy_engine import IPolicyEngine
import requests
from flask import Flask, jsonify, request

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Changed from INFO to DEBUG
logger = logging.getLogger(__name__)

# Create a placeholder for the interface
class IPolicyEngine:
    """Temporary placeholder for the IPolicyEngine interface"""
    pass

class PolicyEngine(IPolicyEngine):
    """
    Policy Engine for federated learning.
    
    The policy engine is responsible for applying policies to the federated learning process,
    including client selection, data privacy, and network optimization.
    """
    
    # Class-level event buffer for simplicity (since Flask routes create new instances)
    _event_buffer = collections.deque(maxlen=1000)  # Store up to 1000 recent events
    _buffer_lock = threading.Lock()
    
    def __init__(self, policy_file: str = None):
        """
        Initialize the policy engine.
        
        Args:
            policy_file: Path to the policy file
        """
        self.policies = {}
        self.policy_file = policy_file or os.environ.get('POLICY_FILE', os.path.join('config', 'policies', 'policies.json'))
        self.load_policies()
        logger.info(f"PolicyEngine initialized with {len(self.policies)} policies")
        
        # Log engine start event
        logger.debug("Logging ENGINE_START event")
        self._log_event("ENGINE_START", {})
        logger.debug(f"Event buffer now has {len(PolicyEngine._event_buffer)} events")
    
    def _log_event(self, event_type: str, details: Dict[str, Any]):
        """
        Log an event to the event buffer.
        
        Args:
            event_type: Type of event (see event schema)
            details: Event-specific details dictionary
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_component": "POLICY_ENGINE",
            "event_type": event_type,
            "details": details
        }
        
        logger.debug(f"Adding event to buffer: {event_type} (id: {event['event_id']})")
        with PolicyEngine._buffer_lock:
            PolicyEngine._event_buffer.append(event)
            logger.debug(f"Event buffer size is now {len(PolicyEngine._event_buffer)}")
        
        logger.debug(f"Logged event: {event['event_id']} - {event_type}")
    
    def load_policies(self) -> None:
        """Load policies from the policy file."""
        try:
            if os.path.exists(self.policy_file):
                with open(self.policy_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'policies' in data:
                        self.policies = data['policies']
                    elif isinstance(data, dict):
                        self.policies = data
                    else:
                        self.policies = {}
                    logger.info(f"Loaded {len(self.policies)} policies from {self.policy_file}")
                    
                    # Log policy loaded event
                    for policy_id in self.policies:
                        self._log_event("POLICY_LOADED", {
                            "policy_id": policy_id,
                            "source": self.policy_file
                        })
            else:
                logger.warning(f"Policy file {self.policy_file} not found")
                self.policies = {}
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            self.policies = {}
            # Log policy error event
            self._log_event("POLICY_ERROR", {
                "error_message": f"Failed to load policies from {self.policy_file}: {str(e)}",
                "context": "during load"
            })
            
    def save_policies(self) -> None:
        """Save policies to the policy file."""
        try:
            with open(self.policy_file, 'w') as f:
                json.dump({'policies': self.policies}, f, indent=2)
            logger.info(f"Saved {len(self.policies)} policies to {self.policy_file}")
        except Exception as e:
            logger.error(f"Error saving policies: {e}")
    
    def register_policy(self, policy) -> None:
        """
        Register a policy with the engine.
        
        Args:
            policy: Policy to register
        """
        self.policies[policy.policy_id] = policy
        # Clear cache when policies change
        self.policy_cache = {}
        logger.info(f"Registered policy {policy.policy_id} ({policy.name})")
    
    def unregister_policy(self, policy_id: str) -> bool:
        """
        Unregister a policy from the engine.
        
        Args:
            policy_id: ID of the policy to unregister
            
        Returns:
            True if the policy was unregistered, False otherwise
        """
        if policy_id in self.policies:
            del self.policies[policy_id]
            # Clear cache when policies change
            self.policy_cache = {}
            logger.info(f"Unregistered policy {policy_id}")
            return True
        
        logger.warning(f"Policy {policy_id} not found, could not unregister")
        return False
    
    def get_policy(self, policy_id: str) -> Optional[Any]:
        """
        Get a policy by ID.
        
        Args:
            policy_id: ID of the policy to get
            
        Returns:
            The policy, or None if not found
        """
        return self.policies.get(policy_id)
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a specific action is allowed by policies.
        
        Args:
            policy_type: Type of policy to check
            context: Context data for policy evaluation
            
        Returns:
            Policy result with allowed flag and reason
        """
        start_time = time.time()
        
        # Log policy evaluation request event
        request_context = {k: v for k, v in context.items() if k not in ['timestamp', 'signature']}
        self._log_event("POLICY_EVAL_REQUEST", {
            "request_id": str(uuid.uuid4()),
            "action": policy_type,
            "context": request_context
        })
        
        # Temporarily comment out the import
        # from core.policies.policy import Policy
        
        # Create a simple Policy class for testing
        class Policy:
            def __init__(self, policy_id, policy_data):
                self.id = policy_id
                self.data = policy_data
                
            def evaluate(self, context):
                """Simple evaluation that always returns allowed=True"""
                return {
                    'allowed': True,
                    'reason': 'Temporary policy implementation for testing'
                }
        
        # Get all enabled policies of the specified type
        policies = [
            Policy(pid, pdata) 
            for pid, pdata in self.policies.items() 
            if pdata['type'] == policy_type and pdata.get('enabled', True)
        ]
        
        if not policies:
            logger.info(f"No policies found for type {policy_type}, allowing by default")
            result = {
                'allowed': True,
                'reason': 'No applicable policies found',
                'policy_id': None
            }
            
            # Log policy evaluation response event
            self._log_event("POLICY_EVAL_RESPONSE", {
                "request_id": context.get("request_id", "unknown"),
                "decision": "allow",
                "matched_policies": [],
                "reason": result['reason'],
                "response_time_ms": (time.time() - start_time) * 1000
            })
            
            return result
            
        # Check each policy
        matched_policies = []
        final_decision = {'allowed': True, 'reason': 'All policies passed', 'policy_id': None}
        config_parameters = {} # To store parameters from 'configure' actions
        
        for policy in policies:
            evaluation_start_time = time.time()
            result = policy.evaluate(context) # Placeholder evaluation
            evaluation_duration_ms = (time.time() - evaluation_start_time) * 1000
            
            matched_policies.append(policy.id)
            action = result.get('action', policy.data.get('rules', [{}])[0].get('action', 'allow')) # Simplified action extraction
            
            if action == 'deny' and not result.get('allowed', True):
                logger.info(f"Policy {policy.id} denied action: {result.get('reason', 'No reason provided')}")
                final_decision = {
                    'allowed': False,
                    'reason': result.get('reason', 'Policy denied action'),
                    'policy_id': policy.id,
                    'violations': result.get('violations', [])
                }
                # Log deny event immediately and break
                self._log_event("POLICY_EVAL_RESPONSE", {
                    "request_id": context.get("request_id", "unknown"),
                    "decision": "deny",
                    "matched_policies": matched_policies,
                    "reason": final_decision['reason'],
                    "policy_id": policy.id, 
                    "evaluation_duration_ms": evaluation_duration_ms,
                    "response_time_ms": (time.time() - start_time) * 1000
                })
                break # Stop processing on first deny
            
            elif action == 'configure':
                # If action is configure, merge parameters (assuming evaluate returns them)
                policy_params = result.get('parameters', policy.data.get('rules', [{}])[0].get('parameters', {})) # Simplified param extraction
                if policy_params:
                    config_parameters.update(policy_params)
                    logger.info(f"Policy {policy.id} provided configuration parameters: {policy_params}")
                    # We might want to stop after the first configure rule matches, 
                    # depending on desired behavior (e.g., highest priority config wins)
                    # For now, let's allow multiple configure policies to add parameters.
                    # break # Uncomment if only first configure should apply
                    
            # Log individual policy evaluation (optional, can be verbose)
            # self._log_event("POLICY_RULE_EVAL", {...})

        # Add merged configuration parameters to the final response if any were found
        if config_parameters:
            final_decision['parameters'] = config_parameters
            final_decision['action_taken'] = 'configure' # Indicate config was applied
            
        # Log final decision event (allow/configured)
        if final_decision['allowed']:
             self._log_event("POLICY_EVAL_RESPONSE", {
                 "request_id": context.get("request_id", "unknown"),
                 "decision": "allow" if not config_parameters else "allow_configure",
                 "matched_policies": matched_policies,
                 "reason": final_decision['reason'],
                 "parameters": config_parameters if config_parameters else None,
                 "response_time_ms": (time.time() - start_time) * 1000
             })
            
        return final_decision
    
    def add_policy(self, policy_type: str, policy_data: Dict[str, Any]) -> str:
        """
        Add a new policy.
        
        Args:
            policy_type: Type of policy
            policy_data: Policy data
            
        Returns:
            ID of the new policy
        """
        policy_id = f"{policy_type}_{int(time.time())}"
        self.policies[policy_id] = {
            'type': policy_type,
            'data': policy_data,
            'created': time.time(),
            'updated': time.time(),
            'enabled': True
        }
        self.save_policies()
        logger.info(f"Added policy {policy_id}")
        
        # Log policy loaded event
        self._log_event("POLICY_LOADED", {
            "policy_id": policy_id,
            "source": "api_add"
        })
        
        return policy_id
        
    def update_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> bool:
        """
        Update an existing policy.
        
        Args:
            policy_id: ID of the policy to update
            policy_data: New policy data
            
        Returns:
            True if the policy was updated, False otherwise
        """
        if policy_id in self.policies:
            self.policies[policy_id]['data'] = policy_data
            self.policies[policy_id]['updated'] = time.time()
            self.save_policies()
            logger.info(f"Updated policy {policy_id}")
            return True
        logger.warning(f"Policy {policy_id} not found")
        return False
        
    def remove_policy(self, policy_id: str) -> bool:
        """
        Remove a policy.
        
        Args:
            policy_id: ID of the policy to remove
            
        Returns:
            True if the policy was removed, False otherwise
        """
        if policy_id in self.policies:
            del self.policies[policy_id]
            self.save_policies()
            logger.info(f"Removed policy {policy_id}")
            return True
        logger.warning(f"Policy {policy_id} not found")
        return False
        
    def get_policies(self, policy_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all policies of a specific type.
        
        Args:
            policy_type: Type of policies to get (optional)
            
        Returns:
            List of policies
        """
        if policy_type:
            return [
                {'id': pid, **pdata} 
                for pid, pdata in self.policies.items() 
                if pdata['type'] == policy_type
            ]
        return [{'id': pid, **pdata} for pid, pdata in self.policies.items()]
    
    def evaluate_policy(self, policy_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a specific policy.
        
        Args:
            policy_id: ID of the policy to evaluate
            context: Context for policy evaluation
            
        Returns:
            Evaluation result
        """
        policy = self.get_policy(policy_id)
        if not policy:
            logger.warning(f"Policy {policy_id} not found, could not evaluate")
            return {
                "compliant": False,
                "violations": [f"Policy {policy_id} not found"],
                "recommendations": [],
                "applied_rules": []
            }
        
        return policy.evaluate(context)
    
    def _create_cache_key(self, policy_type: str, context: Dict[str, Any]) -> str:
        """
        Create a cache key from policy type and context.
        
        Args:
            policy_type: Type of policy
            context: Context information
            
        Returns:
            Cache key string
        """
        import hashlib
        import json
        
        # Remove non-deterministic elements from context
        context_copy = {k: v for k, v in context.items() if k != "timestamp"}
        
        # Create a hash from the policy type and context
        context_str = json.dumps(context_copy, sort_keys=True)
        hash_obj = hashlib.md5(f"{policy_type}:{context_str}".encode())
        
        return hash_obj.hexdigest()

# Create Flask app for API
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})

@app.route('/policies', methods=['GET'])
def get_policies():
    """Get all policies."""
    policy_engine = PolicyEngine()
    policy_type = request.args.get('type')
    return jsonify(policy_engine.get_policies(policy_type))

@app.route('/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    """Get a policy by ID."""
    policy_engine = PolicyEngine()
    policy = policy_engine.get_policy(policy_id)
    if policy:
        return jsonify({'id': policy_id, **policy})
    return jsonify({'error': f'Policy {policy_id} not found'}), 404

@app.route('/policies', methods=['POST'])
def add_policy():
    """Add a new policy."""
    policy_engine = PolicyEngine()
    data = request.json
    policy_type = data.get('type')
    policy_data = data.get('data')
    if not policy_type or not policy_data:
        return jsonify({'error': 'Missing policy type or data'}), 400
    policy_id = policy_engine.add_policy(policy_type, policy_data)
    return jsonify({'id': policy_id, 'type': policy_type, 'data': policy_data}), 201

@app.route('/policies/<policy_id>', methods=['PUT'])
def update_policy(policy_id):
    """Update a policy."""
    policy_engine = PolicyEngine()
    data = request.json
    policy_data = data.get('data')
    if not policy_data:
        return jsonify({'error': 'Missing policy data'}), 400
    if policy_engine.update_policy(policy_id, policy_data):
        return jsonify({'id': policy_id, 'data': policy_data})
    return jsonify({'error': f'Policy {policy_id} not found'}), 404

@app.route('/policies/<policy_id>', methods=['DELETE'])
def remove_policy(policy_id):
    """Remove a policy."""
    policy_engine = PolicyEngine()
    if policy_engine.remove_policy(policy_id):
        return jsonify({'id': policy_id, 'deleted': True})
    return jsonify({'error': f'Policy {policy_id} not found'}), 404

@app.route('/events', methods=['GET'])
def get_events():
    """
    Get events from the event buffer.
    
    Query parameters:
        since_event_id: Optional event ID to get events after this ID
        limit: Maximum number of events to return (default: 1000)
    """
    try:
        # Parse query parameters
        since_event_id = request.args.get('since_event_id')
        limit = int(request.args.get('limit', 1000))  # No hard maximum limit
        
        logger.debug(f"Events endpoint called - buffer size: {len(PolicyEngine._event_buffer)}")
        
        # Lock the buffer while making a copy
        with PolicyEngine._buffer_lock:
            # Make a snapshot to work with
            current_events = list(PolicyEngine._event_buffer)
            logger.debug(f"Copied {len(current_events)} events from buffer")
            
            last_event_id = current_events[-1]["event_id"] if current_events else None
            
            if not current_events:
                logger.debug("Event buffer is empty")
                return jsonify({"events": [], "last_event_id": None})
            
            # Filter events after since_event_id if provided
            start_index = 0
            if since_event_id:
                logger.debug(f"Filtering events after ID: {since_event_id}")
                # Find the index of the event *after* since_event_id
                found = False
                for i, event in enumerate(current_events):
                    if event["event_id"] == since_event_id:
                        start_index = i + 1
                        found = True
                        logger.debug(f"Found event at index {i}, returning events starting from index {start_index}")
                        break
                        
                # If since_event_id not found, return all events
                if not found:
                    logger.debug(f"Event ID not found: {since_event_id}, returning all events")
                    start_index = 0
            
            # Slice the list based on start_index and limit
            results = current_events[start_index : start_index + limit]
            logger.debug(f"Returning {len(results)} events")
        
        return jsonify({
            "events": results,
            "last_event_id": last_event_id
        })
    except Exception as e:
        logger.error(f"Error in /events endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/check', methods=['POST'])
def check_policy():
    """Check if an action is allowed by policies."""
    policy_engine = PolicyEngine()
    data = request.json
    policy_type = data.get('type')
    context = data.get('context', {})
    if not policy_type:
        return jsonify({'error': 'Missing policy type'}), 400
    
    # Add request ID to context if not present
    if 'request_id' not in context:
        context['request_id'] = str(uuid.uuid4())
        
    result = policy_engine.check_policy(policy_type, context)
    return jsonify(result)

# Add API-prefixed routes for compatibility with FL Server
@app.route('/api/check_policy', methods=['POST'])
def api_check_policy():
    """API route for policy check (alias for /check)."""
    policy_engine = PolicyEngine()
    data = request.json
    policy_type = data.get('policy_type') or data.get('type')
    context = data.get('context', {})
    if not policy_type:
        return jsonify({'error': 'Missing policy type'}), 400
    
    # Add request ID to context if not present
    if 'request_id' not in context:
        context['request_id'] = str(uuid.uuid4())
        
    result = policy_engine.check_policy(policy_type, context)
    return jsonify(result)

@app.route('/api/v1/check', methods=['POST'])
def api_v1_check_policy():
    """API v1 route for policy check (alias for /check)."""
    return api_check_policy()

def run_server(host='0.0.0.0', port=5000):
    """Run the policy engine server."""
    app.run(host=host, port=port)

if __name__ == '__main__':
    run_server() 