from __future__ import annotations

from typing import Any

import pytest

from mcp_langfuse.client import LangfuseAPIError, LangfuseArgumentError, LangfuseResponse
from mcp_langfuse.config import Settings
from mcp_langfuse.openapi import load_api_spec
from mcp_langfuse.service import LangfuseToolService
from mcp_langfuse.tool_selection import build_tool_selection


class FakeClient:
    """Minimal async client double for service-layer tests."""

    def __init__(self, response: LangfuseResponse | Exception) -> None:
        """Store the response or exception to raise."""
        self.response = response

    async def call_operation(self, *_args, **_kwargs) -> LangfuseResponse:
        """Return the configured response or raise the configured exception."""
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_settings(**overrides: Any) -> Settings:
    """Create service settings with required auth placeholders."""
    values: dict[str, Any] = {
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_service_returns_success_payload() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="full",
            LANGFUSE_ENABLE_ADMIN_TOOLS=True,
        ),
    )
    service = LangfuseToolService(
        selection,
        FakeClient(
            LangfuseResponse(
                status_code=200,
                content_type="application/json",
                data={"ok": True},
            )
        ),
    )

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status_code"] == 200
    assert result.structuredContent["data"] == {"ok": True}


@pytest.mark.asyncio
async def test_service_returns_error_payload_for_unknown_tool() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="full",
            LANGFUSE_ENABLE_ADMIN_TOOLS=True,
        ),
    )
    service = LangfuseToolService(
        selection,
        FakeClient(LangfuseResponse(status_code=200, content_type="application/json", data={})),
    )

    result = await service.call_tool("langfuse_missing_tool", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "unknown_tool"


@pytest.mark.asyncio
async def test_service_wraps_client_errors() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="full",
            LANGFUSE_ENABLE_ADMIN_TOOLS=True,
        ),
    )
    operation = spec.by_tool_name["langfuse_projects_get"]
    service = LangfuseToolService(
        selection,
        FakeClient(
            LangfuseAPIError(
                message="boom",
                status_code=500,
                operation=operation,
                details={"detail": "broken"},
            )
        ),
    )

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["status_code"] == 500
    assert result.structuredContent["details"] == {"detail": "broken"}


@pytest.mark.asyncio
async def test_service_wraps_argument_errors() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="full",
            LANGFUSE_ENABLE_ADMIN_TOOLS=True,
        ),
    )
    service = LangfuseToolService(selection, FakeClient(LangfuseArgumentError("bad args")))

    result = await service.call_tool("langfuse_projects_get", {"bad": True})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "invalid_arguments"


@pytest.mark.asyncio
async def test_service_reports_disabled_tools() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(spec, make_settings())
    service = LangfuseToolService(
        selection,
        FakeClient(LangfuseResponse(status_code=200, content_type="application/json", data={})),
    )

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "tool_not_enabled"
