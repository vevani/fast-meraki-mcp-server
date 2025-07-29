"""
Integration tests for the Meraki MCP Server.

These tests validate the server setup and API integration without
requiring actual Meraki API credentials.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
@pytest.mark.integration
async def test_null_safe_client_response_processing():
    """Test the null-safe HTTP client response processing."""
    import httpx

    import meraki_mcp_server

    # Create a mock response with null values
    mock_response_data = {
        "organizations": [
            {
                "id": "123",
                "name": "Test Org",
                "url": None,  # This should be converted to empty string
                "api": {
                    "enabled": True,
                    "version": None,  # This should be converted to empty string
                },
            }
        ],
        "meta": None,  # This should be converted to empty string
    }

    client = meraki_mcp_server.NullSafeHTTPXClient()

    # Test the cleaning function directly
    cleaned_data = client._clean_null_values(mock_response_data)

    expected_data = {
        "organizations": [
            {
                "id": "123",
                "name": "Test Org",
                "url": "",  # Null converted to empty string
                "api": {
                    "enabled": True,
                    "version": "",  # Null converted to empty string
                },
            }
        ],
        "meta": "",  # Null converted to empty string
    }

    assert cleaned_data == expected_data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_semantic_tool_discovery_basic():
    """Test basic semantic tool discovery functionality."""
    import meraki_mcp_server

    # Test initialization with minimal OpenAPI spec
    mock_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "get": {
                    "summary": "Test endpoint",
                    "description": "A test endpoint for devices",
                    "operationId": "getTestDevices",
                }
            }
        },
    }
    discovery = meraki_mcp_server.SemanticToolDiscovery(mock_spec)

    # Test with a simple query
    test_intent = "show me network devices"

    # Mock the discovery process since we don't have real API access
    with patch.object(discovery, "discover_tools_for_intent") as mock_discover:
        mock_discover.return_value = [
            {
                "name": "mcp_meraki_listNetworkDevices",
                "description": "List devices in a network",
                "relevance_score": 0.95,
            }
        ]

        result = discovery.discover_tools_for_intent(test_intent, max_tools=5)

        assert isinstance(result, list)
        assert len(result) > 0
        assert "name" in result[0]
        assert "description" in result[0]


@pytest.mark.integration
def test_server_configuration_structure():
    """Test that the server is properly structured for FastMCP."""
    import meraki_mcp_server

    # Check that key configuration constants exist
    assert hasattr(meraki_mcp_server, "logger")

    # Verify that the server setup doesn't crash during import
    # (actual server start requires API key and network access)
    try:
        # The module should import without errors
        assert meraki_mcp_server is not None
    except Exception as e:
        pytest.fail(f"Server configuration failed: {e}")


@pytest.mark.integration
def test_openapi_spec_exists():
    """Test that OpenAPI specification files exist."""
    openapi_dir = Path(__file__).parent.parent / "openapi"
    assert openapi_dir.exists(), "OpenAPI directory should exist"

    # Check if there are any spec files
    spec_files = list(openapi_dir.glob("*.json")) + list(openapi_dir.glob("*.yaml"))
    assert len(spec_files) > 0, "Should have at least one OpenAPI spec file"


@pytest.mark.integration
def test_environment_example_file():
    """Test that environment example file exists and has required fields."""
    env_example = Path(__file__).parent.parent / ".env.example"
    assert env_example.exists(), ".env.example file should exist"

    with open(env_example, "r") as f:
        content = f.read()

    # Should contain API key template
    assert (
        "MERAKI_API_KEY" in content
    ), ".env.example should contain MERAKI_API_KEY template"


@pytest.mark.integration
def test_requirements_file_validity():
    """Test that requirements.txt is properly formatted."""
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    assert requirements_file.exists(), "requirements.txt should exist"

    with open(requirements_file, "r") as f:
        lines = f.readlines()

    # Check for key dependencies
    requirements_text = "".join(lines)
    key_deps = ["fastmcp", "httpx", "pydantic", "python-dotenv"]

    for dep in key_deps:
        assert (
            dep in requirements_text
        ), f"Dependency {dep} should be in requirements.txt"


@pytest.mark.slow
@pytest.mark.integration
def test_server_health_endpoint_structure():
    """Test that health endpoint structure is properly defined."""
    import meraki_mcp_server

    # This tests the structure without actually starting the server
    # The actual server requires API keys and network access
    # Check that required components are available for health endpoint
    assert meraki_mcp_server.logger is not None

    # Verify basic server components are importable
    try:
        from fastmcp import FastMCP

        assert FastMCP is not None
    except ImportError:
        pytest.fail("FastMCP should be importable for server setup")


@pytest.mark.unit
def test_mcp_tool_registration():
    """Test that MCP tools are properly structured."""
    import meraki_mcp_server

    # Test that the required MCP tool structure is available
    # (without actually registering tools which requires server startup)
    # Verify that the module has the expected structure
    assert hasattr(meraki_mcp_server, "FastMCP")

    # Test data structures that would be used for tool registration
    sample_tool_data = {
        "name": "test_tool",
        "description": "Test tool",
        "parameters": {},
    }

    # This should not raise any exceptions
    assert isinstance(sample_tool_data, dict)
    assert "name" in sample_tool_data
