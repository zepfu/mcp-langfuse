"""Async Langfuse API client used by the MCP server."""

from __future__ import annotations

import base64
import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import quote

import httpx

if TYPE_CHECKING:
    from .config import Settings
    from .openapi import OperationSpec

NO_CONTENT_STATUS_CODE = 204


class LangfuseClientError(RuntimeError):
    """Base client error."""


class LangfuseArgumentError(LangfuseClientError):
    """Raised when tool arguments do not match the OpenAPI operation."""


class LangfuseAPIError(LangfuseClientError):
    """Raised when Langfuse returns a non-success response."""

    def __init__(
        self,
        *,
        message: str,
        status_code: int,
        operation: OperationSpec,
        details: Any = None,
    ) -> None:
        """Initialize the API error wrapper."""
        super().__init__(message)
        self.status_code = status_code
        self.operation = operation
        self.details = details


@dataclass(frozen=True)
class LangfuseResponse:
    """Decoded Langfuse HTTP response metadata and payload."""

    status_code: int
    content_type: str | None
    data: Any


class LangfuseClient:
    """Thin async wrapper over Langfuse's HTTP API."""

    def __init__(self, settings: Settings) -> None:
        """Store immutable client settings."""
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Open the HTTP client when used as a context manager."""
        await self._get_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the HTTP client when leaving a context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the cached async client if one exists."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=httpx.BasicAuth(self._settings.public_key, self._settings.secret_key),
                base_url=self._settings.base_url.rstrip("/"),
                follow_redirects=True,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "mcp-langfuse/0.1.0",
                },
                timeout=self._settings.timeout_seconds,
                verify=self._settings.verify_ssl,
            )
        return self._client

    @staticmethod
    def _missing_argument_error(
        operation: OperationSpec,
        argument_name: str,
    ) -> LangfuseArgumentError:
        message = f"Missing required argument '{argument_name}' for {operation.tool_name}"
        return LangfuseArgumentError(message)

    @staticmethod
    def _unsupported_parameter_error(
        operation: OperationSpec,
        parameter_location: str,
    ) -> LangfuseArgumentError:
        message = f"Unsupported parameter location '{parameter_location}' for {operation.tool_name}"
        return LangfuseArgumentError(message)

    @staticmethod
    def _unknown_arguments_error(
        operation: OperationSpec,
        unknown_arguments: dict[str, Any],
    ) -> LangfuseArgumentError:
        unknown = ", ".join(sorted(unknown_arguments))
        message = f"Unknown arguments for {operation.tool_name}: {unknown}"
        return LangfuseArgumentError(message)

    @staticmethod
    def _build_request_path(operation: OperationSpec, path_values: dict[str, Any]) -> str:
        path = operation.path
        for name, value in path_values.items():
            path = path.replace(f"{{{name}}}", quote(str(value), safe=""))
        return path

    def _extract_request_body(self, operation: OperationSpec, payload: dict[str, Any]) -> Any:
        if operation.request_body is None:
            return None

        if "body" not in payload:
            if operation.request_body.required:
                raise self._missing_argument_error(operation, "body")
            return None

        return payload.pop("body")

    def _extract_request_parts(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any], Any]:
        payload = copy.deepcopy(arguments or {})
        path_values: dict[str, Any] = {}
        query_values: dict[str, Any] = {}

        for parameter in operation.parameters:
            if parameter.name not in payload:
                if parameter.required:
                    raise self._missing_argument_error(operation, parameter.name)
                continue

            value = payload.pop(parameter.name)
            if value is None:
                continue

            if parameter.location == "path":
                path_values[parameter.name] = value
                continue

            if parameter.location == "query":
                query_values[parameter.name] = value
                continue

            raise self._unsupported_parameter_error(operation, parameter.location)

        body = self._extract_request_body(operation, payload)
        if payload:
            raise self._unknown_arguments_error(operation, payload)

        return path_values, query_values, body

    async def call_operation(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> LangfuseResponse:
        """Call one normalized Langfuse operation with MCP-style arguments."""
        client = await self._get_client()
        path_values, query_values, body = self._extract_request_parts(operation, arguments)
        path = self._build_request_path(operation, path_values)

        response = await client.request(
            operation.method,
            path,
            json=body if operation.request_body is not None else None,
            params=query_values or None,
        )

        if response.is_error:
            raise LangfuseAPIError(
                message=f"{operation.tool_name} failed with HTTP {response.status_code}",
                status_code=response.status_code,
                operation=operation,
                details=self._decode_response(response),
            )

        return LangfuseResponse(
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            data=self._decode_response(response),
        )

    @staticmethod
    def _decode_response(response: httpx.Response) -> Any:
        """Decode a Langfuse response into JSON, text, or base64-wrapped bytes."""
        if response.status_code == NO_CONTENT_STATUS_CODE or not response.content:
            return None

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        if "text/" in content_type:
            return response.text

        return {
            "content_type": content_type or "application/octet-stream",
            "content_base64": base64.b64encode(response.content).decode("ascii"),
        }
