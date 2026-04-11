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
|-----------|-----------|------|
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

When working inside a phase of a formal project (one with a `PROJECT-PLAN.md` and
phase acceptance criteria), every task in the TodoWrite list must map to a specific
acceptance criterion in the current phase.

Before adding a task to the list, ask: which acceptance criterion does this serve?

- If it traces clearly: add the task normally
- If it does not trace: it is out-of-scope work; either defer it or initiate a scope
  amendment before starting
- If the phase has no acceptance criteria: the project plan is incomplete; surface this
  before proceeding

Use `/phase-gate` at the end of each phase to confirm all criteria are met before
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
