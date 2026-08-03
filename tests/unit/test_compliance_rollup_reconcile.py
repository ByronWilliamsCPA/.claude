# tests/unit/test_compliance_rollup_reconcile.py
"""Tests for the rollup reconcile script's per-repo parser and walker."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_LESSONS = """\
# Compliance Retrospective: 2026-05-16

## Session Summary

| Metric | Value |
|--------|-------|
| Repos reviewed | 1 |
| Total findings (net of overrides) | 10 |
| Critical | 0 |
| Important | 3 |
| Suggested | 7 |
| Unclassified candidates | 2 |

## Patterns Observed

- ".editorconfig absent" -- 1 of 1 repo

## Proposed Manifest Additions

```yaml
- id: FOUND-012
  domain: foundations
  severity: suggested
  description: ".editorconfig absent from project root"
  verify: "file_exists: .editorconfig"
  override_eligible: true
```

## Agent Scope Expansion Candidates

- python-toolchain-auditor: consider adding interrogate threshold check

## High-Frequency Existing Checks

- FOUND-008: 1 of 1 repo
- CI-005: 1 of 1 repo

## Fleet-Wide Actions Required

No fleet-wide patterns detected.
"""


def test_parse_lessons_learned_extracts_totals(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import parse_lessons_learned

    f = tmp_path / "2026-05-16.md"
    f.write_text(SAMPLE_LESSONS)

    parsed = parse_lessons_learned(f, tmp_path)

    assert parsed["session_date"] == "2026-05-16"
    assert parsed["totals"]["critical"] == 0
    assert parsed["totals"]["important"] == 3
    assert parsed["totals"]["suggested"] == 7
    assert parsed["totals"]["unclassified_candidates"] == 2


def test_parse_extracts_findings_by_check_ids(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import parse_lessons_learned

    f = tmp_path / "2026-05-16.md"
    f.write_text(SAMPLE_LESSONS)

    parsed = parse_lessons_learned(f, tmp_path)

    ids = [c["id"] for c in parsed["findings_by_check"]]
    assert "FOUND-008" in ids
    assert "CI-005" in ids


def test_parse_extracts_unclassified_candidate_ids(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import parse_lessons_learned

    f = tmp_path / "2026-05-16.md"
    f.write_text(SAMPLE_LESSONS)

    parsed = parse_lessons_learned(f, tmp_path)

    proposed_ids = [
        c["proposed_manifest_id"] for c in parsed["unclassified_candidates"]
    ]
    assert "FOUND-012" in proposed_ids


def test_parse_handles_missing_optional_sections(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import parse_lessons_learned

    minimal = (
        "# Compliance Retrospective: 2026-05-16\n\n"
        "## Session Summary\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| Repos reviewed | 1 |\n"
    )
    f = tmp_path / "2026-05-16.md"
    f.write_text(minimal)

    parsed = parse_lessons_learned(f, tmp_path)

    assert parsed["session_date"] == "2026-05-16"
    assert parsed["findings_by_check"] == []
    assert parsed["unclassified_candidates"] == []


def test_parse_raises_on_invalid_filename(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import (
        InvalidRetrospectiveError,
        parse_lessons_learned,
    )

    f = tmp_path / "not-a-date.md"
    f.write_text("# x\n")

    with pytest.raises(InvalidRetrospectiveError):
        parse_lessons_learned(f, tmp_path)


def test_parse_links_lessons_learned_is_repo_relative(tmp_path: Path) -> None:
    """Regression test for finding #4 (absolute path leak).

    The Copilot PR review flagged that ``links.lessons_learned`` was
    being stored as the operator's absolute path (``/home/byron/dev/...``)
    and committed into the master log. This test pins the contract that
    the captured link is repo-relative to the clone root.
    """
    from scripts.compliance_rollup_reconcile import parse_lessons_learned

    clone = tmp_path / "some-repo"
    lessons_dir = clone / "docs" / "compliance-reports" / "lessons-learned"
    lessons_dir.mkdir(parents=True)
    f = lessons_dir / "2026-05-16.md"
    f.write_text(SAMPLE_LESSONS)

    parsed = parse_lessons_learned(f, clone)

    assert (
        parsed["links"]["lessons_learned"]
        == "docs/compliance-reports/lessons-learned/2026-05-16.md"
    )
    # No absolute path component leaks into the entry.
    assert str(tmp_path) not in parsed["links"]["lessons_learned"]


def test_parse_block_scalar_description_extracted_as_text(tmp_path: Path) -> None:
    """Regression test for finding #5 (YAML block scalar captured literal).

    The previous regex-based parser stored ``description: >-`` as the
    literal token ``">-"`` instead of the actual description text. This
    test pins that ``yaml.safe_load`` is now used so block scalars
    resolve to their content.
    """
    from scripts.compliance_rollup_reconcile import parse_lessons_learned

    body = (
        "# Compliance Retrospective: 2026-05-16\n\n"
        "## Proposed Manifest Additions\n\n"
        "```yaml\n"
        "- id: FOUND-099\n"
        "  domain: foundations\n"
        "  severity: suggested\n"
        "  description: >-\n"
        "    Multi-line description text\n"
        "    that spans block-scalar lines.\n"
        '  verify: "file_exists: .editorconfig"\n'
        "  override_eligible: true\n"
        "```\n"
    )
    f = tmp_path / "2026-05-16.md"
    f.write_text(body)

    parsed = parse_lessons_learned(f, tmp_path)
    candidates = parsed["unclassified_candidates"]

    assert len(candidates) == 1
    pattern = candidates[0]["pattern"]
    assert "Multi-line description text" in pattern
    assert pattern != ">-"
    assert ">-" not in pattern


def test_repo_local_path_resolves_with_slug_normalization(
    tmp_path: Path,
) -> None:
    from scripts.compliance_rollup_reconcile import resolve_local_clone

    (tmp_path / "audio_processor").mkdir()

    result = resolve_local_clone("audio-processor", tmp_path)

    assert result == tmp_path / "audio_processor"


def test_repo_local_path_returns_none_when_missing(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import resolve_local_clone

    assert resolve_local_clone("nonexistent-repo", tmp_path) is None


def test_reconcile_dedupe_skips_known_keys(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import reconcile

    jsonl = tmp_path / "master-log.jsonl"
    jsonl.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", '
        '"session_id": "existing", "repo": "ByronWilliamsCPA/llc-manager", '
        '"superseded_by": null}\n'
    )

    repos_root = tmp_path / "dev"
    repo_clone = repos_root / "llc-manager"
    (repo_clone / "docs" / "compliance-reports" / "lessons-learned").mkdir(parents=True)
    (
        repo_clone / "docs" / "compliance-reports" / "lessons-learned" / "2026-05-16.md"
    ).write_text(SAMPLE_LESSONS)

    catalog = {
        "repos": [
            {
                "org": "ByronWilliamsCPA",
                "name": "llc-manager",
                "isArchived": False,
            }
        ]
    }
    catalog_file = tmp_path / "github-repos.json"
    catalog_file.write_text(json.dumps(catalog))

    result = reconcile(
        catalog_path=catalog_file,
        jsonl_path=jsonl,
        repos_root=repos_root,
        dry_run=False,
    )

    assert result.appended == 0
    assert result.duplicates_skipped == 1


def test_reconcile_since_filter_excludes_older_entries(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import reconcile

    jsonl = tmp_path / "master-log.jsonl"
    jsonl.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
    )

    repos_root = tmp_path / "dev"
    lessons_dir = (
        repos_root / "llc-manager" / "docs" / "compliance-reports" / "lessons-learned"
    )
    lessons_dir.mkdir(parents=True)
    # Old file: should be filtered out
    (lessons_dir / "2025-01-01.md").write_text(
        SAMPLE_LESSONS.replace("2026-05-16", "2025-01-01")
    )
    # New file: should be included
    (lessons_dir / "2026-05-16.md").write_text(SAMPLE_LESSONS)

    catalog = {
        "repos": [
            {"org": "ByronWilliamsCPA", "name": "llc-manager", "isArchived": False}
        ]
    }
    catalog_file = tmp_path / "github-repos.json"
    catalog_file.write_text(json.dumps(catalog))

    result = reconcile(
        catalog_path=catalog_file,
        jsonl_path=jsonl,
        repos_root=repos_root,
        since="2026-01-01",
        dry_run=False,
    )

    assert result.appended == 1
    assert result.duplicates_skipped == 0


def test_reconcile_isolates_parse_failures(tmp_path: Path) -> None:
    from scripts.compliance_rollup_reconcile import reconcile

    jsonl = tmp_path / "master-log.jsonl"
    jsonl.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
    )

    repos_root = tmp_path / "dev"
    lessons_dir = (
        repos_root / "llc-manager" / "docs" / "compliance-reports" / "lessons-learned"
    )
    lessons_dir.mkdir(parents=True)
    # Valid file
    (lessons_dir / "2026-05-16.md").write_text(SAMPLE_LESSONS)
    # Invalid filename (no date prefix) -- should be a parse failure
    (lessons_dir / "garbage.md").write_text("not a retrospective")

    catalog = {
        "repos": [
            {"org": "ByronWilliamsCPA", "name": "llc-manager", "isArchived": False}
        ]
    }
    catalog_file = tmp_path / "github-repos.json"
    catalog_file.write_text(json.dumps(catalog))

    result = reconcile(
        catalog_path=catalog_file,
        jsonl_path=jsonl,
        repos_root=repos_root,
        dry_run=False,
    )

    assert result.appended == 1  # valid file processed
    assert len(result.parse_failures) == 1
    assert "garbage.md" in result.parse_failures[0]


def test_reconcile_dry_run_does_not_write(tmp_path: Path) -> None:
    """dry_run=True must not create the JSONL even when entries would be appended."""
    from scripts.compliance_rollup_reconcile import reconcile

    repos_root = tmp_path / "dev"
    repo_clone = repos_root / "llc-manager"
    (repo_clone / "docs" / "compliance-reports" / "lessons-learned").mkdir(parents=True)
    (
        repo_clone / "docs" / "compliance-reports" / "lessons-learned" / "2026-05-16.md"
    ).write_text(SAMPLE_LESSONS)

    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "ByronWilliamsCPA",
                        "name": "llc-manager",
                        "isArchived": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    jsonl = tmp_path / "log.jsonl"

    result = reconcile(
        catalog_path=catalog, jsonl_path=jsonl, repos_root=repos_root, dry_run=True
    )

    assert result.appended == 1, (
        "appended counter reflects what would have been written"
    )
    assert not jsonl.exists(), "dry_run must not create the JSONL file"


def test_reconcile_skips_archived_repos(tmp_path: Path) -> None:
    """Repos with isArchived=true must be skipped silently."""
    from scripts.compliance_rollup_reconcile import reconcile

    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        '{"repos": [{"name": "old-repo", "org": "testorg", "isArchived": true}]}',
        encoding="utf-8",
    )
    jsonl = tmp_path / "log.jsonl"

    result = reconcile(catalog_path=catalog, jsonl_path=jsonl, dry_run=False)

    assert result.walked == 0
    assert not jsonl.exists(), "archived repos must not cause any writes"


@pytest.mark.parametrize(
    "value",
    [">-", ">", ">+", "|", "|-", "|+", "", "   ", "\n\t "],
)
def test_is_degenerate_pattern_rejects_scalar_markers_and_blanks(value: str) -> None:
    """YAML block-scalar markers and blanks are parse artifacts, not descriptions.

    An earlier parser emitted ``pattern: ">-"`` into the committed master log for
    20 candidates across four sessions and four repos. The synthesis agent groups
    patterns by fuzzy match and promotes anything seen in 3+ sessions across 2+
    repos, so that single artifact would have ranked first and presented a parse
    bug as the report's headline insight.
    """
    from scripts.compliance_rollup_reconcile import is_degenerate_pattern

    assert is_degenerate_pattern(value)


@pytest.mark.parametrize(
    "value",
    [
        ".editorconfig absent from project root",
        "No em-dash characters in .claude/**/*.md files",
        ">- but with real trailing text",
    ],
)
def test_is_degenerate_pattern_accepts_real_descriptions(value: str) -> None:
    """A genuine description is never rejected, including one that starts with '>-'."""
    from scripts.compliance_rollup_reconcile import is_degenerate_pattern

    assert not is_degenerate_pattern(value)


def test_parse_candidates_falls_back_to_id_on_degenerate_description() -> None:
    """A candidate with an unparseable description stays traceable via its ID.

    Dropping the candidate would lose the signal; keeping the raw marker would
    pollute trending. The fallback preserves the proposed manifest ID so a
    reviewer can still trace the entry back to its origin.
    """
    from scripts.compliance_rollup_reconcile import _parse_unclassified_candidates

    text = (
        "## Proposed Manifest Additions\n\n"
        "```yaml\n"
        "id: FOUND-999\n"
        'description: ""\n'
        "```\n"
    )
    candidates = _parse_unclassified_candidates(text)

    assert len(candidates) == 1
    assert candidates[0]["proposed_manifest_id"] == "FOUND-999"
    assert candidates[0]["pattern"] == "(no description parsed) FOUND-999"


@pytest.mark.parametrize("null_form", ["null", "~", ""])
def test_parse_candidates_treats_yaml_null_description_as_degenerate(
    null_form: str,
) -> None:
    """A YAML null description takes the traceable ID fallback, not "None".

    `yaml.safe_load` turns `description: null`, `description: ~`, and a bare
    `description:` into Python `None`, and `str(None).strip()` is `"None"`.
    That string is not whitespace and is not a block-scalar marker, so the
    degenerate guard would pass it through and a literal `None` would enter
    trending as a real pattern. Normalizing before the guard is what keeps
    that from happening; this test fails if the normalization is removed.
    """
    from scripts.compliance_rollup_reconcile import _parse_unclassified_candidates

    text = (
        "## Proposed Manifest Additions\n\n"
        "```yaml\n"
        "id: FOUND-998\n"
        f"description: {null_form}\n"
        "```\n"
    )
    candidates = _parse_unclassified_candidates(text)

    assert len(candidates) == 1
    assert candidates[0]["proposed_manifest_id"] == "FOUND-998"
    assert candidates[0]["pattern"] == "(no description parsed) FOUND-998"
    assert "None" not in candidates[0]["pattern"]


@pytest.mark.parametrize(
    ("yaml_value", "stringified"),
    [
        ("[]", "[]"),
        ("{}", "{}"),
        ("no", "False"),
        ("0", "0"),
        ("\n  - a\n  - b", "'a'"),
    ],
    ids=["empty-sequence", "empty-mapping", "bare-no", "zero", "sequence"],
)
def test_parse_candidates_rejects_non_string_descriptions(
    yaml_value: str, stringified: str
) -> None:
    """Only a YAML string can be prose; every other node takes the ID fallback.

    A description is human text, so the type that carries it is `str`. Each
    other node `safe_load` can produce here stringifies into something that
    reads as real text and survives the degeneracy guard: an empty sequence
    becomes `"[]"`, a bare `no` becomes `"False"`, `0` becomes `"0"`. Any of
    them would then enter the master log as a groupable pattern and could
    surface as a trending insight. Accepting `str` alone closes the whole
    class rather than the one instance that was first noticed.
    """
    from scripts.compliance_rollup_reconcile import _parse_unclassified_candidates

    text = (
        "## Proposed Manifest Additions\n\n"
        "```yaml\n"
        "id: FOUND-997\n"
        f"description: {yaml_value}\n"
        "```\n"
    )
    candidates = _parse_unclassified_candidates(text)

    assert len(candidates) == 1
    assert candidates[0]["proposed_manifest_id"] == "FOUND-997"
    assert candidates[0]["pattern"] == "(no description parsed) FOUND-997"
    assert stringified not in candidates[0]["pattern"]
