"""Helpers for loading and normalizing the vendored Langfuse OpenAPI spec."""

from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml

METHODS = {"get", "post", "put", "patch", "delete"}
ALLOWED_PARAMETER_LOCATIONS = frozenset({"path", "query"})
JSON_CONTENT_TYPE = "application/json"
SCHEMA_COPY_KEYS = (
    "title",
    "description",
    "type",
    "format",
    "enum",
    "default",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "const",
)


def _snake_case(value: str) -> str:
    value = value.replace("-", "_")
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"_+", "_", value).lower()


def _resolve_ref(ref: str, components: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/components/"):
        message = f"Unsupported ref: {ref}"
        raise ValueError(message)

    current: Any = {"components": components}
    for part in ref.removeprefix("#/").split("/"):
        current = current[part]

    if not isinstance(current, dict):
        message = f"Resolved ref is not an object: {ref}"
        raise TypeError(message)

    return copy.deepcopy(current)


def _resolve_object(
    raw: dict[str, Any] | None,
    components: dict[str, Any],
) -> dict[str, Any] | None:
    if raw is None:
        return None

    if "$ref" not in raw:
        return copy.deepcopy(raw)

    resolved = _resolve_ref(raw["$ref"], components)
    overlay = {key: value for key, value in raw.items() if key != "$ref"}
    resolved.update(copy.deepcopy(overlay))
    return resolved


def _merge_all_of(parts: list[dict[str, Any]]) -> dict[str, Any] | None:
    # Intentional leniency: this merge models input gating, not full JSON-Schema "allOf"
    # AND semantics. Parts that are not object-shaped abort the merge (callers fall back to
    # emitting a verbatim ``allOf``); for object parts we union properties/required and keep
    # the first part-level description so documentation and validation stay useful.
    if not parts:
        return None

    if not all(part.get("type", "object") == "object" or "properties" in part for part in parts):
        return None

    merged: dict[str, Any] = {"type": "object"}
    properties: dict[str, Any] = {}
    required: list[str] = []
    additional_properties: bool | dict[str, Any] | None = None
    description: str | None = None

    for part in parts:
        properties.update(part.get("properties", {}))
        required.extend(part.get("required", []))

        if description is None and part.get("description"):
            description = part["description"]

        if "additionalProperties" in part:
            additional_properties = part["additionalProperties"]

    if description is not None:
        merged["description"] = description
    if properties:
        merged["properties"] = properties
    if required:
        merged["required"] = sorted(set(required))
    if additional_properties is not None:
        merged["additionalProperties"] = additional_properties

    return merged


def _convert_exclusive_bound(result: dict[str, Any], *, bound: str, exclusive: str) -> None:
    """Convert an OpenAPI-3.0 boolean exclusive bound to Draft-2020-12 numeric form."""
    flag = result.get(exclusive)
    if not isinstance(flag, bool):
        return

    if flag and bound in result:
        result[exclusive] = result.pop(bound)
        return

    result.pop(exclusive, None)


def _copy_schema_keywords(schema: dict[str, Any]) -> dict[str, Any]:
    result = {key: copy.deepcopy(value) for key, value in schema.items() if key in SCHEMA_COPY_KEYS}
    _convert_exclusive_bound(result, bound="minimum", exclusive="exclusiveMinimum")
    _convert_exclusive_bound(result, bound="maximum", exclusive="exclusiveMaximum")
    return result


def _apply_array_schema(
    result: dict[str, Any],
    schema: dict[str, Any],
    components: dict[str, Any],
    ref_stack: frozenset[str],
) -> None:
    if "items" in schema:
        result["items"] = openapi_to_json_schema(
            schema["items"],
            components,
            _ref_stack=ref_stack,
        )


def _apply_object_schema(
    result: dict[str, Any],
    schema: dict[str, Any],
    components: dict[str, Any],
    ref_stack: frozenset[str],
) -> None:
    if "properties" in schema:
        result["type"] = result.get("type", "object")
        result["properties"] = {
            name: openapi_to_json_schema(child, components, _ref_stack=ref_stack)
            for name, child in schema["properties"].items()
        }

    if "required" in schema:
        result["required"] = copy.deepcopy(schema["required"])

    if "additionalProperties" not in schema:
        return

    additional = schema["additionalProperties"]
    if isinstance(additional, dict):
        result["additionalProperties"] = openapi_to_json_schema(
            additional,
            components,
            _ref_stack=ref_stack,
        )
        return

    result["additionalProperties"] = bool(additional)


def _apply_union_schema(
    result: dict[str, Any],
    schema: dict[str, Any],
    components: dict[str, Any],
    ref_stack: frozenset[str],
) -> None:
    if "oneOf" in schema:
        result["oneOf"] = [
            openapi_to_json_schema(part, components, _ref_stack=ref_stack)
            for part in schema["oneOf"]
        ]

    if "anyOf" in schema:
        result["anyOf"] = [
            openapi_to_json_schema(part, components, _ref_stack=ref_stack)
            for part in schema["anyOf"]
        ]

    if "allOf" not in schema:
        return

    all_of = [
        openapi_to_json_schema(part, components, _ref_stack=ref_stack) for part in schema["allOf"]
    ]
    merged = _merge_all_of(all_of)
    if merged is not None:
        result.update(merged)
        return

    result["allOf"] = all_of


def _finalize_schema(result: dict[str, Any], *, nullable: bool) -> dict[str, Any]:
    if "type" not in result and "properties" in result:
        result["type"] = "object"

    if (
        result.get("type") == "object"
        and "properties" not in result
        and "additionalProperties" not in result
    ):
        result["additionalProperties"] = True

    if not result:
        result = {"type": "object", "additionalProperties": True}

    if not nullable:
        return result

    if "enum" in result and None not in result["enum"]:
        result["enum"] = [*result["enum"], None]

    json_type = result.get("type")
    if isinstance(json_type, str):
        result["type"] = [json_type, "null"]
        return result

    return {"anyOf": [result, {"type": "null"}]}


def openapi_to_json_schema(
    raw_schema: dict[str, Any] | None,
    components: dict[str, Any],
    *,
    _ref_stack: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Convert a subset of OpenAPI 3.0 schema into JSON Schema.

    Args:
        raw_schema: The OpenAPI schema node to convert (may be ``None``).
        components: The spec ``components`` mapping used to resolve ``$ref`` nodes.
        _ref_stack: Internal guard tracking ``$ref`` targets currently being resolved.

    Returns:
        An equivalent Draft-2020-12 JSON Schema dict with all ``$ref`` nodes resolved.

    Raises:
        ValueError: If a circular ``$ref`` chain is detected.

    """
    if not raw_schema:
        return {"type": "object", "additionalProperties": True}

    ref_stack = _ref_stack
    if "$ref" in raw_schema:
        ref = raw_schema["$ref"]
        if ref in ref_stack:
            message = f"Circular $ref detected: {ref}"
            raise ValueError(message)
        ref_stack = ref_stack | {ref}

    schema = _resolve_object(raw_schema, components)
    if schema is None:
        return {"type": "object", "additionalProperties": True}

    if "$ref" in schema:
        return openapi_to_json_schema(schema, components, _ref_stack=ref_stack)

    nullable = bool(schema.pop("nullable", False))
    result = _copy_schema_keywords(schema)
    _apply_array_schema(result, schema, components, ref_stack)
    _apply_object_schema(result, schema, components, ref_stack)
    _apply_union_schema(result, schema, components, ref_stack)
    return _finalize_schema(result, nullable=nullable)


@dataclass(frozen=True)
class ParameterSpec:
    """Description of a single path or query parameter."""

    name: str
    location: str
    required: bool
    schema: dict[str, Any]
    description: str | None = None


@dataclass(frozen=True)
class RequestBodySpec:
    """Description of a JSON request body exposed as the `body` MCP argument."""

    required: bool
    content_type: str
    schema: dict[str, Any]
    description: str | None = None


def _build_input_schema(
    parameters: tuple[ParameterSpec, ...],
    request_body: RequestBodySpec | None,
    components: dict[str, Any],
) -> dict[str, Any]:
    """Build the MCP input schema from parameters plus the request body.

    Args:
        parameters: The normalized path/query parameters for the operation.
        request_body: The normalized JSON request body, if any.
        components: The spec ``components`` mapping used to resolve ``$ref`` nodes.

    Returns:
        The fully resolved JSON Schema dict for the tool's input.

    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    for parameter in parameters:
        parameter_schema = openapi_to_json_schema(parameter.schema, components)
        if parameter.description and "description" not in parameter_schema:
            parameter_schema["description"] = parameter.description
        properties[parameter.name] = parameter_schema
        if parameter.required:
            required.append(parameter.name)

    if request_body is not None:
        body_schema = openapi_to_json_schema(request_body.schema, components)
        body_schema.setdefault(
            "description",
            request_body.description or f"Request body ({request_body.content_type})",
        )
        properties["body"] = body_schema
        if request_body.required:
            required.append("body")

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = sorted(set(required))

    return schema


@dataclass(frozen=True)
class OperationSpec:
    """Normalized metadata for one Langfuse API operation."""

    tool_name: str
    operation_id: str
    tag: str
    method: str
    path: str
    description: str
    parameters: tuple[ParameterSpec, ...]
    request_body: RequestBodySpec | None
    components: dict[str, Any]
    input_schema: dict[str, Any]

    @property
    def tool_description(self) -> str:
        """Return a readable description shown to MCP clients."""
        prefix = f"{self.method} {self.path}"
        detail = self.description.strip()
        if detail:
            return f"{prefix}\n\nTag: {self.tag}\n\n{detail}"
        return f"{prefix}\n\nTag: {self.tag}"


@dataclass(frozen=True)
class LangfuseAPISpec:
    """Container for the full normalized Langfuse API surface."""

    operations: tuple[OperationSpec, ...]
    by_tool_name: dict[str, OperationSpec]


def _collect_parameters(
    path: str,
    method: str,
    path_item: dict[str, Any],
    operation: dict[str, Any],
    components: dict[str, Any],
) -> tuple[ParameterSpec, ...]:
    merged: list[dict[str, Any]] = []
    for source in (path_item.get("parameters", []), operation.get("parameters", [])):
        for item in source:
            resolved = _resolve_object(item, components)
            if resolved is None:
                continue
            merged.append(resolved)

    operation_id = operation.get("operationId", f"{method.upper()} {path}")
    deduped: dict[tuple[str, str], ParameterSpec] = {}
    for item in merged:
        if "name" not in item:
            message = f"Parameter missing 'name' for {operation_id} ({method.upper()} {path})"
            raise ValueError(message)
        if "in" not in item:
            message = (
                f"Parameter '{item['name']}' missing 'in' for "
                f"{operation_id} ({method.upper()} {path})"
            )
            raise ValueError(message)

        location = item["in"]
        if location not in ALLOWED_PARAMETER_LOCATIONS:
            message = (
                f"Unsupported parameter location '{location}' for parameter "
                f"'{item['name']}' in {operation_id} ({method.upper()} {path})"
            )
            raise ValueError(message)

        parameter = ParameterSpec(
            name=item["name"],
            location=location,
            required=bool(item.get("required", False)),
            schema=item.get("schema", {"type": "string"}),
            description=item.get("description"),
        )
        deduped[(parameter.location, parameter.name)] = parameter

    return tuple(deduped.values())


def _collect_request_body(
    path: str,
    method: str,
    operation: dict[str, Any],
    components: dict[str, Any],
) -> RequestBodySpec | None:
    request_body = _resolve_object(operation.get("requestBody"), components)
    if request_body is None:
        return None

    content = request_body.get("content", {})
    if not content:
        return None

    operation_id = operation.get("operationId", f"{method.upper()} {path}")
    content_type = JSON_CONTENT_TYPE if JSON_CONTENT_TYPE in content else next(iter(content))
    if content_type != JSON_CONTENT_TYPE:
        message = (
            f"Unsupported request body content type '{content_type}' for "
            f"{operation_id} ({method.upper()} {path}); only {JSON_CONTENT_TYPE} is supported"
        )
        raise ValueError(message)

    media_type = content[content_type]

    return RequestBodySpec(
        required=bool(request_body.get("required", False)),
        content_type=content_type,
        schema=media_type.get("schema", {"type": "object", "additionalProperties": True}),
        description=request_body.get("description"),
    )


def parse_api_spec(raw_spec: dict[str, Any]) -> LangfuseAPISpec:
    """Normalize a raw OpenAPI document into a validated Langfuse API spec.

    Args:
        raw_spec: The parsed OpenAPI document (e.g. from YAML).

    Returns:
        A normalized, validated :class:`LangfuseAPISpec`.

    Raises:
        ValueError: If the spec is missing required fields, uses unsupported parameter
            locations or content types, or produces duplicate tool names.

    """
    components = raw_spec.get("components", {})
    operations: list[OperationSpec] = []

    for path, path_item in raw_spec["paths"].items():
        for method, operation in path_item.items():
            if method not in METHODS:
                continue

            if "operationId" not in operation:
                message = f"Operation missing 'operationId' for path {path} method {method}"
                raise ValueError(message)

            operation_id = operation["operationId"]
            tool_name = f"langfuse_{_snake_case(operation_id)}"
            tag = (operation.get("tags") or ["Untagged"])[0]
            description = operation.get("description") or operation.get("summary") or ""
            parameters = _collect_parameters(path, method, path_item, operation, components)
            request_body = _collect_request_body(path, method, operation, components)
            input_schema = _build_input_schema(parameters, request_body, components)

            operations.append(
                OperationSpec(
                    tool_name=tool_name,
                    operation_id=operation_id,
                    tag=tag,
                    method=method.upper(),
                    path=path,
                    description=description,
                    parameters=parameters,
                    request_body=request_body,
                    components=components,
                    input_schema=input_schema,
                )
            )

    operations.sort(key=lambda operation: operation.tool_name)

    names = [operation.tool_name for operation in operations]
    if len(names) != len(set(names)):
        counts = Counter(names)
        dupes = sorted(name for name, count in counts.items() if count > 1)
        message = f"Duplicate tool names after normalization: {', '.join(dupes)}"
        raise ValueError(message)

    by_tool_name = {operation.tool_name: operation for operation in operations}
    return LangfuseAPISpec(operations=tuple(operations), by_tool_name=by_tool_name)


@lru_cache(maxsize=1)
def load_api_spec() -> LangfuseAPISpec:
    """Load and normalize the vendored Langfuse OpenAPI specification.

    Returns:
        The normalized, validated :class:`LangfuseAPISpec` for the vendored spec.

    """
    with (
        resources.files("mcp_langfuse.specs")
        .joinpath("langfuse-openapi.yml")
        .open(
            "r",
            encoding="utf-8",
        ) as handle
    ):
        raw_spec = yaml.safe_load(handle)

    return parse_api_spec(raw_spec)
