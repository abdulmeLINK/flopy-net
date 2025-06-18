from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional, List
from app.services.collector_client import CollectorApiClient
from app.core.topology_loader import TopologyLoader
import os
import time
import datetime
import logging
import requests

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_collector_client():
    return CollectorApiClient()

async def get_gns3_client(request: Request):
    """Dependency to get the GNS3 client from app state."""
    # Return None if GNS3 client is not available
    return getattr(request.app.state, 'gns3_client', None)

async def get_gns3_client_or_error(request: Request):
    """Dependency to get the GNS3 client or raise an error if not available."""
    client = await get_gns3_client(request)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "GNS3 service is not available",
                "error_type": "ServiceUnavailable",
                "service": "gns3"
            }
        )
    return client

@router.get("/metrics")
async def get_network_metrics_data(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get network performance metrics via collector."""
    data = await collector.get_performance_metrics()
    return data

@router.get("/topology")
async def get_network_topology():
    # For now, load from a default topology file (could be made dynamic)
    import os
    default_topology_path = os.path.join(os.path.dirname(__file__), '../../../config/topology/basic_topology.json')
    topology = TopologyLoader.load_from_file(default_topology_path)
    return topology

@router.get("/topology/active")
async def get_active_network_topology(
    request: Request,
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get actual network topology from collector (which aggregates GNS3 and SDN data)."""
    source = request.query_params.get("source", "all")
    format_type = request.query_params.get("format", "detailed")
    include_metrics = request.query_params.get("include_metrics", "true").lower() == "true"
    
    try:
        # Get topology data from collector
        topology_data = await collector.get_network_topology(
            source=source,
            include_metrics=include_metrics,
            format_type=format_type
        )
        
        # Check for errors in the response
        if "error" in topology_data:
            if "not available" in topology_data["error"] or "not active" in topology_data["error"]:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": "Network monitoring service is not available",
                        "error": topology_data["error"],
                        "error_type": "ServiceUnavailable"
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": "Failed to retrieve network topology",
                        "error": topology_data["error"],
                        "error_type": "TopologyError"
                    }
                )
        
        # Transform the collector response to match the expected format
        if format_type == "summary":
            return topology_data
        
        # For detailed format, ensure compatibility with existing frontend
        response = {
            "project_id": topology_data.get("project_info", {}).get("id", "unknown"),
            "project_name": topology_data.get("project_info", {}).get("name", "SDN Topology"),
            "nodes": topology_data.get("nodes", []),
            "links": topology_data.get("links", []),
            "switches": topology_data.get("switches", []),
            "hosts": topology_data.get("hosts", []),
            "node_count": topology_data.get("statistics", {}).get("total_nodes", 0),
            "link_count": topology_data.get("statistics", {}).get("total_links", 0),
            "switch_count": topology_data.get("statistics", {}).get("total_switches", 0),
            "host_count": topology_data.get("statistics", {}).get("total_hosts", 0),
            "timestamp": datetime.datetime.now().isoformat(),
            "collection_time": topology_data.get("collection_time"),
            "statistics": topology_data.get("statistics", {}),
            "source": source
        }
        
        # Include performance metrics if available
        if include_metrics and "metrics" in topology_data:
            response["metrics"] = topology_data["metrics"]
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception("Error retrieving network topology from collector")
        
        error_detail = {
            "message": "Failed to retrieve network topology",
            "error": str(e),
            "error_type": type(e).__name__
        }
        
        logger.error(f"Network topology error details: {error_detail}")
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )

@router.get("/topology/live")
async def get_live_network_topology(
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get live network topology with real-time updates from collector."""
    try:
        # Get live topology data from collector
        topology_data = await collector.get_live_network_topology()
        
        # Check for errors in the response
        if "error" in topology_data:
            if "not available" in topology_data["error"]:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": "Live network monitoring service is not available",
                        "error": topology_data["error"],
                        "error_type": "ServiceUnavailable"
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": "Failed to retrieve live network topology",
                        "error": topology_data["error"],
                        "error_type": "LiveTopologyError"
                    }
                )
        
        # Transform the collector response
        topology = topology_data.get("topology", {})
        response = {
            "nodes": topology.get("nodes", []),
            "links": topology.get("links", []),
            "switches": topology.get("switches", []),
            "hosts": topology.get("hosts", []),
            "statistics": topology_data.get("statistics", {}),
            "timestamp": topology_data.get("timestamp"),
            "source": "live_query"
        }
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception("Error retrieving live network topology from collector")
        
        error_detail = {
            "message": "Failed to retrieve live network topology",
            "error": str(e),
            "error_type": type(e).__name__
        }
        
        logger.error(f"Live network topology error details: {error_detail}")
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )



@router.get("/topology/active/links/{link_id}")
async def get_link_details(
    link_id: str, 
    gns3_client = Depends(get_gns3_client_or_error)
):
    # Get the projects list
    projects = await gns3_client.get_projects()
    if not projects:
        raise HTTPException(status_code=404, detail="No GNS3 projects found")
    
    # Use the first project for now
    project_id = projects[0].get("project_id")
    
    link = await gns3_client.get_link(project_id, link_id)
    if not link:
        raise HTTPException(status_code=404, detail=f"Link {link_id} not found")    
    return link

# Add more placeholders for POST, PUT, DELETE on topology nodes/links as per plan

@router.post("/nodes/{node_id}/action")
async def perform_node_action(node_id: str, action: Dict[str, Any]):
    # Placeholder for implementing node actions (e.g., start, stop, restart) via GNS3 API
    return {
        "message": f"Action '{action.get('type', 'unknown')}' on node '{node_id}' not yet implemented.",
        "status": "pending_implementation"
    }

@router.get("/projects")
async def get_gns3_projects(
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Get all GNS3 projects."""
    projects = await gns3_client.get_projects()
    return projects

@router.get("/projects/{project_id}/nodes")
async def get_project_nodes(
    project_id: str,
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Get all nodes in a GNS3 project."""
    nodes = await gns3_client.get_nodes(project_id)
    return nodes

@router.get("/projects/{project_id}/links")
async def get_project_links(
    project_id: str,
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Get all links in a GNS3 project."""
    links = await gns3_client.get_links(project_id)
    return links

@router.get("/projects/{project_id}/nodes/{node_id}")
async def get_node_details(
    project_id: str,
    node_id: str,
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Get details for a specific node."""
    node = await gns3_client.get_node(project_id, node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return node

@router.get("/projects/{project_id}/nodes/{node_id}/console")
async def get_node_console(
    project_id: str,
    node_id: str,
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Get console information for a node."""
    console = await gns3_client.get_node_console(project_id, node_id)
    return console

@router.post("/projects/{project_id}/nodes/{node_id}/start")
async def start_node(
    project_id: str,
    node_id: str,
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Start a node."""
    success = await gns3_client.start_node(project_id, node_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to start node {node_id}")
    return {"status": "success", "message": f"Node {node_id} started"}

@router.post("/projects/{project_id}/nodes/{node_id}/stop")
async def stop_node(
    project_id: str,
    node_id: str,
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Stop a node."""
    success = await gns3_client.stop_node(project_id, node_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop node {node_id}")
    return {"status": "success", "message": f"Node {node_id} stopped"}

@router.get("/templates")
async def get_gns3_templates(
    gns3_client = Depends(get_gns3_client_or_error)
):
    """Get all GNS3 templates."""
    templates = await gns3_client.get_templates()
    return templates

@router.get("/status")
async def get_network_status(collector: CollectorApiClient = Depends(get_collector_client)) -> Dict[str, Any]:
    """Get comprehensive network status including SDN metrics and health scoring."""
    try:
        # Get latest network metrics
        network_data = await collector.get_latest_metrics(type_filter="network")
        
        if not isinstance(network_data, dict) or "metrics" not in network_data:
            return {
                "status": "error",
                "message": "No network metrics available",
                "health_score": 0,
                "last_updated": None
            }
        
        metrics = network_data.get("metrics", {})
        
        # Calculate network health score
        health_info = calculate_network_health(metrics)
        
        # Comprehensive status response
        status_response = {
            "status": metrics.get("status", "unknown"),
            "gns3_status": {
                "project_name": metrics.get("project_name"),
                "project_status": metrics.get("project_status"),
                "connection_status": metrics.get("status")
            },
            "topology": {
                "nodes_total": metrics.get("node_count", 0),
                "links_total": metrics.get("link_count", 0),
                "nodes_by_status": metrics.get("node_statuses", {}),
                "nodes_by_type": metrics.get("node_types", {})
            },
            "sdn_controller": {
                "status": metrics.get("sdn_status", "unknown"),
                "switches_count": metrics.get("switches_count", 0),
                "total_flows": metrics.get("total_flows", 0),
                "total_ports": metrics.get("total_ports", 0),
                "error": metrics.get("sdn_error")
            },
            "performance": {
                "avg_latency_ms": metrics.get("avg_latency_ms", 0),
                "packet_loss_percent": metrics.get("packet_loss_percent", 0),
                "bandwidth_utilization_percent": metrics.get("bandwidth_utilization_percent", 0)
            },
            "health": health_info,
            "last_updated": metrics.get("collection_timestamp"),
            "details": metrics.get("switch_details", {})
        }
        
        return status_response
        
    except Exception as e:
        logger.error(f"Error getting network status: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "health_score": 0,
            "last_updated": None
        }

def calculate_network_health(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate network health score based on metrics."""
    score = 100
    issues = []
    
    # Check GNS3 connectivity
    if metrics.get("status") != "connected":
        score -= 30
        issues.append("GNS3 disconnected")
    
    # Check active nodes
    node_count = metrics.get("node_count", 0)
    started_nodes = metrics.get("node_statuses", {}).get("started", 0)
    if node_count > 0:
        node_health = (started_nodes / node_count) * 100
        if node_health < 80:
            score -= (80 - node_health) * 0.5
            issues.append(f"Only {started_nodes}/{node_count} nodes running")
    
    # Check SDN metrics
    sdn_status = metrics.get("sdn_status")
    if sdn_status == "connected":
        # Check packet loss
        packet_loss = metrics.get("packet_loss_percent", 0)
        if packet_loss > 5:
            score -= packet_loss * 2
            issues.append(f"High packet loss: {packet_loss}%")
        
        # Check latency
        latency = metrics.get("avg_latency_ms", 0)
        if latency > 100:
            score -= (latency - 100) * 0.1
            issues.append(f"High latency: {latency}ms")
        
        # Check bandwidth utilization
        bandwidth_util = metrics.get("bandwidth_utilization_percent", 0)
        if bandwidth_util > 80:
            score -= (bandwidth_util - 80) * 0.5
            issues.append(f"High bandwidth utilization: {bandwidth_util}%")
            
    elif sdn_status == "error":
        score -= 20
        issues.append("SDN controller unavailable")
    
    # Ensure score doesn't go below 0
    score = max(0, round(score))
    
    # Determine status
    if score >= 90:
        status = "excellent"
        color = "success"
    elif score >= 75:
        status = "good"
        color = "success"
    elif score >= 50:
        status = "fair"
        color = "warning"
    elif score >= 25:
        status = "poor"
        color = "warning"
    else:
        status = "critical"
        color = "error"
    
    return {
        "health_score": score,
        "status": status,
        "color": color,
        "issues": issues,
        "recommendations": generate_recommendations(issues)
    }

def generate_recommendations(issues: List[str]) -> List[str]:
    """Generate recommendations based on network issues."""
    recommendations = []
    
    for issue in issues:
        if "disconnected" in issue.lower():
            recommendations.append("Check GNS3 server connectivity and project status")
        elif "nodes running" in issue.lower():
            recommendations.append("Start stopped nodes or investigate node failures")
        elif "packet loss" in issue.lower():
            recommendations.append("Check network links and switch configurations")
        elif "latency" in issue.lower():
            recommendations.append("Optimize routing paths and check for network congestion")
        elif "bandwidth" in issue.lower():
            recommendations.append("Consider load balancing or upgrading link capacity")
        elif "sdn controller" in issue.lower():
            recommendations.append("Verify SDN controller service is running and accessible")
    
    if not recommendations:
        recommendations.append("Network is operating normally")
    
    return recommendations

@router.get("/metrics/summary")
async def get_network_metrics_summary(
    collector: CollectorApiClient = Depends(get_collector_client),
    hours: int = 24
) -> Dict[str, Any]:
    """Get network metrics summary over a specified time period."""
    try:
        # Calculate time range
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=hours)
        
        # Get historical network metrics
        params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": 1000
        }
        
        historical_data = await collector.get_metrics(type_filter="network", params=params)
        
        if not isinstance(historical_data, dict) or "metrics" not in historical_data:
            return {"error": "No historical metrics available"}
        
        metrics_list = historical_data.get("metrics", [])
        
        if not metrics_list:
            return {"error": "No metrics found for the specified time period"}
        
        # Calculate summary statistics
        summary = calculate_metrics_summary(metrics_list, hours)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting network metrics summary: {str(e)}")
        return {"error": str(e)}

def calculate_metrics_summary(metrics_list: List[Dict[str, Any]], hours: int) -> Dict[str, Any]:
    """Calculate summary statistics from historical metrics."""
    if not metrics_list:
        return {}
    
    # Extract values for analysis
    latencies = [m.get("avg_latency_ms", 0) for m in metrics_list if m.get("avg_latency_ms") is not None]
    packet_losses = [m.get("packet_loss_percent", 0) for m in metrics_list if m.get("packet_loss_percent") is not None]
    node_counts = [m.get("node_count", 0) for m in metrics_list]
    link_counts = [m.get("link_count", 0) for m in metrics_list]
    
    # Calculate statistics
    summary = {
        "time_period_hours": hours,
        "data_points": len(metrics_list),
        "latency": {
            "min": min(latencies) if latencies else 0,
            "max": max(latencies) if latencies else 0,
            "avg": round(sum(latencies) / len(latencies), 2) if latencies else 0
        },
        "packet_loss": {
            "min": min(packet_losses) if packet_losses else 0,
            "max": max(packet_losses) if packet_losses else 0,
            "avg": round(sum(packet_losses) / len(packet_losses), 2) if packet_losses else 0
        },
        "topology": {
            "nodes": {
                "min": min(node_counts) if node_counts else 0,
                "max": max(node_counts) if node_counts else 0,
                "avg": round(sum(node_counts) / len(node_counts), 1) if node_counts else 0
            },
            "links": {
                "min": min(link_counts) if link_counts else 0,
                "max": max(link_counts) if link_counts else 0,
                "avg": round(sum(link_counts) / len(link_counts), 1) if link_counts else 0
            }
        },
        "availability": calculate_availability(metrics_list),
        "last_updated": metrics_list[-1].get("collection_timestamp") if metrics_list else None
    }
    
    return summary

def calculate_availability(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate network availability metrics."""
    if not metrics_list:
        return {"uptime_percent": 0, "connected_periods": 0}
    
    connected_count = sum(1 for m in metrics_list if m.get("status") == "connected")
    total_count = len(metrics_list)
    
    uptime_percent = (connected_count / total_count) * 100 if total_count > 0 else 0
    
    return {
        "uptime_percent": round(uptime_percent, 2),
        "connected_periods": connected_count,
        "total_periods": total_count
    }

@router.get("/hosts")
async def get_network_hosts(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get detailed information about network hosts."""
    try:
        topology_data = await collector.get_live_network_topology()
        hosts = topology_data.get("topology", {}).get("hosts", [])
        
        # Enhance host data with additional statistics
        enhanced_hosts = []
        for host in hosts:
            enhanced_host = {
                **host,
                "status": "active",  # Could be enhanced with real status
                "last_seen": datetime.datetime.now().isoformat(),
                "traffic_stats": {
                    "bytes_sent": 0,  # Could be filled from real data
                    "bytes_received": 0,
                    "packets_sent": 0,
                    "packets_received": 0
                }
            }
            enhanced_hosts.append(enhanced_host)
        
        return {
            "hosts": enhanced_hosts,
            "total_count": len(enhanced_hosts),
            "timestamp": topology_data.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Error getting network hosts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/switches")
async def get_network_switches(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get detailed information about network switches."""
    try:
        topology_data = await collector.get_live_network_topology()
        switches = topology_data.get("topology", {}).get("switches", [])
        
        # Enhance switch data with additional statistics
        enhanced_switches = []
        for switch in switches:
            enhanced_switch = {
                **switch,
                "status": "active",
                "uptime": "unknown",  # Could be filled from real data
                "flow_count": 0,  # Could be filled from SDN controller
                "packet_count": 0,
                "byte_count": 0,
                "port_stats": []
            }
            
            # Process port information
            for port in switch.get("ports", []):
                port_stat = {
                    **port,
                    "status": "up" if port.get("state", 0) != 1 else "down",
                    "rx_bytes": 0,  # Could be filled from real data
                    "tx_bytes": 0,
                    "rx_packets": 0,
                    "tx_packets": 0
                }
                enhanced_switch["port_stats"].append(port_stat)
            
            enhanced_switches.append(enhanced_switch)
        
        return {
            "switches": enhanced_switches,
            "total_count": len(enhanced_switches),
            "timestamp": topology_data.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Error getting network switches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links")
async def get_network_links(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get detailed information about network links."""
    try:
        topology_data = await collector.get_live_network_topology()
        links = topology_data.get("topology", {}).get("links", [])
        
        # Enhance link data with additional statistics
        enhanced_links = []
        for link in links:
            enhanced_link = {
                **link,
                "status": "active",
                "utilization": 0.0,  # Could be filled from real data
                "latency": 0.0,
                "packet_loss": 0.0,
                "bandwidth": "unknown"
            }
            enhanced_links.append(enhanced_link)
        
        return {
            "links": enhanced_links,
            "total_count": len(enhanced_links),
            "timestamp": topology_data.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Error getting network links: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_network_statistics(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get comprehensive network statistics."""
    try:
        topology_data = await collector.get_live_network_topology()
        
        # Get basic counts
        topology = topology_data.get("topology", {})
        hosts = topology.get("hosts", [])
        switches = topology.get("switches", [])
        links = topology.get("links", [])
        
        # Calculate additional statistics
        total_ports = sum(len(switch.get("ports", [])) for switch in switches)
        active_ports = sum(
            1 for switch in switches 
            for port in switch.get("ports", []) 
            if port.get("state", 0) != 1
        )
        
        statistics = {
            "topology": {
                "total_nodes": len(topology.get("nodes", [])),
                "total_hosts": len(hosts),
                "total_switches": len(switches),
                "total_links": len(links),
                "total_ports": total_ports,
                "active_ports": active_ports
            },
            "health": {
                "overall_status": "healthy" if switches else "warning",
                "switch_connectivity": len(switches) > 0,
                "host_connectivity": len(hosts) > 0,
                "link_redundancy": len(links) > len(switches) if switches else False
            },
            "performance": {
                "average_latency": 0.0,  # Could be calculated from real data
                "total_bandwidth": "unknown",
                "utilization": 0.0
            },
            "timestamp": topology_data.get("timestamp"),
            "source": topology_data.get("source", "unknown")
        }
        
        return statistics
    except Exception as e:
        logger.error(f"Error getting network statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/flows")
async def get_network_flows(collector: CollectorApiClient = Depends(get_collector_client)):
    """Get OpenFlow flows from all switches."""
    try:
        # Get topology data first to get switch information
        topology_data = await collector.get_live_network_topology()
        
        if "error" in topology_data:            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Network monitoring service is not available",
                    "error": topology_data["error"],
                    "error_type": "ServiceUnavailable"
                }
            )
        
        switches = topology_data.get("topology", {}).get("switches", [])
        
        # Get flows from collector service
        flows_data = await collector.get_network_flows()
        
        if "error" in flows_data:
            logger.warning(f"Error getting flows from collector: {flows_data['error']}")
            # Return empty flows structure
            flows_data = {
                "flows": [],
                "summary": {
                    "total_flows": 0,
                    "switches_with_flows": 0,
                    "table_stats": {}
                }
            }
        
        # Enhance flows with switch names if available
        all_flows = flows_data.get("flows", [])
        for flow in all_flows:
            switch_dpid = flow.get("switch_dpid")
            if switch_dpid:
                # Try to find switch name from topology
                for switch in switches:
                    if str(switch.get("dpid")) == str(switch_dpid):
                        flow["switch_name"] = switch.get("name", f"Switch-{switch_dpid}")
                        break
                else:
                    flow["switch_name"] = f"Switch-{switch_dpid}"
        
        # Use flow summary from collector service and add policy flows
        flow_summary = flows_data.get("summary", {
            "total_flows": len(all_flows),
            "switches_with_flows": len(set(flow.get("switch_dpid") for flow in all_flows)),
            "table_stats": {}
        })
        
        # Add policy flows categorization
        flow_summary["policy_flows"] = []
        for flow in all_flows:
            priority = flow.get("priority", 0)
            if priority > 100:  # Assuming policy flows have higher priority
                flow_summary["policy_flows"].append(flow)
        
        return {
            "flows": all_flows,
            "summary": flow_summary,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "source": "collector_service"
        }
        
    except Exception as e:
        logger.error(f"Error getting network flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/metrics")
async def get_network_performance_metrics(
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get detailed network performance metrics including real bandwidth and flow statistics."""
    try:
        # Get performance metrics from collector using the new dedicated endpoint
        metrics_data = await collector.get_performance_metrics()
        
        if "error" in metrics_data:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Network performance metrics service is not available",
                    "error": metrics_data["error"],
                    "error_type": "ServiceUnavailable"
                }
            )        # Extract performance metrics from the collector response format
        bandwidth_info = metrics_data.get("bandwidth", {})
        latency_info = metrics_data.get("latency", {})
        flows_info = metrics_data.get("flows", {})
        ports_info = metrics_data.get("ports", {})
        totals_info = metrics_data.get("totals", {})
        rates_info = metrics_data.get("rates", {})
        health_score = metrics_data.get("health_score", 0)
        network_health_info = metrics_data.get("network_health", {})
        
        # Process port statistics
        port_summary = {
            "total_ports": ports_info.get("total", 0),
            "active_ports": ports_info.get("up", 0),
            "ports_with_errors": ports_info.get("errors", 0),
            "total_packets": {
                "rx": totals_info.get("packets_transferred", 0) // 2,  # Estimate split
                "tx": totals_info.get("packets_transferred", 0) // 2
            },
            "total_errors": {
                "rx": totals_info.get("total_errors", 0) // 2,  # Estimate split
                "tx": totals_info.get("total_errors", 0) // 2
            }
        }
        
        # Calculate flow efficiency metrics
        total_flows = flows_info.get("total", 0)
        active_flows = flows_info.get("active", 0)
        flow_efficiency = (active_flows / total_flows * 100) if total_flows > 0 else 0
        
        # Calculate bandwidth values for compatibility
        current_total_bps = bandwidth_info.get("current_total_bps", 0)
        current_average_bps = bandwidth_info.get("current_average_bps", 0)
        peak_bandwidth_bps = bandwidth_info.get("peak_bandwidth_bps", 0)
        
        # Convert to Mbps for display
        total_mbps = current_total_bps / 1000000 if current_total_bps > 0 else 0
        average_mbps = current_average_bps / 1000000 if current_average_bps > 0 else 0
        max_mbps = peak_bandwidth_bps / 1000000 if peak_bandwidth_bps > 0 else 0
        
        # Get values directly from collector response
        total_packets = totals_info.get("packets_transferred", 0)
        total_bytes = totals_info.get("bytes_transferred", 0)
        uptime_seconds = totals_info.get("uptime_seconds", 3600)
        
        # Get rates directly from collector
        packets_per_second = rates_info.get("packets_per_second", 0)
        bytes_per_second = rates_info.get("bytes_per_second", 0)
        flows_per_hour = rates_info.get("flows_per_hour", 0)
        
        response = {
            "timestamp": metrics_data.get("timestamp", time.time()),
            "bandwidth": {
                "total_mbps": total_mbps,
                "average_mbps": average_mbps,
                "max_mbps": max_mbps,
                "utilization_percent": min(100, (total_mbps / max(max_mbps, 1)) * 100) if max_mbps > 0 else 0
            },
            "latency": {
                "average_ms": latency_info.get("average_ms", 0),
                "min_ms": latency_info.get("min_ms", 0),
                "max_ms": latency_info.get("max_ms", 0),
                "status": "good" if latency_info.get("average_ms", 0) < 50 else "high"
            },
            "flows": {
                "total": total_flows,
                "active": active_flows,
                "efficiency_percent": round(flow_efficiency, 2),
                "per_switch_average": flows_info.get("per_switch_average", {})
            },
            "ports": {
                "total_ports": port_summary["total_ports"],
                "active_ports": port_summary["active_ports"],
                "ports_with_errors": port_summary["ports_with_errors"],
                "total_packets": {
                    "rx": total_packets // 2,  # Estimate split
                    "tx": total_packets // 2
                },
                "total_errors": {
                    "rx": totals_info.get("total_errors", 0) // 2,
                    "tx": totals_info.get("total_errors", 0) // 2
                }
            },
            "network_health": {
                "score": network_health_info.get("score", health_score),
                "status": network_health_info.get("status", "fair"),
                "factors": network_health_info.get("factors", {})
            },
            "detailed_stats": {
                "flow_statistics": flows_info,
                "port_statistics": ports_info
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving network performance metrics")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to retrieve network performance metrics",
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

@router.get("/flows/statistics")
async def get_flow_statistics(
    collector: CollectorApiClient = Depends(get_collector_client)
):
    """Get detailed flow statistics from all switches."""
    try:
        # Get flow statistics from collector using the new dedicated endpoint
        flow_data = await collector.get_flow_statistics()
        
        if "error" in flow_data:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Flow statistics service is not available",
                    "error": flow_data["error"],
                    "error_type": "ServiceUnavailable"
                }
            )
        
        flow_stats = flow_data.get("flow_statistics", {})
        utilization = flow_data.get("utilization_metrics", {})
        
        response = {
            "timestamp": flow_data.get("collection_timestamp", time.time()),
            "summary": {
                "total_flows": flow_stats.get("total_flows", 0),
                "active_flows": flow_stats.get("active_flows", 0),
                "inactive_flows": flow_stats.get("total_flows", 0) - flow_stats.get("active_flows", 0),
                "switches_count": len(flow_stats.get("flows_per_switch", {})),
                "efficiency_percent": utilization.get("efficiency_percentage", 0),
                "efficiency_rating": utilization.get("efficiency_rating", "poor")
            },
            "distribution": {
                "by_priority": flow_stats.get("priority_distribution", {}),
                "by_table": flow_stats.get("table_distribution", {}),
                "by_switch": flow_stats.get("flows_per_switch", {})
            },
            "detailed_flows": flow_stats.get("flows", []),
            "utilization_metrics": utilization
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving flow statistics")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to retrieve flow statistics",
                "error": str(e),
                "error_type": type(e).__name__
            }
        )