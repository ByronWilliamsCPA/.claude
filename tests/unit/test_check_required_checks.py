"""Unit tests for scripts/check-required-checks.py validator logic."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

from tests.unit._load_check_required_checks import load_module

crc = load_module()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "data" / "test_fixtures" / "required_checks"


# ── Inline-job behavior ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_single_job_no_name_produces_bare_job_key() -> None:
    workflow_yaml = (FIXTURES / "single_job_no_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"build"}


@pytest.mark.unit
def test_job_with_name_uses_name_field() -> None:
    workflow_yaml = (FIXTURES / "single_job_with_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"CI Gate"}


@pytest.mark.unit
def test_workflow_without_name_omits_prefix() -> None:
    workflow_yaml = (FIXTURES / "no_workflow_name.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Check REUSE Compliance"}


@pytest.mark.unit
def test_no_workflow_name_no_job_name_uses_bare_job_key() -> None:
    workflow_yaml = (FIXTURES / "no_name_no_prefix.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"build"}


# ── Matrix expansion ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_matrix_one_param_expands() -> None:
    workflow_yaml = (FIXTURES / "matrix_one_param.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Test Python 3.10",
        "Test Python 3.11",
        "Test Python 3.12",
    }


@pytest.mark.unit
def test_matrix_two_params_cartesian_expansion() -> None:
    workflow_yaml = (FIXTURES / "matrix_two_params.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Test ubuntu-latest 3.11",
        "Test ubuntu-latest 3.12",
        "Test macos-latest 3.11",
        "Test macos-latest 3.12",
    }


@pytest.mark.unit
def test_matrix_hyphenated_axis_expands() -> None:
    # Real-world workflows commonly use hyphenated axis names like
    # `python-version`, `node-version`. The interpolation regex must
    # accept hyphens (and dots) inside `${{ matrix.<axis> }}`.
    workflow_yaml = (FIXTURES / "matrix_hyphen_axis.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {
        "Test (Python 3.11)",
        "Test (Python 3.12)",
    }


@pytest.mark.unit
def test_include_only_matrix_emits_raw_template_without_interpolation() -> None:
    workflow_yaml = (FIXTURES / "matrix_include_only.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert produced == {"Test ${{ matrix.python }}"}


# ── Reusable-workflow caller-prefix behavior ────────────────────────────────


@pytest.mark.unit
def test_registered_reusable_applies_caller_job_key_as_prefix() -> None:
    # The fixture has `jobs.ci.uses: ...python-ci.yml`; no `name:` field,
    # so the caller-prefix is the bare job key `ci`. The registry stores
    # the unprefixed leaf check name `CI Gate`; the validator applies the
    # caller-job-name prefix at compare time.
    workflow_yaml = (FIXTURES / "reusable_registered.yml").read_text()
    registry = {
        "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml": {
            "produces": ["CI Gate"],
            "source_repo": "ByronWilliamsCPA/.github",
            "last_verified": "2026-05-08",
        },
    }
    produced = crc.extract_produced_check_names(workflow_yaml, registry=registry)
    assert produced == {"ci / CI Gate"}


@pytest.mark.unit
def test_registered_reusable_uses_caller_name_field_when_present() -> None:
    # Same registry, but the fixture's calling job has `name: CI (Python 3.12)`.
    # That display name becomes the caller-prefix.
    workflow_yaml = (FIXTURES / "reusable_with_name.yml").read_text()
    registry = {
        "ByronWilliamsCPA/.github/.github/workflows/python-ci.yml": {
            "produces": ["CI Gate", "Code Quality Checks"],
            "source_repo": "ByronWilliamsCPA/.github",
            "last_verified": "2026-05-08",
        },
    }
    produced = crc.extract_produced_check_names(workflow_yaml, registry=registry)
    assert produced == {
        "CI (Python 3.12) / CI Gate",
        "CI (Python 3.12) / Code Quality Checks",
    }


@pytest.mark.unit
def test_unregistered_reusable_workflow_returns_sentinel() -> None:
    workflow_yaml = (FIXTURES / "reusable_unregistered.yml").read_text()
    produced = crc.extract_produced_check_names(workflow_yaml, registry={})
    assert any(name.startswith("__UNREGISTERED__:") for name in produced)
    assert (
        "__UNREGISTERED__:SomeOrg/private-actions/.github/workflows/build.yml"
        in produced
    )


# ── extract_produced_check_names: malformed inputs ──────────────────────────


@pytest.mark.unit
def test_non_dict_yaml_returns_empty_set() -> None:
    # A workflow YAML that's not a top-level mapping (e.g., a list) is
    # malformed but should not crash; the function returns an empty set
    # so the file is silently skipped (and CI-022 will flag any required
    # check that depended on it).
    assert (
        crc.extract_produced_check_names("- not\n- a\n- mapping\n", registry={})
        == set()
    )
    assert crc.extract_produced_check_names("just a scalar\n", registry={}) == set()


@pytest.mark.unit
def test_jobs_field_non_dict_returns_empty_set() -> None:
    workflow_yaml = "name: Foo\non: push\njobs:\n  - one\n  - two\n"
    assert crc.extract_produced_check_names(workflow_yaml, registry={}) == set()


# ── diff_required_vs_produced ───────────────────────────────────────────────


@pytest.mark.unit
def test_diff_required_vs_produced_flags_missing_producer() -> None:
    findings = crc.diff_required_vs_produced(
        required={"CI Gate", "REUSE"},
        produced={"CI Gate"},
        required_checks_meta={
            "REUSE": {"produced_by": ".github/workflows/reuse.yml"},
        },
    )
    assert len(findings) == 1
    assert findings[0].check_id == "CI-022"
    assert "REUSE" in findings[0].message
    assert ".github/workflows/reuse.yml" in findings[0].message


@pytest.mark.unit
def test_diff_required_vs_produced_flags_unregistered_reusable() -> None:
    findings = crc.diff_required_vs_produced(
        required={"CI Gate"},
        produced={
            "CI Gate",
            f"{crc._UNREGISTERED_PREFIX}SomeOrg/x/.github/workflows/y.yml",
        },
        required_checks_meta={},
    )
    assert any(
        "missing from docs/reusable-workflow-jobs.yaml" in f.message for f in findings
    )


# ── diff_required_vs_branch_protection ──────────────────────────────────────


@pytest.mark.unit
def test_diff_required_vs_branch_protection_missing_and_extra() -> None:
    findings = crc.diff_required_vs_branch_protection(
        required={"CI Gate", "REUSE"},
        contexts=["CI Gate", "Stale Check"],
    )
    messages = [f.message for f in findings]
    assert any("REUSE" in m and "missing" in m for m in messages)
    assert any("Stale Check" in m and "does not list" in m for m in messages)


@pytest.mark.unit
def test_diff_required_vs_branch_protection_exact_match_no_findings() -> None:
    findings = crc.diff_required_vs_branch_protection(
        required={"CI Gate"},
        contexts=["CI Gate"],
    )
    assert findings == []


# ── check_registry_freshness ────────────────────────────────────────────────


@pytest.mark.unit
def test_registry_freshness_flags_stale_entries() -> None:
    registry = {
        "fresh": {"last_verified": "2026-05-01"},
        "stale": {"last_verified": "2025-01-01"},
        "missing": {},
    }
    findings = crc.check_registry_freshness(
        registry=registry,
        today=date(2026, 5, 8),
        max_age_days=90,
    )
    paths = [f.message for f in findings]
    assert any("stale" in m for m in paths)
    assert any("missing" in m and "last_verified" in m for m in paths)
    assert not any("fresh" in m for m in paths)


@pytest.mark.unit
def test_registry_freshness_flags_unparseable_last_verified() -> None:
    findings = crc.check_registry_freshness(
        registry={
            "ByronWilliamsCPA/.github/.github/workflows/foo.yml": {
                "last_verified": "not-a-date",
            },
        },
        today=date(2026, 5, 8),
    )
    assert len(findings) == 1
    assert findings[0].check_id == "CI-024"
    assert "unparseable" in findings[0].message
    assert "not-a-date" in findings[0].message


@pytest.mark.unit
def test_registry_freshness_accepts_native_date_object() -> None:
    # ruamel YAML may return native `date` objects rather than ISO strings;
    # the freshness check must accept both.
    registry = {
        "ByronWilliamsCPA/.github/.github/workflows/foo.yml": {
            "last_verified": date(2026, 5, 1),
        },
    }
    findings = crc.check_registry_freshness(registry=registry, today=date(2026, 5, 8))
    assert findings == []


# ── fetch_classic_protection_contexts ────────────────────────────────────────


def _fake_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> None:
    """Replace subprocess.run with a stub yielding a deterministic CompletedProcess."""

    class _FakeResult:
        def __init__(self) -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(*args, **kwargs):
        return _FakeResult()

    monkeypatch.setattr(subprocess, "run", _fake_run)


@pytest.mark.unit
def test_fetch_classic_protection_contexts_handles_null_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repos with protection but no required_status_checks return null from --jq."""
    _fake_subprocess(monkeypatch, returncode=0, stdout="null\n")
    contexts = crc.fetch_classic_protection_contexts("fake/repo")
    assert contexts == []


@pytest.mark.unit
def test_fetch_classic_protection_contexts_returns_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_subprocess(
        monkeypatch,
        returncode=0,
        stdout=json.dumps(["CI Gate", "REUSE"]) + "\n",
    )
    contexts = crc.fetch_classic_protection_contexts("fake/repo")
    assert contexts == ["CI Gate", "REUSE"]


@pytest.mark.unit
def test_fetch_classic_protection_contexts_raises_on_non_zero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gh non-zero exit must raise, not silently return []. Treating an auth
    failure as 'no contexts' would falsely mark every required check as
    missing from branch protection.
    """
    _fake_subprocess(monkeypatch, returncode=1, stderr="HTTP 401: Bad credentials")
    with pytest.raises(crc.BranchProtectionFetchError, match="exit 1"):
        crc.fetch_classic_protection_contexts("fake/repo")


@pytest.mark.unit
def test_fetch_classic_protection_contexts_raises_on_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_subprocess(monkeypatch, returncode=0, stdout="<html>auth redirect</html>")
    with pytest.raises(crc.BranchProtectionFetchError, match="non-JSON"):
        crc.fetch_classic_protection_contexts("fake/repo")


@pytest.mark.unit
def test_fetch_classic_protection_contexts_raises_on_unexpected_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_subprocess(monkeypatch, returncode=0, stdout=json.dumps({"oops": "dict"}))
    with pytest.raises(crc.BranchProtectionFetchError, match="unexpected type"):
        crc.fetch_classic_protection_contexts("fake/repo")


@pytest.mark.unit
def test_fetch_classic_protection_contexts_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=30)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)
    with pytest.raises(crc.BranchProtectionFetchError, match="timed out"):
        crc.fetch_classic_protection_contexts("fake/repo", timeout=30)


# ── load_required_checks ────────────────────────────────────────────────────


@pytest.mark.unit
def test_load_required_checks_raises_on_missing_name_field(tmp_path: Path) -> None:
    manifest = tmp_path / "m.yaml"
    manifest.write_text("required_checks:\n  - produced_by: foo.yml\n")
    with pytest.raises(ValueError, match="missing or empty 'name' field"):
        crc.load_required_checks(manifest)


@pytest.mark.unit
def test_load_required_checks_raises_on_non_mapping_top_level(tmp_path: Path) -> None:
    manifest = tmp_path / "m.yaml"
    manifest.write_text("- a list at top level\n")
    with pytest.raises(ValueError, match="must be a mapping"):
        crc.load_required_checks(manifest)


@pytest.mark.unit
def test_load_required_checks_handles_empty_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "m.yaml"
    manifest.write_text("")
    names, meta = crc.load_required_checks(manifest)
    assert names == set()
    assert meta == {}


@pytest.mark.unit
def test_load_required_checks_handles_missing_required_checks_key(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "m.yaml"
    manifest.write_text("version: '1.0'\n")
    names, meta = crc.load_required_checks(manifest)
    assert names == set()
    assert meta == {}


@pytest.mark.unit
def test_load_required_checks_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Manifest not found"):
        crc.load_required_checks(tmp_path / "does-not-exist.yaml")


# ── main() argument validation ──────────────────────────────────────────────


@pytest.mark.unit
def test_main_rejects_check_bp_without_repo_slug(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "m.yaml"
    manifest.write_text("required_checks: []\n")
    registry = tmp_path / "r.yaml"
    registry.write_text("{}\n")
    with pytest.raises(SystemExit) as excinfo:
        crc.main(
            [
                "--repo-path",
                str(tmp_path),
                "--manifest",
                str(manifest),
                "--registry",
                str(registry),
                "--check-bp",
            ]
        )
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "--check-bp requires --repo-slug" in captured.err


# -- fetch_ruleset_contexts --------------------------------------------------


def test_fetch_ruleset_contexts_returns_empty_when_no_rulesets(monkeypatch):
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: ("[]", "", 0))
    contexts, provenance = crc.fetch_ruleset_contexts("test/repo", "main")
    assert contexts == set()
    assert provenance == {}


def test_fetch_ruleset_contexts_returns_set_and_provenance(monkeypatch):
    payload = json.dumps(
        [
            {
                "type": "required_status_checks",
                "ruleset_source_type": "Organization",
                "ruleset_source": "ByronWilliamsCPA",
                "ruleset_id": 99,
                "parameters": {
                    "required_status_checks": [
                        {"context": "CI Gate"},
                        {"context": "Security Gate Validation"},
                    ]
                },
            },
            {"type": "required_signatures"},
        ]
    )
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: (payload, "", 0))
    contexts, prov = crc.fetch_ruleset_contexts("BW/repo", "main")
    assert contexts == {"CI Gate", "Security Gate Validation"}
    assert prov == {
        "Organization:ByronWilliamsCPA/99": ["CI Gate", "Security Gate Validation"]
    }


def test_fetch_ruleset_contexts_raises_on_gh_failure(monkeypatch):
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: ("", "auth error", 1))
    with pytest.raises(crc.RulesetFetchError, match="auth error"):
        crc.fetch_ruleset_contexts("test/repo", "main")


def test_fetch_ruleset_contexts_raises_on_malformed_json(monkeypatch):
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: ("not json", "", 0))
    with pytest.raises(crc.RulesetFetchError, match="Malformed"):
        crc.fetch_ruleset_contexts("test/repo", "main")


def test_fetch_ruleset_contexts_raises_on_gh_timeout(monkeypatch):
    """GhCliError(timeout) from _run_gh must surface as RulesetFetchError."""

    def fake_run_gh(args, timeout):
        raise crc.GhCliError("gh CLI timed out after 30s")

    monkeypatch.setattr(crc, "_run_gh", fake_run_gh)
    with pytest.raises(crc.RulesetFetchError, match="timed out"):
        crc.fetch_ruleset_contexts("test/repo", "main")


def test_fetch_ruleset_contexts_raises_on_gh_not_found(monkeypatch):
    """GhCliError(not-found) from _run_gh must surface as RulesetFetchError."""

    def fake_run_gh(args, timeout):
        raise crc.GhCliError("gh CLI not found on PATH")

    monkeypatch.setattr(crc, "_run_gh", fake_run_gh)
    with pytest.raises(crc.RulesetFetchError, match="not found"):
        crc.fetch_ruleset_contexts("test/repo", "main")


# -- fetch_effective_required_contexts ----------------------------------------


def test_fetch_effective_classic_mode_uses_only_classic(monkeypatch):
    monkeypatch.setattr(
        crc, "fetch_classic_protection_contexts", lambda *a, **k: ["A", "B"]
    )
    monkeypatch.setattr(
        crc, "fetch_ruleset_contexts", lambda *a, **k: pytest.fail("should not call")
    )
    contexts, prov = crc.fetch_effective_required_contexts("r/r", "main", "classic")
    assert contexts == {"A", "B"}
    assert prov == {"classic": ["A", "B"]}


def test_fetch_effective_union_combines(monkeypatch):
    monkeypatch.setattr(crc, "fetch_classic_protection_contexts", lambda *a, **k: ["A"])
    monkeypatch.setattr(
        crc,
        "fetch_ruleset_contexts",
        lambda *a, **k: ({"B", "C"}, {"Organization:O/1": ["B", "C"]}),
    )
    contexts, prov = crc.fetch_effective_required_contexts("r/r", "main", "union")
    assert contexts == {"A", "B", "C"}
    assert prov == {"classic": ["A"], "Organization:O/1": ["B", "C"]}


def test_fetch_effective_union_partial_failure_returns_partial(monkeypatch):
    def boom(*a, **k):
        raise crc.BranchProtectionFetchError("404 not found")

    monkeypatch.setattr(crc, "fetch_classic_protection_contexts", boom)
    monkeypatch.setattr(
        crc,
        "fetch_ruleset_contexts",
        lambda *a, **k: ({"X"}, {"Organization:O/1": ["X"]}),
    )
    contexts, prov = crc.fetch_effective_required_contexts("r/r", "main", "union")
    assert contexts == {"X"}
    assert "classic:error" in prov
    assert "404 not found" in prov["classic:error"][0]
