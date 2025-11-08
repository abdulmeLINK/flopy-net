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

from fastapi import APIRouter, Query, Depends, Body, HTTPException
from typing import List, Optional, Dict, Any
from app.services.collector_client import CollectorApiClient
from app.models.collector_models import FrontendMetricQuery
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_collector_client():
    return CollectorApiClient()

# Helper function to extract component from a metric object
def get_component_from_metric(metric_obj: Dict[str, Any]) -> Optional[str]:
    data_dict = metric_obj.get('data', {})
    if isinstance(data_dict, dict):
        # Check common component fields within 'data'
        for key in ['component', 'source', 'instance_id', 'server_name', 'node_name', 'interface']:
            if data_dict.get(key):
                return str(data_dict[key])
    # Check common component fields at the top level of the metric
    for key in ['component', 'source_component', 'source']:
            if metric_obj.get(key):
                return str(metric_obj[key])
    return None

@router.get("/test")
async def test_metrics_connection(collector: CollectorApiClient = Depends(get_collector_client)):
    """Test endpoint to verify collector metrics API connectivity."""
    try:
        # Test basic metrics endpoint
        metrics_data = await collector.get_metrics(params={"limit": 5})
        
        # Test FL metrics endpoint 
        fl_metrics = await collector.get_fl_metrics({"limit": 5})
        
        # Test latest metrics
        latest_metrics = await collector.get_latest_metrics(type_filter="fl_server")
        
        return {
            "status": "success",
            "collector_url": collector.base_url,
            "metrics_sample": metrics_data.get("metrics", [])[:2],  # First 2 metrics
            "metrics_count": len(metrics_data.get("metrics", [])),
            "fl_metrics_count": len(fl_metrics.get("metrics", [])),
            "latest_metrics": latest_metrics
        }
    except Exception as e:
        logger.error(f"Error testing metrics connection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test metrics connection: {str(e)}")

@router.get("/types")
async def get_metric_types(collector: CollectorApiClient = Depends(get_collector_client)) -> List[str]:
    """Get all available metric types from the collector."""
    try:
        metrics_data = await collector.get_metrics()

        types = set()
        
        if metrics_data and "metrics" in metrics_data:
            for metric in metrics_data["metrics"]:
                # Prioritize top-level 'metric_type' as per collector storage
                metric_type_val = metric.get("metric_type")
                if metric_type_val:
                    types.add(str(metric_type_val))
                else:
                    # Fallback to checking 'type' within 'data' or at top level
                    data = metric.get("data", {})
                    if isinstance(data, dict) and data.get("type"):
                        types.add(str(data["type"]))
                    elif metric.get("type"):
                        types.add(str(metric["type"]))
        
        return sorted(list(types))
    except Exception as e:
        logger.error(f"Error getting metric types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metric types: {str(e)}")

@router.get("/components")
async def get_metric_components(collector: CollectorApiClient = Depends(get_collector_client)) -> List[str]:
    """Get all available components from the collector."""
    try:
        metrics_data = await collector.get_metrics()

        components = set()
        
        if metrics_data and "metrics" in metrics_data:
            for metric in metrics_data["metrics"]:
                component_name = get_component_from_metric(metric)
                if component_name:
                    components.add(component_name)
        
        return sorted(list(components))
    except Exception as e:
        logger.error(f"Error getting components: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metric components: {str(e)}")

@router.post("/query")
async def query_metrics(
    query_payload: FrontendMetricQuery = Body(...),
    collector: CollectorApiClient = Depends(get_collector_client)
):
    try:
        params = {}
        if query_payload.metric_types:
            params['metric_type'] = query_payload.metric_types[0]
        if query_payload.start_time:
            params['start_time'] = query_payload.start_time
        if query_payload.end_time:
            params['end_time'] = query_payload.end_time
        if query_payload.components:
            params['source_component'] = query_payload.components[0]

        metrics_data = await collector.get_metrics(params=params)

        processed_metrics = []
        if isinstance(metrics_data, dict) and "metrics" in metrics_data:
            for m in metrics_data.get("metrics", []):
                if not isinstance(m, dict):
                    continue # Skip if metric is not a dict

                # Basic transformation
                transformed_metric = {
                    "timestamp": m.get("timestamp"),
                    "metric_type": m.get("metric_type"),
                    "component": None, # Placeholder
                    "value": None,     # Placeholder
                    "raw_data": m.get("data") # Keep raw data for frontend to inspect
                }

                data_field = m.get("data")
                if isinstance(data_field, dict):
                    transformed_metric["component"] = data_field.get("source_component", data_field.get("component"))
                    
                    # Heuristic to find a 'value'
                    if "value" in data_field:
                        transformed_metric["value"] = data_field["value"]
                    elif "count" in data_field:
                        transformed_metric["value"] = data_field["count"]
                    elif "average" in data_field:
                        transformed_metric["value"] = data_field["average"]
                    else: # Try to find the first numerical value
                        for val in data_field.values():
                            if isinstance(val, (int, float)):
                                transformed_metric["value"] = val
                                break
                
                # Component filtering (if component query param was used)
                if query_payload.components:
                    metric_component_from_payload = params.get('source_component')
                    # Check a few common places for component info in the raw data
                    metric_component_explicit = transformed_metric["component"]
                    metric_component_from_type = m.get("metric_type", "").split('.')[0] # e.g. FL_SERVER from FL_SERVER.accuracy
                    
                    if metric_component_from_payload and (metric_component_explicit == metric_component_from_payload or metric_component_from_type == metric_component_from_payload):
                        processed_metrics.append(transformed_metric)
                else:
                    processed_metrics.append(transformed_metric)

        return {
            "metrics": processed_metrics,
            "total": len(processed_metrics),
            "limit": params.get("limit", 100),
            "offset": params.get("offset", 0)
        }
    except Exception as e:
        logger.error(f"Error querying metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to query metrics: {str(e)}") 