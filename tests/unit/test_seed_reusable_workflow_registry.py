"""Test the registry seed script."""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
_SCRIPT_PATH = SCRIPTS_DIR / "seed-reusable-workflow-registry.py"


def _load_seed_module():
    spec = importlib.util.spec_from_file_location(
        "seed_reusable_workflow_registry",
        _SCRIPT_PATH,
    )
    assert spec is not None, f"Script not found: {_SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_reusable_workflow_registry"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(module)
    return module


seed = _load_seed_module()

FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"


@pytest.mark.unit
def test_scan_org_repo_extracts_check_names(tmp_path: Path) -> None:
    output = tmp_path / "registry.yaml"
    seed.scan_org_repo(
        clone_path=FIXTURES / "seed_input",
        org_slug="ByronWilliamsCPA/.github",
        output_path=output,
        today="2026-05-08",
    )
    yaml = YAML(typ="safe")
    data = yaml.load(output.read_text())
    key = "ByronWilliamsCPA/.github/.github/workflows/example.yml"
    assert key in data
    # The seed script delegates to extract_produced_check_names, which now
    # emits inline job names verbatim (no workflow-level prefix). With
    # `name: Example` at the top and inline job `name: CI Gate`, the
    # produced check name is just `CI Gate`.
    assert data[key]["produces"] == ["CI Gate"]
    assert data[key]["last_verified"] == "2026-05-08"
