"""Shared pytest fixtures and helpers for mcp-langfuse tests."""

from __future__ import annotations

from typing import Any

from mcp_langfuse.config import Settings


def make_settings(**overrides: Any) -> Settings:
    """Create a Settings instance with required auth stubs and optional overrides.

    Args:
        **overrides: Additional Settings field values passed via alias name.

    Returns:
        A fully configured Settings instance suitable for tests.

    """
    values: dict[str, Any] = {
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
    }
    values.update(overrides)
    return Settings(**values)
