"""Unit tests for scripts/check-required-checks.py validator logic."""

from __future__ import annotations

import importlib.abc
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
_SCRIPT_PATH = SCRIPTS_DIR / "check-required-checks.py"

spec = importlib.util.spec_from_file_location("check_required_checks", _SCRIPT_PATH)
assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
crc = importlib.util.module_from_spec(spec)
assert isinstance(spec.loader, importlib.abc.Loader)
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
