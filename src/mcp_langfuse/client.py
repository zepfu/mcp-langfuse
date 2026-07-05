"""Async Langfuse API client used by the MCP server."""

from __future__ import annotations

import asyncio
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
RETRYABLE_STATUS_CODES = frozenset({429, 503})
RETRY_MAX_DELAY_SECONDS = 10.0
RETRY_BASE_DELAY_SECONDS = 0.5
PATH_PARAMETER_PATTERN = re.compile(r"{([^{}]+)}")

_VALIDATOR_CACHE: dict[str, Draft202012Validator] = {}


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
        self._client_lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        """Open the HTTP client when used as a context manager."""
        await self._get_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the HTTP client when leaving a context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the cached async client if one exists."""
        async with self._client_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    auth=httpx.BasicAuth(
                        self._settings.public_key,
                        self._settings.secret_key.get_secret_value(),
                    ),
                    base_url=self._settings.base_url,
                    follow_redirects=False,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": f"mcp-langfuse/{__version__}",
                    },
                    timeout=self._settings.timeout_seconds,
                    verify=self._settings.verify_ssl,
                )
            return self._client

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
                message = f"Missing required argument 'body' for {operation.tool_name}"
                raise LangfuseArgumentError(message)
            return None

        body = payload.pop("body")
        if body is None and operation.request_body.required:
            message = f"Argument 'body' cannot be null for {operation.tool_name}"
            raise LangfuseArgumentError(message)
        return body

    def _extract_request_parts(
        self,
        operation: OperationSpec,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], Any]:
        path_values: dict[str, Any] = {}
        query_values: dict[str, Any] = {}

        for parameter in operation.parameters:
            if parameter.name not in payload:
                if parameter.required:
                    message = (
                        f"Missing required argument '{parameter.name}' for {operation.tool_name}"
                    )
                    raise LangfuseArgumentError(message)
                continue

            value = payload.pop(parameter.name)
            if value is None:
                if parameter.required or parameter.location == "path":
                    message = (
                        f"Argument '{parameter.name}' cannot be null for {operation.tool_name}"
                    )
                    raise LangfuseArgumentError(message)
                continue

            if parameter.location == "path":
                if not str(value).strip():
                    message = (
                        f"Argument '{parameter.name}' cannot be empty for {operation.tool_name}"
                    )
                    raise LangfuseArgumentError(message)
                path_values[parameter.name] = value
                continue

            if parameter.location == "query":
                query_values[parameter.name] = value
                continue

            message = (
                f"Unsupported parameter location '{parameter.location}' for {operation.tool_name}"
            )
            raise LangfuseArgumentError(message)

        body = self._extract_request_body(operation, payload)
        if payload:
            unknown = ", ".join(sorted(payload))
            message = f"Unknown arguments for {operation.tool_name}: {unknown}"
            raise LangfuseArgumentError(message)

        return path_values, query_values, body

    def _validate_arguments(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = copy.deepcopy(arguments or {})
        validator = _VALIDATOR_CACHE.get(operation.tool_name)
        if validator is None:
            validator = Draft202012Validator(operation.input_schema)
            _VALIDATOR_CACHE[operation.tool_name] = validator
        validation_error = best_match(validator.iter_errors(payload))
        if validation_error is not None:
            raise self._schema_validation_error(operation, validation_error)
        return payload

    def _schema_validation_error(
        self,
        operation: OperationSpec,
        validation_error: JSONSchemaValidationError,
    ) -> LangfuseArgumentError:
        location = self._format_validation_path(validation_error.absolute_path)
        message = (
            f"Invalid arguments for {operation.tool_name} at {location}: {validation_error.message}"
        )
        return LangfuseArgumentError(message)

    @staticmethod
    def _serialize_body(operation: OperationSpec, body: Any) -> bytes:
        try:
            return json.dumps(body).encode("utf-8")
        except (TypeError, ValueError) as exc:
            message = f"Request body for {operation.tool_name} is not JSON serializable: {exc}"
            raise LangfuseArgumentError(message) from exc

    @staticmethod
    def _retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after is not None:
            try:
                parsed = int(retry_after)
            except ValueError:
                parsed = None
            if parsed is not None and parsed >= 0:
                return float(min(parsed, RETRY_MAX_DELAY_SECONDS))
        backoff = RETRY_BASE_DELAY_SECONDS * (2**attempt)
        return min(backoff, RETRY_MAX_DELAY_SECONDS)

    async def _send_request(
        self,
        operation: OperationSpec,
        path: str,
        query_values: dict[str, Any],
        serialized_body: bytes | None,
    ) -> httpx.Response:
        client = await self._get_client()
        headers = {"Content-Type": "application/json"} if serialized_body is not None else None
        try:
            response = await client.request(
                operation.method,
                path,
                content=serialized_body,
                params=query_values or None,
                headers=headers,
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

        if response.is_redirect:
            location = response.headers.get("location")
            raise LangfuseTransportError(
                message=(
                    f"{operation.tool_name} received an unexpected redirect; "
                    "check LANGFUSE_BASE_URL for a misconfiguration"
                ),
                operation=operation,
                details={"status_code": response.status_code, "location": location},
            )

        return response

    async def call_operation(
        self,
        operation: OperationSpec,
        arguments: dict[str, Any] | None,
    ) -> LangfuseResponse:
        """Call one normalized Langfuse operation with MCP-style arguments."""
        validated_arguments = self._validate_arguments(operation, arguments)
        path_values, query_values, body = self._extract_request_parts(
            operation,
            validated_arguments,
        )
        path = self._build_request_path(operation, path_values)
        serialized_body = (
            self._serialize_body(operation, body) if operation.request_body is not None else None
        )

        response = await self._send_request(operation, path, query_values, serialized_body)
        for attempt in range(self._settings.retry_attempts):
            if not self._is_retryable(operation, response):
                break
            await asyncio.sleep(self._retry_delay_seconds(response, attempt))
            response = await self._send_request(operation, path, query_values, serialized_body)

        if response.is_error:
            raise LangfuseAPIError(
                message=f"{operation.tool_name} failed with HTTP {response.status_code}",
                status_code=response.status_code,
                operation=operation,
                details=self._decode_error_details(operation, response),
            )

        return LangfuseResponse(
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            data=self._decode_response(operation, response),
        )

    @staticmethod
    def _is_retryable(operation: OperationSpec, response: httpx.Response) -> bool:
        return operation.method == "GET" and response.status_code in RETRYABLE_STATUS_CODES

    @staticmethod
    def _decode_error_details(operation: OperationSpec, response: httpx.Response) -> Any:
        """Best-effort decode of an error response body for diagnostics.

        Args:
            operation: The operation whose response is being decoded.
            response: The HTTP error response.

        Returns:
            The decoded body, or the decode-error details dict when decoding fails.

        """
        try:
            return LangfuseClient._decode_response(operation, response)
        except LangfuseResponseDecodeError as exc:
            return exc.details

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
                body_preview = response.content[:200].decode("utf-8", errors="replace")
                message = f"{operation.tool_name} returned malformed JSON: {exc}"
                raise LangfuseResponseDecodeError(
                    message=message,
                    operation=operation,
                    status_code=response.status_code,
                    details={
                        "exception_type": type(exc).__name__,
                        "content_type": response.headers.get("content-type"),
                        "status_code": response.status_code,
                        "body_preview": body_preview,
                    },
                ) from exc

        if "text/" in content_type:
            return response.text

        return {
            "content_type": content_type or "application/octet-stream",
            "content_base64": base64.b64encode(response.content).decode("ascii"),
        }
