"""Server bootstrap for the Langfuse MCP implementation."""

from __future__ import annotations

import asyncio

import mcp.server.stdio
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from . import __version__
from .client import LangfuseClient
from .config import Settings
from .openapi import load_api_spec
from .service import LangfuseToolService
from .tool_selection import build_tool_selection


def build_server(service: LangfuseToolService) -> Server:
    """Build the low-level MCP server around the Langfuse tool service."""
    server = Server("langfuse")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return service.list_tools()

    @server.call_tool()
    async def call_tool(
        name: str,
        arguments: dict[str, object] | None,
    ) -> types.CallToolResult:
        return await service.call_tool(name, arguments or {})

    return server


async def run_stdio() -> None:
    """Run the MCP server over stdio."""
    settings = Settings.from_env()
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)
    client = LangfuseClient(settings)
    service = LangfuseToolService(selection, client)
    server = build_server(service)

    async with client, mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="langfuse",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """Run the stdio server in a fresh asyncio event loop."""
    asyncio.run(run_stdio())
