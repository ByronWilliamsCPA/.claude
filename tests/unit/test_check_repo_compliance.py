"""Unit tests for scripts/check-repo-compliance.py BP-4/BP-5 ruleset awareness."""

from __future__ import annotations

import json

import pytest

from tests.unit._load_check_repo_compliance import load_module

crc = load_module()

# Shared fixture: a ruleset rules payload with one required_signatures rule.
_RULESET_RULES_FIXTURE = json.dumps(
    [
        {
            "ruleset_source_type": "Organization",
            "ruleset_source": "testorg",
            "ruleset_id": 99,
            "type": "required_signatures",
        }
    ]
)


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
def test_check_repo_marks_exempt_repos_na_for_branch_protection(monkeypatch) -> None:
    """check_repo sets bp_4/bp_5 to N/A and ci_020 to PASS for exempt repos."""
    catalog = {"williaby/homelab-agent-configs": {"branchProtectionExempt": True}}

    mock_sig_calls: list[object] = []
    mock_admins_calls: list[object] = []

    def fake_sig(*args, **kwargs):
        mock_sig_calls.append(args)
        return True

    def fake_admins(*args, **kwargs):
        mock_admins_calls.append(args)
        return True

    monkeypatch.setattr(crc, "file_exists", lambda *a, **kw: True)
    monkeypatch.setattr(crc, "_signatures_enforced", fake_sig)
    monkeypatch.setattr(crc, "_admins_enforced", fake_admins)
    monkeypatch.setattr(crc, "applies_to_api_repos", lambda *a, **kw: False)

    result = crc.check_repo("williaby", "homelab-agent-configs", catalog)

    assert result.bp_4 == "N/A"
    assert result.bp_5 == "N/A"
    assert result.ci_020 == "PASS"
    assert result.ci_021 == "N/A"
    assert not mock_sig_calls, (
        "_signatures_enforced must not be called for exempt repos"
    )
    assert not mock_admins_calls, "_admins_enforced must not be called for exempt repos"


@pytest.mark.unit
def test_check_repo_fails_ci020_when_renovate_missing(monkeypatch) -> None:
    """check_repo sets ci_020 to FAIL when renovate.json is absent."""
    monkeypatch.setattr(crc, "file_exists", lambda *a, **kw: False)
    monkeypatch.setattr(crc, "_signatures_enforced", lambda *a, **kw: False)
    monkeypatch.setattr(crc, "_admins_enforced", lambda *a, **kw: False)
    monkeypatch.setattr(crc, "applies_to_api_repos", lambda *a, **kw: False)

    result = crc.check_repo("ByronWilliamsCPA", "test-repo", {})
    assert result.ci_020 == "FAIL"


@pytest.mark.unit
def test_admins_enforced_uses_repo_path_for_repository_scoped_ruleset(
    monkeypatch,
) -> None:
    """_admins_enforced resolves repos/ URL for Repository-scoped rulesets."""
    repo_rules = json.dumps(
        [
            {
                "ruleset_source_type": "Repository",
                "ruleset_source": "testorg",
                "ruleset_id": 77,
                "type": "required_signatures",
            }
        ]
    )
    clean_ruleset = json.dumps({"bypass_actors": [], "rules": []})
    seen_paths: list[str] = []

    def fake_gh(path: str) -> tuple[str, None]:
        seen_paths.append(path)
        if "/rules/branches/" in path:
            return (repo_rules, None)
        return (clean_ruleset, None)

    monkeypatch.setattr(crc, "gh", fake_gh)
    result = crc._admins_enforced("testorg", "testrepo", "main")
    assert result is True
    ruleset_calls = [p for p in seen_paths if "rulesets/77" in p]
    assert any("repos/testorg/testrepo/rulesets/77" in p for p in ruleset_calls), (
        f"Expected repos/...rulesets path for Repository-scoped ruleset, got: {ruleset_calls}"
    )


@pytest.mark.unit
def test_admins_enforced_returns_true_when_no_bypass(monkeypatch) -> None:
    """_admins_enforced returns True when the ruleset has no admin bypass actors."""
    clean_ruleset = json.dumps({"bypass_actors": [], "rules": []})

    def fake_gh(path: str):
        if "/rules/branches/" in path:
            return (_RULESET_RULES_FIXTURE, None)
        return (clean_ruleset, None)

    monkeypatch.setattr(crc, "gh", fake_gh)
    result = crc._admins_enforced("testorg", "testrepo", "main")
    assert result is True
