"""Tests for setup_org_rulesets.py, focused on the solo-dev safety guard."""

import json
import subprocess

import pytest

from scripts.setup_org_rulesets import SoloDevViolation, validate_solo_dev_safe


def _completed(args=None, returncode=0):
    """Return a CompletedProcess shaped like the real subprocess.run output.

    Production code calls subprocess.run with check=True. A bare None return
    from a mock would crash any callsite that inspects .returncode, and would
    not honor check=True semantics if a returncode != 0 were ever wanted.
    """
    return subprocess.CompletedProcess(args=args or [], returncode=returncode)


def test_rejects_required_approving_reviews_gt_0():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": 1},
            }
        ]
    }
    with pytest.raises(SoloDevViolation, match="required_approving_review_count"):
        validate_solo_dev_safe(body)


def test_accepts_zero_review_count():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": 0},
            }
        ]
    }
    assert validate_solo_dev_safe(body) is None


def test_accepts_no_pull_request_rule():
    body = {"rules": [{"type": "required_signatures"}]}
    assert validate_solo_dev_safe(body) is None


def test_accepts_pull_request_without_count_param():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {"dismiss_stale_reviews_on_push": True},
            }
        ]
    }
    assert validate_solo_dev_safe(body) is None


def test_rejects_count_of_5():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": 5},
            }
        ]
    }
    with pytest.raises(SoloDevViolation, match="5"):
        validate_solo_dev_safe(body)


def test_rejects_require_code_owner_review_true():
    # With a CODEOWNERS file this forces a code-owner approval the solo
    # maintainer cannot self-grant, even when the review count is 0.
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "require_code_owner_review": True,
                },
            }
        ]
    }
    with pytest.raises(SoloDevViolation, match="require_code_owner_review"):
        validate_solo_dev_safe(body)


def test_accepts_require_code_owner_review_false():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "require_code_owner_review": False,
                },
            }
        ]
    }
    assert validate_solo_dev_safe(body) is None


def test_rejects_require_last_push_approval_true():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "require_last_push_approval": True,
                },
            }
        ]
    }
    with pytest.raises(SoloDevViolation, match="require_last_push_approval"):
        validate_solo_dev_safe(body)


def test_render_substitutes_generated_token(tmp_path):
    from scripts.setup_org_rulesets import render_body

    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "BW",
                        "name": "py",
                        "repositoryType": "python-app",
                        "branchProtectionExempt": False,
                    }
                ]
            }
        )
    )
    body = {"conditions": {"repository_name": {"include": ["__GENERATED__"]}}}
    out = render_body(body, "BW", catalog)
    assert out["conditions"]["repository_name"]["include"] == ["py"]


def test_render_passthrough_when_no_token(tmp_path):
    from scripts.setup_org_rulesets import render_body

    catalog = tmp_path / "cat.json"
    catalog.write_text(json.dumps({"repos": []}))
    body = {"conditions": {"repository_name": {"include": ["~ALL"]}}}
    out = render_body(body, "BW", catalog)
    assert out["conditions"]["repository_name"]["include"] == ["~ALL"]


def test_dry_run_makes_no_api_calls(monkeypatch, tmp_path, capsys):
    from scripts.setup_org_rulesets import apply

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "test",
                "rules": [],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))
    called = []
    monkeypatch.setattr(
        "subprocess.check_output", lambda *a, **k: called.append("check_output") or ""
    )
    monkeypatch.setattr(
        "subprocess.run", lambda *a, **k: called.append("run") or _completed()
    )
    apply("BW", body_path, None, catalog, dry_run=True)
    assert "run" not in called
    assert "DRY RUN" in capsys.readouterr().out


def test_apply_rejects_violating_body(monkeypatch, tmp_path):
    from scripts.setup_org_rulesets import SoloDevViolation, apply

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "bad",
                "rules": [
                    {
                        "type": "pull_request",
                        "parameters": {"required_approving_review_count": 2},
                    }
                ],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))
    with pytest.raises(SoloDevViolation):
        apply("BW", body_path, None, catalog, dry_run=True)


def test_target_rule_compat_rejects_push_rule_in_branch_body():
    from scripts.setup_org_rulesets import (
        TargetRuleMismatchError,
        validate_target_rule_compatibility,
    )

    body = {
        "target": "branch",
        "rules": [
            {"type": "required_signatures"},
            {
                "type": "file_path_restriction",
                "parameters": {"restricted_file_paths": []},
            },
        ],
    }
    with pytest.raises(TargetRuleMismatchError, match="file_path_restriction"):
        validate_target_rule_compatibility(body)


def test_target_rule_compat_rejects_max_file_size_in_branch_body():
    from scripts.setup_org_rulesets import (
        TargetRuleMismatchError,
        validate_target_rule_compatibility,
    )

    body = {
        "target": "branch",
        "rules": [{"type": "max_file_size", "parameters": {"max_file_size": 100}}],
    }
    with pytest.raises(TargetRuleMismatchError, match="max_file_size"):
        validate_target_rule_compatibility(body)


def test_target_rule_compat_rejects_branch_rule_in_push_body():
    from scripts.setup_org_rulesets import (
        TargetRuleMismatchError,
        validate_target_rule_compatibility,
    )

    body = {
        "target": "push",
        "rules": [
            {"type": "max_file_size", "parameters": {"max_file_size": 100}},
            {"type": "required_signatures"},
        ],
    }
    with pytest.raises(TargetRuleMismatchError, match="required_signatures"):
        validate_target_rule_compatibility(body)


def test_target_rule_compat_accepts_push_only_rules_in_push_body():
    from scripts.setup_org_rulesets import validate_target_rule_compatibility

    body = {
        "target": "push",
        "rules": [
            {
                "type": "file_path_restriction",
                "parameters": {"restricted_file_paths": []},
            },
            {"type": "max_file_size", "parameters": {"max_file_size": 100}},
        ],
    }
    assert validate_target_rule_compatibility(body) is None


def test_target_rule_compat_accepts_branch_rules_in_branch_body():
    from scripts.setup_org_rulesets import validate_target_rule_compatibility

    body = {
        "target": "branch",
        "rules": [
            {"type": "deletion"},
            {"type": "required_signatures"},
            {"type": "required_status_checks", "parameters": {}},
        ],
    }
    assert validate_target_rule_compatibility(body) is None


def test_target_rule_compat_defaults_target_to_branch():
    """An omitted target field defaults to 'branch' per GitHub API behaviour."""
    from scripts.setup_org_rulesets import (
        TargetRuleMismatchError,
        validate_target_rule_compatibility,
    )

    body = {"rules": [{"type": "max_file_size", "parameters": {"max_file_size": 100}}]}
    with pytest.raises(TargetRuleMismatchError):
        validate_target_rule_compatibility(body)


def test_detect_drift_reports_dropped_rule_types():
    from scripts.setup_org_rulesets import detect_drift

    request = {
        "rules": [
            {"type": "deletion"},
            {"type": "required_signatures"},
            {"type": "required_status_checks", "parameters": {}},
        ]
    }
    response = {"rules": [{"type": "deletion"}, {"type": "required_signatures"}]}
    drift = detect_drift(request, response)
    assert len(drift) == 1
    assert "required_status_checks" in drift[0]


def test_detect_drift_empty_when_types_match():
    from scripts.setup_org_rulesets import detect_drift

    body = {"rules": [{"type": "deletion"}, {"type": "required_signatures"}]}
    assert detect_drift(body, body) == []


def test_detect_drift_ignores_extra_rule_types_in_response():
    """Live state may include rules added by other apply paths; only dropped
    rules indicate a problem with this apply."""
    from scripts.setup_org_rulesets import detect_drift

    request = {"rules": [{"type": "deletion"}]}
    response = {"rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}
    assert detect_drift(request, response) == []


def test_main_returns_target_rule_mismatch_exit_code(monkeypatch, tmp_path):
    from scripts.setup_org_rulesets import EXIT_TARGET_RULE_MISMATCH, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "bad",
                "target": "branch",
                "rules": [
                    {"type": "max_file_size", "parameters": {"max_file_size": 100}},
                ],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))
    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_TARGET_RULE_MISMATCH


def test_main_returns_drift_exit_code(monkeypatch, tmp_path):
    """When the live ruleset is missing rules from the request, exit DRIFT."""
    from scripts.setup_org_rulesets import EXIT_DRIFT_DETECTED, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "test",
                "target": "branch",
                "rules": [
                    {"type": "deletion"},
                    {"type": "required_signatures"},
                ],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    monkeypatch.setattr(
        "scripts.setup_org_rulesets.find_existing_ruleset",
        lambda *a, **k: 999,
    )
    monkeypatch.setattr(
        "scripts.setup_org_rulesets.fetch_ruleset",
        lambda *a, **k: {"rules": [{"type": "deletion"}]},
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: _completed())

    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_DRIFT_DETECTED


def test_fetch_ruleset_success_invokes_gh_with_id(monkeypatch):
    """fetch_ruleset should call `gh api orgs/{org}/rulesets/{id}` and parse JSON."""
    from scripts.setup_org_rulesets import fetch_ruleset

    captured = {}

    def fake_check_output(argv, **kwargs):
        captured["argv"] = argv
        return json.dumps({"id": 42, "name": "ok", "rules": []})

    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    out = fetch_ruleset("BW", 42)
    assert out["id"] == 42
    assert "orgs/BW/rulesets/42" in captured["argv"]


def test_fetch_ruleset_propagates_timeout(monkeypatch):
    """A subprocess timeout in fetch_ruleset should propagate, not be swallowed."""
    from scripts.setup_org_rulesets import fetch_ruleset

    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["gh"], timeout=1)

    monkeypatch.setattr("subprocess.check_output", boom)
    with pytest.raises(subprocess.TimeoutExpired):
        fetch_ruleset("BW", 42)


def test_fetch_ruleset_wraps_parse_error_as_drift(monkeypatch):
    """Unparseable JSON from gh post-apply maps to RulesetDriftError, not raw parse error.

    Rationale: fetch_ruleset only runs after a successful apply. A parse error
    here is a drift signal (we cannot verify the apply persisted), not a gh
    failure (the gh call itself succeeded).
    """
    from scripts.setup_org_rulesets import RulesetDriftError, fetch_ruleset

    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: "not-json-blob")
    with pytest.raises(RulesetDriftError, match="unparseable JSON"):
        fetch_ruleset("BW", 42)


def test_find_existing_ruleset_uses_paginate_flag(monkeypatch):
    """Pagination is required: orgs with >30 rulesets would otherwise miss matches.

    Verifies the gh argv contains --paginate and per_page=100; a regression
    that removes pagination would silently create duplicate rulesets.
    """
    from scripts.setup_org_rulesets import find_existing_ruleset

    captured = {}

    def fake_check_output(argv, **kwargs):
        captured["argv"] = argv
        return ""

    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    find_existing_ruleset("BW", "anything")
    assert "--paginate" in captured["argv"]
    assert any("per_page=100" in str(arg) for arg in captured["argv"])


def test_main_returns_drift_when_ruleset_missing_after_apply(monkeypatch, tmp_path):
    """If POST succeeds but the new ruleset cannot be located, fail closed.

    Prior behaviour: warn-to-stderr and return EXIT_OK (drift safeguard
    silently bypassed). New behaviour: raise RulesetDriftError, return
    EXIT_DRIFT_DETECTED so CI flags the apply for human review.
    """
    from scripts.setup_org_rulesets import EXIT_DRIFT_DETECTED, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "test",
                "target": "branch",
                "rules": [{"type": "deletion"}],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    monkeypatch.setattr(
        "scripts.setup_org_rulesets.find_existing_ruleset",
        lambda *a, **k: None,
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: _completed())

    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_DRIFT_DETECTED


def test_main_drift_path_for_new_ruleset_post(monkeypatch, tmp_path):
    """POST path: existing_id is None, second find returns the new id, drift detected.

    Exercises the `live_id = existing_id or find_existing_ruleset(...)`
    fallback so a regression that swaps the warning-return for the raise
    would be caught regardless of which branch executes.
    """
    from scripts.setup_org_rulesets import EXIT_DRIFT_DETECTED, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "fresh",
                "target": "branch",
                "rules": [
                    {"type": "deletion"},
                    {"type": "required_signatures"},
                ],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    find_calls = {"n": 0}

    def fake_find(*a, **k):
        find_calls["n"] += 1
        # First call (before apply) returns None -> POST path; second
        # call (post-apply re-fetch) returns the new id.
        return None if find_calls["n"] == 1 else 777

    monkeypatch.setattr("scripts.setup_org_rulesets.find_existing_ruleset", fake_find)
    monkeypatch.setattr(
        "scripts.setup_org_rulesets.fetch_ruleset",
        lambda *a, **k: {"rules": [{"type": "deletion"}]},
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: _completed())

    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_DRIFT_DETECTED


def test_main_catches_gh_timeout(monkeypatch, tmp_path, capsys):
    """gh subprocess timeout surfaces as EXIT_GH_FAILURE with a clean message.

    The 30s timeout (#CRITICAL RAD tag in source) is the safety net against
    api.github.com hanging; if a regression removed the TimeoutExpired
    handler, this test would catch it.
    """
    from scripts.setup_org_rulesets import EXIT_GH_FAILURE, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "test",
                "rules": [],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    def hang(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["gh", "api"], timeout=30)

    monkeypatch.setattr("scripts.setup_org_rulesets.find_existing_ruleset", hang)

    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_GH_FAILURE
    assert "timed out" in capsys.readouterr().err


def test_main_catches_unparseable_gh_json(monkeypatch, tmp_path, capsys):
    """Malformed JSON line from gh ruleset list surfaces as EXIT_GH_FAILURE.

    json.JSONDecodeError used to propagate uncaught and crash with a stack
    trace; main() now catches it and exits cleanly.
    """
    from scripts.setup_org_rulesets import EXIT_GH_FAILURE, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "test",
                "rules": [],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    monkeypatch.setattr(
        "subprocess.check_output", lambda *a, **k: "not-valid-json-line"
    )
    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_GH_FAILURE
    assert "unparseable JSON" in capsys.readouterr().err


def test_main_distinguishes_missing_body_from_missing_gh(monkeypatch, tmp_path, capsys):
    """A missing --body path emits a 'body file not found' message, not 'gh CLI not on PATH'."""
    from scripts.setup_org_rulesets import EXIT_GH_FAILURE, main

    missing_body = tmp_path / "does-not-exist.json"
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    rc = main(["--org", "BW", "--body", str(missing_body), "--catalog", str(catalog)])
    assert rc == EXIT_GH_FAILURE
    err = capsys.readouterr().err
    assert "body file not found" in err
    assert "gh CLI" not in err


def test_main_catches_gh_failure(monkeypatch, tmp_path, capsys):
    """gh CalledProcessError surfaces as a clean error message and exit code 4."""
    import subprocess

    from scripts.setup_org_rulesets import EXIT_GH_FAILURE, main

    body_path = tmp_path / "body.json"
    body_path.write_text(
        json.dumps(
            {
                "name": "test",
                "rules": [],
                "conditions": {"repository_name": {"include": ["~ALL"]}},
            }
        )
    )
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))

    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, ["gh", "api"], stderr="403 Forbidden")

    monkeypatch.setattr(
        "scripts.setup_org_rulesets.find_existing_ruleset",
        lambda *a, **k: None,
    )
    monkeypatch.setattr("subprocess.run", boom)

    rc = main(
        [
            "--org",
            "BW",
            "--body",
            str(body_path),
            "--catalog",
            str(catalog),
        ]
    )
    assert rc == EXIT_GH_FAILURE
    assert "gh command failed" in capsys.readouterr().err
