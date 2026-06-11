"""Tests for generated tool reference documentation (Waves 7 + Q-2)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mcp_langfuse.tools_markdown import render_tools_markdown

# ---------------------------------------------------------------------------
# Existing test — anchored to TOOLS.md relative to this file (Q-2)
# ---------------------------------------------------------------------------


def test_tools_markdown_is_synced() -> None:
    expected = render_tools_markdown()
    # Q-2: CWD-independent path — resolve relative to this test file
    tools_md_path = Path(__file__).resolve().parents[1] / "TOOLS.md"
    actual = tools_md_path.read_text(encoding="utf-8")

    assert actual == expected


# ---------------------------------------------------------------------------
# Wave 7: M-1/M-2/M-3/M-4 — CLI argument handling and heading levels
# ---------------------------------------------------------------------------


def test_check_missing_file_exits_2_with_message(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    absent = tmp_path / "absent.md"
    from mcp_langfuse import tools_markdown as tools_md_module

    sys.argv = ["tools_markdown", "--check", "--path", str(absent)]
    try:
        with pytest.raises(SystemExit) as exc_info:
            tools_md_module.main()
    finally:
        sys.argv = []

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert str(absent) in captured.err


def test_check_out_of_date_prints_remedy(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    stale = tmp_path / "stale.md"
    stale.write_text("stale content", encoding="utf-8")
    from mcp_langfuse import tools_markdown as tools_md_module

    sys.argv = ["tools_markdown", "--check", "--path", str(stale)]
    try:
        with pytest.raises(SystemExit) as exc_info:
            tools_md_module.main()
    finally:
        sys.argv = []

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "--write" in captured.err


def test_check_and_write_mutually_exclusive(capsys: pytest.CaptureFixture) -> None:
    from mcp_langfuse import tools_markdown as tools_md_module

    sys.argv = ["tools_markdown", "--check", "--write"]
    try:
        with pytest.raises(SystemExit) as exc_info:
            tools_md_module.main()
    finally:
        sys.argv = []

    # argparse exits with 2 for mutually exclusive group conflict
    assert exc_info.value.code == 2


def test_write_respects_path(tmp_path: Path) -> None:
    out = tmp_path / "out.md"
    from mcp_langfuse import tools_markdown as tools_md_module

    sys.argv = ["tools_markdown", "--write", "--path", str(out)]
    try:
        tools_md_module.main()
    finally:
        sys.argv = []

    assert out.exists()
    written = out.read_text(encoding="utf-8")
    assert written == render_tools_markdown()


def test_tool_details_heading_levels() -> None:
    rendered = render_tools_markdown()
    # M-4: Tool Details must use ### for tags (not ##)
    assert "\n## Trace\n" not in rendered
    # Tool Details tag heading must be ### Trace
    assert "\n### Trace\n" in rendered
    # Tool entries in details must be #### `tool_name`
    assert "\n#### `langfuse_trace_list`" in rendered
