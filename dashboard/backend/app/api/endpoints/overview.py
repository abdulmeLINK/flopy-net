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

import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional, List
from app.services.collector_client import CollectorApiClient
from app.services.policy_client import AsyncPolicyEngineClient
from app.core.config import settings
import json
from datetime import datetime, timedelta

# Import for caching
from fastapi_cache.decorator import cache

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

async def get_collector_client():
    return CollectorApiClient()

async def get_policy_client():
    return AsyncPolicyEngineClient()

@router.get("/fl-status")
@cache(expire=2) # Cache for 2 seconds - very aggressive for local deployment
async def get_fl_status(
    collector: CollectorApiClient = Depends(get_collector_client)
) -> Dict[str, Any]:
    """Get FL status independently with optimized data fetching"""
    try:
        # Use the new FL status endpoint from collector
        try:
            fl_status_data = await collector.get_fl_status()
            
            if fl_status_data and isinstance(fl_status_data, dict) and "error" not in fl_status_data:
                # Use the FL status endpoint data which has accurate current state
                training_active = fl_status_data.get("training_active", False)
                training_complete = fl_status_data.get("training_complete", False)
                fl_server_available = fl_status_data.get("fl_server_available", True)
                current_round = fl_status_data.get("current_round", 0)
                connected_clients = fl_status_data.get("connected_clients", 0)
                accuracy = fl_status_data.get("latest_accuracy", 0)
                loss = fl_status_data.get("latest_loss", 0)
                max_rounds = fl_status_data.get("max_rounds")  # Get max_rounds from FL server via collector
                
                # Convert accuracy to percentage if needed
                if isinstance(accuracy, (int, float)) and accuracy <= 1.0 and accuracy > 0:
                    accuracy = accuracy * 100
                
                # Determine proper status based on FL server state and max_rounds comparison
                if not fl_server_available:
                    # If FL server is not available but we have recent training data, 
                    # determine status based on the training state rather than showing error
                    if current_round > 0 and connected_clients > 0:
                        # Check if training completed based on max_rounds
                        if training_complete or (max_rounds and current_round >= max_rounds):
                            status = "completed"
                        elif training_active and (not max_rounds or current_round < max_rounds):
                            status = "active"
                        else:
                            status = "idle"  # Has data but not currently training
                    else:
                        status = "error"  # No meaningful data and server unavailable
                elif training_complete or (max_rounds and current_round >= max_rounds):
                    # Explicitly marked complete OR reached maximum rounds
                    status = "completed"
                elif training_active and current_round > 0 and (not max_rounds or current_round < max_rounds):
                    # Training is active and hasn't reached max rounds
                    status = "active"
                elif current_round > 0 and not training_active:
                    # Has trained before but not currently active
                    if max_rounds and current_round >= max_rounds:
                        status = "completed"  # Reached max rounds even if not explicitly marked complete
                    else:
                        status = "idle"
                else:
                    status = "idle"  # Never trained or no data
                
                fl_status = {
                    "round": current_round,
                    "clients_connected": connected_clients,
                    "clients_total": connected_clients,  # Use same value for both
                    "accuracy": accuracy,
                    "loss": loss,
                    "status": status,
                    "max_rounds": max_rounds  # Include max_rounds in response for debugging
                }
                logger.info(f"Successfully fetched FL status from enhanced status endpoint: {fl_status}")
                return fl_status
                
        except Exception as e:
            logger.warning(f"Failed to get FL status from status endpoint: {e}")
        
        # Fallback: Try to get the latest round data for accurate client counts
        try:
            fl_rounds_data = await collector.get_fl_rounds(limit=1)
            if fl_rounds_data and isinstance(fl_rounds_data, dict) and "rounds" in fl_rounds_data:
                rounds = fl_rounds_data.get("rounds", [])
                if rounds:
                    latest_round = rounds[0]
                    
                    # Use clients_connected instead of clients_total for connected clients
                    clients_connected = latest_round.get("clients_connected", latest_round.get("clients", 0))
                    clients_total = latest_round.get("clients_total", clients_connected)
                    
                    # If clients_connected is 0, try clients_total as fallback
                    if clients_connected == 0 and clients_total > 0:
                        clients_connected = clients_total
                    
                    # Determine proper status based on training state
                    training_complete = latest_round.get("training_complete", False)
                    round_num = latest_round.get("round", 0)
                    accuracy = latest_round.get("accuracy", 0)
                    
                    # Convert accuracy to percentage if needed
                    if isinstance(accuracy, (int, float)) and accuracy <= 1.0 and accuracy > 0:
                        accuracy = accuracy * 100
                    
                    # Determine status with proper completion detection based on training state
                    if training_complete:
                        status = "completed"  # Explicit completion flag
                    elif round_num > 0 and not training_complete:
                        status = "active"  # Has rounds but not marked as complete
                    elif round_num > 0:
                        status = "idle"  # Has rounds but not active
                    else:
                        status = "idle"  # No rounds yet
                    
                    # Use the latest round data which has accurate client information
                    fl_status = {
                        "round": round_num,
                        "clients_connected": clients_connected,
                        "clients_total": clients_total,
                        "accuracy": accuracy,
                        "loss": latest_round.get("loss", 0),
                        "status": status,
                        "max_rounds": None  # Add max_rounds field for consistency
                    }
                    logger.info(f"Successfully fetched FL status from rounds: {fl_status}")
                    return fl_status
        except Exception as e:
            logger.warning(f"Failed to get FL rounds data: {e}")
        
        # Final fallback to generic metrics
        fl_data = await collector.get_latest_metrics(type_filter="fl_server")
        
        if not isinstance(fl_data, dict):
            # Return default idle state instead of error for better UX
            return {
                "round": 0,
                "clients_connected": 0,
                "clients_total": 0,
                "accuracy": 0,
                "loss": 0,
                "status": "idle",
                "max_rounds": None  # Add max_rounds field for consistency
            }
        
        # Handle direct FL server response format
        accuracy = fl_data.get("accuracy", 0)
        if isinstance(accuracy, (int, float)) and accuracy <= 1.0 and accuracy > 0:
            accuracy = accuracy * 100
            
        # Try multiple field names for client count
        clients_connected = (
            fl_data.get("clients_connected", 0) or
            fl_data.get("connected_clients", 0) or  
            fl_data.get("clients_total", 0) or
            fl_data.get("clients", 0)
        )
        
        current_round = fl_data.get("round", fl_data.get("current_round", 0))
        
        # Determine status based on available data, not hardcoded thresholds
        if current_round > 0:
            status = fl_data.get("status", "active")  # Use provided status or default to active if has rounds
        else:
            status = "idle"
        
        fl_status = {
            "round": current_round,
            "clients_connected": clients_connected,
            "clients_total": clients_connected,
            "accuracy": accuracy,
            "loss": fl_data.get("loss", fl_data.get("latest_loss", 0)),
            "status": status,
            "max_rounds": None  # Add max_rounds field for consistency
        }
        logger.info(f"Successfully fetched FL status from generic metrics: {fl_status}")
        return fl_status
        
    except Exception as e:
        logger.error(f"Failed to fetch FL status: {e}")
        # Return default idle state instead of raising an error for better UX
        return {
            "round": 0,
            "clients_connected": 0,
            "clients_total": 0,
            "accuracy": 0,
            "loss": 0,
            "status": "error",
            "error": str(e),
            "max_rounds": None  # Add max_rounds field for consistency
        }

@router.get("/network-status")
@cache(expire=2) # Cache for 2 seconds - very aggressive for local deployment
async def get_network_status(
    collector: CollectorApiClient = Depends(get_collector_client)
) -> Dict[str, Any]:
    """Get network status independently"""
    try:
        logger.info("Fetching network data from collector...")
        network_data = await collector.get_latest_metrics(type_filter="network")
        logger.info(f"Raw network data type: {type(network_data)}")
        
        # Handle Pydantic model response
        if hasattr(network_data, 'metrics') and hasattr(network_data, 'status'):
            # This is a LatestMetricResponse model
            if network_data.status != "success":
                raise HTTPException(status_code=502, detail=f"Collector returned error status: {network_data.status}")
            
            if not network_data.metrics:
                raise HTTPException(status_code=502, detail="No network metrics available from collector")
            
            # Extract metrics data
            metrics_data = network_data.metrics
            logger.info(f"Metrics data type: {type(metrics_data)}")
            logger.info(f"Metrics data keys: {list(metrics_data.keys()) if isinstance(metrics_data, dict) else 'Not a dict'}")
            
            # Access the data field from metrics
            data = metrics_data.get("data", {}) if isinstance(metrics_data, dict) else {}
            logger.info(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Extract topology information for better metrics
            topology = data.get("topology", {})
            hosts = topology.get("hosts", []) if isinstance(topology, dict) else []
            links = topology.get("links", []) if isinstance(topology, dict) else []
            switches = topology.get("switches", []) if isinstance(topology, dict) else []
            nodes = topology.get("nodes", []) if isinstance(topology, dict) else []
            
            # Get counts from the top-level of data if available, otherwise compute from topology
            switches_count = data.get("switches_count", len(switches))
            hosts_count = data.get("hosts_count", len([n for n in nodes if n.get("type") == "host"]))
            
            # Active nodes are the sum of switches and hosts
            active_nodes = switches_count + hosts_count
            
            # Extract performance metrics
            performance_metrics = data.get("performance_metrics", {})
            latency_info = performance_metrics.get("latency", {})
            bandwidth_info = performance_metrics.get("bandwidth", {})
            flows_info = performance_metrics.get("flows", {})
            
            # Get average latency from performance metrics
            avg_latency = latency_info.get("average_ms", 0) if isinstance(latency_info, dict) else 0
            
            # Calculate bandwidth utilization percentage (assuming 100 Mbps total capacity per port as baseline)
            total_bandwidth_mbps = bandwidth_info.get("total_mbps", 0) if isinstance(bandwidth_info, dict) else 0
            active_ports = bandwidth_info.get("active_ports", 1) if isinstance(bandwidth_info, dict) else 1
            # Assume 100 Mbps capacity per active port, calculate utilization percentage
            total_capacity_mbps = active_ports * 100
            bandwidth_utilization = min((total_bandwidth_mbps / total_capacity_mbps) * 100, 100) if total_capacity_mbps > 0 else 0
            
            # Get actual flow count from flows endpoint for accurate data
            total_flows = 0
            try:
                flows_data = await collector.get_network_flows()
                if "error" not in flows_data:
                    total_flows = flows_data.get("summary", {}).get("total_flows", len(flows_data.get("flows", [])))
                else:
                    # Fallback to performance metrics if flows endpoint fails
                    total_flows = flows_info.get("total", 0) if isinstance(flows_info, dict) else 0
            except Exception as e:
                logger.warning(f"Failed to get flows data for overview: {e}")
                # Fallback to performance metrics
                total_flows = flows_info.get("total", 0) if isinstance(flows_info, dict) else 0
            
            network_status = {
                "nodes_count": active_nodes, # Total nodes is now active_nodes
                "links_count": data.get("links_count", len(links)),
                "avg_latency": avg_latency,
                "packet_loss_percent": data.get("packet_loss_percent", 0),
                "bandwidth_utilization": round(bandwidth_utilization, 2),
                "sdn_status": data.get("sdn_status", "unknown"),
                "switches_count": switches_count,
                "total_flows": total_flows,
                "active_nodes": active_nodes,
                "hosts_count": hosts_count, # Changed from stopped_nodes
                "status": "active" if data.get("sdn_status") == "connected" else "error"
            }
            
            logger.info(f"Successfully fetched network status: {network_status}")
            return network_status
            
        elif isinstance(network_data, dict):
            # Fallback for dict response (legacy)
            if "metrics" not in network_data:
                raise HTTPException(status_code=502, detail="No network metrics available from collector")
            
            metrics_wrapper = network_data.get("metrics", {})
            data = metrics_wrapper.get("data", {})
            
            # Same processing as above...
            topology = data.get("topology", {})
            hosts = topology.get("hosts", []) if isinstance(topology, dict) else []
            links = topology.get("links", []) if isinstance(topology, dict) else []
            switches = topology.get("switches", []) if isinstance(topology, dict) else []
            nodes = topology.get("nodes", []) if isinstance(topology, dict) else []
            
            switches_count = data.get("switches_count", len(switches))
            hosts_count = data.get("hosts_count", len([n for n in nodes if n.get("type") == "host"]))
            
            active_nodes = switches_count + hosts_count
            
            # Get actual flow count from flows endpoint for accurate data
            total_flows = 0
            try:
                flows_data = await collector.get_network_flows()
                if "error" not in flows_data:
                    total_flows = flows_data.get("summary", {}).get("total_flows", len(flows_data.get("flows", [])))
                else:
                    # Fallback to legacy data
                    total_flows = data.get("total_flows", 0)
            except Exception as e:
                logger.warning(f"Failed to get flows data for overview: {e}")
                # Fallback to legacy data
                total_flows = data.get("total_flows", 0)
            
            network_status = {
                "nodes_count": active_nodes,
                "links_count": data.get("links_count", len(links)),
                "avg_latency": data.get("avg_latency_ms", 0),
                "packet_loss_percent": data.get("packet_loss_percent", 0),
                "bandwidth_utilization": data.get("bandwidth_utilization_percent", 0),
                "sdn_status": data.get("sdn_status", "unknown"),
                "switches_count": switches_count,
                "total_flows": total_flows,
                "active_nodes": active_nodes,
                "hosts_count": hosts_count,
                "status": "active" if data.get("sdn_status") == "connected" else "error"
            }
            
            logger.info(f"Successfully fetched network status: {network_status}")
            return network_status
        else:
            logger.error(f"Unexpected network data type: {type(network_data)}")
            raise HTTPException(status_code=502, detail="Invalid network data format from collector")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to fetch network status: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to fetch network status: {str(e)}")

@router.get("/policy-status")
@cache(expire=2) # Cache for 2 seconds - very aggressive for local deployment
async def get_policy_status(
    policy_client: AsyncPolicyEngineClient = Depends(get_policy_client)
) -> Dict[str, Any]:
    """Get policy status independently"""
    try:
        # Fetch policy data from the policy engine
        policies_task = policy_client.get_policies()
        avg_decision_time_task = policy_client.get_average_decision_time()
        
        policies, avg_decision_time = await asyncio.gather(
            policies_task,
            avg_decision_time_task,
            return_exceptions=True
        )
        
        active_policies = 0
        if not isinstance(policies, Exception) and isinstance(policies, list):
            # Filter for active policies
            active_policies = sum(1 for policy in policies if isinstance(policy, dict) and policy.get("status") == "active")
        
        decision_time = 0.0
        if not isinstance(avg_decision_time, Exception) and isinstance(avg_decision_time, (int, float)):
            decision_time = avg_decision_time
        
        # Try to get real policy decisions directly from policy engine instead of collector
        allow_count = 0
        deny_count = 0
        decisions_last_hour = 0
        try:
            # Get policy decisions directly from policy engine with time filtering
            one_hour_ago = datetime.now() - timedelta(hours=1)
            decisions_params = {
                "start_time": one_hour_ago.isoformat(),
                "end_time": datetime.now().isoformat(),
                "limit": 1000  # Get enough decisions for accurate counting
            }
            
            decisions_data = await policy_client.get_policy_decisions(decisions_params)
            
            if decisions_data and isinstance(decisions_data, list):
                # Count allow/deny decisions in the last hour
                for decision in decisions_data:
                    if isinstance(decision, dict):
                        try:
                            # Parse decision timestamp
                            timestamp_str = decision.get("timestamp", decision.get("created_at"))
                            if timestamp_str:
                                # Handle different timestamp formats
                                try:
                                    if timestamp_str.endswith('Z'):
                                        decision_time_parsed = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    else:
                                        decision_time_parsed = datetime.fromisoformat(timestamp_str)
                                except ValueError:
                                    # Try parsing as different formats
                                    try:
                                        decision_time_parsed = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        continue
                                
                                if decision_time_parsed >= one_hour_ago:
                                    decisions_last_hour += 1
                                    action = decision.get("action", decision.get("result", decision.get("decision", ""))).lower()
                                    if any(word in action for word in ["allow", "success", "permit", "accept"]):
                                        allow_count += 1
                                    elif any(word in action for word in ["deny", "fail", "reject", "block", "drop"]):
                                        deny_count += 1
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.debug(f"Error parsing decision timestamp: {e}")
                            continue
        except Exception as e:
            logger.warning(f"Could not fetch policy decisions from policy engine: {e}")
            # For now, let's log this but not fail the entire endpoint
            # In a real deployment, we would want to investigate why policy decisions aren't available
            logger.info("Policy engine decisions unavailable - this might be expected if no policies have been applied yet")
        
        # Handle decision time logic
        if decisions_last_hour > 0:
            # If we have decisions but no decision time from the engine, use a reasonable default
            if decision_time <= 0:
                decision_time = 5.0  # 5ms default when we have activity
        else:
            # No decisions found - this could be normal if system just started or no policies are active
            # Set decision time to 0 to indicate no activity
            if decision_time < 0:
                decision_time = 0.0
        
        policy_status = {
            "active_policies": active_policies,
            "avg_decision_time_ms": decision_time,
            "allow_count_last_hour": allow_count,
            "deny_count_last_hour": deny_count,
            "decisions_last_hour": allow_count + deny_count,  # Total decisions
            "status": "active" if not isinstance(policies, Exception) else "error"
        }
        
        if isinstance(policies, Exception):
            policy_status["error"] = str(policies)
            
        logger.info(f"Successfully fetched Policy status: {policy_status}")
        return policy_status
        
    except Exception as e:
        logger.error(f"Failed to fetch policy status: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch policy status: {str(e)}")

@router.get("/events-summary")
@cache(expire=2) # Cache for 2 seconds - very aggressive for local deployment
async def get_events_summary(
    collector: CollectorApiClient = Depends(get_collector_client)
) -> Dict[str, Any]:
    """Get events summary independently with actual data from collector"""
    try:
        # Try to get events summary directly from collector first (better approach)
        try:
            events_summary_response = await collector._make_request("GET", "/api/events/summary")
            if isinstance(events_summary_response, dict) and "total" in events_summary_response:
                # Collector has a dedicated summary endpoint with actual totals
                total_count = events_summary_response.get("total", 0)
                by_level = events_summary_response.get("by_level", {})
                
                # Map collector level names to dashboard names
                error_count = by_level.get("ERROR", 0) + by_level.get("error", 0)
                warning_count = by_level.get("WARNING", 0) + by_level.get("warning", 0) + by_level.get("WARN", 0) + by_level.get("warn", 0)
                info_count = by_level.get("INFO", 0) + by_level.get("info", 0) + by_level.get("INFORMATION", 0) + by_level.get("information", 0)
                debug_count = by_level.get("DEBUG", 0) + by_level.get("debug", 0)
                
                return {
                    "total_count": total_count,
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "info_count": info_count,
                    "debug_count": debug_count,
                    "status": "healthy" if error_count == 0 else "warning"
                }
        except Exception as e:
            logger.debug(f"Collector events summary endpoint not available: {e}, falling back to events list method")
        
        # Fallback: Get events with response metadata that includes total count
        try:
            events_response = await collector.get_events(params={"limit": settings.DEFAULT_EVENTS_LIMIT})
        except Exception as e:
            logger.warning(f"Failed to get events from collector: {e}")
            # Return default summary if we can't get events
            return {
                "total_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "debug_count": 0,
                "status": "error",
                "error": "Unable to fetch events from collector"
            }
        
        # Extract total count from response metadata if available
        total_count = 0
        events = []
        
        if isinstance(events_response, dict):
            # Check for total count in response metadata
            total_count = events_response.get("total", 0)
            
            if "events" in events_response:
                events = events_response["events"]
            elif "data" in events_response:
                events = events_response["data"]
            elif isinstance(events_response.get("result"), list):
                events = events_response["result"]
            else:
                # Assume the whole response is the events list
                events = []
        elif isinstance(events_response, list):
            events = events_response
            # If no metadata, we'll have to use the count of returned events as fallback
            total_count = len(events)
        else:
            logger.warning(f"Unexpected events response format: {type(events_response)}")
            events = []
        
        # Ensure events is a list
        if not isinstance(events, list):
            logger.warning(f"Events data is not a list: {type(events)}")
            events = []
        
        # If we didn't get total_count from metadata, use length as fallback
        if total_count == 0:
            total_count = len(events)
        
        # Calculate level statistics from the sample events
        error_count = 0
        warning_count = 0
        info_count = 0
        debug_count = 0
        
        for event in events:
            # Handle both dict and object attributes
            level = None
            if hasattr(event, 'level'):
                level = event.level
            elif isinstance(event, dict):
                level = event.get('level') or event.get('event_type') or event.get('severity', 'info')
            
            if level:
                level = level.lower()
                if level == "error":
                    error_count += 1
                elif level == "warning" or level == "warn":
                    warning_count += 1
                elif level == "info" or level == "information":
                    info_count += 1
                elif level == "debug":
                    debug_count += 1
                else:
                    # Default unknown levels to info
                    info_count += 1
        
        # If we have a limited sample, estimate the level counts proportionally
        if len(events) < total_count and len(events) > 0:
            ratio = total_count / len(events)
            error_count = int(error_count * ratio)
            warning_count = int(warning_count * ratio)
            info_count = int(info_count * ratio)
            debug_count = int(debug_count * ratio)
        
        events_summary = {
            "total_count": total_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "debug_count": debug_count,
            "status": "healthy" if error_count == 0 else "warning"
        }
        
        logger.info(f"Successfully fetched events summary: {events_summary}")
        return events_summary
        
    except Exception as e:
        logger.error(f"Error getting events summary: {e}")
        # Return safe fallback instead of raising an exception
        return {
            "total_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "debug_count": 0,
            "status": "error",
            "error": f"Failed to get events summary: {str(e)}"
        }

@router.get("/summary")
async def get_overview_summary(
    collector: CollectorApiClient = Depends(get_collector_client),
    policy_client: AsyncPolicyEngineClient = Depends(get_policy_client)
) -> Dict[str, Any]:
    """Get complete overview summary - kept for backward compatibility"""
    try:
        # Run all component fetches in parallel
        fl_task = get_fl_status(collector)
        network_task = get_network_status(collector)
        policy_task = get_policy_status(policy_client)
        events_task = get_events_summary(collector)
        
        fl_status, network_status, policy_status, events_summary = await asyncio.gather(
            fl_task,
            network_task,
            policy_task,
            events_task,
            return_exceptions=True
        )
        
        # Handle exceptions gracefully - convert HTTPExceptions to error status
        if isinstance(fl_status, Exception):
            fl_status = {"status": "error", "error": str(fl_status)}
        if isinstance(network_status, Exception):
            network_status = {"status": "error", "error": str(network_status)}
        if isinstance(policy_status, Exception):
            policy_status = {"status": "error", "error": str(policy_status)}
        if isinstance(events_summary, Exception):
            events_summary = {"status": "error", "error": str(events_summary)}

        summary = {
            "fl_status": fl_status,
            "network_status": network_status,
            "policy_status": policy_status,
            "events": events_summary,
            "timestamp": datetime.now().isoformat()
        }
        return summary
        
    except Exception as e:
        logger.error(f"Unexpected error in overview summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.websocket("/ws/overview")
async def websocket_overview_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time overview updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial data immediately
        collector = await get_collector_client()
        policy_client = await get_policy_client()
        
        while True:
            try:
                # Collect all status data with timeout
                fl_task = get_fl_status(collector)
                network_task = get_network_status(collector)
                policy_task = get_policy_status(policy_client)
                events_task = get_events_summary(collector)
                
                # Run with timeout to prevent hanging
                fl_data, network_data, policy_data, events_data = await asyncio.wait_for(
                    asyncio.gather(fl_task, network_task, policy_task, events_task, return_exceptions=True),
                    timeout=settings.HTTP_READ_TIMEOUT
                )
                
                # Handle exceptions gracefully
                if isinstance(fl_data, Exception):
                    fl_data = {"status": "error", "error": str(fl_data)}
                if isinstance(network_data, Exception):
                    network_data = {"status": "error", "error": str(network_data)}
                if isinstance(policy_data, Exception):
                    policy_data = {"status": "error", "error": str(policy_data)}
                if isinstance(events_data, Exception):
                    events_data = {"status": "error", "error": str(events_data)}
                
                # Prepare update message
                update_message = {
                    "type": "overview_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "fl": fl_data,
                        "network": network_data,
                        "policy": policy_data,
                        "events": events_data
                    }
                }
                
                # Send update to this specific connection
                await manager.send_personal_message(
                    json.dumps(update_message), 
                    websocket
                )
                
                # Wait before next update (configurable interval)
                await asyncio.sleep(settings.OVERVIEW_UPDATE_INTERVAL)
                
            except asyncio.TimeoutError:
                logger.warning("WebSocket update timed out, continuing...")
                await asyncio.sleep(settings.POLLING_INTERVAL)  # Shorter wait after timeout
            except Exception as e:
                logger.error(f"Error in WebSocket update loop: {e}")
                await asyncio.sleep(settings.POLLING_INTERVAL)  # Wait before retrying
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket) 