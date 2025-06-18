from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.services.collector_client import CollectorApiClient
import logging
import asyncio
from functools import lru_cache
import json
import math
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()



# Cache for frequently accessed data
@lru_cache(maxsize=128)
def get_cached_summary_key(timestamp_minute: int) -> str:
    """Generate cache key for summary data (cached per minute)"""
    return f"fl_summary_{timestamp_minute}"

async def get_collector_client():
    # Use the proper settings configuration for Docker compatibility
    return CollectorApiClient(base_url=settings.COLLECTOR_URL)

@router.get("/metrics")
async def get_fl_metrics(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = Query(100, description="Maximum number of metrics to return", ge=1, le=500),  # Better defaults and validation
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get FL training metrics from collector using optimized SQLite endpoints."""
    logger.info(f"FL Monitoring API: Received request for FL metrics with params - start_time: {start_time}, end_time: {end_time}, limit: {limit}")
    try:
        # **NEW: Use optimized SQLite summary endpoint for better performance**
        if not start_time and not end_time and limit <= 1000:
            # For general requests without time filters, use the optimized summary endpoint
            try:
                logger.info("Using optimized FL summary endpoint for better performance")
                response = await collector.get_fl_summary_fast(limit=limit)
                
                if isinstance(response, dict) and "rounds" in response:
                    metrics = response["rounds"]
                    logger.info(f"FL Monitoring API: Got {len(metrics)} metrics from optimized summary endpoint")
                    
                    # Transform to expected format
                    formatted_metrics = []
                    for metric in metrics:
                        formatted_metric = {
                            "timestamp": metric.get("timestamp", datetime.now().isoformat()),
                            "round": metric.get("round", 0),
                            "accuracy": metric.get("accuracy", 0.0),
                            "loss": metric.get("loss", 0.0),
                            "clients_connected": metric.get("clients_count", 0),
                            "clients_total": metric.get("clients_count", 0),
                            "training_complete": metric.get("training_complete", False),
                            "model_size_mb": metric.get("model_size_mb", 0.0),
                            "status": metric.get("status", "active")
                        }
                        formatted_metrics.append(formatted_metric)
                    
                    logger.info(f"FL Monitoring API: Successfully returning {len(formatted_metrics)} FL metrics from optimized endpoint")
                    return formatted_metrics
                    
            except Exception as summary_error:
                logger.warning(f"Optimized summary endpoint failed, falling back to standard endpoint: {summary_error}")
        
        # **FALLBACK: Use standard FL metrics endpoint with enhanced parameters**
        # Prepare parameters for collector API with performance limits
        params = {
            "limit": min(limit, 500),  # Maximum 500 metrics per request
            "optimize": "true",         # Enable SQLite optimizations
            "use_cache": "true",        # Use caching for repeated requests
            "consolidate_rounds": "true"  # Avoid duplicate rounds
        }
        
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        logger.info(f"Fetching FL metrics from collector with optimized params: {params}")
        
        # Get FL metrics from collector using enhanced endpoint
        response = await collector.get_fl_metrics(params)
        
        if not isinstance(response, dict):
            logger.error(f"Unexpected response type from collector: {type(response)}")
            raise HTTPException(status_code=502, detail="Invalid response format from collector")
        
        # **FIXED: Handle the correct collector response format**
        # The collector returns data in the "metrics" field
        if "metrics" in response and isinstance(response["metrics"], list):
            metrics = response["metrics"]
            logger.info(f"FL Monitoring API: Got {len(metrics)} metrics from collector")
        elif isinstance(response, list):
            metrics = response
        else:
            logger.warning(f"Unexpected FL metrics response format: {response}")
            metrics = []
        
        # Transform collector data to FL monitoring format with minimal processing
        formatted_metrics = []
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
                
            # **FIXED: Extract client data correctly - handle multiple field names from collector**
            clients_connected = (
                metric.get("clients_connected", 0) or
                metric.get("clients", 0) or
                metric.get("connected_clients", 0) or
                0
            )
            
            # Extract model size 
            model_size_mb = metric.get("model_size_mb", 0.0)
            
            # Ensure model_size_mb is a number
            try:
                model_size_mb = float(model_size_mb) if model_size_mb is not None else 0.0
            except (ValueError, TypeError):
                model_size_mb = 0.0
                
            # Ensure clients_connected is an integer
            try:
                clients_connected = int(clients_connected) if clients_connected is not None else 0
            except (ValueError, TypeError):
                clients_connected = 0
                
            formatted_metric = {
                "timestamp": metric.get("timestamp", datetime.now().isoformat()),
                "round": metric.get("round", 0),
                "accuracy": metric.get("accuracy", 0.0),
                "loss": metric.get("loss", 0.0),
                "clients_connected": clients_connected,
                "clients_total": metric.get("clients_total", clients_connected),  # Use connected as fallback for total
                "training_complete": metric.get("training_complete", False),
                "model_size_mb": model_size_mb,
                "status": metric.get("status", "active")
            }
            
            # Log successful client extraction for debugging
            if clients_connected > 0:
                logger.debug(f"FL Monitoring: Round {formatted_metric['round']} - clients: {clients_connected}, model_size: {model_size_mb} MB")
            
            formatted_metrics.append(formatted_metric)
        
        logger.info(f"FL Monitoring API: Successfully returning {len(formatted_metrics)} FL metrics")
        return formatted_metrics
        
    except Exception as e:
        logger.error(f"FL Monitoring API: Error fetching FL metrics: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch FL metrics: {str(e)}")

@router.get("/debug")
async def debug_fl_monitoring():
    """Debug endpoint to test FL monitoring API connectivity."""
    logger.info("FL Monitoring API: Debug endpoint called - API is reachable!")
    return {
        "status": "FL Monitoring API is working", 
        "timestamp": datetime.now().isoformat(),
        "message": "This debug endpoint confirms the FL monitoring API is reachable"
    }

@router.get("/debug/collector")
async def debug_collector_client(collector: CollectorApiClient = Depends(get_collector_client)):
    """Debug endpoint to check collector client configuration."""
    try:
        # Test collector client configuration
        result = {
            "collector_base_url": collector.base_url,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test the collector connection
        try:
            health = await collector.get_health()
            result["collector_health"] = health
            result["collector_connection"] = "success"
        except Exception as e:
            result["collector_health"] = None
            result["collector_connection"] = f"failed: {str(e)}"
        
        # Test the FL status endpoint specifically
        try:
            fl_status = await collector.get_fl_status()
            result["fl_status_response"] = fl_status
            result["fl_status_has_max_rounds"] = "max_rounds" in fl_status if isinstance(fl_status, dict) else False
            result["fl_status_max_rounds_value"] = fl_status.get("max_rounds") if isinstance(fl_status, dict) else None
            result["fl_status_keys"] = list(fl_status.keys()) if isinstance(fl_status, dict) else None
        except Exception as e:
            result["fl_status_response"] = None
            result["fl_status_error"] = str(e)
        
        return result
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/metrics/window")
async def get_fl_metrics_window(
    start_round: int = Query(..., description="Start round number", ge=1),
    end_round: int = Query(..., description="End round number", ge=1),
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get FL metrics for a specific round window with optimized performance."""
    try:
        # Validate and optimize round range
        if start_round > end_round:
            start_round, end_round = end_round, start_round
            
        window_size = end_round - start_round + 1
        
        # Strict window size limit for performance
        if window_size > 300:  # Reduced from 500 for better performance
            logger.warning(f"Window size {window_size} too large, capping at 300")
            end_round = start_round + 299
            window_size = 300
            
        # Fetch metrics with highly optimized parameters
        params = {
            "limit": min(window_size * 2, 600),  # Reduced from 1000 for better performance
            "include_raw": "false"
        }
        
        # Use asyncio timeout for better control
        try:
            response = await asyncio.wait_for(
                collector.get_fl_metrics(params), 
                timeout=30.0  # Increased timeout
            )
        except asyncio.TimeoutError:
            logger.error("Timeout fetching FL metrics from collector")
            raise HTTPException(status_code=504, detail="Request timeout")
        
        # Handle error responses from collector
        if isinstance(response, dict) and "error" in response:
            logger.warning(f"Collector returned error: {response['error']}")
            if response["error"] == "timeout":
                raise HTTPException(status_code=504, detail="Collector service timeout")
            elif response["error"].startswith("http_"):
                status_code = int(response["error"].split("_")[1])
                raise HTTPException(status_code=status_code, detail=f"Collector service error: {status_code}")
            else:
                raise HTTPException(status_code=503, detail="Collector service unavailable")
        
        if not response or "metrics" not in response:
            raise HTTPException(status_code=404, detail="No FL metrics available")
            
        # Efficiently filter to the requested round range
        filtered_metrics = []
        for metric in response["metrics"]:
            round_num = metric.get("round", 0)
            if start_round <= round_num <= end_round:
                # Minimize data transformation
                formatted_metric = {
                    "timestamp": metric.get("timestamp", datetime.now().isoformat()),
                    "round": round_num,
                    "accuracy": min(100, max(0, metric.get("accuracy", 0) * 100 if metric.get("accuracy", 0) <= 1 else metric.get("accuracy", 0))),
                    "loss": round(metric.get("loss", 0), 4),
                    "clients_connected": metric.get("clients_connected", metric.get("connected_clients", metric.get("clients", 0))),
                    "clients_total": metric.get("clients_total", metric.get("clients_connected", metric.get("connected_clients", metric.get("clients", 0)))),
                    "training_complete": metric.get("training_complete", False),
                    "status": metric.get("data_state", "training")
                }
                # Only include model size if meaningful
                if metric.get("model_size_mb", 0) > 0:
                    formatted_metric["model_size_mb"] = round(metric.get("model_size_mb", 0), 3)
                else:
                    formatted_metric["model_size_mb"] = 0.0  # Always include for consistent charting
                    
                filtered_metrics.append(formatted_metric)
        
        if not filtered_metrics:
            raise HTTPException(status_code=404, detail=f"No metrics found for rounds {start_round}-{end_round}")
        
        # Sort by round number for consistency
        filtered_metrics.sort(key=lambda x: x["round"])
        
        actual_start = min(m["round"] for m in filtered_metrics)
        actual_end = max(m["round"] for m in filtered_metrics)
        
        logger.info(f"Window query: requested {start_round}-{end_round}, returned {len(filtered_metrics)} metrics ({actual_start}-{actual_end})")
        
        return {
            "metrics": filtered_metrics,
            "start_round": start_round,
            "end_round": end_round,
            "actual_start": actual_start,
            "actual_end": actual_end,
            "count": len(filtered_metrics)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting FL metrics window: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics window: {str(e)}")

@router.get("/metrics/paginated")
async def get_fl_metrics_paginated(
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(100, description="Items per page", ge=10, le=200), # Reduced max
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get paginated FL metrics with optimized performance."""
    try:
        # Cap page size for performance
        page_size = min(page_size, 200)
        
        # Fetch optimized dataset for pagination
        try:
            response = await asyncio.wait_for(
                collector.get_fl_metrics({
                    "limit": 1500,  # Reduced from 2000
                    "include_raw": "false"
                }),
                timeout=45.0  # Increased timeout
            )
        except asyncio.TimeoutError:
            logger.error("Timeout fetching FL metrics for pagination")
            raise HTTPException(status_code=504, detail="Request timeout")
        
        # Handle error responses from collector
        if isinstance(response, dict) and "error" in response:
            logger.warning(f"Collector returned error: {response['error']}")
            if response["error"] == "timeout":
                raise HTTPException(status_code=504, detail="Collector service timeout")
            elif response["error"].startswith("http_"):
                status_code = int(response["error"].split("_")[1])
                raise HTTPException(status_code=status_code, detail=f"Collector service error: {status_code}")
            else:
                raise HTTPException(status_code=503, detail="Collector service unavailable")
        
        if not response or "metrics" not in response:
            raise HTTPException(status_code=404, detail="No FL metrics available for pagination")
            
        all_metrics = response["metrics"]
        
        if not all_metrics:
            raise HTTPException(status_code=404, detail="No FL metrics data available")
        
        # Sort by round number descending (newest first) efficiently
        all_metrics.sort(key=lambda x: x.get("round", 0), reverse=True)
        
        # Calculate pagination
        total_items = len(all_metrics)
        total_pages = (total_items + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Validate page bounds
        if page > total_pages:
            raise HTTPException(status_code=404, detail="Page not found")
        
        # Get page data
        page_metrics = all_metrics[start_idx:end_idx]
        
        # Format metrics efficiently
        formatted_metrics = []
        for metric in page_metrics:
            # Extract client data with fallback chain  
            clients_connected = (
                metric.get("clients_connected") or 
                metric.get("connected_clients") or 
                metric.get("clients") or 
                metric.get("successful_clients") or 
                0
            )
            
            # Extract model size with fallback
            model_size_mb = metric.get("model_size_mb", 0.0)
            if model_size_mb is None:
                model_size_mb = 0.0
                
            formatted_metric = {
                "timestamp": metric.get("timestamp", datetime.now().isoformat()),
                "round": metric.get("round", 0),
                "accuracy": min(100, max(0, metric.get("accuracy", 0) * 100 if metric.get("accuracy", 0) <= 1 else metric.get("accuracy", 0))),
                "loss": round(metric.get("loss", 0), 4),
                "clients_connected": clients_connected,
                "clients_total": metric.get("clients_total", clients_connected),  # Use connected as fallback
                "training_complete": metric.get("training_complete", False),
                "status": metric.get("data_state", "training"),
                "model_size_mb": model_size_mb
            }
            
            # Log metrics with zero values for debugging
            if clients_connected == 0 or model_size_mb == 0:
                logger.debug(f"FL Monitoring Paginated: Round {formatted_metric['round']} - clients: {clients_connected}, model_size: {model_size_mb} MB")
                
            formatted_metrics.append(formatted_metric)
        
        start_round = min(m["round"] for m in formatted_metrics) if formatted_metrics else 0
        end_round = max(m["round"] for m in formatted_metrics) if formatted_metrics else 0
        
        logger.info(f"Pagination: page {page}/{total_pages}, {len(formatted_metrics)} items, rounds {start_round}-{end_round}")
        
        return {
            "metrics": formatted_metrics,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_items": total_items,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "start_round": start_round,
            "end_round": end_round
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting FL metrics paginated: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch paginated metrics: {str(e)}")

@router.get("/metrics/around")
async def get_fl_metrics_around_round(
    target_round: int = Query(..., description="Target round number", ge=1),
    window_size: int = Query(100, description="Window size around target", ge=10, le=500),
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get FL metrics around a specific round."""
    # Calculate window bounds
    half_window = window_size // 2
    start_round = max(1, target_round - half_window)
    end_round = target_round + half_window
    
    # Use the window endpoint
    return await get_fl_metrics_window(start_round, end_round, collector)

@router.get("/metrics/summary")
async def get_fl_metrics_summary(
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get a summary of FL training metrics with optimized performance."""
    try:
        # Get recent metrics for summary with reduced limit for better performance
        response = await collector.get_fl_metrics({
            "limit": 200,  # Reduced from 1000 for better performance
            "include_raw": "false"
        })
        
        # Handle error responses from collector
        if isinstance(response, dict) and "error" in response:
            logger.warning(f"Collector returned error for summary: {response['error']}")
            if response["error"] == "timeout":
                raise HTTPException(status_code=504, detail="Collector service timeout")
            elif response["error"].startswith("http_"):
                status_code = int(response["error"].split("_")[1])
                raise HTTPException(status_code=status_code, detail=f"Collector service error: {status_code}")
            else:
                raise HTTPException(status_code=503, detail="Collector service unavailable")
        
        if not response or "metrics" not in response or not response["metrics"]:
            raise HTTPException(status_code=404, detail="No FL metrics available for summary")
            
        metrics = response["metrics"]
        
        # Extract values efficiently
        rounds = []
        accuracies = []
        losses = []
        
        for m in metrics:
            round_num = m.get("round", 0)
            if round_num > 0:
                rounds.append(round_num)
            
            acc = m.get("accuracy", 0)
            if isinstance(acc, (int, float)):
                if acc <= 1.0 and acc > 0:
                    acc = acc * 100
                if acc > 0:
                    accuracies.append(acc)
                
            loss = m.get("loss", 0)
            if isinstance(loss, (int, float)) and loss > 0:
                losses.append(loss)
        
        # Calculate summary stats efficiently
        total_rounds = max(rounds) if rounds else 0
        min_accuracy = min(accuracies) if accuracies else 0
        max_accuracy = max(accuracies) if accuracies else 0
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        min_loss = min(losses) if losses else 0
        max_loss = max(losses) if losses else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        training_complete = any(m.get("training_complete", False) for m in metrics)
        round_range = [min(rounds), max(rounds)] if rounds else [0, 0]
        
        summary = {
            "total_rounds": total_rounds,
            "min_accuracy": round(min_accuracy, 2),
            "max_accuracy": round(max_accuracy, 2),
            "min_loss": round(min_loss, 4),
            "max_loss": round(max_loss, 4),
            "avg_accuracy": round(avg_accuracy, 2),
            "avg_loss": round(avg_loss, 4),
            "training_complete": training_complete,
            "data_points": len(metrics),
            "round_range": round_range
        }
        
        logger.info(f"Generated FL metrics summary: {len(metrics)} data points, {total_rounds} rounds")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting FL metrics summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate FL metrics summary: {str(e)}")

@router.get("/latest")
async def get_latest_fl_status(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get latest FL training status from collector."""
    
    try:
        # Use the collector's specific FL status endpoint instead of generic latest metrics
        response = await collector._client.get("/api/metrics/fl/status")
        response.raise_for_status()
        metrics_data = response.json()
        
        if isinstance(metrics_data, dict):
            # Convert timestamp if it's a Unix timestamp
            timestamp = metrics_data.get("timestamp")
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp).isoformat()
            else:
                timestamp = timestamp or datetime.now().isoformat()
            
            # Convert start_time if needed
            start_time = metrics_data.get("start_time")
            if isinstance(start_time, (int, float)):
                start_time = datetime.fromtimestamp(start_time).isoformat()
            else:
                start_time = start_time or timestamp
            
            current_model_size_mb = metrics_data.get("model_size_mb", 0.0)

            if current_model_size_mb == 0.0:
                try:
                    logger.info("FL Monitoring /latest: model_size_mb is 0 from status, attempting to fetch from latest round.")
                    # Fetch the latest single round from the collector to get model_size_mb
                    # Assuming collector.get_fl_metrics can handle a simple "latest round" query
                    # or that a more specific method exists. For now, using a direct client call.
                    latest_round_response = await collector._client.get("/api/metrics/fl/rounds?limit=1&sort_order=desc")
                    latest_round_response.raise_for_status()
                    latest_round_data = latest_round_response.json()
                    
                    if latest_round_data and latest_round_data.get("rounds") and isinstance(latest_round_data["rounds"], list) and len(latest_round_data["rounds"]) > 0:
                        latest_round_metrics = latest_round_data["rounds"][0]
                        current_model_size_mb = latest_round_metrics.get("model_size_mb", 0.0)
                        logger.info(f"FL Monitoring /latest: Fetched model_size_mb: {current_model_size_mb} from latest round.")
                    else:
                        logger.info("FL Monitoring /latest: No rounds data found or latest round has no model_size_mb.")
                except Exception as round_fetch_exc:
                    logger.warning(f"FL Monitoring /latest: Could not fetch latest round to get model_size_mb: {round_fetch_exc}")

            # Map collector FL status data to the expected format for /latest endpoint
            fl_status = {
                "current_round": metrics_data.get("current_round", 0),
                "status": "active" if metrics_data.get("training_active", False) else "inactive", 
                "latest_accuracy": metrics_data.get("latest_accuracy", 0.0),
                "latest_loss": metrics_data.get("latest_loss", 0.0),
                "connected_clients": metrics_data.get("connected_clients", 0),
                "clients_total": metrics_data.get("connected_clients", 0),  # Use same value for both
                "training_active": metrics_data.get("training_active", False),
                "training_complete": metrics_data.get("training_complete", False),
                "data_source": metrics_data.get("data_source", "collector"),
                "fl_server_available": metrics_data.get("fl_server_available", False),
                "collector_monitoring": metrics_data.get("collector_monitoring", True),
                "timestamp": timestamp,
                "start_time": start_time,
                "last_update": timestamp,
                "model_size_mb": current_model_size_mb, # Use the potentially updated model_size_mb
                "max_rounds": metrics_data.get("max_rounds")  # Include max_rounds from collector
            }
            
            return fl_status
        else:
            logger.warning(f"Unexpected response type from collector: {type(metrics_data)}")
            raise HTTPException(status_code=502, detail="Invalid response format from collector")
            
    except Exception as e:
        logger.error(f"Error fetching latest FL status: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch FL status: {str(e)}")

# Add nested endpoints that the frontend expects
@router.get("/metrics/fl/status")
async def get_fl_training_status(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get FL training status in the format expected by the frontend."""
    
    logger.info("FL Status Endpoint: Starting get_fl_training_status - CODE UPDATE TEST")
    
    try:
        # Use the collector's get_fl_status method instead of raw HTTP client
        logger.info("FL Status Endpoint: Making request to collector FL status endpoint via client")
        logger.info(f"FL Status Endpoint: Collector client base URL: {collector.base_url}")
        metrics_data = await collector.get_fl_status()
        
        logger.info(f"FL Status Endpoint: Received data from collector: {metrics_data}")
        logger.info(f"FL Status Endpoint: max_rounds in response: {'max_rounds' in metrics_data if isinstance(metrics_data, dict) else 'N/A'}")
        
        if isinstance(metrics_data, dict) and "error" not in metrics_data:
            # Convert timestamp if needed
            timestamp = metrics_data.get("timestamp")
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp).isoformat()
            else:
                timestamp = timestamp or datetime.now().isoformat()
            
            # Debug logging
            logger.info(f"FL Status Endpoint: metrics_data keys: {list(metrics_data.keys())}")
            logger.info(f"FL Status Endpoint: max_rounds from collector: {metrics_data.get('max_rounds')}")
            
            # The collector's FL status endpoint already returns the correct format
            # Just pass through the data with any necessary field mapping
            max_rounds_value = metrics_data.get("max_rounds")
            logger.info(f"FL Status Endpoint: max_rounds_value extracted: {max_rounds_value} (type: {type(max_rounds_value)})")
            
            training_status = {
                "timestamp": timestamp,
                "training_active": metrics_data.get("training_active", False),
                "current_round": metrics_data.get("current_round", 0),
                "latest_accuracy": metrics_data.get("latest_accuracy", 0.0),
                "latest_loss": metrics_data.get("latest_loss", 0.0),
                "connected_clients": metrics_data.get("connected_clients", 0),
                "training_complete": metrics_data.get("training_complete", False),
                "data_source": metrics_data.get("data_source", "collector"),
                "fl_server_available": metrics_data.get("fl_server_available", False),
                "collector_monitoring": metrics_data.get("collector_monitoring", True),
                "stopped_by_policy": metrics_data.get("stopped_by_policy", False),  # Added policy-stopped field
            }
            
            # Explicitly add max_rounds with proper handling
            if max_rounds_value is not None:
                training_status["max_rounds"] = max_rounds_value
                logger.info(f"FL Status Endpoint: Added max_rounds to response: {max_rounds_value}")
            else:
                training_status["max_rounds"] = None
                logger.info("FL Status Endpoint: max_rounds is None, setting to None in response")
            
            logger.info(f"FL Status Endpoint: training_status keys: {list(training_status.keys())}")
            logger.info(f"FL Status Endpoint: max_rounds in training_status: {training_status.get('max_rounds')}")
            logger.info(f"FL Status Endpoint: training_status max_rounds type: {type(training_status.get('max_rounds'))}")
            logger.info(f"FL Status Endpoint: Full training_status dict: {training_status}")
            return training_status
        else:
            logger.warning(f"Collector returned error or invalid data: {metrics_data}")
            # Fall through to error handling below

    except Exception as e:
        logger.error(f"FL Status Endpoint: Error fetching FL training status: {e}")
        # Return mock status for demo purposes when collector is not available
        mock_status = {
            "timestamp": datetime.now().isoformat(),
            "training_active": True,
            "current_round": 45,
            "latest_accuracy": 0.8245,
            "latest_loss": 0.3521,
            "connected_clients": 5,
            "training_complete": False,
            "data_source": "mock",
            "fl_server_available": True,
            "collector_monitoring": False,
            "max_rounds": 50,
            "stopped_by_policy": False  # Added policy-stopped field
        }
        logger.info(f"FL Status Endpoint: Returning mock status due to error: {mock_status}")
        return mock_status

@router.get("/metrics/fl/rounds")
async def get_fl_rounds_enhanced(
    start_round: Optional[int] = None,
    end_round: Optional[int] = None,
    limit: Optional[int] = Query(1000, description="Maximum number of rounds to return", ge=1, le=5000),
    offset: Optional[int] = Query(0, description="Offset for pagination", ge=0),
    min_accuracy: Optional[float] = None,
    max_accuracy: Optional[float] = None,
    source: Optional[str] = Query("both", description="Data source", regex="^(collector|fl_server|both)$"),
    format: Optional[str] = Query("detailed", description="Response format", regex="^(detailed|summary)$"),
    sort_order: Optional[str] = Query("asc", description="Sort order", regex="^(asc|desc)$"),
    since_round: Optional[int] = None,
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get FL rounds with enhanced filtering - matches frontend expectations."""
    
    try:
        # Get FL rounds from collector using the working FL rounds endpoint
        rounds_response = await collector.get_fl_rounds(limit)
        
        # Extract rounds from response
        if isinstance(rounds_response, dict):
            rounds = rounds_response.get("rounds", [])
            latest_round_from_collector = rounds_response.get("latest_round", 0)
        else:
            logger.warning(f"Unexpected response type from collector: {type(rounds_response)}")
            rounds = []
            latest_round_from_collector = 0
        
        if not isinstance(rounds, list):
            logger.warning(f"Expected list from collector, got {type(rounds)}")
            rounds = []
        
        # Transform to expected format with proper field mapping
        formatted_rounds = []
        for metric in rounds:
            if not isinstance(metric, dict):
                continue
                
            round_num = metric.get("round", 0)
            accuracy = metric.get("accuracy", 0.0)
            
            # Apply filters
            if start_round is not None and round_num < start_round:
                continue
            if end_round is not None and round_num > end_round:
                continue
            if since_round is not None and round_num <= since_round:
                continue
            if min_accuracy is not None and accuracy < min_accuracy:
                continue
            if max_accuracy is not None and accuracy > max_accuracy:
                continue
                
            # FIXED: Properly map all fields expected by the frontend
            # Determine proper round status based on current training state
            round_status = "complete"  # Default to complete for finished rounds
            
            # Get current training status to determine which rounds are still training
            try:
                # Get current training status from the first metric or use a default approach
                if hasattr(collector, '_last_training_status'):
                    current_round = collector._last_training_status.get('current_round', 0)
                    training_active = collector._last_training_status.get('training_active', False)
                else:
                    # Fallback: determine from the data
                    current_round = max((m.get("round", 0) for m in rounds), default=0)
                    training_active = any(m.get("training_complete", True) == False for m in rounds)
                
                # Determine status based on round position and training state
                if round_num < current_round:
                    round_status = "complete"
                elif round_num == current_round and training_active:
                    round_status = "training"
                elif round_num == current_round and not training_active:
                    round_status = "complete"
                else:
                    round_status = "pending"
                    
            except Exception as status_error:
                logger.debug(f"Error determining round status: {status_error}")
                # Use the original status from metric if available
                round_status = metric.get("status", "complete")
            
            # FIXED: Properly extract client data - handle multiple field names from collector
            clients_connected = (
                metric.get("clients_connected", 0) or
                metric.get("clients", 0) or
                metric.get("connected_clients", 0) or
                0
            )
            
            # Ensure clients_connected is an integer
            try:
                clients_connected = int(clients_connected) if clients_connected is not None else 0
            except (ValueError, TypeError):
                clients_connected = 0
            
            formatted_round = {
                "timestamp": metric.get("timestamp", datetime.now().isoformat()),
                "round": round_num,
                "accuracy": accuracy,
                "loss": metric.get("loss", 0.0),
                "clients_connected": clients_connected,
                "clients_total": metric.get("clients_total", clients_connected),
                "training_complete": metric.get("training_complete", False),
                "model_size_mb": metric.get("model_size_mb", 0.0),
                "status": round_status,  # Use the properly determined status
                # Enhanced FL server metrics - properly handle missing fields
                "training_duration": metric.get("training_duration"),
                "successful_clients": metric.get("successful_clients"),
                "failed_clients": metric.get("failed_clients"),
                "aggregation_duration": metric.get("aggregation_duration"),
                "evaluation_duration": metric.get("evaluation_duration"),
                # Additional fields that might be useful
                "clients": clients_connected,  # Alias for backward compatibility
                "data_source": metric.get("data_source", "collector")
            }
            formatted_rounds.append(formatted_round)
        
        # Apply sorting
        if sort_order == "desc":
            formatted_rounds.sort(key=lambda x: x["round"], reverse=True)
        else:
            formatted_rounds.sort(key=lambda x: x["round"])
        
        # Calculate metadata
        total_rounds_available = len(formatted_rounds)
        latest_round = max(latest_round_from_collector, max((r["round"] for r in formatted_rounds), default=0))
        
        response_data = {
            "rounds": formatted_rounds,
            "total_rounds": total_rounds_available,
            "returned_rounds": len(formatted_rounds),
            "latest_round": latest_round,
            "metadata": {
                "source": source,
                "format": format,
                "sort_order": sort_order,
                "filters_applied": {
                    "start_round": start_round,
                    "end_round": end_round,
                    "since_round": since_round,
                    "min_accuracy": min_accuracy,
                    "max_accuracy": max_accuracy
                },
                "timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"FL rounds endpoint: returning {len(formatted_rounds)} rounds (latest: {latest_round})")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in FL rounds endpoint: {e}")
        return {
            "rounds": [],
            "total_rounds": 0,
            "returned_rounds": 0,
            "latest_round": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/config")
async def get_fl_configuration(collector: CollectorApiClient = Depends(get_collector_client)):
    """
    Get comprehensive FL configuration from collector including:
    - FL server configuration (model, dataset, rounds)
    - Policy engine parameters
    - Training hyperparameters
    - Model configuration
    - Federation settings
    """
    try:
        logger.info("FL Monitoring API: Getting FL configuration from collector")
        
        # Get configuration from collector's /api/metrics/fl/config endpoint
        response = await collector.get_fl_configuration()
        
        if not isinstance(response, dict):
            logger.error(f"Unexpected FL config response type from collector: {type(response)}")
            raise HTTPException(status_code=502, detail="Invalid FL configuration response format from collector")
        
        # Check if collector returned an error
        if "error" in response:
            logger.warning(f"Collector returned FL config error: {response['error']}")
            raise HTTPException(status_code=502, detail=f"Collector FL config error: {response['error']}")
        
        # The collector returns the configuration in the expected format
        # Validate required fields exist
        required_sections = ["fl_server", "policy_engine", "training_parameters", "model_config", "federation_config"]
        for section in required_sections:
            if section not in response:
                logger.warning(f"Missing section '{section}' in FL config response")
                response[section] = {}
        
        # Ensure metadata exists
        if "metadata" not in response:
            response["metadata"] = {
                "execution_time_ms": 0,
                "data_sources_used": ["collector"],
                "config_completeness": "unknown",
                "timestamp": datetime.now().isoformat(),
                "api_version": "2.0"
            }
        
        logger.info(f"FL Monitoring API: Successfully retrieved FL configuration with status: {response.get('status', 'unknown')}")
        logger.info(f"FL config data sources: {response.get('data_sources', [])}")
        logger.info(f"FL config completeness: {response.get('metadata', {}).get('config_completeness', 'unknown')}")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"FL Monitoring API: Error fetching FL configuration: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch FL configuration: {str(e)}")

@router.get("/debug/raw-status")
async def debug_raw_fl_status(collector: CollectorApiClient = Depends(get_collector_client)):
    """Debug endpoint to see the raw collector FL status response."""
    try:
        raw_response = await collector.get_fl_status()
        return {
            "raw_collector_response": raw_response,
            "response_type": str(type(raw_response)),
            "has_max_rounds": "max_rounds" in raw_response if isinstance(raw_response, dict) else False,
            "max_rounds_value": raw_response.get("max_rounds") if isinstance(raw_response, dict) else None,
            "collector_base_url": collector.base_url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "collector_base_url": collector.base_url,
            "timestamp": datetime.now().isoformat()
        } 