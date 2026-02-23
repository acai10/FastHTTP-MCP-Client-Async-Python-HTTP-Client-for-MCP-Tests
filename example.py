import asyncio
from http_client import MCPInteractiveHTTPClient


HTTP_URL = "http://localhost:8000/mcp"
SSE_URL = "http://localhost:8000/sse"


async def main_http():
    async with MCPInteractiveHTTPClient(HTTP_URL, transport="http") as client:
        await client.run()


async def main_sse():
    async with MCPInteractiveHTTPClient(SSE_URL, transport="sse") as client:
        await client.run()


if __name__ == "__main__":
    transport = input(
        "Choose transport type:\n1: 'http' (streamable-http)\n2: 'sse' (Server-Sent Events)\nEnter 1 or 2: "
    )
    if transport == "1":
        print("Running MCP Interactive HTTP Client with streamable-http transport...")
        asyncio.run(main_http())
    elif transport == "2":
        print("Running MCP Interactive HTTP Client with SSE transport...")
        asyncio.run(main_sse())
    else:
        print("Invalid choice, defaulting to streamable-http transport...")
        asyncio.run(main_http())
