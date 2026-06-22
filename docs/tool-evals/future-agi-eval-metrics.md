---
title: "Tool Eval: Future AGI Eval Metrics (agent-learning-kit / futureagi-sdk)"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation of the Future AGI evaluation-metrics capability against this configuration, with a port-versus-run-standalone recommendation."
tags:
  - tooling
  - evaluation
  - skills
  - tools
---

**Date:** 2026-06-22
**Source:** <https://github.com/future-agi/agent-learning-kit> (HEAD a13cd0d) and
<https://github.com/future-agi/futureagi-sdk> (HEAD eef8809), both inspected 2026-06-22
**Verdict:** PORT PATTERNS (local heuristic scorers + metric taxonomy) | RUN STANDALONE ALONGSIDE (full SDK on deployed apps)

## Characterization

A dual-language (Python `ai-evaluation`, TypeScript `@future-agi/ai-evaluation`)
evaluation SDK exposing ~72 metrics across hallucination, RAG faithfulness,
agent-trajectory, function-calling, code-security, structured-output, and
LLM-as-judge categories. Stack is Python with optional local model deps
(torch, transformers, nltk, numpy) plus a thin client to the hosted
`futureagi.com` evaluation API and an OTEL trace-enrichment layer. Stated scale
target is production eval pipelines; the SDK is the highest-governance repo in
the org (full OpenSSF baseline, 7 releases, Keep-a-Changelog discipline).

## Value core vs. peripheral LOC

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core (`python/fi/evals`) | ~66,400 | Whole Python SDK; metrics + evaluator + OTEL |
| ── self-contained heuristics (`metrics/heuristics`) | 939 | string / json / similarity / aggregation; **zero API imports** |
| ── API/LLM-judge metrics | bulk of remainder | `evaluator.py`, `manager.py`, `llm_as_judges/` call hosted API or an LLM |
| Peripheral mass | n/a | TypeScript package, logo/gif assets, CLI |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| Local heuristic scorers (939 LOC) | PORTABLE | NEW `skills/llm-eval/` (no equivalent today) | FITS | High |
| Metric taxonomy (the 7-category catalog) | PORTABLE (as a checklist/standard) | `standards/` eval rubric | FITS | High |
| Hallucination / RAG model-backed metrics | FRAMEWORK-LOCKED (torch/transformers) | None directly; heavy local deps | FIGHTS | Low |
| LLM-as-judge metrics | FRAMEWORK-LOCKED (metered LLM call) | `meta-harness` scorer (deliberate use) | FIGHTS (cost lane) | Medium |
| Hosted eval API client | FRAMEWORK-LOCKED | None | FIGHTS | Low |

## Licence

Apache-2.0, no carve-outs in LICENSE or NOTICE. Clean for direct inclusion or
adaptation.

## Relationship classification

ORTHOGONAL. A Python runtime library, not Claude Code loadable content. The
*patterns* (local scorers, metric taxonomy) port into our `.claude/` tree; the
SDK itself runs alongside on apps we deploy.

## Convergent-validation notes

- The OTEL trace-enrichment layer independently mirrors our
  `observability-and-instrumentation` direction (validation, not action here;
  see the traceAI eval for the instrumentation core).
- The 7-category metric split validates that our `ai-detection-agent` covers
  only one narrow slice (AI-authorship), confirming the eval gap is real.

## Recommended actions

1. Create `skills/llm-eval/` that ports the four self-contained heuristic
   scorers (string/json/similarity/aggregation, 939 LOC) as a local, zero-cost
   scoring library. Adapt naming to our conventions; strip the `fi.` namespace.
2. Lift the 7-category metric taxonomy into a `standards/llm-output-eval.md`
   rubric, wired as a checklist into `verification-before-completion`.
3. Expose the heuristic scorers as a pluggable scorer for `meta-harness`
   (its `scorer-template.py` currently asks the user to hand-write this).
4. For hallucination/RAG/LLM-judge metrics, do **not** port: run the SDK
   standalone on deployed agent apps where the metered call is a deliberate,
   budgeted choice. Document this as a RUN STANDALONE option, not a config dep.
