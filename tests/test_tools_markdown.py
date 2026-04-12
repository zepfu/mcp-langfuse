"""Tests for generated tool reference documentation."""

from pathlib import Path

from mcp_langfuse.tools_markdown import render_tools_markdown


def test_tools_markdown_is_synced() -> None:
    expected = render_tools_markdown()
    actual = Path("TOOLS.md").read_text(encoding="utf-8")

    assert actual == expected
