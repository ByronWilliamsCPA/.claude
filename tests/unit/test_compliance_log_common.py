# tests/unit/test_compliance_log_common.py
"""Tests for compliance_log_common shared helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def sample_entry() -> dict:
    return {
        "schema_version": 1,
        "session_date": "2026-05-16",
        "session_id": "2026-05-16T19:42:11Z-fdc2",
        "repo": "ByronWilliamsCPA/llc-manager",
        "repo_path": "/home/byron/dev/llc-manager",
        "audit_mode": "interactive",
        "repo_type": "python-app",
        "visibility": "public",
        "reconciled": False,
        "totals": {
            "critical": 0,
            "important": 3,
            "suggested": 7,
            "unclassified_candidates": 2,
            "overrides_applied": 1,
        },
        "findings_by_check": [],
        "unclassified_candidates": [],
        "fleet_action_proposals": [],
        "scope_expansion_flags": [],
        "links": {},
        "superseded_by": None,
    }


def test_schema_version_constant_is_one() -> None:
    from scripts.compliance_log_common import SCHEMA_VERSION

    assert SCHEMA_VERSION == 1


def test_load_entries_skips_header_line(tmp_path: Path) -> None:
    from scripts.compliance_log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "session_id": "a", '
        '"repo": "x/y", "superseded_by": null}\n'
    )

    entries = load_entries(p)

    assert len(entries) == 1
    assert entries[0]["repo"] == "x/y"


def test_load_entries_returns_empty_for_missing_file(tmp_path: Path) -> None:
    from scripts.compliance_log_common import load_entries

    assert load_entries(tmp_path / "missing.jsonl") == []


def test_resolve_canonical_picks_latest_session_id_when_no_supersede(
    sample_entry: dict,
) -> None:
    from scripts.compliance_log_common import resolve_canonical_per_key

    earlier = {**sample_entry, "session_id": "2026-05-16T08:00:00Z-a"}
    later = {**sample_entry, "session_id": "2026-05-16T18:00:00Z-b"}

    canonical = resolve_canonical_per_key([earlier, later])

    assert len(canonical) == 1
    assert canonical[0]["session_id"] == "2026-05-16T18:00:00Z-b"


def test_resolve_canonical_skips_superseded_entries(sample_entry: dict) -> None:
    from scripts.compliance_log_common import resolve_canonical_per_key

    old = {**sample_entry, "session_id": "old", "superseded_by": "new"}
    new = {**sample_entry, "session_id": "new"}

    canonical = resolve_canonical_per_key([old, new])

    assert len(canonical) == 1
    assert canonical[0]["session_id"] == "new"


def test_resolve_canonical_groups_by_date_and_repo(sample_entry: dict) -> None:
    from scripts.compliance_log_common import resolve_canonical_per_key

    a = {**sample_entry, "session_date": "2026-05-16", "repo": "org/r1"}
    b = {**sample_entry, "session_date": "2026-05-16", "repo": "org/r2"}
    c = {**sample_entry, "session_date": "2026-05-17", "repo": "org/r1"}

    canonical = resolve_canonical_per_key([a, b, c])

    assert len(canonical) == 3


def test_make_dedupe_key_uses_date_and_repo(sample_entry: dict) -> None:
    from scripts.compliance_log_common import make_dedupe_key

    assert make_dedupe_key(sample_entry) == (
        "2026-05-16",
        "ByronWilliamsCPA/llc-manager",
    )
