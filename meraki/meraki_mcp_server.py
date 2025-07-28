import os
from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP
import json
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Setup logging
logger.add("logs/meraki_mcp.log", rotation="10 MB", retention="7 days")
logger.info("Starting Meraki MCP Server")

# Get the API key from environment variables
api_key = os.getenv("MERAKI_API_KEY")
logger.info("Loaded MERAKI_API_KEY from environment variables.")

# Load your local OpenAPI spec
with open("openapi/spec3.json", "r") as f:
    openapi_spec = json.load(f)
logger.info("Loaded OpenAPI spec from openapi/spec3.json.")

# Create an HTTP client for the Meraki API
client = httpx.AsyncClient(
    base_url="https://api.meraki.com/api/v1",
    headers={"X-Cisco-Meraki-API-Key": api_key}
)
logger.info("Created HTTP client for Meraki API.")

# Create the MCP server from the OpenAPI spec
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=client,
    name="Cisco Meraki MCP Server"
)
logger.info("Created FastMCP server from OpenAPI spec.")

if __name__ == "__main__":
    logger.info("Starting MCP server on port 8000.")
    mcp.run(transport="http", host="0.0.0.0", port=8000)
