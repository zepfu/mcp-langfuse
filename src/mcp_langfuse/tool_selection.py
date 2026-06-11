"""Profile and flag-based tool selection for the Langfuse MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings
    from .openapi import LangfuseAPISpec, OperationSpec

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DESTRUCTIVE_METHODS = frozenset({"DELETE"})
ADMIN_FAMILIES = frozenset(
    {
        "BlobStorageIntegrations",
        "LlmConnections",
        "Organizations",
        "Projects",
        "Scim",
    }
)
LEGACY_FAMILIES = frozenset({"LegacyMetricsV1", "LegacyObservationsV1", "LegacyScoreV1"})


@dataclass(frozen=True)
class ToolProfile:
    """Named profile for a common Langfuse MCP tool use case."""

    name: str
    description: str
    families: tuple[str, ...]


@dataclass(frozen=True)
class DocumentedProfile:
    """Resolved profile description used in docs and tests."""

    name: str
    description: str
    families: tuple[str, ...]
    tool_count: int


@dataclass(frozen=True)
class ToolSelection:
    """Result of applying profile and flag-based filtering to the API spec."""

    enabled_operations: tuple[OperationSpec, ...]
    enabled_by_name: dict[str, OperationSpec]
    disabled_reasons: dict[str, str]
    selected_families: frozenset[str]
    gate_overrides: dict[str, str]


class ToolSelectionError(ValueError):
    """Raised when tool selection configuration is invalid."""


TOOL_PROFILES = (
    ToolProfile(
        name="minimal",
        description="Small default read-only observability set.",
        families=("Health", "Trace", "Observations", "Sessions", "Scores"),
    ),
    ToolProfile(
        name="observe_read",
        description="Broader read-only observability and metrics profile.",
        families=("Health", "Trace", "Observations", "Sessions", "Scores", "Metrics", "Models"),
    ),
    ToolProfile(
        name="ingest",
        description="Tracing and media ingestion profile.",
        families=("Ingestion", "Opentelemetry", "Media"),
    ),
    ToolProfile(
        name="evals",
        description="Evaluation, annotation, scoring, and prompt review profile.",
        families=(
            "AnnotationQueues",
            "Comments",
            "ScoreConfigs",
            "Scores",
            "Prompts",
            "PromptVersion",
        ),
    ),
    ToolProfile(
        name="datasets",
        description="Dataset and run management profile.",
        families=("Datasets", "DatasetItems", "DatasetRunItems"),
    ),
    ToolProfile(
        name="prompts",
        description="Prompt management profile.",
        families=("Prompts", "PromptVersion"),
    ),
    ToolProfile(
        name="project_admin",
        description="Project-scoped administration profile.",
        families=("Projects", "BlobStorageIntegrations", "LlmConnections"),
    ),
    ToolProfile(
        name="org_admin",
        description="Organization and SCIM administration profile.",
        families=("Organizations", "Scim"),
    ),
    ToolProfile(
        name="admin",
        description="Combined project and organization administration profile.",
        families=(
            "Projects",
            "BlobStorageIntegrations",
            "LlmConnections",
            "Organizations",
            "Scim",
        ),
    ),
    ToolProfile(
        name="legacy",
        description="Legacy Langfuse API compatibility profile.",
        families=("LegacyMetricsV1", "LegacyObservationsV1", "LegacyScoreV1"),
    ),
    ToolProfile(
        name="full",
        description="All current Langfuse public API families.",
        families=(),
    ),
)

_PROFILES_BY_NAME = {profile.name: profile for profile in TOOL_PROFILES}


def _normalize_name(value: str) -> str:
    return value.strip().lower()


def _resolve_requested_families(
    requested: tuple[str, ...],
    available_families: set[str],
) -> set[str]:
    family_lookup = {_normalize_name(family): family for family in available_families}
    resolved: set[str] = set()

    for family in requested:
        canonical = family_lookup.get(_normalize_name(family))
        if canonical is None:
            message = f"Unknown tool family: {family}"
            raise ToolSelectionError(message)
        resolved.add(canonical)

    return resolved


def _resolve_requested_tools(
    requested: tuple[str, ...],
    available_tool_names: set[str],
) -> set[str]:
    tool_lookup = {_normalize_name(tool_name): tool_name for tool_name in available_tool_names}
    resolved: set[str] = set()

    for tool_name in requested:
        canonical = tool_lookup.get(_normalize_name(tool_name))
        if canonical is None:
            message = f"Unknown tool name: {tool_name}"
            raise ToolSelectionError(message)
        resolved.add(canonical)

    return resolved


def _resolve_profile_families(
    profile_names: tuple[str, ...],
    available_families: set[str],
) -> set[str]:
    resolved: set[str] = set()

    for profile_name in profile_names:
        profile = _PROFILES_BY_NAME.get(_normalize_name(profile_name))
        if profile is None:
            message = f"Unknown tool profile: {profile_name}"
            raise ToolSelectionError(message)

        if profile.name == "full":
            resolved.update(available_families)
            continue

        resolved.update(profile.families)

    return resolved


def _validate_known_families(available: set[str]) -> None:
    """Validate that every hardcoded family constant exists in the spec.

    Args:
        available: The set of family (tag) names present in the loaded spec.

    Raises:
        ToolSelectionError: If any admin, legacy, or profile family is missing.

    """
    referenced: set[str] = set(ADMIN_FAMILIES) | set(LEGACY_FAMILIES)
    for profile in TOOL_PROFILES:
        referenced.update(profile.families)

    missing = sorted(referenced - available)
    if missing:
        names = ", ".join(missing)
        message = f"Configured tool families missing from the API spec: {names}"
        raise ToolSelectionError(message)


def _validate_no_overlap(
    enabled: set[str],
    disabled: set[str],
    *,
    kind: str,
) -> None:
    overlap = sorted(enabled & disabled)
    if not overlap:
        return

    names = ", ".join(overlap)
    message = f"Conflicting {kind} enable and disable entries: {names}"
    raise ToolSelectionError(message)


def _disabled_reason(
    operation: OperationSpec,
    settings: Settings,
    selected_families: set[str],
) -> str | None:
    if operation.tag not in selected_families:
        return f"family `{operation.tag}` is not selected"
    if operation.tag in ADMIN_FAMILIES and not settings.enable_admin_tools:
        return "admin tool families are disabled"
    if operation.tag in LEGACY_FAMILIES and not settings.enable_legacy_tools:
        return "legacy tool families are disabled"
    if operation.method in DESTRUCTIVE_METHODS:
        if not settings.enable_destructive_tools:
            return "destructive tools are disabled"
    elif operation.method in WRITE_METHODS and not settings.enable_write_tools:
        return "write tools are disabled"
    return None


def build_tool_selection(spec: LangfuseAPISpec, settings: Settings) -> ToolSelection:
    """Build the enabled MCP tool set for the provided settings."""
    available_families = {operation.tag for operation in spec.operations}
    _validate_known_families(available_families)
    available_tool_names = set(spec.by_tool_name)

    families_enable = _resolve_requested_families(settings.tool_families_enable, available_families)
    families_disable = _resolve_requested_families(
        settings.tool_families_disable,
        available_families,
    )
    _validate_no_overlap(families_enable, families_disable, kind="family")

    selected_families = _resolve_profile_families(settings.tool_profiles, available_families)
    selected_families.update(families_enable)
    selected_families.difference_update(families_disable)

    enabled_tools = _resolve_requested_tools(settings.tools_enable, available_tool_names)
    disabled_tools = _resolve_requested_tools(settings.tools_disable, available_tool_names)
    _validate_no_overlap(enabled_tools, disabled_tools, kind="tool")

    enabled_operations: list[OperationSpec] = []
    disabled_reasons: dict[str, str] = {}
    gate_overrides: dict[str, str] = {}

    for operation in spec.operations:
        if operation.tool_name in disabled_tools:
            disabled_reasons[operation.tool_name] = "tool is explicitly disabled"
            continue

        if operation.tool_name in enabled_tools:
            reason = _disabled_reason(operation, settings, selected_families)
            if reason is not None:
                gate_overrides[operation.tool_name] = reason
            enabled_operations.append(operation)
            continue

        reason = _disabled_reason(operation, settings, selected_families)
        if reason is None:
            enabled_operations.append(operation)
            continue

        disabled_reasons[operation.tool_name] = reason

    return ToolSelection(
        enabled_operations=tuple(enabled_operations),
        enabled_by_name={operation.tool_name: operation for operation in enabled_operations},
        disabled_reasons=disabled_reasons,
        selected_families=frozenset(selected_families),
        gate_overrides=gate_overrides,
    )


def describe_profiles(spec: LangfuseAPISpec) -> tuple[DocumentedProfile, ...]:
    """Return profile descriptions with tool counts for documentation."""
    all_families = {operation.tag for operation in spec.operations}
    documented: list[DocumentedProfile] = []

    for profile in TOOL_PROFILES:
        if profile.name == "full":
            families = tuple(sorted(all_families))
        else:
            families = tuple(family for family in profile.families if family in all_families)

        family_set = set(families)
        tool_count = sum(1 for operation in spec.operations if operation.tag in family_set)
        documented.append(
            DocumentedProfile(
                name=profile.name,
                description=profile.description,
                families=families,
                tool_count=tool_count,
            )
        )

    return tuple(documented)
