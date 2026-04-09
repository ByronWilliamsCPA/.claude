# Agents and Skills Reference

Complete catalog of available agents and skills in this org-level Claude Code configuration.
All resources are available in `.claude/agents/` and `.claude/skills/`.

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

**[scope-analyzer](/.claude/agents/scope-analyzer.md)**
Analyzes how much of a defined scope has been completed. Compares planned deliverables against
actual implementation and reports completion percentages with gap analysis.

**[project-plan-synthesizer](/.claude/agents/project-plan-synthesizer.md)**
Synthesizes the four initial planning documents (PVS, ADR, Tech Spec, Roadmap) into a comprehensive
`docs/planning/PROJECT-PLAN.md` with semantic release-aligned phase branches, quality gates per
phase, and a Phase 0 TodoWrite checklist. Invoke after `/project-planning` generates source docs
and before Phase 1 development begins. Uses zen-mcp consensus for expert validation.

### API & Backend Development

**[api-development-agent](/.claude/agents/api-development-agent.md)**
Designs REST and GraphQL APIs, creates OpenAPI/Swagger specifications, implements contract testing
with Pact or Schemathesis, and generates interactive API documentation with code examples.

**[database-operations-agent](/.claude/agents/database-operations-agent.md)**
Handles schema design, migrations (Alembic, Flyway), query optimization, execution plan analysis,
and data integrity validation. Produces safe migrations with rollback plans.

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

### Code Quality

**[/quality](/.claude/skills/quality/SKILL.md)**
Runs code quality checks: ruff formatting, ruff linting with auto-fix, BasedPyright type checking,
markdownlint, and yamllint. Activates on: "quality check", "lint", "format code".

**[/rad](/.claude/skills/rad/SKILL.md)**
Response-Aware Development — systematic assumption tagging and multi-model verification. Tags
`#CRITICAL`, `#ASSUME`, and `#EDGE` assumptions in code and routes them to appropriate AI models
for verification. Sub-workflows: verify, list, test. Activates on: "assumption", "RAD", "verify
assumptions".

### Testing

**[/testing](/.claude/skills/testing/SKILL.md)**
Test generation, review, and execution for pytest projects. Covers unit, integration, e2e, security,
and performance testing patterns. Activates on: "run tests", "test suite", "write tests".

**[/test-coverage](/.claude/skills/test-coverage/SKILL.md)**
Analyzes coverage gaps, generates missing tests ranked by criticality, and enforces coverage
thresholds (80% line / 70% branch / 90% critical / 90% patch). Orchestrates test-writer and
test-reviewer agents iteratively. Activates on: "coverage analysis", "coverage gaps".

**[/debug-tests](/.claude/skills/debug-tests/SKILL.md)**
Root-cause-first analysis of failing tests. Investigates fixtures, environment mismatches,
dependency drift, and test isolation before modifying assertions or application code.

### Security

**[/security](/.claude/skills/security/SKILL.md)**
Security validation including GPG/SSH key checks, bandit static analysis, safety dependency
scanning, and environment variable validation. Activates on: "security check", "scan", "security".

### Planning & Documentation

**[/project-planning](/.claude/skills/project-planning/SKILL.md)**
Generates project planning documents: Product Vision Statement (PVS), Architecture Decision Records
(ADRs), Technical Specification, and Roadmap. Activates on: "project plan", "generate plan",
"new project".

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

**[writing-plans](/.submodules/superpowers/skills/writing-plans/SKILL.md)**
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

**[dispatching-parallel-agents](/.submodules/superpowers/skills/dispatching-parallel-agents/SKILL.md)**
Assigns independent tasks to parallel subagents when 3+ independent problems exist simultaneously.
One agent per independent problem domain.

### Code Review

**[requesting-code-review](/.submodules/superpowers/skills/requesting-code-review/SKILL.md)**
Dispatches the `code-reviewer` subagent with structured context: what was implemented, plan
reference, base SHA, head SHA. Mandates addressing Critical issues immediately.

**[receiving-code-review](/.submodules/superpowers/skills/receiving-code-review/SKILL.md)**
Enforces technical verification before acting on any review feedback. Five verification checks per
suggestion. Explicitly prohibits performative agreement. Permits pushback when reviewer is incorrect
or has insufficient context.

### Testing & Quality

**[test-driven-development](/.submodules/superpowers/skills/test-driven-development/SKILL.md)**
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

**[using-git-worktrees](/.submodules/superpowers/skills/using-git-worktrees/SKILL.md)**
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
|------|-----|
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
| Check phase readiness | `/phase-gate` skill or `phase-reviewer` agent |
| Respond to a code review | `receiving-code-review` skill |
| Confirm work is done | `verification-before-completion` skill |
