from __future__ import annotations

import pytest

from mcp_langfuse import server as server_module
from mcp_langfuse.tool_selection import ToolSelectionError


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
