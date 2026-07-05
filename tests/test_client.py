"""Tests for client.py — request correctness, resilience, and per-call cost (Wave 3)."""

from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest
import respx

from mcp_langfuse.client import (
    LangfuseAPIError,
    LangfuseArgumentError,
    LangfuseClient,
    LangfuseResponseDecodeError,
    LangfuseTransportError,
)
from mcp_langfuse.openapi import load_api_spec
from tests.conftest import make_settings as _make_settings


def make_settings(**overrides):
    """Create a client-flavoured Settings with the langfuse.example base URL."""
    return _make_settings(
        **{
            "LANGFUSE_BASE_URL": "https://langfuse.example",
            "LANGFUSE_TIMEOUT_SECONDS": 5.0,
            "LANGFUSE_VERIFY_SSL": True,
            **overrides,
        }
    )


# ---------------------------------------------------------------------------
# Existing tests (must keep passing)
# ---------------------------------------------------------------------------


@respx.mock
async def test_call_operation_maps_query_params() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    route = respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(200, json={"data": [], "meta": {"page": 2}})
    )

    async with LangfuseClient(make_settings()) as client:
        response = await client.call_operation(operation, {"page": 2, "limit": 10})

    assert route.called
    request = route.calls.last.request
    assert request.url.params["page"] == "2"
    assert request.url.params["limit"] == "10"
    assert response.data["meta"]["page"] == 2


@respx.mock
async def test_call_operation_renders_path_and_json_body_for_delete() -> None:
    operation = load_api_spec().by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]
    route = respx.delete(
        "https://langfuse.example/api/public/annotation-queues/queue-1/assignments"
    ).mock(return_value=httpx.Response(200, json={"success": True}))

    async with LangfuseClient(make_settings()) as client:
        response = await client.call_operation(
            operation,
            {"queueId": "queue-1", "body": {"userId": "user-1"}},
        )

    assert response.status_code == 200
    request = route.calls.last.request
    assert json.loads(request.content) == {"userId": "user-1"}


@respx.mock
async def test_call_operation_raises_on_api_error() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_get"]
    respx.get("https://langfuse.example/api/public/projects").mock(
        return_value=httpx.Response(403, json={"message": "forbidden"})
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseAPIError) as exc_info:
            await client.call_operation(operation, {})

    assert exc_info.value.status_code == 403
    assert exc_info.value.details == {"message": "forbidden"}


@respx.mock
async def test_call_operation_wraps_transport_errors() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_get"]
    request = httpx.Request("GET", "https://langfuse.example/api/public/projects")
    respx.get("https://langfuse.example/api/public/projects").mock(
        side_effect=httpx.ConnectError("connection refused", request=request)
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseTransportError) as exc_info:
            await client.call_operation(operation, {})

    assert exc_info.value.details == {
        "exception_type": "ConnectError",
        "request_method": "GET",
        "request_url": "https://langfuse.example/api/public/projects",
    }


async def test_call_operation_rejects_unknown_arguments() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_get"]

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError):
            await client.call_operation(operation, {"unexpected": "value"})


async def test_call_operation_rejects_wrong_query_argument_type() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError, match="limit"):
            await client.call_operation(operation, {"limit": {"bad": "shape"}})


async def test_call_operation_rejects_null_for_required_path_argument() -> None:
    operation = load_api_spec().by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError, match="queueId"):
            await client.call_operation(
                operation,
                {"queueId": None, "body": {"userId": "user-1"}},
            )


async def test_call_operation_rejects_null_for_required_body() -> None:
    operation = load_api_spec().by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError, match="body"):
            await client.call_operation(operation, {"queueId": "queue-1", "body": None})


async def test_call_operation_rejects_non_json_serializable_body() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_create"]

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError, match="JSON serializable"):
            await client.call_operation(
                operation,
                {"body": {"name": "demo", "retention": 0, "metadata": {"bad": {1, 2, 3}}}},
            )


@respx.mock
async def test_call_operation_wraps_malformed_json_responses() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_get"]
    respx.get("https://langfuse.example/api/public/projects").mock(
        return_value=httpx.Response(
            200,
            text="not-json",
            headers={"content-type": "application/json"},
        )
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseResponseDecodeError) as exc_info:
            await client.call_operation(operation, {})

    assert exc_info.value.status_code == 200
    assert exc_info.value.details["body_preview"] == "not-json"


# ---------------------------------------------------------------------------
# Wave 3: Q-3 decode-branch coverage
# ---------------------------------------------------------------------------


@respx.mock
async def test_204_returns_none() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    respx.get("https://langfuse.example/api/public/traces").mock(return_value=httpx.Response(204))

    async with LangfuseClient(make_settings()) as client:
        response = await client.call_operation(operation, {})

    assert response.data is None
    assert response.status_code == 204


@respx.mock
async def test_text_response_returned_as_str() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(200, text="hello world", headers={"content-type": "text/plain"})
    )

    async with LangfuseClient(make_settings()) as client:
        response = await client.call_operation(operation, {})

    assert isinstance(response.data, str)
    assert response.data == "hello world"


@respx.mock
async def test_binary_response_base64_wrapped() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    raw_bytes = b"\x00\x01\x02\x03"
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(
            200,
            content=raw_bytes,
            headers={"content-type": "application/octet-stream"},
        )
    )

    async with LangfuseClient(make_settings()) as client:
        response = await client.call_operation(operation, {})

    assert isinstance(response.data, dict)
    assert response.data["content_base64"] == base64.b64encode(raw_bytes).decode("ascii")
    assert "application/octet-stream" in response.data["content_type"]


# ---------------------------------------------------------------------------
# Wave 3: L-1 empty path parameters
# ---------------------------------------------------------------------------


@respx.mock
async def test_empty_path_param_rejected() -> None:
    operation = load_api_spec().by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]
    # Mock so we don't hit real network if validation doesn't reject early (pre-implementation)
    respx.delete(url__startswith="https://langfuse.example").mock(
        return_value=httpx.Response(200, json={})
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError, match="empty"):
            await client.call_operation(operation, {"queueId": "", "body": {"userId": "user-1"}})


@respx.mock
async def test_whitespace_path_param_rejected() -> None:
    operation = load_api_spec().by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]
    # Mock so we don't hit real network if validation doesn't reject early (pre-implementation)
    respx.delete(url__startswith="https://langfuse.example").mock(
        return_value=httpx.Response(200, json={})
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError, match="empty"):
            await client.call_operation(operation, {"queueId": "   ", "body": {"userId": "user-1"}})


# ---------------------------------------------------------------------------
# Wave 3: L-2 client lock and re-openability
# ---------------------------------------------------------------------------


async def test_get_client_is_locked_and_reopenable() -> None:
    c = LangfuseClient(make_settings())
    clients = await asyncio.gather(*[c._get_client() for _ in range(10)])
    # All calls must return the SAME underlying client object
    assert all(client is clients[0] for client in clients)

    await c.aclose()

    # After close, a fresh call should return a new open client
    fresh = await c._get_client()
    assert fresh is not None
    assert not fresh.is_closed
    await c.aclose()


# ---------------------------------------------------------------------------
# Wave 3: L-7 retry on 429
# ---------------------------------------------------------------------------


@respx.mock
async def test_retry_on_429_honors_retry_after() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    route = respx.get("https://langfuse.example/api/public/traces").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(200, json={"data": [], "meta": {"page": 1}}),
        ]
    )

    async with LangfuseClient(make_settings(LANGFUSE_RETRY_ATTEMPTS=2)) as client:
        response = await client.call_operation(operation, {})

    assert route.call_count == 2
    assert response.status_code == 200


@respx.mock
async def test_retry_exhaustion_raises_api_error() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    route = respx.get("https://langfuse.example/api/public/traces").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(429, headers={"retry-after": "0"}),
        ]
    )

    async with LangfuseClient(make_settings(LANGFUSE_RETRY_ATTEMPTS=2)) as client:
        with pytest.raises(LangfuseAPIError) as exc_info:
            await client.call_operation(operation, {})

    assert exc_info.value.status_code == 429
    assert route.call_count == 3  # initial + 2 retries


@respx.mock
async def test_no_retry_for_post() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_create"]
    route = respx.post("https://langfuse.example/api/public/projects").mock(
        return_value=httpx.Response(503, json={"message": "unavailable"})
    )

    async with LangfuseClient(make_settings(LANGFUSE_RETRY_ATTEMPTS=2)) as client:
        with pytest.raises(LangfuseAPIError):
            await client.call_operation(operation, {"body": {"name": "proj", "retention": 0}})

    assert route.call_count == 1  # non-GET: no retry


# ---------------------------------------------------------------------------
# Wave 3: L-6 redirect raises transport error
# ---------------------------------------------------------------------------


@respx.mock
async def test_redirect_raises_transport_error() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(
            307,
            headers={"location": "https://other.example/api/public/traces"},
        )
    )
    # Also mock the redirect target so respx doesn't complain if the client follows it
    respx.get("https://other.example/api/public/traces").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseTransportError) as exc_info:
            await client.call_operation(operation, {})

    error_msg = str(exc_info.value).lower()
    assert "redirect" in error_msg
    assert "other.example" in str(exc_info.value.details)


# ---------------------------------------------------------------------------
# Wave 3: L-3 malformed JSON on error path still raises LangfuseAPIError
# ---------------------------------------------------------------------------


@respx.mock
async def test_error_response_with_malformed_json_still_api_error() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(
            502,
            text="not-json",
            headers={"content-type": "application/json"},
        )
    )

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseAPIError) as exc_info:
            await client.call_operation(operation, {})

    assert exc_info.value.status_code == 502
    # details should contain a body_preview even when JSON parsing failed
    assert exc_info.value.details is not None
    assert "body_preview" in exc_info.value.details


# ---------------------------------------------------------------------------
# Wave 3: L-4 single serialization path
# ---------------------------------------------------------------------------


@respx.mock
async def test_body_sent_with_json_content_type() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_create"]
    route = respx.post("https://langfuse.example/api/public/projects").mock(
        return_value=httpx.Response(200, json={"id": "proj-1"})
    )

    async with LangfuseClient(make_settings()) as client:
        await client.call_operation(operation, {"body": {"name": "demo", "retention": 0}})

    request = route.calls.last.request
    assert request.headers["content-type"] == "application/json"
    body = json.loads(request.content)
    assert body["name"] == "demo"


# ---------------------------------------------------------------------------
# Wave 3: C-3 hookup — SecretStr unwrapped correctly in auth
# ---------------------------------------------------------------------------


@respx.mock
async def test_basic_auth_uses_secret_value() -> None:
    import base64 as _b64

    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(200, json={"data": [], "meta": {"page": 1}})
    )

    async with LangfuseClient(make_settings()) as client:
        await client.call_operation(operation, {})

    request = respx.calls.last.request
    auth_header = request.headers.get("authorization", "")
    assert auth_header.startswith("Basic ")
    decoded = _b64.b64decode(auth_header.removeprefix("Basic ")).decode()
    assert decoded == "pk-test:sk-test"


# ---------------------------------------------------------------------------
# Wave 3: L-4 caller arguments not mutated
# ---------------------------------------------------------------------------


@respx.mock
async def test_arguments_not_mutated_by_call() -> None:
    operation = load_api_spec().by_tool_name["langfuse_trace_list"]
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(200, json={"data": [], "meta": {"page": 1}})
    )

    original = {"page": 1, "limit": 5}
    snapshot = dict(original)

    async with LangfuseClient(make_settings()) as client:
        await client.call_operation(operation, original)

    assert original == snapshot
