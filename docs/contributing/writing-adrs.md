---
title: "Writing ADRs"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Guide for authoring new architecture decision records."
tags:
  - contributing
  - adr
  - decisions
  - documentation
---

## When to Write an ADR

Write an ADR when a decision is *load-bearing* — meaning silently changing it would break behavior, break the install, or break the mental model a reader needs. If the decision is easily reversible and affects only one file, it is probably an implementation detail, not an ADR.

See [ADR-007](../architecture/adr/ADR-007-dual-audience-docs.md) for the reasoning behind the dual-audience layout this doc is part of.

## The Slim Template

Start from the slim template at `docs/architecture/adr/_template.md` (open it directly in the repo — it is excluded from the built site). The full template sections are:

1. **Context** — the problem and forces at play.
2. **Decision** — a single declarative sentence.
3. **Alternatives Considered** — what you rejected and why.
4. **Consequences** — positive, negative, neutral.
5. **References** — code files, related ADRs, external sources.

There is a longer reference variant at `docs/ADRs/adr-template.md` (excluded from the built site); use it for unusually consequential decisions.

## Naming Convention

`architecture/adr/ADR-NNN-kebab-case-title.md`. Numbers are sequential and never reused.

## Status Lifecycle

ADR decision status lives in a body banner near the top: `Proposed` → `Accepted` → `Deprecated` / `Superseded by ADR-NNN`.

The frontmatter `status:` field is for the **document** itself (`draft`, `in-review`, `published`), not the decision status. They are different axes and both matter.

## Rollback

If you decide you need to revert the dual-audience docs structure, the rollback command block is in the approved plan at `/home/byron/.claude/plans/polished-singing-crab.md` under "Validation & Tooling → Rollback plan".

## See Also

- [Frontmatter Standard](../frontmatter-standard.md)
- [ADR Index](../architecture/adr/index.md)
