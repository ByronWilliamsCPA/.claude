"""Catalog schema integrity tests for docs/reference/github-repos.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CATALOG = Path(__file__).parents[2] / "docs" / "reference" / "github-repos.json"
VALID_TYPES = {
    "python-package",
    "python-app",
    "python-script",
    "config",
    "infrastructure",
    "docs-only",
    "template",
}


@pytest.fixture(scope="module")
def catalog() -> dict[str, object]:
    """Load and return the catalog JSON."""
    return json.loads(CATALOG.read_text())  # type: ignore[return-value]


@pytest.fixture(scope="module")
def repo_entries(catalog: dict[str, object]) -> list[dict[str, object]]:
    """Return all repo entries from the repos array."""
    return catalog["repos"]  # type: ignore[return-value]


@pytest.mark.unit
def test_all_entries_have_repository_type(
    repo_entries: list[dict[str, object]],
) -> None:
    """Every catalog entry must have a repositoryType field."""
    missing = [
        f"{e.get('org', '?')}/{e.get('name', '?')}"
        for e in repo_entries
        if "repositoryType" not in e
    ]
    assert not missing, f"Missing repositoryType on: {missing}"


@pytest.mark.unit
def test_all_repository_types_are_valid(repo_entries: list[dict[str, object]]) -> None:
    """repositoryType must be one of the defined taxonomy values."""
    invalid = [
        f"{e.get('org', '?')}/{e.get('name', '?')}: {e.get('repositoryType', '<missing>')}"
        for e in repo_entries
        if e.get("repositoryType") not in VALID_TYPES
    ]
    assert not invalid, f"Invalid repositoryType values: {invalid}"


@pytest.mark.unit
def test_type_profiles_cover_all_types(catalog: dict[str, object]) -> None:
    """typeProfiles in _meta must define all valid taxonomy types."""
    defined = set(catalog["_meta"]["typeProfiles"].keys())  # type: ignore[index]
    assert defined == VALID_TYPES, f"Profile mismatch: {defined ^ VALID_TYPES}"


@pytest.mark.unit
def test_exempt_workflows_are_valid(catalog: dict[str, object]) -> None:
    """All exempted workflows must be in idealEntry.workflows.presentFromExpected."""
    all_workflows = set(
        catalog["_meta"]["idealEntry"]["workflows"]["presentFromExpected"]  # type: ignore[index]
    )
    for type_name, profile in catalog["_meta"]["typeProfiles"].items():  # type: ignore[union-attr]
        invalid = [w for w in profile["exemptWorkflows"] if w not in all_workflows]  # type: ignore[index]
        assert not invalid, f"{type_name} exempts invalid workflows: {invalid}"


@pytest.mark.unit
def test_exempt_hooks_are_valid(catalog: dict[str, object]) -> None:
    """All exempted hooks must be in idealEntry.preCommit.hooks."""
    all_hooks = set(catalog["_meta"]["idealEntry"]["preCommit"]["hooks"].keys())  # type: ignore[index]
    for type_name, profile in catalog["_meta"]["typeProfiles"].items():  # type: ignore[union-attr]
        invalid = [h for h in profile["exemptHooks"] if h not in all_hooks]  # type: ignore[index]
        assert not invalid, f"{type_name} exempts invalid hooks: {invalid}"
