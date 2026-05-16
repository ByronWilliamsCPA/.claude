"""Tests for setup_org_rulesets.py, focused on the solo-dev safety guard."""

import json

import pytest

from scripts.setup_org_rulesets import SoloDevViolation, validate_solo_dev_safe


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
    validate_solo_dev_safe(body)  # no exception


def test_accepts_no_pull_request_rule():
    body = {"rules": [{"type": "required_signatures"}]}
    validate_solo_dev_safe(body)


def test_accepts_pull_request_without_count_param():
    body = {
        "rules": [
            {
                "type": "pull_request",
                "parameters": {"dismiss_stale_reviews_on_push": True},
            }
        ]
    }
    validate_solo_dev_safe(body)


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
    monkeypatch.setattr("subprocess.run", lambda *a, **k: called.append("run"))
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
    validate_target_rule_compatibility(body)  # no exception


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
    validate_target_rule_compatibility(body)  # no exception


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
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)

    rc = main(["--org", "BW", "--body", str(body_path), "--catalog", str(catalog)])
    assert rc == EXIT_DRIFT_DETECTED


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
