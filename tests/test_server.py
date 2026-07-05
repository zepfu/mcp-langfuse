"""Tests for server.py — startup diagnostics, SDK contract, and e2e (Wave 6)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from mcp_langfuse import server as server_module
from mcp_langfuse.client import LangfuseClient
from mcp_langfuse.openapi import load_api_spec
from mcp_langfuse.service import LangfuseToolService
from mcp_langfuse.tool_selection import ToolSelectionError, build_tool_selection
from tests.conftest import make_settings

# ---------------------------------------------------------------------------
# Existing tests (must keep passing after from_env removal)
# ---------------------------------------------------------------------------


def test_main_exits_with_configuration_error_for_invalid_tool_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    def raise_selection_error(*_args: object, **_kwargs: object) -> None:
        raise ToolSelectionError("Unknown tool profile: broken")

    monkeypatch.setattr(server_module, "build_tool_selection", raise_selection_error)

    with pytest.raises(SystemExit, match="Configuration error: Unknown tool profile: broken"):
        server_module.main()


def test_main_exits_with_configuration_error_for_invalid_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "langfuse.example")

    with pytest.raises(SystemExit, match="Configuration error:"):
        server_module.main()


# ---------------------------------------------------------------------------
# Wave 6: Q-1 — end-to-end tool call over in-memory MCP transport
# ---------------------------------------------------------------------------


@respx.mock
async def test_end_to_end_tool_call_over_memory_transport() -> None:
    import mcp.shared.memory as mcp_memory

    settings = make_settings(LANGFUSE_BASE_URL="https://langfuse.example")
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)
    client = LangfuseClient(settings)
    service = LangfuseToolService(selection, client)
    server = server_module.build_server(service)

    meta = {"page": 1, "limit": 1, "totalItems": 1, "totalPages": 1}
    respx.get("https://langfuse.example/api/public/traces").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": "t-1"}], "meta": meta},
        )
    )

    async with client, mcp_memory.create_connected_server_and_client_session(server) as mcp_client:
        tools_response = await mcp_client.list_tools()
        tool_names = [t.name for t in tools_response.tools]
        assert "langfuse_trace_list" in tool_names

        result = await mcp_client.call_tool("langfuse_trace_list", {"limit": 1})
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["ok"] is True


@respx.mock
async def test_end_to_end_schema_violation_uses_service_error_format() -> None:
    import mcp.shared.memory as mcp_memory

    settings = make_settings(LANGFUSE_BASE_URL="https://langfuse.example")
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)
    client = LangfuseClient(settings)
    service = LangfuseToolService(selection, client)
    server = server_module.build_server(service)

    async with client, mcp_memory.create_connected_server_and_client_session(server) as mcp_client:
        # Pass a dict for limit (which expects an integer) — schema violation
        result = await mcp_client.call_tool("langfuse_trace_list", {"limit": {"bad": 1}})
        assert result.isError is True
        assert result.structuredContent is not None
        assert result.structuredContent["error"] == "invalid_arguments"


# ---------------------------------------------------------------------------
# Wave 6: V-3 — startup diagnostics
# ---------------------------------------------------------------------------


def test_startup_diagnostics_summary_line(capsys: pytest.CaptureFixture) -> None:
    settings = make_settings()
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)

    server_module._log_startup_diagnostics(settings, selection)  # type: ignore[attr-defined]

    captured = capsys.readouterr()
    # Summary line must mention the count of enabled tools and profile names
    assert str(len(selection.enabled_operations)) in captured.err
    assert "minimal" in captured.err


def test_startup_diagnostics_warns_zero_tools(capsys: pytest.CaptureFixture) -> None:
    settings = make_settings(LANGFUSE_TOOL_PROFILES="")
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)

    server_module._log_startup_diagnostics(settings, selection)  # type: ignore[attr-defined]

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "0 tools" in captured.err


def test_startup_diagnostics_warns_unknown_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    # A typo'd env var matching LANGFUSE_* but not in KNOWN_ENV_VARS should trigger a WARNING
    monkeypatch.setenv("LANGFUSE_TOOLS_ENABLED", "x")  # typo: should be LANGFUSE_TOOLS_ENABLE

    settings = make_settings()
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)

    server_module._log_startup_diagnostics(settings, selection)  # type: ignore[attr-defined]

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "LANGFUSE_TOOLS_ENABLED" in captured.err


def test_startup_diagnostics_warns_gate_override(capsys: pytest.CaptureFixture) -> None:
    # T-1: a selection with gate_overrides should produce WARNING naming tool and gate
    settings = make_settings(
        LANGFUSE_TOOL_PROFILES="",
        LANGFUSE_TOOLS_ENABLE="langfuse_projects_delete",
    )
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)

    # Verify the selection has gate_overrides (this test fails until Wave 4 is implemented)
    assert hasattr(selection, "gate_overrides")
    assert "langfuse_projects_delete" in selection.gate_overrides  # type: ignore[attr-defined]

    server_module._log_startup_diagnostics(settings, selection)  # type: ignore[attr-defined]

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "langfuse_projects_delete" in captured.err


# ---------------------------------------------------------------------------
# Wave 6: V-5 — KeyboardInterrupt → SystemExit(130)
# ---------------------------------------------------------------------------


def _run_main_catching_keyboard_interrupt() -> None:
    """Wrap KeyboardInterrupt as SystemExit(1) for pre-implementation failure mode."""
    try:
        server_module.main()
    except KeyboardInterrupt as ki:
        # Pre-implementation: propagates uncaught → wrap so pytest.raises works.
        raise SystemExit(1) from ki


def test_main_handles_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    def raise_keyboard_interrupt(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(asyncio, "run", raise_keyboard_interrupt)

    # After V-5 fix, main() must convert KeyboardInterrupt to SystemExit(130).
    with pytest.raises(SystemExit) as exc_info:
        _run_main_catching_keyboard_interrupt()

    assert exc_info.value.code == 130
