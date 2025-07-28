# Cisco Meraki MCP Server

A FastMCP-based Model Context Protocol (MCP) server providing access to the Cisco Meraki Dashboard API. This implementation follows GoFastMCP standards for OpenAPI integration and ensures 100% compliance with MCP specifications.

## Features

- **Full OpenAPI 3.0+ Compliance**: Complete implementation of Cisco Meraki Dashboard API v1.60.0
- **FastMCP Integration**: Built using FastMCP framework for optimal performance and standards compliance
- **Comprehensive Error Handling**: Robust error handling with detailed logging and validation
- **Health Monitoring**: Built-in health checks for API connectivity and service status
- **Container Ready**: Docker support with proper health checks and security practices
- **Configuration Management**: Environment-based configuration with validation
- **Structured Logging**: Comprehensive logging with rotation and compression

## Quick Start

### Prerequisites

- Python 3.12+
- Cisco Meraki Dashboard API key
- FastMCP compatible environment

### Installation

1. Clone the repository:
```bash
git clone https://github.com/vevani/fast-meraki-mcp-server.git
cd fast-meraki-mcp-server/meraki
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Meraki API key
```

4. Run the server:
```bash
python meraki_mcp_server.py
```

### Docker Deployment

```bash
# Build the image
docker build -t meraki-mcp-server .

# Run the container
docker run -d \
  --name meraki-mcp \
  -p 8000:8000 \
  -e MERAKI_API_KEY=your_api_key_here \
  meraki-mcp-server
```

## Configuration

The server supports configuration through environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MERAKI_API_KEY` | Yes | - | Meraki Dashboard API key |
| `MERAKI_BASE_URL` | No | `https://api.meraki.com/api/v1` | Meraki API base URL |
| `MERAKI_TIMEOUT` | No | `30` | HTTP request timeout (seconds) |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FILE` | No | `logs/meraki_mcp.log` | Log file path |

## API Coverage

This MCP server provides access to all 840 operations across 570 API endpoints, including:

- **Network Management**: Organizations, networks, devices
- **Configuration**: Switch, wireless, security appliance settings
- **Monitoring**: Device status, network health, analytics
- **Security**: Content filtering, threat protection, VPN
- **Administration**: Admins, API keys, audit logs

## Health Monitoring

The server includes comprehensive health checking:

- **API Connectivity**: Validates Meraki API authentication and accessibility
- **OpenAPI Spec**: Verifies specification integrity and completeness  
- **Service Status**: Overall service health and uptime metrics

Access health status:
```bash
# Via Python module
python -m health_check

# Health endpoint (when available)
curl http://localhost:8000/health
```

## Standards Compliance

This implementation ensures 100% compliance with:

- **GoFastMCP Standards**: Complete adherence to FastMCP integration guidelines
- **OpenAPI 3.0+**: Full specification compliance with proper schemas and validation
- **MCP Protocol**: Model Context Protocol standards for tool definitions and interactions
- **Security Best Practices**: Proper authentication, input validation, and error handling

## Development

### Project Structure

```
meraki/
├── __init__.py              # Package initialization and metadata
├── meraki_mcp_server.py     # Main server implementation
├── health_check.py          # Health monitoring utilities
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── .env.example           # Environment configuration template
└── openapi/
    └── spec3.json         # Cisco Meraki OpenAPI specification
```

### Testing

```bash
# Test API connectivity
python -c "from health_check import simple_health_check; import asyncio; print(asyncio.run(simple_health_check()))"

# Validate OpenAPI spec
python -c "
import json
with open('openapi/spec3.json') as f:
    spec = json.load(f)
print(f'Loaded {len(spec[\"paths\"])} paths with {sum(len(methods) for methods in spec[\"paths\"].values())} operations')
"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the existing code style
4. Ensure all health checks pass
5. Submit a pull request

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues and questions:
- Check the health status endpoint for service diagnostics
- Review logs for detailed error information
- Consult the Cisco Meraki API documentation for endpoint-specific details
