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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from fastapi.responses import JSONResponse
import time
from pathlib import Path
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, BackgroundTasks, Query
from contextlib import asynccontextmanager
import asyncio
import aiohttp

# Import for caching
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
# from fastapi_cache.backends.redis import RedisBackend # Alternative

# Setup imports to ensure src is in the Python path
from .core.imports import setup_imports, debug_imports
setup_imports()

from .api.endpoints import (
    overview, fl_monitoring, network, policy, 
    events, scenarios, logs, config_display,
    metrics_explorer, topology_websocket
)
from .core.config import settings

# Attempt to import specific clients, handling potential ModuleNotFoundError
try:
    from .services.collector_client import CollectorApiClient # Corrected path
    from .services.gns3_client import AsyncGNS3Client
    from .services.policy_client import AsyncPolicyEngineClient # Corrected class name
except ModuleNotFoundError as e:
    pass

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

# Global connection status tracking
connection_status = {
    "policy_engine": {"connected": False, "last_check": None, "error": None},
    "gns3": {"connected": False, "last_check": None, "error": None},
    "collector": {"connected": False, "last_check": None, "error": None}
}

async def test_connection_with_retry(url: str, service_name: str, timeout: int = 5, max_retries: Optional[int] = None) -> bool:
    """Test connection to a service with retry logic"""
    # Use service-specific retry logic
    if max_retries is None:
        if service_name == "gns3":
            max_retries = 1  # Only try once for GNS3
        else:
            max_retries = settings.CONNECTION_RETRIES
    
    # Set initial connection status
    connection_status[service_name]["connected"] = False
    connection_status[service_name]["last_check"] = datetime.now()
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                # Use appropriate endpoint for each service
                test_url = url
                method = "GET"  # Default method
                if service_name == "policy_engine":
                    test_url = f"{url}/health"
                elif service_name == "collector":
                    test_url = f"{url}/api/metrics/latest"  # Collector doesn't have /api/health, use metrics endpoint
                    method = "HEAD"  # Use HEAD to avoid downloading large response
                elif service_name == "gns3":
                    test_url = f"{url}/v2/version"  # GNS3 version endpoint
                
                async with session.request(method, test_url) as response:
                    if response.status == 200:
                        connection_status[service_name]["connected"] = True
                        connection_status[service_name]["error"] = None
                        connection_status[service_name]["last_check"] = datetime.now()
                        logger.info(f"✓ {service_name.title()} connection successful: {test_url}")
                        return True
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
        except Exception as e:
            error_msg = str(e)
            connection_status[service_name]["error"] = error_msg
            connection_status[service_name]["last_check"] = datetime.now()
            connection_status[service_name]["connected"] = False
            
            if attempt < max_retries - 1:
                if service_name == "gns3":
                    # Don't retry GNS3 - just log and continue
                    logger.warning(f"⚠ {service_name.title()} not available (will retry in background): {error_msg}")
                    break
                else:
                    wait_time = settings.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"⚠ {service_name.title()} connection failed (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
            else:
                if service_name == "gns3":
                    logger.warning(f"⚠ {service_name.title()} not available (will retry in background): {error_msg}")
                else:
                    logger.error(f"✗ {service_name.title()} connection failed after {max_retries} attempts: {error_msg}")
    
    return connection_status[service_name]["connected"]

async def initialize_connections():
    """Initialize connections to external services in parallel with non-blocking approach"""
    logger.info("🚀 Starting service connections...")
    
    # Create all connection tasks in parallel
    connection_tasks = {
        "policy_engine": test_connection_with_retry(settings.POLICY_ENGINE_URL, "policy_engine", 5, 2),
        "collector": test_connection_with_retry(settings.COLLECTOR_URL, "collector", 5, 2),
        "gns3": test_connection_with_retry(settings.GNS3_URL, "gns3", 3, 1)
    }
    
    try:
        # Run all connection tests in parallel with a reasonable timeout
        results = await asyncio.wait_for(
            asyncio.gather(*connection_tasks.values(), return_exceptions=True),
            timeout=20  # 20 seconds total timeout
        )
        
        # Process results
        service_names = list(connection_tasks.keys())
        for i, result in enumerate(results):
            service_name = service_names[i]
            if isinstance(result, Exception):
                logger.error(f"Connection test failed for {service_name}: {result}")
                connection_status[service_name]["connected"] = False
                connection_status[service_name]["error"] = str(result)
            elif result:
                logger.info(f"✓ {service_name} ready")
            else:
                logger.warning(f"⚠ {service_name} not available (will retry in background)")
                
    except asyncio.TimeoutError:
        logger.warning(f"⚠ Connection tests timed out after 20 seconds - continuing with startup")
        # Update status for any services that didn't complete
        for service_name in connection_tasks.keys():
            if connection_status[service_name]["last_check"] is None:
                connection_status[service_name]["connected"] = False
                connection_status[service_name]["error"] = "Connection test timed out"
                connection_status[service_name]["last_check"] = datetime.now()
    
    # Log final connection status
    connected_services = sum(1 for status in connection_status.values() if status["connected"])
    total_services = len(connection_status)
    logger.info(f"📊 Startup complete: {connected_services}/{total_services} services connected")
    
    # Log individual service status for debugging
    for service_name, status in connection_status.items():
        status_icon = "✓" if status["connected"] else "✗"
        logger.info(f"  {status_icon} {service_name}: {'Connected' if status['connected'] else 'Disconnected'}")
        if status["error"]:
            logger.debug(f"    Error: {status['error']}")
    
    # Create GNS3 client if available
    if connection_status["gns3"]["connected"]:
        await create_gns3_client_if_available()

async def background_health_checks():
    """Background task to periodically check service health"""
    while True:
        try:
            await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
            
            # Quick health checks without blocking
            # Check essential services more frequently
            essential_tasks = [
                test_connection_with_retry(settings.POLICY_ENGINE_URL, "policy_engine", 3, 1),
                test_connection_with_retry(settings.COLLECTOR_URL, "collector", 3, 1)
            ]
            
            # Check GNS3 less frequently and with minimal timeout
            gns3_task = test_connection_with_retry(settings.GNS3_URL, "gns3", 2, 1)
            
            # Run essential checks
            await asyncio.gather(*essential_tasks, return_exceptions=True)
            
            # Run GNS3 check separately with timeout
            try:
                gns3_available = await asyncio.wait_for(gns3_task, timeout=3)
                
                # Create or remove GNS3 client based on availability
                if gns3_available and not hasattr(app.state, 'gns3_client') or app.state.gns3_client is None:
                    await create_gns3_client_if_available()
                elif not gns3_available and hasattr(app.state, 'gns3_client') and app.state.gns3_client is not None:
                    # Clean up GNS3 client if service becomes unavailable
                    try:
                        await app.state.gns3_client.close()
                    except:
                        pass
                    app.state.gns3_client = None
                    logger.info("⚠ GNS3 client removed - service unavailable")
                    
            except asyncio.TimeoutError:
                # GNS3 timeout is expected and not an error
                pass
            
        except Exception as e:
            logger.error(f"Background health check error: {e}")

# Create FastAPI instance with redirect_slashes=False to avoid 307 redirects
app = FastAPI(
    title="FLOPY-NET Backend",
    description="API for the Federated Learning SDN Dashboard",
    version="0.1.0",
    redirect_slashes=False  # Disable redirects for paths with/without trailing slashes
)

# Configure CORS
# Adjust origins as needed for your frontend development and production URLs
origins = [
    "http://localhost:8085",    # Local development
    "http://127.0.0.1:8085",    # Alternative local development
    "http://localhost:3000",    # Another common dev port
    "http://127.0.0.1:3000",    # Another common dev port alternative
]

# In production, you might want to be more restrictive
if os.environ.get("ENVIRONMENT") == "production":
    # Add your production domain(s) here
    production_domain = os.environ.get("PRODUCTION_DOMAIN")
    if production_domain:
        origins.append(f"https://{production_domain}")
else:
    # In development, we can be more permissive
    origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Access-Control-Allow-Origin"],
)

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Check the health of the API and connected services."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "services": connection_status,
        "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    }

@app.get("/api/test/collector")
async def test_collector_connection():
    """Test endpoint to check collector connectivity."""
    client = CollectorApiClient()
    
    # Test connection
    connected = await client.test_connection()
    
    if not connected:
        return {"status": "error", "message": "Could not connect to collector"}
    
    # Test getting events with pagination
    events_response = await client.get_events({"limit": 5})
    events = events_response.get("events", [])
    total = events_response.get("total", 0)
    
    # Test getting summary
    summary = await client.get_events_summary()
    
    # Close client
    await client.aclose()
    
    return {
        "status": "success",
        "collector_url": client.base_url,
        "connection": "OK",
        "events_count": len(events),
        "total_events": total,
        "summary": summary
    }

@app.get("/api/test/metrics")
async def test_metrics_endpoints():
    """Test metrics-specific endpoints."""
    client = CollectorApiClient()
    
    try:
        # Test getting metrics
        metrics = await client.get_metrics(params={"limit": 5})
        metrics_count = len(metrics.get("metrics", [])) if "metrics" in metrics else 0
        
        # Test getting FL metrics
        fl_metrics_response = await client.get_fl_metrics({
            "limit": 5
        })
        fl_metrics_count = len(fl_metrics_response.get("metrics", [])) if "metrics" in fl_metrics_response else 0
        
        # Test getting latest metrics for FL
        latest_fl = await client.get_latest_metrics(type_filter="fl_server")
        
        # Close client
        await client.aclose()
        
        return {
            "status": "success",
            "collector_url": client.base_url,
            "metrics_count": metrics_count,
            "fl_metrics_count": fl_metrics_count,
            "latest_fl_metrics": latest_fl,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "collector_url": client.base_url if hasattr(client, "base_url") else "unknown"
        }

# Include routers from endpoints - fix trailing slashes to match frontend API calls
app.include_router(overview.router, prefix="/api/overview", tags=["Overview"])
app.include_router(fl_monitoring.router, prefix="/api/fl-monitoring", tags=["FL Monitoring"])
app.include_router(network.router, prefix="/api/network", tags=["Network"])
app.include_router(policy.router, prefix="/api/policy-engine", tags=["Policy Engine"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(logs.router, prefix="/ws", tags=["Logs WebSocket"]) # WebSocket for logs
app.include_router(logs.router, prefix="/api/log", tags=["Logs API"]) # REST API for logs including client error logging
app.include_router(config_display.router, prefix="/api/config", tags=["Configuration"])
app.include_router(metrics_explorer.router, prefix="/api/metrics", tags=["Metrics Explorer"])
app.include_router(topology_websocket.router, prefix="/ws", tags=["Topology WebSocket"]) # WebSocket for topology updates

@app.on_event("startup")
async def startup_event():
    """Initialize services and log startup information."""
    app.state.start_time = time.time()
    
    logger.info(f"🚀 Starting Dashboard API backend...")
    logger.info(f"📍 Service URLs:")
    logger.info(f"   Collector: {settings.COLLECTOR_URL}")
    logger.info(f"   Policy Engine: {settings.POLICY_ENGINE_URL}")
    logger.info(f"   GNS3: {settings.GNS3_URL}")
    
    # Initialize connections in background (non-blocking)
    asyncio.create_task(initialize_connections())
    
    # Start background health checks
    asyncio.create_task(background_health_checks())
    
    # Initialize essential service URLs (these will be created on-demand)
    app.state.policy_engine_url = settings.POLICY_ENGINE_URL
    app.state.collector_url = settings.COLLECTOR_URL
    app.state.gns3_url = settings.GNS3_URL

    # Initialize Policy Engine Client
    try:
        from .services.policy_client import AsyncPolicyEngineClient
        app.state.policy_client = AsyncPolicyEngineClient(settings.POLICY_ENGINE_URL)
        logger.info("✓ Policy Engine client initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Policy Engine client: {e}")
        app.state.policy_client = None
    
    # Initialize Caching
    # For production, consider RedisBackend: e.g. FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    logger.info("✓ In-memory cache initialized for FastAPI")
    
    # Only create GNS3 client if connection is successful
    # This will be checked and created on-demand in the background
    app.state.gns3_client = None
    
    logger.info("✅ Dashboard API backend startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    logger.info("🛑 Dashboard API backend shutting down...")
    
    # Clean up any active clients
    if hasattr(app.state, "policy_client"):
        try:
            await app.state.policy_client.close()
        except:
            pass
    
    if hasattr(app.state, "gns3_client"):
        try:
            await app.state.gns3_client.close()
        except:
            pass
    
    logger.info("✅ Dashboard API backend shutdown complete")

@app.get("/api/version", tags=["Version"])
async def get_version():
    """Get version information from environment variables."""
    return {
        "version": settings.VERSION,
        "last_updated": settings.LAST_UPDATED,
        "description": settings.DESCRIPTION,
        "connection_status": connection_status
    }

async def create_gns3_client_if_available():
    """Create GNS3 client only if the service is available."""
    try:
        if connection_status["gns3"]["connected"]:
            from .services.gns3_client import AsyncGNS3Client
            app.state.gns3_client = AsyncGNS3Client(settings.GNS3_URL)
            logger.info("✓ GNS3 client created successfully")
        else:
            app.state.gns3_client = None
            logger.info("⚠ GNS3 client not created - service unavailable")
    except Exception as e:
        logger.warning(f"Failed to create GNS3 client: {e}")
        app.state.gns3_client = None