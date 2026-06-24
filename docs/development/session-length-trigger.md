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
python3 scripts/analyze-session-inflection.py                 # default glob, per-model window
python3 scripts/analyze-session-inflection.py --min-turns 8   # auto-detect window from each model
python3 scripts/analyze-session-inflection.py ~/.claude/projects/**/*.jsonl --json
```

The window is auto-detected per session from the model id in the transcript
(1M for the current Opus/Sonnet/Fable models, 200K for Haiku); `--window`
overrides it. A session whose peak fill exceeds 100% prints a warning: the
window is wrong for that model and the fill numbers are not trustworthy.

Read the recommendation, then update the band in CLAUDE.md "Session length" (and
the table above) so the "offer" floor sits a little below the measured p25
inflection and the "recommend" line sits near the median. Re-run periodically;
the inflection point shifts as project size and working style change.

## Calibration finding: the knee is far below 80% on a 1M window

A first run against an Opus 4.8 session (1M-token window) put the carry-ratio
knee at roughly **15% fill** (about 150K tokens carried), with the session
peaking near 33%. That is one data point, not a calibrated band, but the
direction is unambiguous and it exposes a flaw in the 80%-autocompact anchor
above: on a 1M-context model the session becomes cost-inefficient (the knee)
near 150K tokens, which is only ~15% fill, long before autocompact at 80%
(~800K tokens) is anywhere near. Anchoring the offer to "below 80%" yields a
55 to 70% band that fires several hundred thousand tokens *after* the work
already stopped paying off.

The 55/70 band was implicitly calibrated for a ~200K window (where 55 to 70%
is ~110 to 140K tokens, near the knee). It does not transfer to a 1M window.
Two ways to fix it, to decide once real multi-session history is measured:

- **Absolute carried-context tokens (model-independent, preferred).** Trigger
  on tokens carried, not fill %: e.g. offer around 120 to 150K tokens, recommend
  by ~200K. This tracks the actual re-send cost regardless of the model's
  window, and reads directly off `/context`. It does decouple the trigger from
  the 80% autocompact anchor, which is correct: on a 1M window autocompact is
  not the binding constraint, cost-per-useful-token is.
- **Window-aware fill %.** Keep fill %, but set the band per window class
  (~12% offer / ~15% recommend on 1M; the existing ~55/70 on 200K). More
  fragile, because one fixed percentage cannot serve both Haiku (200K) and
  Opus (1M) sessions.

Until calibrated against real history, the CLAUDE.md band stays at its interim
55/70 values; treat them as a placeholder known to fire late on 1M-context
sessions, not as a measured result.

## Limitations

- The window is auto-detected per session from the model id and only covers the
  models in the script's table; an unrecognized model falls back to 200K with a
  warning, so pass `--window` for models the table does not yet know. Fill % is
  meaningless if the window is wrong, which is why a peak above 100% warns.
- Carry ratio is noisy on planning-heavy sessions with little output; the script
  smooths and applies a minimum-turns filter, but eyeball the per-session table
  before trusting a single session's number.
- The transcript captures token usage, not wall-clock latency, so "slower
  responses" is inferred from context growth rather than measured directly.
