---
title: "Architecture Decision Records"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Index of architecture decision records for Claude Code Configuration."
tags:
  - adr
  - decisions
  - architecture
  - reference
---

Architecture Decision Records (ADRs) capture load-bearing design choices so future maintainers can understand *why* something is the way it is — not just *what* it is.

## Process

1. A decision is load-bearing if silently changing it would break behavior, break the install, or break the mental model a reader needs.
2. New ADRs use the slim template at `docs/architecture/adr/_template.md` (excluded from the built site; open it directly in the repo). The verbose reference variant at `docs/ADRs/adr-template.md` remains for unusually consequential decisions.
3. ADRs are numbered sequentially. Once published, the title and number do not change — supersede with a new ADR instead.
4. Every ADR carries `schema_type: common` frontmatter. The `status:` field is for the doc itself (`draft` / `in-review` / `published`); the ADR's decision status (`Proposed` / `Accepted` / `Deprecated` / `Superseded`) lives in a body banner near the top.

## Index

| # | Title | Decision Status | Topic |
| --- | --- | --- | --- |
| [001](ADR-001-two-layer-symlink-install.md) | Two-Layer Symlink Install | Accepted | Install model |
| [002](ADR-002-hook-composition.md) | Hook Composition and Ordering | Accepted | Hook system |
| [003](ADR-003-tiered-mcp-loading.md) | Tiered MCP Loading Strategy | Accepted | MCP context budget |
| [004](ADR-004-skill-vs-agent-boundary.md) | Skill vs Agent Boundary | Accepted | Capability taxonomy |
| [005](ADR-005-submodule-extension-model.md) | Submodule Extension Model | Accepted | External integration |
| [006](ADR-006-rules-vs-standards.md) | Rules vs Standards Boundary | Accepted | Context injection |
| [007](ADR-007-dual-audience-docs.md) | Dual-Audience Documentation Structure | Accepted | Documentation layout |

## See Also

- [Frontmatter Standard](../../frontmatter-standard.md)
- [Writing ADRs](../../contributing/writing-adrs.md)
- [Architecture Overview](../index.md)
