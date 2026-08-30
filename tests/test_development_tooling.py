"""Static checks for development tooling configuration."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_toml() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def _load_pre_commit() -> dict[str, Any]:
    with (REPO_ROOT / ".pre-commit-config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_dependency_groups_and_uv_sources_contracts() -> None:
    data = _load_toml()
    project = data["project"]
    project_dependencies = project["dependencies"]
    optional_dependencies = project.get("optional-dependencies", {})
    dev_dependencies = data["dependency-groups"]["dev"]

    for tool in ("pytest-classifier", "pytest-testable"):
        assert tool not in project_dependencies
        assert all(tool not in dependencies for dependencies in optional_dependencies.values())
        assert tool in dev_dependencies

    assert "aawm-observe" not in project_dependencies
    assert all(
        "aawm-observe" not in dependencies for dependencies in optional_dependencies.values()
    )
    assert "aawm-observe" not in dev_dependencies

    sources = data["tool"]["uv"]["sources"]
    classifier_source = sources["pytest-classifier"]
    testable_source = sources["pytest-testable"]
    assert classifier_source["git"] == "https://github.com/zepfu/pytest-classifier.git"
    assert classifier_source["rev"] == "55095644184147600c2ddd23237c952a27928054"
    assert testable_source["git"] == "https://github.com/zepfu/pytest-testable.git"
    assert testable_source["rev"] == "6858b18544c0a6a3c7d8823382aeda8cd6092ce8"
    assert "editable" not in classifier_source
    assert "editable" not in testable_source
    assert "path" not in classifier_source
    assert "path" not in testable_source


def test_pytest_and_classifier_tooling_contracts() -> None:
    data = _load_toml()
    pytest_opts = data["tool"]["pytest"]["ini_options"]
    normal_addopts = pytest_opts.get("addopts", "")
    assert "--classify" not in normal_addopts
    assert "--testable" not in normal_addopts

    classifier = data["tool"]["pytest-classifier"]
    assert classifier["src_root"] == "src/mcp_langfuse"
    assert classifier["tests_root"] == "tests"
    assert classifier["mode"] == "error"
    assert classifier["use_testable"] is False


def test_pre_commit_hooks_contracts() -> None:
    config = _load_pre_commit()
    assert set(config["default_install_hook_types"]) == {
        "pre-commit",
        "post-commit",
        "post-merge",
    }

    local_hooks = {}
    for repo in config["repos"]:
        if repo.get("repo") != "local":
            continue
        for hook in repo["hooks"]:
            local_hooks[hook["id"]] = hook

    precommit = local_hooks["precommit"]
    expected_precommit = (
        "env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE uv run --frozen pytest "
        "precommit --classify"
    )
    assert precommit["entry"] == expected_precommit
    assert "precommit --classify" in precommit["entry"]
    assert precommit["stages"] == ["pre-commit"]
    assert precommit["pass_filenames"] is False

    postcommit = local_hooks["postcommit"]
    assert postcommit["entry"] == "uv run --frozen pytest --rootdir . -o addopts= postcommit"
    assert postcommit["pass_filenames"] is False
    assert postcommit["always_run"] is True
    assert postcommit["stages"] == ["post-commit", "post-merge"]


def test_classifier_artifact_roots_are_ignored() -> None:
    ignored = subprocess.run(
        ["git", "check-ignore", "--", ".pytest-classifier/", ".testable-artifacts/"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    assert ignored.stdout.splitlines() == [".pytest-classifier/", ".testable-artifacts/"]
