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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Depends, Body, HTTPException, Request
from pydantic import BaseModel, Field
import logging
import datetime
from typing import Dict, Any, Optional
import os
import json
import traceback
from pathlib import Path as PathLib

# Configure router without redirects for consistency with other endpoints
router = APIRouter(redirect_slashes=False)

# Set up a dedicated logger for client errors
client_logger = logging.getLogger("client_errors")
client_logger.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create logs directory with proper error handling
try:
    # Use absolute path for logs to ensure it works in all environments
    log_dir = os.environ.get('CLIENT_ERROR_LOGS_DIR', 'logs')
    
    # Create absolute path if it's a relative path
    if not os.path.isabs(log_dir):
        log_dir = os.path.abspath(log_dir)
    
    # Create directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    log_file_path = os.path.join(log_dir, 'client_errors.log')
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    client_logger.addHandler(file_handler)
    
    # Add a stream handler to also log to console for immediate visibility
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    client_logger.addHandler(console_handler)
    
    print(f"Client error logs will be written to: {log_file_path}")
except Exception as e:
    print(f"Error setting up client error logging: {e}")
    traceback.print_exc()

class ClientErrorLog(BaseModel):
    message: str
    stack: Optional[str] = Field(None, description="Error stack trace")
    name: Optional[str] = Field(None, description="Error name/type")
    timestamp: str
    component: Optional[str] = Field(None, description="Component where error occurred")
    userAgent: Optional[str] = Field(None, description="Browser user agent")
    additionalData: Optional[Dict[str, Any]] = Field(None, description="Any additional data/context")

# Both routes for consistency (with and without trailing slash)
@router.post("/client-error")
@router.post("/client-error/")
async def log_client_error(request: Request, error: ClientErrorLog):
    """
    Log client-side errors received from the frontend. 
    Errors are written to the client_errors.log file.
    """
    try:
        # Extract client IP for logging
        client_host = request.client.host if request.client else "unknown"
        
        # Format log message
        error_msg = (
            f"CLIENT ERROR from {client_host} | "
            f"{error.message}\n"
            f"Component: {error.component}\n"
            f"Timestamp: {error.timestamp}\n"
            f"Name: {error.name}\n"
            f"UserAgent: {error.userAgent}\n"
            f"Stack: {error.stack}\n"
        )
        
        # Add additional data if available
        if error.additionalData:
            error_msg += f"Additional Data: {json.dumps(error.additionalData, indent=2)}\n"
            
        # Check if client_logger is configured with handlers
        if client_logger.hasHandlers():
            client_logger.error(error_msg)
        else:
            # Fallback to default logger if client_logger is not working
            logging.error(f"(Fallback logging) {error_msg}")
            logging.error("client_logger has no handlers, check initial setup.")
            
        # Print to console for immediate visibility during development
        print(f"Client error logged: {error.message}")
        
        return {"status": "logged", "timestamp": datetime.datetime.now().isoformat()}
    except Exception as e:
        # Log server-side error in handling client error
        logging.error(f"Error processing client error log: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing client error: {str(e)}")

@router.websocket("/logs/{container_name}")
async def websocket_endpoint(websocket: WebSocket, container_name: str = Path(...)):
    """Stream logs from a container."""
    await websocket.accept()
    try:
        import aiofiles
        import json
        import asyncio
        from app.core.config import settings
        
        # First, look for logs in the container_logs directory
        log_path = os.path.join('container_logs', f"{container_name}.log")
        gns3_log_path = None
        
        # Also check in GNS3 container logs directory
        for filename in os.listdir('gns3_container_logs'):
            if container_name in filename:
                gns3_log_path = os.path.join('gns3_container_logs', filename)
                break
        
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": f"Connected to logs for container: {container_name}",
            "timestamp": datetime.datetime.now().isoformat()
        }))
        
        # If no log file is found, try to fetch from GNS3
        if not os.path.exists(log_path) and not gns3_log_path:
            from app.services.gns3_client import AsyncGNS3Client
            gns3_client = AsyncGNS3Client(base_url=settings.GNS3_URL)
            
            # Try to get logs from GNS3 node
            try:
                nodes = await gns3_client.get_nodes()
                node_id = None
                
                # Find the node by name
                for node in nodes:
                    if container_name in node.get("name", ""):
                        node_id = node.get("node_id")
                        break
                
                if node_id:
                    # Get console connection for the node
                    console = await gns3_client.get_node_console(node_id)
                    await websocket.send_text(json.dumps({
                        "type": "info",
                        "message": f"Fetching logs from GNS3 node: {node_id}",
                        "timestamp": datetime.datetime.now().isoformat()
                    }))
                    
                    # Stream logs from GNS3 (simplified for example)
                    while True:
                        logs = await gns3_client.get_node_logs(node_id)
                        if logs:
                            await websocket.send_text(json.dumps({
                                "type": "log",
                                "container": container_name,
                                "message": logs,
                                "timestamp": datetime.datetime.now().isoformat()
                            }))
                        await asyncio.sleep(2)
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"No node found with name containing: {container_name}",
                        "timestamp": datetime.datetime.now().isoformat()
                    }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error retrieving logs from GNS3: {str(e)}",
                    "timestamp": datetime.datetime.now().isoformat()
                }))
        
        # If local log file exists, stream it
        elif os.path.exists(log_path):
            async with aiofiles.open(log_path, mode='r') as f:
                # Read existing content
                content = await f.read()
                lines = content.splitlines()
                
                # Send the last 100 lines or all lines if less
                for line in lines[-100:]:
                    await websocket.send_text(json.dumps({
                        "type": "log",
                        "container": container_name,
                        "message": line,
                        "timestamp": datetime.datetime.now().isoformat()
                    }))
                
                # Seek to the end of the file
                await f.seek(0, 2)
                
                # Continue streaming new content
                while True:
                    line = await f.readline()
                    if line:
                        await websocket.send_text(json.dumps({
                            "type": "log",
                            "container": container_name,
                            "message": line.strip(),
                            "timestamp": datetime.datetime.now().isoformat()
                        }))
                    else:
                        await asyncio.sleep(1)
        
        # If GNS3 log file exists, stream it
        elif gns3_log_path:
            async with aiofiles.open(gns3_log_path, mode='r') as f:
                # Read existing content
                content = await f.read()
                lines = content.splitlines()
                
                # Send the last 100 lines or all lines if less
                for line in lines[-100:]:
                    await websocket.send_text(json.dumps({
                        "type": "log",
                        "container": container_name,
                        "message": line,
                        "timestamp": datetime.datetime.now().isoformat()
                    }))
                
                # No live streaming for GNS3 logs as they are typically captured snapshots
                await websocket.send_text(json.dumps({
                    "type": "info",
                    "message": "End of GNS3 captured logs",
                    "timestamp": datetime.datetime.now().isoformat()
                }))
        
        else:
            # No log file found
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"No log file found for container: {container_name}",
                "timestamp": datetime.datetime.now().isoformat()
            }))
    
    except WebSocketDisconnect:
        print(f"Client disconnected from {container_name} logs")
    except Exception as e:
        print(f"Error in log stream for {container_name}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error streaming logs: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }))
        except:
            pass
        finally:
            await websocket.close()

@router.websocket("/events")
async def events_websocket(websocket: WebSocket):
    """Stream system events from various sources."""
    await websocket.accept()
    try:
        import json
        import asyncio
        from app.core.config import settings
        from app.services.collector_client import CollectorApiClient # Corrected import path
        
        collector_client = CollectorApiClient(base_url=settings.COLLECTOR_URL)
        
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to system events stream from collector",
            "timestamp": datetime.datetime.now().isoformat()
        }))
        
        # Get initial events from collector
        try:
            # Get events without filtering initially to ensure we have data
            events_response = await collector_client.get_events({"limit": 100})
            
            # Ensure events is a list
            if isinstance(events_response, dict) and "events" in events_response:
                events = events_response["events"]
            else:
                events = events_response if isinstance(events_response, list) else []
            
            # Validate each event object before sending
            valid_events = []
            for event in events:
                if isinstance(event, dict) and "timestamp" in event and "source_component" in event:
                    # Map collector event fields to expected frontend fields
                    # Frontend expects component, but collector uses source_component
                    if "source_component" in event and not "component" in event:
                        event["component"] = event["source_component"]
                    
                    # Default message if not provided 
                    if not "message" in event:
                        if "details" in event and event["details"]:
                            event["message"] = f"{event['event_type']}: {json.dumps(event['details'])}"
                        else:
                            event["message"] = event.get("event_type", "Unknown event")
                    
                    valid_events.append(event)
                else:
                    print(f"Skipping invalid event: {event}")
            
            await websocket.send_text(json.dumps({
                "type": "initial_events",
                "events": valid_events,
                "timestamp": datetime.datetime.now().isoformat()
            }))
            
            # Stream events in real-time
            # Safely get max event ID with fallback to 0
            try:
                last_event_id = max([event.get("id", 0) for event in valid_events]) if valid_events else 0
            except (ValueError, TypeError):
                last_event_id = 0
                print("Failed to determine last event ID, starting from 0")
            
            while True:
                # Fetch new events since the last known event ID
                try:
                    params = {
                        "since_id": last_event_id,
                        "limit": 50
                    }
                    
                    new_events_response = await collector_client.get_events(params=params)
                    
                    # Ensure new_events is a list
                    if isinstance(new_events_response, dict) and "events" in new_events_response:
                        new_events = new_events_response["events"]
                    else:
                        new_events = new_events_response if isinstance(new_events_response, list) else []
                    
                    if new_events:
                        # Update the last event ID safely
                        try:
                            last_event_id = max([event.get("id", 0) for event in new_events if isinstance(event, dict)])
                        except (ValueError, TypeError):
                            print("Failed to update last event ID")
                        
                        # Send each new event separately
                        for event in new_events:
                            if isinstance(event, dict):
                                # Map collector fields to frontend expected fields
                                if "source_component" in event and not "component" in event:
                                    event["component"] = event["source_component"]
                                
                                # Default message if not provided
                                if not "message" in event:
                                    if "details" in event and event["details"]:
                                        event["message"] = f"{event['event_type']}: {json.dumps(event['details'])}"
                                    else:
                                        event["message"] = event.get("event_type", "Unknown event")
                                
                                await websocket.send_text(json.dumps({
                                    "type": "event",
                                    "event": event,
                                    "timestamp": datetime.datetime.now().isoformat()
                                }))
                            else:
                                print(f"Skipping invalid event: {event}")
                except Exception as e:
                    # Log error but continue polling
                    print(f"Error fetching new events: {e}")
                
                # Wait a few seconds before checking for new events
                await asyncio.sleep(5)
                
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error connecting to event stream: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }))
    
    except WebSocketDisconnect:
        print("Client disconnected from events stream")
    except Exception as e:
        print(f"Error in events stream: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error in event stream: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }))
        except:
            pass
        finally:
            await websocket.close()