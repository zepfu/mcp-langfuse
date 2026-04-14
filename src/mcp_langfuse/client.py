"""Async Langfuse API client used by the MCP server."""

from __future__ import annotations

import base64
import copy
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import quote

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.exceptions import best_match

from . import __version__

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .config import Settings
    from .openapi import OperationSpec

NO_CONTENT_STATUS_CODE = 204
PATH_PARAMETER_PATTERN = re.compile(r"{([^{}]+)}")


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


class LangfuseTransportError(LangfuseClientError):
    """Raised when the Langfuse API cannot be reached successfully."""

    def __init__(
        self,
        *,
        message: str,
        operation: OperationSpec,
        details: Any = None,
    ) -> None:
        """Initialize the transport error wrapper."""
        super().__init__(message)
        self.operation = operation
        self.details = details


class LangfuseResponseDecodeError(LangfuseClientError):
    """Raised when Langfuse responds with malformed data."""

    def __init__(
        self,
        *,
        message: str,
        operation: OperationSpec,
        status_code: int,
        details: Any = None,
    ) -> None:
        """Initialize the response decode error wrapper."""
        super().__init__(message)
        self.operation = operation
        self.status_code = status_code
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
                base_url=str(self._settings.base_url).rstrip("/"),
                follow_redirects=True,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"mcp-langfuse/{__version__}",
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
    def _null_argument_error(
        operation: OperationSpec,
        argument_name: str,
    ) -> LangfuseArgumentError:
        message = f"Argument '{argument_name}' cannot be null for {operation.tool_name}"
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
    def _schema_validation_error(
        operation: OperationSpec,
        validation_error: JSONSchemaValidationError,
    ) -> LangfuseArgumentError:
        location = LangfuseClient._format_validation_path(validation_error.absolute_path)
        message = (
            f"Invalid arguments for {operation.tool_name} at {location}: {validation_error.message}"
        )
        return LangfuseArgumentError(message)

    @staticmethod
    def _json_serialization_error(
        operation: OperationSpec,
        error: TypeError | ValueError,
    ) -> LangfuseArgumentError:
        message = f"Request body for {operation.tool_name} is not JSON serializable: {error}"
        return LangfuseArgumentError(message)

    @staticmethod
    def _response_decode_error(
        operation: OperationSpec,
        response: httpx.Response,
        error: ValueError,
    ) -> LangfuseResponseDecodeError:
        body_preview = response.content[:200].decode("utf-8", errors="replace")
        message = f"{operation.tool_name} returned malformed JSON: {error}"
        return LangfuseResponseDecodeError(
            message=message,
            operation=operation,
            status_code=response.status_code,
            details={
                "exception_type": type(error).__name__,
                "content_type": response.headers.get("content-type"),
                "status_code": response.status_code,
                "body_preview": body_preview,
            },
        )

    @staticmethod
    def _format_validation_path(path: Iterable[object]) -> str:
        parts: list[str] = []
        for part in path:
            if isinstance(part, int):
                parts.append(f"[{part}]")
                continue
            prefix = "." if parts and not parts[-1].endswith("]") else ""
            parts.append(f"{prefix}{part}")
        return "".join(parts) or "<root>"

    @staticmethod
    def _build_request_path(operation: OperationSpec, path_values: dict[str, Any]) -> str:
        path = operation.path
        for name, value in path_values.items():
            path = path.replace(f"{{{name}}}", quote(str(value), safe=""))
        unresolved = sorted(set(PATH_PARAMETER_PATTERN.findall(path)))
        if unresolved:
            names = ", ".join(unresolved)
            message = f"Missing required path arguments for {operation.tool_name}: {names}"
            raise LangfuseArgumentError(message)
        return path

    def _extract_request_body(self, operation: OperationSpec, payload: dict[str, Any]) -> Any:
        if operation.request_body is None:
            return None

        if "body" not in payload:
            if operation.request_body.required:
                raise self._missing_argument_error(operation, "body")
            return None

        body = payload.pop("body")
        if body is None and operation.request_body.required:
            raise self._null_argument_error(operation, "body")
        return body

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
                if parameter.required or parameter.location == "path":
                    raise self._null_argument_error(operation, parameter.name)
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

    def _validate_arguments(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = copy.deepcopy(arguments or {})
        validator = Draft202012Validator(operation.input_schema)
        validation_error = best_match(validator.iter_errors(payload))
        if validation_error is not None:
            raise self._schema_validation_error(operation, validation_error)
        return payload

    def _ensure_json_serializable(self, operation: OperationSpec, body: Any) -> None:
        if body is None:
            return
        try:
            json.dumps(body)
        except (TypeError, ValueError) as exc:
            raise self._json_serialization_error(operation, exc) from exc

    async def call_operation(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> LangfuseResponse:
        """Call one normalized Langfuse operation with MCP-style arguments."""
        client = await self._get_client()
        validated_arguments = self._validate_arguments(operation, arguments)
        path_values, query_values, body = self._extract_request_parts(
            operation,
            validated_arguments,
        )
        path = self._build_request_path(operation, path_values)
        self._ensure_json_serializable(operation, body)

        try:
            response = await client.request(
                operation.method,
                path,
                json=body if operation.request_body is not None else None,
                params=query_values or None,
            )
        except httpx.RequestError as exc:
            raise LangfuseTransportError(
                message=f"{operation.tool_name} transport failure: {exc}",
                operation=operation,
                details={
                    "exception_type": type(exc).__name__,
                    "request_method": exc.request.method,
                    "request_url": str(exc.request.url),
                },
            ) from exc

        if response.is_error:
            raise LangfuseAPIError(
                message=f"{operation.tool_name} failed with HTTP {response.status_code}",
                status_code=response.status_code,
                operation=operation,
                details=self._decode_response(operation, response),
            )

        return LangfuseResponse(
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            data=self._decode_response(operation, response),
        )

    @staticmethod
    def _decode_response(operation: OperationSpec, response: httpx.Response) -> Any:
        """Decode a Langfuse response into JSON, text, or base64-wrapped bytes."""
        if response.status_code == NO_CONTENT_STATUS_CODE or not response.content:
            return None

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError as exc:
                raise LangfuseClient._response_decode_error(operation, response, exc) from exc

        if "text/" in content_type:
            return response.text

        return {
            "content_type": content_type or "application/octet-stream",
            "content_base64": base64.b64encode(response.content).decode("ascii"),
        }
