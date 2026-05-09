"""Integration tests: full validator run against fake-repo fixture."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.unit._load_check_required_checks import load_module

crc = load_module()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"
FAKE_REPO = FIXTURES / "fake_repo"
MANIFEST = FAKE_REPO / "manifest_input.yaml"
REGISTRY = FIXTURES / "registry_input.yaml"


@pytest.mark.integration
def test_compliant_repo_emits_no_findings(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(
        crc,
        "fetch_branch_protection_contexts",
        return_value=["Python CI / CI Gate", "Check REUSE Compliance"],
    ):
        exit_code = crc.main(
            [
                "--repo-path",
                str(FAKE_REPO),
                "--manifest",
                str(MANIFEST),
                "--registry",
                str(REGISTRY),
                "--repo-slug",
                "fake/repo",
                "--check-bp",
                "--today",
                "2026-05-08",
            ]
        )
    captured = capsys.readouterr()
    findings = json.loads(captured.out)
    assert findings == []
    assert exit_code == 0


@pytest.mark.integration
def test_branch_protection_drift_emits_ci023(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch.object(
        crc,
        "fetch_branch_protection_contexts",
        return_value=["Python CI / CI Gate"],  # missing "Check REUSE Compliance"
    ):
        exit_code = crc.main(
            [
                "--repo-path",
                str(FAKE_REPO),
                "--manifest",
                str(MANIFEST),
                "--registry",
                str(REGISTRY),
                "--repo-slug",
                "fake/repo",
                "--check-bp",
                "--today",
                "2026-05-08",
            ]
        )
    findings = json.loads(capsys.readouterr().out)
    ci023 = [f for f in findings if f["check_id"] == "CI-023"]
    assert len(ci023) == 1
    assert "Check REUSE Compliance" in ci023[0]["message"]
    assert "missing from branch protection" in ci023[0]["message"]
    assert exit_code == 1
