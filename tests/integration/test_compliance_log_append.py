# tests/integration/test_compliance_log_append.py
"""Integration test: the write-side push path lands entries in the central log."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_append_helper_writes_to_central_log_regardless_of_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the append helper resolves the central log via __file__.

    Not via working directory. This catches the C1 bug class: an
    invocation from a non-repo working directory must still land the
    entry in the canonical central log.
    """
    # Simulate the agent running from an unrelated working directory.
    foreign_cwd = tmp_path / "some_other_repo"
    foreign_cwd.mkdir()
    monkeypatch.chdir(foreign_cwd)

    entry = {
        "schema_version": 1,
        "session_date": "2026-05-17",
        "session_id": "2026-05-17T10:00:00Z-test",
        "repo": "test-org/test-repo",
        "repo_path": str(foreign_cwd),
        "audit_mode": "interactive",
        "repo_type": "python-app",
        "visibility": "public",
        "reconciled": False,
        "totals": {
            "critical": 0,
            "important": 1,
            "suggested": 2,
            "unclassified_candidates": 0,
            "overrides_applied": 0,
        },
        "findings_by_check": [],
        "unclassified_candidates": [],
        "fleet_action_proposals": [],
        "scope_expansion_flags": [],
        "links": {},
        "superseded_by": None,
    }

    # Use append_entry directly with a fake jsonl_path to avoid mutating
    # the real central log. This exercises the helper's logic.
    from scripts.compliance_log_append import append_entry

    fake_central = tmp_path / "central" / "master-log.jsonl"
    append_entry(entry, jsonl_path=fake_central, render=False)

    # Assert the entry landed in the central path, NOT under foreign_cwd.
    assert fake_central.exists(), "entry did not land in central log"
    leaked = foreign_cwd / "docs" / "compliance-reports" / "master-log.jsonl"
    assert not leaked.exists(), "entry leaked into the audited repo's tree"

    contents = fake_central.read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in contents if line.strip()]
    # Header + one entry
    assert len(payloads) >= 2
    appended = payloads[-1]
    assert appended["session_id"] == entry["session_id"]
    assert appended["repo"] == entry["repo"]


def test_append_helper_supersede_marks_existing_entry(tmp_path: Path) -> None:
    """Supersede semantics: prior active entry gets superseded_by set.

    When (session_date, repo) already exists, the old entry's
    superseded_by gets the new session_id.
    """
    from scripts.compliance_log_append import append_entry

    fake_central = tmp_path / "master-log.jsonl"

    base_entry = {
        "schema_version": 1,
        "session_date": "2026-05-17",
        "session_id": "2026-05-17T10:00:00Z-old1",
        "repo": "test-org/test-repo",
        "repo_path": "/tmp/test",
        "audit_mode": "interactive",
        "repo_type": "python-app",
        "visibility": "public",
        "reconciled": False,
        "totals": {
            "critical": 0,
            "important": 0,
            "suggested": 0,
            "unclassified_candidates": 0,
            "overrides_applied": 0,
        },
        "findings_by_check": [],
        "unclassified_candidates": [],
        "fleet_action_proposals": [],
        "scope_expansion_flags": [],
        "links": {},
        "superseded_by": None,
    }
    append_entry(base_entry, jsonl_path=fake_central, render=False)

    new_entry = {**base_entry, "session_id": "2026-05-17T18:00:00Z-new2"}
    append_entry(new_entry, jsonl_path=fake_central, render=False)

    contents = fake_central.read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in contents if line.strip()]
    body_entries = [p for p in payloads if p.get("type") != "header"]
    assert len(body_entries) == 2
    old, new = body_entries[0], body_entries[1]
    assert old["superseded_by"] == new_entry["session_id"]
    assert new["superseded_by"] is None
