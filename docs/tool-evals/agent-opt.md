---
title: "Tool Eval: agent-opt"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation of the future-agi agent-opt prompt-optimization library against this configuration, with a port recommendation into meta-harness."
tags:
  - tooling
  - evaluation
  - skills
  - optimization
---

**Date:** 2026-06-22
**Source:** <https://github.com/future-agi/agent-opt> (HEAD b28657e), inspected 2026-06-22
**Verdict:** PORT PATTERNS

## Characterization

A small, focused Python library for automated prompt optimization. It implements
six named algorithms (Random Search, Bayesian/Optuna, Meta-Prompt, PromptWizard,
ProTeGi, GEPA) that iterate a prompt against any evaluator/metric, driving LLM
calls through LiteLLM. Stack is pure-Python with pydantic, optuna, and numpy;
the only metered coupling is the LLM generator. Stated purpose is closing the
prompt-tuning loop; scale target is per-workflow optimization runs.

## Value core vs. peripheral LOC

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core (`src/fi/opt`) | 2,831 | 6 optimizers + base ABCs + generators + datamappers |
| ── the 6 optimizer algorithms | ~1,800 | framework-free search logic |
| ── `generators/litellm.py` | small | the only hosted/metered surface |
| Peripheral mass | n/a | notebook examples, logo/gif, tests |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| 6 optimizer algorithms | PORTABLE | `meta-harness/references/building-blocks.md` | FITS | High |
| `BaseGenerator` / `BaseMapper` / `Evaluator` ABCs | PORTABLE | `meta-harness` interfaces | FITS | High |
| `early_stopping` util | PORTABLE | `meta-harness` Pareto loop | FITS | Medium |
| `generators/litellm.py` | FRAMEWORK-LOCKED (metered) | None; swap for subscription-lane generator | FIGHTS | Low |

## Licence

Apache-2.0, no carve-outs. Clean.

## Relationship classification

ORTHOGONAL. A Python library, not loadable content. The algorithms port directly
into the existing `meta-harness` skill as named building blocks.

## Coupling caveat

The six optimizers import `litellm` directly (for token/cost typing), not only
through the `BaseGenerator` ABC. The ABC still abstracts the actual `generate()`
call, so porting means: keep the algorithm bodies, replace the litellm generator
with a subscription-lane generator (in-session Claude subagent), and strip the
litellm type references. This is a half-day adaptation, not a rewrite.

## Convergent-validation notes

`agent-opt` and our `meta-harness` independently converged on the same shape:
a frozen model, a swappable generator, a pluggable evaluator, and an iterative
search keeping the best candidate. `agent-opt` optimizes the *prompt*;
`meta-harness` optimizes the *scaffold*. They are complementary halves of the
same loop, which is strong validation that our meta-harness design is sound.

## Recommended actions

1. Port the six algorithm bodies into `meta-harness/references/building-blocks.md`
   as documented proposer strategies (ProTeGi and GEPA are the highest-value
   additions; Bayesian/Optuna needs the optuna dep noted as optional).
2. Reuse the `BaseGenerator` / `Evaluator` ABC shape to formalize meta-harness's
   currently-implicit interfaces.
3. Swap the litellm generator for an in-session Claude subagent generator so the
   optimization loop rides the flat subscription, not the metered Provider API
   (per `rules/mcp-strategy.md` cost lanes).
4. Cross-link this with `skills/llm-eval/` (see future-agi-eval-metrics eval) so
   the optimizer's evaluator slot has a ready local scorer.
