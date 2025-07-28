"""
Health check module for Meraki MCP Server.
Provides health check endpoints for monitoring and container orchestration.
"""

import json
import time
from typing import Dict, Any
from pathlib import Path

import httpx
from loguru import logger


class HealthCheck:
    """Health check implementation for Meraki MCP Server."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.meraki.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.start_time = time.time()
        
    async def check_api_connectivity(self) -> Dict[str, Any]:
        """Check connectivity to Meraki Dashboard API."""
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-Cisco-Meraki-API-Key": self.api_key},
                timeout=10.0
            ) as client:
                response = await client.get("/administered/identities/me")
                response.raise_for_status()
                
                return {
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "user": response.json().get("name", "Unknown")
                }
                
        except httpx.HTTPStatusError as e:
            return {
                "status": "unhealthy",
                "error": f"HTTP {e.response.status_code}",
                "details": "API authentication or permission error"
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "details": "API connection failed"
            }
    
    def check_openapi_spec(self) -> Dict[str, Any]:
        """Check if OpenAPI spec is valid and accessible."""
        try:
            spec_path = Path(__file__).parent / "openapi" / "spec3.json"
            
            if not spec_path.exists():
                return {
                    "status": "unhealthy",
                    "error": "OpenAPI spec file not found",
                    "path": str(spec_path)
                }
            
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
            
            # Basic validation
            required_fields = ["openapi", "info", "paths"]
            missing_fields = [field for field in required_fields if field not in spec]
            
            if missing_fields:
                return {
                    "status": "unhealthy",
                    "error": f"Missing required fields: {missing_fields}"
                }
            
            return {
                "status": "healthy",
                "version": spec["info"]["version"],
                "title": spec["info"]["title"],
                "paths_count": len(spec["paths"])
            }
            
        except json.JSONDecodeError as e:
            return {
                "status": "unhealthy",
                "error": "Invalid JSON in OpenAPI spec",
                "details": str(e)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        health_data = {
            "service": "Cisco Meraki MCP Server",
            "version": "1.0.0",
            "uptime_seconds": time.time() - self.start_time,
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Check OpenAPI spec
        health_data["checks"]["openapi_spec"] = self.check_openapi_spec()
        
        # Check API connectivity
        health_data["checks"]["api_connectivity"] = await self.check_api_connectivity()
        
        # Determine overall status
        all_healthy = all(
            check.get("status") == "healthy" 
            for check in health_data["checks"].values()
        )
        
        health_data["status"] = "healthy" if all_healthy else "unhealthy"
        
        return health_data


# Simple HTTP health check for Docker
async def simple_health_check() -> bool:
    """Simple health check that returns True if service is healthy."""
    import os
    
    api_key = os.getenv("MERAKI_API_KEY")
    if not api_key:
        logger.error("MERAKI_API_KEY not set for health check")
        return False
    
    health = HealthCheck(api_key)
    status = await health.get_health_status()
    
    is_healthy = status["status"] == "healthy"
    
    if not is_healthy:
        logger.warning(f"Health check failed: {status}")
    
    return is_healthy


if __name__ == "__main__":
    # Command-line health check
    import asyncio
    import sys
    
    async def main():
        is_healthy = await simple_health_check()
        sys.exit(0 if is_healthy else 1)
    
    asyncio.run(main())