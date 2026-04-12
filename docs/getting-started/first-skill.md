---
title: "Your First Skill"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Walkthrough of triggering a Claude Code skill for the first time."
tags:
  - new_dev
  - skills
  - tutorial
  - getting_started
---

Skills are automations. A skill fires when you trigger it — usually with a slash command typed in the Claude Code prompt. It runs inside the main conversation window, uses the same context and tools as your session, and produces a deterministic result for a common workflow.

## What a Skill Is

A skill directory in `.claude/skills/` (visible as `~/.claude/skills/` after install) contains a `SKILL.md` file with instructions for a specific task. When you type a matching trigger, Claude loads those instructions and executes the workflow. Skills are fast and reliable for repeated, well-defined tasks: creating a commit, generating a PR, running a quality review.

The key difference from agents: skills run *in* the main conversation; agents run *outside* it. Skills share your session context; agents get a fresh one.

For the full taxonomy, see [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md).

## Trigger Your First Skill

The `/commit` skill (part of the `git` skill) is a good first choice. It stages and commits your changes, generates a conventional commit message, and handles the pre-commit hook cycle.

Make sure you have at least one staged or unstaged change in a repository, then type in your Claude Code session:

```text
/git commit
```

Or just describe what you want:

```text
Commit my staged changes with a conventional commit message.
```

Claude recognizes the pattern and invokes the git skill automatically.

Other good first skills to try:

| Slash command | What it does |
| --- | --- |
| `/quality` | Runs Ruff format, lint, and type checking against your changes |
| `/writing` | Runs the three-stage writing quality pipeline on a document |
| `/security` | Runs a security scan of the current codebase |
| `/session-report` | Produces a summary of what was accomplished in this session |

## What a Skill Invocation Looks Like

When a skill is triggered:

1. Claude recognizes the trigger pattern (slash command or keyword match).
2. The `Skill` tool fires the `PreToolUse` hook pipeline — specifically the planning bridge gate (if relevant) and the hookify dispatch.
3. The `SKILL.md` for the matched skill loads into the current conversation context.
4. Claude executes the skill's workflow steps using the available tools.
5. `PostToolUse` fires when the skill's tool calls complete.

The skill runs inline — you will see Claude's tool calls and output in the main conversation window in real time.

## Read the Output

Skills produce visible output in the main conversation: file edits, bash command results, formatted summaries. You can follow along as the skill works. After it completes, you can ask Claude to explain any step, adjust the result, or continue with the next task.

If a skill does not trigger when you expect it to, check:

- The trigger keyword: some skills use exact phrases (see [Skills Catalog](../reference/skills.md)).
- The planning bridge gate: if a plan is required before certain skills fire, you will see a gate message.

## Next

[Picking Agents vs Skills](picking.md) — a quick reference for when to reach for each.
