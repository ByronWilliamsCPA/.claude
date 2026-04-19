# Agent Authoring Conventions

> Folder-level override: applies when editing files under `.claude/agents/`.
> Last scope wins: these rules take precedence over the global CLAUDE.md.

## Frontmatter

```yaml
---
name: <agent-name>
description: <one-line description for orchestrator routing>
model: sonnet          # haiku | sonnet | opus
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---
```

- `model`: default `sonnet`. Use `haiku` for read-only agents. Use `opus` only when deep reasoning is the primary value.
- `tools`: list only what the agent needs. Read-only agents must not include `Write`, `Edit`, or `Bash`.
- MCP tool bundles go in `mcp_config.yaml` under `tier_2_agent_bundles`, not here. See `.claude/rules/mcp-strategy.md`.

## System prompt

- First sentence: role and scope.
- State output format explicitly. For agents feeding downstream steps, require a JSON envelope with an evidence field. See `.claude/rules/supervisor.md` for envelope patterns.
- Keep under 400 lines. Reference `.claude/standards/` files rather than embedding full specs.

## Registration

After creating an agent: add it to `AGENTS-AND-SKILLS.md` and run `pre-commit run --all-files`.
