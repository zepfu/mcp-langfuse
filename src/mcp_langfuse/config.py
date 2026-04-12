"""Configuration for the Langfuse MCP server."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Self

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TOOL_PROFILES = ("minimal",)


def _parse_csv_values(raw: object) -> tuple[str, ...]:
    """Parse comma-separated or iterable config values into a normalized tuple."""
    if raw is None:
        return ()

    if isinstance(raw, str):
        items = raw.split(",")
    elif isinstance(raw, Iterable):
        items = [str(item) for item in raw]
    else:
        items = [str(raw)]

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
    secret_key: str = Field(alias="LANGFUSE_SECRET_KEY")
    timeout_seconds: float = Field(default=30.0, alias="LANGFUSE_TIMEOUT_SECONDS", gt=0)
    verify_ssl: bool = Field(default=True, alias="LANGFUSE_VERIFY_SSL")
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
        """Allow env vars and direct init values to use CSV strings or iterables."""
        return _parse_csv_values(raw)

    @classmethod
    def from_env(cls) -> Self:
        """Load settings from the current environment."""
        return cls()  # type: ignore[call-arg]
