"""Tests for scripts/populate-github-repos.py.

The script merges live `gh repo list` output into the existing catalog while
preserving every manual annotation. The core invariant tested here is that
annotation fields (repositoryType, branchProtectionExempt, migrationPhase,
usesDocker, servesApi, review.*, api.*) survive a round-trip even when the
live GitHub fields change.
"""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.unit._load_populate_github_repos import load_module

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

CATALOG_META: dict[str, Any] = {
    "linkedDoc": "docs/reference/repo-type-taxonomy.md",
    "lastUpdated": "2026-05-14",
    "idealEntry": {"_note": "ideal target state"},
}


def _seed_catalog() -> dict[str, Any]:
    """Return a fixture catalog with one BW repo and one williaby repo."""
    return {
        "_meta": copy.deepcopy(CATALOG_META),
        "repos": [
            {
                "org": "ByronWilliamsCPA",
                "repositoryType": "python-app",
                "name": "alpha",
                "url": "https://github.com/ByronWilliamsCPA/alpha",
                "defaultBranch": "main",
                "description": "old description",
                "isPrivate": False,
                "isArchived": False,
                "migrationPhase": "complete",
                "servesApi": True,
                "api": {
                    "openApiSpec": "docs/api/openapi.yaml",
                    "postmanCollection": "docs/api/postman-collection.json",
                    "lastAudited": "2026-04-01",
                    "testStatus": "passing",
                },
                "review": {
                    "scorecard": {"score": 7.6, "lastChecked": "2026-04-28"},
                },
            },
            {
                "org": "williaby",
                "repositoryType": "python-package",
                "name": "zeta",
                "url": "https://github.com/williaby/zeta",
                "defaultBranch": "main",
                "description": "old williaby description",
                "isPrivate": False,
                "isArchived": False,
                "branchProtectionExempt": True,
                "review": {"renovate": {"configured": True}},
            },
        ],
    }


def _gh_response_for(
    org: str, names_with_live_fields: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Shape a list of dicts to match `gh repo list <org> --json ...` output."""
    return [
        {
            "name": entry["name"],
            "url": f"https://github.com/{org}/{entry['name']}",
            "defaultBranchRef": {"name": entry.get("defaultBranch", "main")},
            "description": entry.get("description", ""),
            "isPrivate": entry.get("isPrivate", False),
            "isArchived": entry.get("isArchived", False),
        }
        for entry in names_with_live_fields
    ]


@pytest.fixture
def fake_gh(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[dict[str, Any]]]:
    """Replace fetch_org_repos with an in-memory dict lookup keyed by org slug."""
    module = load_module()
    responses: dict[str, list[dict[str, Any]]] = {}

    def _fake_fetch(org: str) -> list[dict[str, Any]]:
        if org not in responses:
            msg = f"No fake gh response configured for org {org!r}"
            raise KeyError(msg)
        return responses[org]

    monkeypatch.setattr(module, "fetch_org_repos", _fake_fetch)
    return responses


def test_round_trip_preserves_annotations(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """Annotations must survive a refresh even when live fields change."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [
            {
                "name": "alpha",
                "description": "new description from github",
                "isArchived": True,
            }
        ],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [{"name": "zeta", "description": "new williaby description"}],
    )

    changed = module.refresh_catalog(catalog_path, prune=False)

    assert changed is True, "Catalog should report changes when live fields differ"

    refreshed = json.loads(catalog_path.read_text(encoding="utf-8"))
    alpha = next(r for r in refreshed["repos"] if r["name"] == "alpha")
    zeta = next(r for r in refreshed["repos"] if r["name"] == "zeta")

    # Live fields updated; description is preserved as a manual annotation.
    assert alpha["description"] == "old description", (
        "description must be preserved as a manual annotation, not overwritten"
    )
    assert alpha["isArchived"] is True
    assert zeta["description"] == "old williaby description"

    # Annotations preserved byte-for-byte.
    assert alpha["repositoryType"] == "python-app"
    assert alpha["migrationPhase"] == "complete"
    assert alpha["servesApi"] is True
    assert alpha["api"] == _seed_catalog()["repos"][0]["api"]
    assert alpha["review"] == _seed_catalog()["repos"][0]["review"]
    assert zeta["branchProtectionExempt"] is True
    assert zeta["review"] == _seed_catalog()["repos"][1]["review"]

    # _meta is unchanged.
    assert refreshed["_meta"] == CATALOG_META


def test_new_repo_gets_skeleton_entry(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """A repo present on GitHub but missing from the catalog gets added."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [
            {"name": "alpha", "description": "old description"},
            {"name": "brand-new", "description": "fresh repo"},
        ],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [{"name": "zeta", "description": "old williaby description"}],
    )

    module.refresh_catalog(catalog_path, prune=False)

    refreshed = json.loads(catalog_path.read_text(encoding="utf-8"))
    names = [r["name"] for r in refreshed["repos"]]
    assert "brand-new" in names

    new_entry = next(r for r in refreshed["repos"] if r["name"] == "brand-new")
    assert new_entry["org"] == "ByronWilliamsCPA"
    assert new_entry["repositoryType"] == "unclassified"
    assert new_entry["description"] == "fresh repo"


def test_prune_removes_deleted_repo(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """With --prune, repos missing from GitHub are removed; without, kept."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [{"name": "alpha", "description": "old description"}],
    )
    # zeta is missing from williaby's live response, but another williaby
    # repo is present so the org doesn't trip the empty-response prune guard.
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [{"name": "other", "description": "still here"}],
    )

    module.refresh_catalog(catalog_path, prune=False)
    kept = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert any(r["name"] == "zeta" for r in kept["repos"]), (
        "Default (no --prune) must keep deleted-from-github entries intact"
    )

    # Re-write seed and run with prune=True.
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )
    module.refresh_catalog(catalog_path, prune=True)
    pruned = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert not any(r["name"] == "zeta" for r in pruned["repos"]), (
        "--prune must remove repos absent from live response"
    )


def test_no_changes_returns_false(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """When live data matches catalog exactly, refresh_catalog returns False."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    seed = _seed_catalog()
    catalog_path.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [
            {
                "name": "alpha",
                "description": "old description",
                "isPrivate": False,
                "isArchived": False,
            }
        ],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [
            {
                "name": "zeta",
                "description": "old williaby description",
                "isPrivate": False,
                "isArchived": False,
            }
        ],
    )

    changed = module.refresh_catalog(catalog_path, prune=False)
    assert changed is False


def test_sort_order_is_case_insensitive_by_org_then_name(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """Repos sort by (org, name.lower()); cross-org ordering matches existing layout."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps({"_meta": {}, "repos": []}, indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [
            {"name": "DeQA-Doc"},
            {"name": ".claude"},
            {"name": "audio-processor"},
        ],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [
            {"name": "Zeppelin"},
            {"name": "alpha-tool"},
        ],
    )

    module.refresh_catalog(catalog_path, prune=False)

    out = json.loads(catalog_path.read_text(encoding="utf-8"))
    pairs = [(r["org"], r["name"]) for r in out["repos"]]
    # All ByronWilliamsCPA entries must sort before any williaby entry; within
    # each org, names sort case-insensitively. A regression that swapped the
    # tuple to (name.lower(), org) would interleave the two orgs.
    assert pairs == [
        ("ByronWilliamsCPA", ".claude"),
        ("ByronWilliamsCPA", "audio-processor"),
        ("ByronWilliamsCPA", "DeQA-Doc"),
        ("williaby", "alpha-tool"),
        ("williaby", "Zeppelin"),
    ], f"Cross-org sort regression. Got: {pairs}"


def test_new_repo_reports_changed_true(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """Adding a new repo must mark the catalog as changed."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [
            {"name": "alpha", "description": "old description"},
            {"name": "brand-new", "description": "fresh repo"},
        ],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [{"name": "zeta", "description": "old williaby description"}],
    )

    changed = module.refresh_catalog(catalog_path, prune=False)
    assert changed is True


def test_empty_description_is_preserved(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """An existing entry with description="" must not be refilled from live."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    seed = _seed_catalog()
    # Deliberately blank zeta's description to suppress display.
    for repo in seed["repos"]:
        if repo["name"] == "zeta":
            repo["description"] = ""
    catalog_path.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [{"name": "alpha", "description": "old description"}],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [{"name": "zeta", "description": "github would set this"}],
    )

    module.refresh_catalog(catalog_path, prune=False)

    refreshed = json.loads(catalog_path.read_text(encoding="utf-8"))
    zeta = next(r for r in refreshed["repos"] if r["name"] == "zeta")
    assert zeta["description"] == "", (
        'Deliberately empty "description": "" must be preserved, not refilled'
    )


def test_main_returns_zero_and_prints_status(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() returns 0 and prints an unambiguous status message."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [
            {
                "name": "alpha",
                "description": "old description",
                "isPrivate": False,
                "isArchived": False,
            }
        ],
    )
    fake_gh["williaby"] = _gh_response_for(
        "williaby",
        [
            {
                "name": "zeta",
                "description": "old williaby description",
                "isPrivate": False,
                "isArchived": False,
            }
        ],
    )

    rc = module.main(["--catalog", str(catalog_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "is up to date" in captured.out


def test_prune_refuses_empty_org_without_allow_empty(
    tmp_path: Path,
    fake_gh: dict[str, list[dict[str, Any]]],
) -> None:
    """--prune must refuse when an org returns zero repos unless --allow-empty."""
    module = load_module()
    catalog_path = tmp_path / "github-repos.json"
    catalog_path.write_text(
        json.dumps(_seed_catalog(), indent=2) + "\n", encoding="utf-8"
    )

    fake_gh["ByronWilliamsCPA"] = _gh_response_for(
        "ByronWilliamsCPA",
        [{"name": "alpha", "description": "old description"}],
    )
    fake_gh["williaby"] = []  # Simulate token-scope loss for williaby.

    with pytest.raises(SystemExit) as exc:
        module.refresh_catalog(catalog_path, prune=True)
    assert "williaby" in str(exc.value)
    # The original zeta entry must still be on disk after the refusal.
    after = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert any(r["name"] == "zeta" for r in after["repos"])

    # With allow_empty, prune proceeds and zeta is removed.
    module.refresh_catalog(catalog_path, prune=True, allow_empty=True)
    pruned = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert not any(r["name"] == "zeta" for r in pruned["repos"])
