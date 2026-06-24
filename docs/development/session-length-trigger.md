---
schema_type: common
title: Session-length trigger (quantitative basis and calibration)
status: draft
owner: engineering
tags: [sessions, context, usage, handoff, calibration]
purpose: >
  Defines the quantitative basis for the CLAUDE.md "Session length" trigger that
  tells Claude when to suggest a clean break and run /handoff. Replaces pure
  self-assessment with a context-fill threshold band anchored to the 80%
  autocompact point, names the primary and secondary signals, and documents how
  to calibrate the thresholds to real inflection points in local usage with
  scripts/analyze-session-inflection.py.
---

## Why this exists

The original "Session length" guidance asked Claude to self-assess whether a
session had "grown long" from soft signals (slower responses, many tool calls).
That has no measurable anchor, so it fires inconsistently: sometimes too early
(interrupting productive work), sometimes never (drifting into a lossy
autocompact). This doc gives the trigger a quantitative basis and a way to tune
it to actual data.

## The anchor: autocompact at 80%

Autocompact is configured to fire at 80% context fill
(`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in `settings.json`). Autocompact summarizes
the conversation and discards the rest, so it is lossy by construction. A
deliberate `/handoff` before 80% produces a higher-fidelity carry-forward (the
doc plus a budgeted kickoff prompt) than letting the harness auto-summarize.
The whole trigger is therefore designed to fire the handoff offer *before* the
session reaches the autocompact point, at a natural task boundary.

## Signals

**Primary: context-fill %.** The share of the context window currently in use,
visible on the statusLine bar or via `/context`. It is the most direct proxy for
the cost-and-slowdown effect the trigger exists to manage, and it maps directly
onto the 80% autocompact anchor.

**Secondary (move the offer earlier within the band):**

- Number of distinct task units completed this session (2+ is a natural break).
- Accumulated tool-call count (a large count signals a long, busy session).
- A STOP verdict from `/usage-report blocks` (the five-hour cost circuit
  breaker from `loop-recipes.md`).

## Interim threshold band

These match the CLAUDE.md "Session length" block. They are interim defaults
chosen from the 80% anchor, not measured values; calibrate them per the next
section.

| Context fill | Action |
| --- | --- |
| Below 55% | Keep working. |
| 55 to 70%, and a task unit just finished | Offer the remedy in the same message: "Want a handoff doc and a kickoff prompt for a fresh session? (`/handoff`)". Do not force it. |
| Above 70% (nearing 80% autocompact) | Recommend the break before any new task unit. If mid-task, finish the unit, then `/handoff`. |

Two guards keep the band honest, matching the "do not start too early, do not
run forever" requirement:

- **Do not start too early:** never interrupt mid-task; gate every offer on a
  completed task unit, and never offer below 55% fill.
- **Do not run forever:** by 70% the break is a recommendation, not an offer,
  and no new task unit starts past ~70% without a handoff offer first. 80% is
  the hard ceiling where autocompact takes over.

## Calibration: finding the real inflection point

"Inflection point" here is the context-fill % at which the session stops paying
off, where the tokens carried per token of useful output start climbing
steeply. Below the knee, each turn produces meaningful output for its context
cost; above it, you are mostly re-reading and re-caching a large history for
diminishing new work.

`scripts/analyze-session-inflection.py` measures this from local transcripts:

1. It reads Claude Code transcript JSONL files (default glob:
   `~/.claude/projects/**/*.jsonl`).
2. For each assistant turn it reads `message.usage` and computes the context
   size carried (`input_tokens + cache_read_input_tokens +
   cache_creation_input_tokens`), the fill % against the window, the
   `output_tokens` produced, and the **carry ratio** (context size / output
   tokens, smoothed over a small window).
3. The inflection turn is the first turn, after an early baseline window, whose
   smoothed carry ratio reaches a multiple (default 2.0x) of its baseline. The
   fill % at that turn is the session's inflection estimate.
4. Across all qualifying sessions it reports the distribution of inflection
   fill % (p25 / median / p75) and a recommended threshold.

Run it:

```bash
python3 scripts/analyze-session-inflection.py                 # default glob + 200k window
python3 scripts/analyze-session-inflection.py --window 200000 --min-turns 8
python3 scripts/analyze-session-inflection.py ~/.claude/projects/**/*.jsonl --json
```

Read the recommendation, then update the band in CLAUDE.md "Session length" (and
the table above) so the "offer" floor sits a little below the measured p25
inflection and the "recommend" line sits near the median, keeping both under the
80% autocompact ceiling. Re-run periodically; the inflection point shifts as
project size and working style change.

## Limitations

- The window default is 200k tokens. Override `--window` for 1M-context runs;
  fill % is meaningless if the window is wrong.
- Carry ratio is noisy on planning-heavy sessions with little output; the script
  smooths and applies a minimum-turns filter, but eyeball the per-session table
  before trusting a single session's number.
- The transcript captures token usage, not wall-clock latency, so "slower
  responses" is inferred from context growth rather than measured directly.
