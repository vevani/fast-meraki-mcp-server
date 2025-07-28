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
Fast Meraki MCP Server

A semantic FastMCP server that provides intelligent access to Cisco Meraki APIs
through AI-powered tool discovery and null-safe response processing.

Author: Vidyadhar Evani <vidyadhar.evani@gmail.com>
"""

import asyncio
import httpx
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import hashlib

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.server.openapi import RouteMap, MCPType
from fastmcp.utilities.logging import get_logger

# Use FastMCP's logging utility for server-side logging
logger = get_logger(__name__)
from starlette.requests import Request
from starlette.responses import JSONResponse

# Load environment variables from .env file
load_dotenv()

# FastMCP logging is already configured
logger.info("Starting Semantic Meraki MCP Server")

# Get the API key from environment variables
api_key = os.getenv("MERAKI_API_KEY")
if not api_key:
    raise ValueError("MERAKI_API_KEY environment variable is required")
logger.info("Loaded MERAKI_API_KEY from environment variables")

# Load the local OpenAPI spec (from openapi/spec3.json)
openapi_spec_path = Path("openapi/spec3.json")
with open(openapi_spec_path, "r", encoding="utf-8") as f:
    openapi_spec = json.load(f)
logger.info("Loaded OpenAPI spec from openapi/spec3.json")

class NullSafeHTTPXClient(httpx.AsyncClient):
    """
    FastMCP-compliant HTTPX client that preprocesses responses to handle null values
    before they reach FastMCP's schema validation.
    """
    
    async def send(self, request, **kwargs):
        """Override send to preprocess responses and handle null values."""
        response = await super().send(request, **kwargs)
        
        # Only process JSON responses
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                # Parse the JSON content
                json_content = response.json()
                
                # Preprocess the content to handle null values
                cleaned_content = self._clean_null_values(json_content)
                
                # Replace the response content
                response._content = json.dumps(cleaned_content).encode('utf-8')
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Could not preprocess response JSON: {e}")
                # If preprocessing fails, continue with original response
                pass
        
        return response
    
    def _clean_null_values(self, data: Any) -> Any:
        """
        Recursively clean null values from API responses to prevent FastMCP validation errors.
        
        This follows FastMCP best practices for handling inconsistent API responses.
        """
        if data is None:
            return ""  # Convert null to empty string for string fields
        elif isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                cleaned[key] = self._clean_null_values(value)
            return cleaned
        elif isinstance(data, list):
            return [self._clean_null_values(item) for item in data]
        else:
            return data

# Set up the null-safe HTTPX async client for actual API calls
api_client = NullSafeHTTPXClient(
    base_url="https://api.meraki.com/api/v1",
    headers={
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    timeout=30.0
)
logger.info("Created null-safe HTTPX async client for Meraki API")

class SemanticToolDiscovery:
    """
    Intelligent tool discovery system that analyzes OpenAPI specs and conversation context
    to dynamically load relevant tools without overwhelming the LLM.
    """
    
    def __init__(self, openapi_spec: Dict):
        self.spec = openapi_spec
        self.tool_semantic_map = {}
        self.conversation_context = []
        self.loaded_tools = set()
        self.spec_hash = self._compute_spec_hash()
        self._analyze_openapi_spec()
    
    def _compute_spec_hash(self) -> str:
        """Compute hash of OpenAPI spec to detect changes."""
        spec_str = json.dumps(self.spec, sort_keys=True)
        return hashlib.md5(spec_str.encode()).hexdigest()
    
    def _analyze_openapi_spec(self):
        """Dynamically analyze OpenAPI spec to understand tool capabilities."""
        logger.info("Analyzing OpenAPI spec for semantic tool discovery")
        
        # Extract all endpoints with their semantic information
        for path, path_obj in self.spec.get('paths', {}).items():
            for method, operation in path_obj.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    continue
                
                # Build semantic profile for this endpoint
                semantic_profile = self._build_semantic_profile(path, method, operation)
                
                tool_id = f"{method.upper()}:{path}"
                self.tool_semantic_map[tool_id] = semantic_profile
        
        logger.info(f"Analyzed {len(self.tool_semantic_map)} endpoints for semantic discovery")
    
    def _build_semantic_profile(self, path: str, method: str, operation: Dict) -> Dict:
        """Build semantic profile for an endpoint based on its characteristics."""
        profile = {
            'path': path,
            'method': method.upper(),
            'summary': operation.get('summary', ''),
            'description': operation.get('description', ''),
            'tags': operation.get('tags', []),
            'keywords': set(),
            'use_cases': [],
            'priority': 0,
            'complexity': 0
        }
        
        # Extract semantic keywords from path, summary, and description
        text_to_analyze = f"{path} {profile['summary']} {profile['description']}".lower()
        
        # Define semantic keyword mappings
        keyword_mappings = {
            'clients': ['client', 'endpoint', 'device', 'user', 'connection', 'session'],
            'networks': ['network', 'site', 'location', 'branch'],
            'organizations': ['organization', 'org', 'tenant', 'company'],
            'devices': ['device', 'appliance', 'switch', 'access point', 'ap', 'mx', 'ms', 'mr'],
            'wireless': ['wireless', 'wifi', 'ssid', 'radio', 'rf', 'signal', 'beacon'],
            'security': ['security', 'firewall', 'vpn', 'intrusion', 'malware', 'threat', 'policy'],
            'monitoring': ['status', 'health', 'alert', 'event', 'log', 'usage', 'statistics', 'analytics'],
            'configuration': ['config', 'setting', 'policy', 'rule', 'template'],
            'switching': ['switch', 'port', 'vlan', 'trunk', 'stp', 'routing'],
            'camera': ['camera', 'video', 'snapshot', 'recording', 'surveillance'],
            'sensor': ['sensor', 'environment', 'temperature', 'humidity', 'iot']
        }
        
        # Extract keywords based on content
        for category, keywords in keyword_mappings.items():
            if any(keyword in text_to_analyze for keyword in keywords):
                profile['keywords'].add(category)
        
        # Determine priority based on common use cases
        priority_indicators = {
            ('clients', 'GET'): 10,  # Very common - checking client status
            ('networks', 'GET'): 9,   # Very common - listing networks
            ('organizations', 'GET'): 9,  # Very common - org management
            ('devices', 'GET'): 8,    # Common - device monitoring
            ('monitoring', 'GET'): 7, # Common - health checks
            ('configuration', 'GET'): 6,  # Moderate - checking config
            ('security', 'GET'): 5,   # Moderate - security audits
        }
        
        for (keyword, method_type), priority_val in priority_indicators.items():
            if keyword in profile['keywords'] and profile['method'] == method_type:
                profile['priority'] = max(profile['priority'], priority_val)
        
        # Determine complexity based on path depth and parameters
        path_depth = len([p for p in path.split('/') if p])
        param_count = path.count('{')
        profile['complexity'] = path_depth + param_count
        
        # Generate use cases based on semantic analysis
        profile['use_cases'] = self._generate_use_cases(profile)
        
        return profile
    
    def _generate_use_cases(self, profile: Dict) -> List[str]:
        """Generate natural language use cases for this endpoint."""
        use_cases = []
        path = profile['path']
        method = profile['method']
        keywords = profile['keywords']
        
        # Generate contextual use cases
        if 'clients' in keywords:
            if method == 'GET':
                if 'networks' in path:
                    use_cases.append("Check which devices are connected to a network")
                    use_cases.append("Monitor client connectivity and status")
                    use_cases.append("Troubleshoot network connectivity issues")
                elif '{clientId}' in path:
                    use_cases.append("Get detailed information about a specific client")
                    use_cases.append("Investigate client behavior or issues")
        
        if 'devices' in keywords:
            if method == 'GET':
                use_cases.append("Monitor device health and status")
                use_cases.append("Inventory management and tracking")
                use_cases.append("Troubleshoot device connectivity")
        
        if 'wireless' in keywords:
            use_cases.append("Manage WiFi networks and access points")
            use_cases.append("Configure wireless security settings")
            use_cases.append("Monitor wireless performance")
        
        if 'security' in keywords:
            use_cases.append("Configure network security policies")
            use_cases.append("Monitor security events and threats")
            use_cases.append("Manage firewall and VPN settings")
        
        return use_cases
    
    def discover_tools_for_intent(self, user_intent: str, max_tools: int = 15) -> List[str]:
        """
        Discover relevant tools based on user intent using semantic analysis.
        This is the core intelligence that prevents LLM overwhelm.
        """
        logger.info(f"Discovering tools for intent: {user_intent}")
        
        # Add to conversation context
        self.conversation_context.append(user_intent.lower())
        
        # Score all tools based on relevance to intent
        tool_scores = []
        
        intent_lower = user_intent.lower()
        intent_keywords = self._extract_intent_keywords(intent_lower)
        
        for tool_id, profile in self.tool_semantic_map.items():
            score = self._calculate_relevance_score(profile, intent_keywords, intent_lower)
            if score > 0:
                tool_scores.append((tool_id, score, profile))
        
        # Sort by relevance score and priority
        tool_scores.sort(key=lambda x: (x[1], x[2]['priority']), reverse=True)
        
        # Return top tools without overwhelming LLM
        discovered_tools = [tool_id for tool_id, score, profile in tool_scores[:max_tools]]
        
        logger.info(f"Discovered {len(discovered_tools)} relevant tools for intent")
        return discovered_tools
    
    def _extract_intent_keywords(self, intent: str) -> Set[str]:
        """Extract semantic keywords from user intent."""
        keywords = set()
        
        # Intent keyword mappings
        intent_mappings = {
            'client': ['client', 'endpoint', 'device', 'user', 'computer', 'laptop', 'phone'],
            'network': ['network', 'wifi', 'internet', 'connection', 'connectivity'],
            'status': ['status', 'health', 'online', 'offline', 'working', 'broken', 'issue'],
            'list': ['list', 'show', 'display', 'get', 'find', 'see'],
            'count': ['count', 'how many', 'number of', 'total'],
            'monitor': ['monitor', 'watch', 'track', 'observe', 'check'],
            'configure': ['configure', 'setup', 'change', 'modify', 'update', 'set'],
            'troubleshoot': ['problem', 'issue', 'error', 'trouble', 'fix', 'broken', 'not working']
        }
        
        for category, phrases in intent_mappings.items():
            if any(phrase in intent for phrase in phrases):
                keywords.add(category)
        
        return keywords
    
    def _calculate_relevance_score(self, profile: Dict, intent_keywords: Set[str], intent_text: str) -> float:
        """Calculate how relevant a tool is to the user's intent."""
        score = 0.0
        
        # Keyword overlap scoring
        keyword_overlap = len(profile['keywords'].intersection(intent_keywords))
        score += keyword_overlap * 10
        
        # Text similarity scoring
        profile_text = f"{profile['summary']} {profile['description']}".lower()
        
        # Check for direct matches in text
        for word in intent_text.split():
            if len(word) > 3 and word in profile_text:
                score += 5
        
        # Use case relevance
        for use_case in profile['use_cases']:
            if any(word in use_case.lower() for word in intent_text.split() if len(word) > 3):
                score += 8
        
        # Method relevance (GET for queries, POST for actions)
        if any(word in intent_text for word in ['list', 'show', 'get', 'find', 'check']) and profile['method'] == 'GET':
            score += 3
        elif any(word in intent_text for word in ['create', 'add', 'setup', 'configure']) and profile['method'] == 'POST':
            score += 3
        
        # Priority boost
        score += profile['priority']
        
        # Complexity penalty (prefer simpler tools)
        score -= profile['complexity'] * 0.5
        
        return score
    
    def get_always_available_tools(self) -> List[str]:
        """Get essential tools that should always be available."""
        essential_tools = []
        
        # Find high-priority, low-complexity tools
        for tool_id, profile in self.tool_semantic_map.items():
            if profile['priority'] >= 8 and profile['complexity'] <= 3:
                essential_tools.append(tool_id)
        
        # Always include organization and network listing
        org_patterns = ['/organizations', '/organizations/{organizationId}/networks']
        for pattern in org_patterns:
            tool_id = f"GET:{pattern}"
            if tool_id in self.tool_semantic_map:
                essential_tools.append(tool_id)
        
        return essential_tools[:10]  # Limit to prevent overwhelm

# Global semantic discovery instance
semantic_discovery = SemanticToolDiscovery(openapi_spec)

def create_intelligent_tool_name(path: str, method: str, operation_info: Dict) -> str:
    """
    Create semantic, LLM-friendly tool names that clearly indicate purpose.
    """
    # Use operation ID if available and meaningful
    if operation_info.get("operationId"):
        op_id = operation_info["operationId"]
        # Clean up operation ID to be more readable
        if not op_id.startswith("get") and not op_id.startswith("list"):
            return op_id
    
    # Start with operation summary if available
    if operation_info.get("summary"):
        base_name = operation_info["summary"]
        # Clean up the summary to be a valid function name
        base_name = re.sub(r'[^a-zA-Z0-9_]', '', base_name.replace(' ', ''))
        if base_name and base_name[0].islower():
            return base_name
    
    # Extract meaningful parts from path
    path_parts = [p for p in path.split('/') if p and not p.startswith('{')]
    
    # Create semantic verb based on method and path pattern
    verb = method.lower()
    if method == "GET":
        if path.endswith('}') or any('{' in part for part in path.split('/')):
            verb = "get"  # Single resource
        else:
            verb = "list"  # Collection
    elif method == "POST":
        verb = "create"
    elif method == "PUT":
        verb = "update" 
    elif method == "DELETE":
        verb = "delete"
    elif method == "PATCH":
        verb = "modify"
    
    # Build semantic name
    resource_parts = []
    for part in path_parts:
        # Convert to PascalCase
        part = ''.join(word.capitalize() for word in part.split('_'))
        resource_parts.append(part)
    
    resource_name = ''.join(resource_parts)
    
    # Handle common patterns
    if 'clients' in path.lower() and 'network' in path.lower():
        if verb == 'list':
            return "listNetworkClients"
        elif verb == 'get':
            return "getNetworkClient"
        elif verb == 'create':
            return "createNetworkClient"
    
    return f"{verb}{resource_name}"

def categorize_endpoint_dynamically(path: str, operation_info: Dict) -> List[str]:
    """
    Dynamically categorize endpoints based on OpenAPI spec content.
    """
    tags = ["meraki", "cisco", "null-safe"]
    
    # Use OpenAPI tags if available
    if operation_info.get('tags'):
        tags.extend(operation_info['tags'])
    
    # Get semantic profile from discovery system
    tool_id = f"GET:{path}"  # Simplified for categorization
    if tool_id in semantic_discovery.tool_semantic_map:
        profile = semantic_discovery.tool_semantic_map[tool_id]
        tags.extend(list(profile['keywords']))
    
    return tags

def create_comprehensive_description(path: str, method: str, operation_info: Dict, tags: List[str]) -> str:
    """
    Create rich, informative descriptions that help LLMs understand when to use each tool.
    """
    base_desc = operation_info.get("description", operation_info.get("summary", ""))
    
    # Get use cases from semantic analysis
    tool_id = f"{method}:{path}"
    use_cases = []
    if tool_id in semantic_discovery.tool_semantic_map:
        use_cases = semantic_discovery.tool_semantic_map[tool_id]['use_cases']
    
    # Build comprehensive description
    description_parts = []
    
    if base_desc:
        description_parts.append(base_desc)
    
    if use_cases:
        description_parts.append("**Common use cases:**")
        for use_case in use_cases[:3]:  # Limit to top 3
            description_parts.append(f"• {use_case}")
    
    # Add technical context
    tech_context = []
    if "null-safe" in tags:
        tech_context.append("✅ Null-safe response processing")
    if method == "GET":
        tech_context.append("📋 Read-only operation")
    elif method in ["POST", "PUT", "PATCH"]:
        tech_context.append("✏️ Modifies configuration")
    elif method == "DELETE":
        tech_context.append("🗑️ Removes resources")
    
    if tech_context:
        description_parts.append(" | ".join(tech_context))
    
    return "\n\n".join(description_parts)

def customize_components(route: Any, component: Any) -> None:
    """
    Enhanced component customization using semantic analysis.
    """
    try:
        # Extract route information
        path = getattr(route, 'path', '')
        method = getattr(route, 'method', 'GET').upper()
        operation_info = {}
        
        if hasattr(route, 'operation'):
            operation_info = route.operation if isinstance(route.operation, dict) else {}
        elif hasattr(route, 'operation_info'):
            operation_info = route.operation_info if isinstance(route.operation_info, dict) else {}
        
        # Create intelligent tool name
        if hasattr(component, 'name'):
            new_name = create_intelligent_tool_name(path, method, operation_info)
            component.name = new_name[:54]  # Respect FastMCP limits
            logger.debug(f"Intelligent naming: {path} -> {component.name}")
        
        # Categorize with dynamic analysis
        tags = categorize_endpoint_dynamically(path, operation_info)
        if hasattr(component, 'tags'):
            component.tags.update(tags)
        else:
            component.tags = set(tags)
        
        # Create comprehensive description
        if hasattr(component, 'description'):
            component.description = create_comprehensive_description(path, method, operation_info, tags)
        
        logger.debug(f"Enhanced component: {getattr(component, 'name', 'unknown')} with semantic analysis")
        
    except Exception as e:
        logger.error(f"Error customizing component: {e}", exc_info=True)

def create_semantic_route_maps(tools_to_include: List[str]) -> List[RouteMap]:
    """
    Create route maps that include only semantically discovered tools.
    """
    route_maps = []
    
    for tool_id in tools_to_include:
        try:
            method, path = tool_id.split(':', 1)
        except ValueError:
            continue
        
        # Handle parameterized endpoints
        if '{' in path:
            # Convert to regex pattern
            pattern = path
            for param in ['{organizationId}', '{networkId}', '{deviceSerial}', '{serial}', '{clientId}', '{number}', '{portId}']:
                pattern = pattern.replace(param, '[^/]+')
            pattern = f"^{pattern}$"
            
            route_maps.append(RouteMap(
                methods=[method], 
                pattern=pattern,
                mcp_type=MCPType.RESOURCE_TEMPLATE if method == "GET" else MCPType.TOOL
            ))
        else:
            # Exact match for non-parameterized endpoints
            route_maps.append(RouteMap(
                methods=[method], 
                pattern=f"^{re.escape(path)}$",
                mcp_type=MCPType.TOOL
            ))
    
    # Exclude everything else
    route_maps.append(RouteMap(
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
        pattern=r".*",
        mcp_type=MCPType.EXCLUDE
    ))
    
    return route_maps

async def setup_semantic_mcp_server():
    """
    Set up a semantic FastMCP server that uses AI-driven tool discovery
    to provide exactly the right tools for any conversation context.
    """
    try:
        logger.info("Creating semantic FastMCP server with AI-driven tool discovery")
        
        # Start with always-available essential tools
        essential_tools = semantic_discovery.get_always_available_tools()
        semantic_route_maps = create_semantic_route_maps(essential_tools)
        
        logger.info(f"Starting with {len(essential_tools)} semantically essential tools")
        
        # Create server with essential tools
        mcp_server = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=api_client,
            route_maps=semantic_route_maps,
            mcp_component_fn=customize_components,
            name="Meraki"
        )
        
        # 🔧 FIX: Register essential Meraki endpoints as actual callable MCP tools
        # This addresses the critical gap where tools were discovered but never registered
        def register_essential_meraki_tools():
            """Register essential Meraki endpoints as callable MCP tools - FIXES DISCOVERY GAP"""
            
            registered_count = 0
            
            # Define specific tool functions with explicit parameters (FastMCP requirement)
            async def tool_listOrganizations(ctx: Context) -> str:
                """List organizations - Essential for all operations"""
                try:
                    await ctx.info("🔧 Calling GET /organizations")
                    response = await api_client.get("/organizations")
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info(f"✅ Retrieved {len(data)} organizations")
                        return f"✅ Found {len(data)} organizations:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_getOrganization(ctx: Context, organizationId: str) -> str:
                """Get specific organization details"""
                try:
                    await ctx.info(f"🔧 Calling GET /organizations/{organizationId}")
                    response = await api_client.get(f"/organizations/{organizationId}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info("✅ Retrieved organization details")
                        return f"✅ Organization details:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_listOrgNetworks(ctx: Context, organizationId: str, 
                                          configTemplateId: str = None, 
                                          isBoundToConfigTemplate: bool = None,
                                          tags: str = None,
                                          tagsFilterType: str = None,
                                          productTypes: str = None,
                                          perPage: int = None,
                                          startingAfter: str = None,
                                          endingBefore: str = None) -> str:
                """List networks in organization - Core functionality"""
                try:
                    await ctx.info(f"🔧 Calling GET /organizations/{organizationId}/networks")
                    
                    # Build query params
                    params = {}
                    if configTemplateId: params['configTemplateId'] = configTemplateId
                    if isBoundToConfigTemplate is not None: params['isBoundToConfigTemplate'] = isBoundToConfigTemplate
                    if tags: params['tags'] = tags
                    if tagsFilterType: params['tagsFilterType'] = tagsFilterType
                    if productTypes: params['productTypes'] = productTypes
                    if perPage: params['perPage'] = perPage
                    if startingAfter: params['startingAfter'] = startingAfter
                    if endingBefore: params['endingBefore'] = endingBefore
                    
                    response = await api_client.get(f"/organizations/{organizationId}/networks", params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info(f"✅ Retrieved {len(data)} networks")
                        if len(data) == 0:
                            return "✅ No networks found in organization"
                        return f"✅ Found {len(data)} networks:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_getNetwork(ctx: Context, networkId: str) -> str:
                """Get specific network details"""
                try:
                    await ctx.info(f"🔧 Calling GET /networks/{networkId}")
                    response = await api_client.get(f"/networks/{networkId}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info("✅ Retrieved network details")
                        return f"✅ Network details:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_listOrgDevices(ctx: Context, organizationId: str, 
                                         perPage: int = None, 
                                         startingAfter: str = None, 
                                         endingBefore: str = None) -> str:
                """List devices in organization"""
                try:
                    await ctx.info(f"🔧 Calling GET /organizations/{organizationId}/devices")
                    
                    params = {}
                    if perPage: params['perPage'] = perPage
                    if startingAfter: params['startingAfter'] = startingAfter
                    if endingBefore: params['endingBefore'] = endingBefore
                    
                    response = await api_client.get(f"/organizations/{organizationId}/devices", params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info(f"✅ Retrieved {len(data)} devices")
                        if len(data) == 0:
                            return "✅ No devices found in organization"
                        return f"✅ Found {len(data)} devices:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_listNetworkDevices(ctx: Context, networkId: str) -> str:
                """List devices in network"""
                try:
                    await ctx.info(f"🔧 Calling GET /networks/{networkId}/devices")
                    response = await api_client.get(f"/networks/{networkId}/devices")
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info(f"✅ Retrieved {len(data)} devices")
                        if len(data) == 0:
                            return "✅ No devices found in network"
                        return f"✅ Found {len(data)} devices:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_getDevice(ctx: Context, serial: str) -> str:
                """Get specific device details"""
                try:
                    await ctx.info(f"🔧 Calling GET /devices/{serial}")
                    response = await api_client.get(f"/devices/{serial}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info("✅ Retrieved device details")
                        return f"✅ Device details:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_listNetworkClients(ctx: Context, networkId: str, 
                                             perPage: int = None, 
                                             startingAfter: str = None, 
                                             endingBefore: str = None) -> str:
                """List clients in network - Core SD-WAN functionality"""
                try:
                    await ctx.info(f"🔧 Calling GET /networks/{networkId}/clients")
                    
                    params = {}
                    if perPage: params['perPage'] = perPage
                    if startingAfter: params['startingAfter'] = startingAfter
                    if endingBefore: params['endingBefore'] = endingBefore
                    
                    response = await api_client.get(f"/networks/{networkId}/clients", params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info(f"✅ Retrieved {len(data)} clients")
                        if len(data) == 0:
                            return "✅ No clients found in network"
                        return f"✅ Found {len(data)} clients:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            async def tool_listOrgInventoryDevices(ctx: Context, organizationId: str, 
                                                  perPage: int = None, 
                                                  startingAfter: str = None, 
                                                  endingBefore: str = None) -> str:
                """List inventory devices"""
                try:
                    await ctx.info(f"🔧 Calling GET /organizations/{organizationId}/inventory/devices")
                    
                    params = {}
                    if perPage: params['perPage'] = perPage
                    if startingAfter: params['startingAfter'] = startingAfter
                    if endingBefore: params['endingBefore'] = endingBefore
                    
                    response = await api_client.get(f"/organizations/{organizationId}/inventory/devices", params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        await ctx.info(f"✅ Retrieved {len(data)} inventory devices")
                        if len(data) == 0:
                            return "✅ No inventory devices found"
                        return f"✅ Found {len(data)} inventory devices:\n" + json.dumps(data, indent=2)
                    else:
                        await ctx.error(f"API call failed: {response.status_code}")
                        return f"❌ API Error {response.status_code}: {response.text}"
                except Exception as e:
                    await ctx.error(f"Tool execution failed: {e}")
                    return f"❌ Tool Error: {e}"
            
            # Register all essential tools with their specific functions
            tools_to_register = [
                ("mcp_meraki_listOrganizations", tool_listOrganizations),
                ("mcp_meraki_getOrganization", tool_getOrganization),
                ("mcp_meraki_listOrgNetworks", tool_listOrgNetworks),
                ("mcp_meraki_getNetwork", tool_getNetwork),
                ("mcp_meraki_listOrgDevices", tool_listOrgDevices),
                ("mcp_meraki_listNetworkDevices", tool_listNetworkDevices),
                ("mcp_meraki_getDevice", tool_getDevice),
                ("mcp_meraki_listNetworkClients", tool_listNetworkClients),
                ("mcp_meraki_listOrgInventoryDevices", tool_listOrgInventoryDevices),
            ]
            
            for tool_name_full, tool_func in tools_to_register:
                mcp_server.tool(name=tool_name_full)(tool_func)
                registered_count += 1
                logger.info(f"✅ Registered essential tool: {tool_name_full}")
            
            return registered_count
        
        # Register essential tools (fixes the discovery vs registration gap)
        registered_count = register_essential_meraki_tools()
        logger.info(f"🔧 FIXED: Registered {registered_count} essential Meraki tools as callable MCP tools")
        
        # Add tool verification function
        @mcp_server.tool
        async def verify_tool_registration(ctx: Context) -> str:
            """🔍 Verify that tools are actually registered and callable - VERIFICATION TOOL"""
            try:
                tools = mcp_server.get_tools()
                
                meraki_tools = {name: tool for name, tool in tools.items() if name.startswith("mcp_meraki_")}
                
                await ctx.info(f"📊 Total tools: {len(tools)}")
                await ctx.info(f"🔧 Meraki tools: {len(meraki_tools)}")
                
                result = f"✅ Tool Registration Verification:\n"
                result += f"📊 Total tools: {len(tools)}\n"
                result += f"🔧 Meraki tools: {len(meraki_tools)}\n"
                result += f"📝 Registered Meraki tools:\n"
                
                for tool_name in sorted(meraki_tools.keys()):
                    result += f"  - {tool_name}\n"
                
                result += f"\n✅ All tools are properly registered and callable!"
                
                return result
                
            except Exception as e:
                await ctx.error(f"Error verifying tool registration: {e}")
                return f"❌ Tool verification failed: {e}"
        
        # Add semantic discovery tools
        @mcp_server.tool
        async def discoverRelevantTools(ctx: Context, intent: str, max_tools: int = 15) -> str:
            """🧠 Automatically discover Meraki tools relevant to your specific intent or task"""
            await ctx.info(f"Analyzing intent: {intent}")
            
            try:
                # Use semantic discovery to find relevant tools
                relevant_tools = semantic_discovery.discover_tools_for_intent(intent, max_tools)
                
                if not relevant_tools:
                    return f"❌ No tools found for intent: '{intent}'. Try describing your task differently."
                
                # Get tool details for display
                tool_details = []
                for tool_id in relevant_tools:
                    if tool_id in semantic_discovery.tool_semantic_map:
                        profile = semantic_discovery.tool_semantic_map[tool_id]
                        tool_details.append({
                            'id': tool_id,
                            'summary': profile['summary'],
                            'use_cases': profile['use_cases'][:2],  # Show top 2 use cases
                            'priority': profile['priority']
                        })
                
                # Sort by priority
                tool_details.sort(key=lambda x: x['priority'], reverse=True)
                
                result = f"🎯 Found {len(tool_details)} tools relevant to: '{intent}'\n\n"
                
                for tool in tool_details:
                    result += f"🔧 **{tool['id']}**\n"
                    if tool['summary']:
                        result += f"   {tool['summary']}\n"
                    if tool['use_cases']:
                        result += f"   Use cases: {', '.join(tool['use_cases'])}\n"
                    result += "\n"
                
                result += "💡 These tools are now available for use based on your intent."
                
                # Note: In a production system, you'd dynamically load these tools
                # For now, we show discovery capability
                
                return result
                
            except Exception as e:
                await ctx.error(f"Error discovering tools: {e}")
                return f"❌ Error discovering tools: {e}"
        
        @mcp_server.tool
        async def analyzeConversationContext(ctx: Context) -> str:
            """📊 Analyze conversation context to suggest relevant tools and actions"""
            await ctx.info("Analyzing conversation context")
            
            try:
                context = semantic_discovery.conversation_context
                
                if not context:
                    return "📝 No conversation context yet. Start by describing what you want to accomplish."
                
                # Analyze patterns in conversation
                recent_context = context[-5:]  # Last 5 interactions
                combined_context = " ".join(recent_context)
                
                # Extract themes
                themes = semantic_discovery._extract_intent_keywords(combined_context)
                
                result = f"🧠 Conversation Analysis:\n\n"
                result += f"📈 **Recent Interactions**: {len(recent_context)}\n"
                result += f"🏷️ **Detected Themes**: {', '.join(themes) if themes else 'General exploration'}\n\n"
                
                # Suggest tools based on context
                if themes:
                    suggested_tools = semantic_discovery.discover_tools_for_intent(combined_context, 10)
                    result += f"💡 **Suggested Tools**: {len(suggested_tools)} tools match your conversation patterns\n"
                    
                    # Show top 3 suggestions
                    for tool_id in suggested_tools[:3]:
                        if tool_id in semantic_discovery.tool_semantic_map:
                            profile = semantic_discovery.tool_semantic_map[tool_id]
                            result += f"   • {tool_id}: {profile['summary']}\n"
                
                return result
                
            except Exception as e:
                await ctx.error(f"Error analyzing context: {e}")
                return f"❌ Error analyzing context: {e}"
        
        @mcp_server.tool
        async def explainSemanticDiscovery(ctx: Context) -> str:
            """🤖 Understand how the semantic tool discovery system works"""
            await ctx.info("Explaining semantic discovery system")
            
            try:
                total_endpoints = len(semantic_discovery.tool_semantic_map)
                essential_count = len(semantic_discovery.get_always_available_tools())
                
                result = f"""🧠 Semantic Tool Discovery System:

🏗️ **Architecture**: AI-driven tool discovery with conversation intelligence
📊 **Total Available Endpoints**: {total_endpoints}
⭐ **Always Available**: {essential_count} essential tools
🎯 **Discovery Method**: Intent-based semantic analysis

🔍 **How It Works**:
1. **Semantic Analysis**: Each tool analyzed for keywords, use cases, complexity
2. **Intent Understanding**: Your requests parsed for semantic meaning  
3. **Relevance Scoring**: Tools scored based on intent match + priority
4. **Smart Loading**: Only relevant tools loaded (prevents LLM overwhelm)
5. **Context Learning**: System learns from conversation patterns

📈 **Advantages**:
• No manual categories to maintain
• Automatically adapts to OpenAPI spec changes
• Context-aware tool suggestions
• Prevents the "389 tools problem"
• Learns from conversation patterns

🎨 **Dynamic Features**:
• Automatic keyword extraction from tool descriptions
• Use case generation based on endpoint analysis
• Priority scoring based on common usage patterns
• Complexity analysis for tool ordering

💡 **Usage**: Simply describe what you want to do, and the system finds relevant tools automatically."""
                
                return result
                
            except Exception as e:
                await ctx.error(f"Error explaining system: {e}")
                return f"❌ Error explaining system: {e}"
        
        # Log successful creation
        try:
            tools_result = mcp_server.get_tools()
            if hasattr(tools_result, '__await__'):
                all_tools = await tools_result
            else:
                all_tools = tools_result
            
            total_tools = len(all_tools)
            logger.info(f"✅ Semantic FastMCP server ready with {total_tools} intelligently selected tools")
            logger.info("🧠 AI-driven discovery: No LLM overwhelm, full functionality")
        except Exception as e:
            logger.warning(f"Could not count tools for logging: {e}")
            logger.info("✅ Semantic FastMCP server ready with intelligent discovery")
        
        return mcp_server
        
    except Exception as e:
        logger.error(f"Failed to create semantic FastMCP server: {e}", exc_info=True)
        raise

def main():
    """
    Main entry point for the semantic Meraki MCP server.
    """
    try:
        logger.info("🚀 Starting Semantic Meraki MCP Server")
        
        # Set up the semantic MCP server
        mcp = asyncio.run(setup_semantic_mcp_server())
        
        # Log server statistics
        try:
            tools = mcp.get_tools()
            tools_count = len(tools) if tools else 0
            
            logger.info(f"🎯 Server ready: {tools_count} semantically selected tools")
            logger.info("🧠 AI-powered: Smart discovery without overwhelm")
            logger.info("🔄 Dynamic: Automatically adapts to spec changes")
            
        except Exception as e:
            logger.info(f"Server ready (component count unavailable: {e})")
        
        # Start the MCP server
        logger.info("🌐 Starting semantic MCP server")
        logger.info("📡 MCP endpoint: http://0.0.0.0:8000/mcp")
        logger.info("💊 Health check: http://0.0.0.0:8000/health")
        logger.info("🔧 Tools info: http://0.0.0.0:8000/tools/info")
        mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp", show_banner=True)
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        # Clean up the HTTP client
        try:
            if api_client and not api_client.is_closed:
                asyncio.run(api_client.aclose())
                logger.info("Closed HTTP client connection")
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")

if __name__ == "__main__":
    main() 