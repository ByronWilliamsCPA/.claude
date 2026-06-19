---
title: "Skills Catalog"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Index of all 40+ skills in .claude/skills/ with trigger patterns and workflow descriptions."
tags:
  - reference
  - skills
  - technical
---

Skills are triggered by slash commands or keyword patterns in your Claude Code session. They run inside the main conversation window and handle common, repeatable workflows. See [Agent Dispatch](../architecture/agent-dispatch.md) for the distinction between skills and agents, and [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) for the classification rubric.

All skill directories live in `.claude/skills/` (symlinked to `~/.claude/skills/`). Each contains a `SKILL.md` file with the trigger pattern and instructions.

## Development and Git

| Skill | Trigger | What it does |
| --- | --- | --- |
| `git` | `/git`, `/commit`, `/git pr` | Conventional commits, branch management, PR creation with security scan |
| `finishing-a-development-branch` | `/finishing-a-development-branch` | Runs quality checks, tests, and prepares a branch for PR |
| `using-git-worktrees` | `/using-git-worktrees` | Creates and manages git worktrees for parallel development |
| `ci-fix` | `/ci-fix` | Diagnoses and fixes failing CI pipeline jobs |
| `verification-before-completion` | `/verification-before-completion` | Final verification checklist before marking work complete |

## Code Quality

| Skill | Trigger | What it does |
| --- | --- | --- |
| `quality` | `/quality` | Ruff format, lint, BasedPyright type checking, and code quality gates |
| `rad` | `/rad` | Response-Aware Development: tags and verifies critical code assumptions |
| `requesting-code-review` | `/requesting-code-review` | Structures a review request and invokes the code-reviewer agent |
| `receiving-code-review` | `/receiving-code-review` | Processes incoming code review feedback systematically |
| `subagent-driven-development` | `/subagent-driven-development` | Implements a task using an agent-review loop for quality assurance |
| `dispatching-parallel-agents` | `/dispatching-parallel-agents` | Runs multiple independent agents in parallel for complex tasks |

## Testing

| Skill | Trigger | What it does |
| --- | --- | --- |
| `testing` | `/testing` | Runs the full test suite with coverage reporting |
| `test-coverage` | `/test-coverage` | Analyzes coverage gaps and generates tests to close them |
| `test-driven-development` | `/tdd`, `/test-driven-development` | Enforces red-green-refactor TDD cycle for new features |
| `debug-tests` | `/debug-tests` | Systematic debugging of failing tests with root-cause analysis |

## Security

| Skill | Trigger | What it does |
| --- | --- | --- |
| `security` | `/security` | Security scan and OWASP checks on the codebase |
| `sonarcloud` | `sonar`, `sonarcloud`, `quality gate` | SonarCloud issue analysis, quality gates, and security hotspots |

## Planning and Architecture

| Skill | Trigger | What it does |
| --- | --- | --- |
| `project-planning` | `/project-planning` | Creates a structured project plan with phases and acceptance criteria |
| `phase-gate` | `/phase-gate` | Validates that all phase acceptance criteria are met before closing a phase |
| `executing-plans` | `/executing-plans` | Executes a structured plan step-by-step with checkpoints |
| `brainstorming` | `/brainstorming` | Structured brainstorming for problem-solving or feature design |
| `writing-plans` | `/writing-plans` | Creates a structured writing plan for a document or content piece |
| `claude-md-improver` | `/claude-md-improver` | Reviews and improves CLAUDE.md files |
| `claude-automation-recommender` | `/claude-automation-recommender` | Recommends Claude Code automations for a given workflow |
| `skill-creator` | `/skill-creator` | Creates a new skill from a description or existing workflow |

## Documentation

| Skill | Trigger | What it does |
| --- | --- | --- |
| `doc-audit` | `/doc-audit` | Audits documentation for gaps, accuracy, and frontmatter compliance |
| `diagram-maintenance` | `/diagram-maintenance` | Creates and maintains PlantUML diagrams with SVG rendering |
| `handoff` | `/handoff` | Creates a structured handoff document summarizing current work state |
| `session-report` | `/session-report` | Summary report of what was accomplished in this session |

## Frontend

| Skill | Trigger | What it does |
| --- | --- | --- |
| `frontend-design` | `build UI`, `create component`, `design page`, `frontend`, `dashboard` | UI/UX design, component creation, and React pattern application |

## Document Generation

| Skill | Trigger | What it does |
| --- | --- | --- |
| `pdf` | `/pdf` | Generates or converts content to PDF |
| `docx` | `/docx` | Generates or converts content to Word document |
| `pptx` | `/pptx` | Generates or converts content to PowerPoint |
| `xlsx` | `/xlsx` | Generates or converts content to Excel |

## Writing and Content

| Skill | Trigger | What it does |
| --- | --- | --- |
| `writing` | `/writing` | Full three-stage writing quality pipeline (grammar → validate → style) |
| `writing-rules` | `/writing-rules` | Reviews and enforces writing rules from `.claude/rules/writing.md` |
| `writing-skills` | `/writing-skills` | Creates or refines writing skills for specific content types |
| `using-superpowers` | `/using-superpowers` | Activates community superpowers from the superpowers submodule |

## Meta and Execution

| Skill | Trigger | What it does |
| --- | --- | --- |
| `systematic-debugging` | `/systematic-debugging` | Root-cause-first debugging workflow for complex issues |

## Production Operations

| Skill | Trigger | What it does |
| --- | --- | --- |
| `observability-and-instrumentation` | `/observability-and-instrumentation` | Structured logs, RED/USE metrics, correlation IDs, tracing, symptom-based alerting |
| `deprecation-and-migration` | `/deprecation-and-migration` | Deprecation decision, strangler/adapter/feature-flag migration, zombie-code handling |
| `performance-optimization` | `/performance-optimization` | Measure-first performance work, Core Web Vitals, N+1/bundle anti-patterns, budgets |
| `shipping-and-launch` | `/shipping-and-launch` | Pre-launch checklist, staged canary rollout, post-launch verification, rollback |
| `source-driven-development` | `/source-driven-development` | Version-detect, fetch official docs (context7-first), implement, cite sources |

## Reasoning and Quality

| Skill | Trigger | What it does |
| --- | --- | --- |
| `doubt-driven-development` | `/doubt-driven-development` | Fresh-context adversarial review of every non-trivial decision: claim, contract, issues-only reviewer, reconcile, bounded stop |
| `context-engineering` | `/context-engineering` | Five-tier context hierarchy, file trust levels, confusion management, inline planning; repointed to scoped CLAUDE.md and tiered MCP |

## See Also

- [Agents Catalog](agents.md): the 43 agents and their domains
- [Architecture → Agent Dispatch](../architecture/agent-dispatch.md): how skills are dispatched at runtime
- [Contributing → Adding a Skill](../contributing/adding-skills.md): how to add a new skill
