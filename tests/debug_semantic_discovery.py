#!/usr/bin/env python3
"""
Debug semantic discovery to find out why client and SSID endpoints aren't being found
"""

import asyncio
import json
from pathlib import Path
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meraki_mcp_server import OptimizedSemanticDiscovery

async def debug_semantic_discovery():
    """Debug the semantic discovery system"""
    
    # Load OpenAPI spec
    spec_path = Path("openapi/spec3.json")
    if not spec_path.exists():
        print("❌ OpenAPI spec not found at openapi/spec3.json")
        return
        
    print("✅ Loading OpenAPI spec...")
    with open(spec_path) as f:
        spec = json.load(f)
    
    # Initialize semantic discovery
    print("🔄 Initializing semantic discovery...")
    discovery = OptimizedSemanticDiscovery(spec)
    await discovery.initialize()
    
    print(f"✅ Indexed {len(discovery.tool_index)} tools")
    
    # Test various queries
    test_queries = [
        "list network clients",
        "get network clients", 
        "show clients on network",
        "wireless SSIDs",
        "list SSIDs",
        "show wireless networks",
        "get wireless settings",
        "network endpoints",
        "client devices"
    ]
    
    print("\n🔄 Testing semantic queries...")
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        
        try:
            results = await discovery.discover_tools(query, max_tools=5)
            
            if results:
                print(f"   ✅ Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    method = result.get('method', 'Unknown').upper()
                    path = result.get('path', 'Unknown')
                    description = result.get('description', 'No description')[:80]
                    score = result.get('score', 0.0)
                    print(f"      {i}. {method} {path}")
                    print(f"         Score: {score:.3f} - {description}")
            else:
                print(f"   ❌ No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Check specific endpoints
    print("\n🔍 Checking if specific endpoints are indexed...")
    
    target_endpoints = [
        "GET:/networks/{networkId}/clients",
        "GET:/networks/{networkId}/wireless/ssids", 
        "GET:/networks/{networkId}/appliance/ssids",
        "GET:/networks/{networkId}/wireless/settings"
    ]
    
    for endpoint in target_endpoints:
        if endpoint in discovery.tool_index:
            profile = discovery.tool_index[endpoint]
            print(f"   ✅ {endpoint}")
            print(f"      Keywords: {profile.get('keywords', [])}")
            print(f"      Priority: {profile.get('priority', 0)}")
        else:
            print(f"   ❌ {endpoint} - NOT INDEXED")
    
    # Show some random indexed endpoints for comparison
    print(f"\n📊 Sample of indexed endpoints (showing first 10):")
    for i, (endpoint, profile) in enumerate(list(discovery.tool_index.items())[:10]):
        print(f"   {i+1}. {endpoint}")
        keywords = profile.get('keywords', set())
        if isinstance(keywords, set):
            keywords = list(keywords)
        print(f"      Keywords: {keywords[:5]}...")

if __name__ == "__main__":
    asyncio.run(debug_semantic_discovery())