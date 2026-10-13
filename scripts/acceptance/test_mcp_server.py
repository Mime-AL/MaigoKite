"""Local official-SDK MCP fixture; no external connections or pytest cases."""
import asyncio
from mcp.server.fastmcp import FastMCP

server = FastMCP("runtime-closure")


@server.tool()
async def delayed_echo(text: str, delay: float = 0) -> str:
    await asyncio.sleep(delay)
    return text


if __name__ == "__main__":
    server.run(transport="stdio")
