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


@mcp.tool()
async def get_schedule_profiles() -> str:
    """List current saved schedule profiles."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NUI_API_BASE}/schedule/profiles")
            response.raise_for_status()
            return str(response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"


@mcp.tool()
async def get_schedule_profile(profile_name: str) -> str:
    """Get full content of one schedule profile by name."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NUI_API_BASE}/schedule/profiles/{profile_name}")
            response.raise_for_status()
            return str(response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"


@mcp.tool()
async def set_schedule_profile_daily_time(profile_name: str, hour: int, minute: int = 0) -> str:
    """Set schedule profile to run every day at specific time and shift test offsets accordingly."""
    if hour < 0 or hour > 23:
        return "Invalid hour. Expected 0-23."
    if minute < 0 or minute > 59:
        return "Invalid minute. Expected 0-59."

    cron_expr = f"{minute} {hour} * * *"
    target_offset_minutes = (hour * 60) + minute

    async with httpx.AsyncClient() as client:
        try:
            get_response = await client.get(f"{NUI_API_BASE}/schedule/profiles/{profile_name}")
            get_response.raise_for_status()
            get_data = get_response.json()
            if not get_data.get('success'):
                return str(get_data)

            profile_data = get_data.get('data') or {}
            profile_data['profile_name'] = profile_name
            profile_data['cron_rule'] = {
                'type': 'custom',
                'preview': f'Cron: {cron_expr}'
            }

            tests = profile_data.get('tests')
            if isinstance(tests, list) and tests:
                numeric_offsets = [
                    int(t.get('startOffsetMinutes', 0))
                    for t in tests
                    if isinstance(t, dict)
                ]
                if numeric_offsets:
                    first_offset = min(numeric_offsets)
                    delta = target_offset_minutes - first_offset

                    for test in tests:
                        if not isinstance(test, dict):
                            continue
                        old_offset = int(test.get('startOffsetMinutes', 0))
                        shifted = old_offset + delta
                        test['startOffsetMinutes'] = max(0, min(1439, shifted))

            save_response = await client.post(f"{NUI_API_BASE}/schedule/profiles", json=profile_data)
            save_response.raise_for_status()
            return str(save_response.json())
        except httpx.HTTPStatusError as e:
            return f"Error connecting to NUI API: {e}"
        except httpx.RequestError as e:
            return f"Request to NUI API failed: {e}"


@mcp.tool()
async def set_profile_test_time(profile_name: str, test_title: str, hour: int, minute: int = 0) -> str:
    """Set one test block start time in a profile while keeping existing cron_rule unchanged."""
    if hour < 0 or hour > 23:
        return "Invalid hour. Expected 0-23."
    if minute < 0 or minute > 59:
        return "Invalid minute. Expected 0-59."

    target_offset_minutes = (hour * 60) + minute

    async with httpx.AsyncClient() as client:
        try:
            get_response = await client.get(f"{NUI_API_BASE}/schedule/profiles/{profile_name}")
            get_response.raise_for_status()
            get_data = get_response.json()
            if not get_data.get('success'):
                return str(get_data)

            profile_data = get_data.get('data') or {}
            profile_data['profile_name'] = profile_name

            tests = profile_data.get('tests')
            if not isinstance(tests, list):
                return f"Invalid profile format: tests is not a list for profile '{profile_name}'"

            updated = False
            for test in tests:
                if isinstance(test, dict) and str(test.get('title', '')).strip() == str(test_title).strip():
                    test['startOffsetMinutes'] = target_offset_minutes
                    updated = True

            if not updated:
                return f"Test '{test_title}' not found in profile '{profile_name}'"

            save_response = await client.post(f"{NUI_API_BASE}/schedule/profiles", json=profile_data)
            save_response.raise_for_status()
            return str(save_response.json())
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
