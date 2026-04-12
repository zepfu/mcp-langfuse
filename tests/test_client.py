from __future__ import annotations

import json

import httpx
import pytest
import respx

from mcp_langfuse.client import LangfuseAPIError, LangfuseArgumentError, LangfuseClient
from mcp_langfuse.config import Settings
from mcp_langfuse.openapi import load_api_spec


def make_settings() -> Settings:
    return Settings(
        LANGFUSE_BASE_URL="https://langfuse.example",
        LANGFUSE_PUBLIC_KEY="pk-test",
        LANGFUSE_SECRET_KEY="sk-test",
        LANGFUSE_TIMEOUT_SECONDS=5.0,
        LANGFUSE_VERIFY_SSL=True,
    )


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_call_operation_rejects_unknown_arguments() -> None:
    operation = load_api_spec().by_tool_name["langfuse_projects_get"]

    async with LangfuseClient(make_settings()) as client:
        with pytest.raises(LangfuseArgumentError):
            await client.call_operation(operation, {"unexpected": "value"})
