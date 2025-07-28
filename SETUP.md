# Fast Meraki MCP Server Setup Guide

A semantic FastMCP server that provides intelligent access to Cisco Meraki APIs through AI-powered tool discovery and null-safe response processing.

## Features

- **🧠 Semantic Tool Discovery**: AI-powered analysis of user intent to discover relevant tools automatically
- **🎯 Smart Tool Selection**: Only 9 essential tools always available, others discovered on-demand  
- **🛡️ Null-Safe Processing**: Automatic handling of null values from Meraki API responses
- **📊 Three-Layer Architecture**: Clean separation of API, processing, and MCP layers
- **🔧 Production Ready**: Comprehensive error handling, logging, health monitoring, and async support
- **⚡ High Performance**: Optimized for minimal latency and resource usage

## Prerequisites

- **Python 3.12+** (recommended for best performance)
- **Cisco Meraki API key** with read permissions ([Get one here](https://dashboard.meraki.com/api_access))
- **FastMCP 2.10.6+** (current implementation version)

## Current Implementation Details

This server is built with **FastMCP 2.10.6** and implements:

- ✅ **Semantic Discovery System**: `SemanticToolDiscovery` class with AI-powered intent analysis
- ✅ **Null-Safe HTTP Client**: `NullSafeHTTPXClient` for preprocessing API responses
- ✅ **Essential Tool Registration**: 9 core Meraki tools explicitly registered as callable MCP tools
- ✅ **Health Monitoring**: Built-in health checks and tool information endpoints
- ✅ **Three-Layer Architecture**: API → Processing → MCP layers for maintainability

## Installation

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd fast-meraki-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root directory:
   ```bash
   # Required
   MERAKI_API_KEY=your_actual_meraki_api_key_here
   
   # Optional (defaults shown)
   MCP_SERVER_PORT=8000
   MCP_SERVER_HOST=0.0.0.0
   LOG_LEVEL=INFO
   ```

4. **Verify OpenAPI specification:**
   The server uses `openapi/spec3.json` - this should be present in the project root.

## Usage

### Start the Server

```bash
python meraki_mcp_server.py
```

**Expected startup output:**
```
🚀 Starting Semantic Meraki MCP Server
🎯 Server ready: 12 semantically selected tools
🧠 AI-powered: Smart discovery without overwhelm
🔄 Dynamic: Automatically adapts to spec changes
📡 MCP endpoint: http://0.0.0.0:8000/mcp
💊 Health check: http://0.0.0.0:8000/health
🔧 Tools info: http://0.0.0.0:8000/tools/info
```

### Available Endpoints

- **MCP Protocol**: `http://0.0.0.0:8000/mcp`
- **Health Check**: `http://0.0.0.0:8000/health`  
- **Tool Information**: `http://0.0.0.0:8000/tools/info`

### Tool Categories

The server provides **12 total tools** organized in two categories:

#### Essential Meraki Tools (9 tools - Always Available)
Core network management tools that are immediately callable:

| Tool | API Endpoint | Purpose |
|------|-------------|---------|
| `mcp_meraki_listOrganizations` | `GET /organizations` | List all accessible organizations |
| `mcp_meraki_getOrganization` | `GET /organizations/{organizationId}` | Get organization details |
| `mcp_meraki_listOrgNetworks` | `GET /organizations/{organizationId}/networks` | List networks in organization |
| `mcp_meraki_getNetwork` | `GET /networks/{networkId}` | Get network configuration |
| `mcp_meraki_listOrgDevices` | `GET /organizations/{organizationId}/devices` | List all devices in organization |
| `mcp_meraki_listNetworkDevices` | `GET /networks/{networkId}/devices` | List devices in specific network |
| `mcp_meraki_getDevice` | `GET /devices/{serial}` | Get device details and status |
| `mcp_meraki_listNetworkClients` | `GET /networks/{networkId}/clients` | List clients connected to network |
| `mcp_meraki_listOrgInventoryDevices` | `GET /organizations/{organizationId}/inventory/devices` | List inventory devices |

#### AI-Powered Discovery Tools (3 tools)
Intelligent meta-tools for enhanced user experience:

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `discoverRelevantTools` | AI-powered tool discovery based on intent | Input: "I want to monitor network performance" |
| `analyzeConversationContext` | Analyze conversation for better tool suggestions | Automatic context-aware recommendations |
| `explainSemanticDiscovery` | Explain how the discovery system works | Learn about the AI capabilities |

## Architecture Details

### Semantic Tool Discovery System

The server implements intelligent tool discovery through several components:

1. **Semantic Profile Building**: Each API endpoint gets analyzed for:
   - **Keywords**: Extracted from paths, descriptions, and operation IDs
   - **Use Cases**: Generated based on endpoint analysis
   - **Priority**: Calculated based on common usage patterns (1-10 scale)
   - **Complexity**: Determined by required parameters (1-10 scale)

2. **Intent Analysis**: User requests are processed to:
   - Extract semantic keywords and intent
   - Score relevance against available tools
   - Return ranked recommendations

3. **Context Learning**: The system maintains conversation context to improve suggestions over time.

### Null-Safe Processing

The `NullSafeHTTPXClient` automatically handles Meraki API quirks:

```python
class NullSafeHTTPXClient(httpx.AsyncClient):
    def _clean_null_values(self, data):
        """Converts null values to empty strings for FastMCP compatibility"""
        if data is None:
            return ""  # Prevents validation errors
        # Recursive processing for nested objects and arrays
```

## API Integration Examples

### Using with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "servers": {
    "meraki": {
      "command": "python",
      "args": ["/path/to/fast-meraki-mcp-server/meraki_mcp_server.py"],
      "env": {
        "MERAKI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Using with FastMCP Client

```python
import asyncio
from fastmcp.client import Client

async def test_meraki_mcp():
    # Connect to the semantic Meraki MCP server
    client = Client("http://0.0.0.0:8000/mcp")
    
    # Test essential tools
    result = await client.call_tool("mcp_meraki_listOrganizations")
    print(f"Organizations: {result}")
    
    # Test AI-powered discovery
    discovery_result = await client.call_tool(
        "discoverRelevantTools", 
        {"intent": "monitor network performance", "max_tools": 5}
    )
    print(f"Discovered tools: {discovery_result}")
    
    # Get explanation of the system
    explanation = await client.call_tool("explainSemanticDiscovery")
    print(f"System explanation: {explanation}")

if __name__ == "__main__":
    asyncio.run(test_meraki_mcp())
```

## Health & Monitoring

### Health Check
```bash
curl http://0.0.0.0:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "null_safe_processing": "active",
  "fastmcp_compliance": "100%",
  "filtering_method": "FastMCP route mapping with null-safe HTTPX client"
}
```

### Tool Information
```bash
curl http://0.0.0.0:8000/tools/info
```

Provides statistics about available tools and server performance.

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure `MERAKI_API_KEY` is set in your `.env` file
2. **API Permissions**: Verify your API key has read access to organizations
3. **Network Access**: Ensure the server can reach `api.meraki.com`
4. **Port Conflicts**: Check if port 8000 is available

### Debug Mode

Enable detailed logging:
```bash
LOG_LEVEL=DEBUG python meraki_mcp_server.py
```

### Logs

Server logs are automatically created in the `logs/` directory with detailed information about:
- Server startup and configuration
- Tool discovery and registration
- API calls and responses
- Error handling and debugging

## Performance Characteristics

- **Startup Time**: ~2-3 seconds (OpenAPI spec analysis)
- **Tool Discovery**: ~100-200ms (semantic analysis)
- **API Response**: ~500-1000ms (depends on Meraki API)
- **Memory Usage**: ~50-100MB (spec caching and discovery system)

## Summary

This Fast Meraki MCP Server provides:

✅ **AI-Powered Intelligence**: Semantic tool discovery prevents tool overwhelm  
✅ **Production Ready**: Null-safe processing, comprehensive error handling  
✅ **Easy Integration**: Works with Claude Desktop and FastMCP clients  
✅ **High Performance**: Optimized three-layer architecture  
✅ **Maintainable**: Clean separation of concerns and comprehensive logging  

For detailed architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Cisco Meraki API Documentation](https://developer.cisco.com/meraki/api-v1/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)

## 📝 License

This project is licensed under the Apache License, Version 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Vidyadhar Evani <vidyadhar.evani@gmail.com>

## 👤 Author & Contact

**Vidyadhar Evani**
- Email: vidyadhar.evani@gmail.com
- GitHub: [@vevani](https://github.com/vevani)

For questions, issues, or contributions related to this Fast Meraki MCP Server implementation, please contact the author or create an issue in the repository.

## 🤝 Contributing

We welcome contributions! Please see the main [README.md](README.md) for contribution guidelines. 