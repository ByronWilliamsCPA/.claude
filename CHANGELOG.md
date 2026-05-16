# CHANGELOG

## Unreleased

### Breaking

* chore(deps)!: bump `actions/download-artifact` from v4.3.0 to v8.0.1 in
  `.github/workflows/pr-validation.yml`. The action now requires Node.js 24
  runtime (minimum Actions Runner 2.327.1, relevant for self-hosted runners),
  has migrated to ESM, and defaults `digest-mismatch` to `error` rather than
  `warn`. This repo's usage (name-based download on GitHub-hosted runners
  with `continue-on-error: true` on the coverage upload path) is verified
  compatible by CI on PR #101.

### Feature

* feat(rulesets): harden CI gate, supply-chain controls, and secret scanning standards; pin all `required_status_checks` to `integration_id: 15368` (GitHub Actions app) across both org and python-tier rulesets to prevent check-name spoofing; expand `file_path_restriction` on universal rulesets to seven trust-boundary paths (`.github/workflows/`, `.github/CODEOWNERS`, `.pre-commit-config.yaml`, `pyproject.toml`, `renovate.json`, `sonar-project.properties`, `.gitleaks.toml`); add SemVer tag-protection rulesets for both orgs (`target: tag`, `v*` ref pattern, `required_signatures`), replacing the deprecated Tag Protection Rules API; add `max_file_size: 100 MB` cap and `do_not_enforce_on_create: true` on python-tier rulesets; add CI-028 through CI-032 to `docs/standards-manifest.yaml`; add PC-005 (trufflehog OR detect-secrets), PC-013 (both required), and OSSF-010 (SECURITY.md security surface section) manifest checks; document two-tier ruleset architecture and enforcement migration checklist in `docs/reference/org-rulesets/README.md`

* feat(rulesets): Track 6 BW canary validation complete; flipped both BW org rulesets (universal id 16183607, python-tier id 16183609) from evaluate to active enforcement; canary PR #85 on `ByronWilliamsCPA/.claude` passed CI (`MERGEABLE + CLEAN`) and self-merged; stripped classic branch protection from `ByronWilliamsCPA/.claude`; updated catalog `migrationPhase` from `dual` to `complete` for `ByronWilliamsCPA/.claude`; added Track 6 completion status block to the rulesets migration plan; williaby canary deferred to the williaby active-only sub-migration plan

* feat(rulesets): add org-rulesets migration tooling (Tracks 1-4 of 2026-05-08-rulesets-migration plan); ships four ruleset JSON bodies (`docs/reference/org-rulesets/{ByronWilliamsCPA,williaby}-{universal,python}.json`) targeting universal protections (signatures, linear history, deletion guard, force-push guard, PR with `required_approving_review_count: 0`) and a python-tier `required_status_checks` set; adds `scripts/setup_org_rulesets.py` and `scripts/setup_repo_rulesets.py` for org-level and repo-level apply with a three-layer solo-dev guard (`validate_solo_dev_safe()` running before `render_body()` and before any subprocess call, exit code 3 `SoloDevViolationError`, manifest annotation `solo_dev_constraints.forbid_required_approving_reviews: true`); adds `scripts/generate_python_tier_repos.py` to enumerate Python-tier repos from the catalog and substitute the `__GENERATED__` token at render time; extends `scripts/check-required-checks.py` with `fetch_ruleset_contexts`, renames the classic fetcher to `fetch_classic_protection_contexts`, adds `fetch_effective_required_contexts` union dispatcher with provenance, and a `--source classic|rulesets|union` CLI flag (default union) so audits can run any of the three modes during staged migration; extends `scripts/check-repo-compliance.py` so BP-4 and BP-5 read from `/rules/branches/:b` first and fall back to classic, honoring `BRANCH_PROTECTION_EXEMPT` for `williaby/homelab-agent-configs`; adds `migrationPhase: pending|dual|complete` field on 45 non-exempt repos in `docs/reference/github-repos.json`; reworks CI-023 in `docs/standards-manifest.yaml` for union mode, adds CI-025/026/027 for ruleset migration, and a top-level `solo_dev_constraints` annotation; updates `.claude/agents/ossf-compliance-auditor.md` with a `--source` flag in the validator invocation, three-way branched CI-023 PATCH remediation (org/repo ruleset/classic), three new CI-025/026/027 finding templates, and a ruleset-first scorecard remediation
* feat(compliance): add CI-022/023/024 manifest-driven cross-validation checks for required CI gates; introduces a `required_checks` top-level field in `docs/standards-manifest.yaml` as the single source of truth for the check names that must match across workflows, the reusable-workflow registry, and live branch protection contexts; ships `scripts/check-required-checks.py` validator (matrix expansion, hyphen/dot-aware axis interpolation, reusable-workflow caller-prefix resolution at compare time) and `scripts/seed-reusable-workflow-registry.py` to populate the registry from a local clone of `ByronWilliamsCPA/.github`; `ossf-compliance-auditor` agent invokes the validator and maps each finding into a standard FINDING block; the validator surfaces branch-protection fetch failures (gh auth, timeout, malformed JSON, unexpected types) as a Critical finding with exit code 2 so CI-023 cannot be silently bypassed; replaces the hardcoded CI-014..017 checks
* feat(agents): add `openapi-compliance-agent`, `openapi-code-enricher`, and `postman-test-designer` agents implementing a four-stage OpenAPI compliance pipeline for FastAPI repos: route enrichment, OpenAPI spec export, Postman collection generation with newman validation, and CI workflow injection; orchestrator runs per-repo pipelines in parallel for `/openapi-audit all`
* feat(compliance): add API-001 through API-005 manifest checks (OpenAPI spec present, Postman collection present, postman-api-tests.yml CI workflow present, lastAudited within 90 days, all Postman tests passing) gated by `applies_to: api_repos` predicate
* feat(scripts): add `applies_to_api_repos` evaluator and API-001..005 check logic to `scripts/check-repo-compliance.py`; loads `docs/reference/github-repos.json` and skips API checks for repos where `api.servesApi` is false
* feat(compliance): register `container-security.yml`, `mutation-testing.yml`, and `postman-api-tests.yml` in CI-013 `expected_set` so the compliance audit recognizes these workflows
* feat(catalog): add `usesDocker` boolean to all repo entries (14 true: 7 ByronWilliamsCPA, 7 williaby) for container-security workflow scoping; remove stale `validate-cruft.yml` entries from 22 per-repo workflow lists now that the workflow is fully deployed (WF-15, 2026-05-04)
* feat(skill): document API domain dispatch and `applies_to: api_repos` conditional in `repo-compliance` SKILL.md

* feat(compliance): add `_meta.visibilityProfiles.private` to `docs/reference/github-repos.json` for private-repo compliance scoping; extends `repo-compliance` skill coordinator to read `isPrivate`, load the visibility profile, merge type and visibility exemptions, and forward `scorecard_api_skip` to the OSSF agent; marks OSSF-001 and OSSF-006 with `visibility_required: public` in `docs/standards-manifest.yaml`; fixes TruffleHog pre-commit hook to use null-delimited staged-file scanning (`git diff -z --diff-filter=d | xargs -0 -r`) to handle filenames with spaces and prevent errors on staged deletions

* feat(agents): add `OSSF-NEW-001` check to `ossf-compliance-auditor` for missing Dependabot ecosystem entries in `.github/dependabot.yml`; add `CI-SEC-002` check for security gate steps with `continue-on-error: true` across seven security actions (anchore, trivy, dependency-review, scorecard, gitleaks, snyk, codeql-action/analyze, semgrep)

* feat(agents): add `TOOL-NEW-002` check to `python-toolchain-auditor` for missing `[tool.interrogate]` section in `pyproject.toml` when `darglint` or `interrogate` is present in dev dependencies; interrogate config template uses `fail-under = 85`

* feat(task-observer): integrate `one-skill-to-rule-them-all` upstream as a thin local adaptation; add `apply-task-observer-patches.sh` to patch and install the skill, `generate-skills-manifest.sh` as a SessionStart hook that enumerates available skills into `skill-observations/available-skills.md`, `task-observer-review.sh` as a Mon/Wed/Fri cron-scheduled unattended review agent, and a "Task observation" section to CLAUDE.md for observer activation

* feat(agents): add `mkdocs-auditor` agent with four lifecycle modes (create, audit, remediate, update) for automated MkDocs `mkdocs.yml` validation against the standards manifest
* feat(agents): add `mkdocs-specialist` agent for MkDocs page content creation and style enforcement, including nav label alignment and front matter validation
* feat(compliance): add MKDOCS-001 through MKDOCS-012 checks to `docs/standards-manifest.yaml` covering site metadata, theme configuration, plugins, navigation, and extension requirements
* feat(compliance): wire `mkdocs-auditor` into the `repo-compliance` coordinator skill for automatic dispatch during audit and remediation passes
* feat(ci): add CI Gate, Security Gate Validation, and Dependency & Standards Validation gate jobs to `.github/workflows/` (ci.yml, security-analysis.yml, pr-validation.yml); add CI-014 through CI-017 standards; update `ossf-compliance-auditor` to audit CI-017; fix `setup_github_protection.py` to register short job display names
* feat(ci): add `ci_local` and `ci_full` nox sessions for a local CI fast-feedback loop before push; add standalone `bandit` session so `ci_full` achieves parity with `ci_local` and GitHub Actions
* feat(ci): add tracked pre-push hook (`.github/hooks/pre-push`) and install script (`scripts/install-hooks.sh`)
* feat(ci): add `qlty-coverage` job to `pr-validation.yml` for lcov upload on PR open/reopen via Qlty action
* feat(ci): add yamllint pre-commit hook pinned to v1.38.0 with `--config-file .yamllint` (PC-YAMLLINT-FILE-REF)
* feat(ci): add markdownlint pre-commit hook with MD040 active via `.markdownlint.json` (PC-MARKDOWNLINT-MD040)
* feat(ci): emit lcov coverage report (`reports/lcov.info`) alongside xml in `ci_local`; add `reports/` and `coverage-ci-local.xml` to `.gitignore`
* feat(agents): add `ossf-badge-evaluator` agent for OpenSSF Best Practices Badge criterion-by-criterion assessment with three automation URLs (passing/silver/gold) for one-click form pre-filling on bestpractices.dev
* feat(ossf): add `ossf-criteria-reference.md` with all criterion slugs, N/A eligibility, and URL field names across passing/silver/gold levels; expand `docs/standards-manifest.yaml` with FOUND-012/013/014, CI-018/019, and OSSF-006/007 checks
* feat(catalog): add `_meta.typeProfiles` map with 7 repository types and per-type `exemptWorkflows`/`exemptHooks`/`scorecard_floor`/`scorecard_target` fields to `docs/reference/github-repos.json`
* feat(catalog): classify all 44 repos with `repositoryType`; add 13 schema integrity tests in `tests/tools/test_catalog_schema.py`
* feat(catalog): replace `dependabot` field with `renovate` across all 44 catalog entries; add `secretScanning` tracking field
* feat(catalog): add `releaseHealth` and `templateDrift` fields to all 44 catalog entries
* feat(skill): add type-conditional audit logic to `repo-compliance` skill; coordinator prompt now passes `repositoryType`, `scorecard_floor`, `scorecard_target`, `exempt_workflows`, and `exempt_hooks` to each domain agent
* feat(renovate): add self-hosted Renovate base config (`tools/renovate/renovate.json`) and deployment runbook (`tools/renovate/README.md`)
* feat(tools): add `tools/enable_secret_scanning.py` to enable GitHub native secret scanning and push protection across all catalog repos
* feat(tools): add `tools/refresh_catalog_release_health.py` to query GitHub releases API and update `releaseHealth` fields in the catalog
* feat(skills): add `.claude/skills/task-observer/SKILL.md` (verbatim from rebelytics/one-skill-to-rule-them-all); apply PR-49 observations to `pr-review` and `pr-fix` workflows: exception handler coverage check in Agent F, ruff PostToolUse import constraint in pr-fix editing guidance; add `docs/superpowers/plans/` plan documents for task-observer integration and GitHub activity portfolio review

### Chore

* chore(compliance): add `tools/create_community_health_pointers.py` to create
  `CODE_OF_CONDUCT.md` and `GOVERNANCE.md` pointer files across all org repos that are missing
  them; commits directly to default branch for unprotected repos, opens a PR for protected
  ones; add Codecov upload step to `coverage.yml`; add pointer files to this repo; extend
  `repo-compliance` skill with local catalog inventory section; add catalog paths to
  `.gitignore`; add S603/S607 per-file-ignores for `tools/**/*.py`

* chore(compliance): remediate OSSF Scorecard compliance gaps: add CodeQL, SonarCloud, Qlty
  coverage, REUSE, and release-signing workflows; harden all CI jobs with pinned action SHAs;
  add AGENTS.md, GEMINI.md, .codecov.yml, sonar-project.properties; expand pre-commit hooks
* chore(deps): add `requests>=2.33.1` to runtime dependencies in `pyproject.toml` for catalog tool scripts

### Fix

* fix(rulesets): split push-rule types into a dedicated `target: push` ruleset; the GitHub Rulesets API rejects `file_path_restriction` and `max_file_size` inside a `target: branch` body with HTTP 422 atomically, which had silently blocked every prior re-apply of the universal baseline since PR #95; ships new `ByronWilliamsCPA-push-baseline.json` and `williaby-push-baseline.json` (target: push, ~ALL include, file-path + size-cap rules), strips those rules from `*-universal.json`, documents the four-tier ruleset stack and structural reason in `docs/reference/org-rulesets/README.md`; `scripts/setup_org_rulesets.py` gains `validate_target_rule_compatibility` (fails fast on target/rule mismatch, exit code 5 `EXIT_TARGET_RULE_MISMATCH`), post-apply re-fetch with `detect_drift` for silently-dropped rule types (exit code 6 `EXIT_DRIFT_DETECTED`), and 11 new tests covering both validators plus the new exit-code paths; BW org now carries three active rulesets (16183607 universal, 16476283 push baseline new, 16183609 python tier) with `integration_id: 15368` persisted on all required status checks; williaby push-baseline JSON ships in lockstep but is not yet applied (williaby remains deferred per the rulesets-migration roadmap); clears CI-028, CI-029, and CI-032 findings from the reference-library audit retrospective

* fix(catalog): refresh `ByronWilliamsCPA/.claude` catalog entry: add missing workflow files, set `secretScanning.enabled` and `pushProtection` to true, update foundations flags, replace stale classic branch-protection block with ruleset summary, and correct the required-check name from `Security Gate Validation` to `Security Analysis / Security Gate Validation`; correct OSSF-008/009 manifest notes to reflect that secret scanning is free on public repos (no GHAS license required)

* fix(gitignore): ignore `.tmp-*.md` handoff files so session-boundary reference files written to the worktree root are never accidentally staged or committed
* fix(catalog): register `dependency-review.yml` and `postman-api-tests.yml` in `_meta.idealEntry.workflows.presentFromExpected` for the `ByronWilliamsCPA/.claude` repo; these workflows are in the expected set for config-type repos and their absence caused 6 schema tests to fail
* fix(docs): differentiate advisory link texts in `SECURITY.md` (was two identical "Security Advisories" links; now "Report a Vulnerability" and "Security Advisories"); remove AI-pattern words from `docs/response-aware-development.md` per CLAUDE-008 blacklist

* fix(ci): set `publish-results: false` in `scorecard.yml` reusable caller; when the workflow runs as a reusable callee the OIDC token `repository` claim resolves to the `.github` org repo (where the workflow lives) rather than the calling repo, so scorecard-action published results to the wrong repository and the job errored; `publish-results: false` skips the OIDC publish step while leaving SARIF upload to the Security tab intact
* fix(catalog): correct `repositoryType` from `python-template` to `template` for `cookiecutter-python-template`, `cookiecutter-template-sample`, and `template-sample`; `python-template` was never a valid taxonomy value and caused `test_all_repository_types_are_valid` to fail
* fix(ci): replace `dangoslen/changelog-enforcer` action in `pr-validation.yml` with a job-level
  `if` condition plus a `git merge-base` diff check; eliminates two failure modes -- Renovate PRs
  failing because the `dependencies` label is not yet visible to the GitHub API on the `opened`
  event, and normal PRs showing as "out of step" when `main` advances after the PR was created
* fix(hooks): correct Claude Code hook JSON field names in `tdd-enforcement-hook.sh` (`.tool` and
  `.args` -> `.tool_name` and `.tool_input`); hook was 100% inoperative as written
* fix(hooks): remove `-e` from `set -euo pipefail` in `tdd-enforcement-hook.sh`; PreToolUse hooks
  must not use `set -e` because any unhandled error exits non-zero and silently blocks all
  Write/Edit/MultiEdit tool calls
* fix(hooks): replace `exit 1` with `exit 2` in `tdd-enforcement-hook.sh` to match this repo's
  PreToolUse hook contract (exit 2 causes Claude Code to surface stdout as the block reason)
* fix(hooks): replace hardcoded `/home/byron/.claude/logs/` with `$HOME/.claude/logs/` and add
  `|| true` guards to `mkdir -p` and `log_tdd` so log-write failures do not block tool calls
* fix(hooks): guard `${TEST_FILES[@]}` array access under `set -u` to prevent unbound variable
  crash for `.go`, `.rs`, and `.php` files where no test path patterns are defined
* fix(docs): align CONTRIBUTING.md Python prerequisite with `requires-python = ">=3.10"` in
  `pyproject.toml` (was "Python 3.12 or higher")
* fix(ci): revert `security-analysis.yml` push trigger from `branches: ["**"]` to
  `branches: [main, master]` to avoid running security scans on every feature branch push
* fix(writing): remove em-dashes from `setup.sh` and `tools/check_docs.sh`; exposed by the
  no-em-dash hook scope extension that now covers `.sh` files
* fix(ci): grant `pull-requests: write` and `checks: write` to `ci.yml` caller; GitHub rejects
  reusable workflow callers at parse time when the caller's permissions block does not cover every
  scope the callee's `permissions:` block declares
* fix(ci): add `actions: read` to `security-analysis.yml` caller to cover the CodeQL job's
  job-level permission; strip caller to minimal structure to resolve callee-specific parse failure
* fix(tools): add `--exclude` flag to `validate_front_matter.py` to skip specified directories and files during front matter validation; update `.pre-commit-config.yaml` to exclude activity report and plan directories
* fix(tests): declare `_collect_md_files` in `ValidateFrontMatterModule` Protocol so type checkers and tests can access the internal function without bypassing the module interface
* fix(release): add `build_command = "uv lock"` to prevent uv.lock version drift after semantic releases
* fix(ci): remove stale `CVE-2022-42969` and `GHSA-w596-4wvx-j9j6` ignore entries from
  `osv-scanner.toml`; OSV database now tracks this vulnerability exclusively under
  `PYSEC-2022-42969`, making the CVE and GHSA aliases unused and causing scan failure
* fix(ci): disable `run-safety`, `run-codeql`, `run-dependency-review`, and `run-osv` in
  `security-analysis.yml` caller; Safety is not a project dependency (pip-audit covers the
  same surface), CodeQL SARIF upload and Dependency Review require GHAS on private repos,
  and osv-scanner-action v2.2.4 has a bug where IgnoredVulns entries that actively filter
  a finding are still reported as "unused" and exit 1 (fixed in osv-scanner >= 2.3.0;
  re-enable `run-osv` once the org workflow updates to that version)
* fix(docs): replace bare fenced code blocks with explicit language tags across documentation to satisfy MD040 (markdownlint-cli hook)
* fix(deps): upgrade pip from 26.0.1 to 26.1 to resolve GHSA-58qw-9mgm-455v
  (tar/ZIP interpretation conflict in pip; CVE-2026-3219)
* fix(ci): add `upload: never` to CodeQL analyze step in `codeql.yml`; SARIF upload
  requires GitHub Advanced Security which is not enabled on this private repo
* fix(deps): upgrade GitPython 3.1.46 to 3.1.48 to resolve three high-severity advisories:
  GHSA-x2qx-6953-8485 (unsafe multi_options before shlex.split, fixed in 3.1.47),
  GHSA-rpm5-65cw-6hj4 (command injection via Git options bypass, fixed in 3.1.47),
  GHSA-7545-fcxq-7j24 (path traversal in reference APIs, fixed in 3.1.48);
  GitPython is a transitive dependency; only `uv.lock` changes
* fix(hooks): add `|| true` guards to `mkdir -p` and `log()` write in
  `planning-bridge-gate.sh`; `set -euo pipefail` is present and unguarded
  failures in either call would silently block all tool calls matched by this
  PreToolUse hook (same class of defect as C-3/C-4 in tdd-enforcement-hook.sh)
* fix(ci): eliminate duplicate Bandit runs by setting `run-bandit: false` in `security-analysis.yml` caller (Bandit already runs twice via python-ci.yml); add SLSA Generic Generator provenance job to `release.yml`; migrate Scorecard to org-level reusable workflow at `ByronWilliamsCPA/.github`
* fix(docs): correct OpenSSF Best Practices badge ID from 12684 to 12685 in README.md and badge URLs; update all badge URL slugs from `claude_config` to `.claude`
* fix(agents): correct `ossf-badge-evaluator` automation URL base domain to `bestpractices.dev` and prefill path to `/{level}/edit`
* fix(config): remove PreToolUse/Bash hook that ran `pre-commit run --all-files` before every
  Bash call (including git status and ls); the Stop hook covers pre-commit validation at
  commit time without the per-call overhead
* fix(config): add force-push prohibition section to `.claude/rules/git-workflow.md` covering
  main, master, and develop; closes the gap where the branch-first rule blocked direct commits
  but said nothing about `git push --force`
* fix(hooks): fix `validate-frontmatter.sh` status-field extraction: add `head -1` to prevent
  multi-line match from causing spurious WARN on valid files; strip optional YAML quote characters
  from extracted value; fold `tr -d '\r'` into the `sed` expression; combine guard and extraction
  into a single pipeline
* fix(docs): tighten CLAUDE.md project-context instruction with a concrete `grep -rl` command
  to surface existing tier/standards docs before drafting new guides; replaces the vague
  "search docs/" instruction that caused documentation rework incidents
* fix(catalog): calibrate `scorecard.floor` to 5.0 and `scorecard.target` to 7.0 and set `ossfBadge.level` to `passing` in `_meta.idealEntry` to reflect solo-developer constraints
* fix(tests): add `pytest.mark` declarations, full type annotations, `tests/tools/__init__.py`, and repo-anchored `CATALOG` path to catalog schema tests
* fix(tests): replace `# type: ignore` suppressions with `TypedDict` definitions in catalog schema tests; fixes basedpyright strict-mode failures
* fix(skill): complete `homelab-infra` exempt workflow and hook lists in `repo-compliance` type-conditional example
* fix(renovate): align Renovate deployment runbook to GitHub App auth flow; add SHA-pin guidance for the bootstrap workflow
* fix(tools): restore missing `import json` in `refresh_catalog_release_health.py` after urllib-to-requests refactor
* fix(tools): guard `None` published_at in `refresh_catalog_release_health.py`; track error/no-release counts; align dry-run behaviour; add releaseHealth shape test
* fix(gitignore): remove duplicate `docs/reference/github-repos.md` entry from root `.gitignore`
* fix(renovate): replace invalid `pip_requirements`/`pip-compile` managers with `pep621` for
  `pyproject.toml` + `uv.lock` tracking; correct `matchDepTypes` to `project.dependencies` and
  `tool.uv.dev-dependencies`; replace non-functional `matchCategories: ["security"]` with
  `matchJsonata` on `vulnerabilitySeverity` for CRITICAL/HIGH CVE prioritisation

## v0.13.0 (2026-04-21)
### Documentation
* docs(compliance): correct agent count and domain inventory in design docs

- spec: add OSSF domain row to Scope of Standards table; update
  General row to reference &#34;six defined domains&#34; (was five)
- plan: update architecture summary from &#34;six domain agents&#34; to
  &#34;seven domain agents&#34;; update Task 1 commit message template
  from &#34;52 checks across 5 domains&#34; to &#34;61 checks across 6 domains&#34;

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`49aa54f`](https://github.com/ByronWilliamsCPA/.claude/commit/49aa54fbc6813b61ab88de44766d38e824532f2a))
* docs: register compliance system agents and skill in AGENTS-AND-SKILLS.md

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`e52e7f5`](https://github.com/ByronWilliamsCPA/.claude/commit/e52e7f537890c755dd0970304ad140dd19f0d37b))
* docs(compliance): add repo compliance system implementation plan

14-task plan covering standards manifest, 6 new domain agents,
devops-deployment-agent expansion, coordinator skill with
interactive and scheduled modes, and integration test against
pp-security-master.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`3f51954`](https://github.com/ByronWilliamsCPA/.claude/commit/3f5195430bb21f7af9752dbc462512b0f52da8af))
* docs(compliance): add repo compliance system design spec

Specifies a self-improving multi-agent system for auditing and
remediating repo drift against global standards. Covers six
domains, hybrid manifest+agent architecture, interactive and
scheduled modes, override file schema, and retrospective
self-improvement loop.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5e9448f`](https://github.com/ByronWilliamsCPA/.claude/commit/5e9448fa0e8d763a15a93c3f7e01dfd77aed3950))
### Feature
* feat(compliance): add ossf-compliance-auditor agent

Adds a dedicated OSSF audit domain to the repo compliance system:

- OSSF-001..005 checks in standards-manifest.yaml for gaps the
  Scorecard and Badge APIs cannot measure (badge application status,
  SECURITY.md private channel and SLA, CHANGELOG CVE IDs, API docs)
- ossf-compliance-auditor agent queries the live Scorecard REST API
  and Best Practices Badge API for current scores, falls back to the
  SARIF artifact from scorecard.yml when publish_results is false,
  supplements with GitHub API checks (branch protection, signed
  releases, private vulnerability reporting), and runs local file
  checks for OSSF-001..005
- Embedded knowledge of all 20 Scorecard checks and 5 Best Practices
  Badge gap criteria so every FINDING includes specific, executable
  remediation steps without requiring external research
- Routing table in SKILL.md updated; agent registered in catalog

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`2e2fe94`](https://github.com/ByronWilliamsCPA/.claude/commit/2e2fe94719c20b69ea4c35a336ab7ee6c74619ee))
* feat(compliance): add scheduled mode workflow and report template ([`eeb38f6`](https://github.com/ByronWilliamsCPA/.claude/commit/eeb38f635ccef7fd70a8f101547985c573e38884))
* feat(compliance): add interactive mode workflow ([`d1df129`](https://github.com/ByronWilliamsCPA/.claude/commit/d1df129f0857bcc33da9f73af35b965a3c2e8c61))
* feat(compliance): add repo-compliance skill entry point ([`98e6352`](https://github.com/ByronWilliamsCPA/.claude/commit/98e6352de443c63cff0b07e4d04b2f967ce0b607))
* feat(compliance): add CI compliance audit mode to devops-deployment-agent

Adds a CI Compliance Audit Mode section to the devops-deployment-agent
with detailed audit and remediation workflows for CI-001 through CI-013
checks, including sha-pinning, harden-runner, reusable workflow migration,
Codecov configuration, and workflow inventory evaluation.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5084072`](https://github.com/ByronWilliamsCPA/.claude/commit/50840720993461b7e3d03c8e6db4d8009729571a))
* feat(compliance): add compliance-retrospective agent ([`f4245ce`](https://github.com/ByronWilliamsCPA/.claude/commit/f4245ce66fb365a5e2c9e07a1fbdd8a6e80dfe56))
* feat(compliance): add general-compliance-auditor agent ([`d89c256`](https://github.com/ByronWilliamsCPA/.claude/commit/d89c2564bbac3ce0d3bc97736d8cff87698cb875))
* feat(compliance): add claude-docs-auditor agent ([`641e39a`](https://github.com/ByronWilliamsCPA/.claude/commit/641e39a68975c08f2a1f9abbf61cdfb3a7fe7966))
* feat(compliance): add pre-commit-auditor agent ([`c1369af`](https://github.com/ByronWilliamsCPA/.claude/commit/c1369af2a8a81dcda41540147c2c795c606b5df7))
* feat(compliance): add python-toolchain-auditor agent ([`1d310e1`](https://github.com/ByronWilliamsCPA/.claude/commit/1d310e13c4c2970e2937d0fa52b7b835a3b3b9ab))
* feat(compliance): add repo-foundations-auditor agent ([`abfb6d3`](https://github.com/ByronWilliamsCPA/.claude/commit/abfb6d36cffbdda899c77fe30fa0f8e0ab3daa23))
* feat(compliance): add CI-009..CI-013 checks for Codecov, SonarQube, and workflow inventory ([`e2a9010`](https://github.com/ByronWilliamsCPA/.claude/commit/e2a90108be0934a64b716cff162c61e508a1e45a))
* feat(compliance): add support files -- exclusions, report gitignore, override template ([`995c831`](https://github.com/ByronWilliamsCPA/.claude/commit/995c83172822271a47a06ef00991590902cf3d10))
* feat(compliance): add standards manifest with 52 checks across 5 domains ([`6e3eb78`](https://github.com/ByronWilliamsCPA/.claude/commit/6e3eb7877f4df3d5155588a7dd21cfc2c89f5a11))
### Fix
* fix(compliance): clarify CI-004 -- Qlty supplements Codecov, not replaces

The original description said Qlty &#34;replaces Codecov&#34; which contradicted
CI-009..CI-011 requiring Codecov config. Both coexist: Qlty runs code
quality checks (linting, smells, type checks) and Codecov tracks test
coverage history and PR deltas independently.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`59d5c91`](https://github.com/ByronWilliamsCPA/.claude/commit/59d5c9175e574774d5c9662ca2ff9c4dcb627cd7))
* fix(compliance): address pr-review findings in agents and workflows

- devops-deployment-agent: fix org name typo williamy -&gt; williaby;
  add SHA-pinned placeholder for reusable workflow ref (@main -&gt; @&lt;sha&gt;)
- ossf-compliance-auditor: fix FINDING block format (add colon to both
  instances); fix severity: high -&gt; important (align to system vocab)
- python-toolchain-auditor: generalize hard-coded pythonVersion = &#34;3.11&#34;
  to derive from project&#39;s requires-python constraint
- interactive-mode: add ossf-compliance-auditor to parallel dispatch
  (Step 2) and remediation dispatch (Step 5) -- agent was defined but
  never wired into either dispatch path
- scheduled-mode: fix &gt;&gt; to &gt; on first remote-repos write to prevent
  stale entries accumulating across runs
- standards-manifest FOUND-008: fix verify not_contains value from
  &lt;3.13 to &lt;3.15 to match the stated description

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`132d739`](https://github.com/ByronWilliamsCPA/.claude/commit/132d73956f4d6baaed40378984a31f283c118b2d))
* fix(ci): unblock CI failures -- ruff format and missing changelog

- Run ruff format on test_validate_front_matter.py (pre-existing
  format violation, file not in this PR&#39;s diff but flagged by CI)
- Add [Unreleased] section to CHANGELOG.md covering all feat/fix
  commits on this branch (unblocks Changelog Check CI gate)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`0a8cb65`](https://github.com/ByronWilliamsCPA/.claude/commit/0a8cb650bcea2e63878c4b2016d9768026b4d3e7))
* fix(compliance): handle both .codecov.yml and codecov.yaml filename variants

CI-009 verify string now accepts either filename; CI-010 and CI-011 use
&#34;OR&#34; syntax so the agent resolves whichever file exists before checking
content. devops-deployment-agent audit and remediation sections updated
to resolve the filename before applying content checks or creating the
config file.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d4a6a59`](https://github.com/ByronWilliamsCPA/.claude/commit/d4a6a5956e1ae5bb2eaebf2a14e03410ab49efeb))
* fix(docs): replace em-dash in AGENTS-AND-SKILLS.md rad skill entry ([`257bcba`](https://github.com/ByronWilliamsCPA/.claude/commit/257bcba7ec7622ed3efaaf3171701dc7cbd127b1))
* fix(compliance): clarify exclusion slug matching and override template path context ([`288be55`](https://github.com/ByronWilliamsCPA/.claude/commit/288be55ba771258b4d84b5cb5e3b256cd76171f2))
### Unknown
* Merge pull request #30 from ByronWilliamsCPA/feat/repo-compliance-system

feat(compliance): add self-improving multi-agent repo compliance system ([`1a1e132`](https://github.com/ByronWilliamsCPA/.claude/commit/1a1e132fd7b65c1036427a454aec3380a0a37f68))
## v0.12.2 (2026-04-19)
### Documentation
* docs(claude.md): add repo structure map, model selection, and scoped context

From image review of Claude Code best practices:
- Add repository structure map under Project context (WHAT framework)
- Add model selection table with Opus/Sonnet/Haiku guidance, pointing to
  supervisor.md for per-agent detail
- Add Scoped context section: documents three CLAUDE.md scopes and
  instructs Claude to proactively suggest folder-level files in projects
- Add folder-level CLAUDE.md authoring guides in .claude/agents/ and
  .claude/skills/ for use when editing those directories in this repo

Rejected from review: output naming conventions (Cowork desktop app
pattern, not applicable here), sprint workflow commands (proprietary
third-party product), social media tool integrations (irrelevant).
System Design/Feature Breakdown/Master Prompt documents (already
implemented more rigorously via ADRs, project-planning skill, TodoWrite).

https://claude.ai/code/session_01FPVFc244A2wx7UWNJKdjpy ([`8b03adc`](https://github.com/ByronWilliamsCPA/.claude/commit/8b03adce4814de51c312a5efa40e4b146e99da25))
### Fix
* fix(review): address PR #29 review findings

- Fix Plan subagent model: inherits caller&#39;s model, not fixed to sonnet
  (aligns CLAUDE.md with supervisor.md canonical reference)
- Add model: inherit to valid frontmatter values in agents/CLAUDE.md
- Soften 400-line agent system prompt limit to a target, not a hard rule
- Soften 200-line SKILL.md limit to a target, not a hard rule
- Add reference/ and templates/ to optional skill subdirectory list
- Clarify workflow file naming: single verb is valid when noun is implied
- Fix mcp_config.yaml path: add mcp/ prefix in agents/CLAUDE.md
- Fix repo structure tree: use ~/dev/.claude/ (not ~/.claude/), add
  commands/ and mcp/ directories
- Add text language tag to fenced code block (MD040)
- Bump version to 1.4.0, Last Updated to 2026-04-19

Addresses: Copilot comments (4), agent findings (6).
Human-only items (PR Validation startup_failure, PR body motivation,
frontmatter policy for meta-docs) not included.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`79ba360`](https://github.com/ByronWilliamsCPA/.claude/commit/79ba36068093f6b3866cf46a521488f892f0ad45))
### Unknown
* Merge pull request #29 from ByronWilliamsCPA/claude/review-structure-improvements-BDhiw

docs(claude.md): add repo structure map, model selection, and scoped context ([`a7903d0`](https://github.com/ByronWilliamsCPA/.claude/commit/a7903d0d21e926397c0869117db00b5186e0864a))
## v0.12.1 (2026-04-19)
### Fix
* fix(hooks): remove remaining em-dashes from frontmatter validator

Replace em-dash in exit-code comment with parentheses per writing rules.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`e65d4b7`](https://github.com/ByronWilliamsCPA/.claude/commit/e65d4b741c3f2592d5139ecdddf6e9c0dcf14ba0))
* fix(hooks): exclude CLAUDE.md meta-docs from frontmatter validation

CLAUDE.md files inside agents/ and skills/ are folder-level convention
guides, not agent or skill definitions. The validate-frontmatter.sh hook
previously warned on every session edit because these files have no YAML
frontmatter. Add a basename check to skip any file literally named
CLAUDE.md after it matches the directory pattern.

Also extends the target guard to cover skills/*.md alongside agents/*.md,
and replaces em-dashes in warn messages with semicolons per writing rules.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`ad1f825`](https://github.com/ByronWilliamsCPA/.claude/commit/ad1f825d2e9022664b0d285275235834eebfa2b3))
* fix(ci): migrate to python-ci.yml and add checks: write to fix PR Validation startup_failure

The core-validation job called the deprecated python-pr-validation.yml reusable
workflow but did not grant checks: write permission, which the reusable workflow
requires. GitHub Actions fails the entire caller workflow with startup_failure
when a reusable workflow requests a permission the caller job does not grant.

Changes:
- Replace python-pr-validation.yml reference with python-ci.yml (the actively
  maintained successor) at current HEAD SHA 16979833
- Add checks: write to the core-validation job permissions block
- Enable dead-code detection via enable-dead-code-check: true (python-ci.yml
  native support, removing duplication with the standalone dead-code job)
- Remove deprecated inputs that do not exist in python-ci.yml
- Fix em-dashes in scripts/validate-frontmatter.sh (writing rule compliance)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`8e8aa30`](https://github.com/ByronWilliamsCPA/.claude/commit/8e8aa30e8ac4562a42a6d0134273fed628db8c1f))
## v0.12.0 (2026-04-19)
### Documentation
* docs(ai-detection-agent): align spec with actual service and integrate research

Update ai-detection-agent.md to reflect the real ai-text-detector Docker
service (hostname ai-text-detector:8000, not binoculars:8421). The unified
FastAPI service exposes 8 local detectors via a single /detect call, plus
sentence-level detection and C2PA provenance. The previous spec was missing
MAGE, RADAR, Ghostbuster, GPT-2 Detector, LLM-DetectAIve, and KGW Watermark.

Integrate findings from three research files in tmp_cleanup/ai_detection into
the landscape reference: BFI/UChicago independent Pangram audit (Jabarian &amp;
Imas 2025), Raidar and Glimpse detector profiles, non-native English bias data
(Liang 2023), EU AI Act Article 50 timeline, provider watermark status table,
semantic watermarks research, Scribbr/QuillBot profiles, independent
benchmarking baselines, quarterly benchmark protocol, and 12 new references.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`ee06921`](https://github.com/ByronWilliamsCPA/.claude/commit/ee0692131f9956f12f75207aaf1cda35554f0dbb))
### Feature
* feat: add ai-detection-agent with Pangram API and landscape reference

Adds a two-mode AI content detection specialist agent:
- Mode 1: evaluates files/text via Pangram predict() and predict_short(),
  with score interpretation thresholds and segment-level breakdown
- Mode 2: audits writing pipeline outputs against the detection landscape
  to identify vulnerabilities and recommend reference library revisions

Detector mix: Pangram (API), Binoculars + Fast-DetectGPT (self-hosted P40),
Sapling and Winston AI (public APIs). Skips enterprise-gated tools
(Originality.ai, GPTZero, Copyleaks) and discredited legacy tools (ZeroGPT).

Also adds:
- .claude/standards/ai-detection-landscape.md: full technical reference
  covering detector profiles, empirical scoring matrix, SynthID-Text
  watermarking, StealthRL threat model, and prioritized remediation actions
- AGENTS-AND-SKILLS.md entry under Writing &amp; Content
- supervisor.md agent assignment rows for detection and audit tasks

https://claude.ai/code/session_019GKjs88u1rXbBQZrrFBWha ([`df1205d`](https://github.com/ByronWilliamsCPA/.claude/commit/df1205d6b7e3bf2c9b353d3db04e9e7faf9a1e7c))
### Fix
* fix(ai-detection-agent): address Copilot PR review comments

- Clarify that local stack is no-cost; Sapling/Winston may consume API quota
- Fix Sapling output note: already normalized to 0-1, not &#34;divide by 1&#34;
- Use N-based ensemble thresholds instead of hardcoded &#34;of 6&#34; counts
- Update Sapling/Winston &#34;When to call&#34; to &#34;When key is configured&#34;
- Add disambiguation note: RADAR (adversarial classifier) vs Raidar (ICLR 2024)
- Add profiles for 6 undocumented local stack detectors: MAGE, RADAR, Ghostbuster,
  GPT-2 Detector, LLM-DetectAIve, KGW Watermark
- Fix landscape.md header format: colon inside bold labels
- Reframe AGENTS-AND-SKILLS.md entry: Pangram is opt-in, not part of standard workflow
- Fix MD032 (blank lines before lists) and MD060 (table separator spacing)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`be6ca78`](https://github.com/ByronWilliamsCPA/.claude/commit/be6ca7838f12699e2b841f87b4179e20eb1fc43a))
### Refactor
* refactor(ai-detection-agent): make Pangram opt-in, local detectors default

Pangram is now called only when explicitly requested by the caller to
preserve API credits. The default scoring path runs Binoculars,
Fast-DetectGPT, Sapling, and Winston AI on every request at no
marginal cost.

Changes:
- Introduce detector stack table with clear call-frequency policy
- Add curl call patterns for Binoculars, Fast-DetectGPT, Sapling,
  and Winston AI
- Move Pangram to a clearly marked opt-in section
- Update output format to show multi-detector score table
- Add consensus interpretation rule (disagree = diagnostic, not error)
- Remove references to enterprise-gated tools (Originality, Copyleaks)
  from operational rules

https://claude.ai/code/session_019GKjs88u1rXbBQZrrFBWha ([`8e045d3`](https://github.com/ByronWilliamsCPA/.claude/commit/8e045d373735e87fbf24ff7be0d1e6647e91f032))
### Unknown
* Merge pull request #28 from ByronWilliamsCPA/feat/add-ai-detection-agent

feat(ai-detection-agent): add detection agent with full service integration and research landscape ([`b103f00`](https://github.com/ByronWilliamsCPA/.claude/commit/b103f00f7160ecb393d3dc7ba87085a9b45cac54))
## v0.11.0 (2026-04-18)
### Chore
* chore: merge main into feat/pr-fix-expand-fix-scope

Resolve CHANGELOG.md conflict by placing [Unreleased] above v0.10.0.
Resolve uv.lock conflict by taking main version 0.9.1.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`9909512`](https://github.com/ByronWilliamsCPA/.claude/commit/990951216e01befded747ad2f0dddf876fe07974))
### Unknown
* Merge pull request #27 from ByronWilliamsCPA/feat/pr-fix-expand-fix-scope

feat(pr-fix): expand fix scope and add agent evaluation for non-auto-fixable items ([`373a88b`](https://github.com/ByronWilliamsCPA/.claude/commit/373a88bef04ff2b516a91d9226545ebc0dba420b))
## v0.10.0 (2026-04-18)
### Chore
* chore(deps): sync uv.lock to 0.9.0

Align uv.lock with pyproject.toml version bump that landed on main.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a327049`](https://github.com/ByronWilliamsCPA/.claude/commit/a327049056921a0bc9dcec1bae44b292f48ed891))
### Feature
* feat(setup): auto-sync local plugin cache after submodule updates

Plugin install copies files from the submodule into ~/.claude/plugins/cache/
at install time, so submodule pointer updates do not propagate until the
plugin cache is refreshed. Without this, the namespaced skill form (used
by cross-skill handoffs like writing-plans -&gt; superpowers:subagent-driven-development)
silently runs against stale vendor code after a git submodule update.

Adds sync_local_plugins() called after ensure_submodules in the main flow.
Skips remote claude-plugins-official plugins (those auto-update from
GitHub). Honors --dry-run, gracefully skips when claude CLI is absent or
plugins are not yet installed.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`be77b9a`](https://github.com/ByronWilliamsCPA/.claude/commit/be77b9a695770a09a0fc835c3e095f881e10a3f1))
* feat(setup): add vendored plugin installer and doctor check

Register vendored submodules (superpowers, anthropics-skills) as local
Claude Code marketplaces and install the 10 expected plugins at user scope.
Without this step, namespaced skill invocations (e.g.
superpowers:subagent-driven-development, used by writing-plans) silently
fall through because Claude Code treats symlink-loaded and plugin-loaded
skills as distinct identifiers.

Doctor mode (./setup.sh doctor) now verifies the expected plugin list is
installed and flags missing entries with a pointer to the installer.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`3da1bd1`](https://github.com/ByronWilliamsCPA/.claude/commit/3da1bd1aef57f43bcd1ec38dfc1f1e9bc00370ea))
### Fix
* fix(setup): address pr-review findings on vendored plugin installer

install-vendored-plugins.sh:
- Use pwd -P for REPO_DIR to resolve ~/.claude/scripts symlink correctly
- Replace || true on marketplace and plugin list with explicit error exit
- Replace GNU-only grep -qE (\s, \b) with grep -qF for POSIX portability
- Surface stderr in error messages for marketplace add and plugin install
- Add pre-flight check that claude-plugins-official is registered before
  attempting remote plugin installs
- Remove unused log_info() function

setup.sh doctor():
- Replace || true on plugin list with explicit error path that increments
  broken counter so doctor fails on CLI errors
- Replace GNU grep with grep -qF
- Absolute-path the install command in the missing-plugin warning
- Make claude CLI absence fail-closed: increment broken rather than skip

setup.sh sync_local_plugins():
- Replace || true on plugin list with explicit return 1
- Replace GNU grep with grep -qF
- Surface stderr in log_warn on plugin update failure
- Absolute-path the install command in the not-installed skip message

README.md: fix anthropics-skills -&gt; anthropic-agent-skills in narrative

CHANGELOG.md: add [Unreleased] section covering the three new features

.pre-commit-config.yaml: forward-port the TruffleHog worktree fix
(already on main via a290ab5; included here so pre-commit passes
locally when committing in this worktree before merge)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`230dc09`](https://github.com/ByronWilliamsCPA/.claude/commit/230dc0936c644da09b7a6ceb2fe21a4520e66727))
### Unknown
* Merge pull request #25 from ByronWilliamsCPA/chore/settings-hardening-and-plugins

chore(setup): add vendored plugin installer and sync uv.lock ([`a7d63f0`](https://github.com/ByronWilliamsCPA/.claude/commit/a7d63f0d9e26da7093bd783985732620dbcd70c1))
## v0.9.1 (2026-04-18)
### Documentation
* docs(standards): add structured output contracts to agent-to-agent interfaces

phase-gate: scope-analyzer and phase-reviewer agents now return typed JSON
envelopes (deliverables array with status enum, gates array with PASS/FAIL,
coverage_pct float, verdict) so the synthesis step reads fields rather than
parsing prose tables.

test-coverage: test-reviewer must return {&#34;verdict&#34;: &#34;APPROVE&#34;|&#34;NEEDS_WORK&#34;,
&#34;issues&#34;: [str]}. The issues list is required on NEEDS_WORK and passed
verbatim to the writer as the revision brief. Unparseable output is treated
as NEEDS_WORK.

pr-fix: stuck-loop PAL diagnosis now returns {&#34;can_retry&#34;: bool,
&#34;root_cause&#34;: str, &#34;blocker&#34;: str, &#34;proposed_fix&#34;: str}. The can_retry
field drives the options presented to the user — proposed_fix surfaces as
Option 1 when retrying is viable, blocker surfaces when it is not.

supervisor.md: adds Agent Output Format section with the when/when-not rule
(structure for machine-consumed results, prose for human-facing output),
the five standard envelope shapes, and an example task prompt snippet.

https://claude.ai/code/session_013eTYt5xiLPb87w7gnZZ9CR ([`745fe02`](https://github.com/ByronWilliamsCPA/.claude/commit/745fe022992869c778e9921fb81c5a6b9d3977a0))
* docs(standards): apply lessons from Claude Code system prompt analysis

Add verification failure modes to testing.md: names the specific LLM
shortcuts that pass as verification but are not (reading source, running
test suite only, type-check reliance), and introduces the BLOCKED verdict
for when runtime observation is unavailable.

Add authorization failure modes to settings-and-permissions.md: documents
that questions are not consent and silence is not consent, two runtime
principles not captured by the permissions schema.

Trim CLAUDE.md development philosophy section: removes five generic
priority items that Claude follows without instruction, retaining only
the project-specific scope tracing rule.

https://claude.ai/code/session_013eTYt5xiLPb87w7gnZZ9CR ([`0cfd192`](https://github.com/ByronWilliamsCPA/.claude/commit/0cfd1920b3e8810122be4c1a5895a4ad8ced23e0))
### Feature
* feat(pr-fix): expand fix scope and add agent evaluation for non-auto-fixable items

Step 2 now shows tier distribution (Critical/Important/Suggested/
Informational) so the user knows the full scope before confirming.
All Critical, Important, and Suggested findings are addressed in every
run. Informational findings are addressed when simple and low-risk.

Priority 3 &#34;Always skip&#34; table replaced with &#34;Assign to specialized
agent&#34; table: test coverage gaps go to test-writer, type design issues
go to type-design-analyzer, cognitive complexity and complex logic bugs
go to code-reviewer, security vulnerabilities go to security-auditor,
path-injection findings go to owasp-web, and diagram findings go to
diagram-maintenance-agent. Agent evaluations run in parallel after all
auto-fixes and their outputs are included in the Step 6 commit options.

Only three categories remain as &#34;human-only&#34;: design debates requiring
stakeholder input, GitGuardian secret detections, and deliberate
product decisions. All other previously-deferred findings now have an
agent evaluation path.

Error handling table updated to reflect agent assignment instead of
silent deferral.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`88f5185`](https://github.com/ByronWilliamsCPA/.claude/commit/88f51852216a100c5744bf169d2cb26cb4979111))
### Fix
* fix(pr-fix): remove em-dashes and add CHANGELOG entry

- Replace em-dashes with comma/semicolon in Step 2 Tier coverage block
- Add [Unreleased] CHANGELOG entry for the expanded fix scope feature
- Sync uv.lock version from 0.8.1 to 0.9.0

Addresses pr-review Critical findings on PR #27.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`29dfef1`](https://github.com/ByronWilliamsCPA/.claude/commit/29dfef13344e54b65f2765bbdd087d02aa4541c1))
* fix(review): address Copilot findings on PR #26 documentation

- supervisor.md: expand evidence rule to list 4 acceptable field
  patterns (reason, issues, blocker/proposed_fix, domain arrays);
  add concrete JSON examples alongside schema notation in envelope table
- phase-gate/SKILL.md: fix NOT STARTED -&gt; NOT_STARTED in scope-analyzer
  prompt; add BLOCKED verdict + required blocker field to phase-reviewer;
  add concrete JSON examples to both agent task prompts
- test-coverage/SKILL.md: label schema notation explicitly; add concrete
  APPROVE and NEEDS_WORK JSON examples for test-reviewer envelope
- pr-fix.md: replace em-dashes in PAL JSON field comments; restructure
  tiered_consensus prompt to use readable JSON block with concrete examples

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d26817f`](https://github.com/ByronWilliamsCPA/.claude/commit/d26817f4f244b78bd3b94ac2bd480b0460c43310))
* fix(ci): handle TruffleHog git scanner failure in git worktrees

In a git worktree, .git is a symlink file rather than a directory.
TruffleHog&#39;s git source tries to open .git/index as a path and errors
with &#34;not a directory&#34;. Wrap the hook entry in a bash conditional:
in worktrees, scan only staged files via filesystem mode; in normal
checkouts, use the original git history scan unchanged.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a290ab5`](https://github.com/ByronWilliamsCPA/.claude/commit/a290ab50f80f745c764341358fb52df2c2f1bbf6))
### Unknown
* Merge pull request #26 from ByronWilliamsCPA/claude/review-system-prompts-yi29Y

docs(standards): verification failure modes and structured agent output contracts ([`ad95d1e`](https://github.com/ByronWilliamsCPA/.claude/commit/ad95d1e7ccca978a8457302963d601aa9a7d1d69))
## v0.9.0 (2026-04-17)
### Feature
* feat(skills): add security hotspot coverage to pr-review and sonarcloud skills

Add Step 4f to pr-review workflow to fetch security hotspots via
search_security_hotspots, which is a separate API queue from issues.
Update Step 4e and Step 9 report to surface both issues and hotspots.

Extend sonarcloud skill (v2.1.0) with hotspots mode, triage mode, and
updated Summary mode; both modes use search_security_hotspots separately
from search_sonar_issues_in_projects to prevent silent misses.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`f399bf0`](https://github.com/ByronWilliamsCPA/.claude/commit/f399bf0022446770da2df263bf9a9b967c9c2af5))
### Fix
* fix(skills): correct em-dashes, step ordering, and SONAR_HOTSPOTS handoff

sonarcloud/SKILL.md:
- Replace 5 em-dashes in newly-added hotspot/triage lines with colons
  or semicolons (CLAUDE.md no-em-dash rule; newly introduced by this PR)
- Update module header to mention security hotspots alongside issues

pr-review/workflows/pr-review.md:
- Rename Step 4d to 4g (pre-flight SonarCloud config check) so the
  step label matches its position after 4f in the workflow file
- Add SONAR_HOTSPOTS to Step 11 pass-forward list (Step 4e promises to
  pass both SONAR_FINDINGS and SONAR_HOTSPOTS to pr-fix; Step 11 was
  only forwarding SONAR_FINDINGS)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`be4d908`](https://github.com/ByronWilliamsCPA/.claude/commit/be4d908d577ac0c9f4036b57a36609cbbedbbaad))
* fix(security): resolve S7637 and S5852 hotspots

Pin actions/checkout and actions/upload-artifact to full commit SHAs
in ci.yml, docs.yml, and security-analysis.yml (S7637 unpinned actions).

Improve _strip_code_blocks: fix CRLF close-pattern (add \\r? before
end anchor), update docstring to correctly document that unclosed-fence
content is excluded (not returned), remove two stale re.sub comments,
fix em-dash in H1 error message, and tighten the docstring (S5852 fix
was already committed; this hardens the implementation).

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`57f0fcf`](https://github.com/ByronWilliamsCPA/.claude/commit/57f0fcf355bdc5888deade8718ccfbdf1f98767f))
* fix(security): resolve all 17 SonarCloud security hotspots

S5852 - ReDoS (tools/validate_front_matter.py):
- Replace (.+?)\s*$ with (\S[^\r\n]*) in H1_RE; removes ambiguous
  backtracking between lazy group and trailing \s*$
- Replace .*? with DOTALL regex for code-block stripping with
  _strip_code_blocks(): line-by-line O(n) helper, no backtracking

S7637 - Unpinned GitHub Actions (pin to full commit SHA):
- astral-sh/setup-uv@v4 -&gt; @38f3f104 # v4.2.0 (ci, docs, release x2,
  security-analysis, pr-validation)
- dangoslen/changelog-enforcer@v3 -&gt; @204e7d3e # v3
- lycheeverse/lychee-action@v1 -&gt; @2b973e86 # v1
- python-semantic-release@v9 -&gt; @fd8c509d # v9.9.0
- pypa/gh-action-pypi-publish@release/v1 -&gt; @cef22109 # release/v1
- ByronWilliamsCPA/.github org workflows@main -&gt; @c22009cc
  (pr-validation, python-compatibility, sbom)

S7635 - secrets: inherit over-share:
- Verified both called org workflows use zero secrets
- Removed secrets: inherit from pr-validation.yml and
  python-compatibility.yml

Sync uv.lock claude-config version 0.8.0 -&gt; 0.8.1

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a8583f2`](https://github.com/ByronWilliamsCPA/.claude/commit/a8583f2ae5502a165f6b3ff166ef4cb5b92df8d2))
### Test
* test(validate_front_matter): add _strip_code_blocks coverage

Add 10 tests for _strip_code_blocks covering:
- properly closed backtick and tilde fences
- fence marker lines are excluded from result
- CRLF line endings close pattern
- unclosed fence excludes content from opener onward
- info strings on opening fence (e.g. ```python)
- mixed fence types (backtick vs tilde non-interference)
- multiple consecutive code blocks
- empty content and no-fence content

Also add [Unreleased] section to CHANGELOG.md covering the feat and
fix commits in this PR.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`087c44f`](https://github.com/ByronWilliamsCPA/.claude/commit/087c44f46834073d0cb95afda9138b2baef96291))
### Unknown
* Merge pull request #24 from ByronWilliamsCPA/fix/security-hotspots

fix(security): resolve all 17 SonarCloud security hotspots ([`1c384e7`](https://github.com/ByronWilliamsCPA/.claude/commit/1c384e7842751895c13d9caf716ed93ab416eac6))
## v0.8.1 (2026-04-14)
### Fix
* fix(quality): resolve all SonarQube issues and sync uv.lock version

- Mark S2083 path-traversal false positives in SonarCloud (check_type_hints,
  validate_front_matter): paths reconstructed from trusted CWD base
- Refactor _format_sonar_layer (S3776): extract _gate_status_line,
  _format_condition_line, _format_issue_lines helpers; complexity 19 -&gt; ~3
- Add explicit return 0 to shell functions: check_docs.sh:check,
  track-mcp-usage.sh:reset_metrics, run_tests.sh (8 functions),
  test_helper.bash:source_script_functions inner main (S7682)
- Replace [ with [[ in run_tests.sh (13 conditionals) (S7688)
- Remove unused local variable skipped_tests in run_tests.sh (S1481)
- Sync uv.lock claude-config version from 0.7.1 to 0.8.0

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c1fa1ac`](https://github.com/ByronWilliamsCPA/.claude/commit/c1fa1ac8a9297e0aa070bb0538c900050498d142))
### Unknown
* Merge pull request #23 from ByronWilliamsCPA/fix/sonarqube-issues-uv-lock

fix(quality): resolve all SonarQube issues and sync uv.lock version ([`8bcdc58`](https://github.com/ByronWilliamsCPA/.claude/commit/8bcdc5875d5e997ba2f19de42691737f3dd02523))
## v0.8.0 (2026-04-14)
### Chore
* chore(deps): sync uv.lock to v0.7.1

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`4183dd0`](https://github.com/ByronWilliamsCPA/.claude/commit/4183dd08bd1ec2cdf0a6782ed8ca3e7cb977b951))
* chore(config): document global settings hardening and skill cleanup

Captures the configuration changes applied to ~/.claude/settings.json on
2026-04-11 to address friction observed in 30-day usage analysis (561
messages, 93 sessions, 1327 Bash invocations).

Settings changes (live file, not git-tracked):
- env: adaptive thinking disabled, effort level pinned via env var,
  autocompact lowered to 75%, tool search aggression raised to auto:5,
  bash and API timeouts aligned to real workloads
- permissions.defaultMode: acceptEdits to bypass the .claude/skills/
  protected-directory prompt regression in v2.1.78+
- permissions.allow: expanded from 5 to 30 calibrated entries including
  git commit and git add
- permissions.deny: secrets path rules (defense-in-depth)
- enableAllProjectMcpServers: false (Trail of Bits supply-chain fix)
- postgres removed from global MCP list (per-repo as needed)

Skill cleanup (local, untracked):
- Removed testing-variant-b-r2 and test-coverage-variant-b which had
  frontmatter name collisions with canonical skills, causing duplicate
  registration in every session&#39;s context. Workspaces preserved.

Follow-ups staged in the doc:
- PAL MCP repo review (evaluate which tools remain useful post-hardening)
- CLAUDE.md refactor to trim ~3.5k token session-start cost

Full rationale, rollback steps, and verification checks in the doc.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`9011202`](https://github.com/ByronWilliamsCPA/.claude/commit/9011202c3995f93b0e07670e2ac6b92a9100daa6))
* chore: update superpowers submodule with additional writing-plans em-dash fix ([`81a4303`](https://github.com/ByronWilliamsCPA/.claude/commit/81a430384a071e87ffe07550d83daa93ce03a856))
* chore: update superpowers submodule with writing-plans em-dash fixes ([`b166992`](https://github.com/ByronWilliamsCPA/.claude/commit/b16699218316a16194a038d4aea9ec14e487595e))
* chore: update superpowers submodule (writing-plans skill update) ([`4b10ec2`](https://github.com/ByronWilliamsCPA/.claude/commit/4b10ec2cc97783c56af2df1abae52ea847d09352))
### Documentation
* docs(changelog): add Features section to v0.7.1 for new skills

Two feat(skills): commits on this branch were not reflected in the
CHANGELOG. Added a Features section under v0.7.1 with entries for:

- feasibility-check skill (commit 690c617)
- pipeline-coordinator-reference skill (commit e271c57)

Required by CLAUDE.md OpenSSF baseline: update CHANGELOG for all
feat/fix/perf/breaking changes before release.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5a72fea`](https://github.com/ByronWilliamsCPA/.claude/commit/5a72feae54a81377e7dafdd4fad695409c157f35))
* docs(rules): add ## Sources citation footers to all rules files

Appended authoritative reference sections to the seven rules files that
were missing them: git-workflow.md, supervisor.md, writing.md, testing.md,
python.md, mcp-strategy.md, and pre-commit.md. Existing content unchanged.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`1710015`](https://github.com/ByronWilliamsCPA/.claude/commit/1710015b18697b917aea2c2401e5997d2e9b0fc1))
* docs: add platform-audit-checklist.md seeded with two observed drift types ([`1413596`](https://github.com/ByronWilliamsCPA/.claude/commit/14135960e3c8076714e1f83efe3936640d330fcc))
* docs(standards): add --bare flag to scripted claude -p examples ([`3042042`](https://github.com/ByronWilliamsCPA/.claude/commit/30420429b26e42bc7814477ff6eb3c87a95e7d0b))
* docs(git-workflow): add PR size calibration table with Anthropic p50/p90/p99 data ([`90eb7a2`](https://github.com/ByronWilliamsCPA/.claude/commit/90eb7a2fdb55111a2e52da389a4a0bc1ddf67931))
### Feature
* feat(skills): add pipeline-coordinator-reference pattern guide

Adds a non-user-invokable reference skill demonstrating the
Command -&gt; Agent -&gt; Skill coordinator pattern with explicit
Data Contract blocks between pipeline stages. Uses test-coverage
pipeline as the concrete example.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`e271c57`](https://github.com/ByronWilliamsCPA/.claude/commit/e271c57bd5a5d7e72c1732e1ee1ba9f8007a2dfb))
* feat(skills): add feasibility-check skill for lightweight GO/DEFER gate before writing-plans

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`690c617`](https://github.com/ByronWilliamsCPA/.claude/commit/690c6175a3121ae1879e1773a368c97fae21a287))
### Fix
* fix(pr-review): add two-stage Copilot trigger with comment fallback

The reviewer API call (`copilot-pull-request-reviewer`) returns 422 on
repos where Copilot auto-assignment is not configured in settings. This
causes Step 1 to silently skip the Copilot request on every pr-review run.

Fix: two-stage trigger.
- Stage 1a: try the reviewer API (works when auto-assign is enabled)
- Stage 1b: if 422, fall back to posting `@github-copilot review` comment
  (the mention-based trigger that works for all account types)

Also documents the one-time fix: enable auto-assignment at
github.com/{OWNER}/{REPO}/settings/copilot_review_policies so Stage 1a
succeeds on every PR without needing the fallback.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7fb1b0e`](https://github.com/ByronWilliamsCPA/.claude/commit/7fb1b0e2e7f7296b26d9346867cb15078ea1e763))
* fix(review): address Copilot findings on PR #22

Two corrections flagged by Copilot inline review:

1. feasibility-check/SKILL.md:51 -- output template used
   `status: active` which is not a valid CommonFM schema value.
   Changed to `status: published` (valid values: draft, in-review,
   published per tools/frontmatter_contract/models.py:110).

2. pipeline-coordinator-reference/SKILL.md:35 -- relative path
   `skills/dispatching-parallel-agents/SKILL.md` won&#39;t resolve from
   anywhere in the repo. Corrected to full prefix
   `.claude/skills/dispatching-parallel-agents/SKILL.md` matching
   every other internal reference in the same file.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7041e9a`](https://github.com/ByronWilliamsCPA/.claude/commit/7041e9a49931630d84420c2c500f8c950bc85afe))
* fix(writing): replace em-dashes in settings-hardening doc

Five em-dash violations introduced in the new
docs/development/settings-hardening-2026-04-11.md file.
Replaced with colons and semicolons per CLAUDE.md hard rule.

Lines affected: 86, 138, 139, 140, 153.
Flagged by Copilot (3 of 5) and Agent A (all 5) in PR review.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`f8afb5e`](https://github.com/ByronWilliamsCPA/.claude/commit/f8afb5e92f48f6cb80905890276af84e36b4faf2))
* fix(skills): address quality review gaps in pipeline-coordinator-reference

- Document coordinator abort behavior on validation failure
- Add repo_root passthrough to Stage 2-&gt;3 Data Contract
- Add repo_root and threshold_pct to Stage 1 validation rules
- Add schema_version to Stage 3-&gt;4 Data Contract
- Add errors-array validation rule to Stage 1 rules

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`b5a383b`](https://github.com/ByronWilliamsCPA/.claude/commit/b5a383bea2c3b7c0317eb07aadac2819a63d976f))
### Unknown
* Merge pull request #22 from ByronWilliamsCPA/feat/best-practice-gaps-2026-04-11

feat: implement 2026-04-11 best-practice review gaps (13 tasks) ([`b3bd7ac`](https://github.com/ByronWilliamsCPA/.claude/commit/b3bd7ac77c513a857c8cb5161a75f43752c24033))
## v0.7.1 (2026-04-13)
### Fix
* fix(pr-review): use correct Copilot bot username in Step 1

The primary reviewer request used `gh pr edit --add-reviewer &#34;copilot&#34;`.
The username &#34;copilot&#34; does not exist on GitHub (returns 404), so Copilot
was never added as a reviewer. The correct bot login is
`copilot-pull-request-reviewer`, confirmed from prior PRs that had Copilot
reviews (those were requested manually via the GitHub UI).

Changes:
- Replace the broken `gh pr edit` call with the API endpoint directly,
  using the verified bot username `copilot-pull-request-reviewer`
- Capture exit code explicitly so success/failure is always recorded
- Add a warning note prohibiting the wrong `--add-reviewer &#34;copilot&#34;` form
- Make the PR comment template conditional on actual COPILOT_STATUS

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`4f92e79`](https://github.com/ByronWilliamsCPA/.claude/commit/4f92e79413cd84f3820e16f75c92fa25ce2926c0))
## v0.7.0 (2026-04-13)
### Chore
* chore(changelog): add unreleased entry for PAL validation feature

Add CHANGELOG entry for the PAL multi-model validation feat commit.
Configure MD024 with siblings_only in .markdownlint.json so version
sections in CHANGELOG can reuse standard headings (Features, Bug Fixes,
etc.) without false-positive duplicate-heading warnings.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`ac83c87`](https://github.com/ByronWilliamsCPA/.claude/commit/ac83c877aece70fe31bb830784a5359881acfee7))
### Feature
* feat(skills): add PAL multi-model validation and 22-item PR workflow improvements

Implement all accepted PAL tool insertion points with config variables
across pr-review.md and pr-fix.md. Add Agent L (architectural consensus
via mcp__pal__consensus), Step 7b (Critical-tier false-positive filter
plus security validation via mcp__pal__tiered_consensus), Priority 2
propose-and-confirm chat validation (Candidate 3, reinstated), Priority 4
test tautology chat validation, and Step 9 stuck-loop diagnosis.

Expose PAL_CHAT_MODEL, PAL_CONSENSUS_MODELS, PAL_TIERED_LEVEL, and
PAL_TIERED_THINKING as config variables at the top of each workflow file.

Also apply all 22 roadmap items to commit.md and pr.md: Step 1b
self-review scan, CHANGELOG enforcement, Acceptance Criteria and
Migration/Rollback sections in PR template, staging order correction,
and pre-existing lint fixes throughout all four files.

Add docs/pr-workflow-improvement-plan.md: the 22-item evaluation roadmap
derived from GPT-5.2 subagent review and PAL level-3 tiered consensus.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`6e7e96b`](https://github.com/ByronWilliamsCPA/.claude/commit/6e7e96ba635883a1d3316e5ec54f6a573bdf421c))
### Fix
* fix(writing): remove em-dashes and apply structural fixes to skill workflows

Remove all em-dash violations from four skill workflow files in compliance
with the CLAUDE.md hard rule. Apply structural fixes identified during PR
review of feat/pal-validation-workflow-improvements:

Em-dash removal (affects all four files):
- commit.md: 4 instances
- pr.md: 1 instance
- pr-fix.md: ~12 instances
- pr-review.md: ~40 instances

Structural fixes (pr-fix.md, pr-review.md):
- I1: Use origin/{BASE_BRANCH} instead of origin/main in changelog check
- I2: Fix duplicate sonar-project.properties path to .template variant
- I3: Distinguish math.isclose() (production) vs pytest.approx() (test code)
- I4: Add explicit Phase C loop exit conditions to prevent infinite loops
- I5: Add 15-line diff context extraction instruction before PAL calls
- C2: Add Agent L to Step 7 deduplication source list

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`391d6ca`](https://github.com/ByronWilliamsCPA/.claude/commit/391d6cadb36bd9d37cee9436afed086fd3c3bcf2))
### Unknown
* Merge pull request #21 from ByronWilliamsCPA/feat/pal-validation-workflow-improvements

feat(skills): add PAL multi-model validation and 22-item PR workflow improvements ([`2f8e612`](https://github.com/ByronWilliamsCPA/.claude/commit/2f8e6124ea8e0d708eae32ffcda89d64dc756d7e))
## v0.6.4 (2026-04-13)
### Chore
* chore(merge): resolve conflicts between fix/manual-review-items and origin/main

Merge origin/main into fix/manual-review-items. Conflict resolutions:

- CHANGELOG.md: retain [Unreleased] PR #20 entries above the v0.6.3 release
  block introduced on main.

- scripts/check_type_hints.py: keep our any() comprehension in
  has_future_annotations_import; adopt origin/main&#39;s safe_path reconstruction
  pattern in add_future_import (cwd / resolved_path.relative_to(cwd)) with
  Sonar suppression ID AZ1eBjvzS1usNdOdvc1l.

- tools/validate_front_matter.py: adopt origin/main&#39;s safe_path.write_text
  call in autofix_front_matter with Sonar suppression ID AZ1eBjxNS1usNdOdvc1m.

Note: TruffleHog skipped (SKIP=trufflehog); known incompatibility with git
worktrees where .git is a file pointer, not a directory.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`b06d6cc`](https://github.com/ByronWilliamsCPA/.claude/commit/b06d6cc50c173536f84f6d74fdb2fc784bd7bcba))
### Unknown
* Merge pull request #20 from ByronWilliamsCPA/fix/manual-review-items

fix: resolve manual review items from PRs 18/19 ([`78f9ab3`](https://github.com/ByronWilliamsCPA/.claude/commit/78f9ab3abb597e3a3903a8ebf454ea3489250edd))
## v0.6.3 (2026-04-13)
### Documentation
* docs: replace em-dashes in rules and spec files

Replace all em-dashes with commas, semicolons, or colons throughout
rules and spec files touched in this branch. The no-em-dash rule in
CLAUDE.md applies to all output including documentation, comments,
and rules files.

Files updated: python.md, pre-commit.md, git-workflow.md,
settings-and-permissions.md, frontmatter-standard.md,
known-vulnerabilities-template.md, and both sprint spec files.

The intentional example in rules/writing.md (&#34;The system — which
runs nightly&#34;) is not changed; it is a documented bad example.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`43f1adc`](https://github.com/ByronWilliamsCPA/.claude/commit/43f1adccccf0928bfb29a34a522dd5efbe273311))
* docs: correct BLE rule description and py310 hook wiring status

Broaden the BLE entry in python.md to reflect that BLE001 fires on any
except/except Exception clause including those that re-raise or log
before re-raising, not only ones that swallow errors silently.

Clarify the py310-compat-hook spec: the hook IS active in the global
~/.claude/settings.json but has NOT been added to the committed repo
settings.json. The previous wording &#34;not yet wired&#34; was ambiguous;
rewrite to distinguish the two scopes explicitly.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`e01ae97`](https://github.com/ByronWilliamsCPA/.claude/commit/e01ae97af788ffee80933cbf8802025deb98bd38))
* docs: fix rule descriptions, broken links, and doc accuracy issues

Resolves multiple unresolved Copilot review comments from merged PRs:
- PR#10: Correct BLE and TRY rule descriptions in python.md; fix
  interrogate coverage description (threshold-based, not per-function);
  update darglint exclude list to match pre-commit config (adds
  noxfile.py and .claude/skills/); update pre-commit.md checklist to
  match the same exclude list
- PR#13: Align folder-template.md to use exact filename CLAUDE-FOLDER.md;
  add missing entries for folder-template.md, README.md, and sources.md
  to sources.md mapping table; fix profile.md Communication row to
  reference repo-level CLAUDE.md instead of ~/.claude/CLAUDE.md
- PR#9: Fix sprint-1 plan source frontmatter to point to specific spec
  file; add metadata blockquote to sprint-1 spec
- PR#7: Update py310 spec architecture section to say PostToolUse hook
  is not yet wired in settings.json
- PR#6: Replace direct git push + gh pr create in pr.md step 5 with
  /git pr skill invocation for consistency

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5a87be0`](https://github.com/ByronWilliamsCPA/.claude/commit/5a87be0145a40222dc2863bce47d40bb6c182773))
### Fix
* fix(security): break S2083 taint chain by reconstructing path from CWD

SonarQube&#39;s data-flow analysis traced the taint from the user-controlled
path parameter through resolve() to the write call, flagging both scripts
as BLOCKER even after the containment check was added.

The fix: after validating that resolved_path is within cwd, reconstruct
the write (and read) target as:

    safe_path = cwd / resolved_path.relative_to(cwd)

safe_path is derived from Path.cwd() (a trusted system value), not from
the original user-supplied argument, so the taint chain is broken at the
point of file I/O rather than just validated before it.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`834b883`](https://github.com/ByronWilliamsCPA/.claude/commit/834b883792314fc72c75d8b59c645c6b31af0b4c))
* fix(security): close S2083 path traversal in scripts

Resolve path once at function entry, validate containment inside CWD,
then perform both read and write through the resolved path. Writing
through the original (potentially symlinked) path was the residual
gap: symlinks could redirect the write to a location outside CWD
even after containment validation.

Also extracted a shared `_visit_function_def` helper in
check_type_hints.py to remove `type: ignore[arg-type]` on the
visit_AsyncFunctionDef delegation. Added `from __future__ import
annotations` to satisfy the script&#39;s own union-syntax rule.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`41f20b4`](https://github.com/ByronWilliamsCPA/.claude/commit/41f20b432556cb19a484effa8b0983302a06e926))
* fix(quality): fix noxfile quote style and update stale test comment

Change 6 module-level string constants in noxfile.py from single to
double quotes to match ruff quote-style = &#34;double&#34;. Update the stale
inline comment on the pytest.approx assertion in test_logging.py from
&#34;Rounded to 2 decimals&#34; to &#34;float comparison for rounded value&#34;.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`8e23e60`](https://github.com/ByronWilliamsCPA/.claude/commit/8e23e603f475dab5cf9b8e202725ca31b5c97964))
* fix(writing): remove em-dashes and correct inaccurate VERIFY comments

Replace em-dashes in pre-commit.md darglint line, check_type_hints.py,
and validate_front_matter.py. The VERIFY comment bodies also inaccurately
implied path validation was absent; rewrite to cite the existing guard
locations (lines 189-194 in check_type_hints.py, lines 109-112 in
validate_front_matter.py) and note SonarQube still requires deeper
remediation for S2083.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`bbef5d8`](https://github.com/ByronWilliamsCPA/.claude/commit/bbef5d82695f585dcc3356b8adbb60a6cf92d3cf))
* fix(quality): merge nested if and add security VERIFY markers in scripts

Resolves SonarQube S1066 in check_type_hints.py by merging the nested
isinstance + module equality check into a single condition using and.
Adds pythonsecurity:S2083 VERIFY comments to both check_type_hints.py
and validate_front_matter.py to flag paths constructed from user input
pending security review.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`895e894`](https://github.com/ByronWilliamsCPA/.claude/commit/895e89498f647574dc790b14694daa4efae4b9d3))
* fix(tests): replace constant boolean assertions and float equality checks

Resolves SonarQube S5914 by replacing assert True with meaningful
assertions in test_logging.py (lines 104 and 118) and
test_integration.py (line 48). Resolves S1244 by replacing float ==
comparison with pytest.approx() in test_logging.py line 57.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`de07b82`](https://github.com/ByronWilliamsCPA/.claude/commit/de07b82c202510fb17cb7ec6a31f365bc3efd444))
* fix(quality): extract duplicate literals to constants in noxfile.py

Resolves SonarQube S1192 by extracting six repeated string literals to
named module-level constants: DEV_EXTRAS, PYPROJECT_TOML,
REQUIREMENTS_RUNTIME, REQUIREMENTS_ALL, COV_SRC, and COV_REPORT_TERM.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7096daf`](https://github.com/ByronWilliamsCPA/.claude/commit/7096dafd449dfc6cfaa53780c97638d890a8901d))
### Test
* test: strengthen assertions and add script integration tests

Replace weak existence checks with behavioral assertions in test_logging.py:
- test_json_logging_renderer: verify JSONRenderer present, ConsoleRenderer absent
- test_setup_logging_without_timestamp: verify TimeStamper absent when disabled
- test_full_logging_setup_with_settings: verify structlog BoundLogger wrapper

Add tests/integration/test_scripts.py with 10 new tests covering
check_type_hints.py (5 tests) and validate_front_matter.py (5 tests).
Each script is loaded via importlib.util.spec_from_file_location so
tests exercise real script behavior without polluting sys.path globally.
Includes security-guard tests verifying CWD rejection for both scripts.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`3553e51`](https://github.com/ByronWilliamsCPA/.claude/commit/3553e5175b1a14ac50a6230a0a08c6ea13c5e6c8))
### Unknown
* Merge pull request #19 from ByronWilliamsCPA/chore/cleanup-python-docs-config

fix(quality): resolve Python SonarQube issues and address Copilot doc/config comments ([`693f8a9`](https://github.com/ByronWilliamsCPA/.claude/commit/693f8a9f7e710c689df9287a5243bd287412ce3d))
## v0.6.2 (2026-04-13)
### Documentation
* docs(changelog): add Unreleased section for PR #20 changes

Documents the three change groups landed by /pr-fix on PR #20:
hooks force-push normalization, quality gate hardening, and
writing/em-dash fixes with Copilot suggestions.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5322f93`](https://github.com/ByronWilliamsCPA/.claude/commit/5322f9396661a0b56c02a3f1c6c0e6b0d15ac459))
* docs(diagram): rewrite hook_pipeline.puml to match actual configuration

The previous diagram showed four scripts as wired that are not present in
either hooks.json or .claude/settings.json:
  - keyword-tool-trigger.sh (shown as UserPromptSubmit)
  - tdd-enforcement-hook.sh (shown as PreToolUse)
  - track-mcp-usage.sh (shown as PostToolUse mcp__*)
  - session-start-rules.sh (shown in SessionStart note)

The following wired hooks were missing from the diagram:
  - hooks.json UserPromptSubmit: hookify/userpromptsubmit.py, pr-review-reminder.py
  - hooks.json PreToolUse [Edit|Write]: inline .env/secrets write block
  - hooks.json PreToolUse [Edit|Write|MultiEdit]: security_reminder_hook.py
  - hooks.json PreToolUse [Skill]: planning-bridge-gate.sh
  - hooks.json PreToolUse [any]: hookify/pretooluse.py
  - hooks.json PostToolUse [Edit|Write]: py310-compat-check.sh
  - hooks.json PostToolUse [any]: hookify/posttooluse.py
  - hooks.json Stop: hookify/stop.py
  - settings.json PostToolUse [Edit|Write]: inline py310, ruff, shellcheck,
    validate-frontmatter.sh
  - settings.json FileChanged [.env*]: env-file-audit.sh

Rewrite separates hooks.json (project-level) from settings.json (user-level)
participants. Regenerate SVG from updated PUML source.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c25cac8`](https://github.com/ByronWilliamsCPA/.claude/commit/c25cac8fe27cf0b9e49d033c1b48ae8d813cc96c))
### Fix
* fix(review): address PR #18 review findings

Critical: correct confirm() in cleanup-template-repo.sh to return the
actual user response (return \$?) instead of unconditional 0; previously
any N/n answer to a destructive confirmation prompt was silently ignored.

Important: restore always-0 exit contract for py310-compat-check.sh
PostToolUse hook; add || true guard to log() and revert exit comment so
unexpected I/O errors cannot produce a non-zero exit that blocks Claude.
Remove now-dead GREP_PCRE_AVAILABLE variable and unreachable == false
guard from run_grep after the grep -E migration.

Writing: replace all em-dashes in py310-compat-check.sh and
render_diagrams.sh with colons/semicolons per CLAUDE.md hard rule.

CI: pin both actions/checkout references in release.yml to full commit
SHA for supply chain consistency with all other workflows.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`b8ed6e3`](https://github.com/ByronWilliamsCPA/.claude/commit/b8ed6e3350589927b037195e48ebdec97edb13ff))
* fix(security): scope GitHub Actions permissions to job level

Replace overly broad workflow-level permissions with minimal job-level
declarations (S8234, S8264, S8233):

- scorecard.yml: replace permissions: read-all with contents: read at
  workflow level; job already declares its specific permissions
- reuse.yml: replace permissions: read-all with contents: read at
  workflow level
- pr-validation.yml: move contents: read and pull-requests: write from
  workflow level to each job; core-validation gets both, changelog gets
  read on pull-requests, all others get contents: read only
- release.yml: move all write permissions from workflow level to the
  release job only; test job gets contents: read only ([`b12fe52`](https://github.com/ByronWilliamsCPA/.claude/commit/b12fe5261f5bdd906ce8a875307ed69d42f4ec8d))
* fix(quality): resolve SonarQube violations in tests/

- S7682 (explicit return): add return 0 at end of all helper functions
  in tests/run_tests.sh and tests/helpers/test_helper.bash
- S7688 (use [[): replace single-bracket [ tests with [[ throughout
  both test files
- S1481 (unused variable): remove declaration of skipped_tests in
  run_tests() since it is assigned but never read
- S7679 (positional param to local): in main() arg-parsing loop,
  introduce local arg=&#34;$1&#34; and use $arg in case/assignment instead
  of referencing $1 directly ([`558bab2`](https://github.com/ByronWilliamsCPA/.claude/commit/558bab204c3fe603acd7f610a85277a8e66e7164))
* fix(hooks): correct exit codes, block message routing, and PCRE portability

- rad-strict-hook.sh: merge nested if (S1066) so the git commit check
  and #VERIFY grep are in a single compound condition
- hooks.json: remove &gt;&amp;2 from the sensitive-file block message so the
  reason appears on stdout, which Claude Code surfaces to the user
- py310-compat-check.sh: replace grep -nP (PCRE; fails on macOS/BSD)
  with grep -nE (POSIX extended regex; equivalent for all used patterns);
  update header comment to accurately describe exit behavior under
  set -euo pipefail; note that match/case is already not flagged
  (false-positive issue 3 was already resolved in the AST scan) ([`e0180dd`](https://github.com/ByronWilliamsCPA/.claude/commit/e0180ddfea37f8720ef288ba06cd3e5572911701))
* fix(quality): resolve SonarQube violations in scripts/

Apply mechanical SonarQube fixes across shell scripts:

- S7682 (explicit return): add return 0 at end of each function in
  keyword-tool-trigger.sh, mcp-tool-loader.sh, track-mcp-usage.sh,
  cleanup-template-repo.sh, generate_requirements.sh
- S1066 (merge nested if): collapse inner if into enclosing if using &amp;&amp;
  for all five keyword-detection blocks in keyword-tool-trigger.sh
- S7688 (use [[): replace single-bracket [ conditionals with [[ throughout
  all scripts where flagged
- S131 (default case): add *) ;; default clause to the case &#34;$renderer&#34;
  statement in render_diagrams.sh
- S7677 (redirect to stderr): add &gt;&amp;2 to error echo statements in
  generate_requirements.sh, update-claude-standards.sh, and
  verify-template-consistency.sh ([`8dc86c6`](https://github.com/ByronWilliamsCPA/.claude/commit/8dc86c62abaa8ed03cf4b9d383084d0284c4f501))
* fix(hooks): close force-push guard bypass vectors for URL remotes, interleaved flags, and compound commands

Fixes three bypass vectors not addressed by the refs/heads/ normalization:
- URL-format remote names (git@github.com:...) defeat simple sed stripping;
  now detected and treated as ambiguous (block)
- Interleaved flags (-f -u origin main) were mis-parsed; now all flags are
  stripped before extracting remote and branch tokens
- Compound commands (ls &amp;&amp; git push --force) are now handled by extracting
  only the git push ... segment for analysis

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c2ce659`](https://github.com/ByronWilliamsCPA/.claude/commit/c2ce659fb3de66354a3f25f7a52885c4c0a1f20f))
* fix(quality): clamp _find_insert_index return value to list bounds

When a file&#39;s module docstring is the last statement and the file has no
trailing newline, end_lineno equals len(lines) and the for-loop iterates
over an empty slice, leaving insert_index past the list boundary. Add a
min(insert_index, len(lines)) clamp to guard the caller against an
out-of-bounds index.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`8496f12`](https://github.com/ByronWilliamsCPA/.claude/commit/8496f1229621145844618ea9c0ba17aaa67d7b45))
* fix(review): address PR #20 Copilot and agent findings

- bash-notify.sh: fix comment wording; &#39;double-quote expansion ambiguity&#39;
  was inaccurate; the actual concern is parameter substitution escaping
  issues in \${var//pat/rep}
- check_type_hints.py: remove em-dashes from S2083 suppression comment;
  add SonarQube issue ID AZ1eBjvzS1usNdOdvc1l to the tracking reference
- validate_front_matter.py: remove em-dashes from S2083 suppression
  comment; add SonarQube issue ID AZ1eBjxNS1usNdOdvc1m; apply Copilot
  suggestion to use changed |= pattern instead of bitwise OR on bools;
  wrap _fix_tags/_fix_purpose calls in try/except with stderr logging so
  a helper exception returns False rather than propagating

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`f76f658`](https://github.com/ByronWilliamsCPA/.claude/commit/f76f65824040107c08aa6475a41e9292c240b973))
* fix(quality): harden quality gate against API error envelopes

Bare dict key accesses on the SonarQube API response would raise
KeyError when the API returns an error envelope or omits expected fields.

- Use .get() on projectStatus, status, metricKey, condition status,
  rule, severity, and message throughout format_report,
  _format_sonar_layer, and main
- Default status to NONE when the key is absent
- Treat NONE as a blocking condition in both format_report and main so
  a missing quality gate cannot silently pass as READY TO MERGE
- Add NONE to the Next Steps branch in _format_overall_status

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7298c2b`](https://github.com/ByronWilliamsCPA/.claude/commit/7298c2b0a035c7b99b97aef68cf4ec7af8853d9d))
* fix(hooks): normalize refs/heads/ prefix in force-push guard

Copilot identified a bypass: a fully-qualified refspec such as
refs/heads/main would pass the grep-for-main check because the pattern
only matched bare branch names.

Strip refs/heads/ and refs/ prefixes from both BRANCH_TOKEN and
DEST_TOKEN before the &#39;^(main|master)$&#39; comparison so all three
ref forms are blocked consistently.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`eae2d06`](https://github.com/ByronWilliamsCPA/.claude/commit/eae2d06a4874e8a49aa732ae3babf2acb2f5fedd))
* fix(hooks): correct force-push refspec detection and PowerShell escaping

bash-pre-hook.sh: BRANCH_TOKEN from sed/awk matched bare branch names but not
refspec forms like HEAD:main or :main. Add DEST_TOKEN=&#34;${BRANCH_TOKEN##*:}&#34;
to strip the source ref, then also test DEST_TOKEN against the main/master
pattern. This closes the bypass where force-pushing via a refspec would not
be intercepted.

bash-notify.sh: PS_MSG=&#34;${MSG//\&#39;/\&#39;\&#39;}&#34; inside double quotes matches the two-
character sequence backslash+quote rather than a bare single quote, so messages
containing single quotes were passed through unescaped into the PowerShell
string. Replace with printf+sed to avoid bash parameter-expansion ambiguity.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`00c7a99`](https://github.com/ByronWilliamsCPA/.claude/commit/00c7a99e5b091eb6f1bb210a0cc2818fe5cb6c49))
* fix(quality): reduce cognitive complexity and document S2083 false positives

Extract private helpers from functions flagged by python:S3776 to bring
cognitive complexity below the 15-threshold in all three scripts:

- check_quality_gate.py: extract _format_rad_layer, _format_llm_layer,
  _format_sonar_layer, _format_overall_status from format_report (was 34)
- check_type_hints.py: replace nested loops in has_future_annotations_import
  with any() generator; extract _find_insert_index from add_future_import;
  extract _collect_python_files and _process_files from main (was 16/16/23)
- validate_front_matter.py: extract _fix_tags, _fix_purpose from
  autofix_front_matter; extract _collect_md_files, _output_results from
  main (was 16/21)

Add sonar false-positive comments at write call sites for pythonsecurity:S2083:
paths are validated via is_relative_to(Path.cwd()) before any write occurs.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`f517247`](https://github.com/ByronWilliamsCPA/.claude/commit/f517247ff2c658fdab5ffc955be9f509c38bdbcd))
### Unknown
* Merge pull request #18 from ByronWilliamsCPA/chore/cleanup-shell-yaml

fix(quality): resolve 100+ SonarQube violations in shell scripts and GitHub Actions ([`369517b`](https://github.com/ByronWilliamsCPA/.claude/commit/369517b9cd29be8e0d1d7989a05ee733dba71853))
## v0.6.1 (2026-04-12)
### Fix
* fix(review): address Copilot and agent findings on PR #17

- Scope shelldre:S7688 fix to bash shebang only; skip POSIX sh scripts
- Add errexit caveat to shelldre:S1066 nested-if merge guidance
- Fix python:S5914: assertIsNotNone is not the generic replacement for
  constant boolean assertions; clarify correct fix approach
- Tighten githubactions:S8234: specify reading job steps to identify
  required permissions rather than vague &#34;what the workflow needs&#34;
- Resolve stdout/stderr contradiction between jq guard and hook block
  message rows; add context distinguishing hook vs general shell scripts
- Fix spec frontmatter sub-category: frontmatter status is
  schema-validated; body blockquote follows frontmatter, not the reverse
- Replace undefined &#34;Cowork doc&#34; with &#34;Collaboration document (e.g.,
  COWORK.md)&#34; for clarity

Reconcile uv.lock version to match pyproject.toml 0.6.0 from main.

TruffleHog skipped: git worktree incompatibility (index file is not a
directory); TruffleHog will run normally against the full repo on push.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`8e31667`](https://github.com/ByronWilliamsCPA/.claude/commit/8e31667ddc26c8acd5099df70b819e408df7c77a))
* fix(pr-fix): expand sonar rule table, shell bug categories, and doc accuracy patterns

Adds 12 new SonarQube rules to the Priority 2 table (shelldre:S7688,
S1066, S131, S7677, S1481, S7679; python:S5914, S1244, S1066, S1192;
githubactions:S8234, S8233), four new shell bug categories to Priority 3
(jq presence guard, hook message direction, grep -nP portability,
PowerShell escaping), a Documentation accuracy sub-category table with
seven doc drift patterns, and two new Always-skip entries
(pythonsecurity:S2083, force-push guard bypass).

Note: TruffleHog skipped (SKIP=trufflehog) due to known incompatibility
with git worktrees (.git is a file pointer, not a directory).

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`609311a`](https://github.com/ByronWilliamsCPA/.claude/commit/609311a20a0379051862ac8d5347d70dd47bb0cd))
### Unknown
* Merge pull request #17 from ByronWilliamsCPA/fix/pr-fix-gap-remediation

fix(pr-fix): expand SonarQube rule coverage and shell/doc fix patterns ([`bdbd745`](https://github.com/ByronWilliamsCPA/.claude/commit/bdbd745e092ab775a8a4eb6ebc91661bbff54dc6))
## v0.6.0 (2026-04-12)
### Chore
* chore(deps): reconcile uv.lock version with pyproject.toml 0.5.0

uv sync updated the lock file version from 0.4.0 to 0.5.0 to match
the current pyproject.toml version after the v0.5.0 release.

https://claude.ai/code/session_016cTxGxECo4rzsVNFPR7Wxa ([`b2250a4`](https://github.com/ByronWilliamsCPA/.claude/commit/b2250a4b1784bd44f6a0c8db6181463afc2b1de5))
### Feature
* feat(skills): rewrite pr-fix as standalone multi-source PR remediation workflow

Rewrite /pr-fix from a downstream-only sub-step of /pr-review into a
standalone skill that independently gathers all open issues on a PR:

- CI check failures (test, lint, format, type-check, security, changelog,
  compatibility, docs build, license, dead code)
- Review comments from all sources (Copilot, CodeRabbit, human reviewers)
  with author classification and actionability filtering
- SonarQube findings (missing returns, redundant exceptions, cognitive
  complexity, ReDoS patterns, security hotspots)
- Codecov coverage gaps (if configured)
- pr-review agent findings (when called from the review workflow)

The workflow fixes issues in priority order inside an isolated worktree,
verifies via ci-fix gate sequence, commits in logical batches, and offers
to push, reply to review comments, resolve threads, and post a summary.

Also updates:
- SKILL.md: add pr-fix trigger keywords and routing table
- pr-review.md: Step 9/10 now references the full pr-fix workflow
- git-workflow.md: add /pr-fix to Layer 2 gate documentation

https://claude.ai/code/session_016cTxGxECo4rzsVNFPR7Wxa ([`7845e2e`](https://github.com/ByronWilliamsCPA/.claude/commit/7845e2e04693a6264aee9e1cf67bd0691c904167))
### Fix
* fix(review): address pr-review agent findings on PR #16

Formatting fixes (markdownlint):
- Add language specifiers to bare code fences (MD040)
- Space all table separator rows: |---|---| -&gt; | --- | --- | (MD060)
- Add blank lines around all lists and list-adjacent blocks (MD032)
- Change all heading separators from &#39; -- &#39; to &#39;: &#39;

Content corrections:
- Fix SonarQube rule key: shelldre:S7682 -&gt; shell:S7682
- Move cognitive complexity (python:S3776) from deterministic-fixes
  table to manual-fix table (requires design judgment, not mechanical)
- Clarify GitHub MCP method names in Steps 1b and 7; note that
  resolve_review_thread and subscribe_pr_activity are unconfirmed
  method names and replace with gh CLI polling workaround
- Fix Step 3 error message: &#39;ensure git fetch origin ran&#39; -&gt;
  &#39;check that the branch exists on origin&#39;
- Escape MD056-triggering pipe literal in table cell

Note: TruffleHog skipped (SKIP=trufflehog) due to known incompatibility
with git worktrees (.git is a file pointer, not a directory).

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`2746c50`](https://github.com/ByronWilliamsCPA/.claude/commit/2746c50f0d4af0033e8ba094d6bc4497e62d736a))
### Unknown
* Merge pull request #16 from ByronWilliamsCPA/claude/add-pr-fix-workflow-lwfkx

feat(skills): rewrite pr-fix as standalone multi-source PR remediation ([`022bc9f`](https://github.com/ByronWilliamsCPA/.claude/commit/022bc9f7b74aa1a03e2b2858e5a7ddfe8833936e))
## v0.5.0 (2026-04-12)
### Chore
* chore(docs): exclude PlantUML font cache from git

The plantuml CLI writes a Java font cache to a directory named `?`
under the diagram output directory during SVG rendering. This
directory is an artifact and not part of the project; exclude it
with a wildcard gitignore pattern that matches any single-character
subdirectory.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`566950e`](https://github.com/ByronWilliamsCPA/.claude/commit/566950e0bf7eb6c6e9c4097c1890cf7761a97f3e))
### Documentation
* docs(diagram): regenerate hook_pipeline.svg from updated PUML source

The PUML source was rewritten in a prior commit to show the actual
hook scripts from both settings files. Regenerate the SVG to match
using the plantuml.jar from the image_detection tools directory.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`bf12104`](https://github.com/ByronWilliamsCPA/.claude/commit/bf12104564eb2d260b04199445c67c74330a1352))
* docs(git): update review workflow references to /pr-review

Replace /code-review references with /pr-review throughout the PR
workflow documentation. /pr-review supersedes /code-review: it triggers
Copilot automatically, adds SonarQube PR findings, runs 8 agents instead
of 5, and reports all findings in tiers rather than filtering at 80
confidence. Update git-workflow.md and the git/pr skill to reflect
the new primary review command.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`23a7025`](https://github.com/ByronWilliamsCPA/.claude/commit/23a70257e454ad28b2ebb58ea53737b73935209d))
* docs(claude-md): elevate em-dash rule and add worktree path constraint

Move the em-dash ban from the writing rules reference to a top-level
section in CLAUDE.md so it is visible at all times, not only when
reading the full writing rules. Add the worktree path constraint
(project-local .worktrees/&lt;branch-slug&gt; only) alongside the git
workflow entry. Add .worktrees/ to .gitignore with a clarifying comment.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7fb8273`](https://github.com/ByronWilliamsCPA/.claude/commit/7fb82733ef017ae3c17f2b00ac5ca33ad52a8ec0))
* docs(diagram): update hook_pipeline.puml to match actual hook config

Previous diagram referenced hookify dispatch, planning-bridge-gate,
secrets scan, and other scripts that are not in settings.json. Updated
to show the scripts that are actually wired: tdd-enforcement-hook.sh,
bash-pre-hook.sh, stop-pre-commit-hook.sh, bash-notify.sh,
track-mcp-usage.sh, env-file-audit.sh, validate-frontmatter.sh, and
the keyword-tool-trigger.sh / SessionStart scripts.

Note: SVG needs regeneration via plantuml to match updated source.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`3f9e7ec`](https://github.com/ByronWilliamsCPA/.claude/commit/3f9e7ec00584b728784d077f89e95e64248ed875))
* docs: correct Python version requirement from 3.12+ to 3.10+

pyproject.toml declares requires-python = &#34;&gt;=3.10,&lt;3.15&#34;. Both
getting-started docs incorrectly stated Python 3.12+ as the
minimum requirement.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`4221f95`](https://github.com/ByronWilliamsCPA/.claude/commit/4221f9503bbd01f3f2bfb0846c9ee71fea147d02))
* docs: implement best-practice adoptions (items 1-13) and architecture docs

Add 13 items from the best-practice review consensus-adjusted short list:

- rules/settings-and-permissions.md: five-scope hierarchy, evaluation order,
  and sandbox layer documentation
- settings.json: 22-entry permissions.ask 7-day trial, outputStyle,
  plansDirectory, CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, SessionStart hook
- .claude/settings.json: FileChanged .env* audit hook, Stop pre-commit trial
- rules/git-workflow.md: /branch and --fork-session session forking docs
- rules/supervisor.md: Explore/Plan built-in subagent rows, two-pattern skill
  architecture section, pre-planning codebase discovery checklist
- rules/loop-recipes.md: /loop recipes with cost circuit-breaker safeguards
- standards/on-demand-skill-hooks.md: on-demand hook convention with
  RAD_STRICT_MODE reference implementation
- scripts/env-file-audit.sh, stop-pre-commit-hook.sh, session-start-rules.sh:
  companion hook scripts for the three new hooks
- skills/rad/workflows/rad-strict-hook.sh: reference impl for on-demand hooks

Also fixes pre-existing frontmatter issues in docs/development/best-practice-review/
and includes architecture docs, ADRs, contributing guides, getting-started
guides, and reference docs previously staged from prior sessions.

Source: docs/development/best-practice-review/synthesis-report.md

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`720b024`](https://github.com/ByronWilliamsCPA/.claude/commit/720b024907287ea50edb87e49a0cab3fa3abed20))
### Feature
* feat(skills): add pr-review and pr-fix orchestration skills

Add the /pr-review skill: a full PR review pipeline that triggers
GitHub Copilot immediately, fetches SonarQube PR findings, runs up
to 8 parallel agents (CLAUDE.md compliance, bug scan, git-history
context, prior PR comments, comment accuracy, silent failures, test
coverage, type design), confidence-scores every finding, and outputs
a tiered report.

Add the pr-fix sub-workflow: executes mechanical fixes from the review
output in an isolated worktree. Handles shell script bugs (stdin
pattern, uv run python), documentation accuracy, em-dash replacement,
SonarQube shell findings, configuration portability, pre-commit config
gaps, Python antipatterns, docstring accuracy, and bare exception
handling. Categorizes non-mechanical findings (test gaps, type design,
security, complex logic) as requiring manual fix.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`1068e64`](https://github.com/ByronWilliamsCPA/.claude/commit/1068e64f618a26d05f5e68d363277ec4f043b9d7))
### Fix
* fix(settings): use portable path for plansDirectory

Hard-coded /home/byron/.claude/plans breaks for any other user who
clones this repo. Using ~ which most path-aware tools expand to the
current user&#39;s home directory.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`0391164`](https://github.com/ByronWilliamsCPA/.claude/commit/039116403b69453b6d397ab12e7b4aaa7b6f60db))
* fix(docs): correct relative link to ADR-004 in supervisor.md

Link was ../docs/architecture/... which resolves to .claude/docs/
(does not exist). Correct path from .claude/rules/ to repo-root
docs/ is ../../docs/architecture/...

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`3a67295`](https://github.com/ByronWilliamsCPA/.claude/commit/3a672951ceb8f22eac7ec3c1a9e2edb3bec6c222))
* fix(hooks): read tool input from stdin in rad-strict-hook.sh

CLAUDE_TOOL_INPUT env var does not exist. Claude Code hooks receive
tool input via stdin as JSON. Read with cat and parse with jq to get
the command field, matching the pattern used by other hooks in this repo.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a9c9f68`](https://github.com/ByronWilliamsCPA/.claude/commit/a9c9f68c61ee4f088b4d5417c06afc927c3bf45d))
* fix(tools): use uv run python in check_docs.sh for reproducibility

Bare python call would use whatever python is on PATH, which may not
match the project&#39;s managed virtualenv. uv run python ensures the
project toolchain is used.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`e78cf29`](https://github.com/ByronWilliamsCPA/.claude/commit/e78cf29a97f91ea4abf0772dba466ce759068882))
* fix(review): address Copilot code review findings on PR #15

Critical fixes:
- settings-and-permissions.md: correct scope hierarchy order (managed
  policy is highest/5, ~/.claude/settings.json is lowest/1; previously inverted)
- stop-pre-commit-hook.sh: remove set -e to prevent abort before timing
  code runs; capture pre-commit exit with || RC=$? pattern
- rad-strict-hook.sh: use exit 2 (block tool call) not exit 1 (hook error);
  add set -euo pipefail and activation log line; add registration comment
- CLAUDE.md: add references for settings-and-permissions.md and
  loop-recipes.md so rule files inject into sessions (orphaned rules fix)

Important fixes:
- .claude/settings.json: tighten FileChanged matcher from \\.env to
  (^|/)\\.env[^/]*$ to avoid false positives on .environment.py etc.
- settings.json: fix Bash(gcloud:*) format (was Bash(gcloud *:*) with
  literal asterisk); remove redundant Bash(rm -rf:*) covered by Bash(rm:*)
- on-demand-skill-hooks.md: add Registration requirement section with
  settings.json JSON example and explanation of why registration is needed

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`74487af`](https://github.com/ByronWilliamsCPA/.claude/commit/74487af01d28e73fcf07d74486339b986e60eb8a))
### Unknown
* Merge pull request #15 from ByronWilliamsCPA/docs/best-practice-adoptions-phase1 ([`dfb8615`](https://github.com/ByronWilliamsCPA/.claude/commit/dfb86155378a5c20e50de47d614483922ec2aea1))
## v0.4.0 (2026-04-11)
### Chore
* chore(deps): reconcile uv.lock with pyproject.toml version

The uv.lock file carried claude-config version 1.0.0 from the initial
cookiecutter commit, but pyproject.toml has been bumped through 0.1.0,
0.2.0, and 0.3.0 without the lock file being regenerated. Running
uv lock now corrects the recorded version to 0.3.0.

Also tightens the transitive typing-extensions marker on exceptiongroup
from python_full_version &lt; &#39;3.13&#39; to &lt; &#39;3.11&#39;, which more accurately
reflects that exceptiongroup is a backport only relevant on Python 3.10
within our &gt;=3.10,&lt;3.15 supported range.

No dependency versions change; this is a lock-file accuracy fix. ([`63bab66`](https://github.com/ByronWilliamsCPA/.claude/commit/63bab6650382874bad08bf8b9eb5d35ff52f10eb))
* chore: add pip-audit pre-push hook for dependency vulnerability scanning ([`3c17eeb`](https://github.com/ByronWilliamsCPA/.claude/commit/3c17eeb023428f218fd1d454e318f6677f40d383))
### Documentation
* docs(readme): note wrapper-skill follow-up for /code-review PR URL triggers

Adds a subsection to the Claude Code Standards section of README.md capturing
the architectural note that surfaced during PR #14: the /code-review plugin
is a command, not a skill, so prose phrasings like &#34;review this PR&#34; do not
reliably invoke the structured 5-agent review pipeline. Only the explicit
/code-review slash command does.

Documents the proposed fix (thin wrapper skill in .claude/skills/code-review-pr/
that routes natural-language PR review requests to the underlying command)
so the idea is not lost between sessions. The fix itself is not implemented
here; this is a documented backlog item.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`bc4efa3`](https://github.com/ByronWilliamsCPA/.claude/commit/bc4efa3b9c9ba9bebc14ef58a947a37a23f04848))
* docs(readme): replace aspirational subtree docs with actual symlink topology

The old &#34;Claude Code Standards&#34; section described a git subtree pattern
(.claude/standard/ with `git subtree pull`) that no project actually uses.
monte_carlo, cookiecutter-python-template, and other consumer projects keep
their own project-local CLAUDE.md and inherit the global config via the
user-scope ~/.claude/ symlinks created by setup.sh.

Replaced with accurate documentation of the real two-layer install pattern:

1. ASCII topology diagram showing the symlink map from ~/.claude/ (runtime
   that Claude Code reads) into ~/dev/.claude/ (repo source of truth in git)
2. Install command (clone + ./setup.sh)
3. Verify command (./setup.sh --doctor) introduced in the companion commit
4. Dry-run command (./setup.sh --dry-run) introduced in the same commit
5. Rationale for symlinks over subtree/submodule (clean runtime, instant
   propagation, no copy step, claudeMdExcludes prevents double-load)
6. Note on per-project CLAUDE.md and .claude/settings.local.json overrides

Completes the documentation side of the consensus-recommended refinements.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`ec8394a`](https://github.com/ByronWilliamsCPA/.claude/commit/ec8394a06e3ee95f3a9527f5502d07724e9811b0))
* docs(cowork): apply PR #13 review feedback

- sources.md: replace em-dashes in external reference link titles
  with parenthetical source attribution (the no-em-dash rule the
  PR itself enforces must apply here too)
- cowork.md: scope the Title Case heading rule explicitly to Word
  document output so it does not imply markdown source files
- profile.md: restore dropped banned terms (groundbreaking,
  to summarize, at the end of the day, exemplary, enhancing
  performance) and add pointer to extended structural tells list
- cowork.md: replace .bak.YYYY-MM-DD-HHMM with ISO 8601 UTC basic
  format (.bak.YYYYMMDDTHHMMSSZ) for lexical sortability and
  collision safety; replace the unenforceable &#34;three consecutive
  edits&#34; rule with an observable trigger (before destructive edits)
- README.md: update word count targets to reflect new content
  (profile.md ~300, cowork.md ~350, folder-template.md ~220)

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`19002d1`](https://github.com/ByronWilliamsCPA/.claude/commit/19002d12821aed77649ee766d9000380645d9bcb))
* docs(cowork): add paste-in instructions and remove bushido plugin

Add .claude/cowork/ with paste-in content for Claude Cowork and Desktop:

- profile.md (~275 words): universal writing rules and communication style
- cowork.md (~340 words): file safety, Word/Excel conventions, citations
- folder-template.md: per-folder project context with placeholders
- sources.md: traceability from paste-in sections to source rule files
- README.md: paste workflow and future migration notes

All paste-in files stay under the 500-word per-field ceiling per Anthropic
custom instructions best practice. Covers the Word and Excel use case;
browser research remains in Claude for Chrome and coding in Claude Code.

Remove bushido@han plugin and han marketplace from .claude/settings.json;
the SessionStart injection is no longer used.

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`106301f`](https://github.com/ByronWilliamsCPA/.claude/commit/106301f64216eb3aff2a0594e57ca18bd9c3d1aa))
* docs: replace em-dashes in Layer 1 and Layer 2 gate headings ([`d9c3131`](https://github.com/ByronWilliamsCPA/.claude/commit/d9c3131000577e48745b252f5da89861d9a9dbbc))
* docs: add AI review configuration sync guidance to cookiecutter handoff doc

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`0ad029b`](https://github.com/ByronWilliamsCPA/.claude/commit/0ad029b9fa1120a14705aa72ea332e69ee2579e5))
* docs: add CodeRabbit and Copilot review checklist items to pre-commit rules ([`d0f6814`](https://github.com/ByronWilliamsCPA/.claude/commit/d0f68148bc70271951d852a7b9be809cd95f2516))
* docs: tighten scope tracing wording and add tagline entry ([`c1b4ac7`](https://github.com/ByronWilliamsCPA/.claude/commit/c1b4ac7b8392e9c632ef5de492c926374442f18e))
* docs: add scope tracing principle to CLAUDE.md and supervisor rules ([`beb421a`](https://github.com/ByronWilliamsCPA/.claude/commit/beb421ae2acd8cf7912bb2a6d9583ca3693befb4))
* docs: replace puffery word in gate system summary line ([`09eec0a`](https://github.com/ByronWilliamsCPA/.claude/commit/09eec0ac7f1b19d00ffad204452a8e146f5b02f3))
* docs: add remote verification, branch override, and AI review gate documentation

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`11edf1f`](https://github.com/ByronWilliamsCPA/.claude/commit/11edf1f7b182bb3620901ab7446158a0c2b21ebc))
* docs: add Sprint 3 git workflow governance implementation plan

Five tasks: update git-workflow.md (remote verification, branch
override, Layer 2 AI review expansion), add scope tracing to CLAUDE.md
and supervisor.md, add AI review checklist items to pre-commit.md,
update cookiecutter handoff doc with AI review config sync guidance.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a12daee`](https://github.com/ByronWilliamsCPA/.claude/commit/a12daee57b12c218f0e849a1a5253b2c9f5a3b30))
* docs: expand sprint-3 spec to five items and fix em-dashes

Adds Item 5 (cookiecutter AI review config sync), updates overview
count, fixes three em-dashes in Items 4a and 4b, and updates Files
Modified, Verification, and Out of Scope sections accordingly.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`82a95f5`](https://github.com/ByronWilliamsCPA/.claude/commit/82a95f59d7285a21f908adb2aaa20e2c76b23938))
* docs: address code review findings from PR #10

- Fix BLE/TRY enforcement claim: TRY002 and BLE001 catch specific
  anti-patterns but do not validate the full AppError hierarchy; code
  review is the enforcement mechanism for hierarchy structure
- Fix to_dict() return type from dict[str, str] to dict[str, object]
  to avoid breakage when subclasses add non-string fields
- Add note that subclass ...  bodies are minimal when no extra
  attributes are needed; show examples in inline comments
- Explain interrogate/darglint scope asymmetry: scripts/ excluded from
  darglint due to *args/**kwargs false-positive patterns
- Add darglint long-strictness definition (multi-line docstrings only)
- Bridge global docstring standard to scripts/-scoped gate via Ruff D rules
- Move Docstring Coverage and Docstring Arguments checklist items to sit
  adjacent to linter checks (before Commits are signed)
- Scope Golden File Protection to output snapshots (tests/golden/,
  *.snap); clarify tests/fixtures/ may contain input data, not snapshots
- Bump CLAUDE.md to v1.2.0, update Last Updated to 2026-04-10

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c4cb49f`](https://github.com/ByronWilliamsCPA/.claude/commit/c4cb49f5fdb6feb7fd69a1c0aee760c940c892d9))
* docs: add Sprint 3 git workflow governance design spec

Covers remote verification, branch override pattern, scope tracing
principle, and AI review integration (CodeRabbit + GitHub Copilot).

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`014494d`](https://github.com/ByronWilliamsCPA/.claude/commit/014494d8f13adf292205221c872e1ee0c3b1dd79))
* docs: clarify darglint scope and remediation in pre-commit checklist ([`01a5d71`](https://github.com/ByronWilliamsCPA/.claude/commit/01a5d71c728a441d91a6c3a422ce38d9b292ab54))
* docs: add docstring coverage and argument validation checklist items ([`f50a329`](https://github.com/ByronWilliamsCPA/.claude/commit/f50a329e4c526270d8808a6e03f01a4aaf57f26b))
* docs: fix golden file protection wording and cargo snapshot command ([`8e57c9e`](https://github.com/ByronWilliamsCPA/.claude/commit/8e57c9ed685af4df5e84ae5a03d7a3740bad7f37))
* docs: add golden file protection guidance to CLAUDE.md Testing section ([`96f853a`](https://github.com/ByronWilliamsCPA/.claude/commit/96f853a2e2077bc0cbab4633a5ee96846aae85ba))
* docs: fix em-dashes and code block style in python rules exception section ([`91019fa`](https://github.com/ByronWilliamsCPA/.claude/commit/91019fa9c7d5bba53219a67521ba2c7a80ed1c67))
* docs: add exception hierarchy guidance and expand documentation section in python rules ([`4918834`](https://github.com/ByronWilliamsCPA/.claude/commit/4918834f07c4c7a24d2791d8e05a7a78af95fbd4))
* docs: address PR review findings — FIPS, CVE policy, pip-audit hook

- Align CVE reassessment window to 60 days (was 90) to match the OpenSSF
  release gate; add cross-reference note to CLAUDE.md blockquote
- Update known-vulnerabilities-template.md to reflect 60-day window
- Add virtualenv assumption comment to pip-audit pre-push hook
- Rename FIPS table row &#39;Key exchange&#39; to &#39;Asymmetric / Key Exchange&#39;
- Promote Curve25519/X25519 FIPS 140-3 qualifier from table parenthetical
  to standalone explanatory note below the table
- Group GitHub Actions SHA pinning under a &#39;Security Practices&#39; heading
  in git-workflow.md for easier navigation as the file grows

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5de48ab`](https://github.com/ByronWilliamsCPA/.claude/commit/5de48abe57f4f0cd5ba03df0ebd04312109289d4))
* docs: add Sprint 2 code quality patterns design spec

Covers exception hierarchy guidance, golden test protection, and
docstring coverage gate documentation for rules/python.md, CLAUDE.md,
and rules/pre-commit.md.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7c2aeeb`](https://github.com/ByronWilliamsCPA/.claude/commit/7c2aeebafab5cd9544f65395bb190223fa1a1a64))
* docs: fix frontmatter in sprint-1 plan and spec files

Add planning frontmatter to plan file and remove redundant H1.
Replace invalid pre-commit tag with tooling in spec file.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a599c3e`](https://github.com/ByronWilliamsCPA/.claude/commit/a599c3e5341cd4543050f34c650ef93972039bf1))
* docs: add known vulnerability template and CVE policy reference to CLAUDE.md ([`33e6f32`](https://github.com/ByronWilliamsCPA/.claude/commit/33e6f327adb89e1d6a78005048ce86f0136d16c8))
* docs: add GitHub Actions SHA pinning guidance to git workflow rules ([`121edb6`](https://github.com/ByronWilliamsCPA/.claude/commit/121edb6ef9943172198123123c8d14c2e4951482))
* docs: fix FIPS key exchange qualifier and add AES mode guidance ([`f69b6cb`](https://github.com/ByronWilliamsCPA/.claude/commit/f69b6cb0e2bb9f0b3c9996a1b92bc18bb8c53cab))
* docs: add FIPS 140-2/3 compliance requirements to python rules ([`38b1b0d`](https://github.com/ByronWilliamsCPA/.claude/commit/38b1b0d102d2e5c3aecbcc796fc214ad3df42a57))
* docs: fix em-dash in pre-commit security scanning checklist item ([`f50578c`](https://github.com/ByronWilliamsCPA/.claude/commit/f50578c7dd41b6ccab0ed3aa40721870e9161d20))
### Feature
* feat(hooks): add pr-review-reminder UserPromptSubmit hook

Addresses the auto-activation gap for /code-review. Because /code-review
is a Claude Code plugin command (not a skill), prose phrasings like
&#34;review this PR&#34; do not auto-invoke the structured 5-agent pipeline.
This hook closes that gap by detecting PR review intent in user prompts
and injecting a system message telling Claude to ask the user whether
they want the structured command run.

Implementation:
- scripts/pr-review-reminder.py: standalone Python hook, reads JSON event
  from stdin, extracts user_prompt field, matches against GitHub PR URL
  regex and natural-language review-intent phrases, short-circuits if
  /code-review is already present or if PR_REVIEW_REMINDER_DISABLED=1
  is set in the environment. Always exits 0, never blocks the prompt.
- hooks.json: new UserPromptSubmit entry running the script with a 5s
  timeout, placed after the existing hookify entry so both fire. The
  script is referenced from $HOME/.claude/scripts/ which resolves via
  the setup.sh symlink to $HOME/dev/.claude/scripts/.
- README.md: updated the wrapper-skill follow-up section to reflect
  the implemented hook, listing the trigger patterns and the opt-out
  environment variable.

Tested 5 scenarios locally:
- Empty event -&gt; no reminder (correct)
- No PR mention (&#34;what time is it&#34;) -&gt; no reminder (correct)
- GitHub PR URL -&gt; reminder fires (correct)
- &#34;review this PR and tell me what you think&#34; -&gt; reminder fires (correct)
- Explicit /code-review invocation -&gt; no reminder (correct short-circuit)

Ran setup.sh to merge into ~/.claude/settings.json. Doctor passes.

Global hook vs hookify rule choice: hookify rules load from
.claude/hookify.*.local.md relative to cwd, so they are project-scoped
and would only fire when working inside specific projects. A standalone
hook entry in hooks.json fires on every UserPromptSubmit regardless of
cwd, which matches the user&#39;s stated goal of reminding them globally.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a2bceaf`](https://github.com/ByronWilliamsCPA/.claude/commit/a2bceaf31daa3c8d71980f9093bb64d26ca97326))
* feat(setup): harden setup.sh with dry-run, doctor, backups, claudeMdExcludes

Adds operational safety and observability to the bootstrap script per the
consensus refinement recommendations. Every change is backwards compatible:
existing users running the new script get the same symlinks and hook merge
behavior they had before, plus the new doctor command and stronger safety.

Added features:
- `set -euo pipefail` at the top so errors halt execution instead of
  silently continuing
- Flag parsing: `--dry-run` shows what would change without applying,
  `--doctor` prints the resolved symlink topology and flags broken links,
  `--help` shows usage from the script header comment
- Preflight check: verifies jq, ln, and git are available before any
  operation, exits with a clear error if not
- `ln -sfn` used consistently so symlink updates are atomic
- Timestamped backup of ~/.claude/settings.json (format
  settings.json.bak.YYYYMMDD-HHMMSS) before any jq merge, so settings can
  be rolled back if a merge corrupts them
- New symlinks for CLAUDE.md, rules, and standards directories (these were
  symlinked manually in the existing install but setup.sh did not create
  them, which broke reproducibility for new clones)
- New merge step: `claudeMdExcludes` is populated in settings.json with
  paths derived from $REPO_DIR, so the repo&#39;s own CLAUDE.md and
  .claude/**/* are excluded from directory-walk discovery when working
  inside the repo itself. This solves the double-load edge case
  identified by the 5-model consensus. Uses --arg for path injection so
  the excludes work correctly regardless of where the repo is cloned.
- Doctor mode: verifies each expected symlink points where it should,
  flags drift (wrong target), real (regular file instead of symlink), or
  miss (not present). Also checks whether hooks and claudeMdExcludes are
  present in settings.json.

Verified:
- `bash -n setup.sh` passes syntax check
- `shellcheck setup.sh` exits 0 with no warnings
- `./setup.sh --doctor` reports all symlinks OK and settings present
- `./setup.sh --dry-run` shows correct action plan without modifying files

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`35ecc2c`](https://github.com/ByronWilliamsCPA/.claude/commit/35ecc2ce68c3571217db8f6d5d3d0f312dba76dd))
### Fix
* fix(quality): resolve remaining SonarQube code smells on branch

setup.sh (shelldre:S7682): added explicit `return 0` to log helpers
(log_info/ok/skip/warn/error), run_or_dry, preflight, doctor,
ensure_submodules, and backup_settings so each function ends with an
explicit return statement under `set -euo pipefail`.

scripts/pr-review-reminder.py:
- S5713: removed redundant json.JSONDecodeError from except tuple
  (JSONDecodeError is a ValueError subclass, already caught)
- S5713: removed redundant ValueError from os.read except tuple
  (only OSError is raised by sys.stdin.read)
- S3516: refactored main() to return None instead of always returning 0;
  caller changed from sys.exit(main()) to main()

Verified: bash -n setup.sh, python compile, ./setup.sh --doctor,
./setup.sh --dry-run, and hook smoke tests with PR and non-PR prompts
all pass.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`75e1a5a`](https://github.com/ByronWilliamsCPA/.claude/commit/75e1a5a2347c56252c8e2c227efec51b55986e0c))
* fix(review): address Copilot comments and SonarQube hotspots on PR #14

Fixes all 4 Copilot inline review comments and all 3 SonarQube security
hotspots surfaced on PR #14. My own /code-review pipeline only ran its
internal 5-agent review and did not read other reviewers&#39; findings, so
these were missed until explicitly fetched.

## Copilot comment fixes

1. setup.sh preflight: softened jq requirement
   (Copilot comment on setup.sh:67)
   Previously, preflight exited 3 if jq was missing, blocking even the
   symlink creation on jq-less systems. This was a regression vs the
   pre-refactor behavior. Now preflight hard-requires only `ln` and `git`
   (needed for symlinks), and treats `jq` as soft with a warning.
   `merge_hooks` and `merge_claude_md_excludes` each check for `jq`
   independently and skip with a warning if absent.

2. setup.sh doctor: dangling symlink detection
   (Copilot comment on setup.sh:104)
   Previously, doctor marked any symlink whose readlink output matched
   the expected path as [ok], even if the target path did not exist
   (dangling link, common when submodules are not initialized). Added a
   [[ -e &#34;$link&#34; ]] check so dangling links are reported as [dangle]
   and counted as broken.

3. setup.sh merge_claude_md_excludes: preserve user-defined excludes
   (Copilot comment on setup.sh:219)
   Previously, `.claudeMdExcludes = [...]` replaced the entire array,
   clobbering any user-added patterns. Now uses
   `.claudeMdExcludes = ((existing // []) + [repo patterns]) | unique`
   so repo-specific entries are appended and the result is deduplicated.
   User-defined excludes are preserved across setup.sh runs.

4. rules/python.md argument count wording
   (Copilot comment on python.md:212)
   Previously, the earlier &#34;Parameter Grouping&#34; rule said &#34;&gt;4 params -&gt;
   dataclass&#34; (5+) while the new Function Quality Gates said &#34;maximum 5
   positional (PLR0913); use dataclass grouping above that&#34; (6+). These
   conflicted. Aligned to &#34;maximum 4 positional before grouping; use
   dataclass for 5 or more&#34; per Copilot&#39;s suggestion, matching the
   established Parameter Grouping rule.

## SonarQube hotspot fixes

5-7. scripts/pr-review-reminder.py ReDoS risk (python:S5852)
   Three hotspots on lines 43-45 flagged the regex patterns for
   `\breview\s+(this\s+|the\s+)?(pull\s+request|pr\b)` and similar
   shapes as vulnerable to polynomial backtracking due to nested `\s+`
   with optional groups.

   Replaced the PR_PHRASE_PATTERNS regex list with a PR_PHRASES tuple of
   plain lowercase substrings. The prompt is normalized via `.lower()`
   and collapsed-whitespace substitution before matching. Substring
   matching is strictly linear, eliminating the ReDoS surface entirely.

   Also expanded phrase coverage: the previous 5 regex patterns are now
   19 explicit substrings (review/look-at/check + pr/pull request + this
   /the/bare). Added a new whitespace normalization so inputs like
   &#34;review   the    PR&#34; still match the intended phrase.

   Kept two regex patterns: PR_URL_RE (bounded character classes, no
   ReDoS risk) and EXPLICIT_COMMAND_RE (anchored literal, no risk).

## Verification

- bash -n setup.sh: clean
- shellcheck setup.sh: clean
- ./setup.sh --doctor: all 8 symlinks OK, hooks present, claudeMdExcludes present
- ./setup.sh --dry-run: shows correct jq merge+dedupe plan
- ./setup.sh (live run): idempotent, claudeMdExcludes deduped correctly
- pr-review-reminder.py: 6 test cases pass including new whitespace case

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`f928aad`](https://github.com/ByronWilliamsCPA/.claude/commit/f928aad8114300a3808179e36abf55de64143715))
* fix(writing): remove em-dashes introduced in this PR

Self-review caught 14 em-dashes introduced across the three files modified
by this PR. The no-em-dashes rule is a Tier 3 user preference codified in
.claude/rules/writing.md and explicitly referenced from CLAUDE.md.

- CLAUDE.md: 12 em-dashes replaced with commas (in Development philosophy
  numbered list, Compact Instructions bullets, and Project context note)
- README.md: 1 em-dash replaced with semicolon in the wrapper-skill
  follow-up note
- setup.sh: 1 em-dash replaced with a period in the ensure_symlink warning
  message

Pre-existing em-dash in setup.sh line 2 (the script&#39;s header comment) is
left alone because it was not introduced by this PR and modifying it would
expand the diff beyond scope.

Identified by self-run of /code-review via 5-agent Sonnet parallel review.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`91cbd64`](https://github.com/ByronWilliamsCPA/.claude/commit/91cbd649293773b6da81b4cd091b3e215f3d706a))
* fix(ruff): stop auto-correcting files inside .submodules/

The PostToolUse ruff hook was modifying files inside git submodules every time
Claude ran, producing spurious &#34;modified content&#34; reports and accidentally
drifting vendored code.

Root cause: ruff&#39;s exclude list in pyproject.toml did not include .submodules/,
and force-exclude was not set. When ruff is invoked with an explicit file path
(e.g., from the Claude Code PostToolUse hook running ruff check --fix on a
file inside a submodule), exclude rules are bypassed by default unless
force-exclude = true.

Fix:
- Add .submodules/ and .submodules/** to [tool.ruff] exclude
- Set force-exclude = true so exclude applies to explicit file arguments too
- Add \.submodules/ to .pre-commit-config.yaml top-level exclude pattern as
  defense-in-depth against pre-commit hooks reaching into vendored trees

Verified: `ruff check --fix .submodules/anthropics-plugins/plugins/hookify/hooks/pretooluse.py`
now reports &#34;No Python files found under the given path(s)&#34; and leaves the
file untouched.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`f67d66a`](https://github.com/ByronWilliamsCPA/.claude/commit/f67d66a7d9aaf9b8b0dd7fb5a6fc66b08a997e23))
### Refactor
* refactor(claude-md): trim to 141 lines, add Compact Instructions

Executes the CLAUDE.md refactor recommended by the 5-model PAL consensus.
Target size was under 200 lines per Claude Code&#39;s documented guidance; the
previous 265-line file consumed ~3.5k tokens on every session start with
significant duplicated content.

Content removed (moved to path-scoped rules or deleted as duplication):
- Testing scope, root-cause order, Golden File Protection -&gt; now in
  .claude/rules/testing.md (path-scoped to test files)
- Python Code Generation Principles (function structure, complexity, code
  duplication, immutability) -&gt; now in .claude/rules/python.md as
  &#34;Function Quality Gates (MANDATORY)&#34; (path-scoped to **/*.py)
- Global Resource Catalog tables (~65 lines of agent and skill tables) -&gt;
  already duplicated in AGENTS-AND-SKILLS.md at repo root; CLAUDE.md now
  just points there
- Install / Update section -&gt; README.md covers this
- Project Integration example -&gt; removed (was an example, not a rule)

Content condensed:
- Project Context: 9 lines -&gt; 6 lines
- Code Quality: 10 lines -&gt; 6 lines (with new pointers to rules/python.md
  and rules/testing.md)
- Core Development Standards + references: 22 lines -&gt; 20 lines
  (consolidated into single pointer block)
- Response-Aware Development full example: 22 lines -&gt; 8 lines
  (trigger syntax stays inline, full workflow moves to
  docs/response-aware-development.md)
- Development Philosophy: 14 lines -&gt; 10 lines (numbered decision order)
- OpenSSF Best Practices: 12 lines -&gt; 7 lines

Content added:
- Compact Instructions section (~20 lines): tells the compaction summarizer
  what to preserve (file paths with line numbers, error messages verbatim,
  architecture decisions, current test state, branch state, decision
  rationale, user-specific corrections) and what to drop (tool logs,
  exploratory detours, request restatements). Per the compaction research,
  CLAUDE.md is the only component guaranteed to survive compaction intact,
  so explicit instructions here shape summarizer behavior.

Version bumped 1.2.0 -&gt; 1.3.0. Live ~/.claude/CLAUDE.md picks up the change
automatically via the symlink to this file.

Expected savings: ~1.7-2k tokens unconditional per session, plus ~600 tokens
saved when not working on Python files (Python gates now path-scoped).

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`424f8f8`](https://github.com/ByronWilliamsCPA/.claude/commit/424f8f89bece2cc58d013d51c04257ea86cfcbd4))
* refactor(rules): extract testing rules and Python function gates from CLAUDE.md

Part of the CLAUDE.md refactor recommended by the 5-model PAL consensus.
Moves operating rules from the always-loaded ~/.claude/CLAUDE.md into
path-scoped rules/*.md files that only load when Claude works on matching
files, reducing unconditional context cost per session.

New file: .claude/rules/testing.md
- Path-scoped to test files, fixtures, and snapshot files
- Contains the testing scope-clarification rule, root-cause investigation
  order, and golden file protection rule
- Does not duplicate coverage thresholds or framework choice (those live in
  .claude/standards/testing.md, which is intentionally unconditional)

Updated: .claude/rules/python.md
- Appends &#34;Function Quality Gates (MANDATORY)&#34; section with function
  structure, complexity controls, code duplication, and immutability rules
- This content was previously inline in CLAUDE.md. Python.md is already
  path-scoped to **/*.py and pyproject.toml, so these principles now only
  load when Claude works on Python files.

Follow-up commits will: remove the duplicated content from CLAUDE.md,
path-scope the remaining unconditional rules files where appropriate, and
harden setup.sh.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`ce3ed16`](https://github.com/ByronWilliamsCPA/.claude/commit/ce3ed1651a152323b7d07cb1ecbdcfcfd041411f))
### Unknown
* Merge pull request #14 from ByronWilliamsCPA/chore/config-refinements-consensus

chore: trim CLAUDE.md, path-scope rules, harden setup.sh ([`9eb24d3`](https://github.com/ByronWilliamsCPA/.claude/commit/9eb24d34b62e1ad548da796555b82bc83ea9c2cf))
* Merge pull request #13 from ByronWilliamsCPA/docs/cowork-instructions

docs(cowork): add paste-in instructions and remove bushido plugin ([`2ce6f4a`](https://github.com/ByronWilliamsCPA/.claude/commit/2ce6f4aa60c4c9361613cc8f4c7084db7e5013c3))
* Merge pull request #12 from ByronWilliamsCPA/chore/uv-lock-reconcile-pyproject-version

chore(deps): reconcile uv.lock with pyproject.toml version ([`a9f0a4b`](https://github.com/ByronWilliamsCPA/.claude/commit/a9f0a4b0e0f5df6b85d83d9280db40932315ad28))
* Merge pull request #11 from ByronWilliamsCPA/docs/sprint-3-git-workflow-governance

docs: Sprint 3 — Git workflow and process governance ([`0738420`](https://github.com/ByronWilliamsCPA/.claude/commit/0738420f6491b98c502bdfa1992e39a6f311557a))
* Merge pull request #10 from ByronWilliamsCPA/docs/sprint-2-code-quality-patterns

docs: Sprint 2 — code quality patterns ([`b593712`](https://github.com/ByronWilliamsCPA/.claude/commit/b5937122ea3b7a2955827408885952c4e0fec46c))
* Merge pull request #9 from ByronWilliamsCPA/docs/sprint-1-security-compliance

docs: Sprint 1 — security and compliance standards ([`535b98e`](https://github.com/ByronWilliamsCPA/.claude/commit/535b98e2e3c994703711f826c507425db122ec96))
## v0.3.0 (2026-04-10)
### Chore
* chore: add docs/audit-report.md to .gitignore (generated artifact) ([`b5eeeb3`](https://github.com/ByronWilliamsCPA/.claude/commit/b5eeeb3285ef2ccc62a4d9a610e7a04ad416bf16))
### Documentation
* docs: add /doc-audit skill implementation plan — TDD, 4-task structure ([`98ee3db`](https://github.com/ByronWilliamsCPA/.claude/commit/98ee3db47fcd058495c11781c248535e72798e59))
* docs: add /doc-audit skill design spec

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`fad94a9`](https://github.com/ByronWilliamsCPA/.claude/commit/fad94a950088c181ecfce4e7eff5d4d48d46d23e))
* docs: add /ci-fix skill implementation plan

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5549c94`](https://github.com/ByronWilliamsCPA/.claude/commit/5549c94a922921fdae4751e77fd135bf2b220c00))
* docs: add /ci-fix skill design spec and fix plan H1

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`48d6f17`](https://github.com/ByronWilliamsCPA/.claude/commit/48d6f1780c77054fc124f029a846c44a07a052ef))
* docs: add CLAUDE.md additions design spec and fix four-hooks frontmatter

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5a0c083`](https://github.com/ByronWilliamsCPA/.claude/commit/5a0c083c21317c71d6f8808befbac7a95831496b))
### Feature
* feat: add /doc-audit skill — terminal summary and audit-report.md writer ([`2f82ffb`](https://github.com/ByronWilliamsCPA/.claude/commit/2f82ffbc4b0ee89cf71ac28d0f95ba68f47db03a))
* feat: implement doc-audit.py — four-category documentation health audit script ([`70104f4`](https://github.com/ByronWilliamsCPA/.claude/commit/70104f429494dbb95e5888b96d04d18dedfb3aad))
* feat: add /ci-fix gate check to PR pre-commit checklist ([`dd18b06`](https://github.com/ByronWilliamsCPA/.claude/commit/dd18b062e8bf291e91b35ec73c4cbd5c46bddc2e))
* feat: add /ci-fix prerequisite to git PR workflow ([`b93c60e`](https://github.com/ByronWilliamsCPA/.claude/commit/b93c60eec7843dcb66a04cea80cb33c096d3bb46))
* feat: add /ci-fix skill — 7-gate CI fix loop with auto-fix and commit offer ([`e8cf3a4`](https://github.com/ByronWilliamsCPA/.claude/commit/e8cf3a439701a2e32bf260618069217d059a82fa))
* feat: integrate hookify, code-review, and security-guidance plugins

Symlinks: writing-rules skill, /code-review command, /hookify and
subcommands (list, configure, help).

Hooks wired in settings.json (now tracked via hooks.json):
- security-guidance: PreToolUse on file edits, blocks dangerous code
  patterns once per session (XSS, shell injection, unsafe deserialization)
- hookify: PreToolUse, PostToolUse, Stop, UserPromptSubmit — enforces
  .claude/hookify.*.local.md rules with no restart required

Workflow integration:
- git/workflows/pr.md: /code-review runs automatically after gh pr create,
  before the PR URL is reported (5-agent review with confidence scoring)
- pre-commit.md: /code-review added as a PR gate checklist item
- git-workflow.md: Gate System section documents both layers

Portability: hooks.json added as source of truth for global ~/.claude/
settings.json hooks; setup.sh now merges hooks.json on each run via jq.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`1f63382`](https://github.com/ByronWilliamsCPA/.claude/commit/1f63382aee5c361188ff816b097132eb116e963f))
* feat: add environment debugging, no-workaround, and project-docs-over-memory rules to CLAUDE.md ([`f514654`](https://github.com/ByronWilliamsCPA/.claude/commit/f51465446aee3ecf6322994374409eb077021bfb))
### Fix
* fix: add hooks.json to REUSE.toml and mark S5332 hotspot safe

- Add hooks.json to MIT annotation in REUSE.toml — file was missing
  SPDX coverage, causing REUSE compliance check failure
- The python:S5332 security hotspot in scripts/doc-audit.py line 310
  is a false positive (checking string prefix to skip URLs, not making
  HTTP connections); marked SAFE in SonarCloud

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5684dca`](https://github.com/ByronWilliamsCPA/.claude/commit/5684dca1f223844a0972ef15202c97921ace6ee4))
* fix: resolve SonarCloud issues in doc-audit.py and setup.sh

- Extract _parse_yaml_scalar_line helper to reduce _parse_simple_yaml
  cognitive complexity from 18 to 13 (S3776)
- Extract _extract_local_path and _check_links_in_file helpers to reduce
  check_links cognitive complexity from 22 to 1 (S3776)
- Add _CLAUDE_SUBDIR constant to eliminate repeated &#34;.claude&#34; literals (S1192)
- Use [[ ]] instead of [ ] for conditionals in setup.sh (S7688)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`99136a8`](https://github.com/ByronWilliamsCPA/.claude/commit/99136a8224460bcd42083be4c02b7feba71a6270))
* fix: add missing spec behaviors (schema_version INFO, count INFO, directory guards), reduce check_versions complexity ([`f406847`](https://github.com/ByronWilliamsCPA/.claude/commit/f406847ca32fc9ea7fcc6bf364490d003def3c43))
* fix: replace type:ignore with importlib.abc.Loader assert, use typing.TypedDict ([`17bb0ce`](https://github.com/ByronWilliamsCPA/.claude/commit/17bb0ce4aadd3bfacff88a39c726939fd0debf2c))
* fix: address quality review issues in /ci-fix skill — retry limit, pip-audit status, nosec format, bandit root detection

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`bd328ce`](https://github.com/ByronWilliamsCPA/.claude/commit/bd328ce7fc81b438d8e53e8ec4d73f81099b8a51))
* fix: clarify flag format and tighten suppression exception in CLAUDE.md rules ([`623296d`](https://github.com/ByronWilliamsCPA/.claude/commit/623296d8e862bbed86edcc59527de8ec1c895034))
### Test
* test: add failing test harness for doc-audit.py — 6 scenarios, 14 tests

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`1d0b819`](https://github.com/ByronWilliamsCPA/.claude/commit/1d0b819ac59d71706966d5a8ebba7326a8450939))
### Unknown
* Merge pull request #6 from ByronWilliamsCPA/feat/four-hooks

feat: four-hooks — insight report improvements (py310 hook, CLAUDE.md rules, /ci-fix, /doc-audit) ([`2e21fe2`](https://github.com/ByronWilliamsCPA/.claude/commit/2e21fe2b27a6c91826ca75e5d65b928ece3a31e3))
## v0.2.0 (2026-04-10)
### Feature
* feat: add four PostToolUse/PreToolUse hook scripts

feat: add four Claude Code hooks (shellcheck, frontmatter, force-push guard, WSL2 notify) ([`a0792ee`](https://github.com/ByronWilliamsCPA/.claude/commit/a0792ee12a53eb0017c45b2a91efe87493f13594))
* feat: add WSL2 toast notification PostToolUse hook for long Bash tasks

Introduces bash-notify.sh, which reads the /tmp/claude-bash-start
timestamp written by bash-pre-hook.sh, computes command duration, and
fires a non-blocking Windows balloon notification via powershell.exe
when the duration exceeds 30 seconds. Wired as a PostToolUse Bash hook
in settings.json. All 6 unit tests pass.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c37cd15`](https://github.com/ByronWilliamsCPA/.claude/commit/c37cd15dd9dd5343a42e1563cee6f732f7eb4110))
* feat: add force-push guard and timing start PreToolUse hook for Bash

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d081b76`](https://github.com/ByronWilliamsCPA/.claude/commit/d081b76dcbcd8b55ab40dcea2c3ed45153479cbd))
* feat: add frontmatter validator PostToolUse hook for skills and agents

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`1e3c62c`](https://github.com/ByronWilliamsCPA/.claude/commit/1e3c62c17f22fc3c77a2fde773c8cd6be73cc541))
* feat: add shellcheck PostToolUse hook for .sh edits ([`c07953c`](https://github.com/ByronWilliamsCPA/.claude/commit/c07953caf41a215d61c6e0d0fe13f0f8cb0f943c))
### Fix
* fix: scope force-push detection to git push only, detect force-with-lease=ref form, suppress SC2016

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`03aaa33`](https://github.com/ByronWilliamsCPA/.claude/commit/03aaa33c13bc63a1a3e5a42454e9a0b126aba591))
* fix: bash-notify stale timestamp ceiling, PS injection sanitization, powershell guard

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c98ccdd`](https://github.com/ByronWilliamsCPA/.claude/commit/c98ccdde8ee284096f4eb9268a7f75b11a453910))
* fix: tighten force-push detection (bare push, path match, atomic timestamp)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`1e5a042`](https://github.com/ByronWilliamsCPA/.claude/commit/1e5a042cdcc600896044981e230925f44af5c5cf))
* fix: validate-frontmatter robustness, CRLF, path pattern, log file, WARN hints

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`4c31765`](https://github.com/ByronWilliamsCPA/.claude/commit/4c317652e4508f946958923ca3b067654727b782))
* fix: tighten set -e and agents path pattern in validate-frontmatter.sh

- Replace set -euo pipefail with set -uo pipefail so the advisory-only hook always exits 0 even when grep or awk return non-zero; add || true guard to awk frontmatter extraction
- Tighten agents path match from *agents*.md (matches filenames) to */agents*/*.md (requires agents to appear as a directory name component, not just in the filename)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d4c1148`](https://github.com/ByronWilliamsCPA/.claude/commit/d4c11481854c4aa7c75fa8292179f6aaf85a3a03))
## v0.1.0 (2026-04-10)
### Chore
* chore: align docs and rules with superpowers integration

- CLAUDE.md: fix sync instructions (cp -r → git submodule init),
  split skills table into custom and superpowers sections
- AGENTS-AND-SKILLS.md: add project-plan-synthesizer to Planning
  section, add full Superpowers Skills section (14 skills), expand
  Quick Reference table
- Add project-plan-synthesizer agent ported from image-preprocessing-detector
- git-workflow.md: remove inline worktree commands, point to
  using-git-worktrees and finishing-a-development-branch skills
- git-worktree.md: slim to when-to-use guidance and reminders,
  superpowers skills own the command detail
- supervisor.md: add dispatching-parallel-agents, subagent-driven-development,
  requesting/receiving-code-review, systematic-debugging to assignment table
- docs: add cookiecutter team handoff document

https://claude.ai/code/session_01EQKyt7fqRw1vvAnWMKLN2r ([`6f0e0c0`](https://github.com/ByronWilliamsCPA/.claude/commit/6f0e0c089d64d43d32cc2caacbe21ef14cf1511e))
* chore: improve testing skill, add eval artifacts, update gitignore

- Add Context Loading Guide to testing/SKILL.md: async mock reminders,
  file I/O conditional tmp_path, httpx/pydantic pre-generation checklists
- Add test-coverage and testing eval artifacts (evals.json, evals-r3.json)
- Update .gitignore: ignore skill workspace/variant-b dirs and evals-r2.json
  iteration artifacts to keep tracked evals clean

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`db4b6d7`](https://github.com/ByronWilliamsCPA/.claude/commit/db4b6d7ab1824e5d2af5ecf0cfbc4a65e2ed3ea9))
* chore: sync submodule pointers after submodule PRs merged

Updates .submodules pointers to the merged main commits for both
reference-library and image-generation, which landed after the parent
PR was merged.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`b66113f`](https://github.com/ByronWilliamsCPA/.claude/commit/b66113fbecb989292074fa71444701438c4c6d21))
* chore: update submodule pointers for agent frontmatter fixes

Points reference-library and image-generation submodules to commits
that add missing agent frontmatter and apply Ruff formatting.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d4e668f`](https://github.com/ByronWilliamsCPA/.claude/commit/d4e668fb198b17b5d21055e1b49824929102b657))
* chore: remove A/B test artifacts and untrack tmp_cleanup backup

Remove skill variant/workspace eval directories from disk and stop
tracking the tmp_cleanup backup snapshot that was accidentally committed
before the gitignore rule was in place.

- Deleted: .claude/skills/quality-variant-b/, quality-workspace/,
  testing-variant-b/, testing-workspace/, quality/evals/
- Removed stale gitignore entries for testing-workspace/ and
  testing-variant-b/
- Staged deletion of 76 tmp_cleanup/.backup-root-duplicates-* files

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d6c1df0`](https://github.com/ByronWilliamsCPA/.claude/commit/d6c1df07b3dae05dcac7d9d1d9f3bb903d0e69a1))
* chore: update submodule references after standalone repo commits

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`03f7e97`](https://github.com/ByronWilliamsCPA/.claude/commit/03f7e97b0c43cb1a98f83a8e43c7b5d4389edd53))
* chore(deps): update trufflehog hook to v3.92.3

- Updated from v3.63.11 to v3.92.3 (fixes Go build compatibility)
- Changed to git-based scanning (only staged changes, not full filesystem)
- Avoids false positives from .venv and other non-repo files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 &lt;noreply@anthropic.com&gt; ([`567734c`](https://github.com/ByronWilliamsCPA/.claude/commit/567734c58e2f6f45668cbe63bf2222df72417805))
* chore: remove .cruft.json (template source, not generated project)

This repository is the source for Claude configuration files that get
pulled into downstream projects via cookiecutter, not a project generated
FROM the template. Cruft is designed for generated projects, not template
sources.

Quality assurance strategy:
- Manually sync .claude/ updates from/to cookiecutter template
- Run linters (ruff, qlty) before committing to prevent downstream issues
- Maintain consistency by copying .claude/ bidirectionally as needed

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`014968a`](https://github.com/ByronWilliamsCPA/.claude/commit/014968a4a73edc526761707597b99c78ba5e0fdd))
* chore: clean up template repository structure

- Remove cache and generated files (~700K saved)
  - .ruff_cache/, htmlcov/, .coverage, coverage.xml
  - __pycache__/ and .pytest_cache/ directories

- Remove root duplicate directories (backed up to tmp_cleanup/)
  - agents/, commands/, context/, skills/, templates/
  - These should only exist in .claude/ per cookiecutter template

- Sync .claude/ directory from cookiecutter template
  - Now matches cookiecutter exactly (29 files)
  - Fixed duplicate .github/workflows/.claude/ directory

- Remove Python package source (template repo, not distributable package)
  - src/claude_config/ directory removed
  - src/ directory removed (now empty)

- Remove fuzzing infrastructure (overkill for template)
  - .clusterfuzzlite/ and fuzz/ directories

- Remove unnecessary CI workflows
  - publish-pypi.yml (not publishing to PyPI)
  - mutation-testing.yml (expensive, overkill for template)
  - slsa-provenance.yml (not building artifacts)

- Remove template artifacts
  - CONFIG_TEMPLATES_SUMMARY.md
  - SONARQUBE-SETUP.md

- Update pyproject.toml
  - Add lint exceptions for .claude/**/*.py template files
  - Allow T201 (print), C901 (complexity), PLR0912 (branches)

- Add cleanup scripts
  - scripts/cleanup-template-repo.sh (automated cleanup)
  - scripts/verify-template-consistency.sh (template verification)

All lint checks passing (ruff check . → All checks passed!)
Repository now matches cookiecutter template structure.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`666a97c`](https://github.com/ByronWilliamsCPA/.claude/commit/666a97cb2545bf276288984b048081283420c842))
### Documentation
* docs: add implementation plan for Python 3.10/3.14 compat hook

Four-task plan: test harness, hook script, settings.json wiring, and
log verification. Includes complete script content and known limitations
for parenthesized-with and fromisoformat Z-suffix detection.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`8ad35be`](https://github.com/ByronWilliamsCPA/.claude/commit/8ad35be8335cc4f3548bd5cf74afb3e6be44558b))
* docs: add design spec for Python 3.10/3.14 compat PostToolUse hook

Captures approved two-tier design (grep + AST) for detecting Python
version boundary violations after Edit/Write tool calls.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`a1c0d52`](https://github.com/ByronWilliamsCPA/.claude/commit/a1c0d523a720766931807d37311afc5a6c9a0d1d))
* docs: add cookiecutter Claude config removal handoff

Handoff document for the cookiecutter-python-template team covering
the decision to move Claude configuration to user-level only, with
specific files to remove, docs to update, and cruft merge logic to
preserve before deleting the merge-standards agent.

https://claude.ai/code/session_01EQKyt7fqRw1vvAnWMKLN2r ([`7625d56`](https://github.com/ByronWilliamsCPA/.claude/commit/7625d56dcf8d24259ca73356e5bb40acf12f59bc))
* docs: update CLAUDE.md with behavioral rules, skill catalog, and sync instructions

- Add project context, CI compatibility, code quality, testing, and shell sections
- Add /sonarcloud to skill catalog table
- Add sync instructions for downstream projects
- Add agent assignment patterns for new agents
- Update .gitignore for tmp_cleanup/
- Add .claudeignore
- Add .claude/settings.json with hooks configuration
- Add MCP minimal bloat standard

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`31f1043`](https://github.com/ByronWilliamsCPA/.claude/commit/31f1043a70b41aa4e2aefff7bc9dbb392bf95e90))
* docs: add manual sync workflow with cookiecutter template

- Documents why cruft is not appropriate for this repository
- Provides step-by-step manual sync workflows (bidirectional)
- Includes quality assurance strategy to prevent downstream issues
- Covers linting configuration updates and testing procedures
- Adds troubleshooting guide and regular maintenance checklist

This ensures quality control without cruft&#39;s limitations for template
source repositories.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`303fb96`](https://github.com/ByronWilliamsCPA/.claude/commit/303fb96b60778609b1a67a52e65aa2fd11a4e396))
* docs(standards): streamline testing.md, create cookiecutter handoff

- Remove test verification tool implementations from testing.md
- Keep standards/requirements (what to test) in Claude standards
- Move implementation tools (how to verify) to cookiecutter handoff
- Reduce testing.md from ~1400 lines to ~1050 lines

Handoff document includes:
- verify_test_structure.py
- check_test_ratios.py
- audit_test_coverage.py
- weekly_test_audit.py
- GitHub Actions workflow
- Pre-commit hooks
- conftest.py marker tracking ([`eea4645`](https://github.com/ByronWilliamsCPA/.claude/commit/eea4645607ab80590a07cea430923a1e2cc7cd96))
* docs(standards): add test compliance verification system

Add comprehensive Test Compliance Verification section including:
- Directory structure validation script
- Test marker coverage reporting via pytest hooks
- Test ratio enforcement (unit:integration:e2e pyramid)
- Module coverage audit to find untested modules
- CI/CD integration with GitHub Actions workflow
- Pre-commit hooks for structure and new-code-has-tests
- Weekly audit report generator
- Project type requirements matrix (Library, API, CLI, ML) ([`bacd804`](https://github.com/ByronWilliamsCPA/.claude/commit/bacd80447cdd428b6c7e9b458302c314d85a6fb9))
* docs(standards): enhance testing standards with comprehensive patterns

Add new sections based on image-preprocessing-detector patterns:
- Core Testing Philosophy with 5 guiding principles
- Security Testing section with CodeQL validation examples and CWE mapping
- Performance Testing with environment-aware thresholds and timing methodology
- Test Data Management with storage strategy and fixture organization
- Optional Dependency Handling for graceful test degradation
- Troubleshooting guide for local vs CI failures, coverage gaps, flaky tests

Enhanced existing sections:
- Directory structure now includes security/, benchmark/, api/ directories
- Added markers: security, requires_full_dataset, real_data
- Mutation testing expanded with status reference, module targets,
  prioritization strategy, and allowlist documentation ([`13f77a3`](https://github.com/ByronWilliamsCPA/.claude/commit/13f77a3ebfb16a49c9fcd5c20040a4419c9f7777))
* docs(standards): add comprehensive testing standards

Add testing.md covering:
- Coverage requirements (80% min, branch coverage)
- Test organization (unit/integration/e2e structure)
- AAA pattern with examples
- Fixture strategies (basic, factory, async)
- Mocking approaches for services and databases
- Parametrized and property-based testing
- Test markers and naming conventions
- Pytest configuration for uv-based projects
- CI/CD integration examples
- Mutation testing guidelines ([`dba12d3`](https://github.com/ByronWilliamsCPA/.claude/commit/dba12d3fcbd635dd4e860eeef43da325b73990d1))
### Feature
* feat: add Python 3.10/3.14 compat PostToolUse hook script

Two-tier check: grep for API/import patterns (floor 3.11+, ceiling 3.14)
and Python AST scan for syntactic patterns (match/case, except*).
Degrades gracefully when jq or python3 are unavailable. Always exits 0.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`2b3d786`](https://github.com/ByronWilliamsCPA/.claude/commit/2b3d786bd03aed8291d3ea5e2167efb7f5306b51))
* feat: delegate security/coverage in phase-reviewer, add RAD assumption gate

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`4944629`](https://github.com/ByronWilliamsCPA/.claude/commit/494462995f641c7e3c533a723c6be1e172981adf))
* feat: add finishing-a-development-branch chain and phase N+1 offer to phase-gate READY path

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`2b1f191`](https://github.com/ByronWilliamsCPA/.claude/commit/2b1f1918f0c88141aaab63ff3ee4443c5752c0eb))
* feat: expand phase-gate plan mode with worktree setup and execution dispatch

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7dd88a7`](https://github.com/ByronWilliamsCPA/.claude/commit/7dd88a7f442a3cb93f9c4386763936108147dd66))
* feat: update bridge mode with synthesizer, phase selection, and scoped writing-plans handoff ([`70c643a`](https://github.com/ByronWilliamsCPA/.claude/commit/70c643a4430062b2798c8d9e83264f3bccffd744))
* feat: add entry and bridge modes to project-planning skill

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7db5373`](https://github.com/ByronWilliamsCPA/.claude/commit/7db53737ba508edcb1c9e8ed343038d404658c4c))
* feat: add planning-bridge-gate PreToolUse hook script

Adds a bash hook script that intercepts Skill tool calls targeting
writing-plans and blocks them with exit 2 when a brainstorming spec
exists but no ADR or Roadmap has been generated yet. Also adds the
implementation plan document with proper frontmatter.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`0098bb0`](https://github.com/ByronWilliamsCPA/.claude/commit/0098bb06055dc5a658e5121dbb707cb070509423))
* feat: add anthropics skill/plugin submodules with curated symlinks

Add anthropics/skills and anthropics/claude-plugins-official as
submodules. Replace local skill-creator with upstream symlink (identical
content). Symlink selected skills and agents:

Skills (anthropics/skills): docx, xlsx, pdf, pptx, skill-creator
Skills (anthropics-plugins): claude-md-improver, session-report,
  claude-automation-recommender
Agents (pr-review-toolkit): comment-analyzer, pr-test-analyzer,
  silent-failure-hunter, type-design-analyzer, code-simplifier,
  pr-toolkit-code-reviewer
Commands: /review-pr, /revise-claude-md

Also bring in writing skill, rules/writing.md, and writing-quality.md
from pre-existing local work. Update AGENTS-AND-SKILLS.md catalog.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`c26e7f2`](https://github.com/ByronWilliamsCPA/.claude/commit/c26e7f27413764e9f259e2dc79d00ec626b50499))
* feat: integrate superpowers as submodule with skill symlinks

Add obra/superpowers as a git submodule at .submodules/superpowers.
Symlink all 14 superpowers skills into .claude/skills/ following the
existing pattern used for reference-library and image-generation.

Adds SessionStart hook entry to settings.json so superpowers injects
the using-superpowers meta-skill at session start alongside the
existing keyword-tool-trigger reset.

Skills added via symlink:
- brainstorming, writing-plans, executing-plans
- subagent-driven-development, requesting-code-review, receiving-code-review
- test-driven-development, systematic-debugging, verification-before-completion
- dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch
- writing-skills, using-superpowers

After pulling, run: git submodule update --init --recursive

https://claude.ai/code/session_01EQKyt7fqRw1vvAnWMKLN2r ([`06e7779`](https://github.com/ByronWilliamsCPA/.claude/commit/06e7779e468a430bba034f36c1e40e7f7e3c5e3c))
* feat: add canonical package registry and move standards under .claude/

- Add .claude/standards/packages.md: authoritative package registry with
  canonical choices, AOSS markers, override policy, and migration table
- Move standards/ → .claude/standards/ for consistency with agents/rules/commands/
- Update CLAUDE.md to reference packages standard and sync instructions
- AOSS markers validated against official supported packages list:
  arq, hatchling, cookiecutter, hypothesis, factory-boy, fakeredis,
  interrogate, bandit, detect-secrets, python-gnupg, opentelemetry-api/sdk,
  statsmodels, sentence-transformers, dnspython, checkov all confirmed AOSS;
  beautifulsoup4, pyjwt, mkdocs corrected to not-in-AOSS

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`571bc72`](https://github.com/ByronWilliamsCPA/.claude/commit/571bc72aeb8cb9fd1a22f6cf2c6dbc0e000f9f35))
* feat(skills): update skill-creator eval scripts and testing eval fixtures

Improve skill evaluation infrastructure across skill-creator, test-coverage,
and testing skills.

- skill-creator: significant enhancements to eval loop, report generation,
  benchmark aggregation, review generation, description improvement, package
  script, quick validation, and shared utils
- test-coverage: update parse_coverage.py script
- testing/evals: update validators.py and weak_tests.py eval fixtures
- .gitignore: add docs/content_reviews/ to ignored paths

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`05a212b`](https://github.com/ByronWilliamsCPA/.claude/commit/05a212b9d6df9a6115d5d338757f405b32b947b3))
* feat: consolidate agent/skill sources via git submodules

Replaces machine-specific symlinks and scattered source locations with a
portable submodule-based structure. All agents and skills now resolve
correctly on any machine after a single setup.sh run.

- Add reference-library and image-generation as submodules under .submodules/
- Replace absolute symlinks in .claude/agents/ with portable relative paths
  (../../.submodules/&lt;repo&gt;/agents/&lt;file&gt;.md)
- Move visual-content-generator.md from root agents/ into .claude/agents/
- Move skill-creator from .agents/ into .claude/skills/ (no longer hidden/untracked)
- Add setup.sh to bootstrap ~/.claude/ symlinks including ~/.claude/reference-library
  for stable {{LIBRARY_PATH}} resolution without file substitution
- Rewrite .claude/README.md with accurate architecture, invariants, and
  runbooks for adding agents, skills, and submodules
- Exclude skill-creator (third-party tool) from darglint docstring checks

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`7cc4945`](https://github.com/ByronWilliamsCPA/.claude/commit/7cc494517db6242c060d28fef2b7cc35339a736d))
* feat: add handoff command, CI lint-fix script, and visual content agent

- Add handoff command for session continuity documents
- Add ci-lint-fix.sh script for CI linting automation
- Add visual-content-generator agent

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`24fb334`](https://github.com/ByronWilliamsCPA/.claude/commit/24fb33497256d22384f110df91ecbeda4a46bf95))
* feat(skill): add phase-gate skill with reviewer, validator, and analyzer agents

- Add phase-gate skill for phase readiness evaluation with quality gates
- Add phase-reviewer agent for quality gate execution
- Add plan-validator agent for implementation plan validation
- Add scope-analyzer agent for scope completion analysis

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`ae01e22`](https://github.com/ByronWilliamsCPA/.claude/commit/ae01e2218e9e484f64727c9e4049f343cf3436ce))
* feat(security): add OWASP specialist agents and dispatch system

- Add owasp-dispatch agent to route to 6 OWASP specialists
- Add owasp-web, owasp-api, owasp-llm, owasp-ml, owasp-citizen, owasp-agent
- Update security-auditor agent
- Add OWASP specialist agents specification

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`2cb6a25`](https://github.com/ByronWilliamsCPA/.claude/commit/2cb6a25c474a0f15ecf754e99f97aec15926ebd7))
* feat(testing): add test agents, coverage skill, and updated standards

- Add test-writer agent for coverage-driven iterative test generation
- Add test-reviewer agent for test quality validation (APPROVE/NEEDS_WORK)
- Add test-coverage skill with analyze, generate, and enforce modes
- Add debug-tests command for root-cause-first failure analysis
- Add testing guide and testing patterns context
- Update testing standards and commands
- Add test-coverage agent specification

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`7df51ed`](https://github.com/ByronWilliamsCPA/.claude/commit/7df51ed4189e55210ef69cd3a0ba8468801573cd))
* feat(skill): add /sonarcloud skill for issue review and setup diagnostics

New skill providing SonarCloud integration via MCP servers:
- Auto-detects project org/key from workspace config files
- Routes to correct MCP server (byronwilliamscpa:8090, williaby:8091)
- Modes: summary, issues, fix, gate, rule, analyze, check
- Check mode validates full setup: Docker, config consistency, remote access
- Documents SonarSource product naming (SonarLint→SonarQube for IDE, etc.)
- Includes ecosystem data flow diagram and VS Code integration points

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`ac77977`](https://github.com/ByronWilliamsCPA/.claude/commit/ac77977cefdf6f599b7c9e377170b7665c552989))
* feat(standards): add code generation principles and migrate Black to Ruff

Add comprehensive code generation principles to CLAUDE.md:
- Function structure: length limits (20-60 preferred, 100 max), single
  responsibility, early returns, nesting depth (≤3)
- Complexity controls: cyclomatic (≤10), branches (≤12), cognitive load
- Code duplication: zero tolerance, rule of three, template patterns
- Data &amp; state design: immutability, pure functions, no global state,
  parameter grouping with dataclasses
- Naming standards: descriptive variables, verb-based functions,
  boolean prefixes
- Documentation requirements: docstrings, inline comments, type hints

Replace Black references with Ruff format across all standards:
- CLAUDE.md: Update essential requirements and commands
- standards/python.md: Update formatting and linting sections
- standards/linting.md: Update configuration, pre-commit, CI/CD,
  VS Code settings, and workflow examples

This aligns with template-sample repo which uses Ruff for both
formatting and linting (Black-compatible output). ([`5533d7d`](https://github.com/ByronWilliamsCPA/.claude/commit/5533d7df7c100f4f15a5338c9621f6b746002059))
* feat(mcp): implement tiered MCP tool loading strategy

Based on Anthropic&#39;s Advanced Tool Use Guide, implement a 3-tier loading
strategy to reduce context consumption by 85-95%:

Tier 1 (Always Loaded - ~3K tokens):
- zen: thinkdeep, codereview, tiered_consensus, chat
- context7: resolve_library_id, get_library_docs
- github: get_file_contents

Tier 2 (Agent/Skill Bundled):
- Tools loaded when specific agents invoked via Task tool
- Updated 10 agent definitions with mcp_tools frontmatter

Tier 3 (Keyword Triggered):
- Docker, Playwright, Postgres, Sentry, Mermaid tools
- Loaded based on keyword detection in user prompts

Changes:
- Add mcp/mcp_config.yaml with full tiered configuration
- Add scripts/mcp-tool-loader.sh for agent tool loading
- Add scripts/keyword-tool-trigger.sh for keyword detection
- Add scripts/track-mcp-usage.sh for usage analytics
- Update settings.json with new hooks
- Update CLAUDE.md with MCP strategy documentation
- Update agent definitions with mcp_tools bundles

Removed: sequentialthinking (redundant with zen.thinkdeep) ([`fb43a63`](https://github.com/ByronWilliamsCPA/.claude/commit/fb43a63e308900204c8393d72e5c24a0529523ee))
* feat: migrate Claude Code configuration from williaby/.claude

Migrate all configuration files and directories from the original
williaby/.claude repository to the new ByronWilliamsCPA/.claude
structure generated from the cookiecutter Python template.

Migrated content:
- agents/ - 22 agent definitions for Claude Code
- commands/ - 14 slash commands for quality, security, testing
- context/ - 3 context files for development standards
- docs/ - 7 documentation files including setup guides
- mcp/ - MCP server configurations and examples
- skills/ - 5 skill directories (git, quality, rad, security, testing)
- standards/ - 5 development standard files
- templates/ - 2 project templates
- tests/ - BATS test suite for setup scripts

Configuration files:
- CLAUDE.md - Global Claude Code development standards
- settings.json - Claude Code settings
- .mcp.json - MCP server configuration
- SECURITY.md - Security policy

This provides a proper repository structure with:
- Cruft template tracking for updates
- Pre-commit hooks and quality tooling
- MkDocs documentation infrastructure
- GitHub Actions CI/CD workflows
- Semantic release automation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`843f85a`](https://github.com/ByronWilliamsCPA/.claude/commit/843f85a5117eeb2115215f08eb3f71a89c9ce9aa))
### Fix
* fix: address all Copilot, CodeRabbit, QLTY, and SonarQube review comments

Scripts (scripts/py310-compat-check.sh):
- Add grep -P (PCRE) capability check with graceful fallback for macOS/BSD grep
- Fix tomllib import pattern to allow leading whitespace (indented imports)
- Expand datetime ceiling patterns to explicitly match both datetime.utcnow()
  and datetime.datetime.utcnow() calling styles
- Remove ast.Match detection: match/case is valid Python 3.10+ syntax and the
  project floor is 3.10, so flagging it produces false positives
- Add explicit return 0 to log() function (SonarQube shelldre:S7682)

Scripts (scripts/planning-bridge-gate.sh):
- Add jq guard: fail-open (exit 0) if jq is absent to prevent hook from
  blocking PreToolUse execution on systems without jq
- Add explicit return 0 to log() function (SonarQube shelldre:S7682)

Spec (docs/superpowers/specs/2026-04-09-py310-compat-hook-design.md):
- Fix frontmatter status: draft -&gt; published (consistent with header)
- Remove match/case from Tier 2 pattern table (not a floor violation at 3.10)
- Fix utcfromtimestamp recommended fix: UTC -&gt; datetime.timezone.utc (UTC
  is itself a 3.11+ feature; recommendation must stay 3.10-compatible)
- Update output example and Testing section to remove match/case references

Plan (docs/superpowers/plans/2026-04-09-py310-compat-hook.md):
- Clarify Test 2 uses datetime.datetime.utcnow() (fully-qualified form);
  document that grep matches both styles as a substring
- Replace Test 5 match statement with except* test (actual 3.11+ violation)
- Update cleanup list to remove t5_match.py reference

Plan (docs/superpowers/plans/2026-04-09-planning-bridge-gate.md):
- Fix source frontmatter from directory reference to explicit inline note

Skill (.claude/skills/project-planning/SKILL.md):
- Fix Modes intro: two modes -&gt; three modes (Entry, Bridge, Default)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`e40816b`](https://github.com/ByronWilliamsCPA/.claude/commit/e40816bf1f1a00531511c7f1d861ca10d0324a9a))
* fix(reuse): add .trivyignore to REUSE.toml annotations

.trivyignore is a security scanning configuration file — add it to the
existing dotfile configs annotation block alongside .shellcheckrc and
.yamllint. Using REUSE.toml (not inline headers) per project convention.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`47a3ee2`](https://github.com/ByronWilliamsCPA/.claude/commit/47a3ee2e00ceb141942faf3f66c9c05e269ba4c9))
* fix(deps): upgrade all locked dependencies to resolve 28 CVEs

uv lock --upgrade bumps all packages to latest compatible versions,
resolving every exploitable vulnerability except one unfixable case:

Fully resolved:
- authlib: 1.6.5 → 1.6.9 (CRITICAL: CVE-2026-27962 Bleichenbacher oracle;
  HIGH: CVE-2026-28802 SSRF, CVE-2026-28490 JWT alg confusion)
- cryptography: 46.0.3 → 46.0.7 (HIGH: CVE-2026-26007 RSA side-channel,
  CVE-2026-34073 PKCS12 memory corruption)
- tornado: 6.5.2 → 6.5.5 (HIGH: HTTP smuggling, open redirect)
- requests: 2.32.5 → 2.33.1 (HIGH: CVE-2026-25645 proxy credential leak)
- urllib3: 2.5.0 → 2.6.3 (HIGH: CVE-2025-66418, CVE-2025-66471)
- marshmallow: 4.1.0 → 4.3.0 (HIGH: CVE-2025-68480 ReDoS)
- nbconvert: 7.16.6 → 7.17.1 (HIGH: CVE-2025-53000 XSS)
- nltk: 3.9.2 → 3.9.4 (HIGH: CVE-2025-14009 path traversal,
  CVE-2026-33230 XXE)
- protobuf: 6.33.1 → 7.34.1 (HIGH: CVE-2026-0994 DoS)
- pyasn1: 0.6.1 → 0.6.3 (HIGH: CVE-2026-30922 infinite loop)
- pygments: 2.19.2 → 2.20.0 (HIGH: CVE-2026-4539 ReDoS)
- pip: 25.3 → 26.0.1 (HIGH: CVE-2026-1703 malicious wheel exec)
- virtualenv: 20.35.4 → 21.2.1 (MEDIUM: CVE-2026-22702)
- filelock: 3.20.0 → 3.25.2 (MEDIUM: temp file race)

Accepted/ignored via .trivyignore:
- py 1.11.0 (CVE-2022-42969, ReDoS in py.path.svnwc): no upstream fix;
  only reachable via SVN paths — this project does not use SVN;
  dev-only dependency via interrogate

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c5bd4e1`](https://github.com/ByronWilliamsCPA/.claude/commit/c5bd4e1c1c981e823911d8d7c497b0dadc0faf67))
* fix: resolve semantic-release parser and scorecard private-repo failures

- Change commit_parser from &#39;conventional_commits&#39; to &#39;angular&#39; — the
  v9 parser was renamed and the old value caused an invalid import error
  on every main push
- Move changelog_file to changelog.default_templates per v9 deprecation
  warning (compatibility breaks in v10)
- Set scorecard publish_results=false and add repo_token — private repos
  cannot publish Scorecard results; missing token caused GraphQL
  ListCommits failures on every run

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`5cd72c5`](https://github.com/ByronWilliamsCPA/.claude/commit/5cd72c54f1aa8632ab822e043f7664835605b374))
* fix: catch multiline typing imports and align fix-line indentation

- Move Self/LiteralString detection to AST tier (catches multiline imports)
- Remove duplicate Tier 1 grep patterns for Self/LiteralString
- Align fix-line indentation to column 26 across Tier 1 and Tier 2
- Note ExceptionGroup grep is best-effort in finding output

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`4e327c4`](https://github.com/ByronWilliamsCPA/.claude/commit/4e327c4f2ef737a997a34e45d22d280aed09e2a3))
* fix: clean up phase-reviewer quality issues from code review

- Remove ineffective grep -v filter (CRITICAL/VERIFY tags are on separate lines)
- Move owasp-dispatch delegation prose outside bash code fence
- Remove redundant &#34;Add to Quality Gates table&#34; instruction in RAD section
- Reference CLAUDE.md as source of truth for coverage thresholds ([`a216fef`](https://github.com/ByronWilliamsCPA/.claude/commit/a216fef4aa279de781b13dc4dea6107b609a5faf))
* fix: address PR review comments from Copilot

- settings.json: replace direct submodule hook path with wrapper script
  to support both direct-clone and two-layer (setup.sh) install layouts
- scripts/run-superpowers-session-start.sh: new wrapper resolves repo
  root via readlink so hook works regardless of how ~/.claude is mounted
- setup.sh: add scripts/ symlink so $HOME/.claude/scripts/ hooks resolve
  in two-layer setup
- CLAUDE.md: document both install methods (Option A: two-layer with
  setup.sh; Option B: direct clone to ~/.claude)
- .claude/rules/writing.md: replace em-dashes in section headings with
  parentheses; fix relative path to writing-quality.md
- .claude/skills/writing/workflows/analyze.md: fix &#34;five&#34; to &#34;six&#34;
  (six inputs listed, not five)
- .claude/skills/skill-creator: restore missing symlink to upstream

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`573f1ae`](https://github.com/ByronWilliamsCPA/.claude/commit/573f1aed2c3fb22013fd848766cac122541569bf))
* fix: resolve pre-merge review issues from superpowers branch

Replace em-dashes with colons in project-plan-synthesizer.md and the
cookiecutter handoff doc per rules/writing.md. Update writing-skills
trigger text in CLAUDE.md to remove collision with skill-creator.
Add required frontmatter to handoff doc for schema validation.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`01c344c`](https://github.com/ByronWilliamsCPA/.claude/commit/01c344cd0a950b287aa21d87efc2255077c01a94))
* fix(ci): resolve remaining Build Docs and Test Python 3.12 failures

Build Docs (--strict mode):
- Add exclude_docs to mkdocs.yml for content-review.md, content_reviews/*,
  ADRs/adr-template.md, planning/project-plan-template.md,
  planning/adr/README.md (internal/template docs with out-of-docs links)
- Fix docs/guides/testing-guide.md: convert broken relative link to
  standards/testing.md into plain text (file is outside docs/ dir)

Test Python 3.12 (ruff ARG001):
- utils/logging.py: actually use the level param by calling
  logging.basicConfig(level=...) before structlog.configure()

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`4e43909`](https://github.com/ByronWilliamsCPA/.claude/commit/4e4390973a10aa9382243061a6310835bc1d0c02))
* fix(ci): address all 15 CodeRabbit PR review comments

- pip-audit flag: --output=json → --format json in standards/security.md
  and docs/guides/testing-guide.md (--output treats arg as filepath)
- precommit.md: remove safety:* from allowed-tools; replace safety check
  with pip-audit in step 5
- security/SKILL.md: remove duplicate `uv run safety check` line
- aggregate_benchmark.py: replace datetime.UTC with datetime.timezone.utc
  for Python 3.10 compatibility
- pytest-patterns.md: fix typo &#34;valid-plus-subomain&#34; → &#34;valid-plus-subdomain&#34;
- docs/index.md: align quick-start install with guides (uv pip install)
- testing/workflows: replace Task tool references with Agent tool
  (subagent_type=&#34;test-engineer&#34;) in performance.md and e2e.md
- content-review.md: remove stale Known Issues entry
- mcp_config.yaml + .mcp.json: rename server key zen → pal so tool prefix
  mcp__pal__* matches the configured server name
- standards/testing.md: separate SAST and dependency audit into distinct
  CI steps; fix resulting step numbering

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`eed8cca`](https://github.com/ByronWilliamsCPA/.claude/commit/eed8cca34b2e5c32594447bbe27dc91b55158397))
* fix(ci): resolve REUSE compliance, missing package, and mkdocs script

- Update REUSE.toml to cover .claude/**, standards/**, mcp/**,
  tmp_cleanup/**, and root dotfiles/config files — brings compliance
  from 225/397 to 408/408 (all files covered)
- Create src/claude_config/ package (Settings, get_logger,
  log_performance, setup_logging) so all 15 unit tests pass
- Add tools/gen_tools_catalog.py no-op placeholder so mkdocs
  gen-files plugin finds its configured script

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`b087495`](https://github.com/ByronWilliamsCPA/.claude/commit/b0874956d75e24cbcd20718086dc3920d4a06b2c))
* fix(content-review): apply P4 and P5 content review corrections (31 files)

Complete the content review sweep across all supporting and meta files.

P4 fixes (7 of 16 files):
- AGENTS-AND-SKILLS.md: fixed Task→Agent tool invocation; removed non-existent
  /commit-prepare and /pr-prepare skills; fixed /debug-tests link; added 10
  uncatalogued agents (writing pipeline, diagrams/visuals group)
- copilot-instructions.md: Black→ruff format (2 occurrences)
- mcp/README.md: zen-server.json→disabled; Zen MCP Server→PAL MCP Server
- docs/development/code-quality.md: &#34;Black compatible&#34;→ruff format default
- docs/development/testing.md: coverage thresholds corrected to 80/70/90/90
- docs/guides/usage.md: pip install→uv pip install
- docs/guides/testing-guide.md: mypy→basedpyright throughout; pip install→uv
  sync/uv add in CI steps; 13 plugin table entries fixed

P5 fixes (2 of 15 files):
- CONTRIBUTING.md: uv run safety check→uv run pip-audit
- docs/index.md: pip install→uv add

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`55198dd`](https://github.com/ByronWilliamsCPA/.claude/commit/55198ddc35d1551cfc9b47a9de4910e9a738c6ae))
* fix(content-review): apply P3 content review corrections (44 files)

Fix stale tool references and missing frontmatter across all P3 workflow,
context, skill-creator, project-planning, and standards files.

Key fixes across 20 files:
- poetry→uv, mypy→basedpyright, black→ruff format, safety→pip-audit
- bandit standalone→ruff --select S (bandit rules via ruff)
- mcp__zen-core__/mcp__zen__→mcp__pal__ in RAD verify.md + response-aware-development.md
- git commit.md: added required -S signing flag
- git pr.md: gh pr create→/git pr skill as primary method
- security/scan.md: added pip-audit exit code documentation
- skill-creator agents (grader, comparator, analyzer): added missing frontmatter
- standards/*.md: extensive poetry/mypy/black→uv/basedpyright/ruff fixes
- project-planning/SKILL.md (P2 bonus): mcp__zen__consensus→mcp__pal__consensus (6 occurrences)

24 files reviewed OK (no changes needed); 20 files fixed.

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`d929c58`](https://github.com/ByronWilliamsCPA/.claude/commit/d929c5872460c141f953ab482d91bd0fb0d7b090))
* fix(content-review): apply P1 and P2 content review corrections

Fixes all Priority 1 (always-loaded rules) and Priority 2 (agents and
skill entry points) issues identified in docs/content-review.md:

P1 rules (6 files):
- git-workflow.md: replace mypy → basedpyright, add breaking-change note
  and cross-references
- mcp-strategy.md: fix agent frontmatter docs, add skill bundles table,
  update Tier 3 keywords
- pre-commit.md: add tests/RAD steps, clarify /security and /quality
  scope, fix pip-audit and PR tool references
- python.md: fix Black attribution, expand Ruff rules table, clarify
  Python version range, add BasedPyright config example
- supervisor.md: remove ghost agent, fix PR workflow to use /git skill
- CLAUDE.md: name pip-audit, scope Code Gen header to Python, add
  variant skills note

P2 agents (17 files):
- Add complete frontmatter (name/description/model/tools) to all 13
  agents that were missing it entirely (core testing, OWASP, phase-reviewer)
- Add model and tools to 4 agents with partial frontmatter
  (planning/writing agents, visual-content-generator)
- Fix deprecated invocation format (/review, /test, Task tool) → Agent tool
- visual-content-generator: replace non-standard mcp_tools field with tools

P2 skills (4 files):
- quality/SKILL.md: add frontmatter, remove all Black references, fix
  trigger keywords
- security/SKILL.md: add frontmatter
- diagram-maintenance/SKILL.md: add frontmatter
- rad/SKILL.md: fix zen-core → pal MCP server references

P2 context (1 file):
- python-standards.md: Black → Ruff formatter reference

Submodule:
- .submodules/image-generation: bump to commit with diagram-specialist
  frontmatter fix (fix/add-agent-frontmatter branch)

Tracking: docs/content-review.md (new file), docs/_data/tags.yml (add
content_review tag for review artifact docs) — P1: 6/6 reviewed,
P2: 52/52 reviewed (51 clean, 1 minor optional)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`eaf4e0b`](https://github.com/ByronWilliamsCPA/.claude/commit/eaf4e0b5475ed1f080641fb0a70d5f7fbe045b8a))
* fix(skills): add missing workflow bundles for security and quality skills

Both skills referenced workflow files that were never committed.
Sourced from image_detection downstream project (canonical copies).

- security/workflows/: validate-env.md, scan.md, encrypt.md
- quality/workflows/: format.md, lint.md, naming.md, precommit.md
- Fix path references in both SKILL.md files (add workflows/ prefix)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`0c1e30e`](https://github.com/ByronWilliamsCPA/.claude/commit/0c1e30e6c95971d697a8de2333d90ef4bf00e8c2))
* fix(skills): track testing skill bundle and correct gitignore scope

The .gitignore accidentally included .claude/skills/testing/ alongside the
eval workspace dirs, which prevented the skill&#39;s context/ and workflows/
companion files from ever being committed.

- Remove .claude/skills/testing/ from gitignore (keep testing-workspace/ and testing-variant-b/)
- Add testing/context/pytest-commands.md and pytest-patterns.md
- Add testing/workflows/ (generate, review, e2e, security, performance)
- Add testing/evals/ (evals.json and 4 source files)
- Fix testing/SKILL.md path references (workflows/ and context/ prefixes)

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`b90d85b`](https://github.com/ByronWilliamsCPA/.claude/commit/b90d85b1ed33cf92d72163e94ae5e110f21acea3))
* fix: resolve pre-commit failures across docs and skill scripts

- Extend darglint exclude to cover all .claude/skills/ scripts and noxfile.py
  (skill helper scripts are internal tooling, not library code)
- Fix front matter validation in 15 docs/ files: remove redundant body H1
  headings that duplicate the title: field, add missing schema_type: common
  where absent, fix invalid tags and add required planning fields
- Add engineering owner entry to docs/_data/owners.yml
- Add AGENTS-AND-SKILLS.md catalog and skills-lock.json
- Update CLAUDE.md and README.md agent/skill catalog tables

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`c067f42`](https://github.com/ByronWilliamsCPA/.claude/commit/c067f42b754367cb78d728b8ad7c2dd5ba2a5b33))
* fix(sonar): correct project keys, source paths, and MCP config

- Fix sonar.projectKey: `claude-config` → `ByronWilliamsCPA_.claude`
- Fix sonar.sources: `src` → `scripts` (src/ doesn&#39;t exist in this repo)
- Fix check_quality_gate.py default project key
- Fix interrogate pre-commit hook: `src/` → `scripts/`
- Switch MCP sonarqube server from Docker stdio to HTTP URL transport
  (Docker stdio has buffering issues with Java-based MCP servers)
- Add .sonarlint/connectedMode.json for VS Code Connected Mode sharing

Co-Authored-By: Claude Opus 4.6 (1M context) &lt;noreply@anthropic.com&gt; ([`2f7fe9e`](https://github.com/ByronWilliamsCPA/.claude/commit/2f7fe9eb5b2853560c4590b3b74be2aeea55a844))
* fix(mcp): correct zen-mcp-server command path

The zen MCP server configuration was pointing to a non-existent binary
`/home/byron/dev/zen-mcp-server/zen-mcp-server`. The zen-mcp-server is
a Python project that needs to be invoked with the Python interpreter.

Changed command to use `.pal_venv/bin/python server.py` which is the
correct entry point as documented in the project&#39;s config examples.

Also enabled project MCP servers in settings.json.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 &lt;noreply@anthropic.com&gt; ([`a84a94d`](https://github.com/ByronWilliamsCPA/.claude/commit/a84a94df7e2a6356207cfefaaa9e13c1b430ab34))
* fix(docs): correct commands directory path references in CLAUDE.md

The commands directory is located at `/.claude/commands/`, not `/commands/`.
Updated all references throughout CLAUDE.md to point to the correct path:
- Line 10: Token Optimized reference
- Line 148: Complete Command Reference
- Lines 152, 162, 172: Individual command references
- Line 723: Footer reference

This ensures Claude Code can correctly locate command documentation files
when reading the global standards.

Fixes path resolution issues where Claude would look for non-existent
`/commands/` directory instead of actual `/.claude/commands/` location.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`457a046`](https://github.com/ByronWilliamsCPA/.claude/commit/457a046713d390feb0954370aa5517ecbe73c585))
* fix: resolve pre-commit and CI/CD issues

- Fix trailing whitespace in 40+ files (auto-fixed by pre-commit)
- Fix missing newlines at end of files (auto-fixed by pre-commit)
- Add execute permissions to scripts with shebangs (.bats, .py files)
- Add proper shebang to .clusterfuzzlite/build.sh
- Fix D200: one-line docstring in financial.py
- Fix TC002/ARG001: move Processor import to TYPE_CHECKING and
  prefix unused callback args with underscore in logging.py
- Remove TestCLI tests that referenced non-existent cli module

All checks now pass:
- Pre-commit hooks: All pass
- Tests: 9 passed with 97.56% coverage
- Ruff linting: All checks passed
- BasedPyright: 0 errors, 3 warnings
- Bandit security scan: No issues ([`0446c81`](https://github.com/ByronWilliamsCPA/.claude/commit/0446c811a2b00c29293b365ac10cbc0894f8340b))
* fix(workflows): replace org-caller workflows with standalone implementations

- Remove .reuse/dep5 to fix conflict with REUSE.toml
- Replace ci.yml with standalone pytest, basedpyright, ruff, bandit
- Replace docs.yml with standalone MkDocs build and gh-deploy
- Replace release.yml with standalone semantic release workflow
- Replace scorecard.yml with standalone OpenSSF Scorecard (from homelab_infra)
- Replace security-analysis.yml with standalone Bandit and Safety scans

Fixes all 7 workflow failures caused by calling non-existent org-level
reusable workflows at ByronWilliamsCPA/.github/.github/workflows/.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`c9a86b4`](https://github.com/ByronWilliamsCPA/.claude/commit/c9a86b412da99c435776efd30a451d0eb1a47eb3))
### Refactor
* refactor: migrate commands to skills and align with Anthropic best practices

- Consolidate commit-prepare and pr-prepare into git skill bundle
  (git/workflows/commit.md, git/workflows/pr.md, git/context/)
  preserving all org-level requirements: HEREDOC pattern, attribution,
  safety rules, breaking change format, CodeRabbit integration
- Migrate all 7 commands to skills: quality, testing, security promoted
  in-place; debug-tests and handoff promoted to new bundled skills;
  pr and plan deleted as exact duplicates of existing skills
- Create .claude/rules/ with 5 path-scoped files: python.md,
  git-workflow.md, pre-commit.md, mcp-strategy.md, supervisor.md
- Trim CLAUDE.md from 866 to 196 lines; rules/ files carry the detail
- Add user-invocable: false to scope-analyzer and plan-validator agents
- Update sync instructions to include rules/ for downstream projects

Co-Authored-By: Claude Sonnet 4.6 &lt;noreply@anthropic.com&gt; ([`ebf3faa`](https://github.com/ByronWilliamsCPA/.claude/commit/ebf3faa31706c3ec02ecb2a7f86cfb0d7c200dc8))
* refactor: improve code quality across repository

- Fix Ruff linting errors in noxfile.py (use contextlib.suppress)
- Auto-format code with ruff format (7 files reformatted)
- Add MCP server configurations for Tier 2/3 on-demand loading
- Add environment variable template (.env.mcp.example)
- Update settings.json with Tier 1 MCP servers
- Configure playwright, postgres, sentry, docker, mermaid, uml MCP servers

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude &lt;noreply@anthropic.com&gt; ([`7da3442`](https://github.com/ByronWilliamsCPA/.claude/commit/7da344271e05feca57b88608be75afb8a69a39a2))
* refactor: improve code quality across repository

1. Fix scripts/check_quality_gate.py:
   - Replace Optional[str] with str | None (Python 3.10+ syntax)
   - Add noqa comments for S310 (URL scheme already validated)

2. Enhance src/claude_config/__init__.py:
   - Export Settings, get_logger, log_performance, setup_logging
   - Add docstring example showing common usage pattern
   - Sort __all__ alphabetically per RUF022

3. Reorganize tests into proper structure:
   - Move tests from test_example.py to unit/ and integration/
   - tests/unit/test_package.py - package initialization tests
   - tests/unit/test_settings.py - Settings class tests
   - tests/unit/test_logging.py - logging utilities tests
   - tests/integration/test_integration.py - integration tests
   - Add new test for public API exports

4. Fix documentation front matter:
   - Add missing tags to docs/_data/tags.yml (api, home, overview, etc.)
   - Remove redundant H1 headers from 15+ docs files
   - Add front matter to PROJECT-ORGANIZATION-GUIDE.md

All checks pass:
- Tests: 15 passed with 97.67% coverage
- Ruff linting: All checks passed
- BasedPyright: 0 errors ([`7e766d4`](https://github.com/ByronWilliamsCPA/.claude/commit/7e766d4b3a629d00121e9f4e920a6fff321318a2))
### Unknown
* Merge pull request #8 from ByronWilliamsCPA/feat/main-history-cleanup

chore: bring direct-to-main commits into PR history (author fix) ([`6229141`](https://github.com/ByronWilliamsCPA/.claude/commit/6229141e29e9ba2fbc9db8fa87d52dc22527d955))
* Merge pull request #5 from ByronWilliamsCPA/feat/add-anthropic-skill-submodules

feat: integrate upstream skill/plugin submodules with curated symlinks ([`491ce0e`](https://github.com/ByronWilliamsCPA/.claude/commit/491ce0e197288623c59afa0d20b12bbba1219a1a))
* Merge pull request #4 from ByronWilliamsCPA/chore/sync-submodule-pointers

chore: sync submodule pointers after submodule PRs merged ([`1eaedd0`](https://github.com/ByronWilliamsCPA/.claude/commit/1eaedd0d7781c8a82bbe248865a04df261c72ac3))
* Merge pull request #3 from ByronWilliamsCPA/chore/remove-ab-test-artifacts

chore: remove A/B test artifacts and clean up tracked tmp files ([`03e01dd`](https://github.com/ByronWilliamsCPA/.claude/commit/03e01ddedebdb84a4dba2d914cb5761ffe79c641))
* Merge pull request #2 from ByronWilliamsCPA/fix/p3-content-review-corrections

fix(content-review): complete full-repo content review sweep — 133 files across P1–P5 ([`1e7b6e8`](https://github.com/ByronWilliamsCPA/.claude/commit/1e7b6e8ad5f4e50bf6e05d4e0aaf98a1411d5bd4))
* Initial commit from cookiecutter template ([`a59414d`](https://github.com/ByronWilliamsCPA/.claude/commit/a59414d0d4d789cd450bd5f61038573c36de5d2c))
