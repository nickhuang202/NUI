from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("NUI_Stats")

# Base URL for the NUI REST API
NUI_API_BASE = "http://172.17.9.199:5000/api"

@mcp.tool()
async def get_system_health() -> str:
    """Check overall system CPU, memory, and service health."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NUI_API_BASE}/v1/health")
            response.raise_for_status()
            return str(response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"


@mcp.tool()
async def get_test_status() -> str:
    """Check if a standard test is currently running or finished."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NUI_API_BASE}/test/status")
            response.raise_for_status()
            return str(response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"


@mcp.tool()
async def get_port_status() -> str:
    """View link UP/DOWN status of all ports."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NUI_API_BASE}/port_status")
            response.raise_for_status()
            return str(response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"


@mcp.tool()
async def get_transceiver_info() -> str:
    """Get optical metrics (temperature, power levels) of inserted transceivers."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NUI_API_BASE}/transceiver_info")
            response.raise_for_status()
            return str(response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"

if __name__ == "__main__":
    import asyncio
    
    # Example usage. To run the server, use `mcp run mcp_server.py`
    async def main():
        print("MCP Server 'NUI_Stats' initialized. Start it by running: mcp run mcp_server.py")
        print("\nTesting 'get_system_health()':")
        try:
            print(await get_system_health())
        except Exception as e:
            print(e)
            
    asyncio.run(main())
