"""Tests for the assurance-spine coverage diagnostic.

The script joins the standards manifest to the seventeen spine categories on
the `sp_category` field. Its whole value is the empty cell: a category with no
checks is a blind spot made visible. That value is destroyed in two ways, and
both are what these tests guard.

An unrecognised category (a typo such as `SP-99`) must not count as mapped.
If it did, the header would report higher coverage while the row it claims to
cover stays empty, which is the reverse of what the report exists to show. An
absent category must stay unmapped for the same reason.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "spine-coverage.py"


def _load_module() -> Any:
    """Import the hyphenated script by path.

    `spine-coverage.py` is not an importable module name, so a normal import
    statement cannot reach it.

    Returns:
        The loaded module object.
    """
    spec = importlib.util.spec_from_file_location("spine_coverage", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unknown_category_is_not_counted_as_mapped() -> None:
    """`SP-99` inflates nothing: it is invalid, not covered."""
    mod = _load_module()
    checks = [
        {"id": "OPS-001", "sp_category": "SP-09"},
        {"id": "BAD-001", "sp_category": "SP-99"},
    ]

    coverage = mod.build_coverage(checks)
    assert coverage["SP-09"] == ["OPS-001"]
    assert "SP-99" not in coverage

    invalid = mod.invalid_categories(checks)
    assert invalid == {"SP-99": ["BAD-001"]}

    rendered = "\n".join(mod.render(checks, coverage))
    assert "mapped to a spine category: 1" in rendered
    assert "unmapped: 1" in rendered
    assert "SP-99" in rendered, "an invalid value must be reported, not swallowed"


def test_absent_category_stays_unmapped() -> None:
    """A check with no usable `sp_category` contributes to no row and no total.

    Four spellings of "not stated" are covered: the key omitted, an explicit
    `null`, an empty string, and whitespace only. `category_text` normalizes
    all four to blank, so all four must land on the unmapped pile rather than
    in the invalid list. Reporting a blank as invalid would flood the
    diagnostic with rows that name no wrong value and hide the real ones.
    """
    mod = _load_module()
    checks: list[dict[str, Any]] = [
        {"id": "FOUND-001"},
        {"id": "FOUND-002", "sp_category": None},
        {"id": "FOUND-003", "sp_category": ""},
        {"id": "FOUND-004", "sp_category": "   "},
    ]

    coverage = mod.build_coverage(checks)
    assert all(ids == [] for ids in coverage.values())
    assert mod.invalid_categories(checks) == {}, (
        "a blank category is unstated, not a wrong value"
    )

    rendered = "\n".join(mod.render(checks, coverage))
    assert "mapped to a spine category: 0" in rendered
    assert "unmapped: 4" in rendered


@pytest.mark.parametrize("category", [0, False])
def test_falsey_category_is_invalid_not_absent(category: object) -> None:
    """`0` and `False` are malformed values, not missing ones.

    A truthiness test would push both onto the absent pile, where they are
    silently forgiven. They are present and wrong, so they belong in the
    invalid list where a maintainer sees them and fixes the mapping.
    """
    mod = _load_module()
    checks: list[dict[str, Any]] = [{"id": "BAD-001", "sp_category": category}]

    assert mod.mapped_count(checks) == 0
    assert mod.invalid_categories(checks) == {str(category): ["BAD-001"]}

    rendered = "\n".join(mod.render(checks, mod.build_coverage(checks)))
    assert "INVALID sp_category VALUES" in rendered
    assert str(category) in rendered


def test_every_spine_category_appears_even_with_no_checks() -> None:
    """All seventeen rows are present; the empty ones are the point."""
    mod = _load_module()
    coverage = mod.build_coverage([])

    assert set(coverage) == set(mod.SPINE)
    assert len(coverage) == 17
    rendered = "\n".join(mod.render([], coverage))
    for category in mod.SPINE:
        assert category in rendered


# Valid, invalid, and absent in one fixture, so a CLI run exercises every
# classification branch the report can take.
_CLI_CHECKS: list[dict[str, Any]] = [
    {"id": "OPS-001", "sp_category": "SP-09", "verification_class": "RUNTIME-CONFIG"},
    {"id": "OPS-002", "sp_category": "SP-11", "verification_class": "MANUAL"},
    {"id": "BAD-001", "sp_category": "SP-99"},
    {"id": "FOUND-001"},
]


def _run_cli(
    monkeypatch: pytest.MonkeyPatch, output: str, capsys: pytest.CaptureFixture[str]
) -> str:
    """Invoke `main()` against the fixture check list and return its stdout.

    Args:
        monkeypatch: pytest fixture used to stub the manifest reader and argv.
        output: Value for the `--output` flag.
        capsys: pytest fixture capturing stdout.

    Returns:
        Everything the run printed.
    """
    mod = _load_module()
    monkeypatch.setattr(mod, "load_checks", lambda: _CLI_CHECKS)
    monkeypatch.setattr(
        mod.sys, "argv", ["spine-coverage.py", "--output", output], raising=True
    )
    assert mod.main() == 0, "the report is a diagnostic; it must never gate a build"
    return capsys.readouterr().out


def test_cli_table_output_reports_counts_and_invalid_values(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default rendering names the invalid mapping instead of hiding it."""
    out = _run_cli(monkeypatch, "table", capsys)

    assert "manifest checks: 4" in out
    assert "mapped to a spine category: 2" in out
    assert "unmapped: 2" in out
    assert "INVALID sp_category VALUES" in out
    assert "SP-99" in out
    assert "2/17 spine categories" in out


def test_cli_json_output_carries_the_same_numbers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The machine-readable branch must not disagree with the table branch.

    Two renderers computing coverage independently is how a report starts
    telling two different stories about the same manifest.
    """
    payload = json.loads(_run_cli(monkeypatch, "json", capsys))

    assert payload["total_checks"] == 4
    assert payload["mapped_checks"] == 2
    assert payload["invalid_categories"] == {"SP-99": ["BAD-001"]}
    assert payload["coverage"]["SP-09"] == ["OPS-001"]
    assert payload["coverage"]["SP-11"] == ["OPS-002"]
    assert "SP-99" not in payload["coverage"]
    assert len(payload["uncovered"]) == 15


# `load_checks()` must degrade to an empty list on every way the manifest read
# can fail, rather than letting FileNotFoundError, a YAML parse error, or an
# AttributeError on a non-mapping root escape and crash a diagnostic that
# documents itself as always exiting 0. Each test below points MANIFEST_PATH
# at a controlled fixture (never the real manifest) and asserts on the actual
# observable contract: a zero-check return, a stderr warning naming the
# failure, and `main()` still exiting 0 and printing a report.


def test_load_checks_reports_missing_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A manifest path that does not exist degrades to no checks, not a crash."""
    mod = _load_module()
    missing = tmp_path / "does-not-exist.yaml"
    monkeypatch.setattr(mod, "MANIFEST_PATH", missing)

    assert mod.load_checks() == []

    err = capsys.readouterr().err
    assert "warning" in err
    assert str(missing) in err


def test_load_checks_reports_malformed_yaml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unparseable YAML degrades to no checks instead of raising ScannerError."""
    mod = _load_module()
    bad_yaml = tmp_path / "manifest.yaml"
    bad_yaml.write_text("checks: [unterminated\n", encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST_PATH", bad_yaml)

    assert mod.load_checks() == []

    err = capsys.readouterr().err
    assert "warning" in err
    assert "malformed" in err


def test_load_checks_reports_non_mapping_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A bare-list YAML root degrades to no checks instead of AttributeError.

    ``data.get("checks", [])`` on a plain list raises ``AttributeError: 'list'
    object has no attribute 'get'`` with no guard; the isinstance check is
    what turns that crash into a named, recoverable warning.
    """
    mod = _load_module()
    list_root = tmp_path / "manifest.yaml"
    list_root.write_text("- OPS-001\n- OPS-002\n", encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST_PATH", list_root)

    assert mod.load_checks() == []

    err = capsys.readouterr().err
    assert "warning" in err
    assert "non-mapping root" in err


def test_load_checks_reports_missing_pyyaml(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A PyYAML-absent environment degrades to no checks instead of ImportError.

    The real crash happens at module import time (`import yaml` used to be
    unconditional at module scope); this test exercises the equivalent
    degraded state by flipping the availability flag the deferred import
    sets, which is the only part of that failure mode `load_checks` can
    observe once the module has already loaded.
    """
    mod = _load_module()
    monkeypatch.setattr(mod, "_YAML_AVAILABLE", False)

    assert mod.load_checks() == []

    err = capsys.readouterr().err
    assert "warning" in err
    assert "pyyaml" in err.lower()


def test_cli_survives_and_reports_when_manifest_is_unreadable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`main()` still exits 0 and renders a report when the manifest is gone.

    This is the end-to-end version of the four `load_checks` tests above: it
    confirms the degraded path reaches `main` and does not merely stay
    contained inside `load_checks` itself.
    """
    mod = _load_module()
    missing = tmp_path / "does-not-exist.yaml"
    monkeypatch.setattr(mod, "MANIFEST_PATH", missing)
    monkeypatch.setattr(mod.sys, "argv", ["spine-coverage.py"], raising=True)

    assert mod.main() == 0, "an unreadable manifest must not change the exit code"

    captured = capsys.readouterr()
    assert "warning" in captured.err
    assert "manifest checks: 0" in captured.out
