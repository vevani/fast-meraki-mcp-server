"""
Basic tests for the Meraki MCP Server.

Since this is a server that requires API keys and external dependencies,
most tests are basic import and structure tests.
"""

import os
import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_server():
    """Test that the server module can be imported successfully."""
    import meraki_mcp_server

    assert meraki_mcp_server is not None


def test_server_module_attributes():
    """Test that the server module has expected attributes."""
    import meraki_mcp_server

    # Check that key classes are available
    assert hasattr(meraki_mcp_server, "NullSafeHTTPXClient")
    assert hasattr(meraki_mcp_server, "SemanticToolDiscovery")


def test_python_version():
    """Test that we're running on supported Python version."""
    assert sys.version_info >= (3, 12), "Python 3.12+ is required"


def test_required_dependencies():
    """Test that required dependencies can be imported."""
    try:
        import dotenv
        import fastmcp
        import httpx
        import pydantic

        assert True  # All imports successful
    except ImportError as e:
        pytest.fail(f"Required dependency missing: {e}")


@pytest.mark.unit
def test_environment_variable_handling():
    """Test environment variable handling without actual API key."""
    import meraki_mcp_server

    # Test with missing API key
    old_key = os.environ.get("MERAKI_API_KEY")
    if "MERAKI_API_KEY" in os.environ:
        del os.environ["MERAKI_API_KEY"]

    # Should not crash even without API key
    try:
        # Just test that the module loads
        assert meraki_mcp_server.logger is not None
    finally:
        # Restore original key if it existed
        if old_key:
            os.environ["MERAKI_API_KEY"] = old_key


@pytest.mark.unit
def test_null_safe_client_initialization():
    """Test that NullSafeHTTPXClient can be initialized."""
    import meraki_mcp_server

    # Test initialization without making actual HTTP calls
    client = meraki_mcp_server.NullSafeHTTPXClient()
    assert client is not None
    assert hasattr(client, "_clean_null_values")


def test_null_safe_data_cleaning():
    """Test the null value cleaning functionality."""
    import meraki_mcp_server

    client = meraki_mcp_server.NullSafeHTTPXClient()

    # Test cleaning various data types
    test_cases = [
        (None, ""),
        ({"key": None}, {"key": ""}),
        ([None, "value"], ["", "value"]),
        ({"nested": {"null_key": None}}, {"nested": {"null_key": ""}}),
        ("normal_string", "normal_string"),
        (123, 123),
        (True, True),
    ]

    for input_data, expected in test_cases:
        result = client._clean_null_values(input_data)
        assert result == expected, f"Failed for input {input_data}"


@pytest.mark.unit
def test_semantic_tool_discovery_initialization():
    """Test that SemanticToolDiscovery can be initialized."""
    import meraki_mcp_server

    # Test initialization with minimal OpenAPI spec
    mock_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    discovery = meraki_mcp_server.SemanticToolDiscovery(mock_spec)
    assert discovery is not None
    assert hasattr(discovery, "discover_tools_for_intent")
    assert hasattr(discovery, "get_always_available_tools")


def test_gitignore_patterns():
    """Test that sensitive files are properly ignored."""
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    assert gitignore_path.exists(), ".gitignore file should exist"

    with open(gitignore_path, "r") as f:
        gitignore_content = f.read()

    # Check for important patterns
    important_patterns = [".env", "__pycache__", "*.log", ".vscode"]
    for pattern in important_patterns:
        assert (
            pattern in gitignore_content
        ), f"Pattern {pattern} should be in .gitignore"
