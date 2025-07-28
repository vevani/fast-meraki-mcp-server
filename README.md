# Fast Meraki MCP Server

A **semantic FastMCP server** that provides intelligent access to Cisco Meraki network management APIs through AI-powered tool discovery and null-safe response processing.

## 🧠 Semantic Discovery & AI-Powered Intelligence

This server implements **semantic tool discovery** to solve the "tool overwhelm" problem - instead of exposing 500+ Meraki API endpoints, it intelligently discovers and suggests only the tools relevant to your specific intent.

### Key Features

- 🧠 **AI-Powered Tool Discovery**: Semantic analysis of user intent to find relevant tools automatically
- 🎯 **Smart Tool Selection**: Only 9 essential tools always available, others discovered on-demand
- 🛡️ **Null-Safe Processing**: Automatically handles null values from Meraki API responses 
- ✅ **FastMCP 2.10.6 Compliant**: Uses latest FastMCP patterns and best practices
- 🔧 **Production-Ready**: Comprehensive error handling, logging, and health monitoring
- 📊 **Three-Layer Architecture**: Clean separation of API, processing, and MCP layers

### Architecture Overview

The server implements a sophisticated **three-layer architecture**:

1. **API Layer**: `NullSafeHTTPXClient` - handles Meraki API communication with preprocessing
2. **Processing Layer**: `SemanticToolDiscovery` - AI-powered tool selection and conversation analysis  
3. **MCP Layer**: FastMCP server integration with health monitoring and tool management

*See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation.*

### Problems Solved

#### 🧠 Tool Overwhelm Prevention
**Problem**: Meraki API has 500+ endpoints, overwhelming for LLMs and users
**Solution**: Semantic discovery analyzes user intent and suggests only relevant tools
**Benefit**: Users get exactly what they need without cognitive overload

#### 🛡️ Null Value Handling  
**Problem**: Meraki API returns null values that break FastMCP validation
**Solution**: `NullSafeHTTPXClient` preprocesses responses before validation
**Result**: Zero breaking changes, seamless API integration

#### 🔧 Discovery vs Registration Gap
**Problem**: Previous implementations could discover tools but not call them
**Solution**: Explicitly register 9 essential tools as callable MCP tools
**Result**: Tools are both discoverable AND usable

## 🚀 Quick Start

### Prerequisites

- Python 3.12+ (recommended for best performance)
- Meraki API Key with read permissions ([Get one here](https://dashboard.meraki.com/api_access))
- FastMCP 2.10.6+ for semantic discovery support

### Installation

1. **Clone and Setup**:
```bash
git clone <repository-url>
cd fast-meraki-mcp-server
pip install -r requirements.txt
```

2. **Configure Environment**:
```bash
# Create .env file from template
cp .env.example .env
# Edit .env file with your actual API key
# MERAKI_API_KEY=your_actual_api_key_here
```

3. **Run the Server**:
```bash
python meraki_mcp_server.py
```

The server will start with semantic discovery and null-safe processing:
- **MCP Endpoint**: `http://0.0.0.0:8000/mcp`
- **Health Check**: `http://0.0.0.0:8000/health`
- **Tools Info**: `http://0.0.0.0:8000/tools/info`

### Startup Log Example
```
🚀 Starting Semantic Meraki MCP Server
🎯 Server ready: 12 semantically selected tools
🧠 AI-powered: Smart discovery without overwhelm  
🔄 Dynamic: Automatically adapts to spec changes
📡 MCP endpoint: http://0.0.0.0:8000/mcp
```

## 🔧 FastMCP Integration

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
from fastmcp.client import Client

# Connect to the null-safe Meraki MCP server
client = Client("http://localhost:8000/mcp")

# Test null-safe processing
result = await client.call_tool("diagnose_null_handling")
print(result)  # ✅ Null-safe processing is working correctly
```

## 🛡️ Null-Safe Processing Details

### How It Works

The `NullSafeHTTPXClient` intercepts HTTP responses and preprocesses them:

```python
class NullSafeHTTPXClient(httpx.AsyncClient):
    async def send(self, request, **kwargs):
        response = await super().send(request, **kwargs)
        
        if response.headers.get("content-type", "").startswith("application/json"):
            json_content = response.json()
            cleaned_content = self._clean_null_values(json_content)
            response._content = json.dumps(cleaned_content).encode('utf-8')
        
        return response
    
    def _clean_null_values(self, data):
        """Recursively converts null values to empty strings"""
        if data is None:
            return ""  # Convert null to empty string
        elif isinstance(data, dict):
            return {k: self._clean_null_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_null_values(item) for item in data]
        else:
            return data
```

### Benefits

- **Zero API Breakage**: Works with existing Meraki API without changes
- **FastMCP Compliant**: Follows FastMCP 2.0 best practices and patterns
- **Transparent**: Null processing is automatic and doesn't affect normal responses
- **Debuggable**: Includes diagnostic tools to verify null-safe processing

## 📊 Available Tools

The server provides **12 total tools**: 9 essential Meraki tools + 3 intelligent discovery tools.

### Essential Meraki Tools (Always Available)
Core network management functionality for immediate use:

| Tool | Description | Use Case |
|------|-------------|----------|
| `mcp_meraki_listOrganizations` | List all organizations | Starting point for all operations |
| `mcp_meraki_getOrganization` | Get organization details | Organization information and settings |
| `mcp_meraki_listOrgNetworks` | List networks in organization | Network discovery and overview |
| `mcp_meraki_getNetwork` | Get network details | Network configuration and status |
| `mcp_meraki_listOrgDevices` | List devices in organization | Device inventory and management |
| `mcp_meraki_listNetworkDevices` | List devices in network | Network-specific device listing |
| `mcp_meraki_getDevice` | Get device details | Device status and configuration |
| `mcp_meraki_listNetworkClients` | List clients in network | Client monitoring and troubleshooting |
| `mcp_meraki_listOrgInventoryDevices` | List inventory devices | Hardware inventory management |

### AI-Powered Discovery Tools
Intelligent tools for enhanced user experience:

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `discoverRelevantTools` | Find tools relevant to your intent | "I want to monitor network performance" |
| `analyzeConversationContext` | Analyze conversation for better suggestions | Automatic context awareness |
| `explainSemanticDiscovery` | Understand how the discovery system works | Learn about the AI capabilities |

## 🔍 Troubleshooting

### Health & Status Checks

**Check Server Health**:
```bash
curl http://0.0.0.0:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "null_safe_processing": "active",
  "fastmcp_compliance": "100%",
  "filtering_method": "FastMCP route mapping with null-safe HTTPX client"
}
```

**Check Tool Information**:
```bash
curl http://0.0.0.0:8000/tools/info
```

### Common Issues & Solutions

#### Server Won't Start
- ❌ **Missing API Key**: Ensure `MERAKI_API_KEY` is set in your `.env` file
- ❌ **Permission Issues**: Verify API key has read access to organizations
- ❌ **Port Conflicts**: Check if port 8000 is already in use

#### API Key Problems  
- ❌ **Invalid Key**: Verify your API key at [Meraki Dashboard](https://dashboard.meraki.com/api_access)
- ❌ **Insufficient Permissions**: Ensure read access to the organizations you want to query
- ❌ **Network Access**: Verify the server can reach `api.meraki.com`

#### Tool Discovery Issues
- ❌ **No Results**: Try different intent descriptions (e.g., "show network devices" vs "device management")
- ❌ **Wrong Tools**: The semantic analysis learns from conversation - provide more context
- ❌ **Too Many Tools**: Use `max_tools` parameter to limit results

### Debug Mode

For detailed logging, set environment variable:
```bash
LOG_LEVEL=DEBUG python meraki_mcp_server.py
```

Check logs in the `logs/` directory for detailed information.

## 📈 Performance & Monitoring

### Health Monitoring

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "null_safe_processing": "active",
  "fastmcp_compliance": "100%",
  "filtering_method": "FastMCP route mapping with null-safe HTTPX client"
}
```

### Tool Statistics

```bash
curl http://localhost:8000/tools/info
```

## 🏗️ Architecture

The server implements a **three-layer approach** for FastMCP compliance:

1. **API Layer**: `NullSafeHTTPXClient` handles Meraki API communication
2. **Processing Layer**: Null-safe preprocessing before FastMCP validation
3. **MCP Layer**: FastMCP server with route filtering and tool management

This architecture ensures **100% FastMCP compliance** while gracefully handling real-world API inconsistencies.

## 🤝 Contributing

When contributing, ensure:

- ✅ **FastMCP Compliance**: Follow FastMCP 2.0 patterns and best practices
- ✅ **Null-Safe Processing**: Maintain null value handling for all new endpoints
- ✅ **Production Quality**: No shortcuts, no mock data, comprehensive error handling
- ✅ **Documentation**: Update inline comments and architecture documentation

## 📝 License

This project is licensed under the Apache License, Version 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Vidyadhar Evani <vidyadhar.evani@gmail.com>

## 👤 Author

**Vidyadhar Evani**
- Email: vidyadhar.evani@gmail.com
- GitHub: [@vevani](https://github.com/vevani)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](../../issues).

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

**Built with FastMCP 2.0 | Null-Safe Processing | Production Ready** 🚀
