---
title: "MCP Fleet Status"
schema_type: common
status: published
owner: core-maintainer
purpose: "Living reference for MCP server health across the dev fleet."
tags:
  - mcp_strategy
  - tooling
---

> Last audited: 2026-06-27

## Global Config (`~/.claude/settings.json`)

Servers defined in the global config are visible in every project session, labeled
"User" in the MCP panel of other repos and "Project" in this repo (since
`~/.claude/` is symlinked here).

| Server | Type | Always-on | Notes |
|--------|------|-----------|-------|
| zen (pal) | command (Python) | Yes | Requires venv at `/home/byron/dev/zen-mcp-server/.pal_venv/` |
| context7 | command (npx) | Yes | npx at `/home/byron/.npm-global/bin/npx` |
| github | command (docker) | Conditional | Requires `GITHUB_PERSONAL_ACCESS_TOKEN` in env; fails silently without it |
| sonarqube | url (localhost:8090) | Conditional | Requires `SONARQUBE_TOKEN` + Docker container running |
| sonarqube-williaby | url (localhost:8091) | Conditional | Same token; sometimes fails to register tools even when healthy |

Tier 2/3 servers (defined in `mcp/*.json`, listed in `enabledMcpjsonServers`):
playwright, sentry, mermaid, docker, uml-mcp-server

## Binary-Managed Servers

These servers manage their own wiring outside `settings.json` and the tier system.

| Server | Config | Managed by |
|--------|--------|------------|
| codebase-memory-mcp v0.8.1 | `~/.claude/.mcp.json` | `codebase-memory-mcp install` |

Do NOT add these to `settings.json` or `mcp/*.json`; the binary is authoritative.

## Required Environment Variables

| Variable | Where Set | Purpose |
|----------|-----------|---------|
| `SONARQUBE_TOKEN` | `~/.bashrc` | sonarqube + sonarqube-williaby auth |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `~/.bashrc` (add: scopes repo, read:org, read:user) | github MCP server auth |
| `SNYK_TOKEN` | `~/.bashrc` (add when Snyk plan executes) | snyk MCP tools auth |

## Fleet Project Override Status

Audited 2026-06-27: **0 of 23 project-level settings.json files** have `mcpServers`
blocks. All repos inherit from global config. Repos audited:
- `.claude`, `.github`, `AMC`, `CYO_Adventure`, `MTG_AI`, `PromptCraft`,
  `audio-processor`, `bwcpa-.github`, `cyo-adventure`, `dot-github`,
  `family-office-portal`, `fragrance-rater`, `gleif`, `homelab-infra`,
  `image-generation`, `llc-manager`, `pp-security-master`, `rag-processor`,
  `reference-library`, `taxdome`, `usc`, `williaby-dot-github`, `zen-mcp-server`

This is the correct posture. Do NOT add global Tier 1 servers to project
settings.json: that creates drift when server paths or args change.

## Key Settings

- `enableAllProjectMcpServers: false`: project-level `mcpServers` blocks do not
  auto-enable. Servers must be in global settings or explicitly listed in
  `enabledMcpjsonServers`. Since no project defines `mcpServers`, this has no
  current effect but is the correct default.

## When to Add Project-Level mcpServers

Only add a project-level `mcpServers` block when:
1. A project needs a server the global config does not have (e.g., a project-specific
   Postgres instance).
2. A server needs project-specific env vars (e.g., different `SENTRY_ORG` per project).

Never duplicate the global Tier 1 servers in project settings: it causes drift.

## Validation

Run any time a server seems missing:

```bash
bash ~/.claude/scripts/validate-mcp-connections.sh
```

Expected healthy output (after GitHub PAT and SNYK_TOKEN are set):

```text
=== MCP Connection Validation ===

-- Environment --
  [OK]   GITHUB_PERSONAL_ACCESS_TOKEN: authenticates as ByronWilliamsCPA
  [OK]   SONARQUBE_TOKEN: set (40 chars)
  [OK]   SNYK_TOKEN: set

-- Servers --
  [OK]   zen (pal): venv and server.py present
  [OK]   context7: npx found at /home/byron/.npm-global/bin/npx
  [OK]   github: docker running and PAT set
  [OK]   sonarqube: port 8090 responding (HTTP 405)
  [OK]   sonarqube-williaby: port 8091 responding (HTTP 405)
  [OK]   codebase-memory-mcp: binary present (codebase-memory-mcp 0.8.1)
  [OK]   snyk: npx reachable and SNYK_TOKEN set

=== Summary: 9 ok, 0 warn, 0 fail ===
```

## Known Gotchas

- The `sonarqube-williaby` server sometimes shows as connected but fails to register
  its tools. If tools are absent after the container is healthy, fall back to the
  SonarCloud REST API directly.
- The `github` MCP server starts a Docker container on each session startup (5-10s
  delay). If it is missing from the panel immediately after session open, wait 15 seconds
  before diagnosing.
- The `claude.ai (8)` servers visible in the MCP panel (Consensus, Craft, Gmail, etc.)
  are Anthropic account-level integrations, not local MCP servers. They are independent
  of `settings.json`. "Needs Auth" means they have not been authenticated in the
  claude.ai account settings; this has no effect on the Project target state.
- Context7, sonarqube, and pal may take 15-30 seconds to appear after session open.
  Absence immediately after open is a timing issue, not a configuration problem.
