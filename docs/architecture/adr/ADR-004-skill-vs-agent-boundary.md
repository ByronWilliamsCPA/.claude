---
title: "ADR-004: Skill vs Agent Boundary"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Records when a capability should be a Skill, an Agent, a Rule, or a Standard."
tags:
  - adr
  - decisions
  - agents
  - skills
  - dispatch
---

> **Status**: Accepted
>
> **Decision date**: 2026-04-11
>
> **Deciders**: Byron Williams

## Context

The repo provides four mechanisms for extending Claude's behavior:

1. **Agents** — files in `.claude/agents/`. Invoked explicitly via the `Agent` tool with `subagent_type`. Run in a fresh context with their own tool restrictions. Best for multi-step, domain-isolated work.
2. **Skills** — directories in `.claude/skills/`. Invoked via the `Skill` tool, usually triggered by a keyword or slash command in the user's prompt. Best for short, deterministic automations.
3. **Rules** — markdown files in `.claude/rules/`. Loaded into every session's system prompt via `CLAUDE.md` references. Best for behaviors that must influence every turn.
4. **Standards** — markdown files in `.claude/standards/`. Never auto-loaded. Read on demand when a task calls for reference material. Best for canonical reference that should not bloat the system prompt.

Misclassifying a capability causes real problems:

- A **skill that should be an agent** fires automatically when keywords match, without the explicit invocation that a multi-step, high-stakes task warrants.
- An **agent that should be a skill** requires knowing the exact `subagent_type` string; simple automations that should be one-click become multi-step invocations.
- A **rule that should be a standard** bloats every session's system prompt with content that is only relevant for specific tasks.
- A **standard that should be a rule** means the behavior silently never fires — the document sits in `standards/` but nothing ever loads it into the session context.

This ADR documents the classification rubric and absorbs the flat-directory convention for agents, since that is an implementation detail of the same decision.

## Decision

### Classification rubric

Use this table to classify any new capability:

| Question | Points to |
| --- | --- |
| Must it fire automatically on a keyword or slash command? | Skill |
| Does the user need to explicitly name it to invoke it? | Agent |
| Must it shape every single conversation turn? | Rule |
| Is it reference material consulted for specific tasks only? | Standard |
| Does it involve multi-step reasoning across many tool calls? | Agent |
| Is it a one-shot transformation (commit, format, review)? | Skill |
| Does it need isolated tool restrictions (read-only, no Bash)? | Agent |
| Does it run best inside the main conversation window? | Skill |

In plain English:

- **Skills** are automations. They are fast, deterministic, and triggered by user intent signals (keywords, `/commands`). Examples: `/commit`, `/quality`, `/git pr`.
- **Agents** are specialists. They work in isolation with a narrowly scoped tool set. The main conversation delegates to them; they report back. Examples: `code-reviewer`, `security-auditor`, `test-engineer`.
- **Rules** are behavioral constraints. They must be active from turn one. Examples: `python.md` (linting standards), `git-workflow.md` (branch naming), `supervisor.md` (agent assignment patterns).
- **Standards** are reference libraries. Nothing loads them automatically; they are read when a specific task requires them. Examples: `packages.md` (canonical package choices), `writing-quality.md` (quality thresholds).

### Flat agent directory with domain prefixes

All 43 agents live in a single flat directory: `.claude/agents/`. There is no nesting (`security/`, `testing/`, etc.).

Reason: `setup.sh` creates a single symlink `~/.claude/agents/ → ~/dev/.claude/.claude/agents/`. Supporting nested directories would require either recursive symlink creation or a different install topology. The flat layout also makes `ls ~/.claude/agents/` a complete inventory at a glance.

Domain grouping is preserved via file name prefixes: `owasp-web.md`, `owasp-api.md`, `owasp-llm.md` cluster together alphabetically. The prefix convention is a social norm, not enforced by tooling — but deviating from it makes the catalog harder to scan.

## Alternatives Considered

**Everything as agents**: Agents require explicit invocation with a `subagent_type` parameter. Simple automations like commit message generation would require knowing the exact agent name and constructing an explicit tool call. The ergonomic advantage of skills (keyword trigger, slash command, one keystroke) is lost entirely.

**Everything as skills**: Skills auto-trigger on keyword matches. Multi-step, high-stakes operations (security audit, full test suite generation, database migration review) would fire without explicit user confirmation. Auto-triggering a security audit on every mention of "vulnerable" is noisy and potentially misleading.

**Nested agent directories**: `.claude/agents/security/`, `.claude/agents/testing/`, etc. `setup.sh` would need to either symlink each subdirectory individually or recurse into the directory tree. Neither is simpler than a flat directory with a prefix convention. Nesting also makes the catalog less discoverable — `ls ~/.claude/agents/` stops being a complete inventory.

**Single `.claude/doctrine/` directory for rules and standards**: Removes the semantic distinction between session-injected behavior and on-demand reference. A contributor who mis-files a standard in the rules directory bloats every session. A contributor who mis-files a rule in the standards directory silently breaks the intended behavior. Two directories make the distinction legible.

## Consequences

### Positive

- Contributors have an explicit rubric for classification. The question "should this be a skill or an agent?" has a documented answer.
- Flat agent directory means `ls ~/.claude/agents/` is always a complete catalog. No traversal needed.
- The rules/standards split prevents accidental context bloat from mis-filed reference material.

### Negative

- Some capabilities genuinely span the boundary (e.g., a workflow that starts as a skill but escalates to agent delegation). These require careful SKILL.md authoring to document the handoff.
- The prefix convention for agent files is unenforced. Over time, contributors may add agents without prefixes, making the catalog harder to scan. A linting rule enforcing the prefix convention would close this gap.

### Neutral

- The `AGENTS-AND-SKILLS.md` file at repo root is the canonical human-readable catalog. It must be updated manually when agents or skills are added. Future tooling (via `tools/gen_tools_catalog.py`) can automate this.

## References

- `.claude/rules/supervisor.md` — agent assignment patterns for common task types
- `.claude/agents/` — the 43 agent files
- `.claude/skills/` — the 40+ skill directories
- `.claude/rules/` — session-injected rules
- `.claude/standards/` — on-demand reference standards
- `AGENTS-AND-SKILLS.md` — the canonical agent and skill catalog
- `docs/architecture/agent-dispatch.md` — narrative explanation with embedded diagram
- `docs/architecture/diagrams/agent_skill_dispatch.svg` — runtime dispatch flow diagram
- [ADR-006](ADR-006-rules-vs-standards.md) — the rules vs standards loading semantics decision
