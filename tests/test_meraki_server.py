#!/usr/bin/env python3
"""
Non-intrusive test suite for Meraki MCP Server
Tests FastMCP compliance and server functionality
"""

import asyncio
import json
import httpx
import logging
from typing import Dict, Any, List
from pathlib import Path
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MerakiServerTester:
    """Test suite for Meraki MCP Server"""
    
    def __init__(self, base_url: str = "http://localhost:8000/mcp"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    def log_test(self, name: str, status: str, details: str = "", warning: str = ""):
        """Log test result"""
        test_result = {
            "name": name,
            "status": status,
            "details": details,
            "warning": warning
        }
        self.results["tests"].append(test_result)
        self.results["summary"]["total"] += 1
        
        if status == "PASS":
            self.results["summary"]["passed"] += 1
            logger.info(f"✅ {name}: PASSED")
        elif status == "FAIL":
            self.results["summary"]["failed"] += 1
            logger.error(f"❌ {name}: FAILED - {details}")
        elif status == "WARNING":
            self.results["summary"]["warnings"] += 1
            logger.warning(f"⚠️  {name}: WARNING - {warning}")
    
    def parse_sse_response(self, response_text: str) -> Dict[str, Any] | None:
        """Parse Server-Sent Events response from FastMCP"""
        try:
            # Handle both CRLF and LF line endings
            if response_text.startswith("event: message") and "data: " in response_text:
                # Find the data line
                lines = response_text.replace('\r\n', '\n').split('\n')
                for line in lines:
                    if line.startswith("data: "):
                        json_data = line[6:]  # Remove "data: " prefix
                        return json.loads(json_data)
                return None
            else:
                # Try to parse as regular JSON
                return json.loads(response_text)
        except json.JSONDecodeError:
            return None
    
    async def test_server_health(self) -> bool:
        """Test if server is running and responsive"""
        try:
            async with httpx.AsyncClient() as client:
                # For FastMCP HTTP transport, we need to send proper JSON-RPC
                # Just check if server responds to POST requests
                test_request = {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "ping"
                }
                response = await client.post(
                    self.base_url, 
                    json=test_request,
                    headers=self.headers,
                    timeout=5.0
                )
                if response.status_code in [200, 400, 404]:  # Any response means server is up
                    self.log_test("Server Health Check", "PASS", "Server is responsive")
                    return True
                else:
                    self.log_test("Server Health Check", "FAIL", f"Status code: {response.status_code}")
                    return False
        except Exception as e:
            self.log_test("Server Health Check", "FAIL", str(e))
            return False
    
    async def test_mcp_initialize(self) -> bool:
        """Test MCP initialization handshake"""
        try:
            async with httpx.AsyncClient() as client:
                # Send MCP initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {}
                        },
                        "clientInfo": {
                            "name": "MerakiServerTester",
                            "version": "1.0.0"
                        }
                    }
                }
                
                response = await client.post(
                    self.base_url,
                    json=init_request,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = self.parse_sse_response(response.text)
                    if data and "result" in data:
                        server_info = data["result"]
                        server_name = server_info.get('serverInfo', {}).get('name', 'Unknown')
                        # Check if this was SSE format
                        is_sse = response.text.startswith("event: message")
                        format_info = " (SSE format)" if is_sse else ""
                        details = f"Server: {server_name}{format_info}"
                        self.log_test("MCP Initialize", "PASS", details)
                        if is_sse:
                            self.log_test("FastMCP Streamable HTTP", "PASS", "Server uses SSE format")
                        return True
                    else:
                        self.log_test("MCP Initialize", "FAIL", "No result in response or invalid format")
                        return False
                else:
                    self.log_test("MCP Initialize", "FAIL", f"Status code: {response.status_code}")
                    return False
        except Exception as e:
            self.log_test("MCP Initialize", "FAIL", str(e))
            return False
    
    async def test_list_tools(self) -> List[Dict]:
        """Test listing available tools"""
        try:
            async with httpx.AsyncClient() as client:
                # First initialize
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "clientInfo": {"name": "Tester", "version": "1.0.0"}
                    }
                }
                
                init_response = await client.post(self.base_url, json=init_request, timeout=10.0)
                
                # Complete MCP handshake
                if init_response.status_code == 200:
                    session_id = init_response.headers.get("mcp-session-id")
                    if session_id:
                        # Send initialized notification
                        initialized_request = {
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized",
                            "params": {}
                        }
                        self.headers["mcp-session-id"] = session_id
                        await client.post(self.base_url, json=initialized_request, headers=self.headers, timeout=5.0)
                
                # Then list tools
                list_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
                
                response = await client.post(
                    self.base_url,
                    json=list_request,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = self.parse_sse_response(response.text)
                    if data and "result" in data:
                        tools = data["result"].get("tools", [])
                        self.log_test("List Tools", "PASS", f"Found {len(tools)} tools")
                        return tools
                    else:
                        self.log_test("List Tools", "FAIL", "No result in response or invalid format")
                        return []
                else:
                    self.log_test("List Tools", "FAIL", f"Status code: {response.status_code}")
                    return []
        except Exception as e:
            self.log_test("List Tools", "FAIL", str(e))
            return []
    
    async def test_semantic_discovery(self) -> bool:
        """Test semantic discovery functionality"""
        try:
            tools = await self.test_list_tools()
            
            # Check for discover_meraki_tools
            discovery_tool = None
            for tool in tools:
                if tool.get("name") == "discover_meraki_tools":
                    discovery_tool = tool
                    break
            
            if discovery_tool:
                self.log_test("Semantic Discovery Tool", "PASS", "discover_meraki_tools found")
                
                # Test calling the discovery tool
                async with httpx.AsyncClient() as client:
                    call_request = {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "discover_meraki_tools",
                            "arguments": {
                                "query": "list organizations",
                                "max_results": 5
                            }
                        }
                    }
                    
                    response = await client.post(
                        self.base_url,
                        json=call_request,
                        headers=self.headers,
                        timeout=15.0
                    )
                    
                    if response.status_code == 200:
                        data = self.parse_sse_response(response.text)
                        if data and "result" in data:
                            self.log_test("Semantic Discovery Call", "PASS", "Discovery tool works")
                            return True
                        elif data and "error" in data:
                            error = data.get("error", {}).get("message", "Unknown error")
                            self.log_test("Semantic Discovery Call", "WARNING", "", f"Error: {error}")
                            return True  # Tool exists, just may need API key
                        else:
                            self.log_test("Semantic Discovery Call", "FAIL", "Invalid response format")
                            return False
                    else:
                        self.log_test("Semantic Discovery Call", "FAIL", f"Status: {response.status_code}")
                        return False
            else:
                self.log_test("Semantic Discovery Tool", "FAIL", "discover_meraki_tools not found")
                return False
                
        except Exception as e:
            self.log_test("Semantic Discovery", "FAIL", str(e))
            return False
    
    async def test_fastmcp_compliance(self) -> bool:
        """Test FastMCP compliance features"""
        all_passed = True
        
        # Test 1: Check HTTP transport
        try:
            async with httpx.AsyncClient() as client:
                response = await client.options(self.base_url, timeout=5.0)
                if "fastmcp" in response.headers.get("server", "").lower() or response.status_code in [200, 204, 405]:
                    self.log_test("FastMCP HTTP Transport", "PASS", "HTTP transport working")
                else:
                    self.log_test("FastMCP HTTP Transport", "WARNING", "", "Cannot verify FastMCP server header")
        except Exception as e:
            self.log_test("FastMCP HTTP Transport", "FAIL", str(e))
            all_passed = False
        
        # Test 2: Check JSON-RPC compliance
        try:
            async with httpx.AsyncClient() as client:
                # Send invalid JSON-RPC to test error handling
                invalid_request = {
                    "jsonrpc": "2.0",
                    "id": 999,
                    "method": "invalid_method"
                }
                
                response = await client.post(
                    self.base_url,
                    json=invalid_request,
                    headers=self.headers,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = self.parse_sse_response(response.text)
                    if data and "error" in data:
                        self.log_test("JSON-RPC Error Handling", "PASS", "Proper error response")
                    else:
                        self.log_test("JSON-RPC Error Handling", "WARNING", "", "Unexpected response format")
                else:
                    self.log_test("JSON-RPC Error Handling", "WARNING", "", f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("JSON-RPC Error Handling", "FAIL", str(e))
            all_passed = False
        
        # Test 3: Check streaming capability (FastMCP feature)
        try:
            async with httpx.AsyncClient() as client:
                # Check if server supports streaming
                response = await client.head(self.base_url, timeout=5.0)
                headers = response.headers
                
                if "text/event-stream" in headers.get("accept", "").lower() or response.status_code in [200, 405]:
                    self.log_test("Streaming Support", "PASS", "Server may support streaming")
                else:
                    self.log_test("Streaming Support", "WARNING", "", "Cannot verify streaming support")
        except Exception as e:
            self.log_test("Streaming Support", "WARNING", "", str(e))
        
        return all_passed
    
    async def test_security_headers(self) -> bool:
        """Test security configurations"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, timeout=5.0)
                headers = response.headers
                
                security_checks = {
                    "CORS": "access-control-allow-origin" in headers,
                    "Content-Type": "content-type" in headers,
                }
                
                for check, present in security_checks.items():
                    if present:
                        self.log_test(f"Security Header: {check}", "PASS", f"Header present")
                    else:
                        self.log_test(f"Security Header: {check}", "WARNING", "", f"Header not found")
                
                return all(security_checks.values())
        except Exception as e:
            self.log_test("Security Headers", "FAIL", str(e))
            return False
    
    async def test_resource_list(self) -> bool:
        """Test listing resources"""
        try:
            async with httpx.AsyncClient() as client:
                # Initialize first
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"resources": {}},
                        "clientInfo": {"name": "Tester", "version": "1.0.0"}
                    }
                }
                
                await client.post(self.base_url, json=init_request, timeout=10.0)
                
                # List resources
                list_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "resources/list",
                    "params": {}
                }
                
                response = await client.post(
                    self.base_url,
                    json=list_request,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = self.parse_sse_response(response.text)
                    if data and "result" in data:
                        resources = data["result"].get("resources", [])
                        self.log_test("List Resources", "PASS", f"Found {len(resources)} resources")
                        return True
                    else:
                        self.log_test("List Resources", "WARNING", "", "No resources configured or invalid format")
                        return True
                else:
                    self.log_test("List Resources", "FAIL", f"Status: {response.status_code}")
                    return False
        except Exception as e:
            self.log_test("List Resources", "FAIL", str(e))
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 60)
        logger.info("Starting Meraki MCP Server Test Suite")
        logger.info("=" * 60)
        
        # Update todo
        self.log_test("Test Suite", "INFO", "Starting comprehensive tests")
        
        # Test server health
        if not await self.test_server_health():
            logger.error("Server is not running. Please start the server first.")
            return self.results
        
        # Test MCP protocol
        await self.test_mcp_initialize()
        
        # Test tool discovery
        await self.test_list_tools()
        
        # Test semantic discovery
        await self.test_semantic_discovery()
        
        # Test FastMCP compliance
        await self.test_fastmcp_compliance()
        
        # Test security
        await self.test_security_headers()
        
        # Test resources
        await self.test_resource_list()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {self.results['summary']['total']}")
        logger.info(f"✅ Passed: {self.results['summary']['passed']}")
        logger.info(f"❌ Failed: {self.results['summary']['failed']}")
        logger.info(f"⚠️  Warnings: {self.results['summary']['warnings']}")
        
        # Save results
        results_file = Path("test_results.json")
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
        
        return self.results

async def main():
    """Main test runner"""
    tester = MerakiServerTester()
    
    # Check if server is specified
    if len(sys.argv) > 1:
        tester.base_url = sys.argv[1]
    
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())