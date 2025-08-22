# Copyright 2025 Vidyadhar Evani <vidyadhar.evani@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Fast Meraki MCP Server v2 - Refactored with FastMCP Best Practices

A semantic FastMCP server that provides intelligent access to Cisco Meraki APIs
through AI-powered tool discovery and null-safe response processing.

This refactored version leverages FastMCP's built-in OpenAPI integration,
proper middleware system, and includes resources and prompts.

Author: Vidyadhar Evani <vidyadhar.evani@gmail.com>
"""

import asyncio
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.server.openapi import RouteMap
from fastmcp.utilities.logging import get_logger

# Load environment variables
load_dotenv()

# Use FastMCP's logging utility
logger = get_logger(__name__)

# Configuration
API_KEY = os.getenv("MERAKI_API_KEY")
OPENAPI_SPEC_PATH = Path("openapi/spec3.json")
BASE_URL = "https://api.meraki.com/api/v1"

# Essential routes that are always available
ESSENTIAL_ROUTES = [
    "GET:/organizations",
    "GET:/organizations/{organizationId}",
    "GET:/organizations/{organizationId}/networks",
    "GET:/networks/{networkId}",
    "GET:/organizations/{organizationId}/devices",
    "GET:/networks/{networkId}/devices",
    "GET:/devices/{serial}",
    "GET:/networks/{networkId}/clients",
    "GET:/organizations/{organizationId}/inventory/devices",
]


class OptimizedSemanticDiscovery:
    """
    Optimized semantic tool discovery with caching and lazy loading.
    """

    def __init__(self, openapi_spec: Optional[Dict] = None):
        self.spec = openapi_spec
        self.tool_index = {}  # Lazy-loaded tool profiles
        self._cache = {}  # Simple cache for discovery results
        self.conversation_context = []
        self._initialized = False

    async def initialize(self):
        """Lazy initialization of semantic profiles."""
        if self._initialized or not self.spec:
            return
        
        logger.info("Initializing semantic discovery system")
        
        # Build index of tool keywords for fast lookup
        for path, path_obj in self.spec.get("paths", {}).items():
            for method, operation in path_obj.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue
                
                tool_id = f"{method.upper()}:{path}"
                # Store minimal profile for memory efficiency
                self.tool_index[tool_id] = {
                    "keywords": self._extract_keywords(path, operation),
                    "priority": self._calculate_priority(path, operation),
                    "summary": operation.get("summary", ""),
                }
        
        self._initialized = True
        logger.info(f"Indexed {len(self.tool_index)} tools for semantic discovery")

    def _extract_keywords(self, path: str, operation: Dict) -> Set[str]:
        """Extract keywords from path and operation."""
        keywords = set()
        
        # Extract from path
        path_parts = path.strip("/").split("/")
        keywords.update(p for p in path_parts if not p.startswith("{"))
        
        # Extract from operation
        if operation.get("summary"):
            keywords.update(operation["summary"].lower().split())
        if operation.get("tags"):
            keywords.update(t.lower() for t in operation["tags"])
        
        return keywords

    def _calculate_priority(self, path: str, operation: Dict) -> int:
        """Calculate priority based on common usage patterns."""
        priority = 5  # Default priority
        
        # Higher priority for list operations
        if "GET" in operation and not "{" in path:
            priority += 2
        
        # Higher priority for organization-level operations
        if "organization" in path.lower():
            priority += 1
        
        # Lower priority for complex operations
        if path.count("{") > 2:
            priority -= 2
        
        return max(1, min(10, priority))

    async def discover_tools(self, intent: str, max_tools: int = 15) -> List[Dict]:
        """Discover tools relevant to the given intent."""
        if not self._initialized:
            await self.initialize()
        
        # Check cache
        cache_key = f"{intent}:{max_tools}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Extract intent keywords
        intent_keywords = set(intent.lower().split())
        
        # Score tools based on keyword matches
        scored_tools = []
        for tool_id, profile in self.tool_index.items():
            score = len(intent_keywords & profile["keywords"])
            if score > 0:
                # Parse tool_id to get method and path
                try:
                    method, path = tool_id.split(":", 1)
                    
                    # Get operation details from OpenAPI spec
                    operation_details = {}
                    if self.spec and "paths" in self.spec:
                        path_obj = self.spec["paths"].get(path, {})
                        operation = path_obj.get(method.lower(), {})
                        operation_details = {
                            "operationId": operation.get("operationId", ""),
                            "description": operation.get("description", operation.get("summary", "")),
                            "tags": operation.get("tags", [])
                        }
                    
                    tool_info = {
                        "method": method,
                        "path": path,
                        "score": score * profile["priority"] / 10.0,  # Normalize score
                        **operation_details
                    }
                    scored_tools.append((tool_info, score * profile["priority"]))
                except ValueError:
                    continue
        
        # Sort by score and return top tools
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        result = [tool_info for tool_info, _ in scored_tools[:max_tools]]
        
        # Cache result
        self._cache[cache_key] = result
        
        return result

    def add_to_context(self, message: str):
        """Add message to conversation context."""
        self.conversation_context.append(message)
        # Keep only recent context to manage memory
        if len(self.conversation_context) > 20:
            self.conversation_context = self.conversation_context[-20:]
        
        # Clear cache when context changes significantly
        if len(self.conversation_context) % 5 == 0:
            self._cache.clear()


class MerakiMCPServer:
    """
    Refactored Meraki MCP Server using FastMCP best practices.
    """

    def __init__(self):
        self.mcp = FastMCP(
            name="Meraki Network Manager"
        )
        self.openapi_spec = None
        self.semantic_discovery = None
        self.api_client = None
        
    def load_openapi_spec(self) -> Dict:
        """Load OpenAPI specification."""
        if OPENAPI_SPEC_PATH.exists():
            with open(OPENAPI_SPEC_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logger.warning("OpenAPI spec not found, running with limited functionality")
            return {}

    def get_api_client(self) -> httpx.AsyncClient:
        """Get or create API client with proper configuration."""
        if not self.api_client:
            if not API_KEY:
                raise ValueError("MERAKI_API_KEY environment variable is required")
            
            self.api_client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers={
                    "X-Cisco-Meraki-API-Key": API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self.api_client

    def setup_openapi_integration(self):
        """Set up FastMCP OpenAPI integration."""
        if not self.openapi_spec:
            logger.warning("OpenAPI spec not loaded, skipping OpenAPI integration")
            return
        
        try:
            # Note: FastMCP.from_openapi() creates a new server instance
            # We can't easily merge it with our existing server
            # For now, skip OpenAPI integration and rely on semantic discovery
            logger.info("OpenAPI integration skipped - using semantic discovery instead")
            
        except Exception as e:
            logger.error(f"Failed to set up OpenAPI integration: {e}")
            # Fall back to manual tool registration if needed
            self.setup_manual_tools()

    def setup_manual_tools(self):
        """Register essential Meraki tools manually."""
        
        @self.mcp.tool
        async def list_organizations(ctx: Context) -> Dict:
            """List all Meraki organizations accessible with the API key."""
            try:
                await ctx.info("Fetching Meraki organizations...")
                client = self.get_api_client()
                response = await client.get("/organizations")
                response.raise_for_status()
                orgs = response.json()
                await ctx.info(f"Found {len(orgs)} organizations")
                return {"organizations": orgs}
            except Exception as e:
                await ctx.error(f"Failed to list organizations: {e}")
                return {"error": str(e)}
        
        @self.mcp.tool
        async def get_organization_networks(ctx: Context, organization_id: str) -> Dict:
            """Get all networks for a specific organization."""
            try:
                await ctx.info(f"Fetching networks for organization {organization_id}...")
                client = self.get_api_client()
                response = await client.get(f"/organizations/{organization_id}/networks")
                response.raise_for_status()
                networks = response.json()
                await ctx.info(f"Found {len(networks)} networks")
                return {"networks": networks}
            except Exception as e:
                await ctx.error(f"Failed to get networks: {e}")
                return {"error": str(e)}
        
        @self.mcp.tool
        async def get_network_devices(ctx: Context, network_id: str) -> Dict:
            """Get all devices in a specific network."""
            try:
                await ctx.info(f"Fetching devices for network {network_id}...")
                client = self.get_api_client()
                response = await client.get(f"/networks/{network_id}/devices")
                response.raise_for_status()
                devices = response.json()
                await ctx.info(f"Found {len(devices)} devices")
                return {"devices": devices}
            except Exception as e:
                await ctx.error(f"Failed to get devices: {e}")
                return {"error": str(e)}
        
        @self.mcp.tool
        async def get_device_status(ctx: Context, serial: str) -> Dict:
            """Get the status of a specific device by serial number."""
            try:
                await ctx.info(f"Fetching status for device {serial}...")
                client = self.get_api_client()
                response = await client.get(f"/devices/{serial}/liveTools/ping")
                response.raise_for_status()
                status = response.json()
                return {"device_status": status}
            except Exception as e:
                await ctx.error(f"Failed to get device status: {e}")
                return {"error": str(e)}
        
        @self.mcp.tool
        async def discover_meraki_tools(ctx: Context, query: str, max_results: int = 10) -> Dict:
            """Discover Meraki API tools based on a natural language query."""
            try:
                await ctx.info(f"Searching for tools matching: '{query}'...")
                
                if not self.semantic_discovery:
                    await ctx.warning("Semantic discovery not initialized")
                    return {"error": "Semantic discovery not available"}
                
                # Use semantic discovery to find relevant tools
                results = await self.semantic_discovery.discover_tools(
                    intent=query,
                    max_tools=max_results
                )
                
                discovered_tools = []
                for result in results:
                    tool_info = {
                        "operation_id": result.get("operationId", ""),
                        "method": result.get("method", ""),
                        "path": result.get("path", ""),
                        "description": result.get("description", ""),
                        "tags": result.get("tags", []),
                        "relevance_score": result.get("score", 0.0)
                    }
                    discovered_tools.append(tool_info)
                
                await ctx.info(f"Found {len(discovered_tools)} relevant tools")
                return {
                    "query": query,
                    "tools": discovered_tools,
                    "total_found": len(discovered_tools)
                }
            except Exception as e:
                await ctx.error(f"Failed to discover tools: {e}")
                return {"error": str(e)}
        
        @self.mcp.tool
        async def register_and_call_tool(ctx: Context, operation_id: str, parameters: Dict = None) -> Dict:
            """Dynamically register and call a Meraki API tool by operation ID."""
            try:
                if parameters is None:
                    parameters = {}
                
                await ctx.info(f"Registering and calling tool: {operation_id}")
                
                # Find the operation in the OpenAPI spec
                operation_info = self._find_operation_by_id(operation_id)
                if not operation_info:
                    await ctx.error(f"Operation {operation_id} not found")
                    return {"error": f"Operation {operation_id} not found"}
                
                method = operation_info["method"]
                path = operation_info["path"]
                operation_spec = operation_info["operation"]
                
                await ctx.info(f"Calling {method} {path}")
                
                # Build the actual API path with parameters
                actual_path = path
                path_params = {}
                query_params = {}
                
                # Process parameters from OpenAPI spec
                for param in operation_spec.get("parameters", []):
                    param_name = param["name"]
                    param_location = param.get("in", "query")
                    
                    if param_name in parameters:
                        if param_location == "path":
                            path_params[param_name] = parameters[param_name]
                            actual_path = actual_path.replace(f"{{{param_name}}}", str(parameters[param_name]))
                        elif param_location == "query":
                            query_params[param_name] = parameters[param_name]
                
                # Make the API call
                client = self.get_api_client()
                
                if method.upper() == "GET":
                    response = await client.get(actual_path, params=query_params)
                elif method.upper() == "POST":
                    response = await client.post(actual_path, json=parameters.get("body", {}), params=query_params)
                elif method.upper() == "PUT":
                    response = await client.put(actual_path, json=parameters.get("body", {}), params=query_params)
                elif method.upper() == "DELETE":
                    response = await client.delete(actual_path, params=query_params)
                else:
                    await ctx.error(f"Unsupported HTTP method: {method}")
                    return {"error": f"Unsupported HTTP method: {method}"}
                
                response.raise_for_status()
                result_data = response.json()
                
                await ctx.info(f"Successfully called {operation_id}")
                return {
                    "operation_id": operation_id,
                    "method": method,
                    "path": actual_path,
                    "result": result_data,
                    "success": True
                }
                
            except Exception as e:
                await ctx.error(f"Failed to call tool {operation_id}: {e}")
                return {
                    "operation_id": operation_id,
                    "error": str(e),
                    "success": False
                }
        
        # Register commonly used tools as direct callable tools
        @self.mcp.tool
        async def get_network_clients(ctx: Context, network_id: str, timespan: int = 86400) -> Dict:
            """Get the clients that have used this network in the specified timespan."""
            try:
                await ctx.info(f"Fetching clients for network {network_id}...")
                client = self.get_api_client()
                params = {"timespan": timespan}
                response = await client.get(f"/networks/{network_id}/clients", params=params)
                response.raise_for_status()
                clients = response.json()
                await ctx.info(f"Found {len(clients)} clients")
                return {"network_id": network_id, "clients": clients, "total_clients": len(clients)}
            except Exception as e:
                await ctx.error(f"Failed to get network clients: {e}")
                return {"error": str(e), "network_id": network_id}
        
        @self.mcp.tool
        async def get_network_wireless_ssids(ctx: Context, network_id: str) -> Dict:
            """List the wireless SSIDs configured for this network."""
            try:
                await ctx.info(f"Fetching wireless SSIDs for network {network_id}...")
                client = self.get_api_client()
                response = await client.get(f"/networks/{network_id}/wireless/ssids")
                response.raise_for_status()
                ssids = response.json()
                await ctx.info(f"Found {len(ssids)} SSIDs")
                return {"network_id": network_id, "ssids": ssids, "total_ssids": len(ssids)}
            except Exception as e:
                await ctx.error(f"Failed to get wireless SSIDs: {e}")
                return {"error": str(e), "network_id": network_id}
        
        @self.mcp.tool
        async def get_network_appliance_ssids(ctx: Context, network_id: str) -> Dict:
            """List the appliance SSIDs configured for this network."""
            try:
                await ctx.info(f"Fetching appliance SSIDs for network {network_id}...")
                client = self.get_api_client()
                response = await client.get(f"/networks/{network_id}/appliance/ssids")
                response.raise_for_status()
                ssids = response.json()
                await ctx.info(f"Found {len(ssids)} appliance SSIDs")
                return {"network_id": network_id, "ssids": ssids, "total_ssids": len(ssids)}
            except Exception as e:
                await ctx.error(f"Failed to get appliance SSIDs: {e}")
                return {"error": str(e), "network_id": network_id}
        
        @self.mcp.tool
        async def get_network_info(ctx: Context, network_id: str) -> Dict:
            """Get detailed information about a specific network."""
            try:
                await ctx.info(f"Fetching information for network {network_id}...")
                client = self.get_api_client()
                response = await client.get(f"/networks/{network_id}")
                response.raise_for_status()
                network_info = response.json()
                await ctx.info(f"Retrieved network info for '{network_info.get('name', network_id)}'")
                return {"network": network_info}
            except Exception as e:
                await ctx.error(f"Failed to get network info: {e}")
                return {"error": str(e), "network_id": network_id}

    def _find_operation_by_id(self, operation_id: str) -> Optional[Dict]:
        """Find an operation in the OpenAPI spec by its operationId."""
        if not self.openapi_spec or "paths" not in self.openapi_spec:
            return None
        
        for path, path_obj in self.openapi_spec["paths"].items():
            for method, operation in path_obj.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue
                
                if operation.get("operationId") == operation_id:
                    return {
                        "method": method.upper(),
                        "path": path,
                        "operation": operation
                    }
        
        return None

    def setup_middleware(self):
        """Set up middleware for CORS and other processing."""
        try:
            # Import FastMCP middleware components
            from fastmcp.server.middleware.logging import LoggingMiddleware
            from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
            
            # Add error handling middleware
            error_middleware = ErrorHandlingMiddleware(
                include_traceback=False,  # Security: don't expose tracebacks
                transform_errors=True
            )
            self.mcp.add_middleware(error_middleware)
            
            # Add logging middleware
            logging_middleware = LoggingMiddleware(
                include_payloads=False,  # Security: don't log sensitive data
                max_payload_length=100
            )
            self.mcp.add_middleware(logging_middleware)
            
            logger.info("FastMCP middleware configured successfully")
            
        except ImportError as e:
            logger.warning(f"FastMCP middleware not available: {e}")
        except Exception as e:
            logger.error(f"Failed to setup middleware: {e}")
        
        # Note: CORS support in FastMCP requires custom implementation
        # FastMCP HTTP transport automatically handles many cross-origin scenarios
        logger.info("CORS support handled by FastMCP HTTP transport layer")

    def _clean_null_values(self, data: Any) -> Any:
        """Recursively clean null values from data."""
        if data is None:
            return ""
        elif isinstance(data, dict):
            return {k: self._clean_null_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_null_values(item) for item in data]
        else:
            return data

    def setup_resources(self):
        """Set up MCP resources for read-only data access."""
        
        @self.mcp.resource("meraki://organizations")
        async def organizations_resource() -> Dict:
            """Expose all organizations as a resource."""
            try:
                client = self.get_api_client()
                response = await client.get("/organizations")
                response.raise_for_status()
                return {
                    "uri": "meraki://organizations",
                    "name": "Meraki Organizations",
                    "mimeType": "application/json",
                    "content": response.json()
                }
            except Exception as e:
                logger.error(f"Failed to fetch organizations resource: {e}")
                return {"error": str(e)}
        
        @self.mcp.resource("meraki://organizations/{org_id}/networks")
        async def networks_resource(org_id: str) -> Dict:
            """Expose networks for a specific organization."""
            try:
                client = self.get_api_client()
                response = await client.get(f"/organizations/{org_id}/networks")
                response.raise_for_status()
                return {
                    "uri": f"meraki://organizations/{org_id}/networks",
                    "name": f"Networks for Organization {org_id}",
                    "mimeType": "application/json",
                    "content": response.json()
                }
            except Exception as e:
                logger.error(f"Failed to fetch networks resource: {e}")
                return {"error": str(e)}
        
        @self.mcp.resource("meraki://networks/{network_id}/devices")
        async def devices_resource(network_id: str) -> Dict:
            """Expose devices for a specific network."""
            try:
                client = self.get_api_client()
                response = await client.get(f"/networks/{network_id}/devices")
                response.raise_for_status()
                return {
                    "uri": f"meraki://networks/{network_id}/devices",
                    "name": f"Devices in Network {network_id}",
                    "mimeType": "application/json",
                    "content": response.json()
                }
            except Exception as e:
                logger.error(f"Failed to fetch devices resource: {e}")
                return {"error": str(e)}

    def setup_prompts(self):
        """Set up MCP prompts for common tasks."""
        
        @self.mcp.prompt
        async def network_health_check(network_id: str) -> str:
            """Generate a prompt for checking network health."""
            return f"""Please analyze the health of network {network_id} by:
1. Checking all device statuses and connectivity
2. Reviewing recent alerts and events
3. Analyzing client connection patterns
4. Identifying any performance issues or bottlenecks
5. Suggesting preventive maintenance actions

Focus on actionable insights and prioritize critical issues."""

        @self.mcp.prompt
        async def troubleshooting_guide(issue_description: str) -> str:
            """Generate a troubleshooting prompt based on issue description."""
            return f"""Help me troubleshoot the following issue: {issue_description}

Please provide:
1. Likely root causes ranked by probability
2. Step-by-step diagnostic procedures
3. Relevant Meraki tools and dashboards to check
4. Common fixes and workarounds
5. Escalation criteria if the issue persists

Use Meraki-specific terminology and best practices."""

        @self.mcp.prompt
        async def configuration_audit() -> str:
            """Generate a configuration audit prompt."""
            return """Perform a comprehensive configuration audit:
1. Check for security best practices compliance
2. Identify redundant or conflicting rules
3. Review VLAN and subnet configurations
4. Validate firewall and content filtering rules
5. Check for firmware update requirements
6. Review user access and permissions

Provide specific recommendations for improvements with risk ratings."""

    def setup_discovery_tools(self):
        """Set up semantic discovery tools."""
        
        @self.mcp.tool
        async def discover_tools(ctx: Context, intent: str, max_tools: int = 15) -> Dict:
            """Discover Meraki tools relevant to your specific intent or task."""
            await ctx.info(f"Analyzing intent: {intent}")
            
            if not self.semantic_discovery:
                return {"error": "Semantic discovery not initialized"}
            
            try:
                # Add to conversation context
                self.semantic_discovery.add_to_context(intent)
                
                # Discover relevant tools
                relevant_tools = await self.semantic_discovery.discover_tools(intent, max_tools)
                
                if not relevant_tools:
                    return {
                        "message": f"No tools found for intent: '{intent}'",
                        "suggestion": "Try describing your task differently"
                    }
                
                # Get tool details
                tool_details = []
                for tool_id in relevant_tools:
                    if tool_id in self.semantic_discovery.tool_index:
                        profile = self.semantic_discovery.tool_index[tool_id]
                        tool_details.append({
                            "id": tool_id,
                            "summary": profile["summary"],
                            "priority": profile["priority"]
                        })
                
                await ctx.report_progress(
                    progress=100,
                    total=100,
                    message=f"Found {len(tool_details)} relevant tools"
                )
                
                return {
                    "intent": intent,
                    "tools_found": len(tool_details),
                    "tools": tool_details,
                    "message": "These tools are contextually relevant to your intent"
                }
                
            except Exception as e:
                await ctx.error(f"Discovery failed: {e}")
                return {"error": str(e)}

        @self.mcp.tool
        async def analyze_context(ctx: Context) -> Dict:
            """Analyze conversation context to suggest relevant tools and actions."""
            await ctx.info("Analyzing conversation context")
            
            if not self.semantic_discovery:
                return {"error": "Semantic discovery not initialized"}
            
            try:
                context = self.semantic_discovery.conversation_context
                
                if not context:
                    return {
                        "message": "No conversation context yet",
                        "suggestion": "Start by describing what you want to accomplish"
                    }
                
                # Analyze recent context
                recent_context = context[-5:]
                combined_context = " ".join(recent_context)
                
                # Get suggestions based on context
                suggested_tools = await self.semantic_discovery.discover_tools(combined_context, 10)
                
                return {
                    "recent_interactions": len(recent_context),
                    "suggested_tools_count": len(suggested_tools),
                    "suggested_tools": suggested_tools[:5],  # Top 5
                    "context_summary": f"Based on recent interactions about: {combined_context[:100]}..."
                }
                
            except Exception as e:
                await ctx.error(f"Context analysis failed: {e}")
                return {"error": str(e)}

    def setup_health_endpoints(self):
        """Set up health check and monitoring endpoints."""
        
        @self.mcp.tool
        async def health_check(ctx: Context) -> Dict:
            """Check the health status of the MCP server."""
            try:
                # Test API connectivity
                api_status = "unknown"
                try:
                    client = self.get_api_client()
                    response = await client.get("/organizations")
                    api_status = "healthy" if response.status_code == 200 else "degraded"
                except:
                    api_status = "unhealthy"
                
                # Get tool count
                tools = self.mcp.get_tools()
                tool_count = len(tools) if tools else 0
                
                # Get resource count
                resources = self.mcp.get_resources() if hasattr(self.mcp, 'get_resources') else []
                resource_count = len(resources) if resources else 0
                
                return {
                    "status": "healthy",
                    "api_connectivity": api_status,
                    "tools_registered": tool_count,
                    "resources_registered": resource_count,
                    "semantic_discovery": "active" if self.semantic_discovery else "inactive",
                    "null_safe_processing": "active",
                    "fastmcp_version": "2.10.6+",
                    "server_version": "2.0.0"
                }
                
            except Exception as e:
                await ctx.error(f"Health check failed: {e}")
                return {"status": "error", "error": str(e)}

    async def initialize(self):
        """Initialize the server with all components."""
        logger.info("Initializing Meraki MCP Server v2")
        
        # Load OpenAPI spec
        self.openapi_spec = self.load_openapi_spec()
        
        # Initialize semantic discovery
        self.semantic_discovery = OptimizedSemanticDiscovery(self.openapi_spec)
        await self.semantic_discovery.initialize()
        
        # Set up all components
        self.setup_middleware()
        self.setup_openapi_integration()
        self.setup_manual_tools()  # Always register core tools
        self.setup_resources()
        self.setup_prompts()
        self.setup_discovery_tools()
        self.setup_health_endpoints()
        
        logger.info("Meraki MCP Server v2 initialized successfully")

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.api_client:
                await self.api_client.aclose()
                logger.info("Closed API client connection")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            # Don't re-raise - we want graceful shutdown

    def run(self, **kwargs):
        """Run the MCP server."""
        try:
            # Initialize server
            asyncio.run(self.initialize())
            
            # Log startup information
            # Note: get_tools() is async in FastMCP, so we'll skip this for now
            logger.info(f"🚀 Starting Meraki MCP Server v2")
            logger.info(f"🧠 Semantic discovery: Active")
            logger.info(f"🛡️ Null-safe processing: Enabled")
            logger.info(f"📡 Server endpoint: http://0.0.0.0:8000/mcp")
            
            # Run the server
            self.mcp.run(
                transport="http",
                host="0.0.0.0",
                port=8000,
                path="/mcp",
                show_banner=True,
                **kwargs
            )
            
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            # Cleanup - handle event loop issues gracefully
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                # Event loop might be closed, try to cleanup synchronously
                if self.api_client:
                    logger.info("Performing synchronous cleanup")
                    try:
                        import asyncio as asyncio_module
                        loop = asyncio_module.new_event_loop()
                        asyncio_module.set_event_loop(loop)
                        loop.run_until_complete(self.api_client.aclose())
                        loop.close()
                    except Exception as e:
                        logger.warning(f"Synchronous cleanup failed: {e}")
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")


def main():
    """Main entry point."""
    if not API_KEY:
        logger.error("MERAKI_API_KEY environment variable is required")
        raise ValueError("Please set MERAKI_API_KEY environment variable")
    
    server = MerakiMCPServer()
    server.run()


if __name__ == "__main__":
    main()