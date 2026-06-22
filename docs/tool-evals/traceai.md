---
title: "Tool Eval: traceAI"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation of the future-agi traceAI OpenTelemetry instrumentation library against this configuration, with a run-standalone recommendation and a span-schema concept port."
tags:
  - tooling
  - evaluation
  - observability
  - monitoring
---

**Date:** 2026-06-22
**Source:** <https://github.com/future-agi/traceAI> (HEAD c624d4b), inspected 2026-06-22
**Verdict:** RUN STANDALONE ALONGSIDE (the library) | PORT PATTERNS (the span schema)

## Characterization

An OpenTelemetry-native tracing library that instruments LLM calls, agent
decisions, retrieval steps, and tool invocations as standard OTEL spans across
56 framework integrations in four languages (Python, TypeScript, Java, C#). It
exports to any OTLP backend (Datadog, Grafana, Jaeger, or Future AGI's
collector). Stack is Python-dominant (~73k LOC value core) with per-framework
instrumentor packages. Stated purpose is vendor-neutral AI observability; scale
target is production agent fleets. Strong governance (full OpenSSF baseline,
disciplined emoji-categorized changelog), but CI is effectively absent: the test
suite (31 Python files) is not run by any workflow.

## Value core vs. peripheral LOC

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core (`python/`) | ~72,900 | core `fi_instrumentation` + 56 framework instrumentors |
| Peripheral mass | n/a | java/, csharp/, typescript/, docs/, logo/gif |
| **Total (Python)** | ~72,900 | |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| OTEL span schema / semantic conventions for AI | PORTABLE (as a spec) | `skills/observability-and-instrumentation` | FITS | High |
| `fi_instrumentation` core | FRAMEWORK-LOCKED (OTEL runtime) | None (config repo); standalone on apps | FIGHTS-as-config / standalone value | Medium |
| 56 framework instrumentors | FRAMEWORK-LOCKED | None | FIGHTS-as-config | Low |

## Licence

Apache-2.0, no carve-outs. Clean.

## Relationship classification

ORTHOGONAL. A runtime instrumentation dependency for deployed apps, not Claude
Code config. It is not meant to live in `.claude/`; its value is standalone on
the agent apps we ship, where it pairs with `usage-report` for cost attribution.

## Convergent-validation notes

traceAI's OTEL-first approach validates the design stance of our
`observability-and-instrumentation` skill, which currently prescribes
instrumentation without supplying the concrete AI-span schema. traceAI supplies
exactly that schema.

## Recommended actions

1. Port traceAI's AI-span semantic conventions (the span attribute names for
   LLM call / retrieval / tool / agent-decision) into
   `skills/observability-and-instrumentation` as the concrete schema that skill
   currently lacks. This is a documentation port, not a code dependency.
2. Adopt the library itself only as a RUN STANDALONE choice on real deployed
   agent apps (e.g., the apps built under our project work), not as anything in
   `~/.claude`. Document its CI gap as an adoption risk: pin a known-good
   version and run its tests yourself before depending on it.
3. Do not submodule. It is a category mismatch with our loadable-content tree.
