---
title: "Tool Eval: claude-design-system-prompt"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation of the Trystan-SA claude-design-system-prompt skill library against our existing frontend-design tooling, with a port recommendation."
tags:
  - tooling
  - evaluation
  - skills
  - design
---

**Date:** 2026-07-07
**Source:** <https://github.com/Trystan-SA/claude-design-system-prompt> (main, commit `3c3ddb07d7aa3fef051d83608596470c95cfd8fe`, inspected 2026-07-07); user linked `claude/system-prompt.md` specifically
**Verdict:** PORT PATTERNS

## Characterization

A reverse-engineered system prompt plus 14 procedural skills that turn an LLM
into an "AI-slop-resistant" design collaborator: a 20-chapter philosophy
(content discipline, aesthetic discipline, hierarchy/rhythm, accessibility,
interaction states, system thinking, medium fidelity) paired with skills for
production (discovery, wireframe, prototype, deck, tweak panel, variations),
system extraction (design-system-extract, component-extract), and review
(accessibility, ai-slop, hierarchy/rhythm, interaction-states, polish-pass).
Ships two variants: `claude/` (subagent-parallel reviews, calibrated for
current Fable 5 / Opus 4.7-4.8 instruction-following) and `codex/` (same
content, sequential reviews, no subagents). Stack is plain markdown plus
HTML/CSS/JS examples; no build tooling. Stated scale target: any HTML-output
design task, explicitly including non-Anthropic models.

## Value core vs. peripheral LOC

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core (`claude/`) | 1,409 | `claude/system-prompt.md` + 14 `claude/skills/*.md` |
| Value core (`codex/`, near-duplicate) | ~1,350 (est.) | Same content adapted for sequential (non-subagent) execution |
| Peripheral mass | ~130 | `README.md`, `LICENSE` |
| **Total** | ~2,900 | No build tooling, no assets, no examples to strip |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| `skills/wireframe.md` | PORTABLE (pure prose) | No low-fi, 3+-variation exploration phase exists in `frontend-design/SKILL.md`'s Build mode | FITS | High |
| `skills/make-a-prototype.md` | PORTABLE (pure prose) | No named "interactive clickable prototype" mode distinct from final Build | FITS | Medium |
| `skills/generate-variations.md` | PORTABLE (pure prose) | No named hi-fi, 3+-variation-across-axes mode | FITS | High |
| `skills/polish-pass.md` (+ its 4 sub-review skills: `accessibility-audit`, `ai-slop-check`, `hierarchy-rhythm-review`, `interaction-states-pass`) | PORTABLE (pure prose) | Our `frontend-design` skill has `review`/`a11y`/`perf`/`fix` modes but no single umbrella gate that launches all four in parallel and aggregates/dedupes findings before reporting | FITS | High |
| `skills/ai-slop-check.md` detect-and-replace rule set | PORTABLE (pure prose) | Our `Anti-Patterns (NEVER Use)` section is a 7-bullet list; theirs gives ~10 named rules each with a positive default plus concrete detect/replace guidance (e.g. the `border-radius:12px` + `border-left:4px solid` "default SaaS card" tell) -- a strict upgrade in specificity | FITS | Medium-High |
| `skills/frontend-aesthetic-direction.md` | PORTABLE (pure prose) | Overlaps but sharpens our existing aesthetic guidance: "propose 4 distinct visual directions, no shared palette family, at least one off-distribution" is more concrete than what we have | FITS | Medium |
| `skills/discovery-questions.md` | PORTABLE (pure prose) | Overlaps the `brainstorming` skill's clarifying-question phase; likely redundant once scoped to design-specific questions | FITS | Low |
| `skills/design-system-extract.md`, `skills/component-extract.md` | PORTABLE (pure prose) | Overlaps `DesignSync`/`/design-sync` (Claude Design MCP), which already pulls tokens/components from a real design-system project; their version is model-driven extraction from arbitrary sources (screenshots, existing sites) rather than an MCP round-trip -- complementary, not duplicate | FITS | Medium |
| `skills/make-a-deck.md` | PORTABLE (pure prose) | No equivalent; niche (HTML slide decks) but no gap conflict either | FITS | Low-Medium |
| `skills/make-tweakable.md` | FRAMEWORK-LOCKED (assumes a host canvas that exposes a toolbar toggle and posts `{type:'__activate_edit_mode'}` via `window` message listener -- i.e., the claude.ai Design canvas) | None; we operate in Claude Code / VS Code, not the claude.ai canvas | FIGHTS | Low |
| `codex/` variant | PORTABLE but near-duplicate of `claude/` | None beyond what `claude/` already covers | n/a | Skip (redundant) |
| 20-chapter `system-prompt.md` framing itself | PORTABLE (pure prose) | Overlaps `frontend-design/SKILL.md` + `frontend-designer` agent + `.claude/rules/design.md`; adopting it wholesale would create two competing "how design work happens" systems | FITS structurally but redundant as a whole document | Low (cherry-pick chapters, don't adopt whole) |

## Licence

MIT, (c) 2026 Trystan Sarrade. Clean: no non-commercial carve-outs, no bundled
asset or font exceptions found in `README.md`. Safe for direct inclusion with
attribution preserved on any ported file.

## Relationship classification

HOMOGENEOUS LOADABLE CONTENT. The `claude/` variant is a Claude Code system
prompt plus skills directory, loaded the same way our `.claude/skills/` is.
`make-tweakable.md` is the one exception: its host-protocol phase assumes it
runs inside the claude.ai Design canvas app (an INVERTED/HOST dependency for
that one skill only), not Claude Code itself.

## Convergent-validation notes

- Both projects independently arrived at "generic AI aesthetic" as a named,
  actively-detected failure mode (their `ai-slop-check`, our
  `Anti-Patterns (NEVER Use)` section, itself sourced from
  `nextlevelbuilder/ui-ux-pro-max` per the existing attribution note in
  `frontend-design/SKILL.md`).
- Both use a parallel-subagent-review-then-aggregate pattern for design QA
  (their `polish-pass` launching 4 agents; our `ui-testing-agent` +
  `frontend-designer` split of build vs. verify).
- Both explicitly calibrate instruction phrasing to current-generation model
  behavior (their "conditions instead of quotas" note on Fable 5/Opus 4.7-4.8
  over-triggering on quota language) -- a useful independent confirmation for
  any future prompt tuning in our own agents.

## Recommended actions

PORT PATTERNS, not submodule: the whole repo's `system-prompt.md` would
duplicate our existing `frontend-design` skill + `frontend-designer` agent +
`.claude/rules/design.md` architecture rather than filling a gap, and running
two parallel "how to do design work" systems invites drift. The five
procedural skills that are missing and clean of licence/host issues are worth
adding as focused, standalone gains:

1. Add `wireframe`, `make-a-prototype`, and `generate-variations` as new named
   modes (or sibling workflow files) under `frontend-design/`, giving Build
   mode explicit low-fi and hi-fi-variation phases it currently lacks.
2. Port `polish-pass`'s parallel-four-agent umbrella structure into
   `frontend-design`'s `review` mode: launch `accessibility-audit`,
   `ai-slop-check`, `hierarchy-rhythm-review`, and `interaction-states-pass`
   concurrently via the Agent tool, then aggregate/dedupe before reporting,
   replacing the current single-pass review mode.
3. Upgrade the `Anti-Patterns (NEVER Use)` section using `ai-slop-check.md`'s
   more specific detect-and-replace rules (the named SaaS-card-border tell,
   the placeholder-imagery ordering, etc.), attributing both source projects.
4. Sharpen `frontend-aesthetic-direction` guidance with the "4 distinct
   directions, no shared palette family, one off-distribution" protocol.
5. Skip `make-tweakable.md` (wrong host environment), `discovery-questions.md`
   (redundant with `brainstorming`), the `codex/` variant (redundant with
   `claude/`), and the 20-chapter `system-prompt.md` as a wholesale adoption
   target (redundant with our existing design architecture).
6. Preserve MIT attribution (project name, author, source URL, commit) in a
   comment at the top of whichever file absorbs each ported pattern.
