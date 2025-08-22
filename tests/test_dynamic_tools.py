#!/usr/bin/env python3
"""
Test dynamic tool registration and execution
"""

import asyncio
import httpx
import json

async def test_dynamic_tools():
    """Test the new dynamic tool capabilities"""
    
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
                "clientInfo": {"name": "DynamicTester", "version": "1.0.0"}
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
        
        # 2. List all available tools to see the new ones
        print("\n🔍 Listing all available tools...")
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
                    print(f"✅ Found {len(tools)} total tools:")
                    
                    # Look for our new tools
                    new_tools = [
                        "get_network_clients",
                        "get_network_wireless_ssids", 
                        "get_network_appliance_ssids",
                        "get_network_info",
                        "register_and_call_tool"
                    ]
                    
                    found_tools = []
                    for tool in tools:
                        tool_name = tool.get("name", "")
                        if tool_name in new_tools:
                            found_tools.append(tool_name)
                            print(f"      ✅ {tool_name}: {tool.get('description', 'No description')[:60]}...")
                    
                    missing_tools = set(new_tools) - set(found_tools)
                    if missing_tools:
                        print(f"      ❌ Missing tools: {missing_tools}")
                    else:
                        print(f"      🎉 All new tools registered successfully!")
                        
                    return tools
                else:
                    print(f"   ❌ Error: {data.get('error', {}).get('message', 'Unknown error')}")
                    return []
        else:
            print(f"❌ Tools list failed: {response.status_code}")
            return []

async def test_direct_tool_calls():
    """Test calling the new direct tools"""
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Initialize session
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize", 
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "DirectTester", "version": "1.0.0"}
            }
        }
        
        response = await client.post("http://localhost:8000/mcp", json=init_request, headers=headers)
        session_id = response.headers.get("mcp-session-id")
        headers["mcp-session-id"] = session_id
        
        # Send initialized
        initialized_request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        await client.post("http://localhost:8000/mcp", json=initialized_request, headers=headers)
        
        # Test calling get_network_info tool (this should work without an API key)
        print("\n🧪 Testing get_network_info tool...")
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_network_info",
                "arguments": {
                    "network_id": "L_123456789"  # Sample network ID
                }
            }
        }
        
        response = await client.post("http://localhost:8000/mcp", json=call_request, headers=headers)
        if response.status_code == 200:
            response_text = response.text
            print(f"📝 Raw response preview: {response_text[:200]}...")
            
            # Check if it's an error due to API key or if the tool structure works
            if "data: " in response_text:
                lines = response_text.split('\n')
                for line in lines:
                    if line.startswith('data: ') and '"result"' in line:
                        json_data = line[6:]  # Remove "data: "
                        try:
                            data = json.loads(json_data)
                            if "result" in data:
                                result_content = data["result"]["content"][0]["text"]
                                result_data = json.loads(result_content)
                                
                                if "error" in result_data:
                                    if "API" in result_data["error"] or "key" in result_data["error"].lower():
                                        print("✅ Tool structure works! (Expected API key error)")
                                    else:
                                        print(f"⚠️  Tool error: {result_data['error']}")
                                else:
                                    print("✅ Tool executed successfully!")
                                    print(f"   Network ID: {result_data.get('network_id', 'Unknown')}")
                                break
                        except json.JSONDecodeError:
                            continue
        
        # Test the dynamic register_and_call_tool
        print("\n🧪 Testing register_and_call_tool...")
        call_request = {
            "jsonrpc": "2.0", 
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "register_and_call_tool",
                "arguments": {
                    "operation_id": "getNetworkClients",
                    "parameters": {
                        "networkId": "L_123456789"
                    }
                }
            }
        }
        
        response = await client.post("http://localhost:8000/mcp", json=call_request, headers=headers)
        if response.status_code == 200:
            print("✅ Dynamic tool call completed (check for API key requirement)")
        else:
            print(f"❌ Dynamic tool call failed: {response.status_code}")

if __name__ == "__main__":
    print("🚀 Testing Dynamic Tool Implementation")
    print("=" * 50)
    
    asyncio.run(test_dynamic_tools())
    print("\n" + "=" * 50)
    asyncio.run(test_direct_tool_calls())