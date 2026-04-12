---
title: "Best-Practice Repo Review (2026-04-11)"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Index and navigation for the systematic review of shanraisshan/claude-code-best-practice vs local practices."
tags:
  - development
  - documentation
---

Systematic comparison of the external repository
[shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
against our local Claude Code practices at `/home/byron/dev/.claude`.

## Why this exists

The external repo is a citation-disciplined public teaching product covering
Claude Code concepts, runnable examples, development workflows, Boris Cherny
tips, hook configurations, and changelog-style platform tracking. A
structured comparison against our own setup (CLAUDE.md, 41 custom skills,
29 agents, hooks, submodules) surfaces blind spots and validated tactics we
can adopt without rediscovering them.

## How it was produced

1. **Exploration phase.** Two Explore subagents catalogued both repos in
   parallel to identify natural fracture lines for division of work.
2. **Parallel analysis phase.** Six general-purpose subagents were
   dispatched in parallel, each owning one thematic slice. Each subagent
   fetched its slice via `gh api`, read our local equivalents, drafted an
   analysis, ran it through Gemini 3.1 Pro for second-opinion review via
   `mcp__pal__chat`, revised based on feedback, and wrote a final
   template-conformant analysis document.
3. **Synthesis phase.** The supervisor read all six analysis documents,
   deduplicated recommendations, grouped findings into four themes, and
   produced a prioritized action table.
4. **Consensus validation phase.** The synthesis draft was reviewed in
   parallel by three models (Gemini 3.1 Pro neutral, GPT-5.2 adversarial,
   Qwen 3.5 Plus neutral) via `mcp__pal__chat`. Two additional models
   (Grok 4.1 Fast, GLM 4.5 Air) were requested but blocked by per-call
   token-budget limits. The three responding models surfaced substantive
   critical feedback that reshaped the final short list.
5. **Finalization.** The synthesis report was revised with the consensus
   feedback integrated and a consensus-adjusted 10-item short list added.

## Files in this directory

| File | Role | Length |
| --- | --- | --- |
| [README.md](README.md) | This index | short |
| [synthesis-report.md](synthesis-report.md) | **Primary deliverable.** Cross-cutting themes, prioritized action table, consensus validation, and a consensus-adjusted 10-item two-week short list | ~600 lines |
| [01-core-concepts-and-architecture.md](01-core-concepts-and-architecture.md) | Subagent 1: external `best-practice/` guides and `orchestration-workflow/` vs our CLAUDE.md + rules + standards | 164 lines |
| [02-runnable-implementations.md](02-runnable-implementations.md) | Subagent 2: external `implementation/` + `.claude/agents/` + `.claude/skills/` + `.claude/commands/` + `agent-teams/` vs our local equivalents | 421 lines |
| [03-development-workflows.md](03-development-workflows.md) | Subagent 3: external `development-workflows/` (cross-model, RPI) vs our supervisor rule + dispatching-parallel-agents + subagent-driven-development + executing-plans + writing-plans skills | 148 lines |
| [04-tips-harvest.md](04-tips-harvest.md) | Subagent 4: 76 discrete tips from Boris Cherny (6 files) and Thariq (1 file) classified against our 41 skills and 29 agents | 580 lines |
| [05-hooks-and-configuration.md](05-hooks-and-configuration.md) | Subagent 5: external `.claude/settings.json` + `.claude/hooks/` + `.codex/` vs our settings.json and hook scripts | 383 lines |
| [06-changelog-and-versioning.md](06-changelog-and-versioning.md) | Subagent 6: external `changelog/` meta-practice (tracking Claude Code platform deltas version-by-version) evaluated for adoption | 161 lines |

## How to use this review

**If you want the headline:** read the [Executive summary](synthesis-report.md#executive-summary)
of the synthesis report.

**If you want the two-week adoption plan:** jump to
[Consensus-adjusted short list](synthesis-report.md#consensus-adjusted-short-list-execute-first-within-two-weeks).
Ten items, explicitly ordered.

**If you want the full backlog:** read the
[Prioritized action table](synthesis-report.md#prioritized-action-table)
with 38 rows linked back to their source analysis.

**If you disagree with a recommendation:** read the per-chunk analysis file
referenced in the source citation column. Each recommendation traces back
to a specific external file and an evaluation against a specific local file.

**If you want to preserve authoritative external sources in our own docs:**
the [Authoritative citations preserved](synthesis-report.md#authoritative-citations-preserved)
section collects links to Anthropic official docs, Boris Cherny tweets,
community resources, and the external repo sources that back every claim.

## Scope notes

**Not covered in this review:** the external repo's `tutorial/`, `videos/`,
`presentation/`, and `reports/` directories were excluded as lowest ROI. The
synthesis report can recommend a second pass if needed.

**Not an implementation plan:** the synthesis report produces a prioritized
set of recommendations with effort estimates, not ready-to-execute code
changes. A follow-up implementation plan should be written against the
10-item short list before any code is touched.

**Not a standing audit:** this is a point-in-time snapshot dated 2026-04-11.
The external repo is updated every 1-3 days; by the time this review is
three months old, several entries will have drifted. Re-run the subagent
workflow if a significant refresh is needed.
