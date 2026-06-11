# Agent Authoring Conventions

> Folder-level override: applies when editing files under `.claude/agents/`.
> Last scope wins: these rules take precedence over the global CLAUDE.md.

## Frontmatter

```yaml
---
name: <agent-name>
description: <one-line description for orchestrator routing>
model: sonnet          # haiku | sonnet | opus | fable | inherit
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---
```

- `model`: default `sonnet`. Use `haiku` for read-only agents. Use `opus` only when deep reasoning is the primary value. Use `fable` only when frontier reasoning justifies 2x Opus cost (long-horizon autonomous work, hardest problems); never as a default. Use `inherit` to pass the caller's model through (used by agents that run in subagent pipelines where the orchestrator sets the model); note that `inherit` resolves to Fable when the session runs on Fable, so prefer an explicit tier for agents whose task does not benefit.
- `tools`: list only what the agent needs. Read-only agents must not include `Write`, `Edit`, or `Bash`.
- MCP tool bundles go in `mcp/mcp_config.yaml` under `tier_2_agent_bundles`, not here. See `.claude/rules/mcp-strategy.md`.

## System prompt

- First sentence: role and scope.
- State output format explicitly. For agents feeding downstream steps, require a JSON envelope with an evidence field. See `.claude/rules/supervisor.md` for envelope patterns.
- Target: under 400 lines. Reference `.claude/standards/` files rather than embedding full specs. Agents with multiple modes or large rule sets may exceed this; keep the prompt as short as its responsibilities allow.

## Registration

After creating an agent: add it to `AGENTS-AND-SKILLS.md` and run `pre-commit run --all-files`.
