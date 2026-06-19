# Agents and Skills Reference

Complete catalog of agents and skills in this org-level Claude Code configuration. Most live
directly in `.claude/agents/` and `.claude/skills/`. A subset is vendored from git submodules and
reaches those directories through symlinks.

## Local vs. vendored entries

14 agents, 19 skills, and 7 commands are symlinks into `.submodules/` (reference-library,
superpowers, anthropics-skills, anthropics-plugins, image-generation, jeffallan-claude-skills).
They include the entire writing pipeline (the seven reference-library agents: document-drafter,
grammar-composition-editor, document-validator, writing-style-editor, style-analyzer, tone-rewriter,
audience-reaction-analyzer), the superpowers skill set, the pr-review-toolkit agents, the
anthropics-skills document tools (docx, pdf, pptx, xlsx), and the hookify commands.

These symlinks dangle in any clone where the submodules have not been initialized, which includes
every fresh `git clone` and every Claude Code on the web session. In that state the entries below
are listed but not loadable. To populate them:

```bash
git submodule update --init --recursive
~/.claude/scripts/install-vendored-plugins.sh   # registers the plugin-backed entries
```

To list exactly which entries are vendored in the current checkout (drift-proof; reflects reality
rather than a hand-maintained tag list):

```bash
# Portable across GNU and BSD/macOS find (avoids the GNU-only -printf):
find ~/.claude/agents ~/.claude/skills -maxdepth 1 -type l \
  -exec sh -c 'for l; do printf "%s -> %s\n" "${l##*/}" "$(readlink "$l")"; done' _ {} +
```

If you need auto-population at session start instead of running the command manually, the
`session-start-hook` skill scaffolds a SessionStart hook for exactly this. It is left opt-in here
because submodule fetches can fail under restrictive network policies (a common web-session case),
and finding 3.4 in `docs/audits/config-quality-analysis-2026-06-12.md` proposes marketplace
packaging that removes the symlink fragility entirely.

---

## Agents

Agents are specialized subprocesses invoked via the `Agent` tool (`subagent_type="<name>"`). Each has
a focused role, curated tool access, and a system prompt calibrated for its domain.

### Code Quality & Review

**[code-reviewer](/.claude/agents/code-reviewer.md)**
Performs structured code reviews with MCP integration. Analyzes code for correctness, maintainability,
security issues, and adherence to project standards. Returns actionable feedback with severity ratings.

**[modularization-assistant](/.claude/agents/modularization-assistant.md)**
Breaks down monolithic code, configs, and documentation into maintainable components. Analyzes
architectural opportunities, generates phased execution plans, and validates that refactored modules
preserve existing behavior.

### PR Review Toolkit (vendored)

Six specialists from the `pr-review-toolkit` plugin, dispatched by `/pr-review`. They are symlinks
into `.submodules/anthropics-plugins/`, so they require submodule init to load (see the Local vs.
vendored note above). The catalog symlink `pr-toolkit-code-reviewer` points at the plugin's
`code-reviewer.md` to avoid colliding with the local `code-reviewer` agent.

**[pr-toolkit-code-reviewer](/.claude/agents/pr-toolkit-code-reviewer.md)**
Reviews recently changed code (typically the unstaged `git diff`) for adherence to project guidelines,
style guides, and CLAUDE.md patterns. Flags style violations and potential issues before commit or PR.

**[code-simplifier](/.claude/agents/code-simplifier.md)**
Simplifies recently modified code for clarity, consistency, and maintainability while preserving all
functionality. Follows project best practices and focuses only on the recent change set.

**[comment-analyzer](/.claude/agents/comment-analyzer.md)**
Analyzes code comments and docstrings for accuracy against the code they describe, completeness, and
comment-rot risk. Used after generating documentation or before finalizing a PR.

**[pr-test-analyzer](/.claude/agents/pr-test-analyzer.md)**
Reviews a PR for test coverage quality and completeness, identifying critical gaps in coverage of new
functionality and edge cases.

**[silent-failure-hunter](/.claude/agents/silent-failure-hunter.md)**
Hunts for silent failures, inadequate error handling, and inappropriate fallback behavior in catch
blocks and error paths within a change set.

**[type-design-analyzer](/.claude/agents/type-design-analyzer.md)**
Reviews type design for encapsulation and invariant expression, giving qualitative feedback plus
quantitative ratings on encapsulation, invariant expression, usefulness, and enforcement.

### Testing

**[test-engineer](/.claude/agents/test-engineer.md)**
Generates and reviews tests for Python projects. Handles unit, integration, property-based, and
mutation testing using pytest. Use for broad test generation and review tasks.

**[test-writer](/.claude/agents/test-writer.md)**
Coverage-driven iterative test generation. Runs coverage measurement, identifies uncovered functions
ranked by criticality, writes tests, and loops until targets are met.

**[test-reviewer](/.claude/agents/test-reviewer.md)**
Validates test quality and returns APPROVE or NEEDS_WORK with specific feedback. Checks for flaky
patterns, missing edge cases, poor assertions, and coverage of critical paths.

**[ui-testing-agent](/.claude/agents/ui-testing-agent.md)**
End-to-end UI testing specialist using Playwright. Writes and debugs browser automation tests,
validates accessibility (WCAG 2.1 AA), performs visual regression comparisons, and measures
Core Web Vitals.

### Security

**[security-auditor](/.claude/agents/security-auditor.md)**
Performs comprehensive security analysis including OWASP scanning, dependency vulnerability
assessment, secrets detection, and authentication/authorization review. Returns findings with
severity and remediation steps.

**[owasp-dispatch](/.claude/agents/owasp-dispatch.md)**
Routes security testing requests to one of six OWASP specialist agents based on the target type
(web app, API, LLM application, ML pipeline, citizen development, or agentic AI).

**[owasp-web](/.claude/agents/owasp-web.md)**
OWASP Top 10 specialist for web application security testing. Focuses on injection, broken auth,
XSS, IDOR, security misconfigurations, and client-side vulnerabilities.

**[owasp-api](/.claude/agents/owasp-api.md)**
OWASP API Security Top 10 specialist. Tests for broken object-level authorization, excessive data
exposure, lack of rate limiting, and mass assignment vulnerabilities.

**[owasp-llm](/.claude/agents/owasp-llm.md)**
OWASP LLM Top 10 specialist for AI-powered application security. Covers prompt injection, insecure
output handling, training data poisoning, and excessive agency risks.

**[owasp-ml](/.claude/agents/owasp-ml.md)**
ML pipeline security specialist. Analyzes data poisoning risks, model inversion, adversarial inputs,
and supply chain vulnerabilities in machine learning systems.

**[owasp-citizen](/.claude/agents/owasp-citizen.md)**
Security specialist for citizen development platforms (Power Platform, Zapier, Airtable). Reviews
data handling, access controls, and integration security in low-code/no-code environments.

**[owasp-agent](/.claude/agents/owasp-agent.md)**
Agentic AI security specialist. Reviews autonomous agent systems for privilege escalation,
uncontrolled recursion, insecure tool use, and insufficient human oversight.

### Planning & Architecture

**[phase-reviewer](/.claude/agents/phase-reviewer.md)**
Evaluates whether a development phase is ready to complete. Analyzes scope completion, runs quality
gates, and returns a PASS/FAIL with blocking issues and recommendations.

**[plan-validator](/.claude/agents/plan-validator.md)**
Reviews implementation plans for completeness, feasibility, and risk. Identifies missing steps,
incorrect assumptions, and architectural concerns before work begins.

**[plan-ceo-review](/.claude/agents/plan-ceo-review.md)**
Reviews a plan in founder/CEO mode: challenges whether it solves the right problem, the business
value, the do-nothing baseline, and whether scope matches value. Complements plan-validator
(completeness) with problem-framing. Adapted from the gstack concept (MIT).

**[plan-devex-review](/.claude/agents/plan-devex-review.md)**
Reviews a plan in developer-experience mode: challenges ergonomics, cognitive load, failure-mode
clarity, and maintainability of the interface it will produce. Complements plan-validator and
plan-ceo-review. Adapted from the gstack concept (MIT).

**[scope-analyzer](/.claude/agents/scope-analyzer.md)**
Analyzes how much of a defined scope has been completed. Compares planned deliverables against
actual implementation and reports completion percentages with gap analysis.

**[project-plan-synthesizer](/.claude/agents/project-plan-synthesizer.md)**
Synthesizes the four initial planning documents (PVS, ADR, Tech Spec, Roadmap) into a comprehensive
`docs/planning/PROJECT-PLAN.md` with semantic release-aligned phase branches, quality gates per
phase, and a Phase 0 TodoWrite checklist. Invoke after `/project-planning` generates source docs
and before Phase 1 development begins. Uses the `/consensus` skill for expert validation.

### API & Backend Development

**[api-development-agent](/.claude/agents/api-development-agent.md)**
Designs REST and GraphQL APIs, creates OpenAPI/Swagger specifications, implements contract testing
with Pact or Schemathesis, and generates interactive API documentation with code examples.

**[database-operations-agent](/.claude/agents/database-operations-agent.md)**
Handles schema design, migrations (Alembic, Flyway), query optimization, execution plan analysis,
and data integrity validation. Produces safe migrations with rollback plans.

**[openapi-compliance-agent](/.claude/agents/openapi-compliance-agent.md)**
Orchestrates the full OpenAPI compliance pipeline for API-serving repos. Dispatches
openapi-code-enricher, api-development-agent, postman-test-designer, and
github-workflow-agent sequentially per repo; runs repos in parallel for /openapi-audit
all. Updates the repo catalog on success.

**[openapi-code-enricher](/.claude/agents/openapi-code-enricher.md)**
Patches FastAPI route files for full OpenAPI coverage. Adds app-level metadata to
FastAPI() constructors, enriches route decorators (summary, tags, responses,
status_code, response_model), and creates Pydantic models for untyped request bodies.
Does not touch business logic or authentication code.

**[postman-test-designer](/.claude/agents/postman-test-designer.md)**
Injects pre-request scripts and test assertions into Postman collections, runs newman
on docker-host to validate the API, writes .github/workflows/postman-api-tests.yml,
and returns a pass/fail status to the orchestrator.

### AI & ML Engineering

**[ai-engineer](/.claude/agents/ai-engineer.md)**
Builds LLM applications and RAG systems using the C.R.E.A.T.E. framework (Context, Request,
Examples, Augmentations, Tone & Format, Evaluation). Integrates vector databases (Qdrant, Pinecone,
pgvector) and designs multi-agent orchestration workflows.

### DevOps & Infrastructure

**[devops-deployment-agent](/.claude/agents/devops-deployment-agent.md)**
Manages CI/CD pipelines (GitHub Actions, GitLab CI), deployment strategies (blue-green, canary),
Infrastructure as Code (Terraform, Pulumi, Ansible), and monitoring/alerting configuration.

### Git & GitHub

**[git-workflow-agent](/.claude/agents/git-workflow-agent.md)**
Manages git repository workflows including branch strategy, conventional commit enforcement,
changelog generation, semantic versioning, release coordination, and repository health maintenance.

**[github-workflow-agent](/.claude/agents/github-workflow-agent.md)**
GitHub platform specialist for PR management, issue tracking, GitHub Actions CI/CD, branch
protection rules, CODEOWNERS, and project board administration via the `gh` CLI.

### Compliance & Standards Auditing

**[repo-foundations-auditor](/.claude/agents/repo-foundations-auditor.md)**
Compliance auditor and remediator for repository foundation files. Checks OpenSSF required files
(SECURITY.md, CONTRIBUTING.md, CHANGELOG.md), CODEOWNERS, .gitignore entries, pyproject.toml
metadata, and docs structure against the standards manifest. Returns structured findings in audit
mode; creates or patches files in remediation mode.

**[python-toolchain-auditor](/.claude/agents/python-toolchain-auditor.md)**
Compliance auditor and remediator for Python project toolchain configuration. Checks dev dependency
presence and absence (ruff, basedpyright, pip-audit, pydoclint, interrogate), Ruff rule set
completeness against PyStrict-aligned codes, BasedPyright config, qlty setup, and pyproject.toml
settings against the standards manifest.

**[pre-commit-auditor](/.claude/agents/pre-commit-auditor.md)**
Compliance auditor and remediator for `.pre-commit-config.yaml`. Checks hook presence against the
required list (ruff, basedpyright, bandit, detect-secrets, pydoclint, interrogate, commitizen,
yamllint, markdownlint, no-em-dash) and validates all rev fields are SHA-pinned.

**[claude-docs-auditor](/.claude/agents/claude-docs-auditor.md)**
Compliance auditor and remediator for Claude configuration and project documentation. Checks
CLAUDE.md section presence, `.claude/settings.json`, AGENTS.md/GEMINI.md file locations, and
writing quality. Delegates em-dash and AI pattern scanning to `writing-style-editor`.

**[ossf-compliance-auditor](/.claude/agents/ossf-compliance-auditor.md)**
Audits a repository's OpenSSF Best Practices Badge (Passing level) and Security Scorecard (4+ on
all 20 checks) compliance. Queries the live Scorecard REST API and Best Practices Badge API for
current results, falls back to the SARIF artifact from the scorecard.yml workflow run, and
supplements with GitHub API checks (branch protection, signed release assets, private vulnerability
reporting) and local file checks (SECURITY.md content, CHANGELOG CVE patterns, dependabot config,
fuzzing targets). Every FINDING includes specific, executable remediation steps drawn from embedded
knowledge of each check's requirements.

**[ossf-badge-evaluator](/.claude/agents/ossf-badge-evaluator.md)**
Evaluates a repository against OpenSSF Best Practices Badge criteria (passing, silver, or gold) and
produces a criterion-by-criterion assessment for form submission. For each criterion it inspects the
local repo, returns the recommended radio button selection (Met/Unmet/N/A/?) with confidence level,
generates ready-to-paste justification text, lists supporting evidence, and flags required actions.
Generates three automation URLs (passing/silver/gold) so all Met/N/A answers for each badge level
can be pre-loaded into the submission form in one click. Use before filling out or updating a Best Practices Badge submission.

**[general-compliance-auditor](/.claude/agents/general-compliance-auditor.md)**
Freeform compliance auditor for gaps outside the standards manifest. Receives covered check IDs as
a negative filter, performs a broad LLM review against global standards, and returns unclassified
candidates for retrospective pattern analysis. Audit mode only.

**[compliance-retrospective](/.claude/agents/compliance-retrospective.md)**
Post-run retrospective agent. Synthesizes findings across all repos in a session, detects patterns
in unclassified candidates, and writes a lessons-learned document with ready-to-paste manifest
improvement proposals and agent scope expansion candidates.

**[compliance-synthesis](/.claude/agents/compliance-synthesis.md)**
Cross-session compliance retrospective synthesis. Reads the central master log, computes trending
recurrence, stuck manifest candidates, fleet-action follow-through, coverage gaps, and override
hotspots. Writes a weekly synthesis report to `docs/compliance-reports/synthesis/YYYY-MM-DD.md`.

**[cleanup-backlog-scout](/.claude/agents/cleanup-backlog-scout.md)**
Scouts target repositories for mechanical cleanup work a local model can perform autonomously. Reads
a repo (or the fleet catalog), identifies safe candidates (doc fixes, missing OpenSSF baseline files,
frontmatter additions, dependency bumps, ruff-flagged dead code, link fixes), classifies each by
difficulty against the worker contract's five gates, and writes scoped task entries to the cleanup
backlog. Conservative by default: marks candidates claude-required when classification is uncertain.

**[ossf-criteria-reference](/.claude/standards/ossf-criteria-reference.md)**
Reference knowledge file (not an executable agent; lives in `.claude/standards/`). Catalogs every
OpenSSF Best Practices Badge criterion slug, N/A eligibility, and automation URL field name across
the passing, silver, and gold levels. Consumed by `ossf-badge-evaluator` when generating
form-submission automation URLs.

### Frontend

**[frontend-designer](/.claude/agents/frontend-designer.md)**
Expert frontend designer for distinctive, production-grade UI/UX. Covers creative direction,
accessible component design, React performance patterns, and anti-generic-AI aesthetics. Supports
build, review, a11y audit, and performance optimization modes.

### Documentation & Research

**[documentation-writer](/.claude/agents/documentation-writer.md)**
Creates comprehensive technical documentation following the pyramid structure (overview → user guides
→ reference → advanced topics). Handles API docs, architecture guides, information architecture
design, and documentation lifecycle management.

**[research-agent](/.claude/agents/research-agent.md)**
Performs multi-source technical research with source verification and synthesis. Specializes in
library/framework evaluation, technology comparison, and official documentation analysis with
actionable recommendations.

### Writing & Content

**[ai-detection-agent](/.claude/agents/ai-detection-agent.md)**
AI content detection specialist with two modes: (1) evaluate submitted files and text for
probabilistic AI-generation analysis using the self-hosted `ai-text-detector` stack
(Binoculars, Fast-DetectGPT, MAGE, RADAR, Ghostbuster, and more) plus Sapling and Winston AI;
Pangram is opt-in and used only when explicitly requested; (2) audit writing pipeline outputs
to identify detection vulnerabilities and recommend targeted revisions to reference library
prompts and templates. Cross-references findings against
`.claude/standards/ai-detection-landscape.md`.

**[document-drafter](/.claude/agents/document-drafter.md)**
Pre-pipeline generative agent. Produces first drafts calibrated to the author's voice from outlines,
bullet points, or contextual prompts. Outputs feed directly into the three-stage editing pipeline.

**[grammar-composition-editor](/.claude/agents/grammar-composition-editor.md)**
Mechanical correctness review agent. Checks grammar, composition, plain language, and AI-mechanical
patterns. Stage 1 of the three-agent writing quality pipeline.

**[document-validator](/.claude/agents/document-validator.md)**
Deep factual review agent that verifies claims, identifies assumptions, detects hallucinations,
checks for bias, and flags reasoning errors. Stage 2 of the three-agent writing quality pipeline.

**[writing-style-editor](/.claude/agents/writing-style-editor.md)**
Persona fidelity and AI pattern detection agent. Ensures documents sound like the author wrote them,
not AI-generated boilerplate. Stage 3 of the three-agent writing quality pipeline.

**[tone-rewriter](/.claude/agents/tone-rewriter.md)**
Pre-pipeline generative agent. Rewrites a document for a different audience or register while
preserving factual content. Transforms vocabulary, sentence complexity, structure, and formality.

**[style-analyzer](/.claude/agents/style-analyzer.md)**
Analyzes writing samples to build a personalized style profile. Generates recommended updates to
style-profile.md and the pipeline agents so they calibrate to the user's voice.

**[audience-reaction-analyzer](/.claude/agents/audience-reaction-analyzer.md)**
Post-pipeline analysis agent. Reads a finished document from the perspective of a target audience
and predicts how they will interpret, react to, and act on the content. Identifies gaps in
persuasion, comprehension, and accessibility.

### Diagrams & Visuals

**[diagram-maintenance-agent](/.claude/agents/diagram-maintenance-agent.md)**
PlantUML diagram maintenance specialist for architecture documentation, source traceability,
consistency enforcement, and AI visual generation across any project.

**[diagram-specialist](/.claude/agents/diagram-specialist.md)**
Specialized agent for creating and validating technical diagrams (PlantUML, Mermaid) for network
engineering and infrastructure documentation.

**[visual-content-generator](/.claude/agents/visual-content-generator.md)**
Generates professional visual content (diagrams, blueprints, illustrations) for business documents.
Analyzes target documents, identifies visual needs, prepares optimized prompts, and manages
iterative refinement workflows.

### MkDocs

**[mkdocs-auditor](/.claude/agents/mkdocs-auditor.md)**
MkDocs configuration lifecycle agent for any project. Audits `mkdocs.yml` for required
metadata fields, extension bloat, feature conflicts, version pinning, and docs CI coverage.
Remediates violations in place, scaffolds a compliant `mkdocs.yml` from scratch, and
detects nav and content gaps post-sprint with a structured handoff to `mkdocs-specialist`.
Invoke in audit mode via repo-compliance, or standalone for create, remediate, and update modes.

**[mkdocs-specialist](/.claude/agents/mkdocs-specialist.md)**
MkDocs page content creation and style enforcement agent. Authors missing or stale docs
pages to a consistent Material theme standard: required frontmatter, purpose admonition,
heading hierarchy, semantic admonition usage, and OS-agnostic shell commands. Invoked
after `mkdocs-auditor` surfaces content gaps via update mode, or standalone for
content review and page authoring.

---

## Skills

Skills are prompt-based workflows invoked with `/skill-name`. They activate automatically on
keywords or can be called explicitly. Skills route to sub-workflows based on user intent.

### Development Workflow

**[/git](/.claude/skills/git/SKILL.md)**
Git workflow automation including branch creation/validation, commit message preparation, PR
preparation, PR validation checklist, and branch strategy guidance. Activates on git-related
keywords.

**[/phase-gate](/.claude/skills/phase-gate/SKILL.md)**
Evaluates phase readiness by analyzing scope completion and running quality gates. Use when
transitioning between implementation phases or checking whether a phase is ready for completion.

**[/task-observer](/.claude/skills/task-observer/SKILL.md)**
Session observation skill that records behavioral patterns and tool use during task execution,
synthesizes cross-cutting insights, and logs observations for autonomous scheduled review.
Surfaces relevant past observations when loading other skills. Invoke at the start of any
task-oriented session (any session where you will use tools and produce deliverables).

**[/usage-report](/.claude/skills/usage-report/SKILL.md)**
Summarizes model and token usage from local Claude Code transcripts via ccusage: per-project
daily review, monthly trends, per-session detail, and the active five-hour block with burn
rate (the `/loop` cost circuit breaker). An `agents` mode queries the agents-observe local
API for per-subagent token attribution via the agents-observe plugin (Layer 3). Works on a
Max subscription; costs are API-list-price estimates. Activates on: "usage report", "token
usage", "model spend", "five-hour block", "agents mode", "per-agent usage", "subagent
tokens", "agent attribution".

**[/aggregate-observations](/.claude/commands/aggregate-observations.md)** _(recovery utility)_
Scans all repositories under `~/dev/` for stray `skill-observations/log.md` files and walks
the user through importing OPEN observations into the canonical global log at
`~/.claude/skill-observations/log.md`. Use after recovering from a misconfigured task-observer
session that wrote observations to a project-local path instead of the global log.

### Code Quality

**[/quality](/.claude/skills/quality/SKILL.md)**
Runs code quality checks: ruff formatting, ruff linting with auto-fix, BasedPyright type checking,
markdownlint, and yamllint. Activates on: "quality check", "lint", "format code".

**[/rad](/.claude/skills/rad/SKILL.md)**
Response-Aware Development: systematic assumption tagging and multi-model verification. Tags
`#CRITICAL`, `#ASSUME`, and `#EDGE` assumptions in code and routes them to appropriate AI models
for verification. Sub-workflows: verify, list, test. Activates on: "assumption", "RAD", "verify
assumptions".

**[/pre-commit-authoring](/.claude/skills/pre-commit-authoring/SKILL.md)**
Reference for designing, adding, and auditing pre-commit hooks. Covers the staged-scope invariant
(PC-HOOK-STAGED-SCOPE), fast/slow tier placement, fail-vs-warn semantics, and a common-gotchas
list including the TruffleHog `--since-commit HEAD` trap. Includes an audit pattern for existing
`.pre-commit-config.yaml` files. Activates on: "/pre-commit-authoring", "add a hook", "write a
pre-commit hook", "audit pre-commit", "fix pre-commit hook", "hook false positive".

### Testing

**[/testing](/.claude/skills/testing/SKILL.md)**
Test generation, review, and execution for pytest projects. Covers unit, integration, e2e, security,
and performance testing patterns. Activates on: "run tests", "test suite", "write tests".

**[/test-coverage](/.claude/skills/test-coverage/SKILL.md)**
Analyzes coverage gaps, generates missing tests ranked by criticality, and enforces coverage
thresholds (80% line / 70% branch / 90% critical / 90% patch). Orchestrates test-writer and
test-reviewer agents iteratively. Activates on: "coverage analysis", "coverage gaps".

**[/consensus](/.claude/skills/consensus/SKILL.md)**
Multi-model consensus via OpenRouter with two modes: a tiered IT review team
(levels 1-3, professional roles per domain) and fully flexible model/stance
selection. Bundles a uv-run engine script for parallel fan-out, band-based
roster selection with live catalog validation, failover, and per-level cost
caps; Claude synthesizes the raw responses. Replaces the zen/pal MCP
consensus tools. Activates on: "consensus", "tiered consensus", "tiered
review", "second opinion", "multi-model review", "ask other models",
"review team", "model roster".

**[/debug-tests](/.claude/skills/debug-tests/SKILL.md)**
Root-cause-first analysis of failing tests. Investigates fixtures, environment mismatches,
dependency drift, and test isolation before modifying assertions or application code.

### Security

**[/security](/.claude/skills/security/SKILL.md)**
Security validation including GPG/SSH key checks, bandit static analysis, safety dependency
scanning, and environment variable validation. Activates on: "security check", "scan", "security".

### Planning & Documentation

**[/premise-interrogation](/.claude/skills/premise-interrogation/SKILL.md)**
Pre-spec gate that interrogates demand and scope before any spec or plan is written: challenges
whether the thing should be built at all, who the user is, the real problem, and the cheapest test
of the premise, then hands off to brainstorming. Adapted from the gstack `/office-hours`, mattpocock
`grill-me`, and addyosmani `interview-me` concepts (MIT). Activates on: "challenge the premise",
"should we build this", "is this the real problem", "grill me".

**[/domain-modeling](/.claude/skills/domain-modeling/SKILL.md)**
Maintains a living, folder-scoped domain glossary and challenges terminology drift to enforce
ubiquitous language; surfaces synonym/homonym conflicts instead of silently coining a new term.
Adapted from the mattpocock concept (MIT). Activates on: "domain modeling", "glossary",
"ubiquitous language", "terminology drift".

**[/issue-generation](/.claude/skills/issue-generation/SKILL.md)**
Converts a conversation into a scoped GitHub issue through a capture, redact, confirm, file workflow
with a mandatory PII/secret redaction gate before anything is created. Adapted from the gstack
`/spec` and mattpocock `to-issues` concepts (MIT). Activates on: "file an issue", "turn this into an
issue", "issue from conversation".

**[/project-planning](/.claude/skills/project-planning/SKILL.md)**
Generates project planning documents: Product Vision Statement (PVS), Architecture Decision Records
(ADRs), Technical Specification, and Roadmap. Activates on: "project plan", "generate plan",
"new project".

**[/tool-eval](/.claude/skills/tool-eval/SKILL.md)**
Evaluates an external tool or repo against our `~/.claude` setup and produces a decision: SUBMODULE,
PORT PATTERNS, RUN STANDALONE ALONGSIDE, or IGNORE. Walks eight gates (characterize, LOC map,
coupling boundary, licence carve-outs, relationship classification, gap mapping, delivery-model fit,
convergent validation) and writes a decision doc to `docs/tool-evals/<tool-slug>.md`. Activates on:
"compare X to our setup", "should we adopt/vendor/submodule X", "cherry-pick from X".

### AI & ML Engineering

**[/meta-harness](/.claude/skills/meta-harness/SKILL.md)**
Runs a Meta-Harness-style optimization loop natively: searches over the scaffolding around a
fixed base model (memory, retrieval, context assembly, prompt templates, summarization) by
proposing candidate variants, scoring each on a cheap deterministic eval, and keeping a Pareto
frontier of quality vs cost, using native Agent / Workflow / loop tools instead of a standalone
Python harness. Vendored from 001TMF/harness-forge (MIT); see
`docs/tool-evals/harness-forge.md` for the adoption rationale and MTG_AI pilot trigger. Activates
on: "Meta-Harness", "harness optimization", "scaffold evolution", "optimize the harness without
retraining", "Pareto search over candidates".

### Production Operations

Ported from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT,
commit `a5f0b17`) and adapted to our standards. These cover the production-ops lifecycle
that the superpowers/anthropics skill sets do not.

**[/observability-and-instrumentation](/.claude/skills/observability-and-instrumentation/SKILL.md)**
Instruments code so production behavior is visible: structured logging, RED/USE metrics,
correlation IDs, cardinality discipline, distributed tracing, and symptom-based alerting.
Activates on: "logging", "metrics", "tracing", "alerting", "telemetry", "observability".

**[/deprecation-and-migration](/.claude/skills/deprecation-and-migration/SKILL.md)**
Removes code that no longer earns its keep and migrates users safely: the deprecation
decision, strangler/adapter/feature-flag patterns, the Churn Rule, and zombie-code
handling. Activates on: "deprecate", "migration", "sunset", "remove old system".

**[/performance-optimization](/.claude/skills/performance-optimization/SKILL.md)**
Measure-first performance work: Core Web Vitals targets, the measure/identify/fix/verify
loop, N+1 and bundle-size anti-patterns, and enforced performance budgets. Activates on:
"performance", "optimize", "slow", "Core Web Vitals", "N+1", "bundle size".

**[/shipping-and-launch](/.claude/skills/shipping-and-launch/SKILL.md)**
Safe production launches: pre-launch checklist, feature-flag lifecycle, staged/canary
rollout with decision thresholds, post-launch verification loop, and rollback strategy.
Activates on: "ship", "launch", "deploy", "rollout", "canary", "rollback".

**[/source-driven-development](/.claude/skills/source-driven-development/SKILL.md)**
Grounds framework-specific code in official documentation (context7 preferred for
retrieval): detect versions, fetch authoritative docs, implement, and cite sources.
Activates on: "cite docs", "official documentation", "verify API", "current best practices".

### Reasoning & Quality

Ported from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT,
commit `a5f0b17`) and adapted to our standards. Tier 2 reasoning enhancements that
complement RAD and our review pipeline.

**[/doubt-driven-development](/.claude/skills/doubt-driven-development/SKILL.md)**
Subjects every non-trivial decision to a fresh-context adversarial review before it
stands: name the CLAIM, extract artifact + contract, spawn an issues-only reviewer
(cross-model via the `consensus` skill or `clink` when authorized), reconcile, and stop
on a bounded condition. The active complement to RAD's assumption tagging. Activates on:
"adversarial review", "fresh-context review", "disprove this", "doubt-driven".

**[/context-engineering](/.claude/skills/context-engineering/SKILL.md)**
Curates what the agent sees and when: the five-tier context hierarchy (rules files,
specs, source, errors, history), trust levels for loaded files, confusion management,
and the inline-planning pattern. Repointed to our scoped CLAUDE.md and tiered MCP
loading. Activates on: "context engineering", "new session setup", "output quality
degrading", "rules file".

### Frontend

**[/frontend-design](/.claude/skills/frontend-design/SKILL.md)**
Creates distinctive, production-grade frontend interfaces with high design quality. Covers creative
direction, accessible components, React performance patterns, and anti-generic-AI aesthetics.
Activates on: "build UI", "create component", "design page".

### Infrastructure & Diagrams

**[/diagram-maintenance](/.claude/skills/diagram-maintenance/SKILL.md)**
Maintains PlantUML architecture diagrams, ensures traceability with source files, manages SVG
generation, and enforces consistency across diagram hierarchies. Activates on: "update diagram",
"PUML", "diagram audit".

### Code Review & Quality Gates

**[/sonarcloud](/.claude/skills/sonarcloud/SKILL.md)**
Reviews, triages, and fixes SonarCloud issues via the SonarQube MCP server. Auto-detects project
org and key. Supports issue search, quality gate checks, rule lookup, and automated fixing.
Activates on: "sonar", "quality gate", "sonar issues".

**[/repo-audit](/.claude/skills/repo-compliance/SKILL.md)**
Repo compliance coordinator. Audits any repository against the standards manifest, presents
findings grouped by severity, applies approved remediations, opens a PR, and runs the
retrospective. Interactive mode for single-repo work; scheduled mode for org-wide sweeps.

**[/skill-creator](/.claude/skills/skill-creator)**
Creates new skills, modifies existing ones, runs evals, and benchmarks skill performance. Use when
you want to add a new skill or improve an existing one.

### Writing

**[/writing](/.claude/skills/writing/SKILL.md)**
Orchestrates the seven-agent reference library writing pipeline. Handles document editing,
drafting from outlines, register transformation for different audiences, audience readiness
analysis, and style profile calibration. Modes: `edit` (Stage 1→2→3), `draft` (drafter→pipeline),
`rewrite` (tone-rewriter→pipeline), `analyze` (audience-reaction-analyzer), `calibrate`
(style-analyzer). Activates on: "edit this document", "improve this draft", "draft a memo",
"rewrite for [audience]", "check my writing", "style review", "grammar check", "does this sound
like me", "writing pipeline", "AI patterns", "will this land".

---

## Superpowers Skills (Community-Maintained)

Superpowers skills are sourced from [obra/superpowers](https://github.com/obra/superpowers) via
`.submodules/superpowers` and symlinked into `.claude/skills/`. They are community-maintained and
auto-injected at session start via the `using-superpowers` meta-skill. Update with:
`git submodule update --remote --merge`

### Design & Planning

**[brainstorming](/.submodules/superpowers/skills/brainstorming/SKILL.md)**
Socratic pre-implementation design workflow. Explores context, asks one clarifying question at a
time, proposes 2-3 architectural approaches, generates a spec document, and chains to
`writing-plans`. Hard rule: no code until design is approved.

**[writing-plans](.claude/skills/writing-plans/SKILL.md)**
Creates granular task-by-task implementation plans. Each task targets 2-5 minutes, follows TDD,
includes exact file paths and complete code blocks. Plan is saved to
`docs/superpowers/plans/` and committed before implementation begins.

### Execution

**[executing-plans](/.submodules/superpowers/skills/executing-plans/SKILL.md)**
Loads a written plan, creates a TodoWrite task list, and executes tasks sequentially. Stops
immediately on blockers and chains to `finishing-a-development-branch` on completion.

**[subagent-driven-development](/.submodules/superpowers/skills/subagent-driven-development/SKILL.md)**
Three-subagent review pattern per task: (1) Implementer executes and self-reviews, (2) Spec-compliance
reviewer independently verifies against spec with adversarial skepticism, (3) Code-quality reviewer
validates cleanliness. Never skips review loops.

**[dispatching-parallel-agents](.claude/skills/dispatching-parallel-agents/SKILL.md)**
Assigns independent tasks to parallel subagents when 3+ independent problems exist simultaneously.
One agent per independent problem domain.

### Code Review

**[requesting-code-review](/.submodules/superpowers/skills/requesting-code-review/SKILL.md)**
Dispatches the `code-reviewer` subagent with structured context: what was implemented, plan
reference, base SHA, head SHA. Mandates addressing Critical issues immediately.

**[receiving-code-review](.claude/skills/receiving-code-review/SKILL.md)**
Enforces technical verification before acting on any review feedback. Five verification checks per
suggestion. Explicitly prohibits performative agreement. Permits pushback when reviewer is incorrect
or has insufficient context.

### Testing & Quality

**[test-driven-development](.claude/skills/test-driven-development/SKILL.md)**
Enforces red-green-refactor discipline. Iron Law: no production code without a failing test first.
Any pre-existing production code must be deleted and re-implemented test-first.

**[verification-before-completion](/.submodules/superpowers/skills/verification-before-completion/SKILL.md)**
Universal evidence gate. No completion claim without running verification commands and reading their
output. Prevents optimistic "it should work" declarations.

### Debugging

**[systematic-debugging](/.submodules/superpowers/skills/systematic-debugging/SKILL.md)**
Four-phase framework: root cause investigation → pattern analysis → hypothesis testing →
implementation. No fixes without root cause first. Escalates to architectural review after 3 failed
fixes.

### Git Workflow

**[using-git-worktrees](.claude/skills/using-git-worktrees/SKILL.md)**
Safe worktree setup: detects correct directory, verifies worktree is git-ignored, installs
dependencies, and runs baseline tests before any work begins.

**[finishing-a-development-branch](/.submodules/superpowers/skills/finishing-a-development-branch/SKILL.md)**
Branch completion workflow presenting four options: merge locally / create PR / keep branch / discard
work. Runs full test suite first. Cleans up worktrees only for merge and discard. Requires typed
confirmation before discarding.

### Skill Development

**[writing-skills](/.submodules/superpowers/skills/writing-skills/SKILL.md)**
TDD-based skill authorship. RED phase: establish baseline failures without the skill. GREEN phase:
write minimal documentation to address failures. REFACTOR phase: close loopholes. YAML frontmatter
required; description must start with "Use when...".

### Meta

**[using-superpowers](/.submodules/superpowers/skills/using-superpowers/SKILL.md)**
Meta-skill injected at session start via the SessionStart hook. Instructs Claude to invoke relevant
skills before any response or action. Priority: explicit user instructions > superpowers skills >
default system prompt.

---

## Quick Reference: When to Use What

| Need | Use |
| ---- | --- |
| Review code before merging | `code-reviewer` agent or `requesting-code-review` skill |
| Write missing tests | `test-writer` agent or `/test-coverage` skill |
| Security scan a PR | `security-auditor` agent or `/security` skill |
| Design a REST API | `api-development-agent` |
| Set up CI/CD | `devops-deployment-agent` |
| Research a library/framework | `research-agent` |
| Build LLM/RAG feature | `ai-engineer` |
| Refactor large file | `modularization-assistant` |
| Verify code assumptions | `/rad` skill |
| Plan a new project | `/project-planning` skill → `project-plan-synthesizer` agent |
| Design before coding | `brainstorming` skill |
| Write an implementation plan | `writing-plans` skill |
| Execute a written plan | `executing-plans` skill |
| Implement with review loop | `subagent-driven-development` skill |
| Debug any issue | `systematic-debugging` skill |
| Debug failing tests | `/debug-tests` skill |
| Prepare a PR | `/git` skill or `finishing-a-development-branch` skill |
| Set up isolated branch | `using-git-worktrees` skill |
| Edit a document / run writing pipeline | `/writing` skill |
| Draft from outline or bullets | `/writing draft` |
| Rewrite for a different audience | `/writing rewrite` |
| Check if document will land with its audience | `/writing analyze` |
| Audit a repo for compliance | `/repo-audit` skill |
| Check OSSF Best Practices Badge / Scorecard status | `ossf-compliance-auditor` agent (called by `/repo-audit`) |
| Fill out or update OSSF Best Practices Badge submission | `ossf-badge-evaluator` agent |
| Audit or scaffold `mkdocs.yml`, detect nav gaps | `mkdocs-auditor` agent |
| Author missing MkDocs pages or review page content | `mkdocs-specialist` agent |
| Check phase readiness | `/phase-gate` skill or `phase-reviewer` agent |
| Respond to a code review | `receiving-code-review` skill |
| Confirm work is done | `verification-before-completion` skill |
