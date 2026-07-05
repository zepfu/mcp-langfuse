"""MCP-facing service layer that exposes Langfuse operations as tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Protocol

from mcp import types

from .client import (
    LangfuseAPIError,
    LangfuseArgumentError,
    LangfuseClientError,
    LangfuseResponse,
    LangfuseResponseDecodeError,
    LangfuseTransportError,
)

if TYPE_CHECKING:
    from .openapi import OperationSpec
    from .tool_selection import ToolSelection

DEFAULT_MAX_RESPONSE_BYTES = 200_000


class SupportsCallOperation(Protocol):
    """Protocol for clients that can execute normalized Langfuse operations."""

    async def call_operation(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> LangfuseResponse:
        """Execute a normalized Langfuse operation."""


class _ToolResolutionError(Exception):
    """Internal signal carrying a structured tool-resolution error result."""

    def __init__(self, result: types.CallToolResult) -> None:
        """Store the structured error result for the caller to return."""
        super().__init__("tool resolution failed")
        self.result = result


class LangfuseToolService:
    """Bridge between the Langfuse client and MCP tool contracts."""

    def __init__(
        self,
        selection: ToolSelection,
        client: SupportsCallOperation,
        *,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        """Store the filtered tool selection and client used to execute MCP tool calls."""
        self._selection = selection
        self._client = client
        self._max_response_bytes = max_response_bytes

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

    def _resolve_operation(self, name: str) -> OperationSpec:
        """Resolve a tool name into an enabled operation.

        Args:
            name: The requested MCP tool name.

        Returns:
            The enabled :class:`OperationSpec`.

        Raises:
            _ToolResolutionError: If the tool is disabled or unknown.

        """
        operation = self._selection.enabled_by_name.get(name)
        if operation is not None:
            return operation

        if name in self._selection.disabled_reasons:
            reason = self._selection.disabled_reasons[name]
            raise _ToolResolutionError(
                self._error_result(
                    {
                        "error": "tool_not_enabled",
                        "message": f"Tool is not enabled: {name}",
                        "reason": reason,
                        "tool_name": name,
                    }
                )
            )

        raise _ToolResolutionError(
            self._error_result(
                {
                    "error": "unknown_tool",
                    "message": f"Unknown tool: {name}",
                    "tool_name": name,
                }
            )
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None,
    ) -> types.CallToolResult:
        """Execute one Langfuse-backed MCP tool call."""
        try:
            operation = self._resolve_operation(name)
        except _ToolResolutionError as exc:
            return exc.result

        try:
            response = await self._client.call_operation(operation, arguments)
        except LangfuseClientError as exc:
            return self._error_result(self._client_error_payload(name, exc))

        payload = self._success_payload(name, response)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=self._json_text(payload))],
            structuredContent=payload,
        )

    @staticmethod
    def _client_error_payload(name: str, exc: LangfuseClientError) -> dict[str, Any]:
        """Map a Langfuse client exception to a structured error payload.

        Args:
            name: The tool name being invoked.
            exc: The raised :class:`LangfuseClientError` (or subclass).

        Returns:
            A structured error payload describing the failure.

        """
        if isinstance(exc, LangfuseArgumentError):
            return {"error": "invalid_arguments", "message": str(exc), "tool_name": name}
        if isinstance(exc, LangfuseTransportError):
            return {
                "error": "langfuse_transport_error",
                "message": str(exc),
                "tool_name": name,
                "details": exc.details,
            }
        if isinstance(exc, LangfuseResponseDecodeError):
            return {
                "error": "langfuse_response_decode_error",
                "message": str(exc),
                "status_code": exc.status_code,
                "tool_name": name,
                "details": exc.details,
            }
        if isinstance(exc, LangfuseAPIError):
            return {
                "error": "langfuse_api_error",
                "message": str(exc),
                "status_code": exc.status_code,
                "tool_name": name,
                "details": exc.details,
            }
        return {"error": "langfuse_client_error", "message": str(exc), "tool_name": name}

    def _success_payload(self, tool_name: str, response: LangfuseResponse) -> dict[str, Any]:
        serialized = json.dumps(
            response.data,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        encoded_length = len(serialized.encode("utf-8"))
        data: Any = response.data
        if encoded_length > self._max_response_bytes:
            data = {
                "truncated": True,
                "data_bytes": encoded_length,
                "preview": serialized[: self._max_response_bytes],
            }

        return {
            "ok": True,
            "tool_name": tool_name,
            "status_code": response.status_code,
            "content_type": response.content_type,
            "data": data,
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
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
