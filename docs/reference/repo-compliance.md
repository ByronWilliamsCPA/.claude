---
title: "Repo Compliance System"
schema_type: common
status: published
owner: core-maintainer
purpose: "Reference for the standards manifest, domain agents, audit workflow, override system, and check catalog that make up the repo compliance system."
tags:
  - compliance
  - reference
  - standards
  - automation
  - agents
---

The repo compliance system audits repositories against a shared standards manifest, presents findings by severity, applies approved remediations, and writes a retrospective after each run. It is the authoritative source for what "compliant" means across all repos in the ByronWilliamsCPA and williaby orgs.

## Quick Reference

| Component | Location |
| --- | --- |
| Standards manifest | `docs/standards-manifest.yaml` |
| Compliance exclusions | `docs/compliance-exclusions.yaml` |
| Override file (per repo) | `.claude/compliance-overrides.md` |
| Compliance reports (gitignored) | `docs/compliance-reports/` |
| Lessons-learned output | `docs/compliance-reports/lessons-learned/` |
| Invoke audit | `/repo-audit` (interactive) or `/repo-audit --scheduled` |

## Architecture Overview

The system has four layers:

```text
standards-manifest.yaml          (what to check and how to verify it)
        |
        v
Domain agents (8 agents)         (read the manifest; audit or remediate)
        |
        v
Coordinator skill                (dispatches agents in parallel; merges findings)
        |
        v
Compliance-retrospective agent   (pattern detection; proposes manifest improvements)
```

The coordinator skill is the entry point. It reads the manifest, dispatches the domain agents in parallel, merges their FINDING blocks, filters overrides, and presents results sorted by severity. After all repos in a session are processed, it dispatches the retrospective agent to synthesize patterns across runs.

## Standards Manifest

`docs/standards-manifest.yaml` is the single source of truth for what every check requires. Agents read it at runtime; they do not hardcode check logic.

### Check structure

Every check entry has these fields:

```yaml
- id: FOUND-001              # unique check ID; used in overrides and findings
  domain: foundations        # groups checks by auditing agent
  severity: critical         # critical | important | suggested
  description: "..."         # human-readable statement of the requirement
  verify: "..."              # hint to the domain agent (not executable DSL)
  override_eligible: false   # whether this check can be suppressed via overrides
  not_applicable_when: "..." # optional: condition that exempts the check
  notes: "..."               # optional: additional context and known exceptions
```

The `verify` field is a plain-text instruction for the auditing agent. Agents interpret it using their own tools (Grep, Read, Glob, Bash). It is not an executable DSL.

### Domains and agents

| Domain | Agent | Check prefix |
| --- | --- | --- |
| `foundations` | `repo-foundations-auditor` | FOUND-* |
| `repo_settings` | `repo-foundations-auditor` (extended; queries `gh api repos/{owner}/{repo}`) | REPO-* |
| `toolchain` | `python-toolchain-auditor` | TOOL-* |
| `pre_commit` | `pre-commit-auditor` | PC-* |
| `ci` | `devops-deployment-agent` (CI audit mode) | CI-* |
| `claude_docs` | `claude-docs-auditor` | CLAUDE-* |
| `ossf` | `ossf-compliance-auditor` | OSSF-* (plus live Scorecard/Badge API) |
| `mkdocs` | `mkdocs-auditor` | MKDOCS-* (skipped when mkdocs.yml absent) |
| `api` | `openapi-compliance-agent` (via check-repo-compliance.py) | API-001..005 (when `api.servesApi: true`) |
| General gaps | `general-compliance-auditor` | unclassified candidates |

The `repo_settings` domain audits GitHub repository toggles that are not visible in the working tree (e.g., `allow_auto_merge`, `delete_branch_on_merge`). It is the only domain whose source of truth is the GitHub API rather than a file in the repo. Added 2026-05-26 after the Renovate auto-merge fleet rollout audit revealed that 11 of 42 repos had `allow_auto_merge=false` and 38 of 42 had `delete_branch_on_merge=false` with no manifest check covering either toggle.

The general compliance auditor operates after domain agents complete. It receives the covered check IDs as a negative filter and performs a freeform review for anything not yet in the manifest. Its output feeds the retrospective, not the findings report.

### Severity levels

| Severity | Meaning | Remediate when |
| --- | --- | --- |
| `critical` | Security or supply chain risk; blocks trust | Always; non-negotiable |
| `important` | Quality or process gap; accumulates debt | By default in interactive mode |
| `suggested` | Best practice; low urgency | On request or in batch sweeps |

### Check summary by domain

**FOUND (Foundations, 16 checks):** OpenSSF required files (SECURITY.md, CONTRIBUTING.md, CHANGELOG.md), CODEOWNERS, .gitignore entries, pyproject.toml metadata, docs structure, known-vulnerabilities.md, AGENTS.md, GEMINI.md. Recent additions: FOUND-015 (ADR "Security Considerations" section presence under docs/ADRs/ or docs/architecture/, satisfying NIST SSDF PW.2.1) and FOUND-016 (LICENSES/ files contain no unfilled OSI-template placeholders such as `<year>` or `<copyright holders>`, which automated scanners treat as unlicensed).

**TOOL (Toolchain, 13 checks):** Dev dependency presence (ruff, basedpyright, pip-audit, pydoclint, interrogate), absence of replaced tools (black, mypy, safety, darglint), Ruff PyStrict-aligned rule set, BasedPyright strict config, qlty config, target-version.

**PC (Pre-commit, 16 checks):** Hook presence (ruff, basedpyright, bandit, detect-secrets, pydoclint, interrogate, commitizen, yamllint, markdownlint, no-em-dash), hook SHA pinning on all rev fields. The manifest now also includes PC-007b (interrogate hook scoped to `src/` at 80% fail-under, complementing PC-007 which scopes to `scripts/` at 85%) and PC-016 (global Renovate config validator, suggested). PC-015 (v42-era renovate-config-validator pin lockstep) was never landed; CI-059 is its structural successor (see manifest header comment).

**CI (CI/CD, 86 checks as of 2026-09-06):** Reusable workflow adoption, SHA pinning on all `uses:` references, harden-runner in every job, security scan hardening, required status checks, integration ID pinning, trust-boundary file path restrictions, tag protection rulesets, max file size cap, workflow permissions hygiene, timeout-minutes on all jobs, concurrency groups, PR title enforcement, SBOM generation, Python matrix coverage, merge queue trigger, named environments, test result annotations. CI-036 and CI-081 (the dependency-review workflow presence and license-input checks) were retired 2026-09: `actions/dependency-review-action` now requires paid GitHub Advanced Security. Recent additions: CI-052 (CodeRabbit gating), CI-053 (mutation testing schedule), CI-054 (live Codecov coverage), CI-055/056/057 (org workflow SHA-pin registry), CI-058/059/060/061 (SBOM caller SHA-pin, Renovate semantic enabledManagers lint, third-party Action SHA pins, Renovate Docker image digest pin), CI-003c (no inline SonarCloud actions in ci.yml), CI-062 (merge_queue rule on main-branch ruleset for auto-merging repos, important; landed via merge-queue rollout PR), and CI-063/064 (per-repo `renovate.json` is a thin overlay rather than a redundant duplicate of global rules; global Renovate config explicit `platformAutomerge`).

**REPO (Repo settings, 2 checks as of 2026-05-26):** GitHub repo-level toggles queried via `gh api repos/{owner}/{repo}`. REPO-001 (`allow_auto_merge=true`, critical) is required for any bot-driven auto-merge to function; REPO-002 (`delete_branch_on_merge=true`, important) prevents stale Renovate branches from accumulating after merge. This domain is distinct from CI (workflows), foundations (in-tree files), and OSSF (Scorecard/Badge APIs) because its source of truth is the GitHub repo settings object, not the working tree.

**CLAUDE (Claude docs, 10 checks):** CLAUDE.md presence and required sections (Model Selection, RAD, cross-references), .claude/settings.json, no references to removed tools, no em-dashes in docs, no AI blacklist patterns. Recent additions: CLAUDE-009 (`.claude/settings.json` must not enable `enableAllProjectMcpServers` without a documented justification, per OWASP LLM06/LLM08) and CLAUDE-010 (`$schema` field in `.claude/settings.json`, when present, must be exactly `https://json.schemastore.org/claude-code-settings.json`; the wrong slug silently disables every permission rule in the IDE extension).

**OSSF (OSSF compliance, 15 checks):** OpenSSF Best Practices Badge passing, OpenSSF Security Scorecard at or above 4, branch protection, secret scanning + push protection, plus OSSF-011 (fuzz testing setup such as atheris, libFuzzer, or a `tests/fuzz/` directory, per Silver Badge criterion 6.1) and OSSF-012 (any PATs used as repository secrets must be fine-grained, not classic, per SOC 2 CC6.1 least-privilege). `dependency-review-action` and CodeQL are no longer checked here: both require paid GitHub Advanced Security as of 2026-09 and were retired fleet-wide (see CI-036/CI-081 in `docs/standards-manifest.yaml`).

**MKDOCS (MkDocs docs build, 12 checks):** mkdocs.yml metadata, theme, navigation, plugins, extensions, version pinning, docs/ structure, and CI build wiring. Skipped silently when `mkdocs.yml` is absent.

**API (OpenAPI compliance, 5 checks):** OpenAPI spec presence (API-001..003 verified via the GitHub Contents API), plus Postman collection presence and last-audited timestamp (API-004/005 read from the catalog). Runs only when `api.servesApi: true` in the repo's catalog entry.

### Manifest versioning

The manifest carries `version` and `last_updated` fields at the top level. Bump `last_updated` (ISO date) whenever checks are added, modified, or removed. There is no semantic versioning for the manifest; the `last_updated` date is the version identifier used in compliance reports.

## Override System

### Repo-level overrides

Any repo can suppress individual checks by creating `.claude/compliance-overrides.md` at the repo root. Only checks marked `override_eligible: true` in the manifest can be suppressed. Checks with `override_eligible: false` are always enforced regardless of override entries.

Override file format:

```markdown
| Check ID | Reason | Approved By | Date |
|----------|--------|-------------|------|
| CI-039   | Non-Python repo; matrix CI not applicable | Byron Williams | 2026-05-14 |
| TOOL-009 | Documentation-only repo; qlty config not applicable | Byron Williams | 2026-05-30 |
```

The auditing coordinator reads this file before presenting findings and excludes listed check IDs from the output. Overridden checks are reported separately as a suppressed count, not silently dropped.

### Org-level exclusions

`docs/compliance-exclusions.yaml` lists repos that are excluded from scheduled sweeps entirely. Currently excluded:

- `cookiecutter-python-template`: template source, not a generated project
- `.claude`: this repo is the standards source, not a downstream project

Exclusions suppress the entire audit, not individual checks. They are appropriate for repos that are structurally exempt from the standard model (templates, meta-repos), not for repos that simply have many open gaps.

### not_applicable_when

Some checks carry a `not_applicable_when` field in the manifest that exempts the check for certain repo types without requiring a per-repo override entry. For example:

```yaml
not_applicable_when: "not a Python project"
```

The auditing agent reads this field and auto-skips the check when the condition is met, logging it as EXEMPT rather than PASS or FAIL.

## Running an Audit

### Interactive mode

Interactive mode runs a full audit against a single repo and presents an approval loop for remediation.

```bash
/repo-audit                   # audits the current working directory
/repo-audit /path/to/repo     # audits the specified path
```

Workflow:

1. Load manifest and overrides
2. Dispatch six domain agents in parallel
3. Merge FINDING blocks; filter overrides; sort by severity
4. Present findings grouped as: Critical, Important, Suggested, Unclassified candidates
5. Approval loop: choose All critical+important, All three severities, Specific IDs, or Skip
6. Remediation dispatch (if approved)
7. Open PR with remediation summary
8. Run compliance-retrospective

### Scheduled mode

Scheduled mode runs report-only across all non-excluded repos. No approval loop and no remediation.

```bash
/repo-audit --scheduled
```

Scheduled mode discovers repos from local `~/dev/` clones and remote org listings (`gh repo list ByronWilliamsCPA`, `gh repo list williaby`). It writes one report file per repo to `docs/compliance-reports/<date>-<repo-slug>.md`. All reports are gitignored.

### Audit methodology gotchas

These verification patterns have produced false positives in past audits. Always use the corrected method below.

**Required-check coverage (CI-022/CI-023):** Verify against a recently merged PR's status rollup, never against the merge commit's check-runs.

```bash
# CORRECT: queries the PR's check rollup, which includes pull_request-event-only workflows
gh pr view <PR_NUMBER> --repo <org>/<repo> --json statusCheckRollup \
  --jq '.statusCheckRollup[].name'

# WRONG: workflows triggered by pull_request do not re-run on the merge commit,
# so they are absent from this output. The 2026-05-26 audit used this method
# and incorrectly flagged every repo in ByronWilliamsCPA as missing the
# "Dependency & Standards Validation" check.
gh api repos/<org>/<repo>/commits/<sha>/check-runs --jq '.check_runs[].name'
```

**Bot PR filtering:** Self-hosted Renovate authenticates as a PAT, so `author == "renovate[bot]"` returns zero results. Filter by `headRefName` matching `renovate/*` instead. Bot logins from GitHub Apps end in the literal `[bot]` suffix, e.g. `Copilot[bot]`, `coderabbitai[bot]` (memory: `feedback_bot_login_suffix.md`).

### Finding output format

Each failing check is emitted as a FINDING block by the domain agent:

```yaml
FINDING:
  id: FOUND-001
  severity: critical
  description: SECURITY.md absent from project root
  status: fail
  current_value: file not found
```

Remediation actions are emitted as ACTION lines:

```yaml
ACTION: Created SECURITY.md from template /home/byron/dev/.github/SECURITY.md
ACTION: Appended .worktrees/ to .gitignore
```

## Retrospective and Self-Improvement

After each session (interactive or scheduled), `compliance-retrospective` reads all findings and unclassified candidates across every repo reviewed. It:

- Groups candidates by description similarity
- Promotes any pattern appearing in three or more repos to a manifest candidate
- Identifies domain agents whose scope should expand
- Writes a lessons-learned document to `docs/compliance-reports/lessons-learned/<date>.md`

The lessons-learned document includes ready-to-paste YAML snippets for each proposed manifest addition. To promote a candidate to the manifest, copy the snippet into `docs/standards-manifest.yaml`, assign it the next available check ID in its domain, and commit.

## Adding New Checks

1. Add a YAML entry to the appropriate domain block in `docs/standards-manifest.yaml`
2. Assign the next sequential ID in the domain (e.g., CI-043 if CI-042 is the current last)
3. Set `severity`, `description`, `verify`, `override_eligible`, and optionally `notes` or `not_applicable_when`
4. If the check requires new audit logic: update the owning domain agent's description or audit workflow
5. Run the audit against this repo (`/repo-audit`) to confirm the new check produces the expected result
6. Commit with message: `feat(standards): add <CHECK-ID> to manifest`

The `verify` field is a hint, not executable code. Write it as a plain instruction to the agent: `file_exists: <path>`, `content_present: <file>, <string>`, `sha_pinned: <glob>, <field>`. Agents interpret the hint using their own tool repertoire.

## Solo-Developer Constraints

All managed repos are solo-developer projects. Two constraints shape compliance decisions across the entire system:

**No required approving reviews.** `required_approving_review_count` must remain 0 in every ruleset and branch protection rule. A solo developer cannot self-approve, so a non-zero value would permanently block all merges. `setup_org_rulesets.py` enforces this as a hard guard when deploying rulesets.

**No bypass-actor app.** GitHub Actions bypass is currently granted to the Admin role (actor_id: 5) with `bypass_mode: "always"`. The intended migration path is to replace this with a dedicated GitHub App (Integration actor type) with `bypass_mode: "pull_request"` to disallow direct-push bypasses. This is tracked in CI-028.

## Key Files Reference

| File | Purpose |
| --- | --- |
| `docs/standards-manifest.yaml` | All check definitions; canonical source for agents |
| `docs/compliance-exclusions.yaml` | Repos excluded from scheduled sweeps |
| `.claude/compliance-overrides.md` | Per-repo check suppressions (in each audited repo) |
| `docs/reference/org-rulesets/README.md` | Ruleset architecture, design decisions, enforcement checklist |
| `docs/reference/repo-rulesets/README.md` | Per-repo ruleset templates and deployment notes |
| `docs/reference/repo-type-taxonomy.md` | Seven repo types and their audit exemption profiles |
| `docs/compliance-reports/` | Session reports (gitignored; local only) |
| `docs/compliance-reports/lessons-learned/` | Retrospective output (gitignored; local only) |
| `docs/reference/github-workflow-audit.md` | Sprint 0 baseline: branch protection and workflow status across all 44 repos |

## Required Status Checks

The manifest's `required_checks` block (top-level, above `checks:`) defines which check run names must pass before a PR can merge. These are pinned to `integration_id: 15368` (the GitHub Actions app) in org rulesets to prevent an actor from satisfying the requirement with a synthetic check run.

Current required checks:

| Check run name | Produced by | Applies to |
| --- | --- | --- |
| CI Gate | `.github/workflows/ci.yml` | Python repos |
| Security Analysis / Security Gate Validation | `.github/workflows/security-analysis.yml` | All repos |
| Dependency & Standards Validation | `.github/workflows/pr-validation.yml` | All repos |
| Check REUSE Compliance | `.github/workflows/reuse.yml` | All repos |

The naming convention matters for CI-022/CI-023 verification: a direct job produces a check run named with the job's `name:` field only (not prefixed by the workflow name), while a job that calls a reusable workflow produces `<calling-job-name> / <internal-job-name>`. The manifest comment block at the top of `docs/standards-manifest.yaml` explains this in full.

## See Also

- `docs/reference/org-rulesets/README.md`: ruleset design decisions and enforcement migration checklist
- `docs/reference/repo-type-taxonomy.md`: audit exemption profiles by repo type
- `.claude/agents/`: domain agent definitions
- `.claude/skills/repo-compliance/`: coordinator skill and workflow files
- `docs/standards-manifest.yaml`: the complete check catalog
