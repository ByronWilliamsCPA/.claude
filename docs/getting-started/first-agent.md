---
title: "Your First Agent"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Walkthrough of invoking a Claude Code agent for the first time."
tags:
  - new_dev
  - agents
  - tutorial
  - getting_started
---

Agents are specialists. Each one is a self-contained prompt that runs in an isolated context with a narrowly scoped tool set. You hand an agent a task; it works on it independently and returns a result. You do not need to understand how it works internally: you just need to know when to invoke it and which one to choose.

## What an Agent Is

An agent file in `.claude/agents/` (visible as `~/.claude/agents/` after install) defines a specialist: its name, its tool restrictions, and its system prompt. When you invoke an agent via the `Agent` tool in a Claude Code session, it runs in a fresh context with only those tools. It cannot see your conversation history. It does one thing well, returns a result, and the main conversation continues.

For the full taxonomy of agents vs skills vs rules vs standards, see [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md).

## Pick a Starter Task

The `Explore` agent is a good first choice: it does read-only codebase analysis, produces a concise summary, and has no side effects. Try this task:

> "Explore this repository and give me a brief overview of how it is structured."

## Choose the Agent

Look at the [Agents Catalog](../reference/agents.md) to find the right agent for your task. For the task above, the relevant agent is `Explore`.

You can also let Claude pick: if you describe your task in the main conversation, Claude will suggest the appropriate agent from the catalog (via the supervisor patterns in `.claude/rules/supervisor.md`).

## Invoke It

In a Claude Code session, the main conversation invokes an agent using the `Agent` tool:

```text
Agent(
  subagent_type: "Explore",
  prompt: "Explore this repository. Focus on the .claude/ directory structure,
           the five submodules, and the hook pipeline. Report back in under
           300 words."
)
```

You do not type this directly: Claude generates this call when you ask it to delegate a task. But understanding the shape helps you write clearer task descriptions.

In practice, you would say something like:

> "Use the Explore agent to give me an overview of the .claude/ directory structure."

And Claude will invoke the agent on your behalf.

## What Happens During the Call

1. Claude's main conversation calls the `Agent` tool with `subagent_type: "Explore"`.
2. The `PreToolUse` hook pipeline fires (specifically the hookify dispatch: see [Hook Pipeline](../architecture/hook-pipeline.md)).
3. A fresh context window opens with the Explore agent's system prompt.
4. The agent runs its task using only the tools its frontmatter allows (`Read`, `Glob`, `Grep`, etc. for Explore: no `Write` or `Bash`).
5. The agent returns a single text result to the main conversation.
6. `PostToolUse` fires in the main conversation.
7. The main conversation resumes with the agent's result in context.

The agent cannot see your conversation history. It only sees the `prompt` you passed to it.

## Read the Result

The agent returns a single message. It will be in the main conversation window after the `Agent` tool call completes. Read it, respond if needed, and continue your session normally.

If the result is not what you expected, the most common causes are:

- The `prompt` was too vague. Add constraints: scope, output format, word limit.
- The wrong agent was chosen. Check the [Agents Catalog](../reference/agents.md) for one that fits your task better.
- The agent's tool restrictions did not allow the operations it needed. Check the agent's `tools:` frontmatter.

## Next

[Your First Skill](first-skill.md): trigger an automated workflow with a slash command.
