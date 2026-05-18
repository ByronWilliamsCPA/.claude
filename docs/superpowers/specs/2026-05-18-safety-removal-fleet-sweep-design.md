---
schema_type: common
title: Safety Scanner Removal Fleet Sweep Design
status: draft
owner: engineering
tags: [security, ci_cd, github_actions, compliance, standards]
purpose: Design for removing the redundant safety SCA scanner from the org workflow, two cookiecutter templates, and five live consumer repos in BWCPA and williaby, replacing nothing because OSV-Scanner, pip-audit, Dependency-Review, and Renovate already cover Python dep vulnerability scanning.
---

**Date**: 2026-05-18
**Status**: Draft
**Author**: Byron Williams
**Related**: `ByronWilliamsCPA/.github` PRs #136, #137, #138; `security-analysis-workflow-regression-report.md`

---

## Problem statement

`safety` (the Python SCA tool) has caused four cascading CI regressions across the
fleet in the past four days. Three are fixed via `ByronWilliamsCPA/.github`
PRs #136, #137, #138. One ("Layer 8d", the `--no-build` hardcode introduced by
the merged form of PR #138) is currently blocking every editable-install
consumer's `Security Analysis / Security Gate Validation` required check.

Beyond Layer 8d, multiple consumer repos maintain local copies of the
`security-analysis.yml` workflow with safety 2.x syntax (`safety check`,
exit-code suppression patterns like `|| true`). Two cookiecutter templates
bootstrap new repos with the same safety 2.x patterns, perpetuating the
regression surface.

## Decision

**Remove `safety` from the org workflow and the fleet entirely.** Replace
nothing. Python dependency vulnerability scanning is fully covered by the
existing scanner stack.

### Why removal, not migration

| Concern | Tools that cover it (without safety) | Gap |
|---|---|---|
| Python dep CVE scan (full lockfile) | OSV-Scanner, pip-audit | None |
| Python dep CVE scan (PR diff) | Dependency-Review action | None |
| Multi-ecosystem CVE scan | OSV-Scanner | None |
| Ongoing vuln alerts | Renovate `osvVulnerabilityAlerts`, Renovate `vulnerabilityAlerts` (GHSA), Dependabot alerts | None |
| Vuln auto-remediation | Renovate `transitiveRemediation`, auto-merge minor/patch | None |
| Third-party license check (PR diff) | Dependency-Review `license-check: true`, `deny-licenses: GPL-2.0, GPL-3.0` | None |
| Third-party license audit (full lockfile) | None | Gap; not closed by safety free tier either |
| Own-source SPDX/license headers | REUSE workflow | None |
| SAST | Bandit, CodeQL, SonarCloud | None |
| SBOM generation | `sbom.yml` workflow | None |
| Dependency provenance | Renovate `pinDigests` | None |

Safety's free tier provides only Python CVE scanning (a subset of OSV-Scanner's
data sources). License scanning is a paid-tier feature and is not invoked by
the workflow. No feature the workflow actually uses is lost by removal.

### Standards alignment

- `CHECK-PYTOOL-005`: "safety absent from dependencies (replaced by pip-audit)"
  already declared the directional intent. Removal extends it to workflows.
- `CHECK-CI-007`: forbids exit-code suppression. Multiple consumer repos
  use `safety check || true`. Deletion eliminates the suppression
  in the same diff.
- Org SHA-pinning posture (Renovate `pinDigests`): floating safety from PyPI
  (Option A in the regression report) conflicts with this; removal does not.
- `OSSF Scorecard` Pinned-Dependencies: neutral or improved.

## Scope

### Step 0: `ByronWilliamsCPA/.github` (urgent, unblocks consumers)

One PR, two files in the same repo:

1. `.github/workflows/python-security-analysis.yml` (live workflow)
2. `workflow-templates/python-security-analysis.yml` (template mirror used by
   GitHub's "Suggested workflows" UI)

Edits in each file:

- Remove the `run-safety` input under `on.workflow_call.inputs`
- Update the `python-security` job's `if` to gate on Bandit only
- Rename the job from "Python Security Scan" to "Python SAST (Bandit)"
- Delete the entire `Safety Vulnerability Scan` step
- Drop `safety-report.json` from the artifact upload `path` list
- Update the workflow header comment to remove "Safety"
- Add a CHANGELOG entry documenting the removal and rationale

### Tier 2: Cookiecutter templates (prevent regression source)

| Repo | File(s) |
|---|---|
| `ByronWilliamsCPA/cookiecutter-python-template` | `{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml`, `docs/org-workflows/python-ci.yml` |
| `ByronWilliamsCPA/cookiecutter-template-sample` | `.github/workflows/ci.yml` |

Action: delete safety step and any associated exit-code suppression.

### Tier 3: Live consumers with local workflow copies

| Repo | File(s) | Notes |
|---|---|---|
| `ByronWilliamsCPA/xero-crypto` | `.github/workflows/ci.yml`, `.github/workflows/security-analysis.yml` | 3 safety calls total |
| `williaby/image-preprocessing-detector` | `.github/workflows/security-analysis.yml` | 2 calls, uv-based |
| `williaby/data_ingestor` | `.github/workflows/security-analysis.yml` | 2 calls, poetry-based |
| `williaby/PromptCraft` | `.github/workflows/ci.yml` | Suppressed call |
| `williaby/testing` | `.github/workflows/test.yml` | `|| true` suppressed |

Action: delete safety step and exit-code suppression.

### Tier 4: Documentation backups (optional, low priority)

`williaby/PromptCraft/docs/planning/backups/ci-workflows/{ci-optimized,ci-original}.yml`.

Action: delete safety lines. Can ride along with the PromptCraft Tier 3 PR.

### Manifest update (separate PR in `.claude` repo)

Add `CHECK-CI-NN` (next available CI-* number) to `docs/standards-manifest.yaml`:

```yaml
CHECK-CI-NN:
  id: CHECK-CI-NN
  domain: ci
  severity: error
  description: "safety command absent from workflow YAML"
  verify: |
    content_absent_any: .github/workflows/*.yml, safety check, safety scan, safety --
  rationale: |
    Safety's free-tier vulnerability data is a subset of OSV-Scanner's. The
    license-scanning feature requires Safety paid tier and is not invoked. The
    safety 3.x CLI churned breaking changes that caused cascading regressions
    in 2026-05 (PRs #136/#137/#138 in ByronWilliamsCPA/.github). Coverage is
    fully maintained by OSV-Scanner, pip-audit, Dependency-Review, and Renovate.
  fix: "Delete the safety step from the workflow YAML; verify OSV-Scanner is present in the same workflow or a sibling workflow."
```

Also remove the now-stale `CLAUDE.md, safety check` content check at
`docs/standards-manifest.yaml:1028-1029` since the broader CI rule supersedes
it.

## Sequencing

```text
Step 0 (urgent)
  ├─ ByronWilliamsCPA/.github PR, merge first
  └─ Verify against fragrance-rater PR #22 and llc-manager main run
       ↓
Tier 2 (templates)
  ├─ cookiecutter-python-template PR
  └─ cookiecutter-template-sample PR
       ↓
Tier 3 (live consumers, parallel batches of 3)
  ├─ xero-crypto PR
  ├─ image-preprocessing-detector PR
  ├─ data_ingestor PR
  ├─ PromptCraft PR (folds Tier 4 backup cleanup)
  └─ testing PR
       ↓
Manifest update PR in .claude repo
```

## Diff templates

### Step 0 diff (applies to both `.github` files)

```diff
-      run-safety:
-        description: 'Run Safety vulnerability scan'
-        type: boolean
-        required: false
-        default: true
```

```diff
-    if: ${{ inputs.run-bandit || inputs.run-safety }}
+    if: ${{ inputs.run-bandit }}
```

```diff
-    name: Python Security Scan
+    name: Python SAST (Bandit)
```

```diff
-      - name: Safety Vulnerability Scan
-        if: ${{ inputs.run-safety }}
-        run: |
-          echo "Scanning dependencies for vulnerabilities..."
-          uv run --frozen --no-build safety scan \
-            --save-as json safety-report.json
```

```diff
-          path: |
-            bandit-report.json
-            safety-report.json
+          path: bandit-report.json
```

```diff
-# Comprehensive security scanning with CodeQL, Bandit, Safety, OSV-Scanner, and OWASP
+# Comprehensive security scanning with CodeQL, Bandit, OSV-Scanner, and Dependency-Review
```

### Tier 2-3 per-repo diff template

```diff
-      - name: Safety Vulnerability Scan
-        run: |
-          uv export --format requirements-txt --no-hashes --output-file requirements-scan.txt
-          uv run safety check --file requirements-scan.txt --json > safety-report.json || true
```

Variants seen in the inventory:

- `poetry run safety check` (data_ingestor, PromptCraft, xero-crypto): same deletion pattern
- `safety check || echo "..."` (PromptCraft, xero-crypto): delete step entirely
- `safety check || true` (testing): delete step entirely
- `safety check --output json ...` (cookiecutter-python-template): delete step entirely

Where deletion leaves an empty job or unused upload step, simplify the
surrounding YAML in the same diff. Search each repo for `.safety-policy.yml`
and delete if present (verify with `git grep` that nothing else references it).

### Commit message template

```text
chore(security): remove redundant safety scanner

Removes the `safety` SCA call. Python dependency vulnerability scanning
is fully covered by:
  - OSV-Scanner (multi-ecosystem, PyPA + GHSA + OSS-Fuzz data)
  - Dependency-Review action (PR-time, GHSA-backed)
  - pip-audit (dev dependency, PyPA-backed)
  - Renovate osvVulnerabilityAlerts + vulnerabilityAlerts (ongoing)

Aligns with manifest CHECK-PYTOOL-005 (safety absent from dependencies).
Resolves the safety 3.x CLI drift surface that caused regressions in
ByronWilliamsCPA/.github PRs #136, #137, #138.
```

## PR strategy

- Branch name (all PRs): `chore/remove-safety-scanner`
- Worktree pattern: `.worktrees/chore-remove-safety-scanner` inside each cloned repo
- One PR per repo (multi-file PRs allowed within a repo)
- Step 0: no auto-merge; needs human review and downstream verification
- Tier 2-4: enable auto-merge via `gh pr merge --auto --squash` (never `--admin`, never `--no-verify`) after CI green
- Parallel cap: open Tier 3 PRs in batches of 3 to respect Renovate `prConcurrentLimit: 5`
- Each commit signed; each PR runs `pre-commit run --all-files` before commit per CLAUDE.md global rule

## Verification

| Tier | Pre-merge checks | Post-merge verification |
|---|---|---|
| 0 | `.github` self-test green; manually trigger fragrance-rater PR #22 re-run and confirm Security Gate flips to SUCCESS; re-run on llc-manager latest main | Watch next 5 consumer-repo workflow runs across BWCPA |
| 2 | Cookiecutter renders cleanly with `cookiecutter . --no-input`; rendered repo's CI passes (act or remote test); sample repo CI green | Generate throwaway repo from template post-merge, push, confirm green |
| 3 | Each repo's CI green; confirm no remaining `safety` refs in `.github/workflows/` via `git grep -in safety .github/workflows/` (markdown, CHANGELOG, and historical doc references are acceptable) | None beyond CI green |
| 4 | None beyond CI green | None (backup files) |

## Risks and rollback

| Risk | Likelihood | Mitigation |
|---|---|---|
| Step 0 breaks a consumer that depends on `safety-report.json` artifact downstream | Low | Pre-PR grep both orgs for `safety-report.json` references; if any, include in same PR |
| Auditor or compliance dashboard explicitly named "safety" | Unknown | Audit any SOC2-style docs in the org; user confirmation given that no such dependency exists |
| Removing safety exposes a CVE that OSV missed | Very low (OSV ⊇ safety free-tier data) | One-shot diff: run safety scan + OSV-scan against fragrance-rater before Step 0; compare findings; defer if a real gap surfaces |
| Renovate opens auto-PRs against safety while sweep is in progress | Possible | Add `"safety"` to Renovate `packageRules` ignore list in Step 0 PR (separate commit), or accept noise (Tier 3 PRs will close them) |
| williaby ruleset blocks deletion (required-check expectation) | Unknown | Step 0 doesn't affect williaby; verify each williaby PR's required-check list before merge |
| Pre-commit gates trip on new comments | Standard | `pre-commit run --all-files` per CLAUDE.md global rule before each commit |
| Future safety upgrade reintroduces the tool unnoticed | Medium | New manifest rule `CHECK-CI-NN` catches it on the next `/repo-audit` sweep |

**Rollback strategy**:

- Step 0: revert PR. Consumer-repo Security Gate returns to FAILURE (current state).
- Tier 2-3: revert the individual PR. The affected workflow returns to running broken `safety check` (no worse than current).
- Manifest rule: revert. No downstream effect.

## Future work (deferred from this design)

1. **`williaby/.github` centralization**. williaby has no org-level reusable
   security workflow. Four williaby repos
   (`image-preprocessing-detector`, `data_ingestor`, `PromptCraft`, `testing`)
   maintain local copies of `security-analysis.yml`. After this sweep
   eliminates safety, the local copies become smaller and more amenable to
   consolidation into a single reusable workflow at `williaby/.github`.
   Respect the WF-X applicability-gate memory note: cross-org workflow
   deployments must enforce the same gate in every org.
2. **Downstream-consumer smoke test for `python-security-analysis.yml`**. The
   regression report's process observation #1 stands regardless of Option G.
   Add a matrix-driven smoke test that calls the reusable workflow against a
   real Python project (e.g., `fragrance-rater` or a dedicated fixture repo)
   to catch future regressions before merge.
3. **Bandit removal analysis**. CodeQL + SonarCloud both perform SAST.
   Bandit's incremental value is Python-specific rules CodeQL may miss;
   non-trivial. Worth a parallel analysis to see if a second removal is
   justified or if Bandit fills a real gap.

## Acceptance criteria

- Step 0 PR merged in `ByronWilliamsCPA/.github`. `fragrance-rater` PR #22's
  `Security Analysis / Security Gate Validation` check passes.
- All Tier 2 PRs merged. Generating a new repo from
  `cookiecutter-python-template` produces no `safety` references in workflow
  files.
- All Tier 3 PRs merged. `git grep -in safety` across the affected repos
  returns no matches in `.github/workflows/`.
- Tier 4 cleanup complete (PromptCraft backups updated or accepted as historical).
- Manifest update merged in `.claude` repo. `CHECK-CI-NN` runs on the next
  `/repo-audit` and reports zero violations.
- All previously-failing editable-install consumer CIs are green.

## Out of scope

- Migrating other safety installations not surfaced by the initial `gh search
  code` sweep. The implementation plan must include a per-repo `git grep -in
  safety` against each cloned repo to catch references in non-workflow YAML
  (pre-commit configs, scripts), in `pyproject.toml` extras, or in docs that
  also reference command-line invocations. Any new finding is folded into
  the same-repo PR.
- Replacing OSV-Scanner, Bandit, or CodeQL with alternatives.
- Adding full-lockfile third-party license auditing (a real gap, but
  independent of this work).
- Re-evaluating the choice of OSV-Scanner versus alternatives (e.g.,
  Trivy, Snyk); current OSV-Scanner coverage is sufficient.
