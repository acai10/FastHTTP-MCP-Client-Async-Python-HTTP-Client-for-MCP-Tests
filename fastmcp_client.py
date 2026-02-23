"""
FastMCP HTTP Client Example

from fastmcp import Client, FastMCP

MCP-Server must be running locally on port 8000 before executing this client script.
Using:
main.py:
    mcp.run(transport="streamable-http")
json:
    "url": "http://localhost:8000/mcp",
    "type": "http"

# HTTP server
client = Client("http://localhost:8000/mcp")

async def main():
    async with client:
        # Basic server interaction
        await client.ping()

        # List available operations
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()

        # Execute operations
        print(tools)
        print(resources)
        print(prompts)

asyncio.run(main())
"""
