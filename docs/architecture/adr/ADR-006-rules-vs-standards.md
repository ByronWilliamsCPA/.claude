---
title: "ADR-006: Rules vs Standards Boundary"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records why .claude/rules/ and .claude/standards/ are separate with different loading semantics."
tags:
  - adr
  - decisions
  - rules
  - standards
  - architecture
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams

## Context

`.claude/rules/` and `.claude/standards/` are both directories under `.claude/`. Both contain markdown files. From a filesystem perspective they look identical. Their difference is entirely in loading semantics: and that difference is load-bearing.

**Rules** are session-injected behavior. `CLAUDE.md` at repo root contains explicit references to rule files (e.g., `> Python linting and function quality gates: see .claude/rules/python.md`). Claude Code reads `CLAUDE.md` at session start and loads the referenced rules into the system prompt. A rule file in `.claude/rules/` that is referenced from `CLAUDE.md` influences every single turn of every session where it applies. Rules are path-scoped where possible: `python.md` includes a note that it applies to Python files; `git-workflow.md` applies to git operations. But they are all loaded at session start, regardless of whether the current task is Python or git.

**Standards** are on-demand reference material. They are never referenced from `CLAUDE.md`. Nothing loads them automatically. They exist to answer the question "what is the canonical approach for X?" when a task touches X. A standard is read explicitly: either by the model when it decides to look something up, or by an agent whose prompt instructs it to consult a specific standard. Examples: `packages.md` (canonical package choices), `writing-quality.md` (prose quality thresholds), `testing.md` (coverage requirements and test patterns).

Mixing them creates two distinct failure modes:

1. **Standard mis-filed as a rule**: The content is loaded into every session's system prompt. If `writing-quality.md` were in `rules/`, its detailed quality thresholds would consume context on every coding session, every debugging session, every git operation: regardless of whether prose quality is relevant.

2. **Rule mis-filed as a standard**: The behavior silently stops firing. If `git-workflow.md` were in `standards/`, contributors could commit to main directly, skip signing, or use non-conventional commit formats, and nothing in the session would stop them.

Both failure modes are invisible to the contributor making the placement decision. A mis-filed document passes all syntax checks, renders in the docs site, and looks correct. The failure only manifests at runtime: either as unexpected context bloat or as a missing behavioral guard.

## Decision

The two directories are maintained as separate conceptual categories, not just filesystem conventions. The distinguishing criterion is a single question:

> **Must this content influence behavior in every session, from the very first turn?**

If yes: `.claude/rules/`. If no: `.claude/standards/`.

This question is intentionally conservative. A document that influences behavior in *most* sessions but not *every* session still goes in `standards/`: load it on demand in the sessions where it applies, rather than burdening sessions where it does not. The cost of an occasionally-missed lookup (a session that should have checked a standard but did not) is lower than the cost of constant context bloat.

To make a rule's scope explicit, rules files include a path-scoping note near the top (e.g., `> path-scoped to Python files`). This is documented convention, not technical enforcement: Claude Code does not filter rules by file type at load time.

## Alternatives Considered

**Single `.claude/doctrine/` directory with naming conventions** (`rule_*.md` / `std_*.md`): The naming convention carries the semantic distinction, but the loading behavior still depends on whether `CLAUDE.md` references the file. A contributor who adds a rule with the wrong prefix, or forgets to add a `CLAUDE.md` reference, creates the same silent failure as a mis-filed file. Two directories make the distinction structural, not cosmetic.

**Load everything from `.claude/` into the system prompt**: Eliminates the mis-filing failure mode by removing the distinction. Cost: every session pays the context cost of all reference material. At current file counts, this is approximately 15,000–25,000 additional tokens per session. Combined with the MCP tool load problem (see [ADR-003](ADR-003-tiered-mcp-loading.md)), this leaves insufficient context for substantive work in a 128K-token session.

**Load nothing automatically; require explicit invocation for rules too**: Eliminates context bloat completely. Cost: behavioral guards (commit signing, linting standards, security reminders) silently stop firing unless the user explicitly invokes them every session. This degrades the "always-on" quality guarantees that make the configuration useful.

## Consequences

### Positive

- Clear mental model: the directory name is the loading contract. No need to read `CLAUDE.md` to understand whether a document fires automatically.
- Mis-filing is visibly wrong to a careful reader: if a document obviously applies to all sessions (a coding standard, a security guard), it is obviously wrong to put it in `standards/`.
- The distinction scales: adding new behavioral guards goes in `rules/`; adding new reference libraries goes in `standards/`. No architectural change needed.

### Negative

- The distinction is not technically enforced. A document placed in the wrong directory passes all tooling checks. Human review of new additions to either directory is required to catch mis-filings.
- New contributors must learn the distinction before adding capability. This ADR and `docs/architecture/rules-vs-standards.md` are the required reading; without them, the two directories look interchangeable.

### Neutral

- The path-scoping note convention in rules files is social, not mechanical. It documents intent but does not prevent a rule from loading in unrelated sessions.

## References

- `.claude/rules/`: session-injected behavioral constraints
- `.claude/standards/`: on-demand reference material
- `CLAUDE.md`: the session entry point that references rule files
- `docs/architecture/rules-vs-standards.md`: narrative explanation of loading semantics
- [ADR-004](ADR-004-skill-vs-agent-boundary.md): the broader capability taxonomy (skills, agents, rules, standards)
