---
schema_type: planning
title: "GitHub Activity & CI/CD Full Review (All 44 Repos)"
status: draft
owner: core-maintainer
purpose: "Analysis plan for GitHub Actions workflows, CI/CD pipelines, and branch protection rules across 44 repos in williaby and ByronWilliamsCPA orgs."
component: Development-Tools
source: "ad-hoc"
---

## Context

The user has completed an OpenSSF inventory across 44 repos in two orgs (`williaby` and
`ByronWilliamsCPA`). The next layer of analysis is understanding how GitHub Actions workflows,
CI/CD pipelines, and branch protection rules are actually configured at each repo -- specifically:
which checks run on PRs, which are blocking (required status checks) vs non-blocking, and what
branch protection rules govern merges. This report will inform decisions about where to strengthen
CI gates and which repos are currently unprotected.

---

## Step 0: Create Temp Report Directory

Create `docs/github-activity-reports/` with a `.gitignore` that matches the existing pattern used
in `docs/compliance-reports/`:

```gitignore
*
!.gitignore
```

This keeps all generated report files local only -- never committed. The directory acts as a
scratch pad for the full analysis session.

**Critical file:** [docs/compliance-reports/.gitignore](docs/compliance-reports/.gitignore) --
copy this exact gitignore pattern.

---

## Step 1: Parallel Per-Repo Analysis (7 Batches)

Dispatch **7 agents in parallel** (single message, multiple tool calls), each using the
`github-workflow-agent` subagent type. Each agent analyzes its assigned repos and writes one
markdown file per repo to `docs/github-activity-reports/`.

Output file naming convention: `{org}-{repo-slug}.md`
Example: `docs/github-activity-reports/williaby-ledgerbase.md`

### Data Each Agent Must Collect Per Repo

For each repo, using `gh api` with graceful fallback on 404s:

**1. Basic repo info:**

```bash
gh api repos/{owner}/{repo} --jq '{default_branch: .default_branch, visibility: .visibility}'
```

**2. Workflow files (list + content):**

```bash
# List workflow files
gh api repos/{owner}/{repo}/contents/.github/workflows --jq '.[].name' 2>/dev/null

# Fetch and decode each workflow file to inspect triggers
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq '.content' \
  | tr -d '\n' | base64 -d 2>/dev/null
```

From the decoded YAML, extract:

- Workflow name and file path
- Trigger events (`on:` block -- specifically `pull_request`, `push`, `schedule`, `workflow_dispatch`)
- Whether it runs on PRs (any `pull_request` or `pull_request_target` trigger)

**3. Branch protection rules:**

```bash
gh api repos/{owner}/{repo}/branches/{default_branch}/protection 2>/dev/null \
  || echo "NONE"
```

Extract:

- `required_status_checks.contexts[]` -- these are the **blocking** checks
- `required_status_checks.strict` -- whether branch must be up to date
- `required_pull_request_reviews.required_approving_review_count`
- `required_pull_request_reviews.dismiss_stale_reviews`
- `required_pull_request_reviews.require_code_owner_reviews`
- `required_linear_history.enabled`
- `allow_force_pushes.enabled`
- `enforce_admins.enabled`
- `required_signatures.enabled`

**4. Classify each workflow check:**

- **Blocking**: workflow job name appears in `required_status_checks.contexts[]`
- **Non-blocking**: workflow runs on PR but its job name is NOT in required contexts
- **No branch protection**: treat all checks as non-blocking

### Per-Repo Report Template

```markdown
# GitHub Activity Report: {org}/{repo}

**Date:** 2026-04-21
**Visibility:** public | private
**Default branch:** main | master | other
**Branch protection:** configured | none

## Branch Protection Rules

| Rule | Value |
|------|-------|
| Required approving reviews | N |
| Dismiss stale reviews | yes / no |
| Require code owner review | yes / no |
| Require linear history | yes / no |
| Restrict force pushes | yes / no |
| Require signed commits | yes / no |
| Enforce on admins | yes / no |
| Branch must be up to date | yes / no |

## GitHub Actions Workflows

| Workflow Name | File | PR Trigger? | Push Trigger? | Schedule? |
|---------------|------|-------------|---------------|-----------|
| ... | ... | yes / no | yes / no | yes / no |

## Required Status Checks (Blocking)

> Checks that must pass before a PR can be merged.

- `{job name}` (from workflow: `{filename}`)
- None configured

## Non-Required Checks (Non-Blocking)

> Checks that run on PRs but are not required to pass.

- `{job name}` (from workflow: `{filename}`)
- None

## Summary

{1-2 sentences: e.g. "No branch protection. Two workflows run on PRs (lint, test) but neither
is blocking. Merges are fully unguarded."}
```

### Batch Assignments (Workload-Balanced)

Batches are allocated by **API call workload score** (`workflow_count + 3` per repo), not by static
repo count. Each batch targets ~69 units (range: 65-70) so all 7 agents finish in roughly the same
time. Repo sizes and workflow counts were fetched via `gh api` prior to planning.

| Batch | Repos | Orgs | Workload Score |
| ----- | ----- | ---- | -------------- |
| B1 | `homelab-infra` (30), `.claude` (16), `exercise-competition` (16), `image-generation` (4), `library` (3) | BWCPA, BWCPA, williaby, williaby, williaby | **69** |
| B2 | `PromptCraft` (28), `template-sample` (16), `cookiecutter-python-template` (11), `testing` (4), `dart-frog-paludarium` (3), `OPNSense` (3), `family_office` (3) | williaby, BWCPA, BWCPA, williaby, williaby, williaby, williaby | **68** |
| B3 | `image-preprocessing-detector` (27), `maester-tests` (17), `zen-mcp-server` (10), `reference-library` (5), `.claude` (3), `homelab-agent-configs` (3) | williaby, BWCPA, williaby, BWCPA, williaby, williaby | **65** |
| B4 | `.github` (26), `fragrance-rater` (22), `xero-crypto` (10), `monte_carlo` (5), `xero-practice-management` (3), `taxdome` (3) | BWCPA, BWCPA, BWCPA, williaby, williaby, BWCPA | **69** |
| B5 | `ledgerbase` (26), `audio-processor` (23), `data_ingestor` (10), `DeQA-Doc` (5), `klipper-octoprint-configs` (3), `superslicer-configs` (3) | williaby, BWCPA, williaby, BWCPA, williaby, williaby | **70** |
| B6 | `dna` (24), `llc-manager` (23), `cookiecutter-template-sample` (9), `FISProject` (5), `CR-10-` (3), `LifeSphere` (3), `backpacking` (3) | williaby, BWCPA, BWCPA, williaby, williaby, williaby, williaby | **70** |
| B7 | `rag-processor` (24), `python-libs` (23), `pp-security-master` (8), `magg` (7), `OPNS` (3), `GCS` (3) | BWCPA, BWCPA, williaby, williaby, williaby, williaby | **68** |

**Score formula:** `workflow_count + 3` per repo (3 = fixed API calls: repo-info + workflow-list +
branch-protection, regardless of workflow count). Workload data fetched 2026-04-21.

**Note for agents:** Each batch contains repos from both orgs. The agent must set `OWNER`
correctly per repo rather than assuming a single org for the whole batch.

---

## Step 2: Portfolio Analysis

After all 7 batches complete, dispatch a **single synthesis agent** that reads all
`docs/github-activity-reports/*.md` files and writes
`docs/github-activity-reports/00-comprehensive-analysis.md`.

The `00-` prefix causes it to sort to the top of directory listings.

### Full Report Structure

```markdown
# GitHub Activity & CI/CD Comprehensive Analysis

**Date:** 2026-04-21
**Scope:** 43 repos across williaby (27) and ByronWilliamsCPA (16)
**Generated from:** Individual per-repo reports in this directory

---

## Executive Summary

{3-5 sentences covering the state of CI/CD and branch protection across the portfolio.}

---

## Portfolio-Wide Stats

| Metric | Count | % of 43 |
|--------|-------|---------|
| Repos with branch protection | N | N% |
| Repos with ≥1 blocking check | N | N% |
| Repos with CI workflows | N | N% |
| Repos with PR-triggered workflows | N | N% |
| Repos with NO workflows | N | N% |
| Repos with NO protection AND NO workflows | N | N% |

---

## Repo-by-Repo Summary Table

| Repo | Org | Visibility | Branch Protection | Blocking Checks | Non-Blocking Checks | PR Workflows |
|------|-----|------------|-------------------|-----------------|---------------------|--------------|
...

---

## Common CI/CD Patterns

{Identify workflow names or job names that appear across multiple repos. E.g. "9 repos use a
`CI / test` job; 4 require it as a blocking check."}

---

## Branch Protection Coverage

### Fully Protected (all three: reviews + required checks + admin enforcement)
...

### Partially Protected
...

### Unprotected
...

---

## Blocking vs Non-Blocking Gap Analysis

{Repos that have CI workflows running on PRs but zero required status checks -- the "all
theater, no enforcement" category.}

---

## Repos with Zero CI/CD

{Repos with no `.github/workflows/` at all -- ranked by Scorecard score where available.}

---

## Prioritized Recommendations

### Critical (no protection, public, active development)
1. ...

### Important (partial protection, missing key checks)
1. ...

### Suggested (private repos, low-activity)
1. ...
```

---

## Step 3: Cleanup (Optional)

After the user reviews the portfolio report, the temp directory can be deleted since
everything is gitignored and local-only. No cleanup action is required during execution.

---

## Verification

After all agents complete:

1. Count report files: `ls docs/github-activity-reports/ | wc -l` -- expect 44 per-repo files + 1 synthesis = 45 total
2. Check for missing repos: compare filenames against the 44-repo inventory
3. Spot-check 2-3 repos manually using `gh api` to confirm the data in individual reports is accurate
4. Confirm gitignore is working: `git status docs/github-activity-reports/` -- should show no tracked files

---

## Critical Files

| File | Role |
| ---- | ---- |
| [docs/compliance-reports/.gitignore](docs/compliance-reports/.gitignore) | Gitignore pattern to copy |
| `.claude/agents/github-workflow-agent.md` | Agent definition for batches 1-7 |
| `.claude/agents/ossf-compliance-auditor.md` | Reference for `gh api` patterns used in this project |
| `docs/github-activity-reports/` | New temp directory (to be created) |
| `docs/github-activity-reports/00-comprehensive-analysis.md` | Final synthesis output |
