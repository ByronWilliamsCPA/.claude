# tests/unit/test_compliance_log_common.py
"""Tests for compliance_log_common shared helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_schema_version_constant_is_one() -> None:
    from claude_config.compliance.log_common import SCHEMA_VERSION

    assert SCHEMA_VERSION == 1


def test_load_entries_skips_header_line(tmp_path: Path) -> None:
    from claude_config.compliance.log_common import load_entries

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
    from claude_config.compliance.log_common import load_entries

    assert load_entries(tmp_path / "missing.jsonl") == []


def test_resolve_canonical_picks_latest_session_id_when_no_supersede(
    compliance_entry: dict,
) -> None:
    from claude_config.compliance.log_common import resolve_canonical_per_key

    earlier = {**compliance_entry, "session_id": "2026-05-16T08:00:00Z-a"}
    later = {**compliance_entry, "session_id": "2026-05-16T18:00:00Z-b"}

    canonical = resolve_canonical_per_key([earlier, later])

    assert len(canonical) == 1
    assert canonical[0]["session_id"] == "2026-05-16T18:00:00Z-b"


def test_resolve_canonical_skips_superseded_entries(compliance_entry: dict) -> None:
    from claude_config.compliance.log_common import resolve_canonical_per_key

    old = {**compliance_entry, "session_id": "old", "superseded_by": "new"}
    new = {**compliance_entry, "session_id": "new"}

    canonical = resolve_canonical_per_key([old, new])

    assert len(canonical) == 1
    assert canonical[0]["session_id"] == "new"


def test_resolve_canonical_groups_by_date_and_repo(compliance_entry: dict) -> None:
    from claude_config.compliance.log_common import resolve_canonical_per_key

    a = {**compliance_entry, "session_date": "2026-05-16", "repo": "org/r1"}
    b = {**compliance_entry, "session_date": "2026-05-16", "repo": "org/r2"}
    c = {**compliance_entry, "session_date": "2026-05-17", "repo": "org/r1"}

    canonical = resolve_canonical_per_key([a, b, c])

    assert len(canonical) == 3


def test_make_dedupe_key_uses_date_and_repo(compliance_entry: dict) -> None:
    from claude_config.compliance.log_common import make_dedupe_key

    assert make_dedupe_key(compliance_entry) == (
        "2026-05-16",
        "ByronWilliamsCPA/llc-manager",
    )


def test_resolve_canonical_returns_empty_for_empty_input() -> None:
    from claude_config.compliance.log_common import resolve_canonical_per_key

    assert resolve_canonical_per_key([]) == []


def test_resolve_canonical_returns_empty_when_all_entries_superseded(
    compliance_entry: dict,
) -> None:
    from claude_config.compliance.log_common import resolve_canonical_per_key

    a = {**compliance_entry, "session_id": "a", "superseded_by": "b"}
    b = {**compliance_entry, "session_id": "b", "superseded_by": "c"}

    assert resolve_canonical_per_key([a, b]) == []


def test_resolve_canonical_treats_empty_string_supersede_as_superseded(
    compliance_entry: dict,
) -> None:
    from claude_config.compliance.log_common import resolve_canonical_per_key

    superseded_with_empty = {**compliance_entry, "session_id": "x", "superseded_by": ""}

    assert resolve_canonical_per_key([superseded_with_empty]) == []


def test_repo_root_from_resolves_two_levels_up(tmp_path: Path) -> None:
    from claude_config.compliance.log_common import repo_root_from

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    fake_script = scripts_dir / "fake_script.py"
    fake_script.write_text("# placeholder")

    assert repo_root_from(fake_script) == tmp_path
