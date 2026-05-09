"""Tests for setup_repo_rulesets.py."""

import json

import pytest

from scripts.setup_org_rulesets import SoloDevViolationError
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
