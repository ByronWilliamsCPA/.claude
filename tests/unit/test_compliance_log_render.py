# tests/unit/test_compliance_log_render.py
"""Tests for the master-log Markdown renderer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _write_jsonl(path: Path, *entries: dict) -> None:
    lines = ['{"type": "header", "schema_version": 1, "created": "2026-05-16"}']
    lines.extend(json.dumps(e) for e in entries)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        "findings_by_check": [
            {"id": "FOUND-008", "severity": "important", "remediation_status": "open"}
        ],
        "unclassified_candidates": [],
        "fleet_action_proposals": [],
        "scope_expansion_flags": [],
        "links": {
            "lessons_learned": "docs/compliance-reports/lessons-learned/2026-05-16.md"
        },
        "superseded_by": None,
    }


def test_renders_empty_for_header_only_file(tmp_path: Path) -> None:
    from scripts.compliance_log_render import render

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    assert "# Compliance Master Log" in text
    assert "Total sessions:" in text
    assert "0" in text


def test_renders_single_entry_with_summary_header(
    tmp_path: Path, sample_entry: dict
) -> None:
    from scripts.compliance_log_render import render

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl, sample_entry)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    assert "Total sessions:" in text
    assert "1" in text
    assert "ByronWilliamsCPA/llc-manager" in text
    assert "2026-05" in text


def test_renders_reverse_chronological_months(
    tmp_path: Path, sample_entry: dict
) -> None:
    from scripts.compliance_log_render import render

    older = {
        **sample_entry,
        "session_date": "2026-03-01",
        "session_id": "2026-03-01T08:00:00Z-a",
    }
    newer = {
        **sample_entry,
        "session_date": "2026-05-16",
        "session_id": "2026-05-16T19:42:11Z-b",
        "repo": "ByronWilliamsCPA/other",
    }

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl, older, newer)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    may_pos = text.index("2026-05")
    march_pos = text.index("2026-03")
    assert may_pos < march_pos, "newer month should appear before older"


def test_renders_only_canonical_entry_when_superseded(
    tmp_path: Path, sample_entry: dict
) -> None:
    from scripts.compliance_log_render import render

    old = {**sample_entry, "session_id": "old", "superseded_by": "new"}
    new = {**sample_entry, "session_id": "new"}

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl, old, new)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    matches = text.count("ByronWilliamsCPA/llc-manager")
    assert matches == 1, f"expected one canonical row, found {matches}"


def test_renders_reconciled_marker_when_present(
    tmp_path: Path, sample_entry: dict
) -> None:
    from scripts.compliance_log_render import render

    reconciled = {**sample_entry, "reconciled": True}
    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl, reconciled)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    # Find the data row for this entry and confirm it contains "yes" in the reconciled column
    repo_rows = [
        line
        for line in text.splitlines()
        if "ByronWilliamsCPA/llc-manager" in line and line.startswith("|")
    ]
    assert len(repo_rows) == 1
    # The reconciled column has "yes" followed by a pipe and the report column
    assert " | yes |" in repo_rows[0]


def test_does_not_render_reconciled_marker_when_absent(
    tmp_path: Path, sample_entry: dict
) -> None:
    from scripts.compliance_log_render import render

    plain = {**sample_entry, "reconciled": False}
    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl, plain)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    repo_rows = [
        line
        for line in text.splitlines()
        if "ByronWilliamsCPA/llc-manager" in line and line.startswith("|")
    ]
    assert len(repo_rows) == 1
    # The reconciled cell should be empty (not "yes"). Match the empty cell pattern.
    assert " |  |" in repo_rows[0] or repo_rows[0].rstrip().rstrip(
        "|"
    ).rstrip().endswith("|")
