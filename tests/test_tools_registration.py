#!/usr/bin/env python3
"""
Test tool registration and discovery functionality
"""

import asyncio
import httpx
import json

async def test_tools_with_session():
    """Test tool registration with proper session management"""
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # 1. Initialize and get session
        print("🔄 Initializing MCP session...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "ToolTester", "version": "1.0.0"}
            }
        }
        
        response = await client.post("http://localhost:8000/mcp", json=init_request, headers=headers)
        if response.status_code == 200:
            session_id = response.headers.get("mcp-session-id")
            print(f"✅ Session established: {session_id}")
            
            # Parse SSE response
            response_text = response.text
            if "data: " in response_text:
                json_data = response_text.split("data: ", 1)[1].strip()
                data = json.loads(json_data)
                server_info = data["result"]["serverInfo"]
                print(f"✅ Server: {server_info['name']} v{server_info['version']}")
                
                # Send initialized notification to complete the handshake
                headers["mcp-session-id"] = session_id
                initialized_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                await client.post("http://localhost:8000/mcp", json=initialized_request, headers=headers)
                print("✅ Initialization handshake completed")
            
        else:
            print(f"❌ Initialization failed: {response.status_code}")
            return
        
        # 2. List tools with session
        print("\n🔄 Listing available tools...")
        headers["mcp-session-id"] = session_id
        
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await client.post("http://localhost:8000/mcp", json=tools_request, headers=headers)
        if response.status_code == 200:
            response_text = response.text
            if "data: " in response_text:
                json_data = response_text.split("data: ", 1)[1].strip()
                data = json.loads(json_data)
                
                if "result" in data:
                    tools = data["result"].get("tools", [])
                    print(f"✅ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
                        
                    # 3. Test semantic discovery tool specifically
                    discovery_tool = next((t for t in tools if t["name"] == "discover_meraki_tools"), None)
                    if discovery_tool:
                        print(f"\n🔄 Testing semantic discovery tool...")
                        
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
                        
                        response = await client.post("http://localhost:8000/mcp", json=call_request, headers=headers)
                        if response.status_code == 200:
                            response_text = response.text
                            if "data: " in response_text:
                                json_data = response_text.split("data: ", 1)[1].strip()
                                data = json.loads(json_data)
                                
                                if "result" in data:
                                    result = data["result"]["content"][0]["text"]
                                    result_data = json.loads(result)
                                    print(f"✅ Discovery found {result_data.get('total_found', 0)} tools")
                                    print(f"   Query: '{result_data.get('query', '')}'")
                                elif "error" in data:
                                    print(f"⚠️ Discovery error: {data['error']['message']}")
                        else:
                            print(f"❌ Tool call failed: {response.status_code}")
                    else:
                        print("⚠️ Semantic discovery tool not found")
                        
                elif "error" in data:
                    print(f"❌ Error listing tools: {data['error']['message']}")
            else:
                print(f"❌ Invalid response format")
        else:
            print(f"❌ Tools list failed: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_tools_with_session())