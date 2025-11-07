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

import os
from datetime import datetime
from fastapi import APIRouter
from ...core.config import settings

router = APIRouter()

@router.get("/service-urls")
async def get_service_urls():
    """Return the configured service URLs from environment variables."""
    return {
        "gns3_url": settings.GNS3_URL,
        "collector_url": settings.COLLECTOR_URL,
        "policy_engine_url": settings.POLICY_ENGINE_URL,
        "version": os.getenv("APP_VERSION", "0.1.0")
    }

@router.get("/system-info")
async def get_system_info():
    """Return comprehensive system and environment information."""
    return {
        "application": {
            "name": "FLOPY-NET Dashboard",
            "version": os.getenv("APP_VERSION", "unknown"),
            "build_date": os.getenv("BUILD_DATE", "unknown"),
            "git_commit": os.getenv("GIT_COMMIT", "unknown"),
            "environment": os.getenv("ENVIRONMENT", "unknown")
        },
        "services": {
            "gns3_url": settings.GNS3_URL,
            "collector_url": settings.COLLECTOR_URL,
            "policy_engine_url": settings.POLICY_ENGINE_URL
        },
        "runtime": {
            "startup_time": datetime.now().isoformat(),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "connection_timeout": os.getenv("CONNECTION_TIMEOUT", "10"),
            "connection_retries": os.getenv("CONNECTION_RETRIES", "3")
        },
        "container": {
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "container_name": "dashboard-backend"
        }
    }

@router.get("/ping-services")
async def ping_services():
    """Check connectivity to all configured services."""
    import httpx
    import asyncio
    
    async def check_service(url: str, name: str):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{url}/health")
                return {"service": name, "url": url, "status": "online", "code": response.status_code}
        except Exception as e:
            return {"service": name, "url": url, "status": "offline", "error": str(e)}
    
    tasks = [
        check_service(settings.GNS3_URL, "GNS3"),
        check_service(settings.COLLECTOR_URL, "Collector"),
        check_service(settings.POLICY_ENGINE_URL, "Policy Engine")
    ]
    
    results = await asyncio.gather(*tasks)
    return {"services": results}