"""Tests for openapi.py - load-time guarantees and schema fidelity (Waves 1-2)."""

from __future__ import annotations

import copy
import json

import pytest

from mcp_langfuse import openapi as openapi_module
from mcp_langfuse.openapi import load_api_spec, openapi_to_json_schema

# ---------------------------------------------------------------------------
# Existing tests (must keep passing)
# ---------------------------------------------------------------------------


def test_load_api_spec_has_expected_operation_count() -> None:
    spec = load_api_spec()

    assert len(spec.operations) == 87
    assert "langfuse_projects_create" in spec.by_tool_name
    assert "langfuse_trace_delete_multiple" in spec.by_tool_name
    assert "langfuse_annotation_queues_delete_queue_assignment" in spec.by_tool_name


def test_operation_input_schema_captures_path_and_body() -> None:
    spec = load_api_spec()
    operation = spec.by_tool_name["langfuse_annotation_queues_delete_queue_assignment"]
    schema = operation.input_schema

    assert schema["type"] == "object"
    assert "queueId" in schema["properties"]
    assert "body" in schema["properties"]
    assert "queueId" in schema["required"]
    assert "body" in schema["required"]


def test_operation_input_schema_captures_query_parameters() -> None:
    spec = load_api_spec()
    operation = spec.by_tool_name["langfuse_trace_list"]
    schema = operation.input_schema

    assert "page" in schema["properties"]
    assert "limit" in schema["properties"]
    assert schema["additionalProperties"] is False


# ---------------------------------------------------------------------------
# Wave 2: O-1 precomputed fields
# ---------------------------------------------------------------------------


def test_input_schema_is_precomputed() -> None:
    spec = load_api_spec()
    op = spec.by_tool_name["langfuse_trace_list"]
    # input_schema must be a stored field — same object identity on each access (O-1)
    assert op.input_schema is op.input_schema


def test_by_tool_name_is_precomputed() -> None:
    spec = load_api_spec()
    # by_tool_name must be a stored field — same object identity on each access (O-1)
    assert spec.by_tool_name is spec.by_tool_name


def test_no_unresolved_refs_in_input_schemas() -> None:
    spec = load_api_spec()
    for op in spec.operations:
        serialized = json.dumps(op.input_schema)
        assert "$ref" not in serialized, f"Unresolved $ref found in input_schema for {op.tool_name}"


# ---------------------------------------------------------------------------
# Wave 2: parse_api_spec validation (uses module attribute — attr-defined disabled)
# ---------------------------------------------------------------------------

_BASE_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "0.0.1"},
    "paths": {},
    "components": {"schemas": {}},
}


def _make_spec(*operations: dict) -> dict:
    """Build a synthetic raw spec with the given path entries."""
    spec = copy.deepcopy(_BASE_SPEC)
    for op_def in operations:
        path = op_def["path"]
        method = op_def["method"]
        item = op_def["item"]
        spec["paths"].setdefault(path, {})[method] = item
    return spec


def test_duplicate_tool_names_raise() -> None:
    # getTrace and get_trace both normalize to langfuse_get_trace → duplicate
    raw = _make_spec(
        {
            "path": "/test/trace",
            "method": "get",
            "item": {"operationId": "getTrace", "tags": ["Trace"], "responses": {"200": {}}},
        },
        {
            "path": "/test/trace2",
            "method": "get",
            "item": {"operationId": "get_trace", "tags": ["Trace"], "responses": {"200": {}}},
        },
    )
    with pytest.raises(ValueError, match="langfuse_get_trace"):
        openapi_module.parse_api_spec(raw)


def test_header_parameter_rejected_at_load() -> None:
    raw = _make_spec(
        {
            "path": "/test/something",
            "method": "get",
            "item": {
                "operationId": "getSomething",
                "tags": ["Test"],
                "parameters": [{"name": "X-Token", "in": "header", "required": False}],
                "responses": {"200": {}},
            },
        }
    )
    with pytest.raises(ValueError, match="getSomething"):
        openapi_module.parse_api_spec(raw)


def test_non_json_request_body_rejected_at_load() -> None:
    raw = _make_spec(
        {
            "path": "/test/upload",
            "method": "post",
            "item": {
                "operationId": "uploadFile",
                "tags": ["Test"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {"type": "object"},
                        },
                    },
                },
                "responses": {"200": {}},
            },
        }
    )
    with pytest.raises(ValueError, match="uploadFile"):
        openapi_module.parse_api_spec(raw)


def test_missing_operation_id_names_path_and_method() -> None:
    raw = _make_spec(
        {
            "path": "/test/noid",
            "method": "get",
            "item": {
                # deliberately no operationId
                "tags": ["Test"],
                "responses": {"200": {}},
            },
        }
    )
    with pytest.raises(ValueError, match="/test/noid") as exc_info:
        openapi_module.parse_api_spec(raw)
    assert "get" in str(exc_info.value)


def test_circular_ref_raises_value_error() -> None:
    # Schema A references itself via a property → infinite recursion guard (O-3)
    components: dict = {
        "schemas": {
            "A": {
                "type": "object",
                "properties": {
                    "child": {"$ref": "#/components/schemas/A"},
                },
            }
        }
    }
    schema: dict = {"$ref": "#/components/schemas/A"}
    with pytest.raises(ValueError, match=r"[Cc]ircular"):
        openapi_to_json_schema(schema, components)


def test_nullable_enum_accepts_null() -> None:
    schema: dict = {
        "type": "string",
        "enum": ["a", "b"],
        "nullable": True,
    }
    result = openapi_to_json_schema(schema, {})
    assert "enum" in result
    assert None in result["enum"]


def test_boolean_exclusive_minimum_converted() -> None:
    # OpenAPI-3.0 boolean exclusiveMinimum → Draft-2020-12 numeric exclusiveMinimum (O-6)
    schema: dict = {
        "type": "number",
        "minimum": 1,
        "exclusiveMinimum": True,
    }
    result = openapi_to_json_schema(schema, {})
    assert result.get("exclusiveMinimum") == 1
    assert "minimum" not in result
    # Must not retain a boolean value
    assert result.get("exclusiveMinimum") is not True


def test_copy_keys_include_const_and_multiple_of() -> None:
    # O-6: multipleOf, const, minProperties, maxProperties must be preserved
    schema: dict = {
        "type": "number",
        "multipleOf": 2,
        "const": 4,
        "minProperties": 1,
        "maxProperties": 5,
    }
    result = openapi_to_json_schema(schema, {})
    assert result.get("multipleOf") == 2
    assert result.get("const") == 4
    assert result.get("minProperties") == 1
    assert result.get("maxProperties") == 5


def test_all_of_merge_carries_description() -> None:
    # O-4: first part-level description should survive the merge
    schema: dict = {
        "allOf": [
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "description": "part A",
            },
            {
                "type": "object",
                "properties": {"b": {"type": "integer"}},
            },
        ]
    }
    result = openapi_to_json_schema(schema, {})
    assert result.get("description") == "part A"
