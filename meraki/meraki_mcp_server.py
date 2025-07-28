"""
Cisco Meraki MCP Server

A FastMCP-based Model Context Protocol server providing access to the Cisco Meraki Dashboard API.
This implementation follows GoFastMCP standards for OpenAPI integration and MCP tool compliance.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import json
import asyncio

from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP
from loguru import logger
from pydantic import BaseModel, Field


class MerakiMCPConfig(BaseModel):
    """Configuration model for Meraki MCP Server with validation."""
    
    api_key: str = Field(..., description="Meraki Dashboard API key")
    base_url: str = Field(
        default="https://api.meraki.com/api/v1",
        description="Meraki API base URL"
    )
    timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(
        default="logs/meraki_mcp.log",
        description="Log file path"
    )


class MerakiMCPServer:
    """
    Cisco Meraki MCP Server implementation.
    
    Provides a FastMCP-compliant server for accessing Cisco Meraki Dashboard API
    through the Model Context Protocol.
    """
    
    def __init__(self, config: MerakiMCPConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.mcp: Optional[FastMCP] = None
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Configure structured logging for the MCP server."""
        logger.remove()  # Remove default handler
        
        # Add console logging
        logger.add(
            sys.stderr,
            level=self.config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>"
        )
        
        # Add file logging if specified
        if self.config.log_file:
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                self.config.log_file,
                level=self.config.log_level,
                rotation="10 MB",
                retention="7 days",
                compression="gz",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
            )
        
        logger.info("Logging configured for Meraki MCP Server")
    
    def _load_openapi_spec(self) -> dict:
        """Load and validate the OpenAPI specification."""
        spec_path = Path(__file__).parent / "openapi" / "spec3.json"
        
        if not spec_path.exists():
            raise FileNotFoundError(f"OpenAPI spec not found at {spec_path}")
        
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
            
            # Basic validation
            required_fields = ["openapi", "info", "paths"]
            for field in required_fields:
                if field not in spec:
                    raise ValueError(f"OpenAPI spec missing required field: {field}")
            
            logger.info(
                f"Loaded OpenAPI spec: {spec['info']['title']} v{spec['info']['version']} "
                f"({len(spec['paths'])} paths)"
            )
            return spec
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in OpenAPI spec: {e}")
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create configured HTTP client for Meraki API."""
        headers = {
            "X-Cisco-Meraki-API-Key": self.config.api_key,
            "Content-Type": "application/json",
            "User-Agent": "FastMCP-Meraki-Server/1.0.0"
        }
        
        client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=httpx.Timeout(self.config.timeout),
            follow_redirects=True
        )
        
        logger.info(f"Created HTTP client for Meraki API: {self.config.base_url}")
        return client
    
    async def initialize(self) -> None:
        """Initialize the MCP server components."""
        try:
            # Load OpenAPI specification
            openapi_spec = self._load_openapi_spec()
            
            # Create HTTP client
            self.client = self._create_http_client()
            
            # Test API connectivity
            await self._test_api_connection()
            
            # Create FastMCP server with enhanced configuration
            self.mcp = FastMCP.from_openapi(
                openapi_spec=openapi_spec,
                client=self.client,
                name="Cisco Meraki MCP Server",
                description="Model Context Protocol server for Cisco Meraki Dashboard API",
                version="1.0.0"
            )
            
            logger.info("Meraki MCP Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
    
    async def _test_api_connection(self) -> None:
        """Test API connectivity and authentication."""
        if not self.client:
            raise RuntimeError("HTTP client not initialized")
        
        try:
            # Test with a simple endpoint
            response = await self.client.get("/administered/identities/me")
            response.raise_for_status()
            
            user_info = response.json()
            logger.info(f"API connection successful. Authenticated as: {user_info.get('name', 'Unknown')}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid Meraki API key") from e
            elif e.response.status_code == 403:
                raise ValueError("Insufficient API permissions") from e
            else:
                raise ValueError(f"API connection failed: {e.response.status_code}") from e
        except Exception as e:
            raise ValueError(f"API connection test failed: {e}") from e
    
    async def run(self, transport: str = "http", host: str = "0.0.0.0", port: int = 8000) -> None:
        """Run the MCP server."""
        if not self.mcp:
            raise RuntimeError("MCP server not initialized. Call initialize() first.")
        
        logger.info(f"Starting Meraki MCP Server on {host}:{port} using {transport} transport")
        
        try:
            await self.mcp.run(transport=transport, host=host, port=port)
        except Exception as e:
            logger.error(f"MCP server error: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.aclose()
            logger.info("HTTP client closed")


def load_config() -> MerakiMCPConfig:
    """Load configuration from environment variables and .env file."""
    load_dotenv()
    
    api_key = os.getenv("MERAKI_API_KEY")
    if not api_key:
        raise ValueError(
            "MERAKI_API_KEY environment variable is required. "
            "Please set it in your environment or .env file."
        )
    
    config = MerakiMCPConfig(
        api_key=api_key,
        base_url=os.getenv("MERAKI_BASE_URL", "https://api.meraki.com/api/v1"),
        timeout=int(os.getenv("MERAKI_TIMEOUT", "30")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/meraki_mcp.log")
    )
    
    return config


async def main() -> None:
    """Main entry point for the Meraki MCP Server."""
    try:
        # Load configuration
        config = load_config()
        
        # Create and initialize server
        server = MerakiMCPServer(config)
        await server.initialize()
        
        # Run server
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
