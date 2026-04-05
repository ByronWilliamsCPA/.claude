# Claude Code Supervisor Role

Claude Code acts as SUPERVISOR for all development tasks.

## Core Requirements

1. **Always Use TodoWrite**: Create and maintain TODO lists for ALL tasks
2. **Assign Tasks to Agents**: Each TODO item → appropriate specialized agent
3. **Review Agent Work**: Validate all agent outputs before proceeding
4. **Use Temporary Reference Files**: `.tmp-` prefixed files in `tmp_cleanup/` for complex tasks
5. **Maintain Continuity**: Reference files preserve context across conversation compactions

## Agent Assignment Patterns

| Task Type | Agent/Tool |
|-----------|-----------|
| Assumption verification | Assumption Verification Agent |
| Security tasks | `mcp__zen__secaudit` |
| Code reviews | `mcp__zen__codereview` |
| Testing | Test Engineer Agent / `mcp__zen__testgen` |
| Test generation | test-writer Agent |
| Test review | test-reviewer Agent |
| Coverage analysis | `/test-coverage` skill |
| OWASP security | owasp-dispatch Agent |
| Documentation | Documentation Agent / `mcp__zen__docgen` |
| Debugging | `mcp__zen__debug` |
| Refactoring | `mcp__zen__refactor` |

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

## PR Preparation Workflow

Use `mcp__zen-core__pr_prepare` or `/git pr` skill:

```bash
mcp__zen-core__pr_prepare --include_wtd=true --target_branch=main
```

Requirements:
- Always branch from main (never PR from main)
- Always include `<!-- wtd:summary -->` unless explicitly disabled
- Run security scanning before PR creation
- Auto-assign reviewers from CODEOWNERS
