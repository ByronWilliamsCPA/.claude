"""Tests for setup_repo_rulesets.py."""

import json

import pytest

from scripts.setup_org_rulesets import EXIT_GH_FAILURE, SoloDevViolationError
from scripts.setup_repo_rulesets import apply, main


def test_repo_script_rejects_required_reviews(tmp_path):
    body = tmp_path / "body.json"
    body.write_text(
        json.dumps(
            {
                "name": "test",
                "rules": [
                    {
                        "type": "pull_request",
                        "parameters": {"required_approving_review_count": 1},
                    }
                ],
            }
        )
    )
    with pytest.raises(SoloDevViolationError):
        apply("BW/r", body, None, dry_run=True)


def test_repo_script_dry_run_makes_no_api_calls(monkeypatch, tmp_path, capsys):
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"name": "test", "rules": []}))
    called = []
    monkeypatch.setattr(
        "subprocess.check_output", lambda *a, **k: called.append("check_output") or ""
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: called.append("run"))
    apply("BW/r", body, None, dry_run=True)
    assert "run" not in called
    assert "DRY RUN" in capsys.readouterr().out


def test_repo_script_uses_repo_endpoint_in_dry_run(monkeypatch, tmp_path, capsys):
    """Dry-run output should reference the repo path, not the org path."""
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"name": "test", "rules": []}))
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: "")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)
    apply("BW/my-repo", body, None, dry_run=True)
    out = capsys.readouterr().out
    assert "BW/my-repo" in out
    assert "ruleset 'test'" in out


def test_main_distinguishes_missing_body_from_missing_gh(tmp_path, capsys):
    """A missing --body path emits 'body file not found', not 'gh CLI not on PATH'."""
    missing_body = tmp_path / "does-not-exist.json"
    rc = main(["--repo", "BW/x", "--body", str(missing_body)])
    assert rc == EXIT_GH_FAILURE
    err = capsys.readouterr().err
    assert "body file not found" in err
    assert "gh CLI" not in err


def test_main_reports_gh_not_on_path(monkeypatch, tmp_path, capsys):
    """A missing gh binary emits 'gh CLI not on PATH', not 'body file not found'."""
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"name": "test", "rules": []}))

    def raise_gh_not_found(*_a, **_k):
        exc = FileNotFoundError(2, "No such file or directory")
        exc.filename = "gh"
        raise exc

    monkeypatch.setattr("subprocess.check_output", raise_gh_not_found)
    rc = main(["--repo", "BW/x", "--body", str(body)])
    assert rc == EXIT_GH_FAILURE
    err = capsys.readouterr().err
    assert "gh CLI not on PATH" in err
    assert "body file not found" not in err


def test_main_returns_exit_solo_dev_violation_on_bad_body(tmp_path, capsys):
    from scripts.setup_org_rulesets import EXIT_SOLO_DEV_VIOLATION

    body = tmp_path / "body.json"
    body.write_text(
        json.dumps(
            {
                "name": "bad",
                "rules": [
                    {
                        "type": "pull_request",
                        "parameters": {"required_approving_review_count": 3},
                    }
                ],
            }
        )
    )
    rc = main(["--repo", "BW/x", "--body", str(body), "--dry-run"])
    assert rc == EXIT_SOLO_DEV_VIOLATION
    assert "REFUSED" in capsys.readouterr().err
