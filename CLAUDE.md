# Global Claude Development Standards

> **Status**: ✅ Active | Core Standard | **Version**: 1.1.0 | **Last Updated**: 2026-04-09
>
> Universal development standards and practices for Claude Code across all projects.

## Project Context

For project context, always search project docs and markdown files first (especially files in
docs/, initiatives/, or project root). Do not search memory or make assumptions about
organizational priorities.

When asked about business priorities, organizational strategy, or project decisions, read the
relevant project files before answering. If no file covers the topic, state what was searched
and answer from general knowledge with an explicit flag that the answer may not reflect current
project priorities.

## Code Quality

When SonarCloud or linting tools flag issues, fix the actual issues rather than proposing
exclusions. Only exclude files if explicitly approved by the user.

This applies to all quality gates: never propose `# noqa` comments, `# type: ignore`,
`pytest.mark.skip`, `--no-verify`, or CI bypass flags as solutions. Fix the root cause.
Exceptions: vendored or third-party code that cannot be changed, or suppression paired with a
tracking reference (ticket number, GitHub issue, or TODO with link).

## Git Workflow

Always run pre-commit hooks (`pre-commit run --all-files`) before committing.

> **Branch rules, worktree patterns, naming conventions**: See `.claude/rules/git-workflow.md`
>
> **Pre-commit checklist**: See `.claude/rules/pre-commit.md`

## Testing

When asked to fix or improve tests, clarify scope first: adding missing tests vs. fixing
failing tests vs. improving test depth are different tasks.

When tests fail, investigate root causes in this order:

1. **Test fixtures/configuration**: Missing seed data, incorrect factory defaults, conftest issues
2. **Environment mismatches**: SQLite vs Postgres differences (JSONB, UUID, pool_size), Python version
3. **Dependency drift**: Updated library changed behavior, version constraint mismatch
4. **Test isolation**: Shared state, ordering dependencies, missing teardown

## System / Shell

When commands fail due to permissions (e.g., mkdir, mount), try with sudo immediately.

When a connection error, socket failure, or service-unreachable symptom appears, check
platform-level causes first: WSL2 port forwarding rules, Docker bridge networking, Unix socket
paths, and container health. Do not exhaust code-level fixes before ruling out the environment.

## Core Development Standards

- **Code Quality**: Ruff formatting & linting (88 chars, PyStrict-aligned), BasedPyright strict mode
- **Security**: GPG/SSH key validation, dependency scanning (`uv run pip-audit`), encrypted secrets
- **Testing**: Graduated coverage (80% line / 70% branch / 90% critical / 90% patch)
- **Git**: Conventional commits, signed commits, feature branch workflow
- **Response-Aware Development**: Assumption tagging and verification

> **Python linting, BasedPyright config, Ruff rules**: See `.claude/rules/python.md`
>
> **Canonical package choices, override policy**: See `.claude/standards/packages.md`
>
> **Writing rules (no em-dashes, AI pattern blacklist, grammar authority)**: See `.claude/rules/writing.md`
>
> **Writing quality thresholds (pipeline stages, stylometry targets, pass/fail)**: See `.claude/standards/writing-quality.md`

## Response-Aware Development (RAD)

> **Full Documentation**: See `/docs/response-aware-development.md`

When writing code, ALWAYS tag assumptions that could cause production failures:

```javascript
// #CRITICAL: [category]: [assumption that could cause outages/data loss]
// #VERIFY: [defensive code required]

// #ASSUME: [category]: [assumption that could cause bugs]
// #VERIFY: [validation needed]

// #EDGE: [category]: [assumption about uncommon scenarios]
// #VERIFY: [optional improvement]
```

**Mandatory tagging categories**: Timing Dependencies, External Resources, Data Integrity,
Concurrency, Security, Payment/Financial.

**Verification workflow**: Tag during development → hook triggers agent scan on save →
agent categorizes and suggests fixes → validates before commit.

## Code Generation Principles — Python (MANDATORY)

### Function Structure

- **Length**: Prefer 20-60 statements; hard limit 100 (PLR0915)
- **Single Responsibility**: One conceptual task per function
- **Early Returns**: Exit early on errors; avoid deep else branches
- **Nesting Depth**: Maximum 3 levels inside function body

### Complexity Controls

- **Cyclomatic Complexity**: Target ≤10 (C901 enforced)
- **Branches**: Maximum 12 per function (PLR0912)

### Code Duplication

- **Zero Tolerance**: Extract shared functions immediately
- **Rule of Three**: Three similar blocks → refactor to reusable function

### Data & State Design

- **Immutability First**: Use `frozen=True` dataclasses
- **Pure Functions**: Minimize side effects
- **No Global State**: Pass dependencies explicitly
- **Parameter Grouping**: >4 params → dataclass (see `.claude/rules/python.md`)

> **Supervisor patterns, agent assignment, PR workflow**: See `.claude/rules/supervisor.md`
>
> **MCP tool loading strategy**: See `.claude/rules/mcp-strategy.md`

## OpenSSF Best Practices

Required files in every project: `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`

```bash
ls -1 LICENSE SECURITY.md CONTRIBUTING.md CHANGELOG.md README.md 2>/dev/null | wc -l
# Should output: 5
```

Before any release: CHANGELOG updated, no vulnerabilities >60 days old, tests pass (>80%),
version tag follows SemVer. New features: add tests first, document security implications,
update CHANGELOG.

## Project Integration

Projects create focused `CLAUDE.md` files that **extend** (not duplicate) these global standards:

```markdown
# Project Development Guide

> This project extends the global CLAUDE.md standards.

## Project-Specific Standards

- **Performance**: API response p95 < 2s
- **Architecture**: External Qdrant at 192.168.1.16:6333
```

## Global Resource Catalog

> Full catalog with descriptions: See [AGENTS-AND-SKILLS.md](AGENTS-AND-SKILLS.md)

### Key Agents (`.claude/agents/`)

Code Reviewer, Security Auditor, Test Engineer, Test Writer, Test Reviewer,
Frontend Designer, Diagram Maintenance, Documentation Writer, Database Operations,
AI Engineer, Git Workflow, GitHub Workflow, DevOps Deployment, UI Testing,
API Development, OWASP Dispatch (+6 specialists), Phase Reviewer, Scope Analyzer,
Plan Validator, Project Plan Synthesizer, Research Agent, Modularization Assistant, Visual Content Generator

### Available Skills (`.claude/skills/`)

**Custom skills** (this repo):

| Skill                            | Trigger                          | Purpose                                   |
| -------------------------------- | -------------------------------- | ----------------------------------------- |
| `/git`                           | commit, PR, branch               | Full git workflow (commit + PR + branch)  |
| `/quality`                       | quality, lint, format            | Code quality checks                       |
| `/testing`                       | run tests, test suite            | Test execution with coverage              |
| `/security`                      | security, scan, audit            | Security validation                       |
| `/debug-tests`                   | failing test, test error         | Root-cause test debugging                 |
| `/handoff`                       | handoff, session end             | Session continuity document               |
| `/diagram-maintenance`           | diagram, PUML, SVG               | PlantUML updates and SVG generation       |
| `/frontend-design`               | build UI, create component       | Creative direction, UX/a11y               |
| `/phase-gate`                    | phase review, phase status       | Phase readiness evaluation                |
| `/project-planning`              | project plan, generate plan      | PVS, ADR, Tech Spec, Roadmap              |
| `/rad`                           | assumption, verify assumptions   | Assumption tagging and verification       |
| `/test-coverage`                 | coverage analysis, coverage gaps | Coverage measurement and generation       |
| `/sonarcloud`                    | sonar, quality gate              | SonarCloud issue review and fixing        |
| `/skill-creator`                 | create skill, improve skill      | Skill development and iteration           |
| `/writing`                       | writing pipeline, edit, rewrite  | Writing pipeline orchestration            |
| `/code-review`                   | review PR, PR review             | 5-agent PR review with confidence scoring |
| `/hookify`                       | create hook, prevent behavior    | Author project-level gate rules           |
| `/hookify-list`                  | list hooks, list rules           | Show all active hookify rules             |
| `/hookify-configure`             | enable hook, disable hook        | Enable or disable hookify rules           |
| `/auto-dream`                    | memory consolidation, dream      | Memory consolidation across sessions      |
| `/session-report`                | session report, usage report     | HTML session usage and cost report        |
| `/claude-md-improver`            | CLAUDE.md audit and improvement  | CLAUDE.md quality audit and updates       |
| `/claude-automation-recommender` | automation recommendations       | Scan codebase, recommend automations      |
| `/docx`                          | Word doc, .docx                  | Read, create, and edit Word documents     |
| `/pdf`                           | PDF, extract PDF                 | Read, extract, and combine PDF files      |
| `/pptx`                          | PowerPoint, slides, .pptx        | Read, create, edit PowerPoint files       |
| `/xlsx`                          | spreadsheet, .xlsx, .csv         | Read, create, and edit spreadsheets       |

**Superpowers skills** (via `.submodules/superpowers` — community-maintained):

| Skill                            | Trigger                              | Purpose                                        |
| -------------------------------- | ------------------------------------ | ---------------------------------------------- |
| `brainstorming`                  | design, plan, before implementation  | Socratic pre-implementation design             |
| `writing-plans`                  | write a plan, implementation plan    | Granular task-level plan generation            |
| `executing-plans`                | execute plan, implement plan         | Plan execution with sequential task tracking   |
| `subagent-driven-development`    | implement with agents, parallel impl | Three-subagent review pattern per task         |
| `requesting-code-review`         | request code review                  | Structured code review with SHA context        |
| `receiving-code-review`          | received review, review feedback     | Adversarial verification of review feedback    |
| `test-driven-development`        | TDD, write tests first               | TDD discipline enforcement (red/green/refactor)|
| `systematic-debugging`           | debug, investigate bug               | Root-cause-first debugging framework           |
| `verification-before-completion` | done, complete, finished             | Evidence gate before claiming completion       |
| `dispatching-parallel-agents`    | parallel, multiple problems          | Parallel subagent dispatch for independent work|
| `using-git-worktrees`            | worktree, isolated branch            | Safe worktree setup with baseline verification |
| `finishing-a-development-branch` | finish branch, merge, done coding    | Branch completion with merge/PR/discard options|
| `writing-skills`                 | author SKILL.md, write SKILL.md      | TDD-based skill authorship                     |
| `using-superpowers`              | *(auto-injected at session start)*   | Meta-skill enforcing skill-first discipline    |

> Full catalog with agent descriptions: See [AGENTS-AND-SKILLS.md](AGENTS-AND-SKILLS.md)

### Install / Update

See `README.md` for install options (two-layer `~/dev/.claude` + `setup.sh` vs. direct clone to `~/.claude`).

```bash
# Update (two-layer setup)
cd ~/dev/.claude && git pull origin main && git submodule update --remote --merge
```

## Development Philosophy

**Security First** → **Quality Standards** → **Documentation** → **Testing** → **Collaboration**

1. **Security First**: Always validate keys, encrypt secrets, scan dependencies
2. **Reuse First**: Check existing repositories before building new code
3. **Configure, Don't Build**: Prefer configuration over custom implementation
4. **Quality Standards**: Maintain consistent code quality across all projects
5. **Testing**: Maintain high test coverage and run tests before commits
6. **Collaboration**: Use consistent Git workflows and clear commit messages
