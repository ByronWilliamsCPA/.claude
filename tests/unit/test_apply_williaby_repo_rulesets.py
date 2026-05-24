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
import os
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


def _write_uv_shim(bin_dir: Path, log: Path, exit_code: int = 0) -> Path:
    """Create a `uv` shell shim that records each call's args and exits.

    The shim writes one argument per line so test assertions don't depend on
    argv-boundary preservation through `echo "$@"` (which loses spaces).
    """
    shim = bin_dir / "uv"
    shim.write_text(
        f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "{log}"\nexit {exit_code}\n'
    )
    shim.chmod(0o755)
    return shim


def _prepend_to_path(monkeypatch: pytest.MonkeyPatch, *prefixes: Path) -> None:
    """Prepend `prefixes` to PATH while preserving the user's existing PATH.

    Earlier versions rebuilt PATH from scratch, which dropped /usr/local/bin
    and broke on macOS/NixOS where common tools (including `bash` itself on
    some Nix profiles) live outside /usr/bin and /bin.
    """
    base = os.environ.get("PATH", "")
    parts = [str(p) for p in prefixes]
    if base:
        parts.append(base)
    monkeypatch.setenv("PATH", os.pathsep.join(parts))


def _sweep_env(
    catalog: Path,
    log_path: Path | None = None,
    dry_run: bool = False,
    enforcement: str | None = None,
) -> dict[str, str]:
    """Build the env dict for subprocess.run() in sweep tests.

    Args:
        catalog: path to the catalog JSON file.
        log_path: optional path to write the sweep log.
        dry_run: whether to set DRY_RUN=true.
        enforcement: optional ENFORCEMENT value (active, evaluate, or disabled).

    Returns:
        Dict ready for subprocess.run(env=...).
    """
    env = {
        "PATH": os.environ.get("PATH", ""),
        "CATALOG": str(catalog),
    }
    if log_path is not None:
        env["LOG"] = str(log_path)
    if dry_run:
        env["DRY_RUN"] = "true"
    if enforcement is not None:
        env["ENFORCEMENT"] = enforcement
    return env


@pytest.fixture
def fake_setup_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stub the `uv` binary so the sweep can execute offline.

    The sweep script invokes ``uv run python scripts/setup_repo_rulesets.py``.
    To exercise the sweep without hitting the network or the real
    setup_repo_rulesets.py module, this fixture installs a `uv` shell shim
    on PATH that records every invocation's args to a log file and exits 0.
    Returns the log path so tests can assert on the recorded args.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "uv-invocations.log"
    _write_uv_shim(bin_dir, log, exit_code=0)
    _prepend_to_path(monkeypatch, bin_dir)
    return log


@pytest.fixture
def failing_uv_shim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Same as `fake_setup_script` but the shim exits non-zero.

    Used to exercise the sweep's per-repo failure path: continue iterating,
    accumulate failures, exit 1 at the end.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "uv-invocations.log"
    _write_uv_shim(bin_dir, log, exit_code=42)
    _prepend_to_path(monkeypatch, bin_dir)
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
    catalog = tmp_path / "nope.json"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env=_sweep_env(catalog),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 2
    assert "catalog not found" in result.stderr


@requires_sweep_runtime
def test_sweep_fails_when_template_missing(tmp_path: Path):
    """Template-body precondition fires when REPO_ROOT/docs has no templates."""
    # The script resolves REPO_ROOT from BASH_SOURCE[0], so dropping a copy of
    # the sweep into a fake scripts/ directory under tmp_path makes REPO_ROOT
    # resolve to tmp_path, which has no docs/reference/repo-rulesets/ tree.
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    fake_sweep = fake_scripts / "apply_williaby_repo_rulesets.sh"
    fake_sweep.write_text(SWEEP_SCRIPT.read_text())
    fake_sweep.chmod(0o755)

    catalog = tmp_path / "cat.json"
    catalog.write_text(json.dumps({"repos": []}))

    result = subprocess.run(
        [BASH, str(fake_sweep)],
        env=_sweep_env(catalog),
        capture_output=True,
        text=True,
        check=False,
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
        env=_sweep_env(catalog, log_path=log, dry_run=True),
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
        env=_sweep_env(catalog, log_path=log, dry_run=True),
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
        env=_sweep_env(catalog, log_path=log, dry_run=True),
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
        env=_sweep_env(catalog, log_path=log, dry_run=True),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    assert "ByronWilliamsCPA/bw-repo" not in invocations
    assert "williaby/wb-repo" in invocations


# Enforcement validation -------------------------------------------------


@requires_sweep_runtime
def test_sweep_rejects_invalid_enforcement_value(tmp_path: Path):
    """ENFORCEMENT must be active, evaluate, or disabled (case-sensitive)."""
    catalog = tmp_path / "cat.json"
    catalog.write_text(json.dumps({"repos": []}))
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env=_sweep_env(catalog, enforcement="Active"),  # capital A: typo case
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 2
    assert "invalid ENFORCEMENT" in result.stderr


@requires_sweep_runtime
def test_sweep_passes_enforcement_value_to_setup_script(
    tmp_path: Path, fake_setup_script: Path
):
    """The ENFORCEMENT env value flows through to setup_repo_rulesets.py."""
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "williaby",
                        "name": "active-repo",
                        "repositoryType": "docs",
                    }
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env=_sweep_env(catalog, log_path=log, dry_run=True, enforcement="active"),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    # printf "%s\n" "$@" puts each arg on its own line, so we can match exact tokens.
    invocation_lines = invocations.splitlines()
    assert "--enforcement" in invocation_lines
    assert "active" in invocation_lines
    # Confirm the value is the one that follows the flag
    flag_index = invocation_lines.index("--enforcement")
    assert invocation_lines[flag_index + 1] == "active"


# Tier routing parametrized: covers all python-* types plus null/missing -


@pytest.mark.parametrize(
    ("repository_type", "expected_template"),
    [
        ("python-package", "_williaby-template-python.json"),
        ("python-app", "_williaby-template-python.json"),
        ("python-script", "_williaby-template-python.json"),
        ("docs", "_williaby-template-universal.json"),
        ("infra", "_williaby-template-universal.json"),
    ],
)
@requires_sweep_runtime
def test_sweep_tier_routing_covers_all_python_types(
    tmp_path: Path,
    fake_setup_script: Path,
    repository_type: str,
    expected_template: str,
):
    """All python-* types route to python tier; everything else goes universal."""
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "williaby",
                        "name": f"{repository_type}-repo",
                        "repositoryType": repository_type,
                    }
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env=_sweep_env(catalog, log_path=log, dry_run=True),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    invocations = fake_setup_script.read_text()
    assert expected_template in invocations


@requires_sweep_runtime
def test_sweep_warns_and_falls_back_when_repository_type_missing(
    tmp_path: Path, fake_setup_script: Path
):
    """A repo without repositoryType still gets a ruleset, with a warning."""
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    # No repositoryType key at all
                    {"org": "williaby", "name": "untyped-repo"},
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env=_sweep_env(catalog, log_path=log, dry_run=True),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "repositoryType missing in catalog" in result.stderr
    invocations = fake_setup_script.read_text()
    assert "_williaby-template-universal.json" in invocations


# Failure path -----------------------------------------------------------


@requires_sweep_runtime
def test_sweep_continues_after_repo_failure_and_exits_one(
    tmp_path: Path, failing_uv_shim: Path
):
    """A failing repo records FAIL, the sweep continues, and exit is 1."""
    catalog = tmp_path / "cat.json"
    catalog.write_text(
        json.dumps(
            {
                "repos": [
                    {
                        "org": "williaby",
                        "name": "first-repo",
                        "repositoryType": "docs",
                    },
                    {
                        "org": "williaby",
                        "name": "second-repo",
                        "repositoryType": "python-package",
                    },
                ]
            }
        )
    )
    log = tmp_path / "sweep.log"
    result = subprocess.run(
        [BASH, str(SWEEP_SCRIPT)],
        env=_sweep_env(catalog, log_path=log, dry_run=True),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    log_text = log.read_text()
    # Both repos must have been attempted (continue-on-fail)
    assert "first-repo" in log_text
    assert "second-repo" in log_text
    # Both must be marked FAIL with the shim's exit code
    assert "FAIL williaby/first-repo (exit 42)" in log_text
    assert "FAIL williaby/second-repo (exit 42)" in log_text
    # Final summary records both as failed
    assert "applied=0 failed=2" in log_text
