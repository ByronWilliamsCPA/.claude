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

**Architecture:** Sequential per-repo PRs. Step 0 (the org workflow in `ByronWilliamsCPA/.github`) lands first and unblocks every editable-install consumer; then two cookiecutter templates land (Tasks 2 and 3 are mutually independent and can run concurrently once Task 1 is merged, though this plan documents them serially for ease of single-operator execution); then five live-consumer PRs (Tasks 4-8) land. These five can run in batches of three concurrent PRs (e.g., dispatch Tasks 4, 5, 6 in parallel; then Tasks 7, 8) when an operator coordinates them via parallel subagents or multiple terminal sessions; the plan documents them sequentially for the default single-operator flow. Finally the `.claude` manifest rule lands.

**Tech Stack:** GitHub CLI (`gh`), git, pre-commit, ruff, yamllint, cookiecutter, uv, poetry. All commits signed; no `--no-verify`, no `--admin`.

---

## File Structure

The plan modifies files in 9 different repositories. Most edits live inside `.github/workflows/`; PromptCraft additionally touches a `docs/` path for backup workflows and two `.agents/` config files that reference safety in their tool/package lists.

| Repo | Files touched |
|---|---|
| `ByronWilliamsCPA/.github` | `.github/workflows/python-security-analysis.yml`, `workflow-templates/python-security-analysis.yml`, `CHANGELOG.md` |
| `ByronWilliamsCPA/cookiecutter-python-template` | `{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml`, `docs/org-workflows/python-ci.yml` |
| `ByronWilliamsCPA/cookiecutter-template-sample` | `.github/workflows/ci.yml` |
| `ByronWilliamsCPA/xero-crypto` | `.github/workflows/ci.yml`, `.github/workflows/security-analysis.yml` |
| `williaby/image-preprocessing-detector` | `.github/workflows/security-analysis.yml` |
| `williaby/data_ingestor` | `.github/workflows/security-analysis.yml` |
| `williaby/PromptCraft` | `.github/workflows/ci.yml`, `.github/workflows/renovate-auto-merge.yml`, `docs/planning/backups/ci-workflows/ci-optimized.yml`, `docs/planning/backups/ci-workflows/ci-original.yml`, `.agents/core/code-reviewer.yaml`, `.agents/discovery-config.yaml` |
| `williaby/testing` | `.github/workflows/test.yml` |
| `~/dev/.claude` (this repo) | `docs/standards-manifest.yaml` (CI-051 already added via PR #121) |

---

## Conventions used throughout this plan

- All work clones into `~/dev/<repo-name>` if not already present. The `~/dev/.claude` worktree pattern is used for the manifest update; external repos use a branch (no nested worktree across repos).
- Branch name on every PR: `chore/remove-safety-scanner`.
- Commit messages use the conventional-commit template defined in the spec.
- Every commit signs (`git config commit.gpgsign true` already set per global standard); never use `--no-verify`, never `--admin`-merge.
- Before committing, run `pre-commit run --all-files` in the affected repo per the global CLAUDE.md rule. If the repo lacks a pre-commit config, run `yamllint <file>` against each changed file instead.
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

## Task 1: Step 0 for `ByronWilliamsCPA/.github` (live workflow + template mirror) -- COMPLETE

**Status:** Completed via [ByronWilliamsCPA/.github PR #140](https://github.com/ByronWilliamsCPA/.github/pull/140) (`chore(security)!: remove redundant safety scanner`), merged 2026-05-18 22:43Z.

**Files modified by PR #140:**

- `.github/workflows/python-security-analysis.yml`
- `workflow-templates/python-security-analysis.yml`
- `CHANGELOG.md`

**Verification (read-only, confirms current state on main):**

```bash
gh api repos/ByronWilliamsCPA/.github/contents/.github/workflows/python-security-analysis.yml \
  --jq '.content' | base64 -d | grep -c -i safety
# Expected: 0

gh api repos/ByronWilliamsCPA/.github/contents/workflow-templates/python-security-analysis.yml \
  --jq '.content' | base64 -d | grep -c -i safety
# Expected: 0
```

**Downstream consumer impact:** Editable-install consumers (`fragrance-rater`, `llc-manager`) automatically picked up the change on their next workflow run because they reference `@main`. PR #140 unblocked all subsequent Tier 2 and Tier 3 work.

<details>
<summary>Original step-by-step plan (preserved for traceability)</summary>

The pre-execution plan called for: clone repo and branch; edit `.github/workflows/python-security-analysis.yml` and the `workflow-templates/` mirror to remove the `run-safety` input, the safety scan step, the `safety-report.json` artifact, and the workflow header comment reference; add a `CHANGELOG.md` entry under `[Unreleased]`; validate with `yamllint` and `actionlint`; run `pre-commit run --all-files`; commit signed; open PR without auto-merge; verify downstream by re-running `fragrance-rater` PR #22 Security Analysis; merge after green; snapshot post-merge fleet run state. PR #140 executed this plan as merged.

</details>

---

## Task 2: Tier 2a for `ByronWilliamsCPA/cookiecutter-python-template` -- COMPLETE

**Status:** Completed via [ByronWilliamsCPA/cookiecutter-python-template PR #55](https://github.com/ByronWilliamsCPA/cookiecutter-python-template/pull/55) (`chore(security): remove safety from rendered project + docs`), merged 2026-05-19 04:37Z.

**Files modified by PR #55:**

- `{{cookiecutter.project_slug}}/.github/workflows/security-analysis.yml`
- `docs/org-workflows/python-ci.yml`

**Verification (read-only, confirms current state on main):**

```bash
gh api repos/ByronWilliamsCPA/cookiecutter-python-template/contents/%7B%7Bcookiecutter.project_slug%7D%7D/.github/workflows/security-analysis.yml \
  --jq '.content' | base64 -d | grep -c -i safety
# Expected: 0

gh api repos/ByronWilliamsCPA/cookiecutter-python-template/contents/docs/org-workflows/python-ci.yml \
  --jq '.content' | base64 -d | grep -c -i safety
# Expected: 0
```

**Downstream impact:** New projects bootstrapped from this template will no longer carry `safety` references in their rendered security workflow. The cookiecutter doc copy of the org workflow also no longer mentions `safety`.

<details>
<summary>Original step-by-step plan (preserved for traceability)</summary>

The pre-execution plan called for: clone the template repo; remove the `Run Safety` step from the rendered `security-analysis.yml`; remove the `safety check -r requirements.txt` block from the org-workflow doc copy; render the template to `/tmp` and grep for `safety` to confirm zero references; run pre-commit on changed files; commit signed; open a PR with `gh pr merge --auto --squash`; wait for merge. PR #55 executed this plan as merged.

</details>

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
- Modify: `.github/workflows/renovate-auto-merge.yml` (added 2026-05-18 after Task 0 pre-flight surfaced 2 `safety scan` calls with `SAFETY_API_KEY` auth)
- Modify: `.agents/core/code-reviewer.yaml` (remove safety from tool list)
- Modify: `.agents/discovery-config.yaml` (remove safety from package list)
- Modify: `docs/planning/backups/ci-workflows/ci-optimized.yml`
- Modify: `docs/planning/backups/ci-workflows/ci-original.yml`
- Post-merge: delete the `SAFETY_API_KEY` repository secret via `gh secret delete SAFETY_API_KEY --repo williaby/PromptCraft`

**Prerequisite:** Task 1 merged.

**Note on Task 7 expanded scope:** Pre-flight (Task 0) surfaced two safety calls in `renovate-auto-merge.yml` that the original `gh search code "safety check"` query missed because the file uses safety 3.x syntax (`safety scan`). These calls use the org's free-tier SAFETY_API_KEY. Per the user's decision (2026-05-18), free tier is single-codebase and uses the same public data as unauthenticated `safety scan`, so the dashboard value does not justify keeping the integration. Remove and delete the secret.

- [ ] **Step 1: Clone and branch**

```bash
cd ~/dev
[ -d PromptCraft ] || gh repo clone williaby/PromptCraft
cd ~/dev/PromptCraft
git fetch origin main
git checkout -B chore/remove-safety-scanner origin/main
```

- [ ] **Step 2: Find safety references (broad)**

```bash
git grep -inE "safety|SAFETY_API_KEY" .github/ docs/planning/backups/ci-workflows/ .agents/ | tee /tmp/promptcraft-safety-refs.txt
```

Expected references:
- `.github/workflows/ci.yml`: `poetry run safety check || echo "Safety check completed with findings"`
- `.github/workflows/renovate-auto-merge.yml`: two `poetry run safety scan ...` calls plus a `SAFETY_API_KEY: ${{ secrets.SAFETY_API_KEY }}` env entry, plus `safety-report.json` in artifact upload
- `.agents/core/code-reviewer.yaml`: `safety` listed in a security tools list
- `.agents/discovery-config.yaml`: `safety` listed in a package list
- `docs/planning/backups/ci-workflows/ci-optimized.yml`: `poetry run safety check || echo "..."`
- `docs/planning/backups/ci-workflows/ci-original.yml`: `- name: Run safety check` block

- [ ] **Step 3: Edit `.github/workflows/ci.yml`**

Delete the entire safety step (the `- name:` line through its `run:` block end). The `|| echo` suppression goes away with the step.

- [ ] **Step 3b: Edit `.github/workflows/renovate-auto-merge.yml`**

Delete both `poetry run safety scan ...` invocations (each is preceded by an `if [ -n "$SAFETY_API_KEY" ]` branch). Delete the surrounding shell logic that gates on `SAFETY_API_KEY` if it becomes empty after the safety calls are removed. Delete the `SAFETY_API_KEY: ${{ secrets.SAFETY_API_KEY }}` env entry. Delete `safety-report.json` from the artifact upload `path:` list (keep `osv-report.json` and `bandit-report.json`). Delete the `safety_api_key.txt` file management lines (`echo`, `rm`) since the secret no longer flows in.

- [ ] **Step 3c: Edit `.agents/core/code-reviewer.yaml` and `.agents/discovery-config.yaml`**

Remove the `safety` entry from each file's tool / package list. Adjust surrounding YAML structure (e.g., comma separators in flow-style lists, indentation in block-style lists) so the file remains valid YAML.

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

Removes safety from ci.yml, renovate-auto-merge.yml (paid-tier
SAFETY_API_KEY auth flow), .agents/*.yaml tool lists, and the two
ci-workflows backups under docs/planning/backups/. Coverage preserved
by OSV-Scanner, Dependency-Review, and pip-audit. The SAFETY_API_KEY
secret is now unused and will be deleted post-merge via
`gh secret delete SAFETY_API_KEY --repo williaby/PromptCraft`.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-safety-scanner
gh pr create --base main \
  --title "chore(security): remove redundant safety scanner" \
  --body "Mirrors removal in ByronWilliamsCPA/.github. Also: (a) removes the safety scan in renovate-auto-merge.yml that used the free-tier SAFETY_API_KEY (the key is single-codebase on free tier, so it cannot scale to the fleet); (b) drops safety from two .agents/*.yaml tool lists; (c) cleans up two historical ci-workflow backup files under docs/planning/.

Post-merge: \`gh secret delete SAFETY_API_KEY --repo williaby/PromptCraft\` to remove the now-unused secret.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr merge --auto --squash --delete-branch
gh pr checks --watch
```

- [ ] **Step 10: Post-merge cleanup of unused SAFETY_API_KEY secret**

**Before deletion (irreversible):** confirm a backup of the key value exists in 1Password (or accept that recovery requires re-registering the codebase with Safety to mint a fresh key). The free-tier key has no proprietary value, so re-registration is a low-cost recovery path; the 1Password copy is the cheaper option.

After the PR merges (and only then, since the secret might still be referenced briefly during the merge window):

```bash
gh secret delete SAFETY_API_KEY --repo williaby/PromptCraft
gh secret list --repo williaby/PromptCraft | grep -i safety && echo "FAIL: secret still listed" || echo "OK: secret deleted"
```

Expected: secret deleted and not listed. After this step, Task 10's verification should include `gh secret list --repo williaby/PromptCraft | grep -v SAFETY_` to confirm no SAFETY_* secrets remain.

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

## Task 9: Manifest update for `~/dev/.claude` -- COMPLETE (verification only)

**Status:** Both manifest changes already landed.

- `CI-051` added via [`.claude` PR #121](https://github.com/ByronWilliamsCPA/.claude/pull/121) (`chore(compliance): add CI-051 banning safety in workflow YAML`).
- `CLAUDE-006` was restored in the same PR scoped to `black,mypy` only; the safety check is intentionally NOT in its `verify` line because CI-051 covers it at workflow YAML scope. The description on `CLAUDE-006` notes "Safety check absence is covered separately by CI-051".

**Severity reconciliation note:** The spec originally specified `severity: error` for CI-051. The merged manifest entry uses `severity: important`, which is consistent with the rest of the CI-domain checks. Spec has been updated to match.

**Verification (read-only):**

```bash
# Confirm CI-051 is present
gh api repos/ByronWilliamsCPA/.claude/contents/docs/standards-manifest.yaml \
  --jq '.content' | base64 -d | grep -A 5 "id: CI-051" | head -10

# Confirm CLAUDE-006 verify is scoped to black,mypy (NOT safety)
gh api repos/ByronWilliamsCPA/.claude/contents/docs/standards-manifest.yaml \
  --jq '.content' | base64 -d | grep -B 1 -A 6 "id: CLAUDE-006" | head -10
```

Expected: CI-051 entry returns with `severity: important` and `verify: content_absent_any: .github/workflows/*.yml, safety check, safety scan, safety --`. CLAUDE-006 verify shows `content_absent_any: CLAUDE.md, black,mypy` (no safety token).

<details>
<summary>Original step-by-step plan (preserved for traceability)</summary>

The pre-execution plan called for: create an isolated worktree on a new `chore/add-safety-manifest-rule` branch; locate the next free CI-* check number (CI-051); insert a new CHECK entry banning `safety` in workflow YAML; remove or narrow the stale CLAUDE-006 entry that previously checked CLAUDE.md for `safety check`; validate YAML; run pre-commit; commit signed; push and merge via `gh pr merge --auto --squash`. PR #121 executed this plan as merged.

</details>

---

## Task 10: Final verification, repo-audit run

**Files:** None (read-only audit)

**Prerequisite:** Tasks 1-9 all merged.

- [ ] **Step 1: Run the repo-audit skill against the fleet**

In a fresh Claude Code session in `~/dev/.claude`:

```text
/repo-audit ByronWilliamsCPA/fragrance-rater
```

Then for each repo affected by this sweep: `cookiecutter-python-template`, `cookiecutter-template-sample`, `xero-crypto`, `image-preprocessing-detector`, `data_ingestor`, `PromptCraft`, `testing`. (Verification is intentionally scoped to repos that this sweep touched; a separate fleet-wide CI-051 audit can pick up the rest of the catalog.)

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

Expected: Last 5 runs show `Security Analysis / Security Gate Validation` as SUCCESS. The "Layer 8d" blocker (`--no-build` hardcode breaking editable-install consumers) is closed; see [ByronWilliamsCPA/.github PR #140](https://github.com/ByronWilliamsCPA/.github/pull/140) for the resolution.

- [ ] **Step 4: Mark the design and plan as published**

Edit `~/dev/.claude/docs/superpowers/specs/2026-05-18-safety-removal-fleet-sweep-design.md` and change `status: draft` to `status: published` in the frontmatter. Same for this plan file. The frontmatter schema for `schema_type: common` accepts `draft | in-review | published`; do not use `completed` (it will fail `scripts/validate-frontmatter.sh`). Note the completion summary in the body if you want to capture it. Commit both changes in a single commit in `~/dev/.claude`:

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

- [x] Task 1: Step 0 PR merged (`ByronWilliamsCPA/.github` PR #140). `fragrance-rater` PR #22's `Security Analysis / Security Gate Validation` passes.
- [ ] Task 2: `cookiecutter-python-template` PR merged (DONE via PR #55, 2026-05-19 04:37Z). Task 3: `cookiecutter-template-sample` PR merged (PENDING). Generating a new repo from either template produces no `safety` references in workflow files.
- [ ] Tasks 4-8: All Tier 3 PRs merged. `git grep -in safety` across affected repos returns no matches in `.github/workflows/`. (PENDING)
- [ ] Task 7: PromptCraft Tier 4 backups updated. (PENDING; folded into the PromptCraft Tier 3 PR)
- [x] Task 9: Manifest update merged (`.claude` PR #121). `CI-051` runs on the next `/repo-audit` and reports zero violations.
- [ ] Task 10: All previously-failing editable-install consumer CIs are green. (PENDING; requires Tier 3 work to finish)

Follow-up tracking (deferred from this sweep, listed in the spec's "Future work" section): file separate issues for (1) williaby `.github` centralization, (2) downstream-consumer smoke test for the reusable workflow, (3) Bandit removal analysis.
