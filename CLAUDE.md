# Global Claude Development Standards

> **Status**: Active | Core Standard | **Version**: 1.3.0 | **Last Updated**: 2026-04-11
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
> Writing rules (no em-dashes, AI pattern blacklist, grammar authority):
> see `.claude/rules/writing.md`
>
> Writing quality thresholds: see `.claude/standards/writing-quality.md`
>
> MCP tool loading strategy: see `.claude/rules/mcp-strategy.md`
>
> Supervisor patterns and agent assignment: see `.claude/rules/supervisor.md`

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

## Development philosophy

Decision order when priorities conflict:

1. **Security first**, validate keys, encrypt secrets, scan dependencies
2. **Reuse first**, check existing repositories and skills before building new code
3. **Configure, don't build**, prefer configuration over custom implementation
4. **Quality standards**, maintain consistent code quality across projects
5. **Testing**, maintain graduated coverage, run tests before commits
6. **Scope tracing** *(phased projects only)*, every task must trace to a
   phase acceptance criterion; use `/phase-gate` to verify phase readiness

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
