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
    """A check with no `sp_category` contributes to no row and no total."""
    mod = _load_module()
    checks = [{"id": "FOUND-001"}, {"id": "FOUND-002", "sp_category": None}]

    coverage = mod.build_coverage(checks)
    assert all(ids == [] for ids in coverage.values())
    assert mod.invalid_categories(checks) == {}

    rendered = "\n".join(mod.render(checks, coverage))
    assert "mapped to a spine category: 0" in rendered
    assert "unmapped: 2" in rendered


def test_every_spine_category_appears_even_with_no_checks() -> None:
    """All seventeen rows are present; the empty ones are the point."""
    mod = _load_module()
    coverage = mod.build_coverage([])

    assert set(coverage) == set(mod.SPINE)
    assert len(coverage) == 17
    rendered = "\n".join(mod.render([], coverage))
    for category in mod.SPINE:
        assert category in rendered
