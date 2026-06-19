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


def test_load_entries_collects_malformed_json_when_skipped_provided(
    tmp_path: Path,
) -> None:
    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "session_id": "a", '
        '"repo": "x/y", "superseded_by": null}\n'
        "{not valid json}\n",
        encoding="utf-8",
    )

    skipped: list[str] = []
    entries = load_entries(p, skipped=skipped)

    assert len(entries) == 1
    assert len(skipped) == 1
    assert "malformed JSON" in skipped[0]
    assert f"{p}:3" in skipped[0]


def test_load_entries_validate_skips_schema_incomplete_and_collects(
    tmp_path: Path,
) -> None:
    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "session_id": "a", '
        '"repo": "x/y", "superseded_by": null}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "repo": "x/z"}\n',
        encoding="utf-8",
    )

    skipped: list[str] = []
    entries = load_entries(p, validate=True, skipped=skipped)

    assert len(entries) == 1
    assert entries[0]["repo"] == "x/y"
    assert len(skipped) == 1
    assert f"{p}:3" in skipped[0]
    assert "session_id" in skipped[0]


def test_load_entries_strict_validate_raises_on_schema_error(
    tmp_path: Path,
) -> None:
    import pytest

    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "repo": "x/z"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"log\.jsonl:2"):
        load_entries(p, strict=True, validate=True)


def test_load_entries_skips_non_object_json_row(tmp_path: Path) -> None:
    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "session_id": "a", '
        '"repo": "x/y", "superseded_by": null}\n'
        "[1, 2, 3]\n",
        encoding="utf-8",
    )

    skipped: list[str] = []
    entries = load_entries(p, skipped=skipped)

    assert len(entries) == 1
    assert entries[0]["repo"] == "x/y"
    assert len(skipped) == 1
    assert f"{p}:3" in skipped[0]
    assert "expected JSON object" in skipped[0]


def test_load_entries_skips_invalid_utf8_row(tmp_path: Path) -> None:
    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_bytes(
        b'{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        b'{"schema_version": 1, "session_date": "2026-05-16", "session_id": "a"'
        b', "repo": "x/y", "superseded_by": null}\n'
        b"\xff\xfe not valid utf-8\n",
    )

    skipped: list[str] = []
    entries = load_entries(p, skipped=skipped)

    assert len(entries) == 1
    assert entries[0]["repo"] == "x/y"
    assert len(skipped) == 1
    assert f"{p}:3" in skipped[0]
    assert "invalid UTF-8" in skipped[0]


def test_load_entries_default_keeps_schema_incomplete_row(tmp_path: Path) -> None:
    """Default (validate=False) callers must not drop schema-incomplete rows.

    Regression guard for the two production callers (append, reconcile) that
    call ``load_entries`` with no keyword args: a valid-JSON row missing a
    required key is returned unchanged, since schema is only checked under
    ``validate=True``.
    """
    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "repo": "x/z"}\n',
        encoding="utf-8",
    )

    entries = load_entries(p)

    assert len(entries) == 1
    assert entries[0]["repo"] == "x/z"
    assert "session_id" not in entries[0]


def test_load_entries_nonstrict_skips_malformed_without_sink(
    tmp_path: Path,
) -> None:
    """Non-strict load with no ``skipped`` sink warns and skips, never raises."""
    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        '{"schema_version": 1, "session_date": "2026-05-16", "session_id": "a", '
        '"repo": "x/y", "superseded_by": null}\n'
        "{not valid json}\n",
        encoding="utf-8",
    )

    entries = load_entries(p)

    assert len(entries) == 1
    assert entries[0]["repo"] == "x/y"


def test_load_entries_strict_raises_on_malformed_json(tmp_path: Path) -> None:
    import pytest

    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        "{not valid json}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"log\.jsonl:2: malformed JSON"):
        load_entries(p, strict=True)


def test_load_entries_strict_chains_original_cause(tmp_path: Path) -> None:
    """The strict raise chains the originating exception for operator context."""
    import json

    import pytest

    from claude_config.compliance.log_common import load_entries

    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"type": "header", "schema_version": 1, "created": "2026-05-16"}\n'
        "{not valid json}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"malformed JSON") as excinfo:
        load_entries(p, strict=True)

    assert isinstance(excinfo.value.__cause__, json.JSONDecodeError)


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


def test_repo_root_from_finds_pyproject_marker(tmp_path: Path) -> None:
    from claude_config.compliance.log_common import repo_root_from

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    nested = tmp_path / "src" / "claude_config" / "compliance"
    nested.mkdir(parents=True)
    module = nested / "log_common.py"
    module.write_text("# placeholder")

    assert repo_root_from(module) == tmp_path


def test_repo_root_from_raises_when_no_marker(tmp_path: Path) -> None:
    import pytest

    from claude_config.compliance.log_common import repo_root_from

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    fake_script = scripts_dir / "fake_script.py"
    fake_script.write_text("# placeholder")

    with pytest.raises(FileNotFoundError, match=r"pyproject\.toml"):
        repo_root_from(fake_script)
