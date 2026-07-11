---
schema_type: common
title: Context-window autocompaction and session-restart (research basis)
status: published
owner: engineering
tags: [research, analysis, performance, optimization, development]
purpose: >
  Regenerated evidence base for two decisions: (1) when Claude Code should force
  autocompaction, and (2) when it should suggest starting a fresh session. Synthesizes
  four independent deep-research passes (one in-house adversarially-verified harness
  plus three external deep-research models) with our own 595-session local
  measurement, and reconciles them into concrete, citable threshold recommendations.
  Replaces an earlier deep-research report that was lost (only a distilled trace
  survived in docs/audits/config-quality-analysis-2026-06-12.md).
---

## Scope and provenance

This doc answers two separate questions, calibrated separately:

- **Decision 1, autocompaction threshold:** at what carried-context size should a
  session force a (lossy) autocompact.
- **Decision 2, session restart:** when to abandon the session and start fresh from
  a hand-written handoff instead of compacting again.

Evidence comes from four independent research passes run 2026-06-24:

1. **In-house harness** (`Workflow: deep-research`, 103 agents, 5 search angles, 21
   sources, 87 claims extracted, 25 adversarially verified by 3-vote panels, 20
   confirmed / 5 killed). Its sources are all real and checkable.
2. **Three external deep-research reports** (commissioned from other models; stored
   under `tmp_cleanup/context/` at time of writing). Treated as data, cross-checked
   against the harness, and down-weighted where their citations could not be
   corroborated (see Credibility).

Plus our local measurement (`scripts/analyze-session-inflection.py`, 595 sessions,
mostly Opus 4.8 on a 1M window).

## Headline conclusions (where all four passes agree)

1. **Model performance degrades well before the window limit.** Effective context is
   roughly 50-65% of the advertised window (RULER), and realistic multi-fact /
   latent-association tasks degrade much earlier still, materially by 32K tokens on
   NoLiMa. Anthropic confirms the effect in its own docs, naming it "context rot" and
   framing context as a finite "attention budget" with diminishing marginal returns.
   **[high confidence, multiple independent primary sources]**

2. **Degradation and cost are governed by ABSOLUTE tokens, not percentage of the
   window.** A 1M-window model is not safe to 800K just because it can hold 800K; it
   degrades at a similar absolute token count to a 200K model on the same task. So a
   percentage-of-window trigger (the 80% default) fires far too late on large windows.
   **[high confidence as a synthesis; see caveat below]**

3. **Two different numbers, do not conflate them.** The *economic knee* (~150-200K,
   where carried context stops paying off) and the *quality cliff* (where output
   actually degrades) are separate events. The knee is an advisory "consider a clean
   break" signal; the autocompact backstop should sit at the quality cliff, which for
   Opus 4.8 is unmeasured and almost certainly well above 160K. Anthropic's own API
   compaction default is 150K input tokens (min 50K), the literature puts material
   erosion in the ~128-256K region for older/smaller models, and our local carry-ratio
   knee is median ~17% fill (~150-200K). All three describe the knee, NOT the cliff.
   Forcing a lossy compaction at the knee is wasteful (see the band analysis in E).

4. **The cost of long sessions is cumulative, not a rising per-turn baseline.** Our
   local data shows the post-compaction floor is flat (~60-70K) across successive
   compactions; per-turn cost is a sawtooth. Confirmed by all four passes. The cost
   driver is many turns re-sending/re-caching history, not an inflating floor.
   **[high, confirms local field data]**

5. **Restart (not endless compaction) once fidelity has eroded.** Compaction is lossy
   by design and recursive (later summaries flatten earlier ones), so fidelity decays
   across cycles. The restart signal is cumulative cost plus fidelity-loss symptoms,
   not a rising per-turn cost. **[high on the mechanism; the exact cycle count is a
   heuristic, see Open questions]**

## A. Performance vs context length

- **"Lost in the middle"** (Liu et al., TACL 2024, arXiv:2307.03172): U-shaped recall;
  accuracy highest when relevant info is at the start or end, degrades in the middle;
  30%+ drop moving an answer from position 1 to 10 of 20. The U-curve attenuates for
  newer/larger models on simple single-fact retrieval, so it bounds the lower end of
  the problem rather than describing current Claude behavior exactly. **[high]**
- **NIAH overstates real ability.** Needle-in-a-haystack is lexical retrieval; models
  near-saturate it. Realistic tasks tell a different story. **[high]**
- **NoLiMa** (Modarressi et al., ICML 2025, arXiv:2502.05167): removing literal lexical
  overlap, 11 of 13 long-context LLMs fell below 50% of their short-context baseline by
  32K tokens; GPT-4o fell from 99.3% to 69.7% at 32K. **[high, verified 3-0]**
- **RULER** (NVIDIA, COLM 2024, arXiv:2404.06654): multi-hop / variable-tracking /
  aggregation; effective context ~50-65% of advertised; several 128K-claimed flagships
  show ~64K effective length. **[high, verified 3-0]**
- **Chroma "Context Rot"** (2025, research.trychroma.com/context-rot): 18 frontier
  models incl. Claude 4; performance degrades with input length even on a controlled
  non-retrieval repeated-words task, isolating length itself. Vendor report (vector-DB
  interest) but methodology is controlled and independently corroborated. **[high]**
- **Anthropic-specific:** Opus 4.6 scored 76% on the 8-needle 1M MRCR v2 variant vs
  Sonnet 4.5's 18.5%, but still dropped from ~93% at 256K to 76% at 1M, so material
  absolute-token degradation persists even in the improved flagship. MRCR is synthetic
  coreference retrieval (closer to NIAH than to coding), and this is a vendor
  announcement, so it shows retrieval improved, not that peak reasoning holds to 1M.
  No public degradation curve exists for Opus 4.8 specifically. **[medium, vendor]**

**Absolute vs percentage (the one nuance):** the in-house harness's verify panel
*refuted* the strong form of "degradation is better characterized by absolute tokens
than percentage of window" when it rested on a single benchmark (1-2 vote), because no
one source generalizes cleanly across all models. The synthesis still lands on
absolute tokens, because three independent lines (Anthropic's 150K absolute API
default, our absolute-token knee, and the mechanism scaling with token count) agree.
Treat "absolute tokens" as a well-supported synthesis, not a single-paper result.

## B. Cost vs context

- **Caching multipliers** (Anthropic prompt-caching docs): cache read = 0.1x base
  input; 5-minute cache write = 1.25x; 1-hour write = 2x; output never cached. These
  were not run through the harness verify panel but match the official pricing docs and
  all three external reports. **[medium-high; reconfirm against live pricing before
  treating as load-bearing]**
- **Why earlier compaction is cost-rational:** every turn re-sends the conversation
  prefix. Even at the 0.1x cached rate, carrying ~150K tokens costs roughly $0.045/turn
  on Sonnet 4.6 ($0.30/MTok cache-read) and ~$0.075/turn on Opus ($0.50/MTok), plus a
  full re-write at 1.25x-2x whenever the 5-min/1-hour cache TTL lapses. Compacting from
  ~180K down to a ~60-70K floor cuts the per-turn carry by ~60% for all subsequent
  turns. Anthropic's cost guidance calls clearing stale context "the single most
  effective lever." **[medium-high]**
- **Local reconciliation:** our flat ~60-70K floor and sawtooth per-turn cost are
  consistent with how compaction works (raw turns replaced by a bounded summary plus
  fixed system prompt, tools, memory). Long-session cost is cumulative. **[high]**

## C. Practitioner consensus and the Claude Code config mechanism (verified live)

The two knobs are complementary, not one-replaces-the-other (verified against
`code.claude.com/docs/en/env-vars`, 2026-06-24):

- **`CLAUDE_CODE_AUTO_COMPACT_WINDOW`**: "Set the context capacity in tokens used for
  auto-compaction calculations. Defaults to the model's context window: 200K for
  standard models or 1M for extended context models. Use a lower value like `500000` on
  a 1M model to treat the window as 500K for compaction purposes. The value is capped
  at the model's actual context window. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is applied as
  a percentage of this value. Setting this variable decouples the compaction threshold
  from the status line's `used_percentage`."
- **`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`**: "Set the percentage (1-100) of the
  auto-compaction window at which auto-compaction triggers... This variable only causes
  earlier compaction when Claude Code compacts proactively: when
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is set, in cloud sessions, and on Sonnet 4.6 and
  Opus 4.6 without extended context... In other cases, such as a local session on Opus
  4.8 or any model with extended context, auto-compaction triggers when the
  conversation reaches the model's context limit. The override can only lower the
  threshold, so values above the default have no effect."

**Critical consequence:** on a local Opus 4.8 extended-context (1M) session,
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` alone does nothing; compaction fires only at the
~1M limit. To get an earlier absolute trigger you MUST also set
`CLAUDE_CODE_AUTO_COMPACT_WINDOW`. With it set, the trigger in absolute tokens =
`WINDOW * PCT/100`.

**The "400K" folklore:** the widely-repeated "Anthropic recommends a 400K window" is
NOT documented as an official recommendation. It traces to community GitHub issues
(version-specific effective-window caps and early-compaction bugs), not to vendor
guidance. Do not treat 400K as a target; it is far above the degradation/knee band.

## D. Recommendations

### Decision 1: autocompaction threshold (historical derivation; superseded by Recalibration 2026-07-11)

Treat autocompact as a **lossy backstop set at the quality cliff**, not a forced
compaction at the economic knee. Express it in absolute tokens via the
`(capped window) x percentage` construct, which is robust to Anthropic moving a
model's window up and down (the value is capped at the actual window, so the trigger
is always a safe fraction of whatever the window currently is).

**Setting (applied to `~/.claude/settings.json` 2026-06-24):**

```jsonc
"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "500000",
"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "75"
```

Resulting trigger by runtime window (trigger = `min(500000, actual_window) x 0.75`):

| Actual window | Effective (capped) window | Compaction trigger |
| --- | --- | --- |
| 1M (current Opus/Sonnet) | 500,000 | **~375K** (37.5% of 1M) |
| 200K (if a model reverts) | 200,000 | **~150K** (75% of 200K, safe headroom) |

Why ~375K and not 160K: the 595-session band analysis (section E) shows 86% of sessions
peak under ~400K and finish without ever compacting; a 160K trigger would force a lossy
compaction, at the model's least-intelligent point, on the majority of healthy sessions.
A ~375K backstop sits above the natural peak of most sessions and fires only on the
genuine long tail. It also gives Opus 4.8 room to actually use its window, which is what
the 1M is for. Tune `PCT` down only if a measured Opus 4.8 quality curve (open question)
shows degradation below 375K.

**Robustness to window changes (the cap):** `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is "capped
at the model's actual context window," and the percentage applies to the capped value.
So a 200K model can never reach 100% under this setting (trigger is always 75% of the
real window). Even if the cap ever failed, the 375K proactive trigger would be
unreachable on a 200K model and Claude Code would fall back to its default
compact-at-the-limit behavior, which is benign, not a crash. Verify once with `/context`
on a 200K session if one becomes available (see the task-observer check-back item).

### Decision 2: start a new session

The proactive nudge (CLAUDE.md "Session length", fired at the ~150K knee) offers a
graduated choice, not a single action: `/compact [instructions]` to shed stale context
in place while keeping the thread (steered, higher fidelity than the unsteered 375K
autocompact, best when continuing the same work), or `/handoff` + a fresh session (best
when switching tasks or wanting zero carried context). `/compact` sits between "keep
going" and "full restart."

Frame the restart trigger around **cumulative cost + accumulated fidelity loss**, never
a rising per-turn baseline (which our data shows is flat). Prefer `/handoff` + a fresh
session over another `/compact` when ANY of these fire, gated on a finished task unit:

1. **2 or more compaction cycles** have occurred this session (by the 2nd-3rd cycle you
   are summarizing a summary; fidelity loss compounds). Lowering the Decision-1
   threshold makes compactions frequent, so this trigger becomes active in practice.
2. **Fidelity-drift symptoms:** the agent re-asks a settled decision, re-introduces a
   fixed bug, re-reads the same files in a loop, or violates a CLAUDE.md constraint that
   held earlier in the session.
3. **Cumulative cost** crosses a budget (e.g. a STOP verdict from
   `/usage-report blocks`) AND per-turn task progress has stalled.

The handoff is the validated "re-specify cleanly to a fresh context" fix: it discards
accumulated summarization error rather than re-summarizing it again.

## E. The 595-session band analysis (2026-06-24)

Measured from local transcripts (compaction = sustained context drop >= 50K tokens).
Fill % is against each model's max window; 593 of 595 sessions are 1M, 2 are 200K. The
absolute-token column is the trustworthy axis because fill % understates sessions that
were effectively running at a 200K boundary.

- **33 of 595 sessions (5.5%) show compaction; 562 (94.5%) never do.** The 33 produced
  70 drop events.

**Dataset 1, fill % when compaction fired (70 events):** 87% cluster in the 10-20% band
at a median of ~134K absolute tokens; a tail at ~475K (3%) and ~731K (10%). The ~134K
mode is consistent with effective-200K-boundary autocompactions or manual `/compact`,
mislabeled as ~13% by 1M normalization. Observed compactions fire around ~134K absolute.

**Dataset 2, peak fill % for the 562 non-compacting sessions:** median peak ~243K (mode
in the 20-30% band); 86% peak under ~400K (6% <10%, 26% 10-20%, 36% 20-30%, 18% 30-40%);
only ~2% ever exceed ~600K.

**Implication:** a 160K forced trigger would fire on the majority (median peak 243K); a
~375K backstop sits above the natural peak of ~86% of sessions and catches only the long
tail. This is the empirical basis for the Decision-1 value. Caveat: peak fill is a usage
signal, not a quality signal, "peaked at 243K without compacting" means the session ended
before compacting, not that output stayed high quality there.

## Credibility notes

- The in-house harness cited only real, checkable sources (Chroma, NoLiMa 2502.05167,
  RULER 2404.06654, Liu 2307.03172, Anthropic primary docs).
- External report 1 (`compass_artifact_...`) leaned on several uncorroborated sources,
  future-dated arXiv IDs (2605.*), a named internal experiment, and exact version
  regressions asserted as verified. The harness did not surface those papers. Weight
  that report's tool-internals and citation claims lowest.
- External reports 2 and 3 were materially more careful; report 3 independently flagged
  the "400K" claim as unverified, which our live doc check confirmed.

## Open questions (what to measure next)

1. **Opus 4.8 degradation curve.** Verified data exists for Opus 4.6 (76% at 1M); if
   4.8 retains more usable context, the 160K trigger could be relaxed. Measure a
   controlled solve-rate-vs-carried-context curve on our own model and task mix.
2. **Compactions before fidelity collapse.** The "2-3 cycles" restart trigger is a
   reasoned heuristic; no source quantifies the quality-decay-per-compaction curve.
   Probe known facts/decisions after each compaction to find the real cliff.
3. **A/B the threshold and the restart rule** (e.g. 120K vs 160K vs 260K triggers;
   continue-compacting vs hand-off-restart after the 2nd compaction) on matched coding
   tasks, logging test pass rate, total tokens, and re-work rate.
4. **Reconfirm cache multipliers** against current pricing before citing the cost math
   as load-bearing.

## Recalibration 2026-07-11

Both thresholds were lowered on user request: handoff nudge 150K -> 100K, autocompact
backstop 375K -> 250K (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 75 -> 50, same
`CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000`). This is a **policy override, not a
re-derivation**: the 595-session band analysis in section E is unchanged (86% of
sessions still peak under ~400K), and no new measurement motivated the change. Applying
that same band breakdown (section E: 6% under 10%, 26% 10-20%, 36% 20-30%, 18% 30-40%) to
the new 250K backstop rather than the original 375K puts autocompaction in reach of
roughly half of sessions, not only the long tail Decision 1 describes for 375K; the
2026-07-11 numbers are intentionally more aggressive on top of the same evidence, not
equally conservative at a lower absolute value. The trigger was that sessions were still
frequently exceeding the ~150K soft nudge despite
the advisory text in CLAUDE.md, because that nudge was pure prose the assistant had to
notice and act on; there was no mechanical check. The user chose a tighter operating
point rather than waiting for the nudge to be noticed more reliably at the old value.

Alongside the number change, a `UserPromptSubmit` hook (`scripts/session-length-nudge.py`,
documented in `docs/development/session-length-trigger.md` "Mechanical enforcement") was
added so the handoff nudge is now mechanically checked every turn instead of depending
solely on the assistant reading `/context`. This does not change the empirical basis for
either number, only how reliably the (lower) handoff-nudge threshold is enforced.

Anyone revisiting these thresholds later should treat the original 150K/375K values and
their justification (section D) as still empirically sound; the 2026-07-11 numbers are a
deliberately tighter choice on top of that evidence, not a contradiction of it.

## Related

- `docs/development/session-length-trigger.md` (the interim trigger band this supersedes
  for the absolute-token recommendation, and the mechanical-enforcement hook)
- `scripts/analyze-session-inflection.py` (the local measurement: carry-ratio knee and
  compaction counting)
- `scripts/session-length-nudge.py` (mechanical handoff-nudge enforcement, added
  2026-07-11)
- `docs/audits/config-quality-analysis-2026-06-12.md` (surviving trace of the lost report)
