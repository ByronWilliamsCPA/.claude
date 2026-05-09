---
schema_type: planning
title: "Org Rulesets Migration"
status: draft
owner: core-maintainer
purpose: "Migrate 45 GitHub repos across two orgs from classic branch protection to org-level rulesets, enabling ruleset-driven Copilot review without solo-dev approval barriers."
component: Development-Tools
source: "synthesized from parallel Plan-agent research (org ruleset design, tooling changes, migration playbook)"
tags:
  - automation
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate 45 GitHub repos across two orgs (ByronWilliamsCPA, williaby) from classic branch protection to org-level rulesets so Copilot review becomes ruleset-required without introducing self-review barriers for the solo dev.

**Architecture:** Replace the per-PR runtime Copilot trigger in `/pr-review` with the `copilot_code_review` ruleset rule (verified at https://docs.github.com/en/rest/repos/rules), shipped inside two-tier org rulesets (universal baseline + Python-tier). Validators learn to read both classic and ruleset sources during a transition window, then classic protection is stripped. Solo-dev safety is preserved by keeping `required_approving_review_count: 0` in every ruleset and adding a hard guard in the new setup script that rejects any body with a non-zero value. Both org-level and repo-level ruleset bodies are storable as JSON under `docs/reference/org-rulesets/` and `docs/reference/repo-rulesets/`, applied via `setup_org_rulesets.py` and `setup_repo_rulesets.py` respectively.

**Tech Stack:** Python 3.10+ (validators, setup script), `gh` CLI (GitHub API), pytest + monkeypatch (tests), GitHub REST `/orgs/:org/rulesets` and `/repos/:r/rules/branches/:b` endpoints.

---

### Hard Constraints (every task must respect)

1. **Solo dev**: `required_approving_review_count` MUST stay 0 in every ruleset and every classic-protection state. Any code path that sets it to a positive integer is a bug. The new setup script has an automated guard.
2. **Permanent exemption**: `williaby/homelab-agent-configs` (default branch `agent/hermes`) is excluded from every ruleset and every audit. Catalog flag: `branchProtectionExempt: true`.
3. **Intentional non-standard**: `required_conversation_resolution = false` and `required_review_thread_resolution = false`. Do not enable.
4. **Strict transition**: while both classic and ruleset are present, validators run in `--source union` mode and fail on drift in either source.

---

### Architecture Decisions (locked during planning)

### Two rulesets per org, not one

`CI Gate` is Python-only. Including it in a single org ruleset that applies to all repos would permanently fail merges on ~10 non-Python repos. Solution: a "universal" ruleset (3 checks) targeting `~ALL` minus exemptions, plus a "python-tier" ruleset (`CI Gate` only) targeting an explicit Python-repo include list generated from `docs/reference/github-repos.json`.

### Copilot enforcement is a first-class ruleset rule

GitHub exposes `copilot_code_review` as a standalone rule type within rulesets (verified at https://docs.github.com/en/rest/repos/rules). The rule shape is:

```json
{
  "type": "copilot_code_review",
  "parameters": {
    "review_draft_pull_requests": false,
    "review_on_push": false
  }
}
```

This corresponds to the "Automatically request Copilot code review" checkbox in the GitHub ruleset UI. Including this rule in the org ruleset auto-requests Copilot on every PR opened against the targeted branch , no per-PR runtime trigger needed, no separate org-level Copilot setting needed. **Earlier speculative design (`automatic_copilot_code_review_enabled` inside `pull_request.parameters`) was incorrect** , the API rejects that parameter; `copilot_code_review` is a sibling rule object in the `rules` array.

The auto-request via this rule is the only built-in enforcement mechanism. Copilot review is *requested* when the PR opens but is *advisory*: it does not by itself block merge. To make Copilot review *blocking*, add the `Copilot` context to `required_status_checks` once the check posts reliably across a 2-week evaluation window , this is the optional Phase 3.5 follow-up, not part of the initial migration.

### Repo-level ruleset support is a small extension, not in the critical path

The user wants both org and repo-level ruleset standards storable as uploadable JSON. `/repos/:owner/:repo/rulesets` mirrors `/orgs/:org/rulesets` with the same body schema. A `setup_repo_rulesets.py` is a thin variant of `setup_org_rulesets.py` that reads from `docs/reference/repo-rulesets/<org>__<repo>.json` and POSTs/PUTs against the repo endpoint. It is included as Task 9b for completeness but is not required for the migration itself, since every standard rule lives at the org level today.

### Migration phase tracking lives in the repo catalog

`docs/reference/github-repos.json` gains a per-repo `migrationPhase` enum: `pending` | `dual` | `complete`. The validator's `--source` flag is selected from this field, defaulting to `union` for safety.

---

### File Structure

### New files
- `scripts/setup_org_rulesets.py` , applies an org ruleset JSON body to a GitHub org
- `docs/reference/org-rulesets/ByronWilliamsCPA-universal.json` , universal ruleset body
- `docs/reference/org-rulesets/ByronWilliamsCPA-python.json` , Python-tier ruleset body
- `docs/reference/org-rulesets/williaby-universal.json` , universal ruleset body
- `docs/reference/org-rulesets/williaby-python.json` , Python-tier ruleset body
- `scripts/generate_python_tier_repos.py` , emits the Python-repo include list from the catalog
- `scripts/restore_classic_protection.sh` , emergency rollback
- `tests/unit/test_setup_org_rulesets.py` , solo-dev guard + body application tests
- `tests/unit/test_check_repo_compliance.py` , ruleset-aware BP-4/BP-5 tests
- `backups/branch-protection-2026-05-08/` , runtime backup directory (gitignored)

### Modified files
- `scripts/check-required-checks.py` , adds `fetch_ruleset_contexts`, `fetch_effective_required_contexts`, `--source` flag; renames classic fetcher
- `scripts/check-repo-compliance.py` , BP-4/BP-5 read from `/rules/branches/:b` endpoint; `BRANCH_PROTECTION_EXEMPT` constant added
- `docs/standards-manifest.yaml` , CI-023 reworded; CI-025/026/027 added; solo-dev guard annotation
- `docs/reference/github-repos.json` , `migrationPhase` field added to every non-exempt repo
- `.claude/agents/ossf-compliance-auditor.md` , remediation prompts updated for ruleset patches; CI-025/026/027 templates
- `.claude/skills/pr-review/workflows/pr-review.md` , Step 1 simplified (Stage 1b deleted)
- `.claude/skills/pr-review/SKILL.md` , Copilot description updated
- `.claude/rules/git-workflow.md` , Layer 2 Copilot bullet updated
- `.claude/rules/pre-commit.md` , Copilot review item updated
- `docs/OPENSSF_COMPLIANCE.md` , branch-protection sections rewritten for rulesets
- `docs/PROJECT_SETUP.md` , branch-protection setup section rewritten
- `.claude/agents/github-workflow-agent.md` , terminology updated
- `~/.claude/projects/-home-byron-dev--claude/memory/project_branch_protection_standards.md` , generalized to rulesets

### Deleted files (Phase 4)
- `scripts/setup_github_protection.py`

---

## Track 1: Validator Updates (no GitHub state changes)

> Goal: `check-required-checks.py` learns to read both protection sources and report drift with provenance, so the manifest is never silently unenforced during the transition window. All work happens locally; no API state is changed.

### Task 1: Add `fetch_ruleset_contexts` with TDD

**Files:**
- Modify: `scripts/check-required-checks.py` (add new function after line 514)
- Test: `tests/unit/test_check_required_checks.py` (extend)

- [ ] **Step 1: Write failing test for empty ruleset list**

```python
def test_fetch_ruleset_contexts_returns_empty_when_no_rulesets(monkeypatch):
    import scripts.check_required_checks as crc
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: ("[]", "", 0))
    contexts, provenance = crc.fetch_ruleset_contexts("test/repo", "main")
    assert contexts == set()
    assert provenance == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_check_required_checks.py::test_fetch_ruleset_contexts_returns_empty_when_no_rulesets -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'fetch_ruleset_contexts'`

- [ ] **Step 3: Write the function**

```python
class RulesetFetchError(RuntimeError):
    """Raised when ruleset evaluation cannot be fetched from gh."""

def fetch_ruleset_contexts(
    repo_slug: str,
    branch: str = "main",
    timeout: int = _GH_TIMEOUT_SECONDS,
) -> tuple[set[str], dict[str, list[str]]]:
    """Return (contexts, provenance) from all rulesets targeting this branch.

    provenance maps "<source_type>:<source>/<id>" to the contexts that
    ruleset contributes. source_type is "Repository" or "Organization".
    """
    args = ["api", f"repos/{repo_slug}/rules/branches/{branch}"]
    out, err, rc = _run_gh(args, timeout)
    if rc != 0:
        raise RulesetFetchError(f"Could not fetch ruleset evaluation: {err.strip() or out.strip()}")
    try:
        rules = json.loads(out) if out.strip() else []
    except json.JSONDecodeError as e:
        raise RulesetFetchError(f"Malformed ruleset JSON: {e}") from e

    contexts: set[str] = set()
    provenance: dict[str, list[str]] = {}
    for rule in rules:
        if rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters", {}) or {}
        rule_contexts = [
            entry.get("context", "")
            for entry in params.get("required_status_checks", [])
            if entry.get("context")
        ]
        source_type = rule.get("ruleset_source_type", "Unknown")
        source = rule.get("ruleset_source", "?")
        ruleset_id = rule.get("ruleset_id", "?")
        key = f"{source_type}:{source}/{ruleset_id}"
        provenance.setdefault(key, []).extend(rule_contexts)
        contexts.update(rule_contexts)
    return contexts, provenance
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_check_required_checks.py::test_fetch_ruleset_contexts_returns_empty_when_no_rulesets -v`
Expected: PASS

- [ ] **Step 5: Add three more tests (populated, raises on gh failure, malformed JSON)**

```python
def test_fetch_ruleset_contexts_returns_set_and_provenance(monkeypatch):
    import scripts.check_required_checks as crc
    payload = json.dumps([
        {
            "type": "required_status_checks",
            "ruleset_source_type": "Organization",
            "ruleset_source": "ByronWilliamsCPA",
            "ruleset_id": 99,
            "parameters": {"required_status_checks": [
                {"context": "CI Gate"},
                {"context": "Security Gate Validation"},
            ]},
        },
        {"type": "required_signatures"},
    ])
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: (payload, "", 0))
    contexts, prov = crc.fetch_ruleset_contexts("BW/repo", "main")
    assert contexts == {"CI Gate", "Security Gate Validation"}
    assert prov == {"Organization:ByronWilliamsCPA/99": ["CI Gate", "Security Gate Validation"]}

def test_fetch_ruleset_contexts_raises_on_gh_failure(monkeypatch):
    import scripts.check_required_checks as crc
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: ("", "auth error", 1))
    with pytest.raises(crc.RulesetFetchError, match="auth error"):
        crc.fetch_ruleset_contexts("test/repo", "main")

def test_fetch_ruleset_contexts_raises_on_malformed_json(monkeypatch):
    import scripts.check_required_checks as crc
    monkeypatch.setattr(crc, "_run_gh", lambda args, timeout: ("not json", "", 0))
    with pytest.raises(crc.RulesetFetchError, match="Malformed"):
        crc.fetch_ruleset_contexts("test/repo", "main")
```

Run: `uv run pytest tests/unit/test_check_required_checks.py -k fetch_ruleset_contexts -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py
git commit -m "feat(validator): add fetch_ruleset_contexts for ruleset-aware audits"
```

### Task 2: Rename classic fetcher

**Files:**
- Modify: `scripts/check-required-checks.py:442` (function rename only)
- Modify: `tests/unit/test_check_required_checks.py:276-365` (test names + targets)
- Modify: `tests/integration/test_check_required_checks_integration.py:26,56` (monkeypatch target)

- [ ] **Step 1: Rename function and exception class are NOT changed**

`fetch_branch_protection_contexts` → `fetch_classic_protection_contexts`. `BranchProtectionFetchError` keeps its name (still semantically correct).

- [ ] **Step 2: Update all call sites**

```bash
grep -n "fetch_branch_protection_contexts" scripts/ tests/
```

Replace each occurrence with `fetch_classic_protection_contexts`.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest tests/unit/test_check_required_checks.py tests/integration/test_check_required_checks_integration.py -v`
Expected: all pass with new names.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-required-checks.py tests/
git commit -m "refactor(validator): rename fetch_branch_protection_contexts to fetch_classic_protection_contexts"
```

### Task 3: Add `fetch_effective_required_contexts` dispatcher

**Files:**
- Modify: `scripts/check-required-checks.py`
- Test: `tests/unit/test_check_required_checks.py`

- [ ] **Step 1: Write three failing tests**

```python
def test_fetch_effective_classic_mode_uses_only_classic(monkeypatch):
    import scripts.check_required_checks as crc
    monkeypatch.setattr(crc, "fetch_classic_protection_contexts", lambda *a, **k: ["A", "B"])
    monkeypatch.setattr(crc, "fetch_ruleset_contexts", lambda *a, **k: pytest.fail("should not call"))
    contexts, prov = crc.fetch_effective_required_contexts("r/r", "main", "classic")
    assert contexts == {"A", "B"}
    assert prov == {"classic": ["A", "B"]}

def test_fetch_effective_union_combines(monkeypatch):
    import scripts.check_required_checks as crc
    monkeypatch.setattr(crc, "fetch_classic_protection_contexts", lambda *a, **k: ["A"])
    monkeypatch.setattr(crc, "fetch_ruleset_contexts", lambda *a, **k: ({"B", "C"}, {"Organization:O/1": ["B", "C"]}))
    contexts, prov = crc.fetch_effective_required_contexts("r/r", "main", "union")
    assert contexts == {"A", "B", "C"}
    assert prov == {"classic": ["A"], "Organization:O/1": ["B", "C"]}

def test_fetch_effective_union_partial_failure_returns_partial(monkeypatch):
    import scripts.check_required_checks as crc
    def boom(*a, **k):
        raise crc.BranchProtectionFetchError("404 not found")
    monkeypatch.setattr(crc, "fetch_classic_protection_contexts", boom)
    monkeypatch.setattr(crc, "fetch_ruleset_contexts", lambda *a, **k: ({"X"}, {"Organization:O/1": ["X"]}))
    contexts, prov = crc.fetch_effective_required_contexts("r/r", "main", "union")
    assert contexts == {"X"}
    assert "classic:error" in prov
    assert "404 not found" in prov["classic:error"][0]
```

Run: `uv run pytest tests/unit/test_check_required_checks.py -k fetch_effective -v`
Expected: 3 fail with `AttributeError`.

- [ ] **Step 2: Implement the function**

```python
def fetch_effective_required_contexts(
    repo_slug: str,
    branch: str,
    source_mode: str,
) -> tuple[set[str], dict[str, list[str]]]:
    """Return effective required-checks set and provenance per source_mode.

    source_mode: "classic" | "rulesets" | "union"
    Provenance always includes a "<source>:error" key for any source that
    raised, so callers can emit a Critical finding for the failed source
    while still validating what they got.
    """
    if source_mode not in {"classic", "rulesets", "union"}:
        raise ValueError(f"Invalid source_mode: {source_mode!r}")

    contexts: set[str] = set()
    provenance: dict[str, list[str]] = {}

    if source_mode in {"classic", "union"}:
        try:
            classic = list(fetch_classic_protection_contexts(repo_slug, branch))
            contexts.update(classic)
            provenance["classic"] = classic
        except BranchProtectionFetchError as e:
            if source_mode == "classic":
                raise
            provenance["classic:error"] = [str(e)]

    if source_mode in {"rulesets", "union"}:
        try:
            rs_contexts, rs_prov = fetch_ruleset_contexts(repo_slug, branch)
            contexts.update(rs_contexts)
            provenance.update(rs_prov)
        except RulesetFetchError as e:
            if source_mode == "rulesets":
                raise
            provenance["rulesets:error"] = [str(e)]

    return contexts, provenance
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_check_required_checks.py -k fetch_effective -v`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py
git commit -m "feat(validator): add fetch_effective_required_contexts union dispatcher"
```

### Task 4: Rewrite the diff function with provenance

**Files:**
- Modify: `scripts/check-required-checks.py:254-281` (replace `diff_required_vs_branch_protection`)
- Test: `tests/unit/test_check_required_checks.py`

- [ ] **Step 1: Write failing test for provenance in finding text**

```python
def test_diff_required_vs_effective_includes_provenance(monkeypatch):
    import scripts.check_required_checks as crc
    findings = crc.diff_required_vs_effective(
        required={"A", "B"},
        effective={"A"},
        provenance={"classic": ["A"], "Organization:williaby/42": []},
    )
    msgs = [f.message for f in findings]
    assert any("B" in m and "missing" in m.lower() for m in msgs)
    assert any("classic" in m or "Organization:williaby/42" in m for m in msgs)
```

Run: `uv run pytest tests/unit/test_check_required_checks.py::test_diff_required_vs_effective_includes_provenance -v`
Expected: FAIL.

- [ ] **Step 2: Replace the function**

Delete the old `diff_required_vs_branch_protection` (lines 254-281). Add:

```python
def diff_required_vs_effective(
    required: set[str],
    effective: set[str],
    provenance: dict[str, list[str]],
) -> list[Finding]:
    """Diff manifest required-checks set vs effective protection contexts.

    Emits one Critical Finding per missing or extra context, with provenance
    appended to the message so operators know which source needs patching.
    """
    findings: list[Finding] = []
    sources = ", ".join(
        f"{k}={v}" for k, v in sorted(provenance.items()) if not k.endswith(":error")
    ) or "(no protection sources found)"

    missing = required - effective
    extra = effective - required

    for name in sorted(missing):
        findings.append(Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Required check '{name}' is missing from effective protection. "
                f"Sources: {sources}"
            ),
        ))
    for name in sorted(extra):
        findings.append(Finding(
            check_id="CI-023",
            severity="critical",
            message=(
                f"Extra context '{name}' is enforced but not in required_checks. "
                f"Sources: {sources}"
            ),
        ))

    for err_key in ("classic:error", "rulesets:error"):
        if err_key in provenance:
            findings.append(Finding(
                check_id="CI-023",
                severity="critical",
                message=(
                    f"Could not read protection source '{err_key.split(':')[0]}': "
                    f"{provenance[err_key][0]}"
                ),
            ))
    return findings
```

- [ ] **Step 3: Update all call sites in main()**

In `main()` (around line 559-578), replace:

```python
contexts = fetch_branch_protection_contexts(args.repo_slug, args.branch)
findings += diff_required_vs_branch_protection(required, contexts)
```

with:

```python
effective, provenance = fetch_effective_required_contexts(
    args.repo_slug, args.branch, args.source
)
findings += diff_required_vs_effective(required, effective, provenance)
```

- [ ] **Step 4: Run all validator tests**

Run: `uv run pytest tests/unit/test_check_required_checks.py tests/integration/test_check_required_checks_integration.py -v`
Expected: all pass (rename old `diff_required_vs_branch_protection_*` test names to match).

- [ ] **Step 5: Commit**

```bash
git add scripts/check-required-checks.py tests/
git commit -m "feat(validator): replace branch-protection diff with effective-protection diff"
```

### Task 5: Add `--source` CLI flag

**Files:**
- Modify: `scripts/check-required-checks.py:517-541` (`_parse_args`)
- Test: `tests/unit/test_check_required_checks.py`

- [ ] **Step 1: Write failing test**

```python
def test_source_flag_defaults_to_union():
    import scripts.check_required_checks as crc
    args = crc._parse_args(["--repo-slug", "x/y", "--check-bp"])
    assert args.source == "union"

def test_source_flag_accepts_classic():
    import scripts.check_required_checks as crc
    args = crc._parse_args(["--repo-slug", "x/y", "--check-bp", "--source", "classic"])
    assert args.source == "classic"

def test_source_flag_rejects_invalid():
    import scripts.check_required_checks as crc
    with pytest.raises(SystemExit):
        crc._parse_args(["--repo-slug", "x/y", "--source", "garbage"])
```

Run: `uv run pytest tests/unit/test_check_required_checks.py -k source_flag -v`
Expected: 3 fail.

- [ ] **Step 2: Add flag to argparse**

In `_parse_args` after `--check-bp`:

```python
parser.add_argument(
    "--source",
    choices=("classic", "rulesets", "union"),
    default="union",
    help="Which protection source to validate against (default: union).",
)
```

- [ ] **Step 3: Run tests + integration smoke**

Run: `uv run pytest tests/unit/test_check_required_checks.py -k source_flag -v`
Expected: 3 passed.

Run: `uv run python scripts/check-required-checks.py --repo-slug ByronWilliamsCPA/.claude --check-bp --source classic --branch main 2>&1 | head -5`
Expected: behaves identically to today (no ruleset call made).

- [ ] **Step 4: Commit**

```bash
git add scripts/check-required-checks.py tests/unit/test_check_required_checks.py
git commit -m "feat(validator): add --source flag for staged migration validation"
```

### Task 6: Update `check-repo-compliance.py` BP-4/BP-5

**Files:**
- Modify: `scripts/check-repo-compliance.py:37-47` (constants), `:137-152` (BP checks)
- Test: `tests/unit/test_check_repo_compliance.py` (new file)

- [ ] **Step 1: Add BRANCH_PROTECTION_EXEMPT constant**

After line 47 (existing `RENOVATE_IGNORED` constant), add:

```python
BRANCH_PROTECTION_EXEMPT = {"williaby/homelab-agent-configs"}
```

- [ ] **Step 2: Write failing tests for new file**

Create `tests/unit/test_check_repo_compliance.py`:

```python
import json
import pytest
from unittest.mock import patch

import scripts.check_repo_compliance as crc

def test_bp4_passes_when_required_signatures_in_ruleset():
    rules = json.dumps([{"type": "required_signatures"}])
    with patch.object(crc, "gh", side_effect=[(rules, None)]):
        result = crc._signatures_enforced("BW", ".claude", "main")
    assert result is True

def test_bp4_falls_back_to_classic_signatures(monkeypatch):
    monkeypatch.setattr(crc, "gh", lambda path: (
        (json.dumps([]), None) if "/rules/" in path
        else (json.dumps({"enabled": True}), None)
    ))
    assert crc._signatures_enforced("BW", ".claude", "main") is True

def test_bp_checks_return_na_for_exempt_repo():
    result = crc.check_repo("williaby", "homelab-agent-configs", "agent/hermes")
    assert result.bp_4 == "N/A"
    assert result.bp_5 == "N/A"
    assert "exempt" in " ".join(result.notes).lower()
```

Run: `uv run pytest tests/unit/test_check_repo_compliance.py -v`
Expected: tests fail (helper functions don't exist; check_repo doesn't honor exempt).

- [ ] **Step 3: Implement helpers**

After the `gh()` helper (around line 110), add:

```python
def _signatures_enforced(org: str, repo: str, branch: str) -> bool:
    """True if signatures are required via ruleset OR classic protection."""
    rules_data, err = gh(f"repos/{org}/{repo}/rules/branches/{branch}")
    if err is None and rules_data:
        try:
            rules = json.loads(rules_data) if isinstance(rules_data, str) else rules_data
            if any(r.get("type") == "required_signatures" for r in rules):
                return True
        except (json.JSONDecodeError, TypeError):
            pass
    sig_data, err = gh(f"repos/{org}/{repo}/branches/{branch}/protection/required_signatures")
    if err is not None:
        return False
    try:
        return bool(json.loads(sig_data).get("enabled")) if isinstance(sig_data, str) else bool(sig_data.get("enabled"))
    except (json.JSONDecodeError, AttributeError):
        return False
```

- [ ] **Step 4: Update BP-4 and BP-5 in `check_repo`**

Replace lines 137-152 with:

```python
slug = f"{org}/{repo}"
if slug in BRANCH_PROTECTION_EXEMPT:
    result.bp_4 = "N/A"
    result.bp_5 = "N/A"
    result.notes.append("Branch protection exempt by catalog flag")
else:
    result.bp_4 = "PASS" if _signatures_enforced(org, repo, branch) else "FAIL"
    # BP-5 logic (admin enforcement) follows same pattern; see Task 6 step 5
```

- [ ] **Step 5: Implement `_admins_enforced` helper and BP-5**

```python
def _admins_enforced(org: str, repo: str, branch: str) -> bool:
    """True if no active ruleset bypass_actor includes OrganizationAdmin role,
    OR (transition fallback) classic protection has enforce_admins.enabled.
    """
    rules_data, err = gh(f"repos/{org}/{repo}/rules/branches/{branch}")
    ruleset_ids: set[tuple[str, int]] = set()
    if err is None and rules_data:
        try:
            rules = json.loads(rules_data) if isinstance(rules_data, str) else rules_data
            for r in rules:
                rs_type = r.get("ruleset_source_type")
                rs_id = r.get("ruleset_id")
                rs_src = r.get("ruleset_source", "")
                if rs_type and rs_id:
                    ruleset_ids.add((rs_type, rs_src, rs_id))
        except (json.JSONDecodeError, TypeError):
            pass
    for rs_type, rs_src, rs_id in ruleset_ids:
        path = (
            f"orgs/{rs_src}/rulesets/{rs_id}" if rs_type == "Organization"
            else f"repos/{org}/{repo}/rulesets/{rs_id}"
        )
        body, err = gh(path)
        if err is not None:
            continue
        try:
            ruleset = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            continue
        for actor in ruleset.get("bypass_actors", []) or []:
            if actor.get("actor_type") == "RepositoryRole" and actor.get("actor_id") == 5:
                return False
    if ruleset_ids:
        return True
    prot_data, err = gh(f"repos/{org}/{repo}/branches/{branch}/protection")
    if err is not None:
        return False
    try:
        prot = json.loads(prot_data) if isinstance(prot_data, str) else prot_data
        return bool(prot.get("enforce_admins", {}).get("enabled"))
    except (json.JSONDecodeError, AttributeError):
        return False
```

Then in `check_repo`:

```python
result.bp_5 = "PASS" if _admins_enforced(org, repo, branch) else "FAIL"
```

> Note: this BP-5 result will FAIL once the org ruleset is in place because the user (OrganizationAdmin) intentionally has `bypass_mode: always`. That is the correct emergency-unblock posture for a solo dev. The audit's BP-5 result is informational; do not treat the FAIL as blocking. Add a `result.notes.append("BP-5 expected FAIL: solo-dev admin bypass intentional")` for exempt-style transparency.

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/unit/test_check_repo_compliance.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-repo-compliance.py tests/unit/test_check_repo_compliance.py
git commit -m "feat(audit): make check-repo-compliance ruleset-aware with exempt list"
```

---

## Track 2: Ruleset JSON Bodies and Setup Script

> Goal: produce the four ruleset JSON bodies (universal + Python tier × 2 orgs) and the script that POSTs/PUTs them. Solo-dev safety guard is in the script itself.

### Task 7: Author the four ruleset JSON bodies

**Files:**
- Create: `docs/reference/org-rulesets/ByronWilliamsCPA-universal.json`
- Create: `docs/reference/org-rulesets/ByronWilliamsCPA-python.json`
- Create: `docs/reference/org-rulesets/williaby-universal.json`
- Create: `docs/reference/org-rulesets/williaby-python.json`

- [ ] **Step 1: Create directory**

```bash
mkdir -p /home/byron/dev/.claude/docs/reference/org-rulesets
```

- [ ] **Step 2: Write `ByronWilliamsCPA-universal.json`**

```json
{
  "name": "ByronWilliamsCPA-default-branch-baseline",
  "target": "branch",
  "enforcement": "evaluate",
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {
    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []},
    "repository_name": {"include": ["~ALL"], "exclude": [], "protected": true}
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {"type": "required_signatures"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash", "rebase"]
      }
    },
    {
      "type": "copilot_code_review",
      "parameters": {
        "review_draft_pull_requests": false,
        "review_on_push": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {"context": "Security Gate Validation"},
          {"context": "Dependency & Standards Validation"},
          {"context": "Check REUSE Compliance"}
        ]
      }
    }
  ]
}
```

> The `copilot_code_review` rule auto-requests Copilot on every PR opened against the default branch. `review_draft_pull_requests: false` skips drafts (Copilot only reviews ready-for-review PRs). `review_on_push: false` means Copilot is requested once per PR, not re-requested on every push. Both align with the desired solo-dev workflow: Copilot review is advisory, not a re-trigger spam loop.

- [ ] **Step 3: Write `williaby-universal.json` (same body, only `name` and `repository_name.exclude` differ)**

Identical to step 2 except:

```json
"name": "williaby-default-branch-baseline",
...
"repository_name": {"include": ["~ALL"], "exclude": ["homelab-agent-configs"], "protected": true}
```

- [ ] **Step 4: Write `ByronWilliamsCPA-python.json`**

```json
{
  "name": "ByronWilliamsCPA-python-tier-ci-gate",
  "target": "branch",
  "enforcement": "evaluate",
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {
    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []},
    "repository_name": {"include": ["__GENERATED__"], "exclude": [], "protected": true}
  },
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {"context": "CI Gate"}
        ]
      }
    }
  ]
}
```

The `__GENERATED__` token is replaced at apply-time by `setup_org_rulesets.py` after reading the catalog (Task 9 generates the include list).

- [ ] **Step 5: Write `williaby-python.json`**

Identical to step 4 except `name` is `"williaby-python-tier-ci-gate"`.

- [ ] **Step 6: Validate the JSON parses**

```bash
for f in docs/reference/org-rulesets/*.json; do
  python -c "import json,sys; json.load(open(sys.argv[1])); print('OK', sys.argv[1])" "$f"
done
```

Expected: 4 lines of `OK ...`.

- [ ] **Step 7: Commit**

```bash
git add docs/reference/org-rulesets/
git commit -m "feat(rulesets): add four org-ruleset JSON bodies (universal + python-tier × 2 orgs)"
```

### Task 8: Generator for Python-tier repo include list

**Files:**
- Create: `scripts/generate_python_tier_repos.py`
- Test: `tests/unit/test_generate_python_tier_repos.py`

- [ ] **Step 1: Write failing test**

```python
import json
from pathlib import Path
from scripts.generate_python_tier_repos import python_repos_for_org

def test_python_repos_excludes_exempt(tmp_path):
    catalog = tmp_path / "github-repos.json"
    catalog.write_text(json.dumps({
        "repos": [
            {"org": "BW", "name": "py-app", "repositoryType": "python-app", "branchProtectionExempt": False},
            {"org": "BW", "name": "config-only", "repositoryType": "config", "branchProtectionExempt": False},
            {"org": "BW", "name": "py-exempt", "repositoryType": "python-app", "branchProtectionExempt": True},
        ]
    }))
    assert python_repos_for_org("BW", catalog) == ["py-app"]
```

Run: `uv run pytest tests/unit/test_generate_python_tier_repos.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement**

```python
"""Emit Python-tier repo include list for the org-ruleset Python-tier body."""
import json
import sys
from pathlib import Path

PYTHON_TYPES = frozenset({"python-package", "python-app", "python-script"})

def python_repos_for_org(org: str, catalog_path: Path) -> list[str]:
    data = json.loads(catalog_path.read_text())
    return sorted(
        repo["name"]
        for repo in data["repos"]
        if repo["org"] == org
        and repo.get("repositoryType") in PYTHON_TYPES
        and not repo.get("branchProtectionExempt")
    )

def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: generate_python_tier_repos.py <org> <catalog-path>", file=sys.stderr)
        return 2
    org, catalog = argv[1], Path(argv[2])
    for name in python_repos_for_org(org, catalog):
        print(name)
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 3: Run test and live invocation**

Run: `uv run pytest tests/unit/test_generate_python_tier_repos.py -v`
Expected: PASS.

Run: `uv run python scripts/generate_python_tier_repos.py ByronWilliamsCPA docs/reference/github-repos.json | head -5`
Expected: 5 Python repo names from BW org.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_python_tier_repos.py tests/unit/test_generate_python_tier_repos.py
git commit -m "feat(rulesets): add Python-tier repo enumerator from catalog"
```

### Task 9: Implement `setup_org_rulesets.py` with solo-dev guard

**Files:**
- Create: `scripts/setup_org_rulesets.py`
- Test: `tests/unit/test_setup_org_rulesets.py`

- [ ] **Step 1: Write failing solo-dev guard test**

```python
import json
import pytest
from pathlib import Path
from scripts.setup_org_rulesets import validate_solo_dev_safe, SoloDevViolation

def test_rejects_required_approving_reviews_gt_0():
    body = {"rules": [{"type": "pull_request", "parameters": {"required_approving_review_count": 1}}]}
    with pytest.raises(SoloDevViolation, match="required_approving_review_count"):
        validate_solo_dev_safe(body)

def test_accepts_zero_review_count():
    body = {"rules": [{"type": "pull_request", "parameters": {"required_approving_review_count": 0}}]}
    validate_solo_dev_safe(body)  # no exception

def test_accepts_no_pull_request_rule():
    body = {"rules": [{"type": "required_signatures"}]}
    validate_solo_dev_safe(body)
```

Run: `uv run pytest tests/unit/test_setup_org_rulesets.py -v`
Expected: 3 fail (module doesn't exist).

- [ ] **Step 2: Implement guard, body loader, and CLI skeleton**

```python
"""Apply an org ruleset JSON body to a GitHub org via gh CLI.

Solo-dev safety: refuses to apply any body that would require human PR
approval (required_approving_review_count > 0). The user merges their own PRs;
restoring approval requirements would lock the repo.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

CATALOG_DEFAULT = Path("docs/reference/github-repos.json")

class SoloDevViolation(RuntimeError):
    pass

def validate_solo_dev_safe(body: dict) -> None:
    for rule in body.get("rules", []):
        if rule.get("type") != "pull_request":
            continue
        params = rule.get("parameters", {}) or {}
        count = params.get("required_approving_review_count", 0)
        if count and count > 0:
            raise SoloDevViolation(
                f"Body requires {count} approving reviews; solo-dev policy "
                "forbids any value > 0. The user merges their own PRs."
            )

def render_body(body: dict, org: str, catalog: Path) -> dict:
    """Substitute __GENERATED__ tokens with catalog-derived values."""
    out = json.loads(json.dumps(body))  # deep copy
    repo_cond = out.get("conditions", {}).get("repository_name", {})
    if repo_cond.get("include") == ["__GENERATED__"]:
        from scripts.generate_python_tier_repos import python_repos_for_org
        repo_cond["include"] = python_repos_for_org(org, catalog)
    return out

def find_existing_ruleset(org: str, name: str) -> int | None:
    out = subprocess.check_output(
        ["gh", "api", f"orgs/{org}/rulesets", "--jq", ".[] | {id, name}"],
        text=True,
    )
    for line in out.strip().split("\n"):
        if not line:
            continue
        rs = json.loads(line)
        if rs.get("name") == name:
            return rs.get("id")
    return None

def apply(org: str, body_path: Path, enforcement: str | None, catalog: Path,
          dry_run: bool) -> None:
    body = json.loads(body_path.read_text())
    validate_solo_dev_safe(body)
    body = render_body(body, org, catalog)
    if enforcement:
        body["enforcement"] = enforcement
    name = body["name"]
    existing_id = find_existing_ruleset(org, name)
    payload = json.dumps(body)
    if dry_run:
        print(f"DRY RUN: would {'PUT' if existing_id else 'POST'} ruleset '{name}' to org '{org}'")
        print(payload)
        return
    if existing_id:
        cmd = ["gh", "api", "-X", "PUT", f"orgs/{org}/rulesets/{existing_id}",
               "--input", "-"]
    else:
        cmd = ["gh", "api", "-X", "POST", f"orgs/{org}/rulesets", "--input", "-"]
    subprocess.run(cmd, input=payload, text=True, check=True)
    print(f"Applied ruleset '{name}' to org '{org}' (enforcement={body['enforcement']})")

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
    parser.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        apply(args.org, args.body, args.enforcement, args.catalog, args.dry_run)
    except SoloDevViolation as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 3: Run guard tests**

Run: `uv run pytest tests/unit/test_setup_org_rulesets.py -v`
Expected: 3 passed.

- [ ] **Step 4: Add render and apply tests**

```python
def test_render_substitutes_generated_token(tmp_path):
    from scripts.setup_org_rulesets import render_body
    catalog = tmp_path / "cat.json"
    catalog.write_text(json.dumps({"repos": [
        {"org": "BW", "name": "py", "repositoryType": "python-app", "branchProtectionExempt": False}
    ]}))
    body = {"conditions": {"repository_name": {"include": ["__GENERATED__"]}}}
    out = render_body(body, "BW", catalog)
    assert out["conditions"]["repository_name"]["include"] == ["py"]

def test_dry_run_makes_no_api_calls(monkeypatch, tmp_path, capsys):
    from scripts.setup_org_rulesets import apply
    body_path = tmp_path / "body.json"
    body_path.write_text(json.dumps({
        "name": "test", "rules": [],
        "conditions": {"repository_name": {"include": ["~ALL"]}}
    }))
    catalog = tmp_path / "c.json"
    catalog.write_text(json.dumps({"repos": []}))
    called = []
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: called.append("check_output") or "")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: called.append("run"))
    apply("BW", body_path, None, catalog, dry_run=True)
    assert "run" not in called
    out = capsys.readouterr().out
    assert "DRY RUN" in out
```

Run: `uv run pytest tests/unit/test_setup_org_rulesets.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_org_rulesets.py tests/unit/test_setup_org_rulesets.py
git commit -m "feat(rulesets): add setup_org_rulesets.py with solo-dev guard"
```

### Task 9b: Add `setup_repo_rulesets.py` for per-repo overrides (optional, parallel to Task 9)

> Goal: cover the user's "store org and repo level standards as JSON" requirement. Repo-level rulesets are not needed for the migration itself, but the script is a thin variant of Task 9 and gives future flexibility (e.g., a single repo wants an extra status check without changing the org default).

**Files:**
- Create: `scripts/setup_repo_rulesets.py`
- Create: `docs/reference/repo-rulesets/.gitkeep` (empty directory marker)
- Test: `tests/unit/test_setup_repo_rulesets.py`

- [ ] **Step 1: Create the script (90% of code is shared with Task 9)**

```python
"""Apply a repo-level ruleset JSON body to a single GitHub repo via gh CLI.

Mirrors setup_org_rulesets.py but POSTs to /repos/:owner/:repo/rulesets.
Same solo-dev guard: refuses any body with required_approving_review_count > 0.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.setup_org_rulesets import SoloDevViolation, validate_solo_dev_safe

def find_existing_repo_ruleset(repo_slug: str, name: str) -> int | None:
    out = subprocess.check_output(
        ["gh", "api", f"repos/{repo_slug}/rulesets", "--jq", ".[] | {id, name}"],
        text=True,
    )
    for line in out.strip().split("\n"):
        if not line:
            continue
        rs = json.loads(line)
        if rs.get("name") == name:
            return rs.get("id")
    return None

def apply(repo_slug: str, body_path: Path, enforcement: str | None,
          dry_run: bool) -> None:
    body = json.loads(body_path.read_text())
    validate_solo_dev_safe(body)
    if enforcement:
        body["enforcement"] = enforcement
    name = body["name"]
    existing_id = find_existing_repo_ruleset(repo_slug, name)
    payload = json.dumps(body)
    if dry_run:
        print(f"DRY RUN: would {'PUT' if existing_id else 'POST'} ruleset '{name}' to repo '{repo_slug}'")
        print(payload)
        return
    if existing_id:
        cmd = ["gh", "api", "-X", "PUT", f"repos/{repo_slug}/rulesets/{existing_id}", "--input", "-"]
    else:
        cmd = ["gh", "api", "-X", "POST", f"repos/{repo_slug}/rulesets", "--input", "-"]
    subprocess.run(cmd, input=payload, text=True, check=True)
    print(f"Applied ruleset '{name}' to repo '{repo_slug}' (enforcement={body['enforcement']})")

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo slug")
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        apply(args.repo, args.body, args.enforcement, args.dry_run)
    except SoloDevViolation as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 2: Write tests mirroring Task 9 step 4**

```python
import json
import pytest
from pathlib import Path
from scripts.setup_repo_rulesets import apply
from scripts.setup_org_rulesets import SoloDevViolation

def test_repo_script_rejects_required_reviews(tmp_path):
    body = tmp_path / "body.json"
    body.write_text(json.dumps({
        "name": "test",
        "rules": [{"type": "pull_request", "parameters": {"required_approving_review_count": 1}}],
    }))
    with pytest.raises(SoloDevViolation):
        apply("BW/r", body, None, dry_run=True)

def test_repo_script_dry_run_makes_no_api_calls(monkeypatch, tmp_path, capsys):
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"name": "test", "rules": []}))
    called = []
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: called.append("check_output") or "")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: called.append("run"))
    apply("BW/r", body, None, dry_run=True)
    assert "run" not in called
    assert "DRY RUN" in capsys.readouterr().out
```

Run: `uv run pytest tests/unit/test_setup_repo_rulesets.py -v`
Expected: 2 passed.

- [ ] **Step 3: Create the empty docs directory**

```bash
mkdir -p docs/reference/repo-rulesets
touch docs/reference/repo-rulesets/.gitkeep
```

Add a one-line README.md in that directory:

```markdown
## Per-repo ruleset bodies

JSON files in this directory follow the same schema as `../org-rulesets/`. Filename convention: `<org>__<repo>.json`. Apply via `uv run python scripts/setup_repo_rulesets.py --repo <org>/<repo> --body docs/reference/repo-rulesets/<org>__<repo>.json --enforcement active`. The org-level rulesets in `../org-rulesets/` define the universal baseline; per-repo rulesets are additive (a repo's effective protection is the union of every ruleset that targets its default branch).
```

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_repo_rulesets.py tests/unit/test_setup_repo_rulesets.py docs/reference/repo-rulesets/
git commit -m "feat(rulesets): add setup_repo_rulesets.py for per-repo override JSON"
```

---

## Track 3: Manifest and Catalog Updates

### Task 10: Add `migrationPhase` field to repo catalog schema

**Files:**
- Modify: `docs/reference/github-repos.json`
- Modify: `docs/reference/github-repos.md` (if it exists)

- [ ] **Step 1: Add migrationPhase to every non-exempt repo with default value `pending`**

```bash
jq '.repos |= map(if .branchProtectionExempt then . else . + {migrationPhase: "pending"} end)' \
  docs/reference/github-repos.json > /tmp/cat.json
mv /tmp/cat.json docs/reference/github-repos.json
```

- [ ] **Step 2: Verify count**

Run: `jq '[.repos[] | select(.migrationPhase == "pending")] | length' docs/reference/github-repos.json`
Expected: 45 (the non-exempt count).

- [ ] **Step 3: Update the catalog _meta._notes section to document the field**

In the `_meta` block of the JSON, add to `_notes`:

```text
migrationPhase: tracks ruleset migration state per repo.
Values: pending (classic only), dual (classic + ruleset, both active),
complete (rulesets only, classic stripped). N/A for branchProtectionExempt repos.
```

- [ ] **Step 4: Commit**

```bash
git add docs/reference/github-repos.json
git commit -m "feat(catalog): add migrationPhase field for ruleset migration tracking"
```

### Task 11: Update standards-manifest.yaml

**Files:**
- Modify: `docs/standards-manifest.yaml:437-444` (CI-023 rewrite)
- Modify: `docs/standards-manifest.yaml` (insert CI-025/026/027 after CI-024)

- [ ] **Step 1: Rewrite CI-023**

Replace lines 437-444 with:

```yaml
  - id: CI-023
    domain: ci
    severity: critical
    description: >-
      Effective required-status-checks (classic protection ∪ repo rulesets ∪
      org rulesets targeting this repo) exactly equal required_checks names.
    verify: "protection_matches_required_checks: docs/standards-manifest.yaml, source=union"
    override_eligible: false
    not_applicable_when: "repo.branchProtectionExempt == true"
```

- [ ] **Step 2: Add solo-dev guard annotation**

Near the top of the file (after the `required_checks:` block at ~line 8-20), add:

```yaml
solo_dev_constraints:
  forbid_required_approving_reviews: true
  notes: >-
    All managed repos are solo-dev; required_approving_review_count must remain 0
    in every classic protection state and every ruleset rule.
    setup_org_rulesets.py enforces this with a hard guard.
```

- [ ] **Step 3: Add CI-025/026/027**

Insert after CI-024 (~line 453):

```yaml
  - id: CI-025
    domain: ci
    severity: critical
    description: >-
      Each managed org has at least one ruleset with enforcement=active
      targeting the default branch of every non-exempt repo.
    verify: "org_ruleset_present: orgs=[ByronWilliamsCPA,williaby], enforcement=active"
    override_eligible: false
    not_applicable_when: "repo.branchProtectionExempt == true"

  - id: CI-026
    domain: ci
    severity: important
    description: >-
      Org ruleset includes a copilot_code_review rule, which auto-requests
      Copilot review on every PR opened against the default branch. Replaces
      the per-PR runtime trigger in /pr-review.
    verify: "ruleset_contains_rule: orgs=[ByronWilliamsCPA,williaby], rule_type=copilot_code_review"
    override_eligible: true
    not_applicable_when: "repo.branchProtectionExempt == true"
    notes: >-
      Copilot status check 'Copilot' may additionally be added to
      required_status_checks once stability is confirmed (Phase 3.5),
      which would make Copilot review blocking rather than advisory.

  - id: CI-027
    domain: ci
    severity: important
    description: >-
      Classic branch protection is ABSENT once migration has completed
      for this repo (prevents drift back to two sources of truth).
    verify: "classic_protection_absent: branch=default"
    override_eligible: true
    not_applicable_when: "repo.branchProtectionExempt == true OR repo.migrationPhase != complete"
```

- [ ] **Step 4: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -m "feat(manifest): rewrite CI-023 for union mode; add CI-025/026/027 for ruleset migration"
```

---

## Track 4: Auditor Agent Updates

### Task 12: Update CI-022/023/024 invocation block in ossf-compliance-auditor.md

**Files:**
- Modify: `.claude/agents/ossf-compliance-auditor.md:101-115`

- [ ] **Step 1: Add `--source union` to the script invocation**

Replace lines 105-113:

```bash
python scripts/check-required-checks.py \
  --repo-path "${REPO_PATH}" \
  --manifest "${HOME}/.claude/docs/standards-manifest.yaml" \
  --registry "${HOME}/.claude/docs/reusable-workflow-jobs.yaml" \
  --repo-slug "${REPO_SLUG}" \
  --branch "${DEFAULT_BRANCH:-main}" \
  --check-bp \
  --source "${PROTECTION_SOURCE:-union}"
```

Add a paragraph after the code block:

> The `--source` flag is selected from `repo.migrationPhase` in the catalog: `pending` → `classic`, `dual` → `union` (default), `complete` → `rulesets`. Pass via `PROTECTION_SOURCE` env var when invoking from a higher-level harness; default `union` is the safest fallback.

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/ossf-compliance-auditor.md
git commit -m "docs(auditor): add --source flag to CI-022/023/024 invocation"
```

### Task 13: Replace PATCH commands at lines 134-142

**Files:**
- Modify: `.claude/agents/ossf-compliance-auditor.md:128-142`

- [ ] **Step 1: Replace the single PATCH block with three branches**

```text
The remediation depends on which source the finding's provenance line points at:

**Drift in a REPO-LEVEL ruleset:**
\`\`\`bash
gh api repos/${REPO_SLUG}/rulesets/${RULESET_ID} --method PUT --input updated-ruleset.json
\`\`\`

**Drift in an ORG-LEVEL ruleset:**
\`\`\`bash
uv run python scripts/setup_org_rulesets.py --org ${ORG} \
  --body docs/reference/org-rulesets/${ORG}-${TIER}.json \
  --enforcement active
\`\`\`

**Drift remaining in classic protection (transition window only):**
\`\`\`bash
gh api repos/${REPO_SLUG}/branches/${DEFAULT_BRANCH:-main}/protection/required_status_checks \
  --method PATCH \
  --field 'contexts[]=<name>' \
  --field 'strict=true'
\`\`\`
```

Update the `AskUserQuestion` block at lines 130-132 to offer all three choices instead of two.

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/ossf-compliance-auditor.md
git commit -m "docs(auditor): branch CI-023 remediation by source (org/repo ruleset, classic)"
```

### Task 14: Add CI-025/026/027 FINDING templates and Branch-Protection scorecard update

**Files:**
- Modify: `.claude/agents/ossf-compliance-auditor.md:150` (insert after CI-024 prompts)
- Modify: `.claude/agents/ossf-compliance-auditor.md:308-326` (Branch-Protection scorecard remediation copy)

- [ ] **Step 1: Insert CI-025/026/027 FINDING templates after line 150**

```text
**For CI-025 findings (org ruleset missing):**

\`\`\`text
FINDING:
id: CI-025
severity: critical
description: Org '<ORG>' has no active ruleset targeting default branch
status: configuration_gap
current_value: gh api orgs/<ORG>/rulesets returned [] or all entries have enforcement != active
remediation: |
  uv run python scripts/setup_org_rulesets.py --org <ORG> \
    --body docs/reference/org-rulesets/<ORG>-universal.json --enforcement active
  uv run python scripts/setup_org_rulesets.py --org <ORG> \
    --body docs/reference/org-rulesets/<ORG>-python.json --enforcement active
\`\`\`

**For CI-026 findings (Copilot rule missing from ruleset):**

\`\`\`text
FINDING:
id: CI-026
severity: important
description: Org ruleset is missing the copilot_code_review rule
status: configuration_gap
current_value: ruleset id=<id> has no rule of type copilot_code_review
remediation: |
  The Copilot rule is defined in docs/reference/org-rulesets/<ORG>-universal.json.
  Re-apply via:
  uv run python scripts/setup_org_rulesets.py --org <ORG> \\
    --body docs/reference/org-rulesets/<ORG>-universal.json --enforcement active
\`\`\`

**For CI-027 findings (classic protection still present post-migration):**

\`\`\`text
FINDING:
id: CI-027
severity: important
description: Classic branch protection still present on <repo>:<branch> after migrationPhase=complete
status: configuration_gap
current_value: gh api repos/<repo>/branches/<branch>/protection returned 200
remediation: |
  Verify the org rulesets enforce equivalent constraints, then:
  gh api repos/<repo>/branches/<branch>/protection --method DELETE
  Re-run: uv run python scripts/check-required-checks.py --source rulesets --repo-slug <repo> --check-bp
\`\`\`
```

- [ ] **Step 2: Update Branch-Protection scorecard remediation (lines 308-326)**

Add a banner before the existing JSON example:

```text
### Branch-Protection (High)

**Measures:** GitHub branch protection settings on the default branch.
Scorecard now reads BOTH classic protection and rulesets; rulesets are the
preferred mechanism since they read with the default GITHUB_TOKEN (no admin
PAT required).

**Score >= 4 (Tier 1):** ... (unchanged)
**Score >= 6 (Tier 2):** ... (unchanged)
**Score >= 8 (Tier 3):** ... (unchanged)

**Remediation (preferred):** Use the org-level ruleset:
\`\`\`bash
uv run python scripts/setup_org_rulesets.py --org <ORG> \
  --body docs/reference/org-rulesets/<ORG>-universal.json --enforcement active
\`\`\`

**Remediation (legacy classic protection, transition only):** [keep existing JSON example with banner "(legacy , use rulesets first)"]
```

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/ossf-compliance-auditor.md
git commit -m "docs(auditor): add CI-025/026/027 finding templates; update Branch-Protection remediation"
```

---

## Track 5: Pre-flight (Org-level GitHub State, Evaluate Mode)

> Goal: rulesets exist in both orgs in `evaluate` mode, classic protection is backed up, validators report clean against current state. NO enforcement change yet.

### Task 15: Backup all 45 classic protection states

**Files:**
- Create: `backups/branch-protection-2026-05-08/` (gitignored runtime data)
- Modify: `.gitignore` (add `backups/` if not present)

- [ ] **Step 1: Add backups dir to gitignore**

Check: `grep -q "^backups/" .gitignore && echo PRESENT || echo MISSING`
If MISSING, append `backups/` to `.gitignore` and commit.

- [ ] **Step 2: Run the backup loop**

```bash
mkdir -p backups/branch-protection-2026-05-08
while IFS=/ read -r org repo; do
  branch=$(jq -r --arg o "$org" --arg r "$repo" \
    '.repos[] | select(.org==$o and .name==$r) | .defaultBranch' \
    docs/reference/github-repos.json)
  gh api "repos/$org/$repo/branches/$branch/protection" \
    > "backups/branch-protection-2026-05-08/${org}__${repo}.json" 2>/dev/null \
    || echo '{"_error":"no protection"}' \
       > "backups/branch-protection-2026-05-08/${org}__${repo}.json"
done < <(jq -r '.repos[] | select(.branchProtectionExempt != true) | "\(.org)/\(.name)"' \
            docs/reference/github-repos.json)
```

- [ ] **Step 3: Verify 45 backups exist**

Run: `ls backups/branch-protection-2026-05-08/ | wc -l`
Expected: `45`

Run: `grep -l '"_error"' backups/branch-protection-2026-05-08/ | wc -l`
Note the count of repos that had no prior protection (e.g., `family-office-portal`); they will skip restore in the rollback path.

### Task 16: POST four rulesets in evaluate mode

- [ ] **Step 1: ByronWilliamsCPA universal**

```bash
uv run python scripts/setup_org_rulesets.py --org ByronWilliamsCPA \
  --body docs/reference/org-rulesets/ByronWilliamsCPA-universal.json \
  --enforcement evaluate
```

Expected output: `Applied ruleset 'ByronWilliamsCPA-default-branch-baseline' to org 'ByronWilliamsCPA' (enforcement=evaluate)`

- [ ] **Step 2: ByronWilliamsCPA python tier**

```bash
uv run python scripts/setup_org_rulesets.py --org ByronWilliamsCPA \
  --body docs/reference/org-rulesets/ByronWilliamsCPA-python.json \
  --enforcement evaluate
```

- [ ] **Step 3: williaby universal**

```bash
uv run python scripts/setup_org_rulesets.py --org williaby \
  --body docs/reference/org-rulesets/williaby-universal.json \
  --enforcement evaluate
```

- [ ] **Step 4: williaby python tier**

```bash
uv run python scripts/setup_org_rulesets.py --org williaby \
  --body docs/reference/org-rulesets/williaby-python.json \
  --enforcement evaluate
```

- [ ] **Step 5: Verify all four rulesets exist**

```bash
gh api /orgs/ByronWilliamsCPA/rulesets --jq '.[] | {id, name, enforcement, target}'
gh api /orgs/williaby/rulesets --jq '.[] | {id, name, enforcement, target}'
```

Expected: 2 entries per org with `enforcement: "evaluate"`.

- [ ] **Step 6: Run union-mode validator on canary repos to confirm no drift**

```bash
uv run python scripts/check-required-checks.py \
  --repo-slug ByronWilliamsCPA/.claude --branch main --check-bp --source union
uv run python scripts/check-required-checks.py \
  --repo-slug williaby/.claude --branch main --check-bp --source union
```

Expected: exit code 0, no findings (classic still satisfies; ruleset adds nothing in evaluate mode that creates drift).

---

## Track 6: Canary Validation

> Goal: prove that ruleset-only protection is mergeable for the solo dev on one repo per org before sweeping the rest.

### Task 17: Flip rulesets to active and verify mergeability

- [ ] **Step 1: Flip universal rulesets to active**

```bash
uv run python scripts/setup_org_rulesets.py --org ByronWilliamsCPA \
  --body docs/reference/org-rulesets/ByronWilliamsCPA-universal.json --enforcement active
uv run python scripts/setup_org_rulesets.py --org williaby \
  --body docs/reference/org-rulesets/williaby-universal.json --enforcement active
```

- [ ] **Step 2: Open a no-op test PR on each canary**

In the BW canary working tree:

```bash
git checkout -b canary/ruleset-test
echo "<!-- canary -->" >> README.md
git commit -am "chore: canary test for ruleset enforcement"
git push -u origin canary/ruleset-test
gh pr create --title "Canary: ruleset enforcement test" --body "Verifies merge button enables for solo dev under active ruleset."
```

Repeat for the williaby canary.

- [ ] **Step 3: Verify CI runs and merge button enables**

Wait for CI to complete (~5 min). Confirm:

```bash
gh pr checks <PR_NUMBER>
gh pr view <PR_NUMBER> --json mergeable,mergeStateStatus
```

Expected: `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` after checks pass.

If `BLOCKED`: rollback (restore canary classic protection from backup) and investigate ruleset config.

- [ ] **Step 4: Self-merge each canary PR**

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

Expected: success. This validates that solo-dev merge works under active ruleset.

### Task 18: Strip classic protection from canary repos

- [ ] **Step 1: Delete classic protection on BW canary**

```bash
gh api -X DELETE repos/ByronWilliamsCPA/.claude/branches/main/protection
```

- [ ] **Step 2: Delete classic protection on williaby canary**

```bash
gh api -X DELETE repos/williaby/.claude/branches/main/protection
```

- [ ] **Step 3: Update catalog migrationPhase for both canaries**

```bash
jq '.repos |= map(if (.org+"/"+.name) == "ByronWilliamsCPA/.claude" or (.org+"/"+.name) == "williaby/.claude" then .migrationPhase = "complete" else . end)' \
  docs/reference/github-repos.json > /tmp/cat.json
mv /tmp/cat.json docs/reference/github-repos.json
```

- [ ] **Step 4: Validate ruleset-only mode passes**

```bash
uv run python scripts/check-required-checks.py \
  --repo-slug ByronWilliamsCPA/.claude --branch main --check-bp --source rulesets
uv run python scripts/check-required-checks.py \
  --repo-slug williaby/.claude --branch main --check-bp --source rulesets
```

Expected: exit code 0, no findings.

- [ ] **Step 5: Re-run Scorecard on each canary**

```bash
gh workflow run scorecard.yml --repo ByronWilliamsCPA/.claude
gh workflow run scorecard.yml --repo williaby/.claude
```

Wait ~3 min, then:

```bash
gh run list --repo ByronWilliamsCPA/.claude --workflow=scorecard.yml --limit 1 --json conclusion,url
```

Expected: `conclusion: "success"`. Visit the URL and confirm Branch-Protection score >= 8.

- [ ] **Step 6: Commit catalog change**

```bash
git add docs/reference/github-repos.json
git commit -m "chore(catalog): mark canary repos as migrationPhase=complete"
```

---

## Track 7: Sweep (43 Remaining Repos)

> Goal: strip classic protection from every non-exempt, non-canary repo. The ruleset is already `active` (Phase 1), so each repo flips from "ruleset OR classic" to "ruleset only" with no protection gap.

### Task 19: Author and execute the sweep loop

**Files:**
- Create: `scripts/sweep_strip_classic_protection.sh`

- [ ] **Step 1: Write the sweep script**

```bash
#!/usr/bin/env bash
set -euo pipefail

CATALOG=docs/reference/github-repos.json
BACKUP_DIR=backups/branch-protection-2026-05-08
LOG=backups/sweep-$(date +%Y-%m-%d).log
CANARIES="ByronWilliamsCPA/.claude williaby/.claude"

> "$LOG"

while IFS= read -r repo; do
  org=${repo%%/*}; name=${repo##*/}
  case " $CANARIES " in *" $repo "*) echo "skip canary $repo" | tee -a "$LOG"; continue;; esac

  branch=$(jq -r --arg r "$repo" \
    '.repos[] | select(.org+"/"+.name==$r) | .defaultBranch' "$CATALOG")

  test -s "$BACKUP_DIR/${org}__${name}.json" || { echo "MISSING BACKUP $repo" | tee -a "$LOG"; exit 1; }

  echo "Stripping $repo:$branch" | tee -a "$LOG"
  gh api -X DELETE "repos/$repo/branches/$branch/protection" 2>>"$LOG" || true

  uv run python scripts/check-required-checks.py \
    --repo-slug "$repo" --branch "$branch" --check-bp --source rulesets \
    >>"$LOG" 2>&1 || { echo "DRIFT $repo" | tee -a "$LOG"; exit 1; }

  echo "OK $repo" | tee -a "$LOG"
done < <(jq -r '.repos[] | select(.branchProtectionExempt != true) | .org+"/"+.name' "$CATALOG")

echo "SWEEP COMPLETE: $(grep -c "^OK" "$LOG") repos stripped"
```

- [ ] **Step 2: Dry-run first by replacing `gh api -X DELETE` with `echo`**

Manually edit step 1 to comment out the DELETE line, run, confirm log shows all 43 expected repos. Then revert.

- [ ] **Step 3: Execute the sweep**

```bash
chmod +x scripts/sweep_strip_classic_protection.sh
bash scripts/sweep_strip_classic_protection.sh
```

Expected output: `SWEEP COMPLETE: 43 repos stripped`. Log file at `backups/sweep-YYYY-MM-DD.log`.

- [ ] **Step 4: Update catalog migrationPhase to complete for all swept repos**

```bash
jq '.repos |= map(if .branchProtectionExempt then . elif .migrationPhase == "complete" then . else .migrationPhase = "complete" end)' \
  docs/reference/github-repos.json > /tmp/cat.json
mv /tmp/cat.json docs/reference/github-repos.json
```

- [ ] **Step 5: Org-wide union audit confirms no drift**

```bash
while IFS=/ read -r org repo; do
  branch=$(jq -r --arg o "$org" --arg r "$repo" \
    '.repos[] | select(.org==$o and .name==$r) | .defaultBranch' \
    docs/reference/github-repos.json)
  uv run python scripts/check-required-checks.py \
    --repo-slug "$org/$repo" --branch "$branch" --check-bp --source union \
    || echo "DRIFT $org/$repo"
done < <(jq -r '.repos[] | select(.branchProtectionExempt != true) | "\(.org)/\(.name)"' \
            docs/reference/github-repos.json)
```

Expected: no `DRIFT` lines.

- [ ] **Step 6: Commit catalog and sweep script**

```bash
git add docs/reference/github-repos.json scripts/sweep_strip_classic_protection.sh
git commit -m "chore(migration): sweep complete; all 45 repos on ruleset-only protection"
```

---

## Track 8: Copilot Verification and Skill Updates

> Goal: confirm the `copilot_code_review` ruleset rule is auto-requesting Copilot on every PR (it was applied as part of Task 16 / Task 17), then update the PR-review skill to drop the runtime trigger code.

### Task 20: Verify Copilot auto-request fires from ruleset

> Note: there is NO separate UI or API step required. The `copilot_code_review` rule was included in the universal ruleset bodies (Task 7) and applied with the rest of the ruleset in Task 16 (evaluate) and Task 17 (active). This task only verifies the rule fires.

- [ ] **Step 1: Confirm the rule appears in both org rulesets**

```bash
gh api /orgs/ByronWilliamsCPA/rulesets --jq '.[].id' | while read id; do
  echo "BW ruleset $id rules:"
  gh api "/orgs/ByronWilliamsCPA/rulesets/$id" --jq '.rules[] | .type'
done
```

Expected: one of the rulesets lists `copilot_code_review` among its rule types.

Repeat for `williaby`.

- [ ] **Step 2: Verify on a live test PR**

Open a no-op PR on `ByronWilliamsCPA/.claude`:

```bash
git checkout -b verify/copilot-auto-request
echo "<!-- copilot verify -->" >> README.md
git commit -am "chore: verify copilot auto-request fires"
git push -u origin verify/copilot-auto-request
gh pr create --title "Verify Copilot auto-request" --body "Confirms ruleset-driven Copilot trigger."
PR=$(gh pr view --json number --jq .number)
sleep 10
gh pr view "$PR" --json requestedReviewers
```

Expected: `requestedReviewers` includes `copilot-pull-request-reviewer` within ~10 seconds of PR open, without any `/pr-review` invocation.

- [ ] **Step 3: Self-merge the verification PR and clean up**

```bash
gh pr merge "$PR" --squash --delete-branch
```

If verification fails, the `copilot_code_review` rule is not firing. Inspect the ruleset's `bypass_actors` (the user must NOT be a bypass actor at the moment of rule evaluation, or the rule is skipped , this is why `bypass_mode: "always"` was chosen rather than `pull_request`). If still failing, check that the user account has access to Copilot code review and the org Copilot quota is not exhausted.

### Task 21: Update PR-review skill workflows

**Files:**
- Modify: `.claude/skills/pr-review/workflows/pr-review.md:60-106`

- [ ] **Step 1: Replace the entire Step 1 block**

Replace lines 60-106 with:

```markdown
### Step 1: Confirm GitHub Copilot Review is queued

Copilot is enrolled as an automatic reviewer via the `copilot_code_review`
rule in the org ruleset (`<ORG>-default-branch-baseline` in both
ByronWilliamsCPA and williaby). It is requested when the PR opens.
No API call from this workflow is needed.

Verify it landed (one-line, non-blocking):

\`\`\`bash
gh api repos/"$OWNER"/"$REPO"/pulls/"$PR_NUMBER" \
  --jq '.requested_reviewers[].login' | grep -q copilot-pull-request-reviewer \
  && echo "Copilot: ruleset-requested OK" \
  || echo "Copilot: NOT requested -- verify copilot_code_review rule in org ruleset"
\`\`\`

If verification fails, the `copilot_code_review` rule is missing or
disabled. Re-apply via:
\`\`\`bash
uv run python scripts/setup_org_rulesets.py --org {ORG} \\
  --body docs/reference/org-rulesets/{ORG}-universal.json --enforcement active
\`\`\`
Do not block the rest of this workflow on the result.
```

- [ ] **Step 2: Update SKILL.md line 38**

Replace:

```text
- **Copilot fires first.** The review request is sent to GitHub Copilot
```

with:

```text
- **Copilot fires first.** The `copilot_code_review` rule in the org
  ruleset auto-requests Copilot when the PR opens, so its async review
  is already running by the time `/pr-review` starts.
```

- [ ] **Step 3: Update rules/git-workflow.md lines 108-112**

Replace the `GitHub Copilot` bullet with:

```markdown
- `GitHub Copilot`: ruleset-required reviewer; fires automatically when
  any PR targeting the default branch opens (the `copilot_code_review`
  rule lives in `<org>-default-branch-baseline` for both orgs).
  Configured via `.github/copilot-instructions.md` to focus on business
  logic, error handling, edge cases, concurrency, and security logic
  flaws that automated linters cannot catch. Leaves advisory comments
  only; not yet a merge blocker (see Phase 3.5 for blocking variant).
```

- [ ] **Step 4: Update rules/pre-commit.md line 46**

Replace:

```text
- [ ] **Copilot review** (optional): for complex logic, request from the Reviewers menu; instructions in `.github/copilot-instructions.md`
```

with:

```text
- [ ] **Copilot review** (automatic, ruleset-driven): fires when PR opens via the `copilot_code_review` rule; address comments before merging. Instructions in `.github/copilot-instructions.md`.
```

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/pr-review/workflows/pr-review.md \
        .claude/skills/pr-review/SKILL.md \
        .claude/rules/git-workflow.md \
        .claude/rules/pre-commit.md
git commit -m "feat(skills): drop pr-review Stage 1b fallback; Copilot now ruleset-driven"
```

---

## Track 9: Cleanup, Documentation, and Memory

### Task 22: Delete old setup_github_protection.py

- [ ] **Step 1: Verify nothing references it**

```bash
grep -rn "setup_github_protection" .claude/ docs/ scripts/ 2>/dev/null
```

Expected: only references in `docs/PROJECT_SETUP.md` and `docs/OPENSSF_COMPLIANCE.md` (handled in Task 23).

- [ ] **Step 2: Delete the file**

```bash
git rm scripts/setup_github_protection.py
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(cleanup): remove setup_github_protection.py (replaced by setup_org_rulesets.py)"
```

### Task 23: Documentation sweep

**Files:**
- Modify: `docs/OPENSSF_COMPLIANCE.md` (lines 123, 150, 359)
- Modify: `docs/PROJECT_SETUP.md` (lines 440-450)
- Modify: `.claude/agents/github-workflow-agent.md` (line 16)
- Modify: `.claude/agents/devops-deployment-agent.md` (line 119, append note)

- [ ] **Step 1: Edit docs/OPENSSF_COMPLIANCE.md**

Line 123: `"Enforced branch protection rules"` → `"Enforced via org-level rulesets (one per org, applied to all non-exempt repos)"`.

Line 150: Replace 4-step UI walkthrough with: `"Org rulesets are managed centrally via scripts/setup_org_rulesets.py. Per-repo branch protection UI is no longer used; see docs/reference/org-rulesets/ for the JSON bodies."`

Line 359: `"Update branch protection rules if needed"` → `"Update org rulesets if needed (single edit applies to all 45 non-exempt repos)"`.

- [ ] **Step 2: Rewrite docs/PROJECT_SETUP.md branch-protection section**

Replace lines 440-450 entirely:

```markdown
### Branch Protection (Org Rulesets)

Branch protection is configured once per org as a ruleset rather than per-repo.
Two rulesets per org:

- **Universal** (`<org>-default-branch-baseline`): applies to all non-exempt
  repos; requires three universal status checks (Security Gate, Dependency
  & Standards, REUSE), signatures, linear history, no force push, no
  deletion. `required_approving_review_count: 0` (solo-dev safe).
- **Python tier** (`<org>-python-tier-ci-gate`): applies only to
  `repositoryType: python-*` repos; adds `CI Gate` status check.

Apply or update via:

\`\`\`bash
uv run python scripts/setup_org_rulesets.py --org ByronWilliamsCPA \
  --body docs/reference/org-rulesets/ByronWilliamsCPA-universal.json \
  --enforcement active
\`\`\`

The script enforces a solo-dev guard: any body with
`required_approving_review_count > 0` is rejected.
```

- [ ] **Step 3: Edit .claude/agents/github-workflow-agent.md line 16**

`"branch protection rules"` → `"org rulesets and ruleset evaluation status"`.

- [ ] **Step 4: Append one line to .claude/agents/devops-deployment-agent.md after line 119**

Add: `"Note: Copilot is auto-requested by the copilot_code_review rule in the org ruleset; this file tunes its review behavior, it does not trigger reviews."`

- [ ] **Step 5: Commit**

```bash
git add docs/OPENSSF_COMPLIANCE.md docs/PROJECT_SETUP.md \
        .claude/agents/github-workflow-agent.md .claude/agents/devops-deployment-agent.md
git commit -m "docs: sweep terminology from branch protection to org rulesets"
```

### Task 24: Update memory notes

**Files:**
- Modify: `~/.claude/projects/-home-byron-dev--claude/memory/project_branch_protection_standards.md`
- Modify: `~/.claude/projects/-home-byron-dev--claude/memory/project_ossf_review_gate.md`

- [ ] **Step 1: Edit `project_branch_protection_standards.md`**

Update frontmatter description: `"Intentional ruleset standards decisions that deviate from GitHub defaults , apply these when auditing or remediating repos"`

Replace body paragraphs:

```markdown
`required_review_thread_resolution = false` is the intended standard across
both org rulesets (`ByronWilliamsCPA-default-branch-baseline`,
`williaby-default-branch-baseline`). Do not flag this as a gap.

**Why:** Conversation resolution enforcement is handled by workflow, not by ruleset.

`williaby/homelab-agent-configs` is permanently exempt from all branch
protection (excluded from the williaby universal ruleset's
`conditions.repository_name.exclude`). Default branch is `agent/hermes`;
no ruleset applies. This is intentional.

**Why:** Structural nuances in that repo make standard ruleset rules inapplicable.

**How to apply:** When running repo-compliance or any branch protection
audit, skip `required_review_thread_resolution` as a check, and exclude
`williaby/homelab-agent-configs` from ruleset findings entirely. Both
decisions are codified in the org rulesets at
`docs/reference/org-rulesets/` and in the `branchProtectionExempt` flag
in `docs/reference/github-repos.json`.
```

- [ ] **Step 2: Append migration note to `project_ossf_review_gate.md`**

After the existing body, append:

```markdown

**Migration note (2026-05-08):** This standard is now enforced by the
org-level rulesets' `pull_request` rule (`required_approving_review_count: 0`)
in addition to per-repo classic protection. The setup_org_rulesets.py script
has a hard guard that refuses to apply any body with a non-zero value.
Restoring approval requirements when a second contributor joins requires
both updating the org ruleset JSON bodies AND removing the guard.
```

- [ ] **Step 3: Update MEMORY.md index entry to reflect ruleset focus**

Edit the line for branch protection standards in `~/.claude/projects/-home-byron-dev--claude/memory/MEMORY.md` to:

```text
- [Branch protection / ruleset standards](project_branch_protection_standards.md) , review_thread_resolution=false intentional standard; homelab-agent-configs permanently exempt from rulesets
```

### Task 25: Final org-wide audit

- [ ] **Step 1: Run repo-compliance across both orgs**

Use the `/repo-audit` slash command (or invoke the `repo-compliance` skill directly) in scheduled mode for each org.

- [ ] **Step 2: Verify expected results**

- CI-022: PASS for all repos
- CI-023: PASS for all 45 non-exempt repos (effective contexts == required_checks)
- CI-024: PASS (registry freshness unchanged)
- CI-025: PASS for all repos (active org ruleset present)
- CI-026: PASS (`copilot_code_review` rule present in both org rulesets)
- CI-027: PASS for all 45 (classic protection absent, migrationPhase == complete)
- BP-4: PASS (signatures via ruleset)
- BP-5: FAIL with note "solo-dev admin bypass intentional" (informational)

- [ ] **Step 3: Archive backups after 7-day stability window**

```bash
tar czf backups/branch-protection-2026-05-08.tar.gz backups/branch-protection-2026-05-08/
rm -rf backups/branch-protection-2026-05-08/
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore(migration): rulesets migration complete; archive classic-protection backups"
```

---

## Rollback Procedures

### Per-repo rollback (for sweep-time failures)

**Files:**
- Create: `scripts/restore_classic_protection.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=backups/branch-protection-2026-05-08
TARGET_REPOS=${1:-ALL}

restore_one() {
  local repo=$1 backup=$2
  local org=${repo%%/*}
  local branch=$(jq -r --arg r "$repo" \
    '.repos[] | select(.org+"/"+.name==$r) | .defaultBranch' \
    docs/reference/github-repos.json)
  if grep -q '"_error"' "$backup"; then
    echo "Skipping $repo (no prior protection)"
    return 0
  fi
  jq 'del(._error)' "$backup" \
    | gh api -X PUT "repos/$repo/branches/$branch/protection" --input -
  echo "Restored $repo"
}

if [[ "$TARGET_REPOS" == "ALL" ]]; then
  for f in "$BACKUP_DIR"/*.json; do
    repo=$(basename "$f" .json | tr '_' '/' | sed 's|//|/|')
    restore_one "$repo" "$f"
  done
else
  for repo in $TARGET_REPOS; do
    restore_one "$repo" "$BACKUP_DIR/${repo//\//__}.json"
  done
fi
```

Usage:

```bash
## Single repo rollback
bash scripts/restore_classic_protection.sh ByronWilliamsCPA/Unify

## Org-wide rollback (after first putting all rulesets back to evaluate)
gh api -X PUT /orgs/ByronWilliamsCPA/rulesets/<RULESET_ID> -f enforcement=evaluate
gh api -X PUT /orgs/williaby/rulesets/<RULESET_ID> -f enforcement=evaluate
bash scripts/restore_classic_protection.sh ALL
```

### Trigger conditions for rollback

| Condition | Granularity | Action |
| --- | --- | --- |
| Single repo unmergeable after Phase 2 sweep | Per-repo | `restore_classic_protection.sh <repo>`; investigate that repo's required_checks |
| Scorecard score on canary drops below 4 in Phase 1 | Per-repo, then halt migration | Restore canary; do NOT proceed to sweep |
| `check-required-checks.py --source union` reports drift on > 5% of repos in Phase 2 | Org-wide | Set rulesets to `evaluate`; restore all |
| Copilot enforcement (Phase 3 follow-up) blocks merges that should pass | Org-wide | Remove `Copilot` from ruleset's `required_status_checks` (if it was added) |

---

## Verification Matrix

| Track | Change | Verify command | Expected |
| --- | --- | --- | --- |
| 1 | Validator union mode works | `pytest tests/unit/test_check_required_checks.py -v` | All pass |
| 1 | Compliance script ruleset-aware | `pytest tests/unit/test_check_repo_compliance.py -v` | All pass |
| 2 | Solo-dev guard active | `pytest tests/unit/test_setup_org_rulesets.py -v` | All pass including SoloDevViolation tests |
| 3 | Manifest CI-025/026/027 present | `grep -c "id: CI-02[567]" docs/standards-manifest.yaml` | 3 |
| 4 | Auditor knows about rulesets | `grep -c "setup_org_rulesets" .claude/agents/ossf-compliance-auditor.md` | >= 3 |
| 5 | Backups exist | `ls backups/branch-protection-2026-05-08/ \| wc -l` | 45 |
| 5 | Rulesets exist in evaluate | `gh api /orgs/ByronWilliamsCPA/rulesets --jq '.[].enforcement'` | `evaluate` × 2 |
| 6 | Canary mergeable | `gh pr view <PR> --json mergeable` | `MERGEABLE` |
| 6 | Canary Scorecard | `gh run list --workflow=scorecard.yml --limit 1` | success, score >= 8 |
| 7 | Sweep completed | `grep -c "^OK" backups/sweep-*.log` | 43 |
| 7 | No drift post-sweep | sweep-script org-wide loop | no `DRIFT` lines |
| 8 | `copilot_code_review` rule present in ruleset | `gh api /orgs/<ORG>/rulesets/<id> --jq '.rules[] \| .type'` | includes `copilot_code_review` |
| 8 | Copilot auto-requested on live PR | open test PR; `gh pr view --json requestedReviewers` | includes `copilot-pull-request-reviewer` within ~10s |
| 9 | Old script removed | `test ! -f scripts/setup_github_protection.py` | exit 0 |
| 9 | Docs updated | `grep -r "setup_github_protection" docs/ 2>/dev/null` | no matches |

---

## Solo-Dev Safety Audit (cross-cutting)

This plan must NOT introduce any of the following at any phase:

| Anti-pattern | Where it would appear | Plan's defense |
| --- | --- | --- |
| `required_approving_review_count > 0` in any ruleset body | `docs/reference/org-rulesets/*.json` | Hard-coded `0` in Task 7 step 2; `validate_solo_dev_safe()` guard in Task 9 |
| `required_approving_review_count > 0` in restored classic protection | `backups/branch-protection-2026-05-08/*.json` | Backups are dumps of CURRENT state, which already has count=0 (per the OSSF review gate memory note) |
| Org ruleset rule that requires Copilot APPROVAL (rather than just request) , this would force a human to approve since Copilot can't bypass `pull_request.required_approving_review_count` | If `Copilot` context were added to `required_status_checks` AND treated as a hard merge gate while Copilot intermittently fails to post | The `copilot_code_review` rule only REQUESTS Copilot, it does not require its approval. The optional Phase 3.5 follow-up (adding `Copilot` to `required_status_checks`) makes Copilot review *blocking* via a status check, not via a review-count requirement. Solo dev still self-merges once the Copilot check posts. |
| `bypass_actors: []` (full enforcement, no admin override) | Org ruleset bodies | All four ruleset bodies include the OrganizationAdmin role (`actor_id: 5`) with `bypass_mode: "always"` so user can emergency-unblock |
| Removing the homelab-agent-configs exemption | Sweep loop, ruleset conditions | Sweep loop filters on `branchProtectionExempt != true`; williaby universal ruleset has explicit `repository_name.exclude: ["homelab-agent-configs"]` |

If any future task in this plan or any future PR violates these, treat as a Critical finding.

---

## Self-Review Checklist (for the plan author)

- [x] Spec coverage: all of the user's three requirements (executable across all repos, updates standards + review agents, no self-review barrier) have tasks
- [x] Solo-dev safety: explicit hard guard in Task 9, defended in cross-cutting audit
- [x] Provenance during transition: union-mode validator default in Task 5
- [x] Rollback path: Task-level (sweep loop fail-stop), org-wide (`restore_classic_protection.sh`)
- [x] Documentation sweep: Tasks 21-23 cover skill, rules, OPENSSF, PROJECT_SETUP, agents, memory
- [x] Type/name consistency: `fetch_ruleset_contexts`, `fetch_classic_protection_contexts`, `fetch_effective_required_contexts`, `diff_required_vs_effective` used consistently across Tasks 1-5; ruleset names `<org>-default-branch-baseline` and `<org>-python-tier-ci-gate` consistent across Tasks 7, 16, 17
- [x] Exempt repo handled: `williaby/homelab-agent-configs` excluded from sweep loop (Task 19), excluded from williaby ruleset (Task 7 step 3), kept exempt in audit (Task 6)
- [x] No placeholders: every `<ORG>` token in command examples is paired with an actual org name in the same task; ruleset IDs are noted as discovered-at-runtime values
