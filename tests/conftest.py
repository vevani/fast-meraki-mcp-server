"""Test configuration and fixtures for the Meraki MCP Server tests."""

import os
import sys
from pathlib import Path

import pytest

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    # Store original values
    original_values = {}

    # Set test environment variables
    test_env_vars = {"MERAKI_API_KEY": "test_key_not_real", "LOG_LEVEL": "DEBUG"}

    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield test_env_vars

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def sample_meraki_response():
    """Sample Meraki API response data with null values for testing."""
    return {
        "organizations": [
            {
                "id": "123456",
                "name": "Test Organization",
                "url": None,  # This should be cleaned
                "api": {"enabled": True, "version": None},  # This should be cleaned
                "licensing": {
                    "model": "co-term",
                    "seat_count": None,  # This should be cleaned
                },
            }
        ],
        "networks": [
            {
                "id": "L_123456789",
                "organizationId": "123456",
                "name": "Test Network",
                "timeZone": "America/Los_Angeles",
                "tags": None,  # This should be cleaned
                "productTypes": ["appliance", "switch"],
                "notes": None,  # This should be cleaned
            }
        ],
        "devices": None,  # This should be cleaned to empty string
    }


@pytest.fixture
def sample_tool_discovery_data():
    """Sample data for semantic tool discovery testing."""
    return {
        "intent": "show me network devices",
        "expected_tools": [
            {
                "name": "mcp_meraki_listNetworkDevices",
                "description": "List devices in a specific network",
                "relevance_score": 0.95,
            },
            {
                "name": "mcp_meraki_listOrgDevices",
                "description": "List all devices in an organization",
                "relevance_score": 0.90,
            },
            {
                "name": "mcp_meraki_getDevice",
                "description": "Get details for a specific device",
                "relevance_score": 0.85,
            },
        ],
    }


# Configure pytest markers for different test types
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file names or locations
        if "test_basic" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
