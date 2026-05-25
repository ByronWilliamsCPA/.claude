---
title: "Reference"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Reference catalogs for agents, skills, hooks, and MCP tools."
tags:
  - reference
  - overview
---

Reference material for every agent, skill, hook, and MCP tool defined in the repo. These pages are catalogs, not tutorials: use the [Getting Started](../getting-started/index.md) section first if you are new.

## Catalogs

- [Agents Catalog](agents.md): all 43 agents grouped by domain.
- [Skills Catalog](skills.md): all 40+ skills grouped by workflow stage.
- [Hooks Reference](hooks.md): all five hook types and their scripts.
- [MCP Strategy](mcp.md): tiered loading reference.

## Compliance and Standards

- [Repo Compliance System](repo-compliance.md): standards manifest, domain agents, audit workflow, override system, and full check catalog overview.
- [Renovate Architecture](renovate-architecture.md): self-hosted Renovate stack, layered config inheritance, manifest enforcement (TOOL-013, PC-015, CI-020, CI-021), and relationship to Dependabot, SBOM, and pip-audit.
- [GitHub Workflow Audit](github-workflow-audit.md): Sprint 0 baseline for branch protection and workflow status across all 44 repos.
- [Org Rulesets](org-rulesets/README.md): ruleset architecture, design decisions, and enforcement migration checklist.
- [Repository Type Taxonomy](repo-type-taxonomy.md): seven repo types and their audit exemption profiles.

## See Also

- `AGENTS-AND-SKILLS.md` at the repo root: the canonical catalog.
- `CLAUDE.md` at the repo root: global development standards.
