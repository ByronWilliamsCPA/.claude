---
schema_type: common
title: Session-length trigger (measurement method and calibration)
status: published
owner: engineering
tags: [usage, development, performance, configuration, analysis]
purpose: >
  Documents how the session-length triggers are measured and recalibrated. The
  decision values and the evidence behind them live in
  docs/development/context-window-autocompaction-research.md, and the root CLAUDE.md
  "Session length" block carries the operative thresholds. This doc explains the
  measurement script and how to re-derive the thresholds from local usage.
---

## What this calibrates

Two separate triggers, both expressed in absolute carried tokens (not percent of window,
which misleads on a 1M model):

1. **Handoff nudge (~100K carried tokens):** the proactive, lossless lever. At a task
   boundary past the cost knee, Claude offers `/compact` or `/handoff`. Operative text:
   root CLAUDE.md "Session length". Mechanically backed by a `UserPromptSubmit` hook,
   `scripts/session-length-nudge.py` (see "Mechanical enforcement" below); the prose
   alone previously depended on Claude noticing the count.
2. **Autocompact backstop (~250K):** the lossy fallback, set via
   `CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`.

Why absolute tokens, and why these values: see
`docs/development/context-window-autocompaction-research.md`.

## The measurement script

`scripts/analyze-session-inflection.py` reads Claude Code transcript JSONL (default glob
`~/.claude/projects/**/*.jsonl`) and, per main-thread assistant turn, computes the carried
context (`input_tokens + cache_read_input_tokens + cache_creation_input_tokens`), the fill
against the per-model window, the output tokens, and the carry ratio (context per output
token). From those it derives two signals:

- **Carry-ratio knee (the ~100K nudge signal).** The fill at which the smoothed carry
  ratio first reaches a multiple of its early-session baseline, where a turn starts
  carrying a lot of context for little new output. Across 595 local sessions the knee sits
  at a median of ~17% of a 1M window (~150-200K tokens), p25 13% / p75 20%.
- **Compaction count (the restart signal).** A compaction leaves no transcript marker, so
  the script detects it as a sustained context drop (>= 50K tokens that does not recover
  the next turn) and counts those per session. This supersedes an earlier draft that left
  compaction detection unconfirmed; the script now counts via the drop heuristic and does
  not depend on a marker format.

Run it:

```bash
python3 scripts/analyze-session-inflection.py                 # default glob, per-model window
python3 scripts/analyze-session-inflection.py --min-turns 8   # skip short sessions
python3 scripts/analyze-session-inflection.py --json          # machine-readable
```

The window is auto-detected per session from the model id (1M for current Opus/Sonnet/
Fable, 200K for Haiku); `--window` overrides. A peak fill above 100% warns that the window
is wrong for that model.

## Mechanical enforcement

`scripts/session-length-nudge.py`, a `UserPromptSubmit` hook wired via `hooks.json`,
checks carried tokens on every turn against the handoff-nudge threshold
(`SESSION_LENGTH_SOFT_TARGET`, default 100,000) so the nudge no longer depends solely on
Claude noticing the count in `/context`. It reads the same usage fields as
`iter_usage()` in `analyze-session-inflection.py` from the most recent main-thread
assistant turn, and once carried tokens cross the threshold it injects a reminder each
time the session climbs into a new 50K-token band (100K, 150K, 200K, ...), tracked per
`session_id` in `~/.claude/tmp_cleanup/.session-length-nudge/`, so it fires once per band
rather than every turn. Disable with `SESSION_LENGTH_NUDGE_DISABLED=1`.

Keep the threshold constant in the script (`DEFAULT_SOFT_TARGET`) and the CLAUDE.md
"Below ~100K" bullet in sync manually; the script cannot read CLAUDE.md prose, so the
number is necessarily duplicated in both places.

## Recalibrating

Re-run periodically; the knee shifts with project size and working style:

1. Read the carry-ratio knee distribution. If the median knee has moved, update the
   CLAUDE.md nudge floor (currently ~100K) and `SESSION_LENGTH_SOFT_TARGET` in
   `scripts/session-length-nudge.py` together.
2. Review the peak-fill and compaction-count distributions. If most sessions now peak much
   higher or lower, revisit the ~250K autocompact backstop (and the
   `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` values).
3. Record the revised values and the reasoning in the research doc.

## Limitations

- The per-model window only covers the models in the script's table; an unrecognized model
  falls back to 200K with a warning, so pass `--window` for models the table does not know.
  Fill is meaningless if the window is wrong, which is why a peak above 100% warns.
- The carry ratio is noisy on planning-heavy sessions with little output; the script
  smooths and applies a minimum-turns filter, but eyeball the per-session table before
  trusting a single session's number.
- The transcript captures token usage, not wall-clock latency, so "slower responses" is
  inferred from context growth, not measured directly.
- Peak fill is a usage signal, not a quality signal: a high peak means the session ran
  long, not that output stayed high quality there.

## Related

- `docs/development/context-window-autocompaction-research.md` (evidence and decisions)
- root `CLAUDE.md` "Session length" (the operative thresholds)
- `scripts/analyze-session-inflection.py` (the measurement)
- `scripts/session-length-nudge.py` (the mechanical handoff-nudge enforcement)
