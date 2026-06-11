---
title: "Agent Teams Pilot"
schema_type: common
status: published
owner: core-maintainer
purpose: "Pilot pattern for replacing hub-and-spoke subagent dispatch with collaborative Claude Code agent teams for analysis work."
tags:
  - development
  - agents
---

This document sketches a pilot for using Claude Code **agent teams** to run
collaborative analysis on the interactive subscription, replacing the current
hub-and-spoke pattern (orchestrator dispatches subagents, each writes findings
independently, orchestrator merges).

## Why

Subagents have no peer edges: they cannot message each other or build on each
other's intermediate work, so analysis is sequential fan-out then merge. Agent
teams add peer messaging and a shared task list, which turns the same fan-out
into genuine collaboration (cross-checking, debate, building on a teammate's
partial result). Teams run as interactive Claude Code sessions, so they stay on
the flat subscription lane, not the metered Agent SDK credit. See
`.claude/rules/mcp-strategy.md` for the cost lanes.

## Prerequisites

- Claude Code v2.1.32 or later.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in the environment.
- `tmux` or iTerm2 for split-pane mode; any terminal works for in-process mode.
- `ANTHROPIC_API_KEY` unset in the spawning environment, so teammates inherit
  the subscription auth rather than silently routing to the metered API
  (anthropics/claude-code#39903).
- Exact slash-command syntax for creating a team, assigning tasks, and messaging
  teammates is evolving; follow the official reference at
  <https://code.claude.com/docs/en/agent-teams> rather than hard-coding it here.

## Pattern: collaborative analysis

A lead session plus N teammates, coordinated through a shared task list with
dependencies and a mailbox for direct peer messages.

1. **Lead decomposes.** The lead writes the analysis into discrete tasks on the
   shared list, marking dependencies (for example, "synthesis" depends on each
   angle's findings).
2. **Teammates claim angles.** Each teammate takes one angle (for a repo
   evaluation: one on architecture, one on licensing and coupling, one on the
   cost or delivery-model fit). Each works in its own context window.
3. **Peer cross-check (the collaborative step).** Before synthesis, each
   teammate sends its draft finding to one peer via the mailbox for a challenge
   pass. This is the edge the subagent model lacks: a teammate revises based on
   another teammate's critique, not just the lead's review.
4. **Lead synthesizes.** Once the angle tasks complete and unblock the synthesis
   task, the lead integrates and resolves any conflicts the peers flagged.

For contested questions, assign explicit adversarial roles ("argue the opposing
case," "try to disprove the other's conclusion") so the debate is structured
rather than incidental.

## Cost and limits

- Token usage runs roughly 7x a single session, drawn from subscription quota,
  not metered dollars.
- Experimental limitations to expect: `/resume` and `/rewind` do not restore
  in-process teammates, one team per lead, no nested teams, task status can lag.

## When to use which

| Need | Use |
| --- | --- |
| Independent fan-out, no peer interaction needed | Subagents (Task/Agent tool) |
| Agents must build on or challenge each other's work | Agent teams |
| A different model's opinion on one decision | zen/pal `tiered_consensus` (metered) |

## Sources

- Agent teams: <https://code.claude.com/docs/en/agent-teams>
- Cost lanes and the subscription guardrail: `.claude/rules/mcp-strategy.md`
- Agent SDK billing split (2026-06-15): <https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan>
