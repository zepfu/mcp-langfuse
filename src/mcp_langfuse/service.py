"""MCP-facing service layer that exposes Langfuse operations as tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Protocol

from mcp import types

from .client import (
    LangfuseAPIError,
    LangfuseArgumentError,
    LangfuseResponse,
    LangfuseResponseDecodeError,
    LangfuseTransportError,
)

if TYPE_CHECKING:
    from .openapi import OperationSpec
    from .tool_selection import ToolSelection


class SupportsCallOperation(Protocol):
    """Protocol for clients that can execute normalized Langfuse operations."""

    async def call_operation(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> LangfuseResponse:
        """Execute a normalized Langfuse operation."""


class LangfuseToolService:
    """Bridge between the Langfuse client and MCP tool contracts."""

    def __init__(self, selection: ToolSelection, client: SupportsCallOperation) -> None:
        """Store the filtered tool selection and client used to execute MCP tool calls."""
        self._selection = selection
        self._client = client

    def list_tools(self) -> list[types.Tool]:
        """Return every Langfuse-backed MCP tool exposed by this service."""
        return [
            types.Tool(
                name=operation.tool_name,
                description=operation.tool_description,
                inputSchema=operation.input_schema,
            )
            for operation in self._selection.enabled_operations
        ]

    def _resolve_operation(self, name: str) -> OperationSpec | types.CallToolResult:
        """Resolve a tool name into an enabled operation or an error result."""
        operation = self._selection.enabled_by_name.get(name)
        if operation is not None:
            return operation

        if name in self._selection.disabled_reasons:
            reason = self._selection.disabled_reasons[name]
            return self._error_result(
                {
                    "error": "tool_not_enabled",
                    "message": f"Tool is not enabled: {name}",
                    "reason": reason,
                    "tool_name": name,
                }
            )

        operation = self._selection.all_by_name.get(name)
        if operation is not None:
            return operation

        return self._error_result(
            {
                "error": "unknown_tool",
                "message": f"Unknown tool: {name}",
                "tool_name": name,
            }
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None,
    ) -> types.CallToolResult:
        """Execute one Langfuse-backed MCP tool call."""
        operation = self._resolve_operation(name)
        if isinstance(operation, types.CallToolResult):
            return operation

        try:
            response = await self._client.call_operation(operation, arguments)
        except LangfuseArgumentError as exc:
            return self._error_result(
                {
                    "error": "invalid_arguments",
                    "message": str(exc),
                    "tool_name": name,
                    "arguments": arguments or {},
                }
            )
        except LangfuseTransportError as exc:
            return self._error_result(
                {
                    "error": "langfuse_transport_error",
                    "message": str(exc),
                    "tool_name": name,
                    "details": exc.details,
                }
            )
        except LangfuseResponseDecodeError as exc:
            return self._error_result(
                {
                    "error": "langfuse_response_decode_error",
                    "message": str(exc),
                    "status_code": exc.status_code,
                    "tool_name": name,
                    "details": exc.details,
                }
            )
        except LangfuseAPIError as exc:
            return self._error_result(
                {
                    "error": "langfuse_api_error",
                    "message": str(exc),
                    "status_code": exc.status_code,
                    "tool_name": name,
                    "details": exc.details,
                }
            )

        payload = self._success_payload(name, response)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=self._json_text(payload))],
            structuredContent=payload,
        )

    @staticmethod
    def _success_payload(tool_name: str, response: LangfuseResponse) -> dict[str, Any]:
        return {
            "ok": True,
            "tool_name": tool_name,
            "status_code": response.status_code,
            "content_type": response.content_type,
            "data": response.data,
        }

    @staticmethod
    def _error_result(payload: dict[str, Any]) -> types.CallToolResult:
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=LangfuseToolService._json_text(payload))],
            structuredContent=payload,
        )

    @staticmethod
    def _json_text(payload: dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True, default=str)
