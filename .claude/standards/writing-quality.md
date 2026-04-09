# Writing Quality Standards

**Version:** 1.0
**Effective:** 2026-04-07
**Applies to:** All professional documents: client communications, legal drafts, analyses, reports, proposals

> This document defines the quality thresholds and pipeline architecture for the
> reference library writing agents. For behavioral rules (no em-dashes, AI pattern
> blacklist), see `.claude/rules/writing.md`. For the authoritative reference files,
> see `.submodules/reference-library/`.

---

## 1. Pipeline Architecture

Seven agents handle all document work. Run them in the sequence appropriate to the task.

### Pre-Pipeline

| Agent | Purpose | When to Use |
| --- | --- | --- |
| `style-analyzer` | Calibrate style profile from writing samples | Once per user, or when voice has evolved |
| `document-drafter` | Generate voice-calibrated first drafts from outlines or prompts | Starting a new document |
| `tone-rewriter` | Transform a finished document's register for a different audience | Same content, new audience |

### Editing Pipeline (run in order)

| Stage | Agent | Scope |
| --- | --- | --- |
| 1 | `grammar-composition-editor` | Grammar, composition, plain language, AI-mechanical patterns |
| 2 | `document-validator` | Factual accuracy, assumptions, hallucinations, bias, reasoning errors |
| 3 | `writing-style-editor` | Voice alignment, AI pattern detection, stylometry enforcement |

### Post-Pipeline

| Agent | Purpose | When to Use |
| --- | --- | --- |
| `audience-reaction-analyzer` | Predict audience comprehension, persuasion, emotional response | After Stage 3 passes, before submission |

### Standard Flows

**Editing an existing draft:**
Stage 1 → Stage 2 → Stage 3

**Drafting from scratch:**
`document-drafter` → Stage 1 → Stage 2 → Stage 3

**Re-targeting for a different audience:**
`tone-rewriter` → Stage 1 → Stage 2 → Stage 3

**Full workflow with audience check:**
Input → Generator (if needed) → Stage 1 → Stage 2 → Stage 3 → `audience-reaction-analyzer`

---

## 2. Remediation Protocol

When Stage 3 (`writing-style-editor`) rewrites text for voice, those sections MUST flow
back through Stage 1 and Stage 2 before submission:

```
Stage 3 rewrites section → Stage 1 re-checks grammar → Stage 2 re-verifies facts → Stage 3 re-approves
```

**Maximum 3 remediation cycles.** If the document has not reached PASS status after 3 cycles,
escalate to human review. Do not continue automated remediation.

---

## 3. Pass/Fail Thresholds

### Stage 1: Grammar and Composition

| Status | Criteria |
| --- | --- |
| **PASS** | No unresolved grammar errors; AI-mechanical patterns eliminated |
| **NEEDS_WORK** | Minor issues present; Stage 2 may proceed but Stage 1 must be re-run after Stage 3 rewrites |
| **FAIL** | Systematic grammar problems or uncorrected errors; do not proceed to Stage 2 |

### Stage 2: Document Validation

| Status | Criteria |
| --- | --- |
| **PASS** | 0 SUSPECT claims; ≤ 2 unverified low-risk claims; no reasoning errors; no critical assumptions unstated |
| **CONDITIONAL** | 1–3 unverified claims with low stakes; assumptions documented; no SUSPECT statistics; Stage 3 may proceed |
| **FAIL** | SUSPECT statistics without sources; universal quantifiers unqualified; fabricated entities; causation asserted without evidence |

### Stage 3: Writing Style

| Status | Criteria |
| --- | --- |
| **PASS** | 0 AI patterns; stylometry targets met; no persona drift |
| **NEEDS_WORK** | 1–3 AI patterns or minor stylometry miss; revisions in progress |
| **FAIL** | 4+ AI patterns, OR systematic persona drift across multiple sections, OR stylometry misses on 3+ metrics |

**Heightened scrutiny** applies when `ai_generated: true` is present in document metadata
(output of `document-drafter` or `tone-rewriter`). Tolerance drops from 3 instances to 0
before PASS.

### Post-Pipeline: Audience Reaction Analyzer

| Status | Criteria |
| --- | --- |
| **READY** | No HIGH-priority items; Comprehension is CLEAR or MOSTLY CLEAR; Persuasion is COMPELLING or ADEQUATE; Call to action is CLEAR |
| **NEEDS REVISION** | 1–3 HIGH-priority items, OR comprehension has SIGNIFICANT GAPS, OR call to action is VAGUE or MISSING |
| **SIGNIFICANT REWORK** | 4+ HIGH-priority items, OR persuasion is WEAK, OR emotional trajectory is MISALIGNED across multiple sections |

---

## 4. Stylometry Targets

Authoritative source: `.submodules/reference-library/writing-style/style-profile.md`

| Metric | Target | Stage 3 PASS Requirement |
| --- | --- | --- |
| Sentence length | Avg 17–22 words | Within range |
| Sentence length variation | σ ≥ 8 | Met |
| Short sentences (< 8 words) | ≥ 15% of total | Met |
| Long sentences (> 30 words) | ≥ 15% of total | Met |
| Lexical diversity (TTR) | ≥ 0.40 | Met |
| Hedge density | 5–10% of sentences | Within range |
| AI patterns | 0 instances | Met |
| Paragraph burstiness | σ ≥ 4 within each multi-sentence paragraph | 0 flat paragraphs flagged |
| Persona drift | 0 sections deviating > 1.5σ from document-wide averages | 0 sections flagged |

**Measurement accuracy**: LLMs cannot reliably compute precise σ or TTR from text alone.
Use qualitative proxies when a computation environment is unavailable. Prefer actual
measurement when a Python environment is available. See `style-profile.md` for proxy guidance.

---

## 5. Agent Scope Boundaries

Each agent owns exactly one concern. Do not cross responsibilities.

| Concern | Owner | Not Owned By |
| --- | --- | --- |
| Grammar, punctuation, composition | Stage 1 | Stages 2, 3 |
| Factual accuracy, assumptions, hallucinations | Stage 2 | Stages 1, 3 |
| Universal quantifiers as factual overclaims | Stage 2 | Stage 1 (grammar only) |
| Voice, persona, AI pattern detection, stylometry | Stage 3 | Stages 1, 2 |
| Audience comprehension and persuasion | `audience-reaction-analyzer` | Pipeline stages |

If Stage 3 notices a possible factual miss, add a "Pipeline Notes" section, do not validate
in-line. Stage 2 owns that territory.

---

## 6. Reference Library

All agent reference files live in the submodule at:

```
.submodules/reference-library/
├── writing-style/
│   ├── style-profile.md          # Stylometry targets (authoritative)
│   ├── ai-detection.md           # AI pattern blacklist (full)
│   ├── tone-voice.md             # 8 tone palettes
│   ├── plain-language-guide.md   # Federal plain language principles
│   ├── logical-fallacies-guide.md
│   ├── structural-formatting.md
│   └── grammar-style/
│       ├── QUICK-START.md        # 80% of grammar questions; load first
│       ├── cross-reference.md    # 21 EoS/CMS/PCP divergences
│       └── index.md              # Concept-to-file routing map
└── legal-style/
    └── QUICK-START.md            # Oregon legal style; start here
```

**File-loading rule**: Load `grammar-style/QUICK-START.md` first. Load additional files
by topic. Never load the full `grammar-style/` directory at once (exceeds 12,000 tokens).
