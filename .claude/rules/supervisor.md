# Claude Code Supervisor Role

Claude Code acts as SUPERVISOR for all development tasks.

## Core Requirements

1. **Always Use TodoWrite**: Create and maintain TODO lists for ALL tasks
2. **Assign Tasks to Agents**: Each TODO item → appropriate specialized agent
3. **Review Agent Work**: Validate all agent outputs before proceeding
4. **Use Temporary Reference Files**: `.tmp-` prefixed files in `tmp_cleanup/` for complex tasks
5. **Maintain Continuity**: Reference files preserve context across conversation compactions

## Agent Assignment Patterns

| Task Type | Agent/Tool | Type |
| --------- | ---------- | ---- |
| Codebase exploration (read-only) | Explore subagent (built-in, haiku, read-only) | Agent |
| Pre-planning structure | Plan subagent (built-in, inherits model, read-only) | Agent |
| Assumption verification | `/rad` skill | Skill |
| Security tasks | security-auditor agent (`zen.secaudit` auto-loaded) | Agent |
| Code reviews | code-reviewer agent (`zen.codereview` auto-loaded) | Agent |
| Requesting a structured review | `requesting-code-review` skill | Skill |
| Responding to review feedback | `receiving-code-review` skill | Skill |
| Testing | test-engineer agent (`zen.testgen` auto-loaded) | Agent |
| Test generation | test-writer agent | Agent |
| Test review | test-reviewer agent | Agent |
| Coverage analysis | `/test-coverage` skill | Skill |
| OWASP security | owasp-dispatch agent | Agent |
| Documentation | documentation-writer agent (`zen.docgen` auto-loaded) | Agent |
| Debugging | `systematic-debugging` skill | Skill |
| Debugging failing tests | `/debug-tests` skill | Skill |
| Refactoring | `/quality` skill + code-reviewer agent | Skill + Agent |
| Multiple independent problems | `dispatching-parallel-agents` skill | Skill |
| Implement task with review loop | `subagent-driven-development` skill | Skill |

> **MCP tool loading**: Tools marked "auto-loaded" activate via Tier 2 bundling when the agent is invoked. See `.claude/rules/mcp-strategy.md` for details.
>
> **Built-in subagents**: `Explore` (haiku, read-only: no Edit/Write/Bash) and
> `Plan` (inherits model, read-only) are native Claude Code subagent types. Invoke
> via `subagent_type: "Explore"` or `subagent_type: "Plan"` in the Agent tool.
> Use Explore before dispatching a general-purpose agent for codebase searches.
> Use Plan for implementation strategy before any code is written.

## Temporary Reference Files

Create when:

- TODO list has >5 items
- Complex implementation details need preservation
- Multi-step workflows span multiple conversation turns

**Naming**: `tmp_cleanup/.tmp-{task-type}-{timestamp}.md`

## Every Development Task Pattern

1. **Create TODO List** via TodoWrite
2. **Assign** each item to the most appropriate agent
3. **Track Progress**: mark in_progress → completed after validation
4. **Reference Files**: create `.tmp-` files for complex tasks immediately
5. **Validate** all agent output before marking complete

## Scope Tracing (Phased Projects)

When working inside a phase of a project that has a `PROJECT-PLAN.md` and phase
acceptance criteria, every task in the TodoWrite list must map to a specific
acceptance criterion in the current phase.

Before adding a task to the list, ask: which acceptance criterion does this serve?

- If it traces clearly: add the task normally
- If it does not trace: it is out-of-scope work; either defer it or initiate a scope
  amendment before starting
- If the phase has no acceptance criteria: the project plan is incomplete; surface this
  before proceeding

Use `/phase-gate` at the end of each phase to verify all criteria are met before
closing.

## PR Preparation Workflow

Use the `/git pr` skill:

```bash
/git pr
```

Requirements:

- Always branch from main (never PR from main)
- Always include `<!-- wtd:summary -->` unless explicitly disabled
- Run security scanning before PR creation
- Auto-assign reviewers from CODEOWNERS

## Two-Pattern Skill Architecture

Skills have two invocation patterns. Choosing the wrong pattern wastes either
context window (agent-preloaded on an irrelevant skill) or latency (tool-invoked
on a skill consulted every turn).

### Pattern A: Agent-preloaded skills

The skill body is injected into an agent's system prompt at startup via `skills:`
frontmatter. The agent has the knowledge from turn one, no per-turn tool call needed.

Use when: the skill is a reference guide or checklist the agent consults repeatedly
(e.g., a security-auditor agent loading its owasp rules).

Frontmatter pair:

- On the agent: `skills: ["skill-name"]`
- On the skill: `user-invocable: false` (prevents accidental direct invocation)

### Pattern B: Tool-invoked skills

The orchestrator calls `Skill("skill-name")` at a specific workflow point. The
skill runs statelessly and returns output.

Use when: the skill is a complete workflow used once per task and the caller needs
the output before proceeding (e.g., `/commit`, `/quality`, `/git pr`).

### Orchestration roles

| Layer | Role | Example |
| ----- | ---- | ------- |
| **Command** | User interaction point; receives intent, dispatches | `/rad-verify-pipeline` |
| **Agent** | Domain specialist; preloaded context + tool restrictions | security-auditor |
| **Skill** | Stateless output generator; called once per invocation | owasp-dispatch |

Commands invoke agents; agents invoke skills. Skills do not invoke agents. See
[ADR-004](../docs/architecture/adr/ADR-004-skill-vs-agent-boundary.md) for the
full classification rubric.

### Current adoption status (2026-04-11)

Pattern B is used exclusively. Pattern A is recommended as a pilot for the two
highest-invocation agents (security-auditor + owasp-dispatch) before wider adoption.
Mass `skills:` frontmatter edits are deferred.

Source: Thariq on skills, Mar 17 2026: <https://x.com/trq212/status/2033949937936085378>

## Pre-Planning Codebase Discovery

Before writing any implementation plan (whether via `writing-plans`, inline, or
the Plan built-in subagent), run a read-only discovery pass using the built-in
**Explore** subagent.

Required checklist:

- [ ] Search for existing implementations of the core function (Grep for the
      primary operation, not just file names)
- [ ] Identify the canonical pattern for this file type in this codebase (how
      are services structured, where do tests live, what imports are standard)
- [ ] Find the closest existing similar feature and note what it reuses
- [ ] Confirm no open TODO, FIXME, or issue already covers this scope (Grep
      for the feature keywords in `docs/` and recent commit messages)

Only after this pass should the File Structure section of any plan be written.
This prevents the plan from specifying helpers that already exist or patterns
that diverge from established conventions.
