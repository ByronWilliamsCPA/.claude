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
    from claude_config.compliance.log_render import render

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    assert "title: Compliance Master Log" in text
    assert "schema_type: common" in text
    assert "Total sessions:" in text
    assert "0" in text


def test_renders_single_entry_with_summary_header(
    tmp_path: Path, sample_entry: dict
) -> None:
    from claude_config.compliance.log_render import render

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
    from claude_config.compliance.log_render import render

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
    from claude_config.compliance.log_render import render

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
    from claude_config.compliance.log_render import render

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
    from claude_config.compliance.log_render import render

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


def _strip_footer(text: str) -> str:
    """Remove the rendered-at footer (the only non-deterministic line)."""
    lines = text.splitlines()
    return "\n".join(line for line in lines if not line.startswith("*Rendered "))


def test_render_is_deterministic_modulo_timestamp_footer(
    tmp_path: Path, sample_entry: dict
) -> None:
    """Regression test for finding #25 (determinism claim was unverified).

    The PR description says the renderer is "deterministic modulo the
    timestamp footer". This test renders the same JSONL twice, strips
    the only non-deterministic line (the ``*Rendered ...*`` footer)
    from each output, and asserts byte-for-byte equality.
    """
    from claude_config.compliance.log_render import render

    jsonl = tmp_path / "master-log.jsonl"
    md1 = tmp_path / "first.md"
    md2 = tmp_path / "second.md"
    _write_jsonl(jsonl, sample_entry)

    render(jsonl, md1)
    render(jsonl, md2)

    assert _strip_footer(md1.read_text(encoding="utf-8")) == _strip_footer(
        md2.read_text(encoding="utf-8")
    )


def test_validated_override_passes_none_through() -> None:
    """A ``None`` override is preserved so render() falls back to defaults."""
    import argparse
    from pathlib import Path as _Path

    from claude_config.compliance.log_render import _validated_override

    parser = argparse.ArgumentParser()
    assert _validated_override(parser, None, base_dir=_Path.cwd()) is None


def test_validated_override_resolves_relative_inside_base(tmp_path: Path) -> None:
    """A relative override resolves under the trusted base directory."""
    import argparse
    from pathlib import Path as _Path

    from claude_config.compliance.log_render import _validated_override

    parser = argparse.ArgumentParser()
    result = _validated_override(parser, _Path("sub/out.md"), base_dir=tmp_path)

    assert result == (tmp_path / "sub" / "out.md").resolve()


def test_validated_override_accepts_absolute_inside_base(tmp_path: Path) -> None:
    """An absolute override that already lives under the base is accepted."""
    import argparse

    from claude_config.compliance.log_render import _validated_override

    candidate = tmp_path / "nested" / "log.jsonl"
    parser = argparse.ArgumentParser()

    assert _validated_override(parser, candidate, base_dir=tmp_path) == (
        candidate.resolve()
    )


def test_validated_override_rejects_traversal_escape(tmp_path: Path) -> None:
    """A ``..`` traversal that escapes the base exits non-zero."""
    import argparse
    from pathlib import Path as _Path

    from claude_config.compliance.log_render import _validated_override

    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit) as excinfo:
        _validated_override(parser, _Path("../../../etc/passwd"), base_dir=tmp_path)

    assert excinfo.value.code == 2


def test_validated_override_rejects_absolute_outside_base(tmp_path: Path) -> None:
    """An absolute path outside the base is rejected rather than followed."""
    import argparse
    from pathlib import Path as _Path

    from claude_config.compliance.log_render import _validated_override

    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit) as excinfo:
        _validated_override(parser, _Path("/etc/passwd"), base_dir=tmp_path)

    assert excinfo.value.code == 2


def test_validated_override_rejects_symlink_escape(tmp_path: Path) -> None:
    """A symlink inside base that points outside is rejected after resolve().

    This guards the load-bearing choice of ``Path.resolve()`` (which follows
    symlinks) over a string-only normalization: swapping it for
    ``os.path.abspath`` would silently reopen the symlink escape.
    """
    import argparse
    from pathlib import Path as _Path

    from claude_config.compliance.log_render import _validated_override

    outside = tmp_path / "outside"
    outside.mkdir()
    base = tmp_path / "base"
    base.mkdir()
    link = base / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not supported on this platform")

    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit) as excinfo:
        _validated_override(parser, _Path("escape/secret.md"), base_dir=base)

    assert excinfo.value.code == 2


def test_validated_override_rejects_sibling_prefix(tmp_path: Path) -> None:
    """A sibling dir sharing a name prefix (``dir`` vs ``dir-secret``) is rejected.

    Documents why containment uses component-wise ``Path.is_relative_to`` rather
    than ``str.startswith``: the latter would wrongly accept ``/x/dir-secret`` as
    living under ``/x/dir``.
    """
    import argparse

    from claude_config.compliance.log_render import _validated_override

    base = tmp_path / "dir"
    base.mkdir()
    sibling = tmp_path / "dir-secret"
    sibling.mkdir()
    candidate = sibling / "out.md"

    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit) as excinfo:
        _validated_override(parser, candidate, base_dir=base)

    assert excinfo.value.code == 2


def test_main_rejects_traversal_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() rejects a --jsonl override that escapes the repository root.

    Guards the wiring: without _validated_override invoked in main(), an
    escaping CLI path would flow straight into render()'s filesystem sinks.
    """
    import sys

    from claude_config.compliance import log_render

    monkeypatch.setattr(sys, "argv", ["log_render", "--jsonl", "/etc/passwd"])
    with pytest.raises(SystemExit) as excinfo:
        log_render.main()

    assert excinfo.value.code == 2


def test_main_passes_validated_paths_to_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """main() canonicalizes both overrides against the repo root before render()."""
    import sys

    from claude_config.compliance import log_render
    from claude_config.compliance.log_render import _REPO_ROOT

    captured: dict[str, Path | None] = {}

    def _capture(jsonl_path: Path | None = None, md_path: Path | None = None) -> None:
        captured["jsonl"] = jsonl_path
        captured["md"] = md_path

    monkeypatch.setattr(log_render, "render", _capture)
    monkeypatch.setattr(
        sys,
        "argv",
        ["log_render", "--jsonl", "sub/in.jsonl", "--md", "sub/out.md"],
    )

    log_render.main()

    assert captured["jsonl"] == (_REPO_ROOT / "sub/in.jsonl").resolve()
    assert captured["md"] == (_REPO_ROOT / "sub/out.md").resolve()


_HEADER_LINE = '{"type": "header", "schema_version": 1, "created": "2026-05-16"}'


def test_render_skips_malformed_json_line_and_notes_in_footer(
    tmp_path: Path, sample_entry: dict
) -> None:
    """A malformed JSON line is skipped, not silently dropped.

    Regression for issue #178 gap 1: the valid row still renders and the
    footer records the skip count so the published artifact reflects the
    omission instead of silently undercounting.
    """
    from claude_config.compliance.log_render import render

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    jsonl.write_text(
        _HEADER_LINE + "\n" + json.dumps(sample_entry) + "\n{not valid json}\n",
        encoding="utf-8",
    )

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    assert "ByronWilliamsCPA/llc-manager" in text
    assert "1 log row(s) skipped" in text


def test_render_skips_schema_incomplete_entry_and_notes_in_footer(
    tmp_path: Path, sample_entry: dict
) -> None:
    """A valid-JSON row missing a required key is skipped with a footer note.

    Regression for issue #178 gap 2: previously the missing ``session_id``
    raised a context-free ``KeyError`` (in ``resolve_canonical_per_key``)
    that aborted the whole render. Now the row is skipped and the valid row
    renders.
    """
    from claude_config.compliance.log_render import render

    incomplete = {
        "schema_version": 1,
        "session_date": "2026-05-16",
        "repo": "ByronWilliamsCPA/incomplete",
        # session_id intentionally omitted -> fails validate_entry
    }
    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    jsonl.write_text(
        _HEADER_LINE
        + "\n"
        + json.dumps(sample_entry)
        + "\n"
        + json.dumps(incomplete)
        + "\n",
        encoding="utf-8",
    )

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    assert "ByronWilliamsCPA/llc-manager" in text
    assert "ByronWilliamsCPA/incomplete" not in text
    assert "1 log row(s) skipped" in text


def test_render_tolerates_missing_audit_mode(
    tmp_path: Path, sample_entry: dict
) -> None:
    """An entry with all required keys but no ``audit_mode`` renders cleanly.

    ``audit_mode`` is a display field, not a schema-required key, so a row
    lacking it renders an empty mode cell (like ``totals``/``links``) rather
    than raising ``KeyError``, and is not counted as a skip.
    """
    from claude_config.compliance.log_render import render

    no_mode = {k: v for k, v in sample_entry.items() if k != "audit_mode"}
    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    _write_jsonl(jsonl, no_mode)

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    repo_rows = [
        line
        for line in text.splitlines()
        if "ByronWilliamsCPA/llc-manager" in line and line.startswith("|")
    ]
    assert len(repo_rows) == 1
    assert "skipped" not in text


def test_render_skips_non_object_json_row_and_notes_in_footer(
    tmp_path: Path, sample_entry: dict
) -> None:
    """A valid-JSON but non-object row is skipped, not allowed to abort render.

    A line such as ``[1, 2, 3]`` parses as JSON but is not a dict; before the
    guard it raised ``AttributeError`` at ``obj.get("type")`` and aborted the
    whole render. Now it is skipped with a footer note and the valid row still
    renders.
    """
    from claude_config.compliance.log_render import render

    jsonl = tmp_path / "master-log.jsonl"
    md = tmp_path / "master-log.md"
    jsonl.write_text(
        _HEADER_LINE + "\n" + json.dumps(sample_entry) + "\n[1, 2, 3]\n",
        encoding="utf-8",
    )

    render(jsonl, md)

    text = md.read_text(encoding="utf-8")
    assert "ByronWilliamsCPA/llc-manager" in text
    assert "1 log row(s) skipped" in text
