"""Unit tests for config.py — Settings hardening (Wave 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_base_url_strips_trailing_slash() -> None:
    # URL without trailing slash stays unchanged
    settings = make_settings(LANGFUSE_BASE_URL="https://x.example")
    assert settings.base_url == "https://x.example"

    # URL with trailing slash has it stripped
    settings2 = make_settings(LANGFUSE_BASE_URL="https://x.example/sub/")
    assert settings2.base_url == "https://x.example/sub"


def test_base_url_rejects_non_http() -> None:
    with pytest.raises(ValidationError):
        make_settings(LANGFUSE_BASE_URL="ftp://x")


def test_secret_key_is_masked() -> None:
    settings = make_settings(LANGFUSE_SECRET_KEY="sk-test")
    # repr and str should NOT contain the raw secret
    assert "sk-test" not in repr(settings)
    assert "sk-test" not in str(settings)
    # But get_secret_value() should return it
    assert settings.secret_key.get_secret_value() == "sk-test"  # type: ignore[union-attr]


def test_csv_rejects_bytes() -> None:
    with pytest.raises(ValidationError):
        make_settings(LANGFUSE_TOOL_PROFILES=b"minimal")


def test_csv_accepts_list_and_dedupes() -> None:
    settings = make_settings(LANGFUSE_TOOL_PROFILES=["a", "b", "a", " b "])
    assert settings.tool_profiles == ("a", "b")


def test_empty_profiles_yields_empty_tuple() -> None:
    settings = make_settings(LANGFUSE_TOOL_PROFILES="")
    assert settings.tool_profiles == ()


def test_retry_and_response_byte_defaults() -> None:
    settings = make_settings()
    assert settings.retry_attempts == 2  # type: ignore[attr-defined]
    assert settings.max_response_bytes == 200_000  # type: ignore[attr-defined]

    with pytest.raises(ValidationError):
        make_settings(LANGFUSE_RETRY_ATTEMPTS=-1)

    with pytest.raises(ValidationError):
        make_settings(LANGFUSE_MAX_RESPONSE_BYTES=0)


def test_missing_required_keys_name_env_vars() -> None:
    from mcp_langfuse.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings()  # type: ignore[call-arg]

    error_msg = str(exc_info.value)
    assert "LANGFUSE_PUBLIC_KEY" in error_msg
    assert "LANGFUSE_SECRET_KEY" in error_msg
