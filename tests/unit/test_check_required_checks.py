"""Unit tests for scripts/check-required-checks.py validator logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._load_check_required_checks import load_module

crc = load_module()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"


@pytest.mark.unit
def test_single_job_no_name_produces_bare_job_key() -> None:
    # GitHub does not prepend the workflow's top-level name: to inline job
    # check names. With workflow `name: Pipeline` and unnamed job `build`,
    # the produced check name is just `build`.
    workflow_yaml = (FIXTURES / "single_job_no_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"build"}


@pytest.mark.unit
def test_job_with_name_uses_name_field() -> None:
    # GitHub uses the job's name: verbatim for inline jobs. The workflow's
    # top-level `name: Pipeline` is NOT prefixed onto the check name.
    workflow_yaml = (FIXTURES / "single_job_with_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"CI Gate"}


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
    # The workflow's top-level `name: Tests` is NOT prefixed onto inline
    # matrix-job check names. Only the interpolated job name is reported.
    workflow_yaml = (FIXTURES / "matrix_one_param.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Test Python 3.10",
        "Test Python 3.11",
        "Test Python 3.12",
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


@pytest.mark.unit
def test_fetch_branch_protection_contexts_handles_null_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repos with protection but no required_status_checks return null from --jq."""
    import subprocess

    class _FakeResult:
        returncode = 0
        stdout = "null\n"

    def _fake_run(*args, **kwargs):
        return _FakeResult()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    contexts = crc.fetch_branch_protection_contexts("fake/repo")
    assert contexts == []
