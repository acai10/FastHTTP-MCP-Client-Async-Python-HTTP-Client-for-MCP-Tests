"""
HTTP client package for MCP interactive clients by acai10.

Exports:
- MCPInteractiveHTTPClient: interactive client using
  - streamable-http transport (mcp.run(transport="streamable-http"))
  - or SSE transport (mcp.run(transport="sse")), depending on the `transport` argument.

Defines:
- MCPInteractiveHTTPClient:
    Wrapper around mcp.client.session.ClientSession with an interactive CLI:
    - initialize MCP session
    - list tools and let the user choose one
    - show tool argument schema and prompt for values
    - call the tool and pretty-print the result
    - optional logging setup via `activate_logger` argument

Constructor:
    MCPInteractiveHTTPClient(
        url: str,
        transport: str = "http",       # "http" (streamable-http) or "sse"
        activate_logger: bool = True,  # configure logging on first use if True
    )

Example usage:
    from http_client import MCPInteractiveHTTPClient
    import asyncio

    HTTP_URL = "http://localhost:8000/mcp"
    SSE_URL = "http://localhost:8000/sse"

    async def main_http():
        async with MCPInteractiveHTTPClient(
            HTTP_URL,
            transport="http",
            activate_logger=True,
        ) as client:
            await client.run()

    async def main_sse():
        async with MCPInteractiveHTTPClient(
            SSE_URL,
            transport="sse",
            activate_logger=True,
        ) as client:
            await client.run()

    if __name__ == "__main__":
        asyncio.run(main_http())
"""

from .http_client import MCPInteractiveHTTPClient

__all__ = [
    "MCPInteractiveHTTPClient",
]
