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
