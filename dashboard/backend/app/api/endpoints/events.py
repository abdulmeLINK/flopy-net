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

from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.collector_client import CollectorApiClient
from typing import Optional, Dict, Any
import logging
import json
import datetime

# Configure router without redirects
router = APIRouter(redirect_slashes=False)
logger = logging.getLogger(__name__)

async def get_collector_client():
    return CollectorApiClient()

@router.get("/log")
@router.get("/log/")
async def get_events_log(
    limit: Optional[int] = Query(20, description="Max number of events to return"),
    offset: Optional[int] = Query(0, description="Number of events to skip"),
    level: Optional[str] = Query(None, description="Filter by event level"),
    component: Optional[str] = Query(None, description="Filter by component"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """
    Get events log from the collector.
    Returns paginated events with optional filtering.
    """
    try:
        # Build query parameters
        params = {
            "limit": limit,
            "offset": offset
        }
        
        # Add optional filters if provided
        if level:
            params["event_level"] = level
        if component:
            params["source_component"] = component
        if event_type:
            params["event_type"] = event_type
        
        data = await collector.get_events(params)
        
        # Map collector events format to frontend expected format if needed
        if 'events' in data and isinstance(data['events'], list):
            events = data['events']
            for event in events:
                # Map source_component to component if needed
                if 'source_component' in event and 'component' not in event:
                    event['component'] = event['source_component']
                
                # Ensure there's a message field
                if 'message' not in event:
                    if 'details' in event and event['details']:
                        try:
                            if isinstance(event['details'], str):
                                event['message'] = event['details']
                            else:
                                event['message'] = f"{event.get('event_type', 'Event')}: {json.dumps(event['details'])}"
                        except:
                            event['message'] = f"{event.get('event_type', 'Event')}"
                    else:
                        event['message'] = event.get('event_type', 'Unknown event')
        
        return data
    except Exception as e:
        logger.error(f"Error in get_events_log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")

@router.get("/summary")
@router.get("/summary/")
async def get_events_summary(
    component: Optional[str] = Query(None, description="Filter by component"),
    level: Optional[str] = Query(None, description="Filter by event level"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """
    Get a summary of event statistics.
    This endpoint provides counts of events by type, severity, etc.
    """
    try:
        # Build query parameters
        params = {}
        if component:
            params["source_component"] = component
        if level:
            params["event_level"] = level
        if event_type:
            params["event_type"] = event_type
            
        # Get the summary from the collector API
        data = await collector.get_events_summary(params)
        
        # Map collector response to expected format if needed
        summary = {
            "by_component": {},
            "by_level": {},
            "total": data.get("total", 0)
        }
        
        # If the collector returns a different format than expected by frontend, transform it
        if "by_component" in data:
            summary["by_component"] = data["by_component"]
            
            # Map source_component to component if needed
            if not "by_component" in data and "by_source_component" in data:
                summary["by_component"] = data["by_source_component"]
        
        if "by_level" in data:
            summary["by_level"] = data["by_level"]
            
            # Map event_level to level if needed
            if not "by_level" in data and "by_event_level" in data:
                summary["by_level"] = data["by_event_level"]
                
        return summary
    except Exception as e:
        logger.error(f"Error in get_events_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch events summary: {str(e)}")