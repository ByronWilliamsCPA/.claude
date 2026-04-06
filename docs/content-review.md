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
| `[~]` | [project-planning/SKILL.md](../.claude/skills/project-planning/SKILL.md) | Fixed (P3 sweep): mcp__zen__consensus→mcp__pal__consensus (6 occurrences) |
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
| `[x]` | [quality/workflows/format.md](../.claude/skills/quality/workflows/format.md) | |
| `[~]` | [quality/workflows/lint.md](../.claude/skills/quality/workflows/lint.md) | Fixed: poetry→uv in allowed-tools; mypy→basedpyright |
| `[~]` | [quality/workflows/naming.md](../.claude/skills/quality/workflows/naming.md) | Fixed: updated allowed-tools; added Ruff N-rules enforcement section |
| `[~]` | [quality/workflows/precommit.md](../.claude/skills/quality/workflows/precommit.md) | Fixed: black→ruff format; mypy→basedpyright; updated allowed-tools |

### Testing Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[x]` | [testing/workflows/generate.md](../.claude/skills/testing/workflows/generate.md) | |
| `[x]` | [testing/workflows/review.md](../.claude/skills/testing/workflows/review.md) | |
| `[x]` | [testing/workflows/e2e.md](../.claude/skills/testing/workflows/e2e.md) | |
| `[x]` | [testing/workflows/performance.md](../.claude/skills/testing/workflows/performance.md) | |
| `[x]` | [testing/workflows/security.md](../.claude/skills/testing/workflows/security.md) | |

### Security Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [security/workflows/scan.md](../.claude/skills/security/workflows/scan.md) | Fixed: safety→pip-audit; bandit→ruff --select S; poetry→uv; added exit code docs |
| `[x]` | [security/workflows/validate-env.md](../.claude/skills/security/workflows/validate-env.md) | |
| `[x]` | [security/workflows/encrypt.md](../.claude/skills/security/workflows/encrypt.md) | |

### Git Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [git/workflows/commit.md](../.claude/skills/git/workflows/commit.md) | Fixed: added git commit -S signing requirement |
| `[~]` | [git/workflows/pr.md](../.claude/skills/git/workflows/pr.md) | Fixed: gh pr create → /git pr skill as primary method |

### RAD Workflows

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [rad/workflows/verify.md](../.claude/skills/rad/workflows/verify.md) | Fixed: mcp__zen-core__→mcp__pal__ in frontmatter and body |
| `[x]` | [rad/workflows/list.md](../.claude/skills/rad/workflows/list.md) | |
| `[x]` | [rad/workflows/test.md](../.claude/skills/rad/workflows/test.md) | |

### Skill Context Files

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [testing/context/pytest-commands.md](../.claude/skills/testing/context/pytest-commands.md) | Fixed: bare pytest → uv run pytest |
| `[x]` | [testing/context/pytest-patterns.md](../.claude/skills/testing/context/pytest-patterns.md) | |
| `[x]` | [git/context/branch-strategy.md](../.claude/skills/git/context/branch-strategy.md) | |
| `[x]` | [git/context/conventional-commits.md](../.claude/skills/git/context/conventional-commits.md) | |
| `[x]` | [rad/context/methodology.md](../.claude/skills/rad/context/methodology.md) | |
| `[x]` | [rad/context/tagging-standards.md](../.claude/skills/rad/context/tagging-standards.md) | |

### Skill-Creator Sub-Agents

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [skill-creator/agents/grader.md](../.claude/skills/skill-creator/agents/grader.md) | Fixed: added missing frontmatter |
| `[~]` | [skill-creator/agents/comparator.md](../.claude/skills/skill-creator/agents/comparator.md) | Fixed: added missing frontmatter |
| `[~]` | [skill-creator/agents/analyzer.md](../.claude/skills/skill-creator/agents/analyzer.md) | Fixed: added missing frontmatter |
| `[x]` | [skill-creator/references/schemas.md](../.claude/skills/skill-creator/references/schemas.md) | |

### Project-Planning Templates & Reference

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[x]` | [project-planning/templates/pvs-template.md](../.claude/skills/project-planning/templates/pvs-template.md) | |
| `[x]` | [project-planning/templates/adr-template.md](../.claude/skills/project-planning/templates/adr-template.md) | |
| `[~]` | [project-planning/templates/tech-spec-template.md](../.claude/skills/project-planning/templates/tech-spec-template.md) | Fixed: Black→ruff format |
| `[x]` | [project-planning/templates/roadmap-template.md](../.claude/skills/project-planning/templates/roadmap-template.md) | |
| `[x]` | [project-planning/reference/document-guide.md](../.claude/skills/project-planning/reference/document-guide.md) | |
| `[x]` | [project-planning/reference/prompting-patterns.md](../.claude/skills/project-planning/reference/prompting-patterns.md) | |
| `[x]` | [project-planning/workflows/synthesize.md](../.claude/skills/project-planning/workflows/synthesize.md) | |

### Standards (referenced from CLAUDE.md)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [standards/testing.md](../standards/testing.md) | Fixed: mypy→basedpyright; added BasedPyright config block; pip-audit bare→uv run |
| `[~]` | [standards/python.md](../standards/python.md) | Fixed: poetry→uv throughout; mypy→basedpyright; black→ruff; Python range; coverage thresholds |
| `[~]` | [standards/linting.md](../standards/linting.md) | Fixed: py311→py312; "handled by Black"→ruff format; removed "(faster than MyPy)" |
| `[~]` | [standards/security.md](../standards/security.md) | Fixed: safety→pip-audit; bandit→uv run bandit; poetry→uv |
| `[~]` | [standards/git-workflow.md](../standards/git-workflow.md) | Fixed: removed "for Poetry" from commit example |
| `[~]` | [standards/git-worktree.md](../standards/git-worktree.md) | Fixed: removed poetry install fallback comments |
| `[x]` | [standards/mcp-minimal-bloat.md](../standards/mcp-minimal-bloat.md) | |
| `[x]` | [standards/owasp-specialist-agents-spec.md](../standards/owasp-specialist-agents-spec.md) | |
| `[~]` | [standards/test-coverage-agent-spec.md](../standards/test-coverage-agent-spec.md) | Fixed: mypy→basedpyright; pip install→uv; pytest→uv run pytest |

### Key Docs (referenced from CLAUDE.md)

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [docs/response-aware-development.md](../docs/response-aware-development.md) | Fixed: Zen MCP Server→PAL MCP Server; stale command names |

---

## Priority 4 — Supporting
> Informational — consulted but not auto-loaded. Lower urgency.

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[~]` | [AGENTS-AND-SKILLS.md](../AGENTS-AND-SKILLS.md) | Fixed: Task tool→Agent tool; removed /commit-prepare and /pr-prepare (non-existent); fixed /debug-tests link; added 10 uncatalogued agents |
| `[~]` | [.github/copilot-instructions.md](../.github/copilot-instructions.md) | Fixed: Black→ruff format (2 occurrences) |
| `[x]` | [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) | |
| `[~]` | [mcp/README.md](../mcp/README.md) | Fixed: zen-server.json→disabled; Zen MCP Server→PAL MCP Server |
| `[x]` | [docs/tdd-enforcement-system.md](../docs/tdd-enforcement-system.md) | |
| `[x]` | [docs/project-env-loading.md](../docs/project-env-loading.md) | |
| `[x]` | [docs/development/architecture.md](../docs/development/architecture.md) | |
| `[~]` | [docs/development/code-quality.md](../docs/development/code-quality.md) | Fixed: "Black compatible"→ruff format default |
| `[x]` | [docs/development/contributing.md](../docs/development/contributing.md) | |
| `[~]` | [docs/development/testing.md](../docs/development/testing.md) | Fixed: coverage thresholds (85%/70%→80/70/90/90 canonical) |
| `[x]` | [docs/guides/configuration.md](../docs/guides/configuration.md) | |
| `[~]` | [docs/guides/usage.md](../docs/guides/usage.md) | Fixed: pip install→uv pip install |
| `[~]` | [docs/guides/testing-guide.md](../docs/guides/testing-guide.md) | Fixed: mypy→basedpyright throughout; pip install→uv sync/uv add; 13 plugin entries fixed |
| `[x]` | [docs/planning/project-vision.md](../docs/planning/project-vision.md) | |
| `[x]` | [docs/planning/roadmap.md](../docs/planning/roadmap.md) | |
| `[x]` | [docs/planning/tech-spec.md](../docs/planning/tech-spec.md) | |

---

## Priority 5 — Not Critical
> Project meta files and informational READMEs. Review last.

| Status | File | Issues / Notes |
|--------|------|----------------|
| `[x]` | [README.md](../README.md) | |
| `[x]` | [CHANGELOG.md](../CHANGELOG.md) | Historical Poetry reference in v1.0.0 entry exempt |
| `[~]` | [CONTRIBUTING.md](../CONTRIBUTING.md) | Fixed: uv run safety check→uv run pip-audit |
| `[x]` | [SECURITY.md](../SECURITY.md) | |
| `[x]` | [.claude/README.md](../.claude/README.md) | |
| `[x]` | [scripts/README.md](../scripts/README.md) | |
| `[x]` | [.github/workflows/README.md](../.github/workflows/README.md) | |
| `[x]` | [docs/ADRs/README.md](../docs/ADRs/README.md) | |
| `[~]` | [docs/index.md](../docs/index.md) | Fixed: pip install→uv add |
| `[x]` | [docs/api-reference.md](../docs/api-reference.md) | |
| `[x]` | [docs/OPENSSF_COMPLIANCE.md](../docs/OPENSSF_COMPLIANCE.md) | |
| `[x]` | [docs/context7-setup.md](../docs/context7-setup.md) | |
| `[x]` | [docs/serena-setup.md](../docs/serena-setup.md) | |
| `[x]` | [docs/PROJECT_SETUP.md](../docs/PROJECT_SETUP.md) | |
| `[x]` | [docs/PYTHON_COMPATIBILITY.md](../docs/PYTHON_COMPATIBILITY.md) | |

---

## Progress Summary

| Priority | Total | Reviewed OK | Needs Update | Missing/Broken | Not Started |
|----------|-------|-------------|--------------|----------------|-------------|
| 1 — Very Critical | 6 | 0 | 6 | 0 | 0 |
| 2 — Critical | 52 | 51 | 1 | 0 | 0 |
| 3 — Important | 44 | 24 | 20 | 0 | 0 |
| 4 — Supporting | 16 | 9 | 7 | 0 | 0 |
| 5 — Not Critical | 15 | 13 | 2 | 0 | 0 |
| **Total** | **133** | **97** | **36** | **0** | **0** |

---

## Known Issues (active)

- [project-planning/SKILL.md](../.claude/skills/project-planning/SKILL.md) — P2 file marked `[x]`, but contains stale `mcp__zen__consensus` references (found during P3 review of adjacent files; fix pending)
