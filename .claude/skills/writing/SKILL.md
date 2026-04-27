---
name: writing
description: >
  Writing pipeline skill — orchestrates the seven-agent reference library pipeline for
  document drafting, editing, and quality review. Use whenever the user wants to edit or
  improve a document, draft something from an outline or bullets, adapt a document for a
  different audience, run a grammar/composition/voice/style check, check for AI patterns,
  review a draft before sending, or run the writing pipeline. Also triggers on: edit this
  document, improve this draft, draft a memo, write a client letter, rewrite for [audience],
  check my writing, style review, grammar check, document review, voice review, writing
  pipeline, does this sound like me, writing quality, AI patterns in my doc, audience
  analysis, will this land, calibrate my writing style.
---

# Writing Pipeline Skill

Orchestrates the seven-agent reference library writing pipeline. Handles all document
work — drafting, editing, audience targeting, and style calibration — by sequencing the
right agents in the right order so you never have to manage the pipeline manually.

## Invocation

```text
/writing [mode]
```

| Mode | What it does |
| --- | --- |
| `/writing edit` | Run an existing draft through Stage 1 → Stage 2 → Stage 3 |
| `/writing draft` | Generate from outline or bullets, then run the full pipeline |
| `/writing rewrite` | Transform register for a different audience, then pipeline |
| `/writing analyze` | Run audience-reaction-analyzer on a finished doc (post-pipeline) |
| `/writing calibrate` | Run style-analyzer to update style profile (one-time setup) |

When the mode is ambiguous or not specified, infer from context: a raw document → `edit`,
bullet points or an outline → `draft`, a finished doc with a new target audience → `rewrite`,
a question about whether the document will land → `analyze`.

## Routing

| Mode | Workflow file |
| --- | --- |
| `edit` | `workflows/edit.md` |
| `draft` | `workflows/draft.md` |
| `rewrite` | `workflows/rewrite.md` |
| `analyze` | `workflows/analyze.md` |
| `calibrate` | `workflows/calibrate.md` |

Read the relevant workflow file before proceeding. Each workflow contains the full
step-by-step orchestration instructions for that mode.

## Key Constants

| Constant | Value |
| --- | --- |
| Max remediation cycles | 3 |
| Reference library path | `.submodules/reference-library/` |
| Quality thresholds | `.claude/standards/writing-quality.md` |
| Behavioral rules | `.claude/rules/writing.md` |

## Agent Roster

All agents are globally installed. Invoke by name.

| Agent | Role | Pipeline position |
| --- | --- | --- |
| `document-drafter` | Generate voice-calibrated first drafts | Pre-pipeline (draft mode) |
| `tone-rewriter` | Transform register for a different audience | Pre-pipeline (rewrite mode) |
| `grammar-composition-editor` | Grammar, composition, plain language | Stage 1 |
| `document-validator` | Factual accuracy, assumptions, hallucinations, bias | Stage 2 |
| `writing-style-editor` | Voice alignment, AI pattern detection, stylometry | Stage 3 |
| `audience-reaction-analyzer` | Predict comprehension, persuasion, emotional response | Post-pipeline (analyze mode) |
| `style-analyzer` | Calibrate style profile from writing samples | Standalone (calibrate mode) |

## Stage Status Values

Each agent writes a YAML pipeline status block to its output. Check these to make
routing decisions between stages.

| Stage | Status field | Values | Action on each |
| --- | --- | --- | --- |
| Stage 1 | `stage_1_grammar.status` | PASS, NEEDS_WORK, FAIL | FAIL = stop; PASS/NEEDS_WORK = continue |
| Stage 2 | `stage_2_validation.status` | PASS, CONDITIONAL, FAIL | FAIL = stop; PASS/CONDITIONAL = continue |
| Stage 3 | `stage_3_style.status` | PASS, NEEDS_WORK, FAIL | PASS = done; NEEDS_WORK/FAIL = remediation loop |

## Scope Boundaries

Each agent owns exactly one concern. Do not ask agents to cross their boundaries:
- Stage 1 owns grammar and composition only — not facts, not voice
- Stage 2 owns facts, assumptions, and reasoning — not grammar, not voice
- Stage 3 owns voice and AI patterns only — if it notices a possible factual issue,
  it adds a "Pipeline Notes" section rather than correcting it inline
