"""Catalog schema integrity tests for docs/reference/github-repos.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

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


class TypeProfile(TypedDict):
    """A single type profile entry from _meta.typeProfiles."""

    description: str
    exemptWorkflows: list[str]
    exemptHooks: list[str]


class IdealEntryWorkflows(TypedDict):
    """Workflow-related fields from _meta.idealEntry."""

    presentFromExpected: list[str]


class IdealEntryPreCommit(TypedDict):
    """Pre-commit fields from _meta.idealEntry."""

    hooks: dict[str, object]


class CatalogMeta(TypedDict):
    """The _meta block of the catalog JSON."""

    typeProfiles: dict[str, TypeProfile]
    idealEntry: dict[str, object]


class Catalog(TypedDict):
    """Top-level structure of docs/reference/github-repos.json."""

    _meta: CatalogMeta
    repos: list[dict[str, object]]


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    """Load and return the catalog JSON."""
    return cast("Catalog", json.loads(CATALOG.read_text()))


@pytest.fixture(scope="module")
def repo_entries(catalog: Catalog) -> list[dict[str, object]]:
    """Return all repo entries from the repos array."""
    return catalog["repos"]


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
def test_type_profiles_cover_all_types(catalog: Catalog) -> None:
    """typeProfiles in _meta must define all valid taxonomy types."""
    defined = set(catalog["_meta"]["typeProfiles"].keys())
    assert defined == VALID_TYPES, f"Profile mismatch: {defined ^ VALID_TYPES}"


@pytest.mark.unit
def test_exempt_workflows_are_valid(catalog: Catalog) -> None:
    """All exempted workflows must be in idealEntry.workflows.presentFromExpected."""
    ideal_workflows = cast(
        "IdealEntryWorkflows", catalog["_meta"]["idealEntry"]["workflows"]
    )
    all_workflows = set(ideal_workflows["presentFromExpected"])
    for type_name, profile in catalog["_meta"]["typeProfiles"].items():
        invalid = [w for w in profile["exemptWorkflows"] if w not in all_workflows]
        assert not invalid, f"{type_name} exempts invalid workflows: {invalid}"


@pytest.mark.unit
def test_exempt_hooks_are_valid(catalog: Catalog) -> None:
    """All exempted hooks must be in idealEntry.preCommit.hooks."""
    ideal_precommit = cast(
        "IdealEntryPreCommit", catalog["_meta"]["idealEntry"]["preCommit"]
    )
    all_hooks = set(ideal_precommit["hooks"].keys())
    for type_name, profile in catalog["_meta"]["typeProfiles"].items():
        invalid = [h for h in profile["exemptHooks"] if h not in all_hooks]
        assert not invalid, f"{type_name} exempts invalid hooks: {invalid}"


@pytest.mark.unit
def test_no_dependabot_field(repo_entries: list[dict[str, object]]) -> None:
    """dependabot must be replaced by renovate in all entries."""
    has_dependabot = [
        f"{e.get('org', '?')}/{e.get('name', '?')}"
        for e in repo_entries
        if "dependabot" in cast("dict[str, object]", e.get("review", {}))
    ]
    assert not has_dependabot, f"Still using dependabot: {has_dependabot}"


@pytest.mark.unit
def test_all_entries_have_renovate(repo_entries: list[dict[str, object]]) -> None:
    """Every catalog entry must have a renovate field."""
    missing = [
        f"{e.get('org', '?')}/{e.get('name', '?')}"
        for e in repo_entries
        if "renovate" not in cast("dict[str, object]", e.get("review", {}))
    ]
    assert not missing, f"Missing renovate field on: {missing}"


@pytest.mark.unit
def test_all_entries_have_secret_scanning(
    repo_entries: list[dict[str, object]],
) -> None:
    """Every catalog entry must have a secretScanning field."""
    missing = [
        f"{e.get('org', '?')}/{e.get('name', '?')}"
        for e in repo_entries
        if "secretScanning" not in cast("dict[str, object]", e.get("review", {}))
    ]
    assert not missing, f"Missing secretScanning field on: {missing}"


@pytest.mark.unit
def test_all_entries_have_release_health(repo_entries: list[dict[str, object]]) -> None:
    """Every catalog entry must have a releaseHealth field in review."""
    missing = [
        f"{e.get('org', '?')}/{e.get('name', '?')}"
        for e in repo_entries
        if "releaseHealth" not in cast("dict[str, object]", e.get("review", {}))
    ]
    assert not missing, f"Missing releaseHealth field on: {missing}"


@pytest.mark.unit
def test_all_entries_have_template_drift(repo_entries: list[dict[str, object]]) -> None:
    """Every catalog entry must have a templateDrift field in review."""
    missing = [
        f"{e.get('org', '?')}/{e.get('name', '?')}"
        for e in repo_entries
        if "templateDrift" not in cast("dict[str, object]", e.get("review", {}))
    ]
    assert not missing, f"Missing templateDrift field on: {missing}"


@pytest.mark.unit
def test_enable_secret_scanning_script_exists() -> None:
    """The secret scanning enablement script must exist and be executable."""
    script = Path(__file__).parents[2] / "tools" / "enable_secret_scanning.py"
    assert script.exists(), "tools/enable_secret_scanning.py not found"
    assert script.stat().st_mode & 0o111, "Script must be executable"


@pytest.mark.unit
def test_refresh_catalog_release_health_script_exists() -> None:
    """The release health refresh script must exist and be executable."""
    script = Path(__file__).parents[2] / "tools" / "refresh_catalog_release_health.py"
    assert script.exists(), "tools/refresh_catalog_release_health.py not found"
    assert script.stat().st_mode & 0o111, "Script must be executable"
