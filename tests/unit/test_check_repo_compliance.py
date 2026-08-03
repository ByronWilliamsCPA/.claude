"""Unit tests for check-repo-compliance.py: BP-4/BP-5 ruleset rules, CI-020/CI-021 scoring, and exempt-repo handling."""

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
    # servesApi: false keeps the api_repos scope an explicit SKIP, so this test
    # exercises branch-protection exemption without also tripping the UNKNOWN
    # applies_to path.
    catalog = {
        "williaby/homelab-agent-configs": {
            "branchProtectionExempt": True,
            "api": {"servesApi": False},
        }
    }

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

    # Empty catalog: the repo is absent, so every applies_to scope resolves
    # UNKNOWN and the API columns report UNK rather than a silent N/A.
    result = crc.check_repo("ByronWilliamsCPA", "test-repo", {})
    assert result.ci_020 == "FAIL"
    assert result.api_001_openapi_spec == "UNK"
    assert result.scopes["api_repos"].applicability is crc.Applicability.UNKNOWN


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


# --------------------------------------------------------------------------- #
# applies_to scope resolution (tri-state)                                     #
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_resolve_applicability_returns_applies_only_for_literal_true() -> None:
    """resolve_applicability yields APPLIES only when the flag is literal True."""
    catalog = {"org/repo": {"api": {"servesApi": True}}}

    verdict = crc.resolve_applicability("org/repo", catalog, "api_repos")

    assert verdict.applicability is crc.Applicability.APPLIES
    assert verdict.raw_value is True


@pytest.mark.unit
def test_resolve_applicability_returns_skip_only_for_literal_false() -> None:
    """resolve_applicability yields SKIP only when the flag is literal False."""
    catalog = {"org/repo": {"api": {"servesApi": False}}}

    verdict = crc.resolve_applicability("org/repo", catalog, "api_repos")

    assert verdict.applicability is crc.Applicability.SKIP
    assert verdict.raw_value is False


@pytest.mark.unit
def test_resolve_applicability_unknown_when_flag_absent_from_entry() -> None:
    """A missing flag key resolves to UNKNOWN, naming the flag in the reason."""
    catalog = {"org/repo": {}}

    verdict = crc.resolve_applicability("org/repo", catalog, "api_repos")

    assert verdict.applicability is crc.Applicability.UNKNOWN
    assert "api.servesApi" in verdict.reason
    assert "populate" in verdict.reason


@pytest.mark.unit
def test_resolve_applicability_unknown_when_flag_is_none() -> None:
    """A flag explicitly set to null resolves to UNKNOWN, not SKIP."""
    catalog = {"org/repo": {"api": {"servesApi": None}}}

    verdict = crc.resolve_applicability("org/repo", catalog, "api_repos")

    assert verdict.applicability is crc.Applicability.UNKNOWN
    assert "null" in verdict.reason


@pytest.mark.parametrize("raw_value", ["yes", 1, 0])
@pytest.mark.unit
def test_resolve_applicability_unknown_for_non_boolean_values(raw_value) -> None:
    """Non-boolean flag values resolve to UNKNOWN, including int 1 and int 0.

    Python treats ``1 == True`` and ``0 == False``, so this pins the
    implementation's ``is True`` / ``is False`` identity checks: an int flag
    must never be silently coerced into APPLIES or SKIP.
    """
    catalog = {"org/repo": {"api": {"servesApi": raw_value}}}

    verdict = crc.resolve_applicability("org/repo", catalog, "api_repos")

    assert verdict.applicability is crc.Applicability.UNKNOWN
    assert verdict.raw_value == raw_value


@pytest.mark.unit
def test_resolve_applicability_unknown_when_slug_absent_from_catalog() -> None:
    """A repo slug missing from the catalog entirely resolves to UNKNOWN."""
    verdict = crc.resolve_applicability("org/missing-repo", {}, "api_repos")

    assert verdict.applicability is crc.Applicability.UNKNOWN
    assert "org/missing-repo" in verdict.reason


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (
            {"api": {"servesApi": True}},
            "APPLIES",
        ),
        (
            {"api": None},
            "UNKNOWN",
        ),
        (
            {"api": {}},
            "UNKNOWN",
        ),
    ],
)
@pytest.mark.unit
def test_resolve_applicability_nested_flag_path(entry, expected) -> None:
    """Nested flag paths (e.g. api.servesApi) resolve through intermediate dicts."""
    catalog = {"org/repo": entry}

    verdict = crc.resolve_applicability("org/repo", catalog, "api_repos")

    assert verdict.applicability.value == expected


@pytest.mark.unit
def test_read_flag_missing_path_returns_none_and_not_found() -> None:
    """_read_flag reports found=False for a path absent from the entry."""
    value, found = crc._read_flag({}, ("api", "servesApi"))

    assert value is None
    assert found is False


@pytest.mark.unit
def test_read_flag_present_null_returns_none_and_found() -> None:
    """_read_flag distinguishes a null value present at the path from absent."""
    value, found = crc._read_flag({"api": {"servesApi": None}}, ("api", "servesApi"))

    assert value is None
    assert found is True


@pytest.mark.unit
def test_assert_scopes_reachable_flags_scope_with_zero_applies_repos() -> None:
    """Regression guard for the MkDocs silent-skip defect.

    A scope where every repo resolves to SKIP or UNKNOWN (never APPLIES) must
    surface as an unreachable-scope problem line, since that is exactly the
    fleet-wide state the MkDocs domain shipped in: publishesDocs absent or
    false everywhere, so all MKDOCS-* checks silently never ran.
    """
    results = [
        crc.RepoResult(slug="org/repo1", branch="main"),
    ]
    results[0].scopes = {
        "api_repos": crc.ScopeVerdict(
            "api_repos",
            crc.Applicability.APPLIES,
            raw_value=True,
            reason="in scope",
        ),
        "docs_repos": crc.ScopeVerdict(
            "docs_repos",
            crc.Applicability.SKIP,
            raw_value=False,
            reason="explicitly out of scope",
        ),
        "deployed_repos": crc.ScopeVerdict(
            "deployed_repos",
            crc.Applicability.APPLIES,
            raw_value=True,
            reason="in scope",
        ),
    }

    problems = crc.assert_scopes_reachable(results, {})

    assert len(problems) == 1
    assert "docs_repos" in problems[0]
    assert "mkdocs" in problems[0]


@pytest.mark.unit
def test_assert_scopes_reachable_no_problem_when_at_least_one_applies() -> None:
    """A scope with at least one APPLIES repo produces no problem line."""
    results = [
        crc.RepoResult(slug="org/repo1", branch="main"),
    ]
    results[0].scopes = {
        "api_repos": crc.ScopeVerdict(
            "api_repos",
            crc.Applicability.APPLIES,
            raw_value=True,
            reason="in scope",
        ),
        "docs_repos": crc.ScopeVerdict(
            "docs_repos",
            crc.Applicability.APPLIES,
            raw_value=True,
            reason="in scope",
        ),
        "deployed_repos": crc.ScopeVerdict(
            "deployed_repos",
            crc.Applicability.APPLIES,
            raw_value=True,
            reason="in scope",
        ),
    }

    problems = crc.assert_scopes_reachable(results, {})

    assert problems == []


@pytest.mark.unit
def test_assert_scopes_reachable_empty_results_returns_no_problems() -> None:
    """No repos means no fleet to assert reach against, so nothing is flagged."""
    problems = crc.assert_scopes_reachable([], {})

    assert problems == []


@pytest.mark.unit
def test_render_scope_summary_always_emits_skip_line_even_when_zero() -> None:
    """render_scope_summary prints a SKIP line per scope, even with zero skips."""
    lines = crc.render_scope_summary([], {})

    assert any("SKIP (publishesDocs: false)" in line for line in lines)


@pytest.mark.unit
def test_render_scope_summary_lists_unknown_repos_with_reason() -> None:
    """render_scope_summary lists each UNKNOWN repo slug with its reason."""
    result = crc.RepoResult(slug="org/unclear-repo", branch="main")
    reason = "publishesDocs absent from catalog entry; populate it"
    result.scopes = {
        "docs_repos": crc.ScopeVerdict(
            "docs_repos", crc.Applicability.UNKNOWN, None, reason
        ),
    }

    lines = crc.render_scope_summary([result], {})

    assert any(f"org/unclear-repo: {reason}" in line for line in lines)


@pytest.mark.unit
def test_load_manifest_scope_checks_covers_every_defined_scope() -> None:
    """The real manifest yields non-empty, sorted check-ID lists for every scope.

    Asserting against SCOPE_DEFINITIONS rather than a hardcoded pair means a
    scope that loses all its manifest checks fails here instead of vanishing
    from the mapping unnoticed. A loop over ``scope_checks.values()`` alone
    cannot catch that: the missing scope simply never enters the loop.
    """
    scope_checks = crc.load_manifest_scope_checks()

    missing = sorted(set(crc.SCOPE_DEFINITIONS) - set(scope_checks))
    assert not missing, f"scopes defined but carried by no manifest check: {missing}"
    for ids in scope_checks.values():
        assert len(ids) > 0
        assert ids == sorted(ids)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("body", "root_type"),
    [
        ("- CI-001\n- CI-002\n", "list"),
        ("just a string\n", "str"),
        ("", "NoneType"),
    ],
    ids=["sequence-root", "scalar-root", "empty-file"],
)
def test_load_manifest_scope_checks_degrades_on_non_mapping_root(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
    body: str,
    root_type: str,
) -> None:
    """A valid YAML document that is not a mapping degrades, it does not crash.

    `yaml.safe_load` happily returns a list, a bare scalar, or `None`. None of
    those carries `.get`, so an unguarded read raises AttributeError and kills
    the whole fleet sweep over a malformed manifest. The documented behaviour
    for an unreadable manifest is an unknown scope count, and a differently
    malformed manifest must land in the same place rather than in a traceback.
    """
    manifest = tmp_path / "standards-manifest.yaml"
    manifest.write_text(body, encoding="utf-8")
    monkeypatch.setattr(crc, "MANIFEST_PATH", manifest)

    assert crc.load_manifest_scope_checks() == {}
    assert root_type in capsys.readouterr().err
