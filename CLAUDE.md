# Global Claude Development Standards

> **Status**: Active | Core Standard | **Version**: 1.4.0 | **Last Updated**: 2026-04-19
>
> Universal development standards and practices for Claude Code across all projects.

Project-specific rules that do not fit here belong in `.claude/rules/*.md`
(path-scoped where possible) or a project-local `CLAUDE.md`. Cross-cutting
reference material lives in `.claude/standards/*.md`.

## Project context

When asked about business priorities, organizational strategy, or project
decisions, read the project files first. Search `docs/`, `initiatives/`,
project root, and `CLAUDE.md` before answering. If no file covers the topic,
state what was searched and answer from training knowledge, prefixed with:
`[Not in project docs, answer from training knowledge only]`.

Do not assume organizational priorities without verifying them in the
project tree.

### Before writing any guide, doc, or standards file

Run this before drafting:

```bash
grep -rl "tier\|framework\|standard\|template" docs/ --include="*.md" 2>/dev/null | head -20
```

Read the results before writing. If an existing tier framework, standards template, or
guide structure covers the topic, align with it rather than inventing a new structure.
Common culprits: audience tier docs, platform audit checklists, contributing guides,
and ADRs that constrain the approach. Missing this search is the most common cause of
documentation rework.

### Repository structure

```text
~/dev/.claude/                    # Repo root (symlinked to ~/.claude/ by setup.sh)
├── CLAUDE.md                     # Global standards (this file)
├── AGENTS-AND-SKILLS.md          # Full agent and skill catalog
├── README.md                     # Setup and install guide
├── .claude/
│   ├── agents/                   # Specialized subagent definitions
│   │   └── CLAUDE.md             # Agent authoring conventions
│   ├── commands/                 # Slash command definitions
│   ├── skills/                   # Reusable skill workflows
│   │   └── CLAUDE.md             # Skill authoring conventions
│   ├── rules/                    # Operational rules (path-scoped)
│   ├── standards/                # Detailed specifications
│   ├── cowork/                   # Cowork session instructions
│   └── context/                  # Shared context fragments
├── docs/
│   ├── architecture/             # ADRs and system diagrams
│   ├── development/              # Code quality and workflow guides
│   ├── getting-started/          # Install, first-run, troubleshooting
│   └── reference/                # Hooks, MCP, agents, skills indexes
├── mcp/                          # MCP tool loading configuration
└── scripts/                      # MCP loading and hook utilities
```

Rules in `.claude/rules/` are path-scoped where possible; they apply only when
Claude is editing files under the path specified in the rule header. Standards
in `.claude/standards/` are full specifications referenced by the rules.

## Code quality

When SonarCloud or linting tools flag issues, fix the actual issue. Never
propose `# noqa`, `# type: ignore`, `pytest.mark.skip`, `--no-verify`, or CI
bypass flags as the solution. The exceptions are vendored or third-party code
that cannot be changed, and suppressions paired with a tracking reference
(ticket number or open issue) expected to result in a proper fix.

> Python linting and function quality gates: see `.claude/rules/python.md`
> (path-scoped to Python files)
>
> Testing scope, root-cause order, and golden file protection:
> see `.claude/rules/testing.md` (path-scoped to test files)

## Git workflow

Always run `pre-commit run --all-files` before committing.

Always create worktrees inside the project at `.worktrees/<branch-slug>`. Never
create them at global or user-config paths (e.g., `~/.config/...`).

> Branch rules, worktree patterns, naming conventions:
> see `.claude/rules/git-workflow.md`
>
> Pre-commit checklist: see `.claude/rules/pre-commit.md`

## System and shell

When commands fail due to permissions (e.g., mkdir, mount), try with sudo
immediately.

When a connection error, socket failure, or service-unreachable symptom
appears, check platform-level causes first: WSL2 port forwarding rules,
Docker bridge networking, Unix socket paths, and container health. Do not
exhaust code-level fixes before ruling out the environment.

## Writing style

**Never use em-dashes (`—`) in any output.** This covers documentation, code
comments, commit messages, ADRs, rules files, standards, scripts, and all
other text. This is a hard rule, not a preference. Replace with a comma,
semicolon, colon, or restructured sentence. The `no-em-dash` pre-commit hook
(PC-011) enforces this automatically on every commit.

> Full writing rules (AI pattern blacklist, grammar authority):
> see `.claude/rules/writing.md`
>
> Writing quality thresholds: see `.claude/standards/writing-quality.md`

## Model selection

Use the right model for the task to balance quality and cost:

| Task type | Model | When |
| --- | --- | --- |
| Complex reasoning, planning, architecture | Opus 4.7 | Multi-step decisions, ADRs, deep code review |
| Standard development work | Sonnet 4.6 (default) | Most coding, editing, PR descriptions |
| Read-only exploration | Haiku 4.5 | File scanning, structure mapping, quick lookups |

In subagent configuration, set `model: haiku` for the built-in `Explore` subagent
(read-only codebase discovery). The built-in `Plan` subagent inherits the caller's
model automatically; do not set it explicitly. Agents that write code or produce
deliverables default to `sonnet` unless the task requires deep reasoning, in which
case specify `model: opus` in the agent prompt.

> Per-agent model defaults and orchestration patterns: see `.claude/rules/supervisor.md`

## Core development standards

- **Code quality**: Ruff format and lint (88 chars, PyStrict-aligned),
  BasedPyright strict mode
- **Security**: GPG/SSH key validation, `uv run pip-audit` for dependency
  scanning, encrypted secrets
- **Testing**: graduated coverage (80% line, 70% branch, 90% critical, 90% patch)
- **Git**: conventional commits, signed commits, feature branch workflow
- **Response-Aware Development**: assumption tagging and verification

> Canonical package choices: see `.claude/standards/packages.md`
>
> MCP tool loading strategy: see `.claude/rules/mcp-strategy.md`
>
> Supervisor patterns and agent assignment: see `.claude/rules/supervisor.md`
>
> Settings scope hierarchy and permissions evaluation: see `.claude/rules/settings-and-permissions.md`
>
> Approved `/loop` recipes and cost safeguards: see `.claude/rules/loop-recipes.md`

## Unfixed CVEs

When `pip-audit` finds a vulnerability that cannot be immediately resolved,
document it in `docs/known-vulnerabilities.md` using the template at
`docs/known-vulnerabilities-template.md`. Never suppress pip-audit output
without a documented entry. Review quarterly. No entry ages past 60 days
without reassessment. The OpenSSF release gate blocks releases for any
vulnerability older than 60 days regardless of reassessment status.

## Response-Aware Development (RAD)

Tag assumptions that could cause production failures using `#CRITICAL`,
`#ASSUME`, and `#EDGE` comment markers paired with `#VERIFY` instructions.
Mandatory categories: timing dependencies, external resources, data integrity,
concurrency, security, payment/financial.

> Full tagging syntax, verification workflow, and examples:
> see `docs/response-aware-development.md`

## OpenSSF baseline

Required files in every project: `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
`CHANGELOG.md`, `README.md`.

Before any release: CHANGELOG updated, no vulnerabilities older than 60 days,
tests pass above 80% coverage, version tag follows SemVer. New features:
write tests first, document security implications, update CHANGELOG.

## Scoped context

CLAUDE.md operates at three scopes: global (`~/.claude/CLAUDE.md`), project
(`./CLAUDE.md`), and folder (`./src/CLAUDE.md`). Last scope wins on conflicts.

When working in a project that has subdirectories with distinct conventions
(e.g., `src/api/`, `src/components/`, `workers/`), proactively suggest creating
folder-level CLAUDE.md files to scope rules to those paths. Keep them focused:
one or two overrides per file, not a full restatement of global rules.

## Development philosophy

**Scope tracing (phased projects)**: every task must trace to a phase
acceptance criterion; use `/phase-gate` to verify phase readiness before
closing a phase.

## Compact Instructions

This section guides the summarization step when context is compacted. CLAUDE.md
is the only component guaranteed to survive compaction intact, content
explicitly listed here is what the summarizer should preserve.

When compacting, always preserve:

- **File paths with line numbers** for any files mentioned in the current task
- **Error messages verbatim**, do not paraphrase error text
- **Architecture decisions with reasoning**, not just "we chose X" but why
- **Current test state**, pass/fail counts and specific failing test names
- **Active branch and uncommitted changes**, branch name, staged files, notable unstaged work
- **Decision rationale** for anything where "we chose X over Y" was discussed
- **User-specific corrections** the user made during the session ("no, do it this way instead")

Do not preserve:

- Tool call logs or raw output (summarize the conclusion)
- Exploratory detours that did not inform the final approach
- Generic restatements of the user's request

## Global resources

Full agent catalog, skill catalog, and install instructions:
see `AGENTS-AND-SKILLS.md` and `README.md` at the repo root.

## Task observation

At the start of any task-oriented session (any interaction where you will
use tools and produce deliverables), invoke the task-observer skill before
beginning work.

When loading any skill, check the observation log for OPEN observations
tagged to that skill at ~/.claude/skill-observations/log.md.
Apply their insights to the current work before beginning.

Available skills are listed in
~/.claude/skill-observations/available-skills.md
(regenerated each session start). Use this file when the task-observer
skill references <available_skills>.
