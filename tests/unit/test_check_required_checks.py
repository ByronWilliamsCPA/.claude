"""Unit tests for scripts/check-required-checks.py validator logic."""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
_SCRIPT_PATH = SCRIPTS_DIR / "check-required-checks.py"

spec = importlib.util.spec_from_file_location("check_required_checks", _SCRIPT_PATH)
assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
crc = importlib.util.module_from_spec(spec)
assert isinstance(spec.loader, importlib.abc.Loader)
# Register in sys.modules so the @dataclass decorator can resolve __module__.
sys.modules["check_required_checks"] = crc
spec.loader.exec_module(crc)

FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"


@pytest.mark.unit
def test_single_job_no_name_produces_workflow_prefixed_check() -> None:
    workflow_yaml = (FIXTURES / "single_job_no_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Pipeline / build"}


@pytest.mark.unit
def test_job_with_name_uses_name_field() -> None:
    workflow_yaml = (FIXTURES / "single_job_with_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Pipeline / CI Gate"}


@pytest.mark.unit
def test_workflow_without_name_omits_prefix() -> None:
    workflow_yaml = (FIXTURES / "no_workflow_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Check REUSE Compliance"}


@pytest.mark.unit
def test_no_workflow_name_no_job_name_uses_bare_job_key() -> None:
    workflow_yaml = (FIXTURES / "no_name_no_prefix.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"build"}


@pytest.mark.unit
def test_matrix_one_param_expands() -> None:
    workflow_yaml = (FIXTURES / "matrix_one_param.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Tests / Test Python 3.10",
        "Tests / Test Python 3.11",
        "Tests / Test Python 3.12",
    }


@pytest.mark.unit
def test_matrix_two_params_cartesian_expansion() -> None:
    workflow_yaml = (FIXTURES / "matrix_two_params.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Test ubuntu-latest 3.11",
        "Test ubuntu-latest 3.12",
        "Test macos-latest 3.11",
        "Test macos-latest 3.12",
    }


@pytest.mark.unit
def test_include_only_matrix_emits_raw_template_without_interpolation() -> None:
    workflow_yaml = (FIXTURES / "matrix_include_only.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    # include-only matrices have no top-level axes, so the validator
    # cannot interpolate ${{ matrix.x }} references. The raw template
    # is emitted; downstream CI-022 will flag this as needing registry coverage.
    assert produced == {"Test ${{ matrix.python }}"}


@pytest.mark.unit
def test_registered_reusable_workflow_resolved_via_registry() -> None:
    workflow_yaml = (FIXTURES / "reusable_registered.yml").read_text()
    registry = {
        "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml": {
            "produces": ["CI Gate"],
            "source_repo": "ByronWilliamsCPA/.github",
            "last_verified": "2026-05-08",
        },
    }
    produced = crc.extract_produced_check_names(workflow_yaml, registry=registry)
    assert produced == {"CI Gate"}


@pytest.mark.unit
def test_unregistered_reusable_workflow_returns_sentinel() -> None:
    workflow_yaml = (FIXTURES / "reusable_unregistered.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert any(name.startswith("__UNREGISTERED__:") for name in produced)
    assert (
        "__UNREGISTERED__:SomeOrg/private-actions/.github/workflows/build.yml"
        in produced
    )


@pytest.mark.unit
def test_diff_required_vs_produced_flags_missing_producer() -> None:
    findings = crc.diff_required_vs_produced(
        required={"CI Gate", "REUSE"},
        produced={"CI Gate"},
        required_checks_meta={
            "REUSE": {"produced_by": ".github/workflows/reuse.yml"},
        },
    )
    assert len(findings) == 1
    assert findings[0].check_id == "CI-022"
    assert "REUSE" in findings[0].message
    assert ".github/workflows/reuse.yml" in findings[0].message


@pytest.mark.unit
def test_diff_required_vs_produced_flags_unregistered_reusable() -> None:
    findings = crc.diff_required_vs_produced(
        required={"CI Gate"},
        produced={
            "CI Gate",
            f"{crc._UNREGISTERED_PREFIX}SomeOrg/x/.github/workflows/y.yml",
        },
        required_checks_meta={},
    )
    assert any(
        "missing from docs/reusable-workflow-jobs.yaml" in f.message for f in findings
    )


@pytest.mark.unit
def test_diff_required_vs_branch_protection_missing_and_extra() -> None:
    findings = crc.diff_required_vs_branch_protection(
        required={"CI Gate", "REUSE"},
        contexts=["CI Gate", "Stale Check"],
    )
    messages = [f.message for f in findings]
    assert any("REUSE" in m and "missing" in m for m in messages)
    assert any("Stale Check" in m and "does not list" in m for m in messages)


@pytest.mark.unit
def test_diff_required_vs_branch_protection_exact_match_no_findings() -> None:
    findings = crc.diff_required_vs_branch_protection(
        required={"CI Gate"},
        contexts=["CI Gate"],
    )
    assert findings == []


@pytest.mark.unit
def test_registry_freshness_flags_stale_entries() -> None:
    from datetime import date

    registry = {
        "fresh": {"last_verified": "2026-05-01"},
        "stale": {"last_verified": "2025-01-01"},
        "missing": {},
    }
    findings = crc.check_registry_freshness(
        registry=registry,
        today=date(2026, 5, 8),
        max_age_days=90,
    )
    paths = [f.message for f in findings]
    assert any("stale" in m for m in paths)
    assert any("missing" in m and "last_verified" in m for m in paths)
    assert not any("fresh" in m for m in paths)


@pytest.mark.unit
def test_registry_freshness_flags_unparseable_last_verified() -> None:
    from datetime import date

    findings = crc.check_registry_freshness(
        registry={
            "ByronWilliamsCPA/.github/.github/workflows/foo.yml": {
                "last_verified": "not-a-date",
            },
        },
        today=date(2026, 5, 8),
    )
    assert len(findings) == 1
    assert findings[0].check_id == "CI-024"
    assert "unparseable" in findings[0].message
    assert "not-a-date" in findings[0].message
