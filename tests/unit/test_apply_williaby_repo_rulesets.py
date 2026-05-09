"""Tests for the williaby per-repo ruleset templates and sweep script.

Covers:
- Template body shape: solo-dev guard invariant, copilot rule presence, signatures.
- Python template superset of universal: extra CI Gate context.
- Sweep script preconditions: missing catalog, missing template body.
- Sweep script tier selection: python repos route to python template, others to universal.
- Sweep script exempt skip: branchProtectionExempt repos are filtered out.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "docs" / "reference" / "repo-rulesets"
UNIVERSAL = TEMPLATE_DIR / "_williaby-template-universal.json"
PYTHON = TEMPLATE_DIR / "_williaby-template-python.json"
SWEEP_SCRIPT = REPO_ROOT / "scripts" / "apply_williaby_repo_rulesets.sh"
BASH = shutil.which("bash") or "/bin/bash"

# Tests that invoke the bash sweep script need both `bash` and `jq` on PATH.
# GitHub Actions Windows runners have neither by default, so the sweep tests
# are skipped on Windows and on any host missing either tool.
requires_sweep_runtime = pytest.mark.skipif(
    sys.platform == "win32"
    or shutil.which("bash") is None
    or shutil.which("jq") is None,
    reason="sweep script requires bash and jq on PATH",
)


def _load_body(path: Path) -> dict:
    return json.loads(path.read_text())


def _rule(body: dict, rule_type: str) -> dict | None:
    for rule in body.get("rules", []):
        if rule.get("type") == rule_type:
            return rule
    return None


@pytest.fixture
def fake_setup_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a stub setup_repo_rulesets.py that records its args.

    The sweep script invokes ``uv run python scripts/setup_repo_rulesets.py``.
    To exercise the sweep without hitting the network, we run the sweep with
    ``PATH`` rewritten to a directory whose ``uv`` is a shell shim that
    appends each invocation's args to a log file and exits 0.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "uv-invocations.log"
    shim = bin_dir / "uv"
    shim.write_text(f'#!/usr/bin/env bash\necho "$@" >> "{log}"\nexit 0\n')
    shim.chmod(0o755)
    monkeypatch.setenv(
        "PATH",
        f"{bin_dir}:{(shutil.which('jq') and Path(shutil.which('jq')).parent) or ''}:/usr/bin:/bin",
    )
    return log


# Template invariants -----------------------------------------------------


def test_universal_template_solo_dev_safe():
    body = _load_body(UNIVERSAL)
    pr_rule = _rule(body, "pull_request")
    assert pr_rule is not None
    assert pr_rule["parameters"]["required_approving_review_count"] == 0


def test_python_template_solo_dev_safe():
    body = _load_body(PYTHON)
    pr_rule = _rule(body, "pull_request")
    assert pr_rule is not None
    assert pr_rule["parameters"]["required_approving_review_count"] == 0


def test_universal_template_has_copilot_rule():
    body = _load_body(UNIVERSAL)
    copilot = _rule(body, "copilot_code_review")
    assert copilot is not None
    assert copilot["parameters"]["review_draft_pull_requests"] is False
    assert copilot["parameters"]["review_on_push"] is False


def test_python_template_has_copilot_rule():
    body = _load_body(PYTHON)
    assert _rule(body, "copilot_code_review") is not None


def test_universal_template_has_required_signatures():
    body = _load_body(UNIVERSAL)
    assert _rule(body, "required_signatures") is not None


def test_python_template_adds_ci_gate_context():
    universal_contexts = {
        c["context"]
        for c in _rule(_load_body(UNIVERSAL), "required_status_checks")["parameters"][
            "required_status_checks"
        ]
    }
    python_contexts = {
        c["context"]
        for c in _rule(_load_body(PYTHON), "required_status_checks")["parameters"][
            "required_status_checks"
        ]
    }
    assert universal_contexts <= python_contexts
    assert "CI Gate" in python_contexts
    assert "CI Gate" not in universal_contexts


def test_repo_templates_omit_repository_name_condition():
    """Repo-scoped bodies must not carry the org-scoped repository_name filter."""
    for path in (UNIVERSAL, PYTHON):
        body = _load_body(path)
        assert "repository_name" not in body.get("conditions", {}), path.name


def test_repo_templates_share_ruleset_name():
    """Both templates use the same ruleset name; per-repo scope makes collisions impossible."""
    assert _load_body(UNIVERSAL)["name"] == _load_body(PYTHON)["name"]


# Sweep script preconditions ---------------------------------------------


@requires_sweep_runtime
def test_sweep_fails_when_catalog_missing(tmp_path: Path):
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env={
            "PATH": __import__("os").environ["PATH"],
            "CATALOG": str(tmp_path / "nope.json"),
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 2
    assert "catalog not found" in result.stderr


@requires_sweep_runtime
def test_sweep_fails_when_template_missing(tmp_path: Path):
    catalog = tmp_path / "cat.json"
    catalog.write_text(json.dumps({"repos": []}))
    # Run from tmp_path so the relative TEMPLATE_DIR resolves to a missing path.
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env={
            "PATH": __import__("os").environ["PATH"],
            "CATALOG": str(catalog),
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert "template body missing" in result.stderr


# Sweep script tier selection (uses uv shim) ------------------------------


@requires_sweep_runtime
def test_sweep_routes_python_repo_to_python_template(
    tmp_path: Path, fake_setup_script: Path
):
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "williaby",
                        "name": "py-repo",
                        "repositoryType": "python-package",
                    }
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env={
            "PATH": __import__("os").environ["PATH"],
            "CATALOG": str(catalog),
            "DRY_RUN": "true",
            "LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    assert "_williaby-template-python.json" in invocations
    assert "williaby/py-repo" in invocations
    assert "--dry-run" in invocations


@requires_sweep_runtime
def test_sweep_routes_non_python_repo_to_universal_template(
    tmp_path: Path, fake_setup_script: Path
):
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "williaby",
                        "name": "docs-repo",
                        "repositoryType": "docs",
                    }
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env={
            "PATH": __import__("os").environ["PATH"],
            "CATALOG": str(catalog),
            "DRY_RUN": "true",
            "LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    assert "_williaby-template-universal.json" in invocations
    assert "_williaby-template-python.json" not in invocations


@requires_sweep_runtime
def test_sweep_skips_branch_protection_exempt_repos(
    tmp_path: Path, fake_setup_script: Path
):
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "williaby",
                        "name": "exempt-repo",
                        "repositoryType": "python-package",
                        "branchProtectionExempt": True,
                    },
                    {
                        "org": "williaby",
                        "name": "real-repo",
                        "repositoryType": "docs",
                    },
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env={
            "PATH": __import__("os").environ["PATH"],
            "CATALOG": str(catalog),
            "DRY_RUN": "true",
            "LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    assert "williaby/exempt-repo" not in invocations
    assert "williaby/real-repo" in invocations


@requires_sweep_runtime
def test_sweep_skips_other_orgs(tmp_path: Path, fake_setup_script: Path):
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "ByronWilliamsCPA",
                        "name": "bw-repo",
                        "repositoryType": "python-package",
                    },
                    {
                        "org": "williaby",
                        "name": "wb-repo",
                        "repositoryType": "docs",
                    },
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env={
            "PATH": __import__("os").environ["PATH"],
            "CATALOG": str(catalog),
            "DRY_RUN": "true",
            "LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    assert "ByronWilliamsCPA/bw-repo" not in invocations
    assert "williaby/wb-repo" in invocations
