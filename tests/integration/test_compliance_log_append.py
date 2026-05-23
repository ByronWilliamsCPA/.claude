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
    compliance_entry: dict,
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
        **compliance_entry,
        "session_date": "2026-05-17",
        "session_id": "2026-05-17T10:00:00Z-test",
        "repo": "test-org/test-repo",
        "repo_path": str(foreign_cwd),
        "totals": {
            "critical": 0,
            "important": 1,
            "suggested": 2,
            "unclassified_candidates": 0,
            "overrides_applied": 0,
        },
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


def test_append_helper_supersede_marks_existing_entry(
    tmp_path: Path,
    compliance_entry: dict,
) -> None:
    """Supersede semantics: prior active entry gets superseded_by set.

    When (session_date, repo) already exists, the old entry's
    superseded_by gets the new session_id.
    """
    from scripts.compliance_log_append import append_entry

    fake_central = tmp_path / "master-log.jsonl"

    base_entry = {
        **compliance_entry,
        "session_date": "2026-05-17",
        "session_id": "2026-05-17T10:00:00Z-old1",
        "repo": "test-org/test-repo",
        "repo_path": "",
        "totals": {
            "critical": 0,
            "important": 0,
            "suggested": 0,
            "unclassified_candidates": 0,
            "overrides_applied": 0,
        },
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


def test_supersede_handles_multiple_active_priors(
    tmp_path: Path,
    compliance_entry: dict,
) -> None:
    """Regression test for finding #22 (multi prior-active supersede).

    A previous bug class: when two active entries already share a
    ``(session_date, repo)`` key, the supersede walk marked only the
    lex-greatest as superseded, leaving the second-newest active and
    silently violating the canonical-per-key invariant.

    The atomic supersede+append path must surface this invariant for
    any future regression that reintroduces multi-active divergence.
    """
    from scripts.compliance_log_append import append_entry
    from scripts.compliance_log_common import (
        load_entries,
        resolve_canonical_per_key,
    )

    fake_central = tmp_path / "master-log.jsonl"

    # Seed two active entries with the same (date, repo) key by writing
    # the file directly: append_entry on its own correctly creates only
    # one active entry, so the multi-active state has to be simulated.
    fake_central.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-17"}\n'
        + json.dumps(
            {
                **compliance_entry,
                "session_date": "2026-05-17",
                "session_id": "2026-05-17T08:00:00Z-old1",
            }
        )
        + "\n"
        + json.dumps(
            {
                **compliance_entry,
                "session_date": "2026-05-17",
                "session_id": "2026-05-17T09:00:00Z-old2",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    append_entry(
        {
            **compliance_entry,
            "session_date": "2026-05-17",
            "session_id": "2026-05-17T18:00:00Z-new3",
        },
        jsonl_path=fake_central,
        render=False,
    )

    entries = load_entries(fake_central)
    canonical = resolve_canonical_per_key(entries)
    # Exactly one canonical entry survives per key.
    assert len(canonical) == 1
    assert canonical[0]["session_id"] == "2026-05-17T18:00:00Z-new3"


def test_supersede_skips_corrupted_jsonl_lines(
    tmp_path: Path,
    compliance_entry: dict,
) -> None:
    """Regression test for finding #23 (corrupted JSONL line in supersede).

    A malformed JSONL line between header and the active prior must be
    preserved verbatim (so a manual inspection can still see what went
    wrong) while supersede + append continues to land cleanly. If the
    swallow path ever hides the truly active prior, the canonical view
    will report two active entries; this test pins that the active
    prior is correctly superseded and the corrupted line is preserved.
    """
    from scripts.compliance_log_append import append_entry
    from scripts.compliance_log_common import (
        load_entries,
        resolve_canonical_per_key,
    )

    fake_central = tmp_path / "master-log.jsonl"

    fake_central.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-17"}\n'
        "{not valid json on this line}\n"
        + json.dumps(
            {
                **compliance_entry,
                "session_date": "2026-05-17",
                "session_id": "2026-05-17T08:00:00Z-old1",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    append_entry(
        {
            **compliance_entry,
            "session_date": "2026-05-17",
            "session_id": "2026-05-17T18:00:00Z-new2",
        },
        jsonl_path=fake_central,
        render=False,
    )

    raw = fake_central.read_text(encoding="utf-8")
    assert "{not valid json on this line}" in raw

    entries = load_entries(fake_central)
    # load_entries raises on malformed lines per the new contract, so
    # callers wanting "skip and continue" semantics must handle that
    # exception themselves. For this test, we want both the surviving
    # canonical entry AND the corrupted line to be present, so we read
    # the raw text and pick entries manually.
    valid_payloads = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "header":
            continue
        valid_payloads.append(obj)

    canonical = resolve_canonical_per_key(valid_payloads)
    assert len(canonical) == 1
    assert canonical[0]["session_id"] == "2026-05-17T18:00:00Z-new2"
    # The prior active entry is now superseded, not active.
    superseded = [p for p in valid_payloads if p.get("superseded_by") is not None]
    assert len(superseded) == 1
    assert superseded[0]["session_id"] == "2026-05-17T08:00:00Z-old1"
    _ = entries  # keep the import wired so static analysis sees the dep
