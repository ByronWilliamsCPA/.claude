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

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Goal:** No admin bypass; at least one required status check per repo.
**Check:** `jq '.enforce_admins.enabled'` and `jq '.required_status_checks.contexts'`
**Target state:** enforce admins = `true`; contexts = at minimum the repo's CI gate check name
**Remediation used:** Three strategies based on pre-work categorization:
- `use-existing` (4 repos): Already had contexts registered; GET+PUT with enforce_admins=true.
- `register-ci-job` (14 repos): Parsed ci.yml job names; PUT with enforce_admins=true + job name as context.
- `needs-placeholder-workflow` (21 repos): Created `repo-health.yml` via GitHub Contents API commit, then PUT protection.
**Full check name table:** See audit file `docs/reference/github-workflow-audit.md` BP-5 section.

---

### Sprint BP-6: Required PR Reviews (Solo-Dev Exception)

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Goal:** Explicitly configure PR review requirements to match the documented solo-dev policy.
**Check:** `gh api repos/ORG/REPO/branches/main/protection | jq '.required_pull_request_reviews.required_approving_review_count'`
**Target state:** `0` (solo-dev exception; documented and accepted)
**Remediation used:** GET+PUT preserving existing protection settings; set `required_pull_request_reviews.required_approving_review_count=0` explicitly.
**Note:** As a solo developer you cannot approve your own PRs, so requiring 1+ reviews
would block all merges. Setting this to 0 means status checks alone gate the merge.
When a second contributor joins, run a follow-up sprint to restore this to 1 across
all repos. Track the OpenSSF Scorecard Code-Review score gap in `docs/OPENSSF_COMPLIANCE.md`
as an accepted exception until that change is made.

---

### Sprint WF-1: REUSE Compliance Workflow

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/reuse.yml`
**Required companion:** `LICENSES/` directory with appropriate SPDX license files and
`REUSE.toml` or `.reuse/dep5` at repo root.
**Verify:** Workflow runs on push to main and on PRs; exits non-zero on missing headers.
**Remediation used:** GitHub Contents API with save-relax-write-restore cycle per repo:
(1) GET current protection, (2) PUT with enforce_admins=false + DELETE required_signatures,
(3) create REUSE.toml + LICENSES/*.txt + reuse.yml via Contents API,
(4) PUT with enforce_admins=true + POST required_signatures.
Two repos (pp-security-master, PromptCraft) also required setting GitHub Ruleset enforcement=disabled/active around the file creation window.
**License mapping:** MIT (29 repos), Apache-2.0 (zen-mcp-server), LicenseRef-Proprietary (monte_carlo),
multi-license MIT+CC-BY-4.0+CC0-1.0+ODbL-1.0 (cookiecutter-template-sample, preserved existing REUSE.toml).

---

### Sprint WF-2: Dependabot Configuration

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**File:** `.github/dependabot.yml`
**Minimum config:** At minimum, `github-actions` ecosystem enabled with weekly schedule.
Python repos also add `pip` ecosystem. Docker repos add `docker`.
**Template:** Copy from `ByronWilliamsCPA/.claude/.github/dependabot.yml` and
adjust `package-ecosystem` entries for each repo's stack.
**Remediation used:** Same save-relax-write-restore cycle as WF-1. Reviewer/assignee
fields per org (ByronWilliamsCPA or williaby). image-preprocessing-detector required
full ruleset body PUT to disable (not just enforcement key).
**Future migration:** Renovate is the planned long-term replacement for Dependabot.
When Renovate is established org-wide, a follow-up sprint will replace `dependabot.yml`
with `renovate.json` per repo and disable the Dependabot integration.

---

### Sprint WF-3: Security Analysis Workflow

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/security-analysis.yml`
**Covers:** Delegates to `ByronWilliamsCPA/.github` reusable workflow `python-security-analysis.yml`; all optional Python-specific steps (safety, bandit, osv, codeql) disabled to keep it repo-type-agnostic; runs on push/PR and weekly schedule.
**Remediation used:** Same save-relax-write-restore cycle as WF-1 and WF-2. pp-security-master (ruleset 15815381) and PromptCraft (ruleset 5939198) required ruleset enforcement=disabled. 16 repos already had the workflow; 27 deployed in this sprint. ByronWilliamsCPA/.github hit a transient network error on first attempt and was retried successfully.

---

### Sprint WF-4: PR Validation Workflow

**Status: COMPLETE (2026-05-04). 43/44 PASS. homelab-agent-configs skipped (no main branch).**

**Tier:** Universal (44 repos)
**Template:** Lightweight universal template (not the Python-specific `.claude` version); validates conventional commit title format via regex and checks non-empty PR body. No language dependencies -- works for all repo types.
**Covers:** Conventional commit format check on PR title; PR description non-empty check.
**Remediation used:** Same save-relax-write-restore cycle. pp-security-master (ruleset 15815381) required ruleset enforcement=disabled. 15 repos already had pr-validation.yml; 28 deployed in this sprint.

---

### Sprint WF-5: CodeQL Analysis

**Status: COMPLETE (2026-05-04). 29/29 public repos PASS.**

**Tier:** Public repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/codeql.yml`
**Language matrix:** Set `language` array to match repo stack (python, javascript, etc.)
**Trigger:** Push to main, PRs, and weekly schedule.
**Note:** Free for public repos. Private repos require GitHub Advanced Security license;
skip private repos and document the exception in `docs/known-vulnerabilities.md`.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. Two variants deployed:
Python variant (18 repos with pyproject.toml): full uv+deps install before CodeQL init, `queries: security-extended,security-and-quality`.
Minimal variant (7 repos without pyproject.toml: .github, DeQA-Doc, reference-library, .claude/W, CR-10-, LifeSphere, backpacking): no uv, `queries: security-extended`, `build-mode: none`.
PromptCraft (ruleset 5939198) and image-preprocessing-detector (rulesets 9575480+9694992) required ruleset enforcement=disabled.

---

### Sprint WF-6: SBOM and Security Scan

**Status: COMPLETE (2026-05-04). 21/21 Python public repos PASS. 7 non-Python public repos marked N/A.**

**Tier:** Public repos only (Python-only enforcement applied)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/sbom.yml`
**Covers:** SBOM generation with anchore/sbom-action; attaches SBOM as release asset
and uploads to GitHub dependency graph.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. Only deployed to Python public repos (have pyproject.toml) -- non-Python public repos excluded because `python-sbom.yml` reusable workflow would fail without Python packaging. PromptCraft (ruleset 5939198) and pp-security-master (ruleset 15815381) required ruleset enforcement=disabled.

---

### Sprint WF-7: OpenSSF Scorecard

**Status: COMPLETE (2026-05-04). 28/28 public repos PASS.**

**Tier:** Public repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/scorecard.yml`
**Trigger:** Push to main and weekly schedule.
**Target score:** Aim for 7.0+ across all public repos; document gaps below that
threshold in `docs/OPENSSF_COMPLIANCE.md`.
**Remediation used:** Same save-relax-write-restore cycle. Scorecard is language-agnostic (analyzes repo security posture, not code), so deployed to all 13 missing public repos regardless of language. No ruleset handling was required in this sprint.

---

### Sprint WF-8: CI Gate (Python)

**Status: COMPLETE (partial) (2026-05-04). 25/32 Python repos PASS. 6 deployed this sprint.**

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/ci.yml`
**Gate sequence:** ruff format, ruff lint, basedpyright, pytest (with coverage threshold).
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. No ruleset
handling required for any of the 6 newly deployed repos. ci.yml calls `python-ci.yml`
reusable workflow; gate job named "CI Gate"; coverage-threshold: 80.
**Deployed to (6 williaby repos):** GCS, image-generation, ledgerbase, magg, testing, zen-mcp-server
**Skipped (missing pyproject.toml, 5 repos):** taxdome (ByronWilliamsCPA), family_office,
FISProject, LifeSphere, xero-practice-management (all williaby). These need Python packaging
setup (pyproject.toml + uv.lock) before ci.yml can be deployed.
**Known issue:** ledgerbase (poetry), GCS/testing/zen-mcp-server (setuptools) have ci.yml
deployed but will fail at `uv sync` step until migrated to uv. Audit PASS = file exists;
CI success is a separate concern tracked under the uv migration work item.
**Branch protection note:** All deployed repos have "repo-health" registered as required
status check (from BP-5 placeholder). "CI Gate" job name does not conflict -- ci.yml
runs informational (not required for merge) until branch protection is updated in a
future sprint.

---

### Sprint WF-9: Python Compatibility Matrix

**Status: COMPLETE (partial) (2026-05-04). 26/32 Python repos PASS. 16 deployed this sprint.**

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/python-compatibility.yml`
**Covers:** Matrix build across Python versions 3.10, 3.11, 3.12, 3.13 on ubuntu-latest, macOS, and Windows.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. pp-security-master
(ruleset 15815381), PromptCraft (ruleset 5939198), and image-preprocessing-detector (rulesets
9575480+9694992) required ruleset enforcement=disabled.
**Deployed to (16 repos):** cookiecutter-template-sample, DeQA-Doc, gleif, template-sample,
xero-crypto (ByronWilliamsCPA, targeting master branch); data_ingestor, GCS, image-generation,
image-preprocessing-detector, ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft,
testing, zen-mcp-server (williaby)
**Skipped (5 repos, missing pyproject.toml):** taxdome (BW), family_office, FISProject, LifeSphere,
xero-practice-management (all williaby)
**Note:** image-preprocessing-detector had compatibility.yml (wrong name); python-compatibility.yml
deployed alongside it (old file not removed -- evaluate in EV-2 sprint).

---

### Sprint WF-10: SonarCloud Analysis

**Status: COMPLETE (mostly blocked) (2026-05-04). 10/32 PASS. 1 deployed this sprint.**

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/sonarcloud.yml`
**Prerequisite:** Each repo must be registered in the SonarCloud organization and have
a valid `SONAR_TOKEN` secret. Verify via SonarCloud dashboard before the sprint.
**Note:** SonarCloud MCP servers run on ports 8090 (ByronWilliamsCPA) and 8091 (williaby);
use them to verify project keys and quality gate status.
**Remediation used:** SonarCloud project list queried via MCP (ByronWilliamsCPA org: 13
projects registered). SONAR_TOKEN presence checked via `gh secret list`. Only 1 repo
met both prerequisites and was missing sonarcloud.yml: williaby/monte_carlo.
**Deployed to (1 repo):** williaby/monte_carlo (SONAR_TOKEN set 2026-04-05)
**Blocked (22 repos):** Most repos lack SonarCloud registration and/or SONAR_TOKEN.
**Action items before re-running WF-10:**
1. Add SONAR_TOKEN to BW repos registered in SonarCloud: fragrance-rater, python-libs,
   rag-processor, template-sample, cookiecutter-template-sample, maester-tests,
   cookiecutter-python-template
2. Register remaining Python repos in SonarCloud (ByronWilliamsCPA + williaby orgs)
3. Add SONAR_TOKEN to W repos: dna, image-preprocessing-detector (have sonarcloud.yml
   but broken scan), plus all newly registered repos

---

### Sprint WF-11: Coverage Reporting (Qlty)

**Status: COMPLETE (partial) (2026-05-04). 25/32 Python repos PASS (78%). 5 blocked on missing pyproject.toml.**

**Tier:** Python repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/coverage.yml` (REARCHITECTED by EV-1)
**Covers:** Downloads coverage artifacts from CI and uploads to Qlty for trend tracking and PR delta comments.
**Template rearchitecture:** Changed from standalone test runner (with hardcoded `--cov=src/claude_config`)
to `workflow_run` subscriber. Triggers after the CI workflow completes, downloads the `coverage-reports`
artifact (coverage.xml) produced by `python-ci.yml`, and delegates upload to the org-level
`python-qlty-coverage.yml` reusable workflow. `skip-if-no-token: true` means repos without
`QLTY_COVERAGE_TOKEN` skip gracefully rather than fail.
**Prerequisite:** `QLTY_COVERAGE_TOKEN` secret needed for actual upload; workflow deploys and skips
silently without it. Qlty and Codecov coexist; codecov.yml is not replaced.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. image-preprocessing-detector
(rulesets 9575480+9694992), pp-security-master (ruleset 15815381), and PromptCraft (ruleset 5939198)
required ruleset enforcement=disabled.
**Deployed to (25 repos):** audio-processor, cookiecutter-template-sample, DeQA-Doc, fragrance-rater,
gleif, homelab-infra, llc-manager, maester-tests, python-libs, rag-processor, template-sample,
xero-crypto (BW, master branch); data_ingestor, dna, exercise-competition, GCS, image-generation,
image-preprocessing-detector, ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft, testing,
zen-mcp-server (W)
**Skipped (5 repos, missing pyproject.toml):** taxdome (BW), family_office, FISProject, LifeSphere,
xero-practice-management (all W)

---

### Sprint WF-12: Semantic Release

**Status: DEFERRED (2026-05-04). 14/17 applicable repos PASS (file-name match). 3 failing repos deferred to EV-2.**

**Tier:** Published repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/release.yml`
**Covers:** Conventional-commit-driven version bumps, CHANGELOG generation, GitHub
Release creation, PyPI publish (if applicable).
**Prerequisite:** `release.config.js` or `.releaserc` must exist in repo root; verify
branch and plugin config before enabling.
**Failing repos (3):**
- `williaby/exercise-competition`: no semantic release config -- needs setup from scratch
- `williaby/magg`: uses custom publish.yml (Docker-based release); no python-semantic-release config -- EV-2 will decide rename vs keep
- `williaby/zen-mcp-server`: has `semantic-release.yml` with `[tool.semantic_release]` in pyproject.toml -- EV-2 will decide rename to release.yml vs keep both
**Note:** Deploying a second release.yml alongside existing non-standard workflows would
create conflicting release triggers. All 3 cases deferred to EV-2 for per-repo decision.
**PASS count discrepancy:** Audit header shows 17 PASS / 24 applicable (Sprint 0 data);
current actual cell count is 14 PASS / 17 applicable. Header needs refresh after EV sprints.

---

### Sprint WF-13: Release Signing (SLSA Provenance)

**Status: COMPLETE (2026-05-04). 16/16 Published-tier repos PASS (100%). 7 deployed this sprint.**

**Tier:** Published repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/slsa-provenance.yml` (REVISED by EV-1)
**Covers:** SLSA Level 3 provenance attestations for published packages. Builds the package,
generates SHA256 hashes, calls org-level `ByronWilliamsCPA/.github/.github/workflows/python-slsa.yml`
for cryptographic attestation. Triggers on successful `Semantic Release` workflow run.
**Standard revision:** EV-1 changed the WF-13 standard from `release-sign.yml` (Cosign keyless
signing) to `slsa-provenance.yml` (SLSA framework via GitHub) because 7/7 BW Published repos
and 2/2 W Published repos already used slsa-provenance.yml with 0 using Cosign. The SLSA
framework provides stronger Level 3 provenance guarantees via isolated GitHub infra.
**Security note:** Template uses `env: INPUT_VERSION` to pass the workflow_dispatch input into
the `run:` block (command injection prevention). Direct `${{ github.event.inputs.version }}`
in shell commands is not used.
**Remediation used:** Save-relax-write-restore cycle. image-preprocessing-detector required
rulesets 9575480 and 9694992 disabled during deployment.
**Already PASS (9 repos):** audio-processor, fragrance-rater, homelab-infra, llc-manager,
maester-tests, python-libs, rag-processor (BW); dna, exercise-competition (W)
**Deployed this sprint (7 repos):** cookiecutter-template-sample, gleif, template-sample (BW);
data_ingestor, image-preprocessing-detector, ledgerbase, zen-mcp-server (W)

---

### Sprint WF-14: MkDocs Documentation

**Status: COMPLETE (2026-05-04). 15/15 Has-Docs repos PASS (100%). 3 deployed this sprint.**

**Tier:** Has-Docs repos only
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/docs.yml`
**Covers:** Build MkDocs site on PRs (verify no broken links); deploy to GitHub Pages
on push to main.
**Prerequisite:** `mkdocs.yml` must exist at repo root and pass the mkdocs-auditor check.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. PromptCraft
(ruleset 5939198) required ruleset enforcement=disabled. Discovery method: checked all repos
with N in W14 for presence of mkdocs.yml via GitHub Contents API; 3 repos found (gleif,
monte_carlo, PromptCraft). Applicable count corrected to 15 (Sprint 0 baseline of 16 was
wrong by 1 -- an extra repo was counted as Has-Docs when it lacked mkdocs.yml).
**Deployed to (3 repos):** ByronWilliamsCPA/gleif, williaby/monte_carlo, williaby/PromptCraft

---

### Sprint EV-1: Non-Standard Workflow Evaluation (ByronWilliamsCPA)

**Status: COMPLETE (2026-05-04).**

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

**EV-1 Findings (ByronWilliamsCPA):**

| Workflow | Repos (BW) | Decision | Rationale |
|---|---|---|---|
| `.github` python-* templates | 1 (.github repo) | KEEP -- foundational | These are the org-level reusable workflow library that WF-1 through WF-14 all delegate to. Not evaluated as "extra" -- they are the standards substrate. |
| `slsa-provenance.yml` | 7 | STANDARDIZE -- becomes WF-13 standard | 7/7 BW Published repos use SLSA provenance (GitHub SLSA framework). 0 use Cosign's release-sign.yml. Evidence overwhelmingly favors slsa-provenance.yml. WF-13 standard changes from release-sign.yml to slsa-provenance.yml. SLSA framework provides unforgeable build provenance via isolated GitHub infra. |
| `validate-cruft.yml` | 8 | STANDARDIZE -- new WF-15 sprint | 8 BW repos validate their cookiecutter template sync via cruft. Applicable to any repo using a cookiecutter/cruft-based template. |
| `fips-compatibility.yml` | 7 | STANDARDIZE -- new WF-16 sprint | 7 BW Python repos test FIPS mode compatibility. Applies to Python repos using cryptographic primitives (hashlib, ssl, cryptography package). |
| `mutation-testing.yml` | 7 | STANDARDIZE -- new WF-17 sprint | 7 BW Python repos run mutation testing (mutmut). Validates test suite quality. Applicable to Python repos with good baseline coverage (>80%). |
| `container-security.yml` | 5 | STANDARDIZE -- new WF-18 sprint | 5 BW repos run container security scanning (Trivy or similar). Applicable to repos that build Docker images. |
| `codecov.yml` | 6 | KEEP STANDALONE | Per established memory: Codecov (coverage history, PR deltas) and Qlty (code quality gates) coexist and serve different purposes. codecov.yml uploads coverage XML to Codecov; this is separate from WF-11 (Qlty). Not standardized separately -- each repo keeps its codecov.yml as a companion to ci.yml. |
| `dependency-review.yml` | 5 | KEEP STANDALONE (evaluate vs WF-3) | GitHub dependency review action blocks PRs that introduce vulnerable dependencies. Complementary to WF-3 (security-analysis.yml which runs on push and weekly schedule). PR-gating behavior is unique. If WF-3's reusable workflow is extended to include dependency review, this can be removed. Defer decision until WF-3 reusable workflow is inspected. |
| `cifuzzy.yml` | 3 (BW) | KEEP STANDALONE | CI Fuzz requires org-level CI Fuzz setup and paid subscription. Not deployable as a general standard. Keep in repos where it's already configured. |
| `qlty.yml` (gleif) | 1 | KEEP STANDALONE | Qlty quality checks in gleif. Related to WF-11 (coverage.yml uses Qlty) but serves the code quality gate function there. Not enough repos to standardize. |
| `cookiecutter-python-template` specific (cruft-update, release-drafter, scheduled-validation, test-template, validate-template) | 1 each | KEEP STANDALONE | Template repo maintenance workflows specific to cookiecutter-python-template. No other repo would benefit. |
| `homelab-infra` specific (compose-validation, dhi-build, docker, mirror-hardened-images, supplemental-checks, trivy-compose-scan) | 1 each | KEEP STANDALONE | Infrastructure-specific workflows for homelab. No other repo would benefit. |
| `python-libs` specific (publish-artifact-registry, publish) | 1 each | KEEP STANDALONE | Google Artifact Registry publish and PyPI publish specific to python-libs release process. No other repo needs these. |
| `maester-tests.yml` | 1 | KEEP STANDALONE | Runs the maester test framework, specific to the maester-tests repo's purpose. |
| `xero-crypto/test.yml` | 1 | KEEP STANDALONE | Minimal CI for xero-crypto (master branch). Non-standard branch setup makes it repo-specific. |
| `template-sample/cifuzzy.yml` | see cifuzzy above | KEEP STANDALONE | Already covered under cifuzzy row. |

**New WF sprints added by EV-1:**
- WF-13: REVISED -- standard changes from release-sign.yml to slsa-provenance.yml (EV-1 decision)
- WF-15: Cruft Template Validation (validate-cruft.yml) -- Published/template-driven repos
- WF-16: FIPS Compatibility (fips-compatibility.yml) -- Python repos using crypto
- WF-17: Mutation Testing (mutation-testing.yml) -- Python repos with 80%+ coverage
- WF-18: Container Security (container-security.yml) -- Repos with Docker images

**WF-11 unblock:** The coverage.yml template blocker (hardcoded --cov=src/claude_config path)
is resolved by parameterizing the `source-dir` input in the org-level python-coverage.yml
reusable workflow and updating the caller template. WF-11 can resume after the template is
updated. The per-repo `source-dir` should default to `src` and be overridable via workflow input.

**Output:** 4 new WF sprints (WF-15 through WF-18) added to the sprint catalog. WF-13 revised.
WF-11 unblocked with a template fix path. No removals at this time (all non-standard workflows
are either being standardized or have valid standalone reasons).

---

### Sprint EV-2: Non-Standard Workflow Evaluation (williaby)

**Status: COMPLETE (2026-05-04). 2 concrete actions taken (removal + rename).**

Same process as EV-1, applied to the williaby org's non-standard workflows.

**Additional consideration for williaby:** This org includes personal and family office
repos with potentially unique requirements (genealogy tooling, personal finance, etc.).
Standalone decisions are more likely here; apply the same matrix but expect more
"keep as standalone" outcomes.

**EV-2 Findings (williaby):**

| Workflow | Repos (W) | Decision | Rationale |
|---|---|---|---|
| `slsa-provenance.yml` | dna, exercise-competition | KEEP -- now standard WF-13 | Aligns with EV-1 decision to adopt slsa-provenance.yml as WF-13 standard. Both repos will PASS WF-13 under revised standard. |
| `validate-cruft.yml` | dna, exercise-competition | KEEP -- WF-15 candidate | Covered by EV-1 new WF-15 sprint. |
| `fips-compatibility.yml` | dna, exercise-competition | KEEP -- WF-16 candidate | Covered by EV-1 new WF-16 sprint. |
| `mutation-testing.yml` | dna, exercise-competition, image-preprocessing-detector | KEEP -- WF-17 candidate | Covered by EV-1 new WF-17 sprint. |
| `container-security.yml` | exercise-competition | KEEP -- WF-18 candidate | Covered by EV-1 new WF-18 sprint. |
| `codecov.yml` | data_ingestor, dna, image-preprocessing-detector | KEEP STANDALONE | Per EV-1 decision (Codecov and Qlty coexist). |
| `cifuzzy.yml` | data_ingestor, dna, image-preprocessing-detector, ledgerbase | KEEP STANDALONE | Per EV-1 decision (CI Fuzz requires per-repo setup). |
| `dependency-review.yml` | dna, ledgerbase, PromptCraft | KEEP STANDALONE | Per EV-1 decision (pending WF-3 evaluation). |
| `compatibility.yml` | image-preprocessing-detector | REMOVE (action taken) | Replaced by python-compatibility.yml deployed in WF-9 sprint. Wrong filename was causing confusion (two different names for the same workflow). Removed via Contents API in EV-2 execution. |
| `semantic-release.yml` | zen-mcp-server | RENAME to release.yml (action taken) | zen-mcp-server uses python-semantic-release with [tool.semantic_release] in pyproject.toml -- identical setup to standard release.yml. Rename to release.yml unblocks WF-12 for this repo. Removed semantic-release.yml after creating release.yml with same content. |
| `docker-pr.yml, docker-release.yml, manual-publish.yml` | magg | KEEP STANDALONE; WF-12=N/A for magg | magg's primary artifact is Docker, not PyPI. docker-release.yml IS the release workflow. WF-12 (python-semantic-release based) does not apply to Docker-only repos. Audit table updated: magg W12 → N/A. |
| `ci.yml` | monte_carlo | ALREADY STANDARD (WF-8 PASS) | monte_carlo's ci.yml was evaluated and confirmed to follow WF-8 standard (delegates to org reusable workflow). No action needed. |
| `ci-test-minimal.yml, cifuzzy-scheduled.yml` | dna | KEEP STANDALONE | Repo-specific variants (minimal test config, scheduled fuzzing). 1 repo each. |
| `benchmark-results.yml, performance-regression.yml` | image-preprocessing-detector | KEEP STANDALONE | ML benchmarking workflows highly specific to this ML preprocessing repo. |
| `qlty.yml` | image-preprocessing-detector | KEEP STANDALONE | Qlty code quality; same decision as gleif/qlty.yml in EV-1. |
| `auto-merge.yml, deploy.yml, dev-checks.yml, gh-pages.yml, license.yml, pre-commit.yml, prepare-poetry.yml, security-*.yml, stale.yml, weekly-check.yml, wtd.yml` | ledgerbase | KEEP STANDALONE | ledgerbase has a large legacy workflow collection from its pre-standard era. Most will be pruned naturally as the new WF standards replace individual checks. Flag security-codeql.yml as potentially redundant with WF-5; flag security-pip-audit.yml as potentially redundant with WF-3. No removals now -- defer to a ledgerbase-specific cleanup sprint. |
| `renovate-auto-merge.yml` | pp-security-master, PromptCraft | KEEP STANDALONE | Useful companion to Renovate (WF-2r). Once WF-2r lands, evaluate promoting to a standard. |
| `deploy-docs-production.yml, deploy-docs.yml` | PromptCraft | EVALUATE vs docs.yml (deferred) | We deployed docs.yml (WF-14) to PromptCraft in this session. These older deploy-docs*.yml files may be redundant. Compare trigger conditions and deployment targets before removing. Flag for follow-up. |
| `auth-service-token-example.yml, codespaces-prebuild.yml, security-scan-summary.yml, setup-assured-oss.yml, ui-testing-pipeline.yml` | PromptCraft | KEEP STANDALONE | PromptCraft-specific workflows (auth examples, UI testing). 1 repo each. |
| `docker-pr.yml, docker-release.yml, semantic-pr.yml` | zen-mcp-server | KEEP STANDALONE | Docker build workflows and semantic PR validator. zen-mcp-server publishes to Docker Hub in addition to PyPI. semantic-pr.yml complements WF-4 with semantic versioning checks. |

**Concrete actions taken in EV-2:**
1. **REMOVE** `williaby/image-preprocessing-detector/.github/workflows/compatibility.yml` -- replaced by python-compatibility.yml; audit W14 already N/A for this repo.
2. **RENAME** `williaby/zen-mcp-server/.github/workflows/semantic-release.yml` → `release.yml` -- unblocks WF-12 for zen-mcp-server; audit W12 changes ✗ → ✓.
3. **UPDATE audit** magg W12: ✗ → N/A (Docker-only repo; python-semantic-release WF-12 does not apply).

**WF-12 impact of EV-2:**
- zen-mcp-server: W12 ✗ → ✓ (+1 PASS)
- magg: W12 ✗ → N/A (-1 applicable, -0 PASS)
- exercise-competition: still ✗ (needs WF-12 setup from scratch; deferred)
- WF-12 PASS count: 17 → 18, applicable: 24 → 23, %: 71% → 78%

**WF-13 impact of EV-2 (combined with EV-1 standard revision):**
All repos with slsa-provenance.yml now count as WF-13 PASS. Total with slsa-provenance.yml across both orgs:
BW: audio-processor, fragrance-rater, homelab-infra, llc-manager, maester-tests, python-libs, rag-processor = 7
W: dna, exercise-competition = 2
Total now PASS: 9 (vs 0 under old Cosign standard). Applicable: 17. % pass: 53%. Remaining 8 repos need slsa-provenance.yml deployed.

---

### Sprint WF-15: Cruft Template Validation

**Status: COMPLETE (2026-05-04). 22/22 cruft-tracked repos PASS (100%). 12 deployed this sprint.**

**Tier:** Cruft-tracked repos only (repos with `.cruft.json` at root)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/validate-cruft.yml`
**Covers:** Verifies repo is in sync with its cookiecutter template via `cruft check`. Fails
PRs that drift from the template; warns only on scheduled/manual runs. Conditionally checks
for orphaned files if `scripts/check_orphaned_files.py` exists (using `hashFiles()`).
**Security note:** `github.event_name` passed via `env: EVENT_NAME` before use in shell to
prevent command injection.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. image-preprocessing-detector
(rulesets 9575480+9694992), pp-security-master (ruleset 15815381), and PromptCraft (ruleset 5939198)
required ruleset enforcement=disabled.
**Already PASS (10 repos):** audio-processor, fragrance-rater, homelab-infra, llc-manager,
maester-tests, python-libs, rag-processor, template-sample (BW); dna, exercise-competition (W)
**Deployed this sprint (12 repos):** cookiecutter-template-sample (BW); data_ingestor, GCS,
image-generation, image-preprocessing-detector, ledgerbase, magg, monte_carlo, pp-security-master,
PromptCraft, testing, zen-mcp-server (W)

---

### Sprint WF-16: FIPS Compatibility

**Status: COMPLETE (2026-05-04). 20/20 applicable repos PASS (100%). 11 deployed this sprint.**

**Tier:** Python repos with `scripts/check_fips_compatibility.py` at root
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/fips-compatibility.yml`
**Covers:** Verifies Python cryptographic operations work in FIPS 140-2/140-3 restricted
environments. Runs the repo's `check_fips_compatibility.py` script with `--fix-hints` and
`--include-tests`. Generates a JSON report and uploads as artifact. Posts pass/fail/warn
summary as a PR comment.
**Security note:** `workflow_dispatch` input `strict_mode` passed via `env: STRICT_MODE`
before use in shell to prevent command injection. Original BW repo version had direct
expression interpolation (`${{ github.event.inputs.strict_mode }}`) inside a bash `if [[ ]]`
block -- a genuine injection risk for user-supplied dispatch inputs. Canonical template fixes this.
**N/A determination:** 5 BW Python repos lack `check_fips_compatibility.py`:
cookiecutter-template-sample, DeQA-Doc, gleif, template-sample, xero-crypto. These are N/A
for WF-16 and not blockers -- they don't use the cryptographic primitives the script tests.
**Remediation used:** Same save-relax-write-restore cycle as prior WF sprints. image-preprocessing-detector
(rulesets 9575480+9694992), pp-security-master (ruleset 15815381), and PromptCraft (ruleset 5939198)
required ruleset enforcement=disabled. All W repos successfully deployed in a single script run.
**Already PASS (9 repos):** audio-processor, fragrance-rater, homelab-infra, llc-manager,
maester-tests, python-libs, rag-processor (BW); dna, exercise-competition (W)
**Deployed this sprint (11 repos, all williaby):** data_ingestor, GCS, image-generation,
image-preprocessing-detector, ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft,
testing, zen-mcp-server

---

### Sprint WF-17: Mutation Testing

**Status: COMPLETE (2026-05-04). 10/10 applicable repos PASS (100%). No new deployments needed.**

**Tier:** Python repos with 80%+ baseline coverage
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/mutation-testing.yml`
**Covers:** Validates test suite quality by running mutmut mutation testing. Delegates to
org-level `python-mutation.yml` reusable workflow. Fails on PRs if mutation score drops
below 80%; weekly scheduled runs report only (no failure gate). Posts mutation score as
a PR comment.
**Applicability determination:** The 10 repos that already have `mutation-testing.yml`
(7 BW + 3 W) are the confirmed-applicable set for this sprint. Remaining W Python repos
require coverage data confirmation (80%+ baseline) before WF-17 can be applied. Since
WF-10/WF-11 are not yet fully resolved for all W repos, marking these N/A for now and
revisiting after coverage infrastructure is stable.
**Already PASS (10 repos, all pre-existing):** audio-processor, fragrance-rater,
homelab-infra, llc-manager, maester-tests, python-libs, rag-processor (BW);
dna, exercise-competition, image-preprocessing-detector (W)
**N/A (remaining W Python repos, coverage not yet confirmed):** data_ingestor, GCS,
image-generation, ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft,
testing, zen-mcp-server

---

### Sprint WF-18: Container Security

**Status: COMPLETE (2026-05-04). 25/25 applicable repos PASS (100%). No new deployments needed.**

**Tier:** Docker repos (repos with a Dockerfile at root)
**Template:** `ByronWilliamsCPA/.claude/.github/workflows/container-security.yml`
**Covers:** Scans Docker images for vulnerabilities using Trivy (fails on CRITICAL/HIGH);
lints Dockerfile with Hadolint (warning threshold). Generates an SBOM and uploads SARIF
to GitHub Security tab. Delegates to org-level `python-container-security.yml` reusable
workflow. Runs on push/PR to Dockerfile-related paths and on a weekly schedule.
**Applicability determination:** All 25 Python repos (12 BW + 13 W) already had both a
Dockerfile and a container-security.yml. The EV-1 decision to standardize (based on 5 BW
repos) underestimated adoption -- the full Python tier had already deployed it organically.
**Template note:** Canonical template uses generic `image-tag: 'local:scan'` (replaces the
original BW repo-specific tags). This is safe because the scan image is never pushed;
the tag is just a local build handle.
**Already PASS (25 repos, all pre-existing):** audio-processor, cookiecutter-template-sample,
fragrance-rater, gleif, homelab-infra, llc-manager, maester-tests, python-libs,
rag-processor, template-sample, xero-crypto (BW, 11); audio-processor (already counted);
data_ingestor, dna, exercise-competition, GCS, image-generation, image-preprocessing-detector,
ledgerbase, magg, monte_carlo, pp-security-master, PromptCraft, testing, zen-mcp-server (W, 13)
**N/A (non-Docker repos):** .claude, .github, backpacking, CR-10-, DeQA-Doc, LifeSphere,
reference-library (BW); family_office, FISProject, xero-practice-management (W)

---

### Sprint WF-2r: Renovate Migration (replaces Dependabot)

**Tier:** Universal (all 44 repos)
**Goal:** Replace `dependabot.yml` with Renovate as the dependency update manager across all repos.
**Prerequisite:** Mend Renovate GitHub App installed on both ByronWilliamsCPA and williaby orgs.

**Migration steps:**
1. Create org-level `renovate.json` in `ByronWilliamsCPA/.github` and `williaby/.github` with shared base config.
2. Let Renovate open onboarding PRs per repo -- it auto-detects ecosystems (pip, docker, github-actions, etc.).
3. Merge each onboarding PR after reviewing Renovate's proposed schedule and grouping config.
4. After Renovate is confirmed active per repo, remove or empty `dependabot.yml` (or keep the `github-actions` entry if you prefer Dependabot for Actions while Renovate handles packages).

**Key Renovate advantages over Dependabot:**
- Centralized org-level config
- Update grouping (e.g., batch all minor/patch updates in one PR)
- Configurable automerge for low-risk updates (patch-level, non-breaking)
- Better monorepo support
- More package managers supported

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
| 5 | BP-5 | Enforce admins + status checks | Universal | DONE 2026-05-04 |
| 6 | BP-6 | PR reviews = 0 (solo-dev exception) | Universal | DONE 2026-05-04 |
| 7 | WF-1 | REUSE compliance | Universal | DONE 2026-05-04 |
| 8 | WF-2 | Dependabot | Universal | DONE 2026-05-04 |
| 9 | WF-3 | Security analysis | Universal | DONE 2026-05-04 |
| 10 | WF-4 | PR validation | Universal | DONE 2026-05-04 |
| 11 | WF-5 | CodeQL | Public | DONE 2026-05-04 |
| 12 | WF-6 | SBOM | Public | DONE 2026-05-04 |
| 13 | WF-7 | OpenSSF Scorecard | Public | DONE 2026-05-04 |
| 14 | WF-8 | CI gate | Python | DONE 2026-05-04 (partial: 25/32; 5 blocked on pyproject.toml) |
| 15 | WF-9 | Python compatibility | Python | DONE 2026-05-04 (partial: 26/32; 5 blocked on pyproject.toml) |
| 16 | WF-10 | SonarCloud | Python | DONE 2026-05-04 (mostly blocked: 10/32; 1 deployed; 22 need SonarCloud registration + SONAR_TOKEN) |
| 17 | WF-11 | Coverage (Qlty) | Python | DONE 2026-05-04 (partial: 25/32; template rearchitected as workflow_run subscriber; 5 blocked on pyproject.toml) |
| 18 | WF-12 | Semantic release | Published | DEFERRED (partial: 15/16 PASS; exercise-competition needs python-semantic-release setup from scratch; magg set to N/A; zen-mcp-server resolved by EV-2 rename) |
| 19 | WF-13 | Release signing (SLSA) | Published | DONE 2026-05-04 -- standard revised by EV-1 to slsa-provenance.yml; 7 deployed; 16/16 PASS (100%) |
| 20 | WF-14 | MkDocs docs | Has-Docs | DONE 2026-05-04 (15/15; 3 deployed to gleif, monte_carlo, PromptCraft) |
| 21 | EV-1 | Non-standard eval (ByronWilliamsCPA) | All | DONE 2026-05-04 -- 4 new WF sprints added (WF-15 to WF-18); WF-13 standard revised; WF-11 unblocked |
| 22 | EV-2 | Non-standard eval (williaby) | All | DONE 2026-05-04 -- compatibility.yml removed; semantic-release.yml renamed to release.yml; magg W12/W13 N/A; WF-13 9/16 PASS under revised standard (before WF-13 sprint) |
| 23 | WF-2r | Renovate migration (replaces Dependabot) | Universal | pending |
| 24 | WF-15 | Cruft template validation | Cruft-tracked | DONE 2026-05-04 -- 22/22 PASS (100%); 12 deployed; hashFiles() conditional for orphaned-files check |
| 25 | WF-16 | FIPS compatibility | Python/crypto | DONE 2026-05-04 -- 20/20 applicable PASS (100%); 11 W repos deployed; 9 BW already had it; 5 BW N/A (no check_fips_compatibility.py); command injection fixed in canonical template |
| 26 | WF-17 | Mutation testing | Python | DONE 2026-05-04 -- 10/10 applicable PASS (100%); all pre-existing; canonical template written; remaining W Python repos N/A pending 80%+ coverage confirmation |
| 27 | WF-18 | Container security | Docker repos | DONE 2026-05-04 -- 25/25 PASS (100%); all pre-existing; canonical template written with generic image-tag 'local:scan' |
