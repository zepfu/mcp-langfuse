"""Configuration for the Langfuse MCP server."""

from __future__ import annotations

from pydantic import AnyHttpUrl, Field, SecretStr, TypeAdapter, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TOOL_PROFILES = ("minimal",)
HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)

_CSV_SEQUENCE_TYPES = (list, tuple, set, frozenset)


def _parse_csv_values(raw: object) -> tuple[str, ...]:
    """Parse comma-separated or sequence config values into a normalized tuple.

    Args:
        raw: A CSV string, a sequence of strings, or ``None``.

    Returns:
        A deduplicated tuple of trimmed, non-empty string values.

    Raises:
        ValueError: If ``raw`` is bytes/bytearray or an unsupported type.

    """
    if raw is None:
        return ()

    if isinstance(raw, str):
        items = raw.split(",")
    elif isinstance(raw, _CSV_SEQUENCE_TYPES):
        items = [str(item) for item in raw]
    else:
        # ValueError (not TypeError) so pydantic wraps it into a ValidationError.
        message = "CSV value must be a string or a sequence of strings"
        raise ValueError(message)  # noqa: TRY004

    normalized = [item.strip() for item in items if item.strip()]
    return tuple(dict.fromkeys(normalized))


class Settings(BaseSettings):
    """Environment-backed Langfuse client settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    base_url: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_BASE_URL")
    public_key: str = Field(alias="LANGFUSE_PUBLIC_KEY")
    secret_key: SecretStr = Field(alias="LANGFUSE_SECRET_KEY")
    timeout_seconds: float = Field(default=30.0, alias="LANGFUSE_TIMEOUT_SECONDS", gt=0)
    verify_ssl: bool = Field(default=True, alias="LANGFUSE_VERIFY_SSL")
    retry_attempts: int = Field(default=2, ge=0, le=10, alias="LANGFUSE_RETRY_ATTEMPTS")
    max_response_bytes: int = Field(
        default=200_000,
        gt=0,
        alias="LANGFUSE_MAX_RESPONSE_BYTES",
    )
    tool_profiles: tuple[str, ...] = Field(
        default=DEFAULT_TOOL_PROFILES,
        alias="LANGFUSE_TOOL_PROFILES",
    )
    tool_families_enable: tuple[str, ...] = Field(
        default=(),
        alias="LANGFUSE_TOOL_FAMILIES_ENABLE",
    )
    tool_families_disable: tuple[str, ...] = Field(
        default=(),
        alias="LANGFUSE_TOOL_FAMILIES_DISABLE",
    )
    tools_enable: tuple[str, ...] = Field(default=(), alias="LANGFUSE_TOOLS_ENABLE")
    tools_disable: tuple[str, ...] = Field(default=(), alias="LANGFUSE_TOOLS_DISABLE")
    enable_write_tools: bool = Field(default=False, alias="LANGFUSE_ENABLE_WRITE_TOOLS")
    enable_destructive_tools: bool = Field(
        default=False,
        alias="LANGFUSE_ENABLE_DESTRUCTIVE_TOOLS",
    )
    enable_admin_tools: bool = Field(default=False, alias="LANGFUSE_ENABLE_ADMIN_TOOLS")
    enable_legacy_tools: bool = Field(default=False, alias="LANGFUSE_ENABLE_LEGACY_TOOLS")

    @field_validator(
        "tool_profiles",
        "tool_families_enable",
        "tool_families_disable",
        "tools_enable",
        "tools_disable",
        mode="before",
    )
    @classmethod
    def _normalize_csv_fields(cls, raw: object) -> tuple[str, ...]:
        """Allow env vars and direct init values to use CSV strings or sequences."""
        return _parse_csv_values(raw)

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, raw: str) -> str:
        """Require an absolute HTTP(S) base URL and strip any trailing slash."""
        return str(HTTP_URL_ADAPTER.validate_python(raw)).rstrip("/")


KNOWN_ENV_VARS: frozenset[str] = frozenset(
    field.alias for field in Settings.model_fields.values() if field.alias
)
