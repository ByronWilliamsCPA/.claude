---
schema_type: planning
title: "Sprint Plan: GitHub Workflow and Branch Protection Standardization"
status: draft
owner: core-maintainer
source: "docs/reference/github-workflow-audit.md"
purpose: "Standardize GitHub workflows and branch protections across all 44 repos in ByronWilliamsCPA and williaby orgs."
component: Development-Tools
tags:
  - compliance
  - planning
  - github_actions
  - ci_cd
---

## Context

Across both orgs (ByronWilliamsCPA: 17 repos, williaby: 27 repos), GitHub workflows and
branch protections are inconsistently configured. The reference implementation is the
`ByronWilliamsCPA/.claude` repo, which has the full standard applied and is verified
through CI. This sprint plan standardizes all 44 repos one item at a time, establishing
a repeatable audit-and-remediate loop for each protection or workflow. It also creates
a structured process for evaluating non-standard items and deciding their fate.

**Source of truth for current repo state:** `docs/reference/github-repos.md`
**Gold standard repo:** `ByronWilliamsCPA/.claude` (13 active workflows, full branch protection)
**Relevant standards:** `docs/OPENSSF_COMPLIANCE.md`, `.claude/standards/git-workflow.md`

---

## Repo Classification Taxonomy

Established in Sprint 0; referenced by all subsequent sprints to determine which
standards apply to each repo.

| Axis | Values |
|---|---|
| Language | `python` / `non-python` |
| Visibility | `public` / `private` |
| Publishing | `published` (PyPI, Docker, GitHub Releases) / `internal` |
| Documentation | `has-docs` (MkDocs structure) / `no-docs` |
| Activity | `active` / `inactive` |

All repos receive full remediation. Classification determines **which tier** of
standards applies, not whether to skip a repo.

---

## Standards Catalog

### Tier Definitions

| Tier | Applies To | Items |
|---|---|---|
| **Universal** | All 44 repos | BP-1 through BP-5, WF-1, WF-2, WF-3, WF-4 |
| **Public** | Public repos only | WF-5, WF-6, WF-7 |
| **Python** | Python repos only | WF-8, WF-9, WF-10, WF-11 |
| **Published** | Repos that publish releases or packages | WF-12, WF-13 |
| **Has-Docs** | Repos with MkDocs structure | WF-14 |

### Branch Protection Standards (Universal)

| ID | Standard | Target State |
|---|---|---|
| BP-1 | No force pushes | Disabled on `main` |
| BP-2 | No branch deletions | Disabled on `main` |
| BP-3 | Linear history | Required on `main` |
| BP-4 | Required commit signatures | Enabled on `main` |
| BP-5 | Enforce admins + required status checks | No admin bypass; at least one CI check required |
| BP-6 | Required PR reviews | 0 reviews (solo-dev exception; restore to 1 when a second contributor joins) |

Required status checks (part of BP-5 setup) vary by repo type and are defined
per-repo in Sprint 0. At minimum: one CI gate check must be listed. For repos
with no CI yet, a placeholder `repo-health` check is acceptable until the CI
sprint lands.

**BP-6 solo-dev exception:** `required_approving_review_count=0` is intentional.
As a solo developer you cannot approve your own PRs. The protection still requires
passing all status checks before merge. When a second contributor joins, restore
this count to 1 across all repos. See the OSSF review gate memory entry for the
rationale. This setting means the Scorecard Code-Review check will score below
10/10 until restored; that gap is accepted and documented.

### Workflow Standards

| ID | Workflow | File | Tier |
|---|---|---|---|
| WF-1 | REUSE compliance | `reuse.yml` | Universal |
| WF-2 | Dependabot configuration | `dependabot.yml` | Universal |
| WF-3 | Security analysis | `security-analysis.yml` | Universal |
| WF-4 | PR validation | `pr-validation.yml` | Universal |
| WF-5 | CodeQL analysis | `codeql.yml` | Public |
| WF-6 | SBOM and security scan | `sbom.yml` | Public |
| WF-7 | OpenSSF Scorecard | `scorecard.yml` | Public |
| WF-8 | CI gate | `ci.yml` | Python |
| WF-9 | Python compatibility matrix | `python-compatibility.yml` | Python |
| WF-10 | SonarCloud analysis | `sonarcloud.yml` | Python |
| WF-11 | Coverage reporting (Qlty) | `coverage.yml` | Python |
| WF-12 | Semantic release | `release.yml` | Published |
| WF-13 | Release signing (Cosign) | `release-sign.yml` | Published |
| WF-14 | MkDocs documentation | `docs.yml` | Has-Docs |

Template source for all workflows: `ByronWilliamsCPA/.claude/.github/workflows/`

---

## Sprint Sequence

23 sprints in priority order. Branch protections first (they are the safety floor),
then universal workflows, then tier-scoped workflows, then evaluation.

### Sprint 0: Inventory and Classification

**Status: COMPLETE (2026-05-04)**

**Goal:** Produce a complete audit table before any remediation begins.

**Actions:**
1. For each of the 44 repos, run `gh api repos/ORG/REPO/branches/main/protection`
   and record current branch protection state.
2. List all `.github/workflows/*.yml` files per repo.
3. Classify each repo across all 5 axes (language, visibility, publishing, docs, activity).
4. For each repo, compute which BP and WF items are in scope.
5. Write the audit table to `docs/reference/github-workflow-audit.md`.

**Output:** A row-per-repo, column-per-standard matrix showing PASS / FAIL / N/A for
all 20 items (6 BP + 14 WF). This is the baseline. All subsequent sprints use this to
prioritize which repos need work.

**Sprint 0 findings (key stats):**
- Repos with all 6 BP PASS: 3/44 (BW/.claude, BW/homelab-infra, W/image-preprocessing-detector)
- WF-11 (coverage.yml) and WF-13 (release-sign.yml): 0% pass rate across all applicable repos
  (repos use `codecov.yml`/`qlty.yml` and `slsa-provenance.yml` instead; EV sprints will evaluate)
- Special cases: `homelab-agent-configs` (no `main` branch), `xero-crypto` (master branch),
  `testing`/williaby (non-standard default branch)
- `docs/reference/github-repos.json` and `docs/reference/github-repos.md` updated with Sprint 0 data

---

### Sprint BP-1: Disable Force Pushes on Main

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Check:** `gh api repos/ORG/REPO/branches/main/protection | jq '.allow_force_pushes.enabled'`
**Target state:** `false`
**Remediation used:** PUT (not PATCH) with full minimal payload since 33/44 repos had no prior
protection (PATCH returns 404 when no protection exists):
`echo '{"required_status_checks":null,"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null,"allow_force_pushes":false,"allow_deletions":false}' | gh api -X PUT repos/ORG/REPO/branches/BRANCH/protection --input -`

---

### Sprint BP-2: Disable Branch Deletions on Main

**Status: COMPLETE (2026-05-04). 43/44 PASS. Covered by the BP-1 PUT payload.**

**Tier:** Universal (44 repos)
**Check:** `gh api ... | jq '.allow_deletions.enabled'`
**Target state:** `false`
**Note:** The BP-1 PUT payload included `allow_deletions: false`, remediating BP-2 simultaneously.
No separate sprint execution required.

---

### Sprint BP-3: Require Linear History

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Check:** `gh api ... | jq '.required_linear_history.enabled'`
**Target state:** `true`
**Remediation used:** GET current protection + PUT with required_linear_history=true added. Script at /tmp/bp3_remediate.py.
**Note:** Repos with merge commits in recent history need a squash-merge policy set
before enabling linear history or existing PR merges will fail.

---

### Sprint BP-4: Require Signed Commits

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Check:** `gh api repos/ORG/REPO/branches/main/protection/required_signatures | jq '.enabled'`
**Target state:** `true`
**Remediation used:** `gh api -X POST repos/ORG/REPO/branches/BRANCH/protection/required_signatures` (no body required).
**Note:** Contributors must have GPG or SSH signing configured locally. Flag any repos
where the contributor list is broader than the primary account.

---

### Sprint BP-5: Enforce Admins and Require Status Checks

**Tier:** Universal (44 repos)
**Goal:** No admin bypass; at least one required status check per repo.
**Check:** `jq '.enforce_admins.enabled'` and `jq '.required_status_checks.contexts'`
**Target state:** enforce admins = `true`; contexts = at minimum the repo's CI gate check name
**Note:** The specific check name differs by repo type. Python repos require `CI Gate`.
Non-Python repos without CI yet require adding a minimal `repo-health` workflow first.
Document the status check name chosen per repo in the audit table.
This sprint does NOT configure PR review counts; that is handled separately in BP-6.

---

### Sprint BP-6: Required PR Reviews (Solo-Dev Exception)

**Tier:** Universal (44 repos)
**Goal:** Explicitly configure PR review requirements to match the documented solo-dev policy.
**Check:** `gh api repos/ORG/REPO/branches/main/protection | jq '.required_pull_request_reviews.required_approving_review_count'`
**Target state:** `0` (solo-dev exception; documented and accepted)
**Remediation:** PATCH `required_approving_review_count=0` via branch protection update.
**Note:** As a solo developer you cannot approve your own PRs, so requiring 1+ reviews
would block all merges. Setting this to 0 means status checks alone gate the merge.
When a second contributor joins, run a follow-up sprint to restore this to 1 across
all repos. Track the OpenSSF Scorecard Code-Review score gap in `docs/OPENSSF_COMPLIANCE.md`
as an accepted exception until that change is made.

---

### Sprint WF-1: REUSE Compliance Workflow

**Tier:** Universal (44 repos)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/reuse.yml`
**Required companion:** `LICENSES/` directory with appropriate SPDX license files and
`REUSE.toml` or `.reuse/dep5` at repo root.
**Verify:** Workflow runs on push to main and on PRs; exits non-zero on missing headers.

---

### Sprint WF-2: Dependabot Configuration

**Tier:** Universal (44 repos)
**File:** `.github/dependabot.yml`
**Minimum config:** At minimum, `github-actions` ecosystem enabled with weekly schedule.
Python repos also add `pip` ecosystem. Docker repos add `docker`.
**Template:** Copy from `ByronWilliamsCPA/.claude/.github/dependabot.yml` and
adjust `package-ecosystem` entries for each repo's stack.

---

### Sprint WF-3: Security Analysis Workflow

**Tier:** Universal (44 repos)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/security-analysis.yml`
**Covers:** Trivy or equivalent for dependency and container scanning; runs on
push/PR and on a weekly schedule.

---

### Sprint WF-4: PR Validation Workflow

**Tier:** Universal (44 repos)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/pr-validation.yml`
**Covers:** Conventional commit format check on PR title; label enforcement;
PR description non-empty check.

---

### Sprint WF-5: CodeQL Analysis

**Tier:** Public repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/codeql.yml`
**Language matrix:** Set `language` array to match repo stack (python, javascript, etc.)
**Trigger:** Push to main, PRs, and weekly schedule.
**Note:** Free for public repos. Private repos require GitHub Advanced Security license;
skip private repos and document the exception in `docs/known-vulnerabilities.md`.

---

### Sprint WF-6: SBOM and Security Scan

**Tier:** Public repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/sbom.yml`
**Covers:** SBOM generation with anchore/sbom-action; attaches SBOM as release asset
and uploads to GitHub dependency graph.

---

### Sprint WF-7: OpenSSF Scorecard

**Tier:** Public repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/scorecard.yml`
**Trigger:** Push to main and weekly schedule.
**Target score:** Aim for 7.0+ across all public repos; document gaps below that
threshold in `docs/OPENSSF_COMPLIANCE.md`.

---

### Sprint WF-8: CI Gate (Python)

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/ci.yml`
**Gate sequence:** ruff format, ruff lint, basedpyright, pytest (with coverage threshold).
**Note:** Each repo may have different test paths or coverage thresholds. Review
`pyproject.toml` before copying the template and adjust tool config sections.
This workflow's job name must match the string registered as a required status check
in BP-5. Coordinate with Sprint BP-5 if BP-5 landed first with a placeholder.

---

### Sprint WF-9: Python Compatibility Matrix

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/python-compatibility.yml`
**Covers:** Matrix build across the supported Python version range (currently 3.10, 3.12, 3.14).
**Note:** Consult `pyproject.toml` `requires-python` for each repo's declared range.

---

### Sprint WF-10: SonarCloud Analysis

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/sonarcloud.yml`
**Prerequisite:** Each repo must be registered in the SonarCloud organization and have
a valid `SONAR_TOKEN` secret. Verify via SonarCloud dashboard before the sprint.
**Note:** SonarCloud MCP servers run on ports 8090 (ByronWilliamsCPA) and 8091 (williaby);
use them to verify project keys and quality gate status.

---

### Sprint WF-11: Coverage Reporting (Qlty)

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/coverage.yml`
**Covers:** Upload coverage XML to Qlty for trend tracking and PR delta comments.
**Prerequisite:** Repo must be registered in Qlty and `QLTY_COVERAGE_TOKEN` must be
set as a repo secret. Qlty and Codecov coexist; do not replace Codecov if present.

---

### Sprint WF-12: Semantic Release

**Tier:** Published repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/release.yml`
**Covers:** Conventional-commit-driven version bumps, CHANGELOG generation, GitHub
Release creation, PyPI publish (if applicable).
**Prerequisite:** `release.config.js` or `.releaserc` must exist in repo root; verify
branch and plugin config before enabling.

---

### Sprint WF-13: Release Signing (Cosign)

**Tier:** Published repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/release-sign.yml`
**Covers:** Cosign keyless signing of release artifacts; SLSA provenance attestation.
**Critical constraint:** The signing workflow must download pre-built artifacts from
the release workflow output. It must NEVER rebuild from source. Attestation must match
exactly what PyPI or the release asset received (see SLSA provenance pattern in memory).

---

### Sprint WF-14: MkDocs Documentation

**Tier:** Has-Docs repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/docs.yml`
**Covers:** Build MkDocs site on PRs (verify no broken links); deploy to GitHub Pages
on push to main.
**Prerequisite:** `mkdocs.yml` must exist at repo root and pass the mkdocs-auditor check.

---

### Sprint EV-1: Non-Standard Workflow Evaluation (ByronWilliamsCPA)

**Goal:** For each workflow in ByronWilliamsCPA repos that is NOT one of WF-1 through
WF-14, evaluate its fate.

**Process per non-standard workflow:**
1. Document what the workflow does and which repos have it.
2. Apply the decision matrix below.
3. Record the decision and rationale in `docs/reference/github-workflow-audit.md`.

**Decision matrix:**

| Condition | Decision |
|---|---|
| Useful to 3+ repos and not covered by existing standards | Add to org standards; create a new WF sprint |
| Useful to exactly 1-2 repos for valid repo-specific reasons | Keep as standalone; document in repo-level README |
| Redundant with an existing standard workflow | Remove; migrate any unique logic into the standard |
| Obsolete, broken, or unmaintained | Remove |

**Output:** List of new WF sprints to add (if any), list of removals, and updated audit table.

---

### Sprint EV-2: Non-Standard Workflow Evaluation (williaby)

Same process as EV-1, applied to the williaby org's non-standard workflows.

**Additional consideration for williaby:** This org includes personal and family office
repos with potentially unique requirements (genealogy tooling, personal finance, etc.).
Standalone decisions are more likely here; apply the same matrix but expect more
"keep as standalone" outcomes.

---

## Per-Sprint Execution Format

Each sprint (BP and WF) follows this repeatable pattern:

1. **Audit:** For each of the 44 repos (filtered by tier), check current state using
   `gh api` or by reading the workflow file. Mark PASS / FAIL / N/A in the audit table.

2. **Triage:** Sort failing repos. Public repos and active Python repos first.
   Inactive repos last.

3. **Remediate:** For branch protection sprints, use `gh api -X PATCH` to set the rule.
   For workflow sprints, copy the template, adjust repo-specific parameters, and open
   a PR to the repo's main branch.

4. **Verify:** After merging or applying the change, re-run the audit check for that
   repo to confirm PASS.

5. **Update audit table:** Mark the item as PASS in `docs/reference/github-workflow-audit.md`
   and note the date remediated.

**Tool:** Use the `github-workflow-agent` subagent for branch protection API calls.
Use `git-workflow-agent` for PR creation. Run sprints with the `dispatching-parallel-agents`
skill when remediating multiple repos in the same sprint.

---

## Org-Level Standards Definition

After Sprint EV-1 and EV-2, update `docs/OPENSSF_COMPLIANCE.md` with the final
canonical list of standard workflows. Add a new section: **Org Workflow Registry**
listing each standard workflow ID, its tier, its template source, and required secrets.
This becomes the authoritative reference for all future repo creation via cookiecutter
templates.

---

## Verification Approach

**End-of-sprint check for BP sprints:**
```bash
gh api repos/ORG/REPO/branches/main/protection | jq '{
  force_pushes: .allow_force_pushes.enabled,
  deletions: .allow_deletions.enabled,
  linear: .required_linear_history.enabled,
  admins: .enforce_admins.enabled,
  checks: .required_status_checks.contexts,
  reviews_required: .required_pull_request_reviews.required_approving_review_count
}'
```

**End-of-sprint check for WF sprints:**
```bash
gh workflow list --repo ORG/REPO | grep -i "<workflow-name>"
gh run list --repo ORG/REPO --workflow=<file>.yml --limit 1
```

**Full audit refresh:** After every 5 sprints, re-run the Sprint 0 audit script to
regenerate `docs/reference/github-workflow-audit.md` and verify cumulative progress.

**OpenSSF Scorecard:** After all public-tier sprints complete, run the Scorecard workflow
manually on each public repo and compare against the baseline recorded in Sprint 0.
Target: all public repos reach 7.0+ overall score.

---

## Sprint Summary Table

| Sprint | ID | Target | Tier | Status |
|---|---|---|---|---|
| 0 | Inventory | Full audit + classification | All | DONE 2026-05-04 |
| 1 | BP-1 | No force pushes | Universal | DONE 2026-05-04 |
| 2 | BP-2 | No branch deletions | Universal | DONE 2026-05-04 |
| 3 | BP-3 | Linear history | Universal | DONE 2026-05-04 |
| 4 | BP-4 | Required signatures | Universal | DONE 2026-05-04 |
| 5 | BP-5 | Enforce admins + status checks | Universal | pending |
| 6 | BP-6 | PR reviews = 0 (solo-dev exception) | Universal | pending |
| 7 | WF-1 | REUSE compliance | Universal | pending |
| 8 | WF-2 | Dependabot | Universal | pending |
| 9 | WF-3 | Security analysis | Universal | pending |
| 10 | WF-4 | PR validation | Universal | pending |
| 11 | WF-5 | CodeQL | Public | pending |
| 12 | WF-6 | SBOM | Public | pending |
| 13 | WF-7 | OpenSSF Scorecard | Public | pending |
| 14 | WF-8 | CI gate | Python | pending |
| 15 | WF-9 | Python compatibility | Python | pending |
| 16 | WF-10 | SonarCloud | Python | pending |
| 17 | WF-11 | Coverage (Qlty) | Python | pending |
| 18 | WF-12 | Semantic release | Published | pending |
| 19 | WF-13 | Release signing | Published | pending |
| 20 | WF-14 | MkDocs docs | Has-Docs | pending |
| 21 | EV-1 | Non-standard eval (ByronWilliamsCPA) | All | pending |
| 22 | EV-2 | Non-standard eval (williaby) | All | pending |
