"""Tests for profile and feature-flag based tool selection."""

from __future__ import annotations

import pytest

from mcp_langfuse.openapi import load_api_spec
from mcp_langfuse.tool_selection import ToolSelectionError, build_tool_selection, describe_profiles
from tests.conftest import make_settings


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


# ---------------------------------------------------------------------------
# Wave 4: T-3 destructive/write gate semantics
# ---------------------------------------------------------------------------


def test_destructive_flag_alone_enables_delete() -> None:
    # T-3: destructive=True alone should enable DELETE; write flag must NOT be required
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="observe_read",
            LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS=True,
            LANGFUSE_ENABLE_WRITE_TOOLS=False,
        ),
    )
    assert "langfuse_trace_delete" in selection.enabled_by_name


def test_write_flag_alone_does_not_enable_delete() -> None:
    # T-3 pin: write=True without destructive must NOT enable DELETE operations
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="observe_read",
            LANGFUSE_ENABLE_WRITE_TOOLS=True,
            LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS=False,
        ),
    )
    assert "langfuse_trace_delete" not in selection.enabled_by_name
    assert "destructive" in selection.disabled_reasons.get("langfuse_trace_delete", "")


# ---------------------------------------------------------------------------
# Wave 4: T-1 gate_overrides
# ---------------------------------------------------------------------------


def test_gate_overrides_recorded_for_forced_tools() -> None:
    # T-1: forcing a gated tool via LANGFUSE_TOOLS_ENABLE must record what gate was bypassed
    spec = load_api_spec()
    selection = build_tool_selection(
        spec,
        make_settings(
            LANGFUSE_TOOL_PROFILES="",
            LANGFUSE_TOOLS_ENABLE="langfuse_projects_delete",
            LANGFUSE_ENABLE_WRITE_TOOLS=False,
            LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS=False,
            LANGFUSE_ENABLE_ADMIN_TOOLS=False,
        ),
    )
    assert "langfuse_projects_delete" in selection.enabled_by_name
    # gate_overrides must record the reason the tool would have been blocked
    assert "langfuse_projects_delete" in selection.gate_overrides  # type: ignore[attr-defined]
    assert selection.gate_overrides["langfuse_projects_delete"]  # type: ignore[attr-defined]


def test_gate_overrides_empty_for_organic_tools() -> None:
    # T-1 pin: tools enabled by normal profile/gate path must NOT appear in gate_overrides
    spec = load_api_spec()
    selection = build_tool_selection(spec, make_settings())
    assert selection.gate_overrides == {}  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Wave 4: T-2 unknown constant family validation
# ---------------------------------------------------------------------------


def test_unknown_constant_family_raises() -> None:
    # T-2: build_tool_selection must fail loudly when spec lacks required admin/legacy families
    from mcp_langfuse import openapi as openapi_module

    # A minimal spec without any admin family tags
    minimal_spec = openapi_module.parse_api_spec(  # type: ignore[attr-defined]
        {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "0"},
            "paths": {
                "/health": {
                    "get": {
                        "operationId": "healthCheck",
                        "tags": ["Health"],
                        "responses": {"200": {}},
                    }
                }
            },
            "components": {},
        }
    )
    with pytest.raises(ToolSelectionError):
        build_tool_selection(minimal_spec, make_settings())


# ---------------------------------------------------------------------------
# Wave 4: T-4 conflicting family overrides raise before apply
# ---------------------------------------------------------------------------


def test_conflicting_family_overrides_raise_before_apply() -> None:
    spec = load_api_spec()
    with pytest.raises(ToolSelectionError):
        build_tool_selection(
            spec,
            make_settings(
                LANGFUSE_TOOL_FAMILIES_ENABLE="Trace", LANGFUSE_TOOL_FAMILIES_DISABLE="Trace"
            ),
        )


# ---------------------------------------------------------------------------
# Wave 4: T-5 describe_profiles tool_count accuracy
# ---------------------------------------------------------------------------


def test_describe_profiles_counts_match_spec() -> None:
    spec = load_api_spec()
    profiles = describe_profiles(spec)
    # Hand-compute expected count for 'minimal' profile
    minimal_families = frozenset(("Health", "Trace", "Observations", "Sessions", "Scores"))
    expected_count = sum(1 for op in spec.operations if op.tag in minimal_families)

    minimal_profile = next(p for p in profiles if p.name == "minimal")
    assert minimal_profile.tool_count == expected_count


# ---------------------------------------------------------------------------
# Wave 4: S-1 prerequisite — all_by_name field removed
# ---------------------------------------------------------------------------


def test_selection_no_longer_exposes_all_by_name() -> None:
    spec = load_api_spec()
    selection = build_tool_selection(spec, make_settings())
    assert not hasattr(selection, "all_by_name")
