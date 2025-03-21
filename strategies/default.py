"""
Default Policy Strategy

This is the default policy strategy for the federated learning system.
It enforces basic security, privacy, and fairness rules.
"""

def evaluate(context):
    """
    Evaluate the policy rules for a given context.
    
    Args:
        context (dict): Context information for policy evaluation.
            This may include:
            - 'operation': The operation being performed (e.g., 'client_selection', 'model_update')
            - 'client_id': The client ID (if applicable)
            - 'round_id': The training round ID (if applicable)
            - 'model_update': Model update details (if applicable)
            - 'client_data_size': Size of client data (if applicable)
            - Additional operation-specific context
    
    Returns:
        dict: Policy evaluation result with the following fields:
            - 'allowed': Boolean indicating whether the operation is allowed
            - 'reason': Reason for policy decision (if not allowed)
            - 'metadata': Additional metadata about the decision
    """
    operation = context.get('operation', '')
    
    # Default response
    result = {
        'allowed': True,
        'reason': '',
        'metadata': {}
    }
    
    # Evaluate policy based on operation
    if operation == 'client_selection':
        result = _evaluate_client_selection(context)
    elif operation == 'model_update':
        result = _evaluate_model_update(context)
    elif operation == 'model_access':
        result = _evaluate_model_access(context)
    elif operation == 'training':
        result = _evaluate_training(context)
    elif operation == 'client_registration':
        result = _evaluate_client_registration(context)
    
    return result


def _evaluate_client_selection(context):
    """Evaluate policy for client selection."""
    client_id = context.get('client_id')
    round_id = context.get('round_id')
    available_clients = context.get('available_clients', [])
    selected_client_count = context.get('selected_client_count', 0)
    
    # Check if enough clients are available
    if len(available_clients) < 3:  # Minimum clients for privacy
        return {
            'allowed': False,
            'reason': 'Not enough clients available for selection',
            'metadata': {'min_required': 3, 'available': len(available_clients)}
        }
    
    # Check if client selection is fair
    client_selections = context.get('client_selection_history', {})
    max_selections = 20  # Maximum times a client can be selected
    
    if client_id in client_selections and client_selections[client_id] >= max_selections:
        return {
            'allowed': False,
            'reason': 'Client has been selected too many times',
            'metadata': {'max_selections': max_selections, 'current': client_selections[client_id]}
        }
    
    return {
        'allowed': True,
        'reason': '',
        'metadata': {}
    }


def _evaluate_model_update(context):
    """Evaluate policy for model update acceptance."""
    client_id = context.get('client_id')
    update_size = context.get('update_size', 0)
    client_data_size = context.get('client_data_size', 0)
    
    # Ensure client has enough data for meaningful update
    if client_data_size < 10:  # Minimum data samples
        return {
            'allowed': False,
            'reason': 'Client does not have enough data for meaningful update',
            'metadata': {'min_required': 10, 'current': client_data_size}
        }
    
    # Verify update is within expected bounds (prevent poisoning)
    if update_size > 100 * 1024 * 1024:  # 100MB max update size
        return {
            'allowed': False,
            'reason': 'Model update is too large',
            'metadata': {'max_size': '100MB', 'current': f'{update_size / (1024*1024):.2f}MB'}
        }
    
    return {
        'allowed': True,
        'reason': '',
        'metadata': {}
    }


def _evaluate_model_access(context):
    """Evaluate policy for model access."""
    client_id = context.get('client_id')
    model_id = context.get('model_id')
    
    # All registered clients can access the global model
    # This could be modified to restrict access based on client properties
    return {
        'allowed': True,
        'reason': '',
        'metadata': {}
    }


def _evaluate_training(context):
    """Evaluate policy for client training."""
    client_id = context.get('client_id')
    training_params = context.get('training_params', {})
    
    # Ensure training parameters are within acceptable bounds
    if training_params.get('epochs', 1) > 10:
        return {
            'allowed': False,
            'reason': 'Too many training epochs requested',
            'metadata': {'max_epochs': 10, 'requested': training_params.get('epochs')}
        }
    
    # Ensure batch size is reasonable
    if training_params.get('batch_size', 32) > 512:
        return {
            'allowed': False,
            'reason': 'Batch size too large',
            'metadata': {'max_batch_size': 512, 'requested': training_params.get('batch_size')}
        }
    
    return {
        'allowed': True,
        'reason': '',
        'metadata': {}
    }


def _evaluate_client_registration(context):
    """Evaluate policy for client registration."""
    client_properties = context.get('client_properties', {})
    
    # Check for required client properties
    required_properties = ['data_size', 'capabilities']
    missing_properties = [prop for prop in required_properties if prop not in client_properties]
    
    if missing_properties:
        return {
            'allowed': False,
            'reason': 'Missing required client properties',
            'metadata': {'missing_properties': missing_properties}
        }
    
    # Verify client has enough data
    if client_properties.get('data_size', 0) < 10:
        return {
            'allowed': False,
            'reason': 'Client does not have enough data',
            'metadata': {'min_data_size': 10, 'current': client_properties.get('data_size', 0)}
        }
    
    return {
        'allowed': True,
        'reason': '',
        'metadata': {}
    } 