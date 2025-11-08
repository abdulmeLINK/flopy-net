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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import asyncio
import json
import logging
from datetime import datetime
from app.services.collector_client import CollectorApiClient

logger = logging.getLogger(__name__)

router = APIRouter()

class TopologyWebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.update_interval = 5  # seconds
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")
        
    async def send_topology_update(self, topology_data: Dict[str, Any]):
        """Send topology update to all connected clients."""
        if not self.active_connections:
            return
            
        message = {
            "type": "topology_update",
            "data": topology_data,
            "timestamp": datetime.now().isoformat()
        }
        
        dead_connections = []
        for connection in self.active_connections[:]:  # Create a copy to iterate
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send topology update to client: {e}")
                dead_connections.append(connection)
                
        # Remove dead connections
        for connection in dead_connections:
            self.disconnect(connection)

manager = TopologyWebSocketManager()

@router.websocket("/topology/live")
async def topology_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time topology updates."""
    await manager.connect(websocket)
    collector_client = CollectorApiClient()
    
    try:
        while True:
            try:
                # Get live topology data
                topology_data = await collector_client.get_live_network_topology()
                
                # Send update to this client
                await websocket.send_text(json.dumps({
                    "type": "topology_update",
                    "data": topology_data,
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Wait before next update
                await asyncio.sleep(manager.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in topology WebSocket loop: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error getting topology data: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }))
                await asyncio.sleep(5)  # Wait before retrying
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
        await collector_client.close()

@router.post("/topology/broadcast")
async def broadcast_topology_update():
    """Manually trigger a topology update broadcast to all connected clients."""
    try:
        collector_client = CollectorApiClient()
        topology_data = await collector_client.get_live_network_topology()
        await manager.send_topology_update(topology_data)
        await collector_client.close()
        
        return {
            "status": "success",
            "message": f"Topology update sent to {len(manager.active_connections)} clients",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error broadcasting topology update: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
