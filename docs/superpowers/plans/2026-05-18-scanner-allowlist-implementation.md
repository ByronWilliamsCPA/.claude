---
schema_type: planning
title: Scanner Allowlist Implementation Handoff
status: draft
owner: engineering
component: Development-Tools
source: "PR #116 post-merge /pr-review (2026-05-17); follow-up artifact #3 from PR #119 review (2026-05-18) operationalizes the ADR-008 design into an executable handoff."
tags: [compliance, ci_cd, security, architecture]
purpose: Implementation handoff for ADR-008 (two-tier scanner allowlist for CI-007/007b). Pre-populates the allowlist data, manifest edits, agent updates, and verification steps so a new team can execute end-to-end without further design work.
---

> **For implementing engineers:** This is a self-contained execution plan. Read it
> top-to-bottom once, then work the checkboxes in order. All design decisions are
> already made in [ADR-008](../../architecture/adr/ADR-008-scanner-allowlist-tiers.md);
> do not re-litigate them. If you encounter a case the design doesn't cover, follow
> the "Decision authority" path in section 11 rather than guessing.

**Spec source:** [`docs/architecture/adr/ADR-008-scanner-allowlist-tiers.md`](../../architecture/adr/ADR-008-scanner-allowlist-tiers.md)

**Goal:** Implement the two-tier scanner allowlist design in ADR-008. Move CI-007 and CI-007b detection from inline manifest regex to a tier-classified config file at `docs/standards/scanner-allowlist.yaml`. Switch audit-time detection to `uses:`-first dispatch with `run:` regex as fallback. Encode tool-flag suppression patterns per scanner so CI-007b catches `--exit-zero`, `--soft-fail`, `--exit-code 0`, etc., in addition to the shell `||` form.

**Out of scope (do NOT do in this PR):**

- Adding `--strict` enforcement modes to the manifest tooling
- Renaming any existing check IDs
- Migrating CI-005 SHA pinning to the allowlist pattern (separate ADR)
- Building a Python-script-based detection backend (rejected in ADR-008 Option D)
- Adding a quarterly review automation for the allowlist (separate follow-up)
- Implementing positive-flag requirement checks (e.g., "trivy must use `--exit-code 1`"); CI-007b is a negative-pattern check, not a positive-requirement check. Track as separate CI-007c if needed later.

---

## Section 1: Pre-reading

Spend 30-60 minutes on this before writing code. If any link 404s, the canonical location moved; ask the decision authority (section 11).

| # | Resource | Why |
|---|---|---|
| 1 | [ADR-008](../../architecture/adr/ADR-008-scanner-allowlist-tiers.md) | The design. Read end to end including alternatives. |
| 2 | [PR #116](https://github.com/ByronWilliamsCPA/.claude/pull/116) | The change that exposed the gaps being closed. |
| 3 | [Issue #35](https://github.com/ByronWilliamsCPA/.claude/issues/35) | Original incident report (pp-security-master XXE escape). |
| 4 | [ADR-006: Rules vs Standards](../../architecture/adr/ADR-006-rules-vs-standards.md) | Why allowlist lives in `docs/standards/`, not `.claude/standards/`. |
| 5 | `.claude/standards/manifest-changes.md` (repo root path; outside the mkdocs site) | Commit/PR classification policy. Your PR is `feat(compliance):`. |
| 6 | `docs/standards-manifest.yaml` `CI-007` and `CI-007b` entries (locate by `id:` field; line numbers drift) | Current state you are replacing. |
| 7 | `.claude/agents/devops-deployment-agent.md` Audit Workflow and Remediation Workflow sections (locate by heading; line numbers drift) | Current dispatch logic you are updating. |
| 8 | `.claude/agents/CLAUDE.md` (repo root path; outside the mkdocs site) | Agent authoring conventions (400-line ceiling; reference standards rather than embedding). |
| 9 | [`docs/_data/tags.yml`](../../_data/tags.yml) | Controlled vocabulary for frontmatter tags. Don't invent new ones; the validator will block your commit. |

---

## Section 2: Current state (as of 2026-05-18)

- ADR-008 status: **Proposed**. Must transition to **Accepted** as part of this PR.
- Manifest `CI-007` has scoped detection embedded in `verify`. The scope keyword set is `(security|scan|bandit|safety|audit|sast|dast|trufflehog|gitleaks|semgrep)`.
- Manifest `CI-007b` has the same scanner alternation regex `(bandit|safety|osv-scanner|semgrep|trufflehog|gitleaks|pip-audit)\b.*\|\|\s*(echo|true|:|exit\s+0)` in `verify`.
- Agent's Audit Workflow has handlers for `content_present`, `content_absent`, `pattern_absent`, `file_exists`, `sha_pinned`, `workflow_inventory`, `sonarqube_quality_gate`, and `CI-007` scoped evaluation. None of these are tier-aware.
- No agent-eval harness exists for testing manifest behavior end-to-end. Verification of this PR's behavior is manual against fixture workflow files (see section 7).

---

## Section 3: Acceptance criteria (PR-ready checklist)

The PR is mergeable when all of these are true:

- [ ] `docs/standards/scanner-allowlist.yaml` exists at the path above, schema-valid (see section 6)
- [ ] All `tier: must_block` entries have at least one of `detect.uses` or `detect.run_pattern` populated
- [ ] All `tier: advisory_by_intent` entries have a non-empty `notes:` field
- [ ] No existing scanner from the current CI-007/007b regex is missing from the new allowlist at `tier: must_block` (regression guard)
- [ ] `docs/standards-manifest.yaml` CI-007 and CI-007b `verify` fields reference the allowlist by path
- [ ] `.claude/agents/devops-deployment-agent.md` Audit Workflow has a `scanner_allowlist` handler
- [ ] The handler is `uses:`-first, `run:` fallback, tier-aware (does not flag `advisory_by_intent` entries for CI-007b)
- [ ] `.claude/agents/devops-deployment-agent.md` Remediation Workflow references the new dispatch path
- [ ] ADR-008's `Status` field transitions from `Proposed` to `Accepted` (section 4 below)
- [ ] `CHANGELOG.md` has an entry under `Unreleased > Feat` classified `feat(compliance):` per the manifest-change policy
- [ ] Pre-commit green on all changed files
- [ ] `/pr-review` returns 0 Critical and 0 Important findings (Suggested or Informational are acceptable)
- [ ] CodeRabbit and Copilot reviews addressed or explicitly declined with reasoning

---

## Section 4: Step-by-step execution plan

Work the checkboxes in order. Each step is a logical commit unless noted otherwise.

### Step 4.1: Set up a worktree

- [ ] Create `feat/scanner-allowlist-tiers` worktree:
      ```bash
      git fetch origin main
      git worktree add -b feat/scanner-allowlist-tiers .worktrees/feat-scanner-allowlist origin/main
      cd .worktrees/feat-scanner-allowlist
      ```
- [ ] Confirm the worktree is at the current `origin/main` head and clean

### Step 4.2: Transition ADR-008 to Accepted

- [ ] Edit `docs/architecture/adr/ADR-008-scanner-allowlist-tiers.md`:
  - Change `> **Status**: Proposed` to `> **Status**: Accepted` (body banner only)
  - Add `> **Acceptance date**: <today>` directly below the Status line
  - **Do NOT change the YAML frontmatter `status:` field.** Per the
    `scripts/validate-frontmatter.sh` enum, valid values are
    `draft | in-review | published | active | deprecated`; `proposed` and
    `accepted` are not valid frontmatter values. All existing ADRs leave the
    frontmatter as `status: draft` while the body banner tracks the lifecycle
    (Proposed/Accepted). Follow that pattern; the validator will reject any
    other frontmatter value.
- [ ] Edit `docs/architecture/adr/index.md`:
  - In the ADR-008 row, change `Proposed` to `Accepted`
- [ ] Commit: `docs(architecture): mark ADR-008 Accepted (scanner allowlist redesign)`

### Step 4.3: Create the allowlist config

- [ ] Create `docs/standards/scanner-allowlist.yaml` with the schema in section 6
- [ ] Populate with the 13 scanner entries in section 7
- [ ] Commit: `feat(compliance): add scanner-allowlist.yaml with tier classification`

### Step 4.4: Update the manifest

- [ ] Edit `docs/standards-manifest.yaml`:
  - Replace CI-007's `verify` field to reference the allowlist (see section 8.1)
  - Replace CI-007b's `verify` field to reference the allowlist (see section 8.2)
  - Update both entries' `notes:` fields to reference the implementation date
- [ ] Commit: `feat(compliance): route CI-007 and CI-007b through scanner-allowlist`

### Step 4.5: Update the agent doc

- [ ] **Baseline check (do this first):** record the current line count.
      At PR #119 authoring time (2026-05-18), `.claude/agents/devops-deployment-agent.md`
      is **169 lines**. The 400-line ceiling per `.claude/agents/CLAUDE.md` gives a
      ~230-line budget; sections 9.1 + 9.2 + 9.3 below land in roughly 60-80 lines,
      so the ceiling is comfortable. If the baseline has grown beyond 320 lines by
      the time you execute this step (re-check with `wc -l`), pre-plan the factoring
      to `.claude/standards/scanner-allowlist-dispatch.md` (see section 11 escalation
      row) before editing the agent doc.
- [ ] Edit `.claude/agents/devops-deployment-agent.md` Audit Workflow section:
  - Replace the existing `CI-007 scoped evaluation` bullet with the new `scanner_allowlist` handler (see section 9.1)
  - Update the existing `pattern_absent` bullet to reference the allowlist (see section 9.2)
- [ ] Edit the same file's Remediation Workflow section (CI-007 and CI-007b entries):
  - Reference the allowlist as the source of truth for both tier assignment and detection patterns (see section 9.3)
- [ ] Verify the file stays under the 400-line target per `.claude/agents/CLAUDE.md`; if it exceeds, factor detail into a referenced section in `.claude/standards/`
- [ ] Commit: `feat(compliance): tier-aware audit dispatch for CI-007/007b`

### Step 4.6: CHANGELOG

- [ ] Edit `CHANGELOG.md` Unreleased > Feat section with this entry (classified per `.claude/standards/manifest-changes.md`):

      ```markdown
      * feat(compliance): replace inline CI-007/007b scanner regex with a tier-classified
        allowlist at `docs/standards/scanner-allowlist.yaml`; switch audit detection to
        `uses:`-first dispatch (precise) with `run:` regex as fallback; encode tool-flag
        suppression patterns (`--exit-zero`, `--soft-fail`, `--exit-code 0`, etc.) per
        scanner so CI-007b catches them in addition to the shell `||` form; expand
        scanner coverage to `trivy`, `grype`, `checkov`, `kics`, `snyk`, `tfsec`. The
        `snyk monitor` invocation is tier=`advisory_by_intent` because it returns 0 by
        design (reporting-only). Implements ADR-008 (Accepted).
      ```
- [ ] Commit: `docs(compliance): CHANGELOG entry for scanner allowlist implementation`

### Step 4.7: Pre-commit and local verification

- [ ] Run `pre-commit run --files <each changed file>` and confirm all hooks pass
- [ ] If the frontmatter validator fails, check `docs/_data/tags.yml` for the allowed
      vocabulary; do NOT invent tags
- [ ] Manually walk one fixture workflow per pattern category (section 7 has the test plan)

### Step 4.8: PR

- [ ] Push: `git push -u origin feat/scanner-allowlist-tiers`
- [ ] Open PR titled exactly: `feat(compliance): two-tier scanner allowlist for CI-007/007b (ADR-008)`
- [ ] PR body: include sections "Summary", "Why" (cite issue #35 and ADR-008), "Changes" (file-by-file), "Test plan" (section 7), "Acceptance criteria" (copy from section 3 above with checkboxes)
- [ ] Run `/pr-review` after the PR opens; address findings

---

## Section 5: Suggested commit grouping

ADR-008 is large enough that a single squash commit hides the implementation logic.
Six commits are suggested (matching steps 4.2 through 4.6 above plus the worktree
setup). Each commit is independently revertable; CHANGELOG lands last so reviewers
see the implementation before the announcement.

| # | Type | Subject |
|---|---|---|
| 1 | `docs(architecture)` | mark ADR-008 Accepted (scanner allowlist redesign) |
| 2 | `feat(compliance)` | add scanner-allowlist.yaml with tier classification |
| 3 | `feat(compliance)` | route CI-007 and CI-007b through scanner-allowlist |
| 4 | `feat(compliance)` | tier-aware audit dispatch for CI-007/007b |
| 5 | `docs(compliance)` | CHANGELOG entry for scanner allowlist implementation |

Per `.claude/standards/manifest-changes.md`, this entire PR is a `feat:` because
it expands enforcement to a new dimension (tier-aware scanner detection). The
individual commits split by file domain, not by semantic-release type.

---

## Section 6: Schema reference for `scanner-allowlist.yaml`

The file at `docs/standards/scanner-allowlist.yaml` uses this shape. Lock these
field names exactly; the agent dispatch logic in section 9 depends on them.

```yaml
# yaml-language-server: $schema=./scanner-allowlist.schema.json  (optional; create
# the JSON Schema file in a follow-up if static validation is wanted)

schema_version: 1

# Last review of upstream scanner behavior (exit codes, suppression flags).
# Refresh quarterly; deprecated scanners may be removed during the refresh.
last_reviewed: "2026-05-18"

scanners:
  - id: <stable identifier; snake_case; matches the canonical CLI name>
    tier: must_block | advisory_by_intent
    detect:
      uses:
        # Zero or more GitHub Action ref entries that invoke this scanner.
        # Each entry is either:
        #   (a) a bare `<owner>/<repo>` string (prefix match; version pin ignored), OR
        #   (b) a mapping with explicit fields for actions whose repository hosts
        #       multiple distinct entry points under different subdirectories
        #       (e.g. snyk/actions/python vs snyk/actions/node).
        - <owner>/<repo>                        # form (a): simple prefix match
        - repo: <owner>/<repo>                  # form (b): multi-path repo
          path: <subdirectory>                  # required when this form is used
      run_pattern: |
        <PCRE pattern; anchored on \b<tool>\b followed by required subcommand
        or argument context. Empty string is allowed only when uses[] is non-empty.>
    suppression_flags:
      # Zero or more PCRE patterns that, when matched in a run: block alongside
      # the scanner invocation, indicate intentional exit-code suppression.
      # CI-007b uses this list for tier=must_block scanners only.
      - <PCRE pattern>
    suppression_env:
      # Zero or more environment variable names. When present in the step's env:
      # block (or the job's env: block) with a value matching the listed pattern,
      # the scanner's exit code is suppressed in-band. CI-007b uses this list
      # alongside suppression_flags. Example: GITLEAKS_EXIT_CODE accepts an
      # integer; setting it to 0 makes gitleaks-action always pass regardless
      # of findings.
      - name: <ENV_VAR_NAME>
        suppressing_value: <PCRE pattern>     # e.g. '^0$' for "exit-code 0"
    notes: >
      Human-readable rationale. REQUIRED for tier=advisory_by_intent (explain
      why blocking semantics do not apply). OPTIONAL but recommended for
      tier=must_block (cite the upstream exit-code behavior or known quirks).
```

**Validation rules** (enforce at PR review; later move into the agent's
allowlist-loading logic):

1. `id` is unique across the list
2. `tier` is one of the two enum values; no third value
3. For `tier: must_block`, at least one of `detect.uses` or `detect.run_pattern`
   must be non-empty
4. For `tier: advisory_by_intent`, `notes` is required and non-empty
5. `suppression_flags` may be empty `[]` for scanners with no known
   first-class suppression flag
6. `suppression_env` may be empty `[]` or omitted entirely; when present, each
   entry must have both `name` (string) and `suppressing_value` (PCRE pattern)
7. `detect.uses` entries using form (b) (the `repo:` + `path:` mapping) must
   set `path:` to a non-empty string; agent dispatch logic distinguishes
   `snyk/actions/python` from `snyk/actions/node` via this field

---

## Section 7: Pre-populated scanner entries

Copy this directly into `scanner-allowlist.yaml` (after the schema header).
Sources for each scanner's exit-code semantics are cited inline. Verify each
citation before merging if the linked docs have changed.

```yaml
scanners:

  # ============================================================
  # Tier 1: must_block (deterministic, exit-code-driven scanners)
  # ============================================================

  - id: bandit
    tier: must_block
    detect:
      uses:
        - PyCQA/bandit-action
      run_pattern: '\bbandit\b'
    suppression_flags:
      - '--exit-zero'
      - '--exit-code\s+[02]'
    notes: >
      PyPA Python AST SAST. Default behavior: exit 1 on any finding at or above
      the default severity threshold. --exit-zero forces exit 0 regardless of
      findings. PR #116's pp-security-master incident invoked bandit with a
      shell || suppressor; the regex pattern catches that, the flags list
      catches the in-tool form.

  - id: safety
    tier: must_block
    detect:
      uses:
        - pyupio/safety-action
      run_pattern: '\bsafety\s+(check|scan)\b'
    suppression_flags:
      - '--continue-on-error'
      - '--exit-code\s+0'
    notes: >
      Python dependency scanner. Note v3+ introduced `safety scan` alongside the
      legacy `safety check`; both are subject to the same blocking semantics. The
      run_pattern matches either.

  - id: osv-scanner
    tier: must_block
    detect:
      uses:
        - google/osv-scanner-action
      run_pattern: '\bosv-scanner\b'
    suppression_flags: []
    notes: >
      Google's multi-ecosystem vulnerability scanner. No first-class blocking-
      control flag in current releases; suppression is shell || only.

  - id: semgrep
    tier: must_block
    detect:
      uses:
        - semgrep/semgrep                     # current canonical Docker container action
        - semgrep/semgrep-action              # legacy; superseded but still in use
        - returntocorp/semgrep-action         # original org name; still resolves
      run_pattern: '\bsemgrep\s+(scan|ci|--config)\b'
    suppression_flags:
      - '--error\s*=?\s*0'                    # disables non-zero exit on findings
      - '--no-error-on-findings'
    notes: >
      Multi-language SAST. --error=0 explicitly disables non-zero exit on
      findings. The run_pattern requires a recognized subcommand (scan, ci) or
      --config flag to avoid false positives from incidental matches. NOTE:
      --disable-nosem disables inline `nosem` suppression comments (the
      OPPOSITE of an exit-code defeater); it is intentionally NOT on the
      suppression_flags list.

  - id: trufflehog
    tier: must_block
    detect:
      uses:
        - trufflesecurity/trufflehog          # action; supports `extra_args:` input
        - trufflesecurity/trufflehog-actions-scan
      run_pattern: '\btrufflehog\s+(git|filesystem|github|gitlab|s3|docker|gcs|circleci|jenkins|huggingface)\b'
    suppression_flags: []                     # no CLI flag suppresses exit codes
    suppression_env:
      - name: TRUFFLEHOG_SUPPRESS_FAIL        # not a real env, placeholder example
        suppressing_value: '^(1|true|yes)$'
    notes: >
      Secrets scanner. The CLI uses `--fail` to OPT IN to non-zero exit on
      findings; there is no inverse `--no-fail` flag. Action-level suppression
      is via `continue-on-error: true` (caught by CI-007), not a CLI/env
      mechanism. Verify the action's input names against the current upstream
      docs at https://github.com/trufflesecurity/trufflehog before merging;
      input field names have changed between versions.
      NOTE: `--no-verification` is a real flag but only disables credential
      verification (secrets still emit findings); it does NOT suppress exit
      codes. It is intentionally NOT on suppression_flags.

  - id: gitleaks
    tier: must_block
    detect:
      uses:
        - gitleaks/gitleaks-action
      run_pattern: '\bgitleaks\s+(detect|protect|dir)\b'
    suppression_flags:
      - '--exit-code\s+0'                     # bare-CLI form (rare)
    suppression_env:
      - name: GITLEAKS_EXIT_CODE              # action form (dominant)
        suppressing_value: '^0$'
    notes: >
      Secrets scanner. The bare CLI uses --exit-code; the gitleaks-action form
      uses the GITLEAKS_EXIT_CODE env var. Most workflows use the action form,
      so suppression_env is the more important detection vector.

  - id: pip-audit
    tier: must_block
    detect:
      uses:
        - pypa/gh-action-pip-audit            # canonical action ref (verified 2026-05-18)
      run_pattern: '\bpip-audit\b'
    suppression_flags: []
    notes: >
      PyPA dependency audit. No first-class blocking-control flag. Note: the
      manifest itself enforces `uv run pip-audit` in pre-push hooks per
      CLAUDE.md, but workflow-level invocations are still subject to CI-007b.
      CORRECTION (added during PR #119 review): the action ref is
      `pypa/gh-action-pip-audit`, NOT `pypa/pip-audit-action` (the latter
      returns 404). Verify before merging if this entry has been edited.

  - id: trivy
    tier: must_block
    detect:
      uses:
        - aquasecurity/trivy-action
      run_pattern: '\btrivy\s+(image|fs|config|repo|sbom|kubernetes|aws|vm|rootfs|iac)\b'
    suppression_flags:
      - '--exit-code\s+0'
      - '--ignore-unfixed'
    notes: >
      Aqua Security multi-purpose scanner (containers, IaC, SBOM, k8s, cloud).
      Default behavior is exit 0 even with findings unless --exit-code 1 is
      passed; this is a positive-flag requirement that CI-007b does NOT enforce
      (out of scope per ADR-008). The suppression_flags list catches workflows
      that explicitly set --exit-code 0 to defeat an otherwise-blocking
      invocation. Track positive enforcement as CI-007c if needed later.

  - id: grype
    tier: must_block
    detect:
      uses:
        - anchore/scan-action
      run_pattern: '\bgrype\b'
    suppression_flags:
      - '--fail-on\s+none'
    notes: >
      Anchore container vulnerability scanner. Default --fail-on threshold is
      "medium"; setting --fail-on none disables blocking.

  - id: checkov
    tier: must_block
    detect:
      uses:
        - bridgecrewio/checkov-action
      run_pattern: '\bcheckov\b'
    suppression_flags:
      - '--soft-fail'
      - '--soft-fail-on\s+\S+'
    notes: >
      Bridgecrew/Palo Alto IaC misconfiguration scanner. --soft-fail disables
      exit-code blocking entirely; --soft-fail-on disables it for matching
      check IDs. Both are first-class flags that defeat CI-007b's intent and
      must be flagged.

  - id: kics
    tier: must_block
    detect:
      uses:
        - checkmarx/kics-github-action
      run_pattern: '\bkics\b'
    suppression_flags:
      - '--ignore-on-exit\s+(all|results)'
      - '--fail-on\s+\(\s*\)'
    notes: >
      Checkmarx IaC scanner. --ignore-on-exit all disables non-zero exit;
      empty --fail-on category list has the same effect.

  - id: tfsec
    tier: must_block
    detect:
      uses:
        - aquasecurity/tfsec-action
      run_pattern: '\btfsec\b'
    suppression_flags:
      - '--soft-fail'
    notes: >
      Terraform-specific scanner. Aqua Security folded it into trivy iac;
      retained here for backwards compat with repos that haven't migrated.
      During the quarterly review, consider removing once no consumer repos
      reference it.

  - id: snyk-test
    tier: must_block
    detect:
      uses:
        # snyk/actions is a single repo with one subdirectory per ecosystem.
        # Use form (b) so the agent can distinguish snyk-test from snyk-monitor
        # when both share the same `<owner>/<repo>` prefix.
        - repo: snyk/actions
          path: python
        - repo: snyk/actions
          path: node
        - repo: snyk/actions
          path: golang
        - repo: snyk/actions
          path: maven
        - repo: snyk/actions
          path: gradle-jdk11
        - repo: snyk/actions
          path: dotnet
      run_pattern: '\bsnyk\s+test\b'
    suppression_flags:
      - '--severity-threshold\s+(none|unknown)'
    notes: >
      Commercial SCA/SAST. `snyk test` returns non-zero on findings at or
      above the configured severity threshold (default low). Setting the
      threshold to `none` or `unknown` produces an always-pass invocation.
      Separate from `snyk monitor` (see advisory_by_intent below). The
      action form uses the same repo (`snyk/actions`) as snyk-monitor;
      disambiguation is by step.with.command (`test` vs `monitor`). When
      dispatch cannot read the `with:` block (e.g., step uses an input
      variable for `command`), fall back to `run_pattern` matching.

  # ===================================================================
  # Tier 2: advisory_by_intent (reporting-only scanners by design)
  # ===================================================================

  - id: snyk-monitor
    tier: advisory_by_intent
    detect:
      uses:
        # Same repo and paths as snyk-test; disambiguated by `with.command:
        # monitor` in the workflow step. When the command field cannot be
        # statically resolved, the run_pattern is authoritative.
        - repo: snyk/actions
          path: python
        - repo: snyk/actions
          path: node
        - repo: snyk/actions
          path: golang
        - repo: snyk/actions
          path: maven
      run_pattern: '\bsnyk\s+monitor\b'
    suppression_flags: []
    notes: >
      `snyk monitor` always returns 0 by design. It submits a snapshot of the
      project to Snyk's web UI for organizational tracking and does not gate
      CI. CI-007b does NOT apply to this invocation. If a workflow runs both
      `snyk test` and `snyk monitor` in the same step, only the `test`
      invocation is subject to CI-007b. The agent dispatch logic in section
      9.1 must read `with.command:` to assign the correct id; absent that
      field, the step is treated as snyk-test (the safer default).
```

**Why these specific scanners and not others:**

- Decided by the canonical security tooling used across the org's repos as of
  2026-05-18. Niche scanners (`dependency-check` for Java-heavy projects,
  `kubescape` for K8s-only repos) are deferred until a consumer repo uses them.
- `codeql` is intentionally excluded: it runs via the official GitHub
  `codeql-action` which manages exit codes itself; the workflow-level shell
  suppression pattern doesn't apply.
- `syft` is excluded as an SBOM generator (not a finding scanner; exit
  semantics aren't about vulnerabilities).

---

## Section 8: Replacement verify field text for the manifest

### Section 8.1: CI-007 `verify` field replacement

In `docs/standards-manifest.yaml`, replace the existing CI-007 `verify` block
with:

```yaml
    verify: |
      content_absent: .github/workflows/*.yml, continue-on-error: true within jobs whose name or id matches ANY of:
        (a) a scanner id from docs/standards/scanner-allowlist.yaml (tier: must_block), OR
        (b) the legacy keyword set (security|scan|bandit|safety|audit|sast|dast|trufflehog|gitleaks|semgrep)
            (preserved from the pre-ADR-008 manifest so generic security-named jobs without a
            recognized scanner ref are still caught; removes the coverage regression observed
            during PR #119 review).
      Also flag continue-on-error: true on a per-step entry whose step uses: matches an allowlist detect.uses entry, or whose run: matches an allowlist detect.run_pattern (covers scanner steps inside non-security-named jobs).
      Allow per-step continue-on-error on a non-scanner step inside an otherwise security-named job (e.g., codecov upload, optional artifact publish).
      Tier source: docs/standards/scanner-allowlist.yaml (must_block entries only).
```

The legacy keyword fallback (clause (b)) is intentional. Removing it during
PR #119 review revealed that jobs named `sast-scan` or `dast` with no
recognized scanner `uses:`/`run:` would silently lose coverage. Keeping (b)
preserves the ADR-008 Consequences > Neutral claim that "no existing check
loses coverage."

Also update the `notes:` field:

```yaml
    notes: >
      Original scope (security-analysis.yml only) missed a real XXE vulnerability in
      pp-security-master where the bandit job lived in ci.yml with continue-on-error: true.
      Broadened to all workflows 2026-05-17 (issue #35). Tier-aware dispatch via
      docs/standards/scanner-allowlist.yaml landed <implementation-date> per ADR-008.
```

### Section 8.2: CI-007b `verify` field replacement

Replace the existing CI-007b `verify` block with:

```yaml
    verify: |
      pattern_absent: .github/workflows/*.yml
      For each scanner in docs/standards/scanner-allowlist.yaml where tier == must_block:
        Match the invocation via detect.uses (preferred; precise) OR detect.run_pattern (fallback).
        Then flag the step if any of these forbidden suffix patterns appear in the same run: block:
          - Shell suppressors:  \|\|\s*(echo|true|:|exit\s+0)
          - Tool-flag suppressors: each scanner's suppression_flags entries (PCRE)
      Evaluate with `rg` (ripgrep) or `grep -P` (PCRE). Standard grep does not support \s and \b reliably.
      Tier source: docs/standards/scanner-allowlist.yaml (must_block entries only; advisory_by_intent entries are exempt by design).
```

Also update the `notes:` field:

```yaml
    notes: >
      Companion to CI-007. Real incident: the same pp-security-master XXE escape used
      `bandit -r src/ || echo "bandit advisory"` to convert a finding into a no-op
      success. Added 2026-05-17 (issue #35). Tier-aware dispatch and tool-flag
      detection landed <implementation-date> per ADR-008.
```

---

## Section 9: Agent doc updates

### Section 9.1: New Audit Workflow bullet for `scanner_allowlist`

In `.claude/agents/devops-deployment-agent.md`, replace the existing
`CI-007 scoped evaluation` bullet (added in PR #116) with this `scanner_allowlist`
handler. The new bullet supersedes the old one.

```markdown
- `scanner_allowlist` handler (CI-007 and CI-007b): load `docs/standards/scanner-allowlist.yaml`. For each workflow file in `.github/workflows/*.yml`:
  1. Walk `jobs.*.steps[*]` structurally (parse as YAML, not regex).
  2. For each step, classify it as a scanner invocation if:
     - The step's `uses:` matches any allowlist entry's `detect.uses` ref. Matching rule:
       (a) For bare-string entries: prefix match on `<owner>/<repo>`, ignoring version pin.
       (b) For `repo:`/`path:` mapping entries: the step's `uses:` must START with `{repo}/{path}` (e.g., `snyk/actions/python@v3` matches an entry with `repo: snyk/actions`, `path: python`); a bare `repo:` match without `path:` is NOT sufficient.
     - When multiple allowlist entries share the same `repo` but differ by `path`, disambiguate by reading `step.with.command` (snyk-test vs snyk-monitor). When `with.command` cannot be statically resolved (e.g., it references `${{ inputs.command }}`), assign the safer default (the `must_block` entry).
     - OR the step's `run:` content matches any allowlist entry's `detect.run_pattern` (evaluate with `rg -P` or equivalent).
     Annotate the scanner's `id` and `tier` on each marked step.
  3. CI-007 check: for each job containing at least one marked step at `tier: must_block`, flag any of:
     - Job-level `continue-on-error: true`
     - Step-level `continue-on-error: true` on the marked step itself
     ALSO flag job-level `continue-on-error: true` on any job whose `name:` or `id:` matches the legacy keyword set `(security|scan|bandit|safety|audit|sast|dast|trufflehog|gitleaks|semgrep)`, even if no allowlist match landed (preserves pre-ADR-008 coverage for generic security-named jobs).
     Per-step `continue-on-error: true` on a NON-marked step inside the same job is allowed.
  4. CI-007b check: for each marked step at `tier: must_block`, scan the step's `run:` body with `rg -P` for:
     - Shell suppressors: `\|\|\s*(echo|true|:|exit\s+0)`
     - Tool-flag suppressors: each `suppression_flags` PCRE for the matched scanner
     Then scan the step's `env:` block (and the enclosing job's `env:` block) for each `suppression_env` entry: if a matching var name is present with a value matching `suppressing_value`, flag the step.
     Flag any match. Steps marked at `tier: advisory_by_intent` are exempt from CI-007b.
  5. Emit FINDING blocks with file path, line number, scanner `id`, matched pattern (or env var name), and tier.
  If `docs/standards/scanner-allowlist.yaml` is missing or malformed, emit a FINDING and abort the CI-007/007b checks (do NOT silently pass with an empty allowlist).
```

### Section 9.2: Update existing `pattern_absent` bullet

The existing `pattern_absent` bullet (added in PR #116) becomes the general-purpose
handler for any `pattern_absent` check, not just CI-007b. Update its text to:

```markdown
- `pattern_absent` checks (general): for any check whose verify directive begins with `pattern_absent:`, follow the embedded pattern instructions in the verify field. Evaluate with `rg -P` (PCRE) or `grep -P`; standard `grep` BRE/ERE does not support `\s` and `\b` is variant-dependent. CI-007b's specific dispatch is handled by the `scanner_allowlist` handler above; this bullet remains as the fallback for future `pattern_absent` checks that do not need tier-aware logic.
```

### Section 9.3: Remediation Workflow updates

Replace the existing CI-007 and CI-007b remediation bullets with:

```markdown
**CI-007 (blocking security scan, job manifest):** For each FINDING from the `scanner_allowlist` handler tagged with the CI-007 check, remove the offending `continue-on-error: true` line via Edit. The allowlist's `tier: must_block` classification is authoritative on whether the step is a scanner invocation. Do not relax `continue-on-error: true` on non-scanner steps inside an otherwise security-named job (e.g., codecov upload).

**CI-007b (blocking security scan, command suppression):** For each FINDING from the `scanner_allowlist` handler tagged with the CI-007b check, remove the matched shell suppressor (`|| echo "..."`, `|| true`, etc.) or the matched tool-flag suppressor (`--exit-zero`, `--soft-fail`, `--exit-code 0`, etc.) per the scanner's `suppression_flags` list in `docs/standards/scanner-allowlist.yaml`. If the original intent was to capture advisory output for a comment, replace the suppressor with a follow-up step gated on `if: failure()`, not a same-line `||` or in-tool flag.
```

---

## Section 10: Verification (test plan)

No agent-eval harness exists. Manual verification against fixture workflow
files is the gate.

### Test 10.1: Regression on pp-security-master pattern

- [ ] Create a fixture workflow file with this content under `/tmp/test-fixtures/`:
      ```yaml
      jobs:
        ci:
          steps:
            - run: bandit -r src/ || echo "advisory"
      ```
- [ ] Run the audit agent against the fixture (use the `repo-compliance` skill or
      invoke the agent directly with the fixture as the target)
- [ ] Verify CI-007b FINDING is emitted with `scanner_id: bandit`,
      `matched_pattern: \|\|\s*echo`, and the line number of the `run:` block
- [ ] Verify CI-007 does NOT fire (no `continue-on-error: true` in the fixture)

### Test 10.2: Tier 2 advisory case (must NOT fire CI-007b)

- [ ] Fixture:
      ```yaml
      jobs:
        report:
          steps:
            - run: snyk monitor --project-name=foo
      ```
- [ ] Verify CI-007b does NOT fire (snyk-monitor is tier=`advisory_by_intent`)
- [ ] Verify CI-007 does NOT fire

### Test 10.3: Tool-flag suppression detection

- [ ] Fixture:
      ```yaml
      jobs:
        scan:
          steps:
            - run: checkov --directory infra/ --soft-fail
      ```
- [ ] Verify CI-007b FINDING fires with `scanner_id: checkov`,
      `matched_pattern: --soft-fail`

### Test 10.4: uses-first detection (no run: needed)

- [ ] Fixture (replace `<PIN-SHA-HERE>` with a real 40-character commit SHA from
      `aquasecurity/trivy-action` before saving; the literal `<PIN-SHA-HERE>` is a
      placeholder and will fail YAML parsing if left in place):
      ```yaml
      jobs:
        scan:
          continue-on-error: true
          steps:
            - uses: aquasecurity/trivy-action@<PIN-SHA-HERE>
              with:
                scan-type: fs
      ```
- [ ] Verify CI-007 FINDING fires (job-level `continue-on-error: true` AND the step
      uses an allowlist `detect.uses` ref)

### Test 10.5: False-positive guard (incidental text match)

- [ ] Fixture:
      ```yaml
      jobs:
        prep:
          steps:
            - run: echo "Installing trivy now..."
      ```
- [ ] Verify CI-007 does NOT fire (the step's `uses:` doesn't match, and the
      `run_pattern` for trivy is `\btrivy\s+(image|fs|...)\b` which requires a
      subcommand, NOT just the substring `trivy`)

### Test 10.6: Missing allowlist file (graceful failure)

- [ ] Temporarily rename `docs/standards/scanner-allowlist.yaml` to
      `scanner-allowlist.yaml.bak`
- [ ] Run the audit agent
- [ ] Verify a FINDING is emitted reporting the missing file, AND that
      CI-007/007b are NOT silently passing
- [ ] Restore the file

If any of 10.1 through 10.6 fails, the implementation is incomplete. Do NOT
merge.

---

## Section 11: Decision authority and escalation

| Situation | Who to ask |
|---|---|
| Disagreement on tier classification for a scanner | Byron Williams (`@williaby`) |
| A scanner not in the allowlist appears in a real workflow | First check the rejection list in ADR-008 ("Why these specific scanners"); if not addressed, propose addition in the PR description |
| Test 10.x fails despite implementing per the plan | Re-read the relevant section. If the failure is in the agent dispatch, check `.claude/agents/devops-deployment-agent.md` line-by-line against section 9.1 |
| The pre-commit `validate-front-matter` hook blocks the commit | The tag vocabulary in `docs/_data/tags.yml` is the controlled list. Pick existing tags or add new ones to that file (requires its own justification) |
| The 400-line agent doc ceiling is exceeded | Factor the longer narrative into `.claude/standards/scanner-allowlist-dispatch.md` and reference from the agent doc (see `.claude/agents/CLAUDE.md` for the pattern) |
| Anything else | Open a GitHub issue with the `compliance` label, link to this handoff doc, and ask before pressing forward |

---

## Section 12: Known pitfalls

These have bitten previous compliance/manifest PRs; expect them to bite again here.

1. **The frontmatter validator runs on ALL markdown files in `docs/`, not just
   changed files.** A pre-existing bad frontmatter in an unrelated file blocks
   your commit. Diagnose with `pre-commit run validate-front-matter --all-files`.
   Run this BEFORE making your changes so you know the baseline state.

2. **Pre-commit output is hundreds of lines.** A failing hook appears partway
   through. If your commit fails, redirect to a file and grep:
   ```bash
   git commit -m "..." > /tmp/commit.log 2>&1; grep -E "Failed|FAILED|ISSUES" /tmp/commit.log
   ```

3. **`pip-audit` has a hyphen in the name.** PCRE `\b` anchors work correctly
   because `t` is a word char and the trailing space/EOL is non-word; verify
   with a manual test against a fixture line `pip-audit --strict`.

4. **`snyk` is a common-word substring** (e.g., `snyk` could appear in
   environment variable names like `SNYK_TOKEN`). The `run_pattern` for snyk-test
   anchors on `\bsnyk\s+test\b` (subcommand required) to avoid this.

5. **`trivy` defaults to exit 0 without `--exit-code 1`.** This is a
   positive-flag requirement, NOT a suppression check. CI-007b only catches
   negative patterns (presence of `--exit-code 0`, presence of `||`, etc.).
   The positive enforcement is intentionally out of scope per ADR-008.

6. **`tfsec` is deprecated.** Aqua Security folded it into `trivy iac`. Keep it
   in the allowlist for backwards compat but plan to remove it during the next
   quarterly review.

7. **Branch-from-`origin/main`, not local `main`.** The repo conventions in
   `.claude/rules/git-workflow.md` require feature branches; local main may be
   stale or have unmerged commits. Always `git worktree add -b ... origin/main`.

8. **Sign every commit.** `commit.gpgsign` is `true` in the repo config; an
   unsigned commit will be rejected at push time by branch protection on the
   target repo.

9. **`.claude/standards/manifest-changes.md` requires `feat(compliance):` for
   this PR.** Not `fix:`. Not `docs:`. Don't second-guess; the policy directly
   addresses this case (expanding enforcement to a new dimension).

---

## Section 13: Definition of done

- [ ] All Section 3 acceptance criteria satisfied
- [ ] All Section 10 tests pass against fixture workflow files
- [ ] PR review pipeline (`/pr-review`) returns 0 Critical, 0 Important
- [ ] Reviewer (decision authority per section 11) approves
- [ ] PR merged to `main` with a merge commit referencing ADR-008
- [ ] ADR-008 status in `index.md` reflects Accepted
- [ ] Quarterly-review reminder filed as a separate GitHub issue (suggested
      cadence: every March/June/September/December; remove deprecated scanners
      like `tfsec` when consumer repos have migrated)

---

## Appendix A: Estimated effort

Based on the per-section scope:

- Section 4.2 (ADR transition): 10 minutes
- Section 4.3 (allowlist creation, with population from section 7): 30-60 minutes
  (budget +30 minutes for re-verifying each scanner's action ref and CLI flags
  against current upstream docs before committing; the original PR #119 entries
  had 2 incorrect refs caught only at review time)
- Section 4.4 (manifest updates): 20 minutes
- Section 4.5 (agent doc updates): 60 minutes (45 for the edit; +15 for the
  `with.command:` disambiguation logic for snyk and the env-block scan for
  gitleaks-style suppression)
- Section 4.6 (CHANGELOG): 10 minutes
- Section 4.7 (pre-commit, manual testing): 60 minutes
- Section 4.8 (PR creation and review): 60 minutes
- Section 10.6 (missing-file abort path): 20 minutes (new abort-with-FINDING
  behavior in the agent; not just config)
- PR review iterations (Copilot, CodeRabbit, `/pr-review`): 60-90 minutes

**Total: 6-8 hours of focused work, plus review cycles.** This assumes the
new team has worked in this repo's conventions before. Add 2-3 hours for
onboarding if they have not. The earlier 4-5 hour estimate (PR #119 v1)
proved optimistic once the scanner-ref verification overhead and the new
agent dispatch surfaces (`with.command:` disambiguation, env-block scanning,
missing-file abort) were added; this revised estimate reflects the realistic
budget.

---

## Appendix B: Files this PR will touch

| File | Action | Lines (approx) |
|---|---|---|
| `docs/architecture/adr/ADR-008-scanner-allowlist-tiers.md` | Status -> Accepted | 2-3 lines |
| `docs/architecture/adr/index.md` | Update ADR-008 row | 1 line |
| `docs/standards/scanner-allowlist.yaml` | NEW | ~200 lines |
| `docs/standards-manifest.yaml` | Edit CI-007 and CI-007b verify + notes | ~30 lines |
| `.claude/agents/devops-deployment-agent.md` | Audit + Remediation workflow updates | ~40 lines |
| `CHANGELOG.md` | New Unreleased > Feat entry | ~12 lines |

Total PR size estimate: ~285 lines. Comfortably within the p50 PR size budget
documented in `.claude/rules/git-workflow.md` (118 lines is p50, 498 is p90).
