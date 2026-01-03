"""Main MCP server entry point for Sonos control."""

import asyncio
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .api_client import SonosApiClient
from .tools import register_tools


def main():
    """Run the Sonos MCP server."""
    # Get API URL from environment or use default
    api_url = os.environ.get("SONOS_API_URL", "http://localhost:5000")
    
    # Create API client
    client = SonosApiClient(base_url=api_url)
    
    # Create MCP server
    server = Server("sonos-mcp-server")
    
    # Register all tools
    register_tools(server, client)
    
    async def run():
        """Run the server with stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    main()
