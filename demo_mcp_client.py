import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import os
import json

async def main():
    server_params = StdioServerParameters(
        command="/root/.local/bin/uvx",
        args=["--python", "3.12", "--from", "mcp[cli]", "--with", "fastmcp", "--with", "httpx", "mcp", "run", "/home/NUI/mcp_server.py"],
        env=dict(os.environ) # pass current environment
    )

    print("Connecting to NUI MCP Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\nExecuting 'get_system_health' tool...")
            result = await session.call_tool("get_system_health", arguments={})
            
            try:
                # The result is returned as a stringified JSON representation, parse it.
                # In Python mcp SDK, result.content is a list of blocks.
                text_content = result.content[0].text
                
                # We do a quick format to make it readable
                print("\n=== System Health ===")
                data = json.loads(text_content.replace("'", '"').replace("False", "false").replace("True", "true"))
                print(json.dumps(data, indent=2))
            except Exception as e:
                print("Raw output:")
                print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
