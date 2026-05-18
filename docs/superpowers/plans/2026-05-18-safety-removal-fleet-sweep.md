---
schema_type: common
title: Safety Scanner Removal Fleet Sweep Implementation Plan
status: draft
owner: engineering
tags: [security, ci_cd, github_actions, compliance, standards]
purpose: Step-by-step plan to remove the redundant safety SCA scanner from the org workflow, two cookiecutter templates, and five live consumer repos, then register a manifest rule to prevent reintroduction.
---

**Date**: 2026-05-18
**Status**: Draft
**Author**: Byron Williams
**Spec**: [2026-05-18-safety-removal-fleet-sweep-design.md](../specs/2026-05-18-safety-removal-fleet-sweep-design.md)

---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `safety` from every workflow YAML across BWCPA and williaby, and add a manifest rule to prevent reintroduction.

**Architecture:** Sequential per-repo PRs. Step 0 (the org workflow in `ByronWilliamsCPA/.github`) lands first and unblocks every editable-install consumer; then two cookiecutter templates land in parallel to stop the regression at the source; then five live-consumer PRs land in parallel batches of three; finally the `.claude` manifest rule lands.

**Tech Stack:** GitHub CLI (`gh`), git, pre-commit, ruff, yamllint, cookiecutter, uv, poetry. All commits signed; no `--no-verify`, no `--admin`.

---

## File Structure

The plan modifies files in 10 different repositories. Within each repo, edits stay inside `.github/workflows/` (and one `docs/` path for PromptCraft backups).

| Repo | Files touched |
|---|---|
| `ByronWilliamsCPA/.github` | `.github/workflows/python-security-analysis.yml`, `workflow-templates/python-security-analysis.yml`, `CHANGELOG.md` |
| `ByronWilliamsCPA/cookiecutter-python-template` | `{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml`, `docs/org-workflows/python-ci.yml` |
| `ByronWilliamsCPA/cookiecutter-template-sample` | `.github/workflows/ci.yml` |
| `ByronWilliamsCPA/xero-crypto` | `.github/workflows/ci.yml`, `.github/workflows/security-analysis.yml` |
| `williaby/image-preprocessing-detector` | `.github/workflows/security-analysis.yml` |
| `williaby/data_ingestor` | `.github/workflows/security-analysis.yml` |
| `williaby/PromptCraft` | `.github/workflows/ci.yml`, `docs/planning/backups/ci-workflows/ci-optimized.yml`, `docs/planning/backups/ci-workflows/ci-original.yml` |
| `williaby/testing` | `.github/workflows/test.yml` |
| `~/dev/.claude` (this repo) | `docs/standards-manifest.yaml` (add CHECK-CI-051) |

---

## Conventions used throughout this plan

- All work clones into `~/dev/<repo-name>` if not already present. The `~/dev/.claude` worktree pattern is used for the manifest update; external repos use a branch (no nested worktree across repos).
- Branch name on every PR: `chore/remove-safety-scanner`.
- Commit messages use the conventional-commit template defined in the spec.
- Every commit signs (`git config commit.gpgsign true` already set per global standard); never use `--no-verify`, never `--admin`-merge.
- After every edit, `pre-commit run --files <changed paths>` runs locally before commit. If the repo lacks a pre-commit config, run `yamllint <file>` instead.
- Auto-merge enabled with `gh pr merge --auto --squash` only on Tier 2-4 PRs, never on Step 0.

---

## Task 0: Pre-flight verification

**Files:** None (read-only audit)

**Purpose:** Catch any safety references the initial `gh search code` sweep missed, confirm `safety-report.json` has no downstream consumers, and verify gh auth + repo access.

- [ ] **Step 1: Verify gh auth and repo access for both orgs**

```bash
gh auth status
gh repo view ByronWilliamsCPA/.github --json name,defaultBranchRef -q '.name'
gh repo view williaby/PromptCraft --json name,defaultBranchRef -q '.name'
```

Expected: prints `.github` and `PromptCraft` with no auth errors.

- [ ] **Step 2: Deep grep both orgs for safety references in workflows**

```bash
gh search code --owner ByronWilliamsCPA --owner williaby \
  "safety" --extension yml --extension yaml --limit 100 \
  | tee /tmp/safety-sweep-inventory.txt
```

Compare against the inventory in the spec's "Scope" section. Any new file mentioned in the output that is NOT in the spec must be added to the appropriate tier before proceeding. If a new file appears, stop and update the spec + plan before continuing.

- [ ] **Step 3: Search for downstream consumers of `safety-report.json`**

```bash
gh search code --owner ByronWilliamsCPA --owner williaby \
  "safety-report.json" --limit 50 | tee /tmp/safety-report-consumers.txt
```

Expected lines are limited to:
- The workflow files that *produce* `safety-report.json` (already in scope)
- The org workflow's `Upload Security Reports` step (already in scope)

If any line points to a file that *reads* or *parses* `safety-report.json` (e.g., a downstream script, a compliance dashboard, an action that ingests the JSON), stop and surface that consumer to the user. The spec's risk table flagged this as "Low likelihood"; this step verifies the assumption.

- [ ] **Step 4: Search for `.safety-policy.yml` files across both orgs**

```bash
gh search code --owner ByronWilliamsCPA --owner williaby \
  ".safety-policy.yml" --limit 30 | tee /tmp/safety-policy-files.txt
```

Note any matches. Each match's repo gets the policy file deleted in its respective Tier 2/3 PR.

- [ ] **Step 5: Snapshot the current failing state**

```bash
gh run list --repo ByronWilliamsCPA/fragrance-rater --workflow "Security Analysis" --limit 3
gh run list --repo ByronWilliamsCPA/llc-manager --workflow "Security Analysis" --limit 3
```

Expected: Recent runs show `Security Analysis / Security Gate Validation` as FAILURE. Record the run IDs; they're the "before" baseline for Step 0 verification.

- [ ] **Step 6: Commit the audit log to a tracking note (no git commit yet)**

Write the contents of `/tmp/safety-sweep-inventory.txt`, `/tmp/safety-report-consumers.txt`, and `/tmp/safety-policy-files.txt` into a single working note at `/tmp/safety-sweep-preflight.md`. This is a session-local artifact; do not commit. Reference it from each subsequent task.

---

## Task 1: Step 0 for `ByronWilliamsCPA/.github` (live workflow + template mirror)

**Files:**
- Modify: `.github/workflows/python-security-analysis.yml` (in `ByronWilliamsCPA/.github`)
- Modify: `workflow-templates/python-security-analysis.yml` (in `ByronWilliamsCPA/.github`)
- Modify: `CHANGELOG.md` (in `ByronWilliamsCPA/.github`)

- [ ] **Step 1: Clone and create branch**

```bash
cd ~/dev
[ -d dot-github ] || gh repo clone ByronWilliamsCPA/.github dot-github
cd ~/dev/dot-github
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

Expected: branch created from latest origin/main. If the branch already exists locally, the `-B` flag resets it.

- [ ] **Step 2: Edit `.github/workflows/python-security-analysis.yml`**

Open the file. Apply these edits exactly as shown in the spec's "Step 0 diff" section. To summarize, delete these blocks and lines:

1. The entire `run-safety:` input block (under `on.workflow_call.inputs`).
2. The `if:` expression on the `python-security` job, replacing `${{ inputs.run-bandit || inputs.run-safety }}` with `${{ inputs.run-bandit }}`.
3. The job's `name:` field, changing `Python Security Scan` to `Python SAST (Bandit)`.
4. The entire `- name: Safety Vulnerability Scan` step (from the `- name:` line through the end of its `run:` block).
5. The `safety-report.json` line in the `Upload Security Reports` step's `path:` list. If the result is a single-line `path:`, collapse it to `path: bandit-report.json`.
6. The workflow header comment, changing `Comprehensive security scanning with CodeQL, Bandit, Safety, OSV-Scanner, and OWASP` to `Comprehensive security scanning with CodeQL, Bandit, OSV-Scanner, and Dependency-Review`.

- [ ] **Step 3: Edit `workflow-templates/python-security-analysis.yml`**

Apply the **same** six edits as Step 2. This file is the template mirror; it must match the live workflow.

- [ ] **Step 4: Add CHANGELOG entry**

Open `CHANGELOG.md`. Add an entry under the `[Unreleased]` heading (create the heading if absent):

```markdown
## [Unreleased]

### Removed

- `safety` SCA scanner from `python-security-analysis.yml` and the
  `workflow-templates/` mirror. Python dependency vulnerability scanning
  is fully covered by OSV-Scanner, Dependency-Review, and consumer-side
  `pip-audit`. Resolves the cascading regressions from PRs #136/#137/#138
  and the editable-install blocker from #138's merged form. See design
  doc in `~/.claude/docs/superpowers/specs/2026-05-18-safety-removal-fleet-sweep-design.md`.
```

- [ ] **Step 5: Validate YAML syntax**

```bash
yamllint .github/workflows/python-security-analysis.yml \
         workflow-templates/python-security-analysis.yml
```

Expected: no errors. If lint complains about line length on a comment, wrap; otherwise the deletion is line-removing only and should not introduce new violations.

- [ ] **Step 6: Run actionlint if available**

```bash
command -v actionlint && actionlint .github/workflows/python-security-analysis.yml || echo "actionlint not installed, skipping"
```

Expected: no errors, or skip if actionlint is absent.

- [ ] **Step 7: Run pre-commit on changed files**

```bash
pre-commit run --files \
  .github/workflows/python-security-analysis.yml \
  workflow-templates/python-security-analysis.yml \
  CHANGELOG.md
```

Expected: all hooks pass. If `no-em-dash` flags anything, replace em-dashes with colons or commas per the global CLAUDE.md rule.

- [ ] **Step 8: Commit**

```bash
git add .github/workflows/python-security-analysis.yml \
        workflow-templates/python-security-analysis.yml \
        CHANGELOG.md
git commit -m "$(cat <<'EOF'
chore(security): remove redundant safety scanner

Removes the safety SCA call from python-security-analysis.yml (live)
and workflow-templates/python-security-analysis.yml (template mirror).
Python dependency vulnerability scanning is fully covered by:
  - OSV-Scanner (multi-ecosystem, PyPA + GHSA + OSS-Fuzz data)
  - Dependency-Review action (PR-time, GHSA-backed)
  - pip-audit (dev dependency in consumer repos, PyPA-backed)
  - Renovate osvVulnerabilityAlerts + vulnerabilityAlerts (ongoing)

Aligns with manifest CHECK-PYTOOL-005 (safety absent from dependencies).
Resolves the safety 3.x CLI drift surface that caused regressions in
PRs #136, #137, #138 and the editable-install blocker from #138's
merged form.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds, pre-commit hooks pass on commit.

- [ ] **Step 9: Push and open PR**

```bash
git push -u origin chore/remove-safety-scanner
gh pr create \
  --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "$(cat <<'EOF'
## Summary

Removes the `safety` SCA call from the org's reusable
`python-security-analysis.yml` workflow and its `workflow-templates/`
mirror. Replaces nothing.

## Why

The fleet runs five independent Python-dep vulnerability scanners
today (OSV-Scanner, Dependency-Review action, consumer-side pip-audit,
Renovate `osvVulnerabilityAlerts`, Renovate `vulnerabilityAlerts`).
`safety` is the only one currently broken (Layer 8d from the
regression report) and the only one whose Python-CVE coverage is a
strict subset of OSV-Scanner's data sources.

The fleet's own standards manifest (CHECK-PYTOOL-005) already declared
the directional intent: "safety absent from dependencies (replaced by
pip-audit)." This PR extends that intent to workflow YAML.

## Resolves

- Layer 8d (`--no-build` hardcode breaks editable-install consumers)
  from the security-analysis-workflow-regression-report
- The cascading safety-upstream drift surface that produced PRs
  #136, #137, #138

## Verification

- Workflow self-test green on this PR
- Manually retriggered `fragrance-rater` PR #22 Security Analysis
  workflow run AFTER this PR's branch becomes the org workflow's main:
  Security Gate Validation flips from FAILURE to SUCCESS
- Manually retriggered latest `llc-manager` main run: same flip

## Coverage preserved

| Concern | Tool that covers it |
|---|---|
| Python dep CVE (full lockfile) | OSV-Scanner, pip-audit (consumer) |
| Python dep CVE (PR diff) | Dependency-Review action |
| Multi-ecosystem CVE | OSV-Scanner |
| Ongoing vuln alerts | Renovate osvVulnerabilityAlerts + vulnerabilityAlerts |
| Third-party license check (PR diff) | Dependency-Review `license-check: true` |
| Own-source SPDX | REUSE workflow |
| SAST | Bandit, CodeQL, SonarCloud |
| SBOM | sbom.yml |

## Out of scope

- Centralizing williaby's per-repo security workflow copies; tracked
  separately
- Adding a downstream-consumer smoke test for the reusable workflow;
  tracked separately
- Removing safety from consumer-repo local workflow copies; covered by
  follow-up PRs in cookiecutter-python-template, cookiecutter-template-sample,
  xero-crypto, image-preprocessing-detector, data_ingestor, PromptCraft,
  and testing

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed. **Do not enable auto-merge.** This PR needs manual verification against downstream consumers.

- [ ] **Step 10: Capture the PR URL and number**

```bash
gh pr view --json url,number > /tmp/safety-sweep-pr-step0.json
cat /tmp/safety-sweep-pr-step0.json
```

- [ ] **Step 11: Wait for the PR's self-test CI to go green**

```bash
gh pr checks --watch
```

Expected: All checks pass. The reusable workflow's self-test does NOT exercise the consumer code path (per the regression report's process observation #1), so this is necessary but not sufficient.

- [ ] **Step 12: Verify downstream against `fragrance-rater` PR #22**

Trigger a re-run of fragrance-rater's Security Analysis workflow against PR #22 using the branch from this PR:

```bash
# Get the head SHA of this PR's branch
HEAD_SHA=$(git rev-parse HEAD)

# fragrance-rater calls the org workflow via @main; to test against the
# branch, the simplest path is to temporarily merge this PR into a fork
# of the org workflow OR ask the reviewer to test by pinning the consumer
# call to @chore/remove-safety-scanner.

# Document the verification command for the reviewer:
echo "To verify: in ByronWilliamsCPA/fragrance-rater PR #22, edit"
echo "  uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main"
echo "to"
echo "  uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@chore/remove-safety-scanner"
echo "and confirm Security Gate Validation flips from FAILURE to SUCCESS."
```

Expected behavior: do not push speculative changes to fragrance-rater. Surface this verification step to the reviewer in a PR comment. If you have authority to make the test change, do it on a throwaway branch in fragrance-rater, NOT on PR #22 itself.

- [ ] **Step 13: Merge after verification confirms**

Only after Step 12 confirms downstream green:

```bash
gh pr merge --squash --delete-branch
```

Expected: PR merged, branch deleted, default branch updated.

- [ ] **Step 14: Snapshot post-merge state**

```bash
gh run list --repo ByronWilliamsCPA/fragrance-rater --workflow "Security Analysis" --limit 3
gh run list --repo ByronWilliamsCPA/llc-manager --workflow "Security Analysis" --limit 3
```

Expected: New runs (triggered automatically by the org workflow's `@main` update) show `Security Analysis / Security Gate Validation` as SUCCESS. If still FAILURE, investigate before proceeding to Task 2.

---

## Task 2: Tier 2a for `ByronWilliamsCPA/cookiecutter-python-template`

**Files:**
- Modify: `{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml`
- Modify: `docs/org-workflows/python-ci.yml`

**Prerequisite:** Task 1 merged.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d cookiecutter-python-template ] || gh repo clone ByronWilliamsCPA/cookiecutter-python-template
cd ~/dev/cookiecutter-python-template
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Edit `{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml`**

Open the file. Find the `safety` step. The current content includes:

```yaml
- name: Run Safety
  run: uv run safety check --output json > safety-report.json || true
```

Delete the entire step (the `- name:` line through the end of its `run:` block). Also delete any `safety-report.json` reference in the artifact upload step. If the step is the only content of its job, delete the job; otherwise leave the surrounding YAML intact.

- [ ] **Step 3: Edit `docs/org-workflows/python-ci.yml`**

This file currently contains:

```yaml
uv run safety check -r requirements.txt || {
  ...
}
```

Delete the safety invocation block, including the `|| { ... }` suppression. If the parent step has no remaining content, delete the step.

- [ ] **Step 4: Render the cookiecutter to a throwaway dir and verify CI shape**

No formal cookiecutter test harness exists in `.claude` per the Explore findings, so use the manual render-and-inspect pattern:

```bash
rm -rf /tmp/cookiecutter-render-test
uvx cookiecutter . --no-input --output-dir /tmp/cookiecutter-render-test
cd /tmp/cookiecutter-render-test/*/
grep -rn "safety" .github/workflows/ && echo "FAIL: safety still present" || echo "OK: no safety references"
cd ~/dev/cookiecutter-python-template
```

Expected: `OK: no safety references` printed. If `FAIL` printed, return to Step 2 and find the missed reference.

- [ ] **Step 5: Run pre-commit on changed files**

```bash
pre-commit run --files \
  '{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml' \
  docs/org-workflows/python-ci.yml
```

Expected: hooks pass.

- [ ] **Step 6: Commit**

```bash
git add '{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml' \
        docs/org-workflows/python-ci.yml
git commit -m "$(cat <<'EOF'
chore(security): remove safety from rendered project + org-workflow doc

Mirrors the removal in ByronWilliamsCPA/.github main. New projects
bootstrapped from this template will no longer carry the safety 2.x
syntax. Python dep vuln scanning remains covered by pip-audit
(already a dev dep in the rendered project) and OSV-Scanner (in the
rendered security workflow).

Aligns with manifest CHECK-PYTOOL-005.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Push, open PR, enable auto-merge**

```bash
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove safety from rendered project + docs" \
  --body "Mirrors the removal in ByronWilliamsCPA/.github. See design doc in ~/.claude/docs/superpowers/specs/2026-05-18-safety-removal-fleet-sweep-design.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
```

Expected: PR merges automatically once CI passes.

- [ ] **Step 8: Wait for merge and confirm**

```bash
gh pr checks --watch
gh pr view --json state -q '.state'
```

Expected: `MERGED`.

---

## Task 3: Tier 2b for `ByronWilliamsCPA/cookiecutter-template-sample`

**Files:**
- Modify: `.github/workflows/ci.yml`

**Prerequisite:** Task 1 merged. (Task 2 does not block Task 3, they can run in parallel after Task 1, but the plan sequences them for serial execution.)

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d cookiecutter-template-sample ] || gh repo clone ByronWilliamsCPA/cookiecutter-template-sample
cd ~/dev/cookiecutter-template-sample
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Edit `.github/workflows/ci.yml`**

Find the block:

```yaml
uv run safety check -r requirements.txt || {
  ...
}
```

Delete the entire `safety` invocation block, including the `|| { ... }` suppression. If the parent step is left empty, delete the step.

- [ ] **Step 3: Validate YAML syntax**

```bash
yamllint .github/workflows/ci.yml
```

Expected: no errors.

- [ ] **Step 4: Run pre-commit if configured**

```bash
[ -f .pre-commit-config.yaml ] && pre-commit run --files .github/workflows/ci.yml || echo "no pre-commit, skipping"
```

- [ ] **Step 5: Commit, push, open PR, auto-merge**

```bash
git add .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
chore(security): remove safety from CI workflow

Mirrors the removal in ByronWilliamsCPA/.github main. OSV-Scanner
and pip-audit (dev dep) provide full Python dep vuln coverage.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove safety from CI workflow" \
  --body "Mirrors the removal in ByronWilliamsCPA/.github.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

Expected: PR merges.

---

## Task 4: Tier 3a for `ByronWilliamsCPA/xero-crypto`

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/security-analysis.yml`

**Prerequisite:** Task 1 merged. Tasks 2-3 can be in flight or merged.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d xero-crypto ] || gh repo clone ByronWilliamsCPA/xero-crypto
cd ~/dev/xero-crypto
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Find all safety references in the repo**

```bash
git grep -in "safety" .github/ | tee /tmp/xero-crypto-safety-refs.txt
```

Expected output includes the three references in `ci.yml` and `security-analysis.yml`. If additional references appear in other files (e.g., `dependabot.yml`, action configs), add them to the deletion list.

- [ ] **Step 3: Edit `.github/workflows/ci.yml`**

Find the line:

```yaml
safety check || echo "Safety completed with findings"
```

Delete the entire step containing this line (the `- name:` line through the `run:` block end). If the step is the only one in its job, delete the job; otherwise leave surrounding YAML intact.

- [ ] **Step 4: Edit `.github/workflows/security-analysis.yml`**

Find the two `poetry run safety check ...` invocations. Delete both steps entirely (each `- name:` line through its `run:` block end). Also delete any `safety-report.json` reference in artifact upload steps. If a now-empty job remains, delete it.

- [ ] **Step 5: Verify no remaining safety references in workflows**

```bash
git grep -in "safety" .github/workflows/ && echo "FAIL: refs remain" || echo "OK: clean"
```

Expected: `OK: clean`.

- [ ] **Step 6: Delete `.safety-policy.yml` if present**

```bash
[ -f .safety-policy.yml ] && git rm .safety-policy.yml || echo "no policy file"
```

- [ ] **Step 7: Validate YAML**

```bash
yamllint .github/workflows/ci.yml .github/workflows/security-analysis.yml
```

Expected: no errors.

- [ ] **Step 8: Run pre-commit if configured**

```bash
[ -f .pre-commit-config.yaml ] && pre-commit run --files .github/workflows/ci.yml .github/workflows/security-analysis.yml || echo "no pre-commit"
```

- [ ] **Step 9: Commit, push, open PR, auto-merge**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(security): remove redundant safety scanner

Removes safety from ci.yml (1 call) and security-analysis.yml (2 calls).
Coverage preserved by OSV-Scanner, Dependency-Review, and pip-audit.

Aligns with manifest CHECK-PYTOOL-005.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "Mirrors the removal in ByronWilliamsCPA/.github.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

Expected: PR merges.

---

## Task 5: Tier 3b for `williaby/image-preprocessing-detector`

**Files:**
- Modify: `.github/workflows/security-analysis.yml`

**Prerequisite:** Task 1 merged.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d image-preprocessing-detector ] || gh repo clone williaby/image-preprocessing-detector
cd ~/dev/image-preprocessing-detector
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Find safety references**

```bash
git grep -in "safety" .github/ | tee /tmp/ipd-safety-refs.txt
```

Expected: two `uv run safety check ...` lines in `security-analysis.yml`.

- [ ] **Step 3: Edit `.github/workflows/security-analysis.yml`**

Delete the two safety step blocks entirely. Also delete `safety-report.json` from any artifact upload step. If a now-empty job remains, delete the job.

- [ ] **Step 4: Delete `.safety-policy.yml` if present**

```bash
[ -f .safety-policy.yml ] && git rm .safety-policy.yml || echo "no policy file"
```

- [ ] **Step 5: Verify clean**

```bash
git grep -in "safety" .github/workflows/ && echo "FAIL" || echo "OK"
yamllint .github/workflows/security-analysis.yml
```

Expected: `OK` and no yamllint errors.

- [ ] **Step 6: Run williaby's required-check inventory**

```bash
gh api repos/williaby/image-preprocessing-detector/rules/branches/main \
  --jq '.[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'
```

Note any required check names. If `Security Analysis / Safety Vulnerability Scan` (or similar) is listed as required, the deletion will leave the rule waiting for a check that never runs. In that case, update the ruleset to remove the obsolete required check entry, coordinate with the user before pushing.

- [ ] **Step 7: Run pre-commit if configured**

```bash
[ -f .pre-commit-config.yaml ] && pre-commit run --files .github/workflows/security-analysis.yml || echo "no pre-commit"
```

- [ ] **Step 8: Commit, push, open PR, auto-merge**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(security): remove redundant safety scanner

Removes 2 safety calls from security-analysis.yml. Coverage preserved
by OSV-Scanner, Dependency-Review, and pip-audit.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "Mirrors removal in ByronWilliamsCPA/.github.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

---

## Task 6: Tier 3c for `williaby/data_ingestor`

**Files:**
- Modify: `.github/workflows/security-analysis.yml`

**Prerequisite:** Task 1 merged.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d data_ingestor ] || gh repo clone williaby/data_ingestor
cd ~/dev/data_ingestor
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Find safety references**

```bash
git grep -in "safety" .github/ | tee /tmp/data-ingestor-safety-refs.txt
```

Expected: two `poetry run safety check ...` lines in `security-analysis.yml`.

- [ ] **Step 3: Edit `.github/workflows/security-analysis.yml`**

Delete both safety step blocks entirely. Also delete any `safety-report.json` references in artifact upload steps.

- [ ] **Step 4: Delete `.safety-policy.yml` if present**

```bash
[ -f .safety-policy.yml ] && git rm .safety-policy.yml || echo "no policy file"
```

- [ ] **Step 5: Verify clean and lint**

```bash
git grep -in "safety" .github/workflows/ && echo "FAIL" || echo "OK"
yamllint .github/workflows/security-analysis.yml
```

Expected: `OK` and no yamllint errors.

- [ ] **Step 6: Check required-check ruleset**

```bash
gh api repos/williaby/data_ingestor/rules/branches/main \
  --jq '.[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context' 2>/dev/null || echo "no ruleset"
```

If any required check references safety, coordinate with the user before merging.

- [ ] **Step 7: Run pre-commit, commit, push, open PR, auto-merge**

```bash
[ -f .pre-commit-config.yaml ] && pre-commit run --files .github/workflows/security-analysis.yml || echo "no pre-commit"
git add -A
git commit -m "$(cat <<'EOF'
chore(security): remove redundant safety scanner

Removes 2 safety calls from security-analysis.yml. Coverage preserved
by OSV-Scanner, Dependency-Review, and pip-audit.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "Mirrors removal in ByronWilliamsCPA/.github.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

---

## Task 7: Tier 3d for `williaby/PromptCraft` (live workflow + Tier 4 backups)

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/planning/backups/ci-workflows/ci-optimized.yml`
- Modify: `docs/planning/backups/ci-workflows/ci-original.yml`

**Prerequisite:** Task 1 merged.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d PromptCraft ] || gh repo clone williaby/PromptCraft
cd ~/dev/PromptCraft
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Find safety references**

```bash
git grep -in "safety" .github/ docs/planning/backups/ci-workflows/ | tee /tmp/promptcraft-safety-refs.txt
```

Expected references:
- `.github/workflows/ci.yml`: `poetry run safety check || echo "Safety check completed with findings"`
- `docs/planning/backups/ci-workflows/ci-optimized.yml`: `poetry run safety check || echo "..."`
- `docs/planning/backups/ci-workflows/ci-original.yml`: `- name: Run safety check` block

- [ ] **Step 3: Edit `.github/workflows/ci.yml`**

Delete the entire safety step (the `- name:` line through its `run:` block end). The `|| echo` suppression goes away with the step.

- [ ] **Step 4: Edit `docs/planning/backups/ci-workflows/ci-optimized.yml` and `ci-original.yml`**

Both files are historical CI backups. Delete the safety steps in each. If you prefer to leave historical backups untouched as a record, add a top-of-file comment instead:

```yaml
# Historical backup. Safety scanner was removed fleet-wide on 2026-05;
# see ByronWilliamsCPA/.github PR for the removal rationale.
```

Default: delete the safety steps. The comment alternative is acceptable only if a reviewer requests preserving the literal historical content.

- [ ] **Step 5: Delete `.safety-policy.yml` if present**

```bash
[ -f .safety-policy.yml ] && git rm .safety-policy.yml || echo "no policy file"
```

- [ ] **Step 6: Verify clean and lint**

```bash
git grep -in "safety" .github/workflows/ && echo "FAIL: workflow refs remain" || echo "OK: workflows clean"
yamllint .github/workflows/ci.yml
```

Expected: `OK: workflows clean` and no yamllint errors. Backup files may still have leftover safety references if you chose the comment alternative in Step 4; that's acceptable.

- [ ] **Step 7: Check required-check ruleset**

```bash
gh api repos/williaby/PromptCraft/rules/branches/main \
  --jq '.[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context' 2>/dev/null || echo "no ruleset"
```

Coordinate with user if safety appears in required checks.

- [ ] **Step 8: Run pre-commit if configured**

```bash
[ -f .pre-commit-config.yaml ] && pre-commit run --files .github/workflows/ci.yml docs/planning/backups/ci-workflows/ || echo "no pre-commit"
```

- [ ] **Step 9: Commit, push, open PR, auto-merge**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(security): remove redundant safety scanner

Removes safety from ci.yml plus the two ci-workflows backups under
docs/planning/backups/. Coverage preserved by OSV-Scanner,
Dependency-Review, and pip-audit.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "Mirrors removal in ByronWilliamsCPA/.github. Also cleans up two historical ci-workflow backup files under docs/planning/.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

---

## Task 8: Tier 3e for `williaby/testing`

**Files:**
- Modify: `.github/workflows/test.yml`

**Prerequisite:** Task 1 merged.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d testing ] || gh repo clone williaby/testing
cd ~/dev/testing
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Find safety references**

```bash
git grep -in "safety" .github/ | tee /tmp/testing-safety-refs.txt
```

Expected: `safety check --json || true` in `test.yml`.

- [ ] **Step 3: Edit `.github/workflows/test.yml`**

Delete the entire safety step. The `|| true` suppression goes away with it. If the step is the only one in its job, delete the job entirely.

- [ ] **Step 4: Delete `.safety-policy.yml` if present**

```bash
[ -f .safety-policy.yml ] && git rm .safety-policy.yml || echo "no policy file"
```

- [ ] **Step 5: Verify clean, lint, commit, push, open PR, auto-merge**

```bash
git grep -in "safety" .github/workflows/ && echo "FAIL" || echo "OK"
yamllint .github/workflows/test.yml
[ -f .pre-commit-config.yaml ] && pre-commit run --files .github/workflows/test.yml || echo "no pre-commit"

git add -A
git commit -m "$(cat <<'EOF'
chore(security): remove redundant safety scanner

Removes safety from test.yml (was `safety check --json || true`,
exit-code suppressed). Coverage preserved by OSV-Scanner and
pip-audit if added.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "Mirrors removal in ByronWilliamsCPA/.github.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

---

## Task 9: Manifest update for `~/dev/.claude`

**Files:**
- Modify: `docs/standards-manifest.yaml` (add CHECK-CI-051)
- Modify: `docs/standards-manifest.yaml` (remove or update stale CHECK-CLAUDE-* mention of safety)

**Prerequisite:** Tasks 1-8 all merged.

- [ ] **Step 1: Create an isolated worktree to avoid the uncommitted work in the main checkout**

```bash
cd ~/dev/.claude
git fetch origin main
git worktree add .worktrees/chore-add-safety-manifest-rule -b chore/add-safety-manifest-rule origin/main
cd .worktrees/chore-add-safety-manifest-rule
```

Expected: worktree created at `~/dev/.claude/.worktrees/chore-add-safety-manifest-rule`.

- [ ] **Step 2: Find the last CHECK-CI-* entry**

```bash
grep -n "id: CI-0" docs/standards-manifest.yaml | tail -5
```

Expected output includes `id: CI-050`. The next free number is CI-051.

- [ ] **Step 3: Find the exact YAML location to insert CI-051**

```bash
grep -n "CI-050" docs/standards-manifest.yaml
```

Note the line numbers. The new entry inserts immediately AFTER the closing block of CI-050.

- [ ] **Step 4: Read the surrounding YAML structure**

```bash
sed -n '1420,1450p' docs/standards-manifest.yaml
```

Inspect the exact indentation, field order, and block style. Match the style precisely.

- [ ] **Step 5: Insert the new CHECK-CI-051 entry**

Using the Edit tool, append immediately after the last line of the CI-050 block:

```yaml
  - id: CI-051
    domain: ci
    severity: important
    override_eligible: false
    description: >-
      safety command absent from workflow YAML (replaced by OSV-Scanner,
      Dependency-Review, and pip-audit). Prevents reintroduction of the
      safety 3.x CLI drift surface that caused cascading regressions in
      2026-05 (ByronWilliamsCPA/.github PRs #136/#137/#138).
    verify: >-
      content_absent_any: .github/workflows/*.yml, safety check, safety scan, safety --
    source_frameworks:
      - manifest-internal
    notes: >-
      Safety's free-tier Python CVE data is a strict subset of OSV-Scanner's
      sources (PyPA + GHSA + OSS-Fuzz). License scanning requires Safety
      paid tier and is not invoked by any current workflow. Coverage is
      fully maintained by OSV-Scanner + Dependency-Review + pip-audit +
      Renovate vulnerability alerts.
```

Match the indentation of the CI-050 entry exactly. Field order: `id`, `domain`, `severity`, `override_eligible`, `description`, `verify`, then optional fields.

- [ ] **Step 6: Remove or update the stale CHECK-CLAUDE-* safety entry**

```bash
grep -n "safety" docs/standards-manifest.yaml | grep -i "claude.md"
```

Expected output points to the entry at lines 1028-1029 that checks `CLAUDE.md, safety check` content absence. This is now superseded by CI-051.

Edit option 1 (cleaner): delete that CHECK entry entirely.
Edit option 2 (conservative): change the verify line to drop the `safety check` token, leaving the rest of the check intact.

Pick option 1 unless the CHECK entry serves another purpose. Document the choice in the commit message.

- [ ] **Step 7: Validate YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('docs/standards-manifest.yaml'))"
```

Expected: no error. If a `yaml.YAMLError` is raised, the indentation in Step 5 is wrong.

- [ ] **Step 8: Run pre-commit on the manifest file**

```bash
pre-commit run --files docs/standards-manifest.yaml
```

Expected: all hooks pass (yamllint, no-em-dash, markdownlint frontmatter if it picks it up, etc.).

- [ ] **Step 9: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -m "$(cat <<'EOF'
chore(compliance): add CI-051 banning safety in workflow YAML

Adds a new CI-domain check that prevents reintroduction of the safety
SCA scanner into any .github/workflows/*.yml file. Pairs with the
fleet-wide removal of safety (Tasks 1-8 of the 2026-05-18 safety
removal sweep).

Also removes the now-stale CHECK-CLAUDE entry that watched CLAUDE.md
for "safety check" mentions; the broader CI rule supersedes it.

Coverage preserved by OSV-Scanner, Dependency-Review, consumer-side
pip-audit, and Renovate vulnerability alerts.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 10: Push and open PR**

```bash
git push -u origin chore/add-safety-manifest-rule
gh pr create --base main \
  --title "chore(compliance): add CI-051 banning safety in workflow YAML" \
  --body "Prevents reintroduction of the safety SCA scanner after the fleet-wide removal completed in 2026-05.

See design doc: \`docs/superpowers/specs/2026-05-18-safety-removal-fleet-sweep-design.md\`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

Expected: PR merges.

- [ ] **Step 11: Clean up the worktree**

```bash
cd ~/dev/.claude
git worktree remove .worktrees/chore-add-safety-manifest-rule
```

Expected: worktree removed cleanly.

---

## Task 10: Final verification, repo-audit run

**Files:** None (read-only audit)

**Prerequisite:** Tasks 1-9 all merged.

- [ ] **Step 1: Run the repo-audit skill against the fleet**

In a fresh Claude Code session in `~/dev/.claude`:

```
/repo-audit ByronWilliamsCPA/fragrance-rater
```

Then for each of: `llc-manager`, `xero-crypto`, `cookiecutter-python-template`, `cookiecutter-template-sample`, `gleif`, `audio-processor`, `rag-processor`, `python-libs`, `maester-tests`, `homelab-infra`, `family-office-portal`, and each williaby repo affected.

Expected: CI-051 passes on every repo (no `safety` references in workflows). No CI checks newly fail because of the manifest update.

- [ ] **Step 2: Cross-check: search both orgs for any remaining safety in YAML**

```bash
gh search code --owner ByronWilliamsCPA --owner williaby \
  "safety" --extension yml --extension yaml --limit 100 \
  > /tmp/safety-final-check.txt
cat /tmp/safety-final-check.txt
```

Expected output lines should be limited to:
- README/CHANGELOG documentation references to the removal
- Comments that mention safety in a historical context

If any line points to an executable safety invocation (`safety check`, `safety scan`, `uv run safety ...`), that repo was missed; open a follow-up PR.

- [ ] **Step 3: Verify the regression report's open blocker is resolved**

```bash
gh run list --repo ByronWilliamsCPA/fragrance-rater --workflow "Security Analysis" --limit 5
```

Expected: Last 5 runs show `Security Analysis / Security Gate Validation` as SUCCESS. The "Layer 8d" blocker from `security-analysis-workflow-regression-report.md` is closed.

- [ ] **Step 4: Mark the design and plan as completed**

Edit `~/dev/.claude/docs/superpowers/specs/2026-05-18-safety-removal-fleet-sweep-design.md` and change `status: draft` to `status: completed` in the frontmatter. Same for this plan file. Commit both changes in a single commit in `~/dev/.claude`:

```bash
cd ~/dev/.claude
git checkout main
git pull origin main
# Use a worktree if the working tree is dirty
git status --short
# If clean, edit in place; if dirty, create a worktree as in Task 9 Step 1
```

Apply the frontmatter change to both files, then:

```bash
git add docs/superpowers/specs/2026-05-18-safety-removal-fleet-sweep-design.md \
        docs/superpowers/plans/2026-05-18-safety-removal-fleet-sweep.md
git commit -m "$(cat <<'EOF'
docs(spec): mark safety removal sweep as completed

All 9 PRs merged across BWCPA and williaby; manifest CI-051 active;
post-merge audit confirmed no remaining safety invocations in
workflow YAML and fragrance-rater Security Gate flipped to SUCCESS.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push origin main
```

---

## Acceptance criteria (from spec)

- [x] Task 1: Step 0 PR merged. `fragrance-rater` PR #22's `Security Analysis / Security Gate Validation` passes.
- [x] Tasks 2-3: Cookiecutter PRs merged. Generating a new repo from `cookiecutter-python-template` produces no `safety` references in workflow files.
- [x] Tasks 4-8: All Tier 3 PRs merged. `git grep -in safety` across affected repos returns no matches in `.github/workflows/`.
- [x] Task 7: PromptCraft Tier 4 backups updated.
- [x] Task 9: Manifest update merged. `CHECK-CI-051` runs on the next `/repo-audit` and reports zero violations.
- [x] Task 10: All previously-failing editable-install consumer CIs are green.
