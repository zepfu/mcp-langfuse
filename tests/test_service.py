"""Tests for service.py — execution-path integrity and response shaping (Wave 5)."""

from __future__ import annotations

from mcp_langfuse.client import (
    LangfuseAPIError,
    LangfuseArgumentError,
    LangfuseClientError,
    LangfuseResponse,
    LangfuseResponseDecodeError,
    LangfuseTransportError,
)
from mcp_langfuse.openapi import load_api_spec
from mcp_langfuse.service import LangfuseToolService
from mcp_langfuse.tool_selection import build_tool_selection
from tests.conftest import make_settings


class FakeClient:
    """Minimal async client double for service-layer tests."""

    def __init__(self, response: LangfuseResponse | Exception) -> None:
        """Store the response or exception to raise."""
        self.response = response
        self.calls: int = 0

    async def call_operation(self, *_args, **_kwargs) -> LangfuseResponse:
        """Return the configured response or raise the configured exception."""
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


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


async def test_service_wraps_transport_errors() -> None:
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
            LangfuseTransportError(
                message="network down",
                operation=operation,
                details={"exception_type": "ConnectError"},
            )
        ),
    )

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "langfuse_transport_error"
    assert result.structuredContent["details"] == {"exception_type": "ConnectError"}


async def test_service_wraps_response_decode_errors() -> None:
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
            LangfuseResponseDecodeError(
                message="malformed json",
                operation=operation,
                status_code=200,
                details={"body_preview": "not-json"},
            )
        ),
    )

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "langfuse_response_decode_error"
    assert result.structuredContent["status_code"] == 200
    assert result.structuredContent["details"] == {"body_preview": "not-json"}


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


# ---------------------------------------------------------------------------
# Wave 5: S-1 — disabled and unknown tool never executes
# ---------------------------------------------------------------------------


async def test_disabled_tool_is_never_executed() -> None:
    # S-1: default (minimal) selection, langfuse_projects_get is disabled
    spec = load_api_spec()
    selection = build_tool_selection(spec, make_settings())
    fake = FakeClient(LangfuseResponse(status_code=200, content_type="application/json", data={}))
    service = LangfuseToolService(selection, fake)

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "tool_not_enabled"
    assert fake.calls == 0


async def test_unknown_tool_is_never_executed() -> None:
    # S-1: completely unknown tool should return unknown_tool, not execute
    spec = load_api_spec()
    selection = build_tool_selection(spec, make_settings())
    fake = FakeClient(LangfuseResponse(status_code=200, content_type="application/json", data={}))
    service = LangfuseToolService(selection, fake)

    result = await service.call_tool("langfuse_nope", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "unknown_tool"
    assert fake.calls == 0


# ---------------------------------------------------------------------------
# Wave 5: S-2 — response truncation
# ---------------------------------------------------------------------------


async def test_large_response_truncated() -> None:
    # S-2: compact JSON > max_response_bytes → truncated marker
    spec = load_api_spec()
    selection = build_tool_selection(
        spec, make_settings(LANGFUSE_TOOL_PROFILES="full", LANGFUSE_ENABLE_ADMIN_TOOLS=True)
    )
    big_data = {"items": ["x" * 10] * 30}  # will exceed 256 bytes when JSON serialized
    fake = FakeClient(
        LangfuseResponse(status_code=200, content_type="application/json", data=big_data)
    )
    service = LangfuseToolService(selection, fake, **{"max_response_bytes": 256})  # noqa: PIE804

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is False
    assert result.structuredContent is not None
    data = result.structuredContent["data"]
    assert data["truncated"] is True
    assert "data_bytes" in data
    assert len(data["preview"]) <= 256


async def test_small_response_not_truncated() -> None:
    # S-2: compact JSON <= max_response_bytes → pass through unchanged
    spec = load_api_spec()
    selection = build_tool_selection(
        spec, make_settings(LANGFUSE_TOOL_PROFILES="full", LANGFUSE_ENABLE_ADMIN_TOOLS=True)
    )
    small_data = {"ok": True}
    fake = FakeClient(
        LangfuseResponse(status_code=200, content_type="application/json", data=small_data)
    )
    service = LangfuseToolService(selection, fake, **{"max_response_bytes": 256})  # noqa: PIE804

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["data"] == small_data


# ---------------------------------------------------------------------------
# Wave 5: S-2/S-3 — compact UTF-8 text content
# ---------------------------------------------------------------------------


async def test_text_content_is_compact_utf8() -> None:
    # S-2/S-3: text must be compact (no ": " separator, no newline) and UTF-8 safe
    spec = load_api_spec()
    selection = build_tool_selection(
        spec, make_settings(LANGFUSE_TOOL_PROFILES="full", LANGFUSE_ENABLE_ADMIN_TOOLS=True)
    )
    fake = FakeClient(
        LangfuseResponse(status_code=200, content_type="application/json", data={"msg": "héllo"})
    )
    service = LangfuseToolService(selection, fake)

    result = await service.call_tool("langfuse_projects_get", {})

    text = result.content[0].text  # type: ignore[index,union-attr]
    # Must contain the un-escaped UTF-8 character
    assert "héllo" in text
    # Must not contain pretty-print ": " separator
    assert '": ' not in text
    # Must not contain newlines (compact)
    assert "\n" not in text


# ---------------------------------------------------------------------------
# Wave 5: S-4 — invalid_arguments payload does not echo back arguments
# ---------------------------------------------------------------------------


async def test_invalid_arguments_error_omits_arguments_echo() -> None:
    # S-4: invalid_arguments structured content should NOT contain an "arguments" key
    spec = load_api_spec()
    selection = build_tool_selection(
        spec, make_settings(LANGFUSE_TOOL_PROFILES="full", LANGFUSE_ENABLE_ADMIN_TOOLS=True)
    )
    fake = FakeClient(LangfuseArgumentError("bad args"))
    service = LangfuseToolService(selection, fake)

    result = await service.call_tool("langfuse_projects_get", {"bad": True})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "invalid_arguments"
    assert "arguments" not in result.structuredContent


# ---------------------------------------------------------------------------
# Wave 5: S-6 — LangfuseClientError base class is caught
# ---------------------------------------------------------------------------


async def test_base_client_error_mapped() -> None:
    # S-6: LangfuseClientError (base) must produce langfuse_client_error in structuredContent
    spec = load_api_spec()
    selection = build_tool_selection(
        spec, make_settings(LANGFUSE_TOOL_PROFILES="full", LANGFUSE_ENABLE_ADMIN_TOOLS=True)
    )
    fake = FakeClient(LangfuseClientError("boom"))
    service = LangfuseToolService(selection, fake)

    result = await service.call_tool("langfuse_projects_get", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"] == "langfuse_client_error"
