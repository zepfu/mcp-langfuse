"""Tests for profile and feature-flag based tool selection."""

from typing import Any

from mcp_langfuse.config import Settings
from mcp_langfuse.openapi import load_api_spec
from mcp_langfuse.tool_selection import build_tool_selection


def make_settings(**overrides: Any) -> Settings:
    """Create selection settings with required auth placeholders."""
    values: dict[str, Any] = {
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
    }
    values.update(overrides)
    return Settings(**values)


def test_default_selection_is_minimal_and_read_only() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(spec, make_settings())

    enabled = selection.enabled_by_name

    assert "langfuse_health_health" in enabled
    assert "langfuse_trace_list" in enabled
    assert "langfuse_trace_delete" not in enabled
    assert "langfuse_projects_get" not in enabled


def test_profile_and_family_overrides_expand_available_tools() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="prompts",
            LANGFUSE_TOOL_FAMILIES_ENABLE="Models",
            LANGFUSE_ENABLE_WRITE_TOOLS=True,
        ),
    )

    enabled = selection.enabled_by_name

    assert "langfuse_prompts_get" in enabled
    assert "langfuse_prompts_create" in enabled
    assert "langfuse_prompt_version_update" in enabled
    assert "langfuse_models_list" in enabled
    assert "langfuse_projects_get" not in enabled


def test_explicit_tool_enable_overrides_profiles_and_safety_gates() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="",
            LANGFUSE_TOOLS_ENABLE="langfuse_projects_delete",
        ),
    )

    assert tuple(selection.enabled_by_name) == ("langfuse_projects_delete",)


def test_explicit_tool_disable_removes_otherwise_enabled_tool() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="observe_read",
            LANGFUSE_TOOLS_DISABLE="langfuse_trace_list",
        ),
    )

    assert "langfuse_trace_list" not in selection.enabled_by_name
    assert selection.disabled_reasons["langfuse_trace_list"] == "tool is explicitly disabled"
