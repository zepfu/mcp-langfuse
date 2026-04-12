"""Generate the repository tool reference from the vendored Langfuse spec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .openapi import OperationSpec, load_api_spec, openapi_to_json_schema
from .tool_selection import describe_profiles

TOOLS_MD_PATH = Path("TOOLS.md")
MAX_ENUM_PREVIEW = 5
MAX_FIELD_PREVIEW = 6
MAX_EXAMPLE_DEPTH = 2


def _first_present_key(schema: dict[str, Any]) -> str | None:
    for key in ("oneOf", "anyOf", "allOf"):
        if schema.get(key):
            return key
    return None


def _type_summary(schema: dict[str, Any]) -> str:
    """Return a compact human-readable summary for a JSON schema node."""
    schema_type = schema.get("type")
    summary = "unknown"
    if isinstance(schema_type, list):
        summary = " | ".join(str(item) for item in schema_type)
    elif isinstance(schema_type, str):
        summary = schema_type
    else:
        variant_key = _first_present_key(schema)
        if variant_key is not None:
            summary = variant_key
        elif "properties" in schema:
            summary = "object"
        elif "items" in schema:
            summary = "array"
    return summary


def _schema_summary(schema: dict[str, Any]) -> str:
    """Return a short inline summary for parameter documentation."""
    parts = [_type_summary(schema)]

    if "format" in schema:
        parts.append(f"format={schema['format']}")
    if "enum" in schema:
        enum_values = ", ".join(json.dumps(value) for value in schema["enum"][:MAX_ENUM_PREVIEW])
        suffix = ", ..." if len(schema["enum"]) > MAX_ENUM_PREVIEW else ""
        parts.append(f"enum=[{enum_values}{suffix}]")
    if schema.get("type") == "object" and "properties" in schema:
        required = set(schema.get("required", []))
        keys = []
        for name, child in list(schema["properties"].items())[:MAX_FIELD_PREVIEW]:
            marker = "*" if name in required else ""
            keys.append(f"{name}{marker}:{_type_summary(child)}")
        suffix = ", ..." if len(schema["properties"]) > MAX_FIELD_PREVIEW else ""
        parts.append(f"fields={{{', '.join(keys)}{suffix}}}")
    if schema.get("type") == "array" and "items" in schema:
        parts.append(f"items={_type_summary(schema['items'])}")

    return ", ".join(parts)


def _example_for_object(schema: dict[str, Any], *, depth: int) -> dict[str, Any]:
    """Build an example object using required properties only."""
    result: dict[str, Any] = {}
    required = schema.get("required", [])
    for name in required:
        child = schema.get("properties", {}).get(name, {})
        result[name] = _example_value(child, depth=depth + 1)
    return result


def _example_for_variant(schema: dict[str, Any], *, depth: int) -> Any:
    """Build an example from the first available schema variant."""
    variant_key = _first_present_key(schema)
    if variant_key is None:
        return "<value>"
    return _example_value(schema[variant_key][0], depth=depth + 1)


def _example_for_primitive(schema_type: object, schema: dict[str, Any]) -> Any:
    """Build an example for primitive JSON schema types."""
    if schema_type == "string":
        return schema.get("format", "string")
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0
    if schema_type == "boolean":
        return False
    return None


def _example_value(schema: dict[str, Any], *, depth: int = 0) -> Any:
    """Build a compact JSON example value for documentation."""
    if depth >= MAX_EXAMPLE_DEPTH:
        return "<value>"

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((item for item in schema_type if item != "null"), schema_type[0])

    enum_values = schema.get("enum")
    if enum_values:
        return enum_values[0]

    primitive = _example_for_primitive(schema_type, schema)
    if primitive is not None:
        return primitive

    example: Any
    if schema_type == "array":
        items = schema.get("items", {})
        example = [_example_value(items, depth=depth + 1)]
    elif schema_type == "object" or "properties" in schema:
        example = _example_for_object(schema, depth=depth)
    elif _first_present_key(schema) is not None:
        example = _example_for_variant(schema, depth=depth)
    else:
        example = "<value>"

    return example


def _render_parameter_lines(operation: OperationSpec) -> list[str]:
    """Render the parameter list for one tool entry."""
    lines: list[str] = []
    for parameter in operation.parameters:
        schema = openapi_to_json_schema(parameter.schema, operation.components)
        required = "required" if parameter.required else "optional"
        description = parameter.description or "No description provided."
        lines.append(
            f"- `{parameter.name}`: {required}; source=`{parameter.location}`; "
            f"schema={_schema_summary(schema)}. {description}"
        )

    if operation.request_body is not None:
        schema = openapi_to_json_schema(operation.request_body.schema, operation.components)
        required = "required" if operation.request_body.required else "optional"
        description = operation.request_body.description or "No description provided."
        body_intro = (
            f"- `body`: {required}; source=`request body`; "
            f"content-type=`{operation.request_body.content_type}`; "
        )
        lines.append(f"{body_intro}schema={_schema_summary(schema)}. {description}")

    if not lines:
        lines.append("- None.")

    return lines


def _example_arguments(operation: OperationSpec) -> dict[str, Any]:
    """Build a minimal required-arguments example for one tool entry."""
    example: dict[str, Any] = {}

    for parameter in operation.parameters:
        if not parameter.required:
            continue
        schema = openapi_to_json_schema(parameter.schema, operation.components)
        example[parameter.name] = _example_value(schema)

    if operation.request_body is not None and operation.request_body.required:
        body_schema = openapi_to_json_schema(operation.request_body.schema, operation.components)
        example["body"] = _example_value(body_schema)

    return example


def render_tools_markdown() -> str:
    """Render the root `TOOLS.md` file from the vendored OpenAPI spec."""
    spec = load_api_spec()
    profiles = describe_profiles(spec)
    operations_by_tag: dict[str, list[OperationSpec]] = {}
    for operation in spec.operations:
        operations_by_tag.setdefault(operation.tag, []).append(operation)

    lines = [
        "# TOOLS",
        "",
        "Generated from `src/mcp_langfuse/specs/langfuse-openapi.yml`.",
        "",
        "## How To Use These Tools",
        "",
        "- Every tool is a 1:1 MCP wrapper around a Langfuse public API operation.",
        "- Path and query parameters are passed as top-level MCP arguments.",
        "- JSON request bodies are passed in a top-level `body` argument.",
        "- Successful calls return structured content shaped like "
        "`{ok, tool_name, status_code, content_type, data}`.",
        "- Failed calls return `isError: true` with structured content containing "
        "`error`, `message`, and any available Langfuse API details.",
        "- Tool discovery is filtered before `tools/list` is returned, using profiles, family "
        "overrides, and explicit tool overrides.",
        "",
        f"Total tools: {len(spec.operations)}",
        "",
        "## Tool Loading Profiles",
        "",
        "- Default profiles: `minimal`",
        "- Safety gates are off by default: write, destructive, admin, and legacy tools must be "
        "explicitly enabled.",
        "- Override knobs: `LANGFUSE_TOOL_PROFILES`, `LANGFUSE_TOOL_FAMILIES_ENABLE`, "
        "`LANGFUSE_TOOL_FAMILIES_DISABLE`, `LANGFUSE_TOOLS_ENABLE`, and "
        "`LANGFUSE_TOOLS_DISABLE`.",
        "- Safety gates: `LANGFUSE_ENABLE_WRITE_TOOLS`, `LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS`, "
        "`LANGFUSE_ENABLE_ADMIN_TOOLS`, and `LANGFUSE_ENABLE_LEGACY_TOOLS`.",
        "",
    ]

    for profile in profiles:
        families = ", ".join(f"`{family}`" for family in profile.families) or "all families"
        lines.append(f"### `{profile.name}`")
        lines.append("")
        lines.append(f"- Intent: {profile.description}")
        lines.append(f"- Families: {families}")
        lines.append(f"- Total matching tools: {profile.tool_count}")
        lines.append("")

    lines.append("## Tool Index")
    lines.append("")

    for tag in sorted(operations_by_tag):
        lines.append(f"### {tag}")
        lines.extend(
            f"- `{operation.tool_name}` -> `{operation.method} {operation.path}`"
            for operation in operations_by_tag[tag]
        )
        lines.append("")

    lines.append("## Tool Details")
    lines.append("")

    for tag in sorted(operations_by_tag):
        lines.append(f"## {tag}")
        lines.append("")
        for operation in operations_by_tag[tag]:
            lines.append(f"### `{operation.tool_name}`")
            lines.append("")
            intent = operation.description or "No description provided by Langfuse."
            lines.append(f"- Intent: {intent}")
            lines.append(f"- Langfuse operation: `{operation.operation_id}`")
            lines.append(f"- HTTP: `{operation.method} {operation.path}`")
            lines.append("- Parameters:")
            lines.extend(_render_parameter_lines(operation))
            example_arguments = _example_arguments(operation)
            if example_arguments:
                example_json = json.dumps(
                    example_arguments,
                    indent=2,
                    ensure_ascii=True,
                    sort_keys=True,
                )
                lines.append("- Usage example:")
                lines.append("```json")
                lines.append(example_json)
                lines.append("```")
            else:
                lines.append("- Usage example:")
                lines.append("```json")
                lines.append("{}")
                lines.append("```")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    """CLI entry point for rendering `TOOLS.md`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if TOOLS.md is out of date.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write TOOLS.md to the repository root.",
    )
    arguments = parser.parse_args()

    rendered = render_tools_markdown()

    if arguments.check:
        current = TOOLS_MD_PATH.read_text(encoding="utf-8") if TOOLS_MD_PATH.exists() else ""
        raise SystemExit(0 if current == rendered else 1)

    if arguments.write:
        TOOLS_MD_PATH.write_text(rendered, encoding="utf-8")
        return

    sys.stdout.write(rendered)
