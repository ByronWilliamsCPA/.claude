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
        pytest.fail(f"Unexpected gh() call to {path}")

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
