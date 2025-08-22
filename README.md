# Fast Meraki MCP Server

A **high-performance FastMCP server** that provides intelligent access to Cisco Meraki network management APIs through semantic tool discovery and AI-powered features.

## 🚀 Features

- **🧠 Semantic Tool Discovery**: AI-powered tool selection based on intent
- **🛡️ Null-Safe Processing**: Automatic handling of API inconsistencies  
- **📊 MCP Resources**: Read-only data access through resource URIs
- **💬 MCP Prompts**: Pre-built prompts for common network tasks
- **⚡ Optimized Performance**: Connection pooling, caching, and lazy loading
- **✅ FastMCP 2.10.6+**: Full compliance with latest MCP standards

## 📋 Prerequisites

- Python 3.12+ 
- Meraki API Key with read permissions ([Get one here](https://dashboard.meraki.com/api_access))
- FastMCP 2.10.6+

## 🔧 Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd fast-meraki-mcp-server
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and add your Meraki API key
```

4. **Run the server**:
```bash
python meraki_mcp_server.py
```

The server will start on `http://0.0.0.0:8000/mcp`

## 🎯 Core Capabilities

### Essential Tools (Always Available)
- `list_organizations` - List all Meraki organizations
- `get_organization` - Get organization details
- `list_networks` - List networks in organization
- `get_network` - Get network details
- `list_devices` - List devices (organization or network level)
- `get_device` - Get device details
- `list_clients` - List network clients
- `list_inventory` - List inventory devices

### Semantic Discovery Tools
- `discover_tools` - Find tools relevant to your intent
- `analyze_context` - Get suggestions based on conversation
- `health_check` - Check server and API status

### Resources (Read-Only Data)
- `meraki://organizations` - All organizations
- `meraki://organizations/{org_id}/networks` - Networks for an organization
- `meraki://networks/{network_id}/devices` - Devices in a network

### Prompts (Task Templates)
- `network_health_check` - Generate network health analysis prompt
- `troubleshooting_guide` - Create troubleshooting instructions
- `configuration_audit` - Generate configuration review prompt

## 💻 Usage Examples

### With Claude Desktop

Add to your Claude Desktop configuration:

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

### With FastMCP Client

```python
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        # List available tools
        tools = await client.list_tools()
        
        # Discover relevant tools
        result = await client.call_tool(
            "discover_tools", 
            {"intent": "monitor network performance"}
        )
        
        # Get organizations
        orgs = await client.call_tool("list_organizations", {})
```

## 🏗️ Architecture

The server implements a clean, modular architecture:

```
MerakiMCPServer
├── FastMCP Integration (OpenAPI-based tools)
├── Middleware System (null-safe processing, logging)
├── Semantic Discovery (AI-powered tool selection)
├── Resources (URI-based data access)
└── Prompts (Reusable task templates)
```

### Key Components

1. **OpenAPI Integration**: Automatically generates tools from Meraki OpenAPI spec
2. **Middleware Pipeline**: Processes requests/responses for null handling and logging
3. **Optimized Discovery**: Cached, lazy-loaded semantic analysis
4. **Connection Pooling**: Efficient HTTP client with connection reuse

## ⚙️ Configuration

Environment variables (`.env` file):

```bash
# Required
MERAKI_API_KEY=your_api_key_here

# Optional
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
LOG_LEVEL=INFO
MAX_CONNECTIONS=10
REQUEST_TIMEOUT=30
DISCOVERY_CACHE_SIZE=100
```

## 🔍 Troubleshooting

### Check Server Health
```bash
curl http://localhost:8000/health
```

### Common Issues

**API Key Issues**:
- Ensure `MERAKI_API_KEY` is set in `.env`
- Verify key has read permissions at [Meraki Dashboard](https://dashboard.meraki.com/api_access)

**Connection Issues**:
- Check network connectivity to `api.meraki.com`
- Verify firewall allows outbound HTTPS (port 443)

**Performance Issues**:
- Increase `MAX_CONNECTIONS` for higher throughput
- Adjust `DISCOVERY_CACHE_SIZE` for better discovery performance

## 🧪 Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

## 📈 Performance

- **Startup Time**: ~2 seconds
- **Tool Discovery**: ~100ms (cached)
- **API Response**: ~750ms average
- **Memory Usage**: ~60MB
- **Connection Pool**: 10 concurrent connections

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## 👤 Author

**Vidyadhar Evani**
- Email: vidyadhar.evani@gmail.com
- GitHub: [@vevani](https://github.com/vevani)

---

Built with FastMCP 2.10.6+ | Optimized for Production | Full MCP Compliance