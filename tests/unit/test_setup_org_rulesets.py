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


def test_main_catches_gh_failure(monkeypatch, tmp_path, capsys):
    """gh CalledProcessError surfaces as a clean error message and exit code 4."""
    import subprocess

    import scripts.setup_org_rulesets as ssor

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

    monkeypatch.setattr(ssor, "find_existing_ruleset", lambda *a, **k: None)
    monkeypatch.setattr("subprocess.run", boom)

    rc = ssor.main(
        [
            "--org",
            "BW",
            "--body",
            str(body_path),
            "--catalog",
            str(catalog),
        ]
    )
    assert rc == ssor.EXIT_GH_FAILURE
    assert "gh command failed" in capsys.readouterr().err
