"""Unit tests for scripts/check-repo-compliance.py BP-4/BP-5 ruleset awareness."""

from __future__ import annotations

import json

import pytest

from tests.unit._load_check_repo_compliance import load_module

crc = load_module()


@pytest.mark.unit
def test_signatures_enforced_via_ruleset(monkeypatch):
    """BP-4: ruleset evaluation endpoint returns required_signatures rule."""
    rules = json.dumps([{"type": "required_signatures"}])

    def fake_gh(path):
        if "/rules/" in path:
            return (rules, None)
        msg = f"Unexpected gh() call to {path}"
        raise AssertionError(msg)

    monkeypatch.setattr(crc, "gh", fake_gh)
    assert crc._signatures_enforced("BW", ".claude", "main") is True


@pytest.mark.unit
def test_signatures_enforced_falls_back_to_classic(monkeypatch):
    """BP-4: empty ruleset result falls back to classic protection enabled."""

    def fake_gh(path):
        if "/rules/" in path:
            return ("[]", None)
        return (json.dumps({"enabled": True}), None)

    monkeypatch.setattr(crc, "gh", fake_gh)
    assert crc._signatures_enforced("BW", ".claude", "main") is True


@pytest.mark.unit
def test_signatures_not_enforced_anywhere(monkeypatch):
    """BP-4: both ruleset and classic return no signature requirement."""

    def fake_gh(path):
        if "/rules/" in path:
            return ("[]", None)
        return (json.dumps({"enabled": False}), None)

    monkeypatch.setattr(crc, "gh", fake_gh)
    assert crc._signatures_enforced("BW", ".claude", "main") is False


@pytest.mark.unit
def test_admins_not_enforced_when_org_admin_bypass(monkeypatch):
    """BP-5: org ruleset with RepositoryRole id=5 bypass returns False."""
    rules = json.dumps(
        [
            {
                "type": "required_signatures",
                "ruleset_source_type": "Organization",
                "ruleset_source": "BW",
                "ruleset_id": 99,
            }
        ]
    )
    ruleset = json.dumps(
        {
            "bypass_actors": [
                {
                    "actor_type": "RepositoryRole",
                    "actor_id": 5,
                    "bypass_mode": "always",
                },
            ],
        }
    )

    def fake_gh(path):
        if "/rules/branches/" in path:
            return (rules, None)
        if "/rulesets/99" in path:
            return (ruleset, None)
        return (None, "not found")

    monkeypatch.setattr(crc, "gh", fake_gh)
    assert crc._admins_enforced("BW", ".claude", "main") is False


@pytest.mark.unit
def test_branch_protection_exempt_via_catalog():
    """Catalog flag drives exemption; catalog is the source of truth."""
    catalog = {
        "williaby/homelab-agent-configs": {"branchProtectionExempt": True},
        "williaby/other-repo": {"branchProtectionExempt": False},
        "williaby/no-flag": {},
    }
    assert crc.is_branch_protection_exempt("williaby/homelab-agent-configs", catalog)
    assert not crc.is_branch_protection_exempt("williaby/other-repo", catalog)
    assert not crc.is_branch_protection_exempt("williaby/no-flag", catalog)


@pytest.mark.unit
def test_branch_protection_exempt_fallback_when_catalog_missing():
    """When catalog is empty, fallback set still recognizes homelab repo."""
    assert crc.is_branch_protection_exempt("williaby/homelab-agent-configs", {})
    assert not crc.is_branch_protection_exempt("williaby/other-repo", {})


@pytest.mark.unit
def test_check_repo_marks_exempt_repos_na_for_branch_protection() -> None:
    """check_repo sets bp_4/bp_5 to N/A and ci_020 to PASS for exempt repos."""
    from unittest.mock import patch

    mod = load_module()
    catalog = {"williaby/homelab-agent-configs": {"branchProtectionExempt": True}}
    with (
        patch.object(mod, "file_exists", return_value=True),
        patch.object(mod, "_signatures_enforced", return_value=True),
        patch.object(mod, "_admins_enforced", return_value=True),
        patch.object(mod, "applies_to_api_repos", return_value=False),
    ):
        result = mod.check_repo("williaby", "homelab-agent-configs", catalog)
    assert result.bp_4 == "N/A"
    assert result.bp_5 == "N/A"
    assert result.ci_020 == "PASS"


@pytest.mark.unit
def test_check_repo_fails_ci020_when_renovate_missing() -> None:
    """check_repo sets ci_020 to FAIL when renovate.json is absent."""
    from unittest.mock import patch

    mod = load_module()
    with (
        patch.object(mod, "file_exists", return_value=False),
        patch.object(mod, "_signatures_enforced", return_value=False),
        patch.object(mod, "_admins_enforced", return_value=False),
        patch.object(mod, "applies_to_api_repos", return_value=False),
    ):
        result = mod.check_repo("ByronWilliamsCPA", "test-repo", {})
    assert result.ci_020 == "FAIL"


@pytest.mark.unit
def test_admins_enforced_returns_false_when_bypass_actor_id_5_present(
    monkeypatch,
) -> None:
    """_admins_enforced returns False when a RepositoryRole actor_id=5 bypass exists."""
    mod = load_module()
    rules = json.dumps(
        [
            {
                "ruleset_source_type": "Organization",
                "ruleset_source": "testorg",
                "ruleset_id": 99,
                "type": "required_signatures",
            }
        ]
    )
    ruleset_with_bypass = json.dumps(
        {
            "bypass_actors": [
                {
                    "actor_type": "RepositoryRole",
                    "actor_id": 5,
                    "bypass_mode": "always",
                }
            ],
            "rules": [],
        }
    )

    call_count = 0

    def fake_gh(path: str):
        nonlocal call_count
        call_count += 1
        if "/rules/branches/" in path:
            return (rules, None)
        return (ruleset_with_bypass, None)

    monkeypatch.setattr(mod, "gh", fake_gh)
    result = mod._admins_enforced("testorg", "testrepo", "main")
    assert result is False


@pytest.mark.unit
def test_admins_enforced_returns_true_when_no_bypass(monkeypatch) -> None:
    """_admins_enforced returns True when the ruleset has no admin bypass actors."""
    mod = load_module()
    rules = json.dumps(
        [
            {
                "ruleset_source_type": "Organization",
                "ruleset_source": "testorg",
                "ruleset_id": 99,
                "type": "required_signatures",
            }
        ]
    )
    clean_ruleset = json.dumps({"bypass_actors": [], "rules": []})

    def fake_gh(path: str):
        if "/rules/branches/" in path:
            return (rules, None)
        return (clean_ruleset, None)

    monkeypatch.setattr(mod, "gh", fake_gh)
    result = mod._admins_enforced("testorg", "testrepo", "main")
    assert result is True
