---
schema_type: common
title: PDF Reader and Verifier Agents
status: draft
owner: engineering
tags: [agents, architecture, optimization, specifications]
purpose: Design for two pinned, reusable agents that isolate PDF reading on a cheap model and semantic page-verification on a mid-tier model, so catch-all subagent PDF work stops inheriting the session Opus model (about 31% of Opus subagent spend in the SAA build).
---

> **Brainstorming**: approved | **Date**: 2026-06-17 | **Author**: Byron Williams | **Lifecycle**: draft (design approved, implementation not started)

## Problem

In the SAA build, subagent work that read and extracted PDFs ran on Opus by
inheritance (the `general-purpose` agent has no pinned model, so it took the
session model). That bucket was about $322 of Opus spend, roughly 31% of all
Opus subagent cost, on work that involves no judgment: pulling text and tables
from named page ranges and locating claims for page verification. Typed
specialist agents (Explore, research-agent, etc.) avoided this because their
definitions pin a model; the catch-all did not.

This design adds two pinned, reusable agents so PDF reading always runs on a
cheap model, with semantic judgment isolated on a mid-tier model, and no
judgment delegated to the cheapest tier.

## Goals

- Pin PDF reading to Haiku and claim verification to Sonnet so neither inherits
  Opus.
- Keep numeric extraction deterministic (libraries, not the model) so a cheap
  model cannot silently corrupt a figure that feeds an exhibit.
- Make both agents global and reusable across projects.
- No hosted services: source documents never leave the machine.

## Non-goals

- Replacing the deterministic per-source extractors in SAA `src/extract/`. Those
  remain the structured-extraction path; these agents feed and verify, not
  supplant.
- Structured value interpretation (typed CSV of business figures). That overlaps
  `src/extract/` and is explicitly out of scope.
- OCR on the default path (see Decision: OCR).

## Components

### Agent: `pdf-reader` (model: haiku)

Faithful content reader. Given a PDF path and page ranges, returns clean text
and tables anchored to page numbers. It interprets nothing; numbers come from
the extraction library.

Frontmatter:

```yaml
---
name: pdf-reader
description: Read-only PDF content extractor. Pulls text and tables from named page ranges to a structured envelope. Use for bulk PDF reading and extraction feedstock; pins to Haiku so it never inherits a costly session model.
model: haiku
tools: ["Read", "Bash", "Grep", "Glob"]
---
```

Output envelope:

```json
{
  "source_path": "data/raw/oic_2026_01_21.pdf",
  "extraction_method": "text_layer | needs_ocr | ocr",
  "pages": [
    {"page": 14, "text": "...", "tables": ["col,col\\nval,val", "..."]}
  ],
  "evidence": "pages requested 12-15; text_layer detected (avg 939 chars/pg); 2 tables on p14"
}
```

### Agent: `pdf-verifier` (model: sonnet)

Claim locator and verifier. Given a claim plus either a PDF path or a
`pdf-reader` envelope, finds the supporting passage and returns a verdict with a
verbatim quote and page citation. This is where the small amount of semantic
judgment lives.

Frontmatter:

```yaml
---
name: pdf-verifier
description: Read-only PDF claim verifier. Given a claim and a PDF (or a pdf-reader envelope), locates the supporting passage and returns supported/contradicted/not_found with a verbatim quote and page citation. Pins to Sonnet.
model: sonnet
tools: ["Read", "Grep", "Glob"]
---
```

Output envelope:

```json
{
  "claim": "OPERF Regular Account was $101.42B at 2026-03-31",
  "verdict": "supported | contradicted | not_found",
  "quote": "Regular Account ... $101.42 billion as of March 31, 2026",
  "page": 3,
  "source_path": "data/raw/fact_2026q1.pdf",
  "evidence": "located on p3; figure and date match verbatim"
}
```

### Deterministic extraction helper: `scripts/pdf_extract.py`

A committed CLI the reader invokes via Bash. Keeps extraction deterministic,
testable, and out of the model's hands. Uses `pdfplumber` (tables) and
`PyMuPDF`/`fitz` (text, page detection). Accepts a path and page range, emits the
pages/tables JSON. Detects text-layer vs image-only by average characters per
page and sets `extraction_method` accordingly.

## Data flow (coordination)

Pipeline, chained by the orchestrator:

1. Caller invokes `pdf-reader` once for the page ranges (expensive extraction on
   Haiku).
2. Caller passes the reader envelope to `pdf-verifier` for each claim (cheap,
   text-only work on Sonnet).
3. The verifier may re-open a single page when a table needs visual
   confirmation, but normally works from the reader's text.

This keeps the costly page extraction on the cheapest model and runs only light
verification on the mid tier. Independent agents that each re-open the PDF were
rejected as duplicative I/O.

## Decision: OCR (off by default, opt-in, flagged)

Evidence from the SAA corpus: 67 of 68 source PDFs have clean text layers; the
sole image-only file is a 1989 academic paper (`faj_michaud_1989.pdf`) cited for
methodology, not a data source. Every document that feeds an exhibit is
born-digital.

Therefore:

- Default: on image-only or thin-layer detection, the reader returns
  `extraction_method: needs_ocr` and stops. No silent guessing on the numeric
  path.
- Opt-in: OCR runs only when the caller explicitly requests it. Output is tagged
  `extraction_method: ocr`, a weaker lineage grade that mandates human
  verification before it can enter any exhibit (Sourced/Modeled/Expert
  discipline). OCR engine selection is deferred until first real need; the helper
  exposes an `--ocr` flag that is wired to a TODO until then.

Rationale: OCR's failure mode (a plausible misread digit) is the exact
silent-corruption risk the lineage discipline exists to prevent, and the corpus
shows the high-stakes numeric path never needs it.

## Dependencies

- Add `pdfplumber` to the environment that runs the helper.
- `PyMuPDF` (`fitz`) and `PyPDF2` are already present in the SAA build
  environment. They are not in this repo's `pyproject.toml`/`uv.lock`; add all
  three wherever the helper is hosted (see Open decisions).
- No third-party skills installed; no hosted APIs. The
  `claude-office-skills/pdf-extraction` skill (pdfplumber-based, security-audited)
  was evaluated and its patterns may inform `pdf_extract.py`, but it is not added
  to the trust boundary. `tanis90/pdf-converter-mineru` was rejected: it calls a
  hosted MinerU API and would transmit source documents off-machine.

## Convention deviation (noted)

`.claude/agents/CLAUDE.md` says read-only agents must not include `Bash`. The
`pdf-reader` is read-only in effect but needs `Bash` to invoke
`scripts/pdf_extract.py`. The grant is intentional and scoped: the prompt
restricts Bash to running the extraction helper and forbids modifying source
PDFs. The `pdf-verifier` remains strictly read-only (no Bash).

## Files

- `.claude/agents/pdf-reader.md`
- `.claude/agents/pdf-verifier.md`
- `scripts/pdf_extract.py`
- `tests/test_pdf_extract.py`
- Update `AGENTS-AND-SKILLS.md` (registration).

## Open decisions

Resolve both before implementation; each is a deliberate design choice, not an
oversight.

- **Read-only tier plus `Bash`.** `pdf-reader` is pinned to `haiku` (the tier
  `.claude/agents/CLAUDE.md` reserves for read-only agents) yet is granted
  `Bash`, which the same convention reserves to non-read-only agents. The grant
  is intentional and scoped (Bash only invokes `pdf_extract.py`, never mutates
  source PDFs). Decide whether to keep the deviation and document the scoped
  grant inline in the agent definition so reviewers and the frontmatter
  validator do not re-flag it, or to move extraction off the read-only agent so
  the convention holds unmodified.
- **Where the helper and its dependencies live.** The agents are global
  (`~/.claude/agents/`) and reusable across projects, but a global agent that
  invokes `scripts/pdf_extract.py` via `Bash` resolves that relative path
  against the consuming project's working directory, not `~/.claude/`. Decide
  between a global helper invoked by absolute path (with `pdfplumber`,
  `PyMuPDF`, and `PyPDF2` in the global environment) and a per-project vendored
  helper (with those dependencies added to each consuming project's lockfile).
  The Files list above assumes the latter; confirm or switch it.

## Testing / acceptance

- `pdf_extract.py` unit tests against a known text-layer PDF: extracted totals
  tie to a hand-checked figure (reuses the SAA G1 spot-check discipline); page
  count and `extraction_method` correct.
- Image-only detection: a scanned fixture returns `needs_ocr` and does not emit
  fabricated text.
- `pdf-verifier` behavior: correctly locates a known claim (verdict `supported`
  with right page) and returns `not_found` for a fabricated claim rather than
  inventing support.

## Expected payoff

The read/extract bucket was about $322 of Opus on this build; the same work on a
pinned Haiku reader is roughly $64 (about $258 saved), with no judgment delegated
to the cheap model. Future builds inherit the saving automatically because the
agents are global.
