"""Server bootstrap for the Langfuse MCP implementation."""

from __future__ import annotations

import asyncio
import os
import sys

import mcp.server.stdio
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import ValidationError

from . import __version__, config
from .client import LangfuseClient
from .config import Settings
from .openapi import load_api_spec
from .service import LangfuseToolService
from .tool_selection import ToolSelection, ToolSelectionError, build_tool_selection

KEYBOARD_INTERRUPT_EXIT_CODE = 130


def build_server(service: LangfuseToolService) -> Server:
    """Build the low-level MCP server around the Langfuse tool service."""
    server = Server("langfuse")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return service.list_tools()

    @server.call_tool(validate_input=False)
    async def call_tool(
        name: str,
        arguments: dict[str, object] | None,
    ) -> types.CallToolResult:
        return await service.call_tool(name, arguments or {})

    return server


def _log_startup_diagnostics(settings: Settings, selection: ToolSelection) -> None:
    """Print a startup diagnostics summary and warnings to stderr.

    Args:
        settings: The resolved server settings.
        selection: The computed tool selection.

    """
    tool_count = len(selection.enabled_operations)
    profiles = ", ".join(settings.tool_profiles) or "(none)"
    summary = (
        f"mcp-langfuse: {tool_count} tools enabled; profiles=[{profiles}]; "
        f"gates write={settings.enable_write_tools} "
        f"destructive={settings.enable_destructive_tools} "
        f"admin={settings.enable_admin_tools} legacy={settings.enable_legacy_tools}"
    )
    _emit(summary)

    if not selection.enabled_operations:
        _emit("WARNING: 0 tools enabled; check LANGFUSE_TOOL_PROFILES and safety gates")

    for name in sorted(os.environ):
        if name.startswith("LANGFUSE_") and name not in config.KNOWN_ENV_VARS:
            _emit(f"WARNING: unknown environment variable {name} is set but not recognized")

    for tool_name, reason in sorted(selection.gate_overrides.items()):
        _emit(f"WARNING: tool {tool_name} was force-enabled, bypassing gate: {reason}")


def _emit(message: str) -> None:
    """Write a single diagnostic line to stderr.

    Args:
        message: The diagnostic message to print.

    """
    print(message, file=sys.stderr)  # noqa: T201


async def run_stdio() -> None:
    """Run the MCP server over stdio."""
    settings = Settings()  # type: ignore[call-arg]
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)
    _log_startup_diagnostics(settings, selection)
    client = LangfuseClient(settings)
    service = LangfuseToolService(
        selection,
        client,
        max_response_bytes=settings.max_response_bytes,
    )
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
    try:
        asyncio.run(run_stdio())
    except (ToolSelectionError, ValidationError) as exc:
        message = f"Configuration error: {exc}"
        raise SystemExit(message) from None
    except KeyboardInterrupt:
        raise SystemExit(KEYBOARD_INTERRUPT_EXIT_CODE) from None
