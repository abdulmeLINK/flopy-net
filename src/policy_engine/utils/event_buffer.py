"""
Event Buffer Utility

This module provides event logging and buffering functionality for the policy engine.
"""

import uuid
import time
import threading
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Event buffer configuration
MAX_EVENT_BUFFER_SIZE = 500
EVENT_BUFFER: List[Dict[str, Any]] = []
EVENT_BUFFER_LOCK = threading.Lock()


def log_event(
    event_type: str, 
    details: Dict[str, Any], 
    source_component: str = "POLICY_ENGINE"
) -> str:
    """
    Log an event to the event buffer with memory optimization.
    
    Args:
        event_type: Type of event (e.g., 'POLICY_CHECK', 'POLICY_DENIED')
        details: Event-specific details dictionary
        source_component: Source component name
        
    Returns:
        The generated event ID
    """
    event_id = str(uuid.uuid4())
    timestamp = time.time()
    
    # Create compact event object
    event = {
        "id": event_id,
        "type": event_type,
        "timestamp": timestamp,
        "source": source_component,
        "details": _truncate_details(details)
    }
    
    # Add to event buffer with automatic cleanup
    with EVENT_BUFFER_LOCK:
        EVENT_BUFFER.append(event)
        # Trim buffer more aggressively to save memory
        if len(EVENT_BUFFER) > MAX_EVENT_BUFFER_SIZE:
            # Remove oldest 20% of events
            remove_count = max(1, MAX_EVENT_BUFFER_SIZE // 5)
            del EVENT_BUFFER[:remove_count]
            
    # Log the event (reduced verbosity)
    logger.debug(f"Event logged: {event_type}")
    
    return event_id


def _truncate_details(details: Dict[str, Any], max_size: int = 1000) -> Dict[str, Any]:
    """Truncate details if too large to save memory."""
    if isinstance(details, dict) and len(str(details)) < max_size:
        return details
    return {"summary": str(details)[:500]}


def get_events(
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    since_timestamp: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Get events from the buffer with optional filtering.
    
    Args:
        event_type: Filter by event type (optional)
        limit: Maximum number of events to return
        offset: Number of events to skip
        since_timestamp: Only return events after this timestamp
        
    Returns:
        List of event dictionaries
    """
    with EVENT_BUFFER_LOCK:
        # Make a copy to avoid modification during iteration
        events = list(EVENT_BUFFER)
    
    # Apply filters
    if event_type:
        events = [e for e in events if e.get('type') == event_type]
    
    if since_timestamp:
        events = [e for e in events if e.get('timestamp', 0) > since_timestamp]
    
    # Sort by timestamp (newest first)
    events.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    # Apply pagination
    return events[offset:offset + limit]


def get_event_count() -> int:
    """Get the current number of events in the buffer."""
    with EVENT_BUFFER_LOCK:
        return len(EVENT_BUFFER)


def clear_events() -> int:
    """Clear all events from the buffer. Returns count of cleared events."""
    with EVENT_BUFFER_LOCK:
        count = len(EVENT_BUFFER)
        EVENT_BUFFER.clear()
        return count


def get_event_types() -> List[str]:
    """Get list of unique event types in the buffer."""
    with EVENT_BUFFER_LOCK:
        return list(set(e.get('type', '') for e in EVENT_BUFFER))
