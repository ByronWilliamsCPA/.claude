---
title: "Tool Eval: simulate-sdk"
schema_type: common
status: published
owner: core-maintainer
purpose: "Evaluation of the future-agi simulate-sdk agent-simulation library against this configuration, with a run-standalone recommendation and a persona-harness concept port."
tags:
  - tooling
  - evaluation
  - testing
  - automation
---

**Date:** 2026-06-22
**Source:** <https://github.com/future-agi/simulate-sdk> (HEAD 1875fa3), inspected 2026-06-22
**Verdict:** RUN STANDALONE ALONGSIDE (the library) | PORT PATTERNS (the persona-harness concept, minor)

## Characterization

A Python SDK for persona-driven, multi-turn simulation testing of voice and text
AI agents. Voice paths run over LiveKit (WebRTC); text paths orchestrate direct
provider calls (OpenAI, Anthropic, Gemini, LangChain, custom). Results feed the
`ai-evaluation` SDK. Stack is compact Python (~2,244 LOC in `fi/`) with a hard
LiveKit dependency (11 import sites) and a hosted-API touch (6 files). Stated
purpose is enterprise agent simulation; scale target is pre-production
conversational QA.

## Value core vs. peripheral LOC

| Segment | LOC | Notes |
| --- | --- | --- |
| Value core (`fi/`) | 2,244 | runner, wrappers, persona orchestration |
| ── voice path | subset | requires LiveKit + Deepgram credentials |
| ── persona/runner logic | subset | the conceptually portable part |
| Peripheral mass | n/a | docs/, examples/, banner/gif, requirements.txt + poetry.lock |

## Candidate element table

| Element | Portable? | Maps to our gap | Fits delivery model? | Value-to-effort |
| --- | --- | --- | --- | --- |
| Persona-driven multi-turn test harness (concept) | PORTABLE (as a pattern) | testing family (no conversational-sim equivalent) | FITS (as a skill) | Medium |
| Text-agent runner | FRAMEWORK-LOCKED (provider SDKs) | None | FIGHTS | Low |
| Voice path | FRAMEWORK-LOCKED (LiveKit daemon) | None | FIGHTS (needs daemon) | Low |

## Licence

Apache-2.0, no carve-outs. Clean.

## Relationship classification

ORTHOGONAL. A runtime test library, not loadable content. Only the persona-harness
*idea* ports; the implementation is provider- and LiveKit-bound.

## Convergent-validation notes

simulate-sdk fills a slot our testing family (`test-engineer`, `test-writer`,
`ui-testing-agent`) does not cover: multi-turn conversational simulation under
adversarial personas. This confirms the gap rather than supplying loadable code.

## Recommended actions

1. Port only the concept: add a short pattern note to the testing family (or a
   thin `skills/agent-simulation` reference) describing persona-driven multi-turn
   testing, so the technique is captured even though the code is not.
2. Adopt the library as RUN STANDALONE on conversational/voice agent apps where
   LiveKit is already in the stack; do not pull it into `~/.claude`.
3. Lowest delivery-model fit of the four candidates (voice path needs a LiveKit
   daemon and a hosted-API touch). Treat as the optional, last-priority item.
