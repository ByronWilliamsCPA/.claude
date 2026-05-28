"""Regression suite for the compliance auditor against seeded fixture repos.

Two layers, both deterministic and API-free:

1. Structural seeding tests assert each fixture still contains (or lacks) the
   content that makes it a control or a defect. They catch an accidental edit
   that silently un-seeds a defect.
2. Auditor tests run the local per-check auditor
   (``check-repo-compliance.py`` local mode) against every fixture and assert
   the control PASSES each covered check while each defect FAILS its own check.
   They catch a regression in the auditor logic itself.

The separate shell runner (``scripts/run-auditor-regression.sh``) exercises the
same logic through the CLI surface and documents the contract for running the
full LLM auditor weekly. These tests are the fast, in-CI guard.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._load_check_repo_compliance import load_module

crc = load_module()

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "test_fixtures"
    / "compliance_auditor"
)

# (defect directory name, check id the defect must trip)
DEFECTS = [
    ("defect_FOUND-001", "FOUND-001"),
    ("defect_FOUND-002", "FOUND-002"),
    ("defect_CI-028", "CI-028"),
    ("defect_CI-043", "CI-043"),
    ("defect_CI-061", "CI-061"),
    ("defect_CI-018", "CI-018"),
]

COVERED_CHECKS = [check_id for _, check_id in DEFECTS]


# --------------------------------------------------------------------------- #
# Layer 1: structural seeding                                                 #
# --------------------------------------------------------------------------- #


@pytest.mark.integration
def test_control_has_security_md() -> None:
    assert (FIXTURE_ROOT / "control" / "SECURITY.md").exists()


@pytest.mark.integration
def test_control_has_contributing_md() -> None:
    assert (FIXTURE_ROOT / "control" / "CONTRIBUTING.md").exists()


@pytest.mark.integration
def test_defect_found001_missing_security_md() -> None:
    assert not (FIXTURE_ROOT / "defect_FOUND-001" / "SECURITY.md").exists()


@pytest.mark.integration
def test_defect_found002_missing_contributing_md() -> None:
    assert not (FIXTURE_ROOT / "defect_FOUND-002" / "CONTRIBUTING.md").exists()


@pytest.mark.integration
def test_defect_ci028_ruleset_entry_missing_integration_id() -> None:
    ruleset = (
        FIXTURE_ROOT
        / "defect_CI-028"
        / "docs"
        / "reference"
        / "org-rulesets"
        / "baseline.json"
    )
    content = ruleset.read_text()
    assert "integration_id" in content, "fixture must still be a ruleset file"
    # At least one required-status-check context must lack the integration_id pin.
    assert content.count("integration_id") < content.count('"context"'), (
        "CI-028 fixture must have an entry missing integration_id"
    )


@pytest.mark.integration
def test_defect_ci043_has_privileged_trigger_with_checkout() -> None:
    workflow = FIXTURE_ROOT / "defect_CI-043" / ".github" / "workflows" / "labeler.yml"
    content = workflow.read_text()
    assert "pull_request_target" in content or "workflow_run" in content, (
        "CI-043 fixture must use a privileged trigger"
    )
    assert "actions/checkout" in content, "CI-043 fixture must check out untrusted code"


@pytest.mark.integration
def test_defect_ci061_has_unpinned_image() -> None:
    compose = (
        FIXTURE_ROOT / "defect_CI-061" / "services" / "renovate" / "docker-compose.yml"
    )
    content = compose.read_text()
    assert "renovate/renovate" in content, "fixture must reference the renovate image"
    assert "@sha256:" not in content, "CI-061 fixture image must NOT be digest-pinned"


@pytest.mark.integration
def test_defect_ci018_release_lacks_slsa_job() -> None:
    release = FIXTURE_ROOT / "defect_CI-018" / ".github" / "workflows" / "release.yml"
    content = release.read_text()
    assert "slsa-framework/slsa-github-generator" not in content, (
        "CI-018 fixture release.yml must NOT contain a SLSA provenance job"
    )


# --------------------------------------------------------------------------- #
# Layer 2: auditor pass/fail against the corpus                               #
# --------------------------------------------------------------------------- #


@pytest.mark.integration
@pytest.mark.parametrize("check_id", COVERED_CHECKS)
def test_control_passes_every_covered_check(check_id: str) -> None:
    result = crc.audit_local(FIXTURE_ROOT / "control", check_id)
    assert result["status"] == "pass", (
        f"control must PASS {check_id}, got {result['status']}: {result['detail']}"
    )


@pytest.mark.integration
@pytest.mark.parametrize(("defect_dir", "check_id"), DEFECTS)
def test_defect_fails_its_own_check(defect_dir: str, check_id: str) -> None:
    result = crc.audit_local(FIXTURE_ROOT / defect_dir, check_id)
    assert result["status"] == "fail", (
        f"{defect_dir} must FAIL {check_id}, got {result['status']}: {result['detail']}"
    )


@pytest.mark.integration
def test_audit_local_rejects_unknown_check() -> None:
    with pytest.raises(KeyError):
        crc.audit_local(FIXTURE_ROOT / "control", "NOPE-999")
