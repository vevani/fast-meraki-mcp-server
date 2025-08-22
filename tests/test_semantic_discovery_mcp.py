#!/usr/bin/env python3
"""
Test semantic discovery through the MCP server interface
"""

import asyncio
import httpx
import json

async def test_semantic_discovery_via_mcp():
    """Test semantic discovery through MCP interface"""
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # 1. Initialize MCP session
        print("🔄 Initializing MCP session...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "SemanticTester", "version": "1.0.0"}
            }
        }
        
        response = await client.post("http://localhost:8000/mcp", json=init_request, headers=headers)
        if response.status_code == 200:
            session_id = response.headers.get("mcp-session-id")
            print(f"✅ Session established: {session_id}")
            
            # Complete handshake
            headers["mcp-session-id"] = session_id
            initialized_request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            await client.post("http://localhost:8000/mcp", json=initialized_request, headers=headers)
            print("✅ MCP handshake completed")
        else:
            print(f"❌ Initialization failed: {response.status_code}")
            return
        
        # 2. Test semantic discovery queries
        test_queries = [
            "list network clients",
            "get wireless SSIDs",
            "show network endpoints",
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            # Call the discover_meraki_tools function
            call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "discover_meraki_tools",
                    "arguments": {
                        "query": query,
                        "max_results": 5
                    }
                }
            }
            
            response = await client.post("http://localhost:8000/mcp", json=call_request, headers=headers)
            if response.status_code == 200:
                response_text = response.text
                if "data: " in response_text:
                    json_data = response_text.split("data: ", 1)[1].strip()
                    data = json.loads(json_data)
                    
                    if "result" in data:
                        result_content = data["result"]["content"][0]["text"]
                        result_data = json.loads(result_content)
                        
                        print(f"   ✅ Found {result_data.get('total_found', 0)} tools")
                        print(f"   📝 Query: '{result_data.get('query', '')}'")
                        
                        tools = result_data.get('tools', [])
                        for i, tool in enumerate(tools[:3], 1):  # Show top 3
                            method = tool.get('method', 'Unknown')
                            path = tool.get('path', 'Unknown')
                            description = tool.get('description', 'No description')[:60]
                            score = tool.get('relevance_score', 0.0)
                            print(f"      {i}. {method} {path}")
                            print(f"         Score: {score:.3f} - {description}...")
                        
                        # Check if we found the endpoints we were looking for
                        if query == "list network clients":
                            found_clients = any('/clients' in tool.get('path', '') for tool in tools)
                            if found_clients:
                                print(f"      ✅ SUCCESS: Found network clients endpoint")
                            else:
                                print(f"      ❌ ISSUE: Network clients endpoint not found")
                        
                        elif query == "get wireless SSIDs":
                            found_ssids = any('ssid' in tool.get('path', '').lower() for tool in tools)
                            if found_ssids:
                                print(f"      ✅ SUCCESS: Found SSID endpoints")
                            else:
                                print(f"      ❌ ISSUE: SSID endpoints not found")
                        
                    elif "error" in data:
                        print(f"   ❌ Error: {data['error']['message']}")
                else:
                    print(f"   ❌ Invalid response format")
            else:
                print(f"   ❌ Request failed: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_semantic_discovery_via_mcp())