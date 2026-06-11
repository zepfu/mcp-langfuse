"""Smoke tests for plan-adversarial-review-remediation.

These tests validate that the feature works end-to-end after implementation.
They are permanent regression guards.
"""

from __future__ import annotations

import json

from mcp_langfuse.config import Settings
from mcp_langfuse.openapi import load_api_spec
from mcp_langfuse.tool_selection import build_tool_selection


def test_mcp_langfuse_imports() -> None:
    """All mcp_langfuse modules must be importable without error."""
    from mcp_langfuse import (
        __version__,
        client,
        config,
        openapi,
        server,
        service,
        tool_selection,
        tools_markdown,
    )

    # Verify the module objects are non-None
    assert __version__ is not None
    assert client is not None
    assert config is not None
    assert openapi is not None
    assert server is not None
    assert service is not None
    assert tool_selection is not None
    assert tools_markdown is not None


def test_default_selection_has_tools() -> None:
    """Default settings must produce a non-empty enabled tool set.

    Guards against the silent zero-tools regression class (T-6/C-2).
    """
    settings = Settings(
        LANGFUSE_PUBLIC_KEY="pk-test",
        LANGFUSE_SECRET_KEY="sk-test",
    )
    spec = load_api_spec()
    selection = build_tool_selection(spec, settings)

    assert len(selection.enabled_operations) > 0
    assert len(selection.enabled_by_name) > 0


def test_input_schemas_have_no_refs() -> None:
    """Every precomputed input_schema must be $ref-free (L-9/O-1).

    All $refs must be resolved at load time; no deferred resolution at call time.
    """
    spec = load_api_spec()
    for op in spec.operations:
        serialized = json.dumps(op.input_schema)
        assert "$ref" not in serialized, f"Unresolved $ref in input_schema for {op.tool_name}"
