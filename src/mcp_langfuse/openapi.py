"""Helpers for loading and normalizing the vendored Langfuse OpenAPI spec."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml

METHODS = {"get", "post", "put", "patch", "delete"}
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
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
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
    if not parts:
        return None

    if not all(part.get("type", "object") == "object" or "properties" in part for part in parts):
        return None

    merged: dict[str, Any] = {"type": "object"}
    properties: dict[str, Any] = {}
    required: list[str] = []
    additional_properties: bool | dict[str, Any] | None = None

    for part in parts:
        properties.update(part.get("properties", {}))
        required.extend(part.get("required", []))

        if "additionalProperties" in part:
            additional_properties = part["additionalProperties"]

    if properties:
        merged["properties"] = properties
    if required:
        merged["required"] = sorted(set(required))
    if additional_properties is not None:
        merged["additionalProperties"] = additional_properties

    return merged


def _copy_schema_keywords(schema: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in schema.items() if key in SCHEMA_COPY_KEYS}


def _apply_array_schema(
    result: dict[str, Any],
    schema: dict[str, Any],
    components: dict[str, Any],
) -> None:
    if "items" in schema:
        result["items"] = openapi_to_json_schema(schema["items"], components)


def _apply_object_schema(
    result: dict[str, Any],
    schema: dict[str, Any],
    components: dict[str, Any],
) -> None:
    if "properties" in schema:
        result["type"] = result.get("type", "object")
        result["properties"] = {
            name: openapi_to_json_schema(child, components)
            for name, child in schema["properties"].items()
        }

    if "required" in schema:
        result["required"] = copy.deepcopy(schema["required"])

    if "additionalProperties" not in schema:
        return

    additional = schema["additionalProperties"]
    if isinstance(additional, dict):
        result["additionalProperties"] = openapi_to_json_schema(additional, components)
        return

    result["additionalProperties"] = bool(additional)


def _apply_union_schema(
    result: dict[str, Any],
    schema: dict[str, Any],
    components: dict[str, Any],
) -> None:
    if "oneOf" in schema:
        result["oneOf"] = [openapi_to_json_schema(part, components) for part in schema["oneOf"]]

    if "anyOf" in schema:
        result["anyOf"] = [openapi_to_json_schema(part, components) for part in schema["anyOf"]]

    if "allOf" not in schema:
        return

    all_of = [openapi_to_json_schema(part, components) for part in schema["allOf"]]
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

    json_type = result.get("type")
    if isinstance(json_type, str):
        result["type"] = [json_type, "null"]
        return result

    return {"anyOf": [result, {"type": "null"}]}


def openapi_to_json_schema(
    raw_schema: dict[str, Any] | None,
    components: dict[str, Any],
) -> dict[str, Any]:
    """Convert a subset of OpenAPI 3.0 schema into JSON Schema."""
    if not raw_schema:
        return {"type": "object", "additionalProperties": True}

    schema = _resolve_object(raw_schema, components)
    if schema is None:
        return {"type": "object", "additionalProperties": True}

    if "$ref" in schema:
        return openapi_to_json_schema(schema, components)

    nullable = bool(schema.pop("nullable", False))
    result = _copy_schema_keywords(schema)
    _apply_array_schema(result, schema, components)
    _apply_object_schema(result, schema, components)
    _apply_union_schema(result, schema, components)
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

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the MCP input schema derived from parameters plus request body."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for parameter in self.parameters:
            parameter_schema = openapi_to_json_schema(parameter.schema, self.components)
            if parameter.description and "description" not in parameter_schema:
                parameter_schema["description"] = parameter.description
            properties[parameter.name] = parameter_schema
            if parameter.required:
                required.append(parameter.name)

        if self.request_body is not None:
            body_schema = openapi_to_json_schema(self.request_body.schema, self.components)
            body_schema.setdefault(
                "description",
                self.request_body.description or f"Request body ({self.request_body.content_type})",
            )
            properties["body"] = body_schema
            if self.request_body.required:
                required.append("body")

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = sorted(set(required))

        return schema

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

    @property
    def by_tool_name(self) -> dict[str, OperationSpec]:
        """Map tool names to normalized Langfuse operation metadata."""
        return {operation.tool_name: operation for operation in self.operations}


def _collect_parameters(
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

    deduped: dict[tuple[str, str], ParameterSpec] = {}
    for item in merged:
        parameter = ParameterSpec(
            name=item["name"],
            location=item["in"],
            required=bool(item.get("required", False)),
            schema=item.get("schema", {"type": "string"}),
            description=item.get("description"),
        )
        deduped[(parameter.location, parameter.name)] = parameter

    return tuple(deduped.values())


def _collect_request_body(
    operation: dict[str, Any],
    components: dict[str, Any],
) -> RequestBodySpec | None:
    request_body = _resolve_object(operation.get("requestBody"), components)
    if request_body is None:
        return None

    content = request_body.get("content", {})
    if not content:
        return None

    preferred_content_type = "application/json"
    content_type = (
        preferred_content_type if preferred_content_type in content else next(iter(content))
    )
    media_type = content[content_type]

    return RequestBodySpec(
        required=bool(request_body.get("required", False)),
        content_type=content_type,
        schema=media_type.get("schema", {"type": "object", "additionalProperties": True}),
        description=request_body.get("description"),
    )


@lru_cache(maxsize=1)
def load_api_spec() -> LangfuseAPISpec:
    """Load and normalize the vendored Langfuse OpenAPI specification."""
    with (
        resources.files("mcp_langfuse.specs")
        .joinpath("langfuse-openapi.yml")
        .open(
            "r",
            encoding="utf-8",
        ) as handle
    ):
        raw_spec = yaml.safe_load(handle)

    components = raw_spec.get("components", {})
    operations: list[OperationSpec] = []

    for path, path_item in raw_spec["paths"].items():
        for method, operation in path_item.items():
            if method not in METHODS:
                continue

            operation_id = operation["operationId"]
            tool_name = f"langfuse_{_snake_case(operation_id)}"
            tag = (operation.get("tags") or ["Untagged"])[0]
            description = operation.get("description") or operation.get("summary") or ""
            parameters = _collect_parameters(path_item, operation, components)
            request_body = _collect_request_body(operation, components)

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
                )
            )

    operations.sort(key=lambda operation: operation.tool_name)
    return LangfuseAPISpec(operations=tuple(operations))
