---
schema_type: common
title: "Claude Config Content Review"
status: draft
owner: core-maintainer
purpose: "Systematic review of all Markdown files that affect Claude's behavior, organized by criticality."
tags:
  - documentation
  - quality
  - overview
---

Systematic review of all `.md` files that affect Claude's behavior, organized by criticality.
Pulled together from various sources — goal is to verify each file has accurate, complete content.

## Status Legend

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Not yet reviewed |
| `[x]` | Reviewed — OK |
| `[~]` | Reviewed — needs update |
| `[!]` | Reviewed — missing or broken content |

---

## Priority 1 — Very Critical
> Always-loaded files that directly govern Claude's behavior.

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [CLAUDE.md](../CLAUDE.md) | Fixed: named pip-audit explicitly; scoped Code Gen section to Python; added variant skills note |
| `[~]` | [.claude/rules/git-workflow.md](../.claude/rules/git-workflow.md) | Fixed: mypy→basedpyright; added breaking-change notation; added cross-references |
| `[~]` | [.claude/rules/mcp-strategy.md](../.claude/rules/mcp-strategy.md) | Fixed: agent frontmatter example; added Tier 2 skill bundles; updated Tier 3 keywords |
| `[~]` | [.claude/rules/pre-commit.md](../.claude/rules/pre-commit.md) | Fixed: added tests+RAD steps; named /security skill; clarified /quality scope; pip-audit exit code; removed zen-core ref |
| `[~]` | [.claude/rules/python.md](../.claude/rules/python.md) | Fixed: Black→Ruff label; expanded Ruff rules table; clarified Python version range; added BasedPyright config example; fixed context/python-standards.md |
| `[~]` | [.claude/rules/supervisor.md](../.claude/rules/supervisor.md) | Fixed: removed ghost agent+MCP tools; replaced table with accurate agent/skill/type breakdown; removed mcp__zen-core__pr_prepare |

---

## Priority 2 — Critical
> Agent definitions and skill entry points — invoked directly.

### Agent Definitions (`.claude/agents/`)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[x]` | [code-reviewer.md](../.claude/agents/code-reviewer.md) | Fixed: added frontmatter (name, description, model, tools) |
| `[x]` | [security-auditor.md](../.claude/agents/security-auditor.md) | Fixed: added frontmatter |
| `[x]` | [test-engineer.md](../.claude/agents/test-engineer.md) | Fixed: added frontmatter |
| `[x]` | [test-writer.md](../.claude/agents/test-writer.md) | Fixed: added frontmatter |
| `[x]` | [test-reviewer.md](../.claude/agents/test-reviewer.md) | Fixed: added frontmatter |
| `[x]` | [owasp-dispatch.md](../.claude/agents/owasp-dispatch.md) | Fixed: added frontmatter |
| `[x]` | [owasp-agent.md](../.claude/agents/owasp-agent.md) | Fixed: added frontmatter |
| `[x]` | [owasp-web.md](../.claude/agents/owasp-web.md) | Fixed: added frontmatter |
| `[x]` | [owasp-api.md](../.claude/agents/owasp-api.md) | Fixed: added frontmatter |
| `[x]` | [owasp-llm.md](../.claude/agents/owasp-llm.md) | Fixed: added frontmatter |
| `[x]` | [owasp-ml.md](../.claude/agents/owasp-ml.md) | Fixed: added frontmatter |
| `[x]` | [owasp-citizen.md](../.claude/agents/owasp-citizen.md) | Fixed: added frontmatter |
| `[x]` | [ai-engineer.md](../.claude/agents/ai-engineer.md) | |
| `[x]` | [api-development-agent.md](../.claude/agents/api-development-agent.md) | |
| `[x]` | [database-operations-agent.md](../.claude/agents/database-operations-agent.md) | |
| `[x]` | [devops-deployment-agent.md](../.claude/agents/devops-deployment-agent.md) | |
| `[x]` | [frontend-designer.md](../.claude/agents/frontend-designer.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [ui-testing-agent.md](../.claude/agents/ui-testing-agent.md) | |
| `[x]` | [git-workflow-agent.md](../.claude/agents/git-workflow-agent.md) | |
| `[x]` | [github-workflow-agent.md](../.claude/agents/github-workflow-agent.md) | |
| `[x]` | [documentation-writer.md](../.claude/agents/documentation-writer.md) | |
| `[x]` | [diagram-maintenance-agent.md](../.claude/agents/diagram-maintenance-agent.md) | |
| `[x]` | [diagram-specialist.md](../.claude/agents/diagram-specialist.md) | Submodule symlink → .submodules/image-generation; frontmatter added in submodule repo |
| `[x]` | [research-agent.md](../.claude/agents/research-agent.md) | |
| `[x]` | [modularization-assistant.md](../.claude/agents/modularization-assistant.md) | |
| `[x]` | [visual-content-generator.md](../.claude/agents/visual-content-generator.md) | Fixed: replaced non-standard mcp_tools: field with tools: |
| `[x]` | [phase-reviewer.md](../.claude/agents/phase-reviewer.md) | Fixed: added frontmatter |
| `[x]` | [scope-analyzer.md](../.claude/agents/scope-analyzer.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [plan-validator.md](../.claude/agents/plan-validator.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [style-analyzer.md](../.claude/agents/style-analyzer.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [tone-rewriter.md](../.claude/agents/tone-rewriter.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [document-drafter.md](../.claude/agents/document-drafter.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [document-validator.md](../.claude/agents/document-validator.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [grammar-composition-editor.md](../.claude/agents/grammar-composition-editor.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [writing-style-editor.md](../.claude/agents/writing-style-editor.md) | Fixed: added model + tools to frontmatter |
| `[x]` | [audience-reaction-analyzer.md](../.claude/agents/audience-reaction-analyzer.md) | Fixed: added model + tools to frontmatter |

### Skill Entry Points (`.claude/skills/*/SKILL.md`)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[x]` | [quality/SKILL.md](../.claude/skills/quality/SKILL.md) | Fixed: added frontmatter; removed Black refs; narrowed keywords to "quality, lint, format" |
| `[x]` | [testing/SKILL.md](../.claude/skills/testing/SKILL.md) | |
| `[x]` | [security/SKILL.md](../.claude/skills/security/SKILL.md) | Fixed: added frontmatter |
| `[x]` | [git/SKILL.md](../.claude/skills/git/SKILL.md) | |
| `[x]` | [debug-tests/SKILL.md](../.claude/skills/debug-tests/SKILL.md) | |
| `[~]` | [handoff/SKILL.md](../.claude/skills/handoff/SKILL.md) | Minor: no workflows/ subdirectory (optional improvement — skill is functional) |
| `[x]` | [phase-gate/SKILL.md](../.claude/skills/phase-gate/SKILL.md) | |
| `[x]` | [rad/SKILL.md](../.claude/skills/rad/SKILL.md) | |
| `[x]` | [skill-creator/SKILL.md](../.claude/skills/skill-creator/SKILL.md) | |
| `[x]` | [diagram-maintenance/SKILL.md](../.claude/skills/diagram-maintenance/SKILL.md) | Fixed: added frontmatter |
| `[x]` | [frontend-design/SKILL.md](../.claude/skills/frontend-design/SKILL.md) | |
| `[x]` | [project-planning/SKILL.md](../.claude/skills/project-planning/SKILL.md) | |
| `[x]` | [sonarcloud/SKILL.md](../.claude/skills/sonarcloud/SKILL.md) | |
| `[x]` | [test-coverage/SKILL.md](../.claude/skills/test-coverage/SKILL.md) | |

### Active Context (`.claude/context/`)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[x]` | [python-standards.md](../.claude/context/python-standards.md) | P1 fix confirmed (Black→Ruff); fully aligned with rules and pyproject.toml |
| `[x]` | [testing-patterns.md](../.claude/context/testing-patterns.md) | |

---

## Priority 3 — Important
> Loaded at runtime by skills/agents. Wrong content here causes bad outputs.

### Quality Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [quality/workflows/format.md](../.claude/skills/quality/workflows/format.md) | |
| `[ ]` | [quality/workflows/lint.md](../.claude/skills/quality/workflows/lint.md) | Known: uses poetry, not uv |
| `[ ]` | [quality/workflows/naming.md](../.claude/skills/quality/workflows/naming.md) | Known: PEP 8 only, no tooling guidance |
| `[ ]` | [quality/workflows/precommit.md](../.claude/skills/quality/workflows/precommit.md) | Known: references black and mypy |

### Testing Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [testing/workflows/generate.md](../.claude/skills/testing/workflows/generate.md) | |
| `[ ]` | [testing/workflows/review.md](../.claude/skills/testing/workflows/review.md) | |
| `[ ]` | [testing/workflows/e2e.md](../.claude/skills/testing/workflows/e2e.md) | |
| `[ ]` | [testing/workflows/performance.md](../.claude/skills/testing/workflows/performance.md) | |
| `[ ]` | [testing/workflows/security.md](../.claude/skills/testing/workflows/security.md) | |

### Security Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [security/workflows/scan.md](../.claude/skills/security/workflows/scan.md) | |
| `[ ]` | [security/workflows/validate-env.md](../.claude/skills/security/workflows/validate-env.md) | |
| `[ ]` | [security/workflows/encrypt.md](../.claude/skills/security/workflows/encrypt.md) | |

### Git Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [git/workflows/commit.md](../.claude/skills/git/workflows/commit.md) | |
| `[ ]` | [git/workflows/pr.md](../.claude/skills/git/workflows/pr.md) | |

### RAD Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [rad/workflows/verify.md](../.claude/skills/rad/workflows/verify.md) | |
| `[ ]` | [rad/workflows/list.md](../.claude/skills/rad/workflows/list.md) | |
| `[ ]` | [rad/workflows/test.md](../.claude/skills/rad/workflows/test.md) | |

### Skill Context Files

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [testing/context/pytest-commands.md](../.claude/skills/testing/context/pytest-commands.md) | |
| `[ ]` | [testing/context/pytest-patterns.md](../.claude/skills/testing/context/pytest-patterns.md) | |
| `[ ]` | [git/context/branch-strategy.md](../.claude/skills/git/context/branch-strategy.md) | |
| `[ ]` | [git/context/conventional-commits.md](../.claude/skills/git/context/conventional-commits.md) | |
| `[ ]` | [rad/context/methodology.md](../.claude/skills/rad/context/methodology.md) | |
| `[ ]` | [rad/context/tagging-standards.md](../.claude/skills/rad/context/tagging-standards.md) | |

### Skill-Creator Sub-Agents

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [skill-creator/agents/grader.md](../.claude/skills/skill-creator/agents/grader.md) | |
| `[ ]` | [skill-creator/agents/comparator.md](../.claude/skills/skill-creator/agents/comparator.md) | |
| `[ ]` | [skill-creator/agents/analyzer.md](../.claude/skills/skill-creator/agents/analyzer.md) | |
| `[ ]` | [skill-creator/references/schemas.md](../.claude/skills/skill-creator/references/schemas.md) | |

### Project-Planning Templates & Reference

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [project-planning/templates/pvs-template.md](../.claude/skills/project-planning/templates/pvs-template.md) | |
| `[ ]` | [project-planning/templates/adr-template.md](../.claude/skills/project-planning/templates/adr-template.md) | |
| `[ ]` | [project-planning/templates/tech-spec-template.md](../.claude/skills/project-planning/templates/tech-spec-template.md) | |
| `[ ]` | [project-planning/templates/roadmap-template.md](../.claude/skills/project-planning/templates/roadmap-template.md) | |
| `[ ]` | [project-planning/reference/document-guide.md](../.claude/skills/project-planning/reference/document-guide.md) | |
| `[ ]` | [project-planning/reference/prompting-patterns.md](../.claude/skills/project-planning/reference/prompting-patterns.md) | |
| `[ ]` | [project-planning/workflows/synthesize.md](../.claude/skills/project-planning/workflows/synthesize.md) | |

### Standards (referenced from CLAUDE.md)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [standards/testing.md](../standards/testing.md) | Modified (git status) |
| `[ ]` | [standards/python.md](../standards/python.md) | |
| `[ ]` | [standards/linting.md](../standards/linting.md) | |
| `[ ]` | [standards/security.md](../standards/security.md) | |
| `[ ]` | [standards/git-workflow.md](../standards/git-workflow.md) | |
| `[ ]` | [standards/git-worktree.md](../standards/git-worktree.md) | |
| `[ ]` | [standards/mcp-minimal-bloat.md](../standards/mcp-minimal-bloat.md) | |
| `[ ]` | [standards/owasp-specialist-agents-spec.md](../standards/owasp-specialist-agents-spec.md) | |
| `[ ]` | [standards/test-coverage-agent-spec.md](../standards/test-coverage-agent-spec.md) | |

### Key Docs (referenced from CLAUDE.md)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [docs/response-aware-development.md](../docs/response-aware-development.md) | |

---

## Priority 4 — Supporting
> Informational — consulted but not auto-loaded. Lower urgency.

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [AGENTS-AND-SKILLS.md](../AGENTS-AND-SKILLS.md) | |
| `[ ]` | [.github/copilot-instructions.md](../.github/copilot-instructions.md) | |
| `[ ]` | [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) | |
| `[ ]` | [mcp/README.md](../mcp/README.md) | |
| `[ ]` | [docs/tdd-enforcement-system.md](../docs/tdd-enforcement-system.md) | |
| `[ ]` | [docs/project-env-loading.md](../docs/project-env-loading.md) | |
| `[ ]` | [docs/development/architecture.md](../docs/development/architecture.md) | |
| `[ ]` | [docs/development/code-quality.md](../docs/development/code-quality.md) | |
| `[ ]` | [docs/development/contributing.md](../docs/development/contributing.md) | |
| `[ ]` | [docs/development/testing.md](../docs/development/testing.md) | |
| `[ ]` | [docs/guides/configuration.md](../docs/guides/configuration.md) | |
| `[ ]` | [docs/guides/usage.md](../docs/guides/usage.md) | |
| `[ ]` | [docs/guides/testing-guide.md](../docs/guides/testing-guide.md) | |
| `[ ]` | [docs/planning/project-vision.md](../docs/planning/project-vision.md) | |
| `[ ]` | [docs/planning/roadmap.md](../docs/planning/roadmap.md) | |
| `[ ]` | [docs/planning/tech-spec.md](../docs/planning/tech-spec.md) | |

---

## Priority 5 — Not Critical
> Project meta files and informational READMEs. Review last.

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[ ]` | [README.md](../README.md) | |
| `[ ]` | [CHANGELOG.md](../CHANGELOG.md) | |
| `[ ]` | [CONTRIBUTING.md](../CONTRIBUTING.md) | |
| `[ ]` | [SECURITY.md](../SECURITY.md) | |
| `[ ]` | [.claude/README.md](../.claude/README.md) | |
| `[ ]` | [scripts/README.md](../scripts/README.md) | |
| `[ ]` | [.github/workflows/README.md](../.github/workflows/README.md) | |
| `[ ]` | [docs/ADRs/README.md](../docs/ADRs/README.md) | |
| `[ ]` | [docs/index.md](../docs/index.md) | |
| `[ ]` | [docs/api-reference.md](../docs/api-reference.md) | |
| `[ ]` | [docs/OPENSSF_COMPLIANCE.md](../docs/OPENSSF_COMPLIANCE.md) | |
| `[ ]` | [docs/context7-setup.md](../docs/context7-setup.md) | |
| `[ ]` | [docs/serena-setup.md](../docs/serena-setup.md) | |
| `[ ]` | [docs/PROJECT_SETUP.md](../docs/PROJECT_SETUP.md) | |
| `[ ]` | [docs/PYTHON_COMPATIBILITY.md](../docs/PYTHON_COMPATIBILITY.md) | |

---

## Progress Summary

| Priority | Total | Reviewed OK | Needs Update | Missing/Broken | Not Started |
|----------|-------|-------------|--------------|----------------|-------------|
| 1 — Very Critical | 6 | 0 | 6 | 0 | 0 |
| 2 — Critical | 52 | 51 | 1 | 0 | 0 |
| 3 — Important | 44 | 0 | 0 | 0 | 44 |
| 4 — Supporting | 16 | 0 | 0 | 0 | 16 |
| 5 — Not Critical | 15 | 0 | 0 | 0 | 15 |
| **Total** | **133** | **50** | **7** | **1** | **75** |

---

## Known Issues (pre-populated from initial analysis)

- [quality/workflows/lint.md](../.claude/skills/quality/workflows/lint.md) — uses `poetry` instead of `uv`; uses `mypy` instead of `basedpyright`
- [quality/workflows/precommit.md](../.claude/skills/quality/workflows/precommit.md) — references `black` (should be `ruff format`) and `mypy` (should be `basedpyright`)
- [quality/workflows/naming.md](../.claude/skills/quality/workflows/naming.md) — lists PEP 8 rules only; no tooling guidance (ruff N-rules handle this automatically)
- [quality/SKILL.md](../.claude/skills/quality/SKILL.md) — missing frontmatter `---` block; no check-vs-fix decision tree; no toolchain specification
- [standards/testing.md](../standards/testing.md) — has uncommitted modifications (check git diff)
