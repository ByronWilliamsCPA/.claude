# Supabase MCP Server Setup

> **Status**: Active | Standard
> **Version**: 1.0.0
> **Last Updated**: 2026-07-02
> **References**: `rules/mcp-strategy.md`, `standards/claude-design-setup.md`, `standards/snyk-mcp-setup.md`, `standards/mcp-minimal-bloat.md`

The Supabase MCP server connects Claude Code to a single Supabase project so an
agent can read schema and data, generate TypeScript types, and search Supabase
docs from the terminal. It is the data-layer counterpart to the two other
scoped connectors: Claude Design moves UI component/token files, Playwright
drives a live browser, and Supabase reaches the Postgres backend. It exposes
roughly 35 tools across feature groups, so it must never load globally, only in
repos backed by a Supabase project.

## Tier placement and registration model

Supabase is a **per-Supabase-repo Tier 2 connector**, registered at
`--scope project` into the repo's committed `.mcp.json`. This is the deliberate
opposite of Claude Design's `--scope local` choice, and the divergence is
principled:

- Claude Design's URL is identical in every repo, so there is nothing
  repo-specific worth committing, and local scope keeps the committed `.mcp.json`
  free of OAuth connectors.
- Supabase's URL encodes a genuinely per-repo, **non-secret** payload: the
  `project_ref` plus the security-hardening flags (`read_only`, `features`).
  That is exactly the kind of repo-bound, review-worthy configuration that
  belongs under version control.

No credential lives in the file. Auth is OAuth via dynamic client registration
(the older personal access token is no longer required), and the token is cached
per machine, not stored in `.mcp.json`. Committing the URL therefore leaks
nothing; each developer completes the OAuth grant once locally.

Because native MCP has no per-agent lazy loading, "load it only where needed" is
enforced by **scope**: a project-scoped server is present only in that repo's
directory and is invisible elsewhere. The config repo (`~/dev/.claude`) has no
Supabase project and does not carry this server.

## Hardening (required)

Register the hardened URL, never the bare `?project_ref=...` form. The bare form
hands a read-write agent the full lethal-trifecta surface: untrusted content in
the database flows into `execute_sql` and can be exfiltrated. Supabase's own
guidance calls for all three guards below.

```text
https://mcp.supabase.com/mcp?project_ref=<REF>&read_only=true&features=database,docs,development
```

- `read_only=true` runs queries as a read-only Postgres user. This is the single
  most important guard. Drop it only for a throwaway development project when the
  agent must run migrations (`apply_migration`) or other writes, and never point
  such a configuration at production.
- `features=database,docs,development` restricts the tool surface. It deliberately
  excludes `account` (create/pause/delete projects, read billing), `storage`,
  `branching`, and `functions` (Edge Functions). Add a group only when the repo actually needs
  it.
- Use a **development** Supabase project, not production. The prompt-injection
  wrapper Supabase applies to SQL results is, in their words, not foolproof.

## One-time setup (per Supabase repo)

```bash
# 1. From inside the repo, register the hardened server at project scope.
#    This writes the entry into the committed .mcp.json.
claude mcp add --scope project --transport http supabase \
  "https://mcp.supabase.com/mcp?project_ref=<REF>&read_only=true&features=database,docs,development"
```

```text
# 2. Complete the OAuth grant (the step the quick-start text omits).
#    `claude mcp add` only records the URL; the endpoint is OAuth-protected.
/mcp
#    Select supabase, choose Authenticate, complete the browser consent.
```

Until the grant is completed, `claude mcp list` reports `Failed to connect` even
though the URL is correct: the passive health check does not perform the OAuth
flow. A bare `401` on the endpoint is the expected pre-auth state. The grant is
per machine, so each developer runs the `/mcp` Authenticate step once.

Writing `.mcp.json` by hand is equivalent; the entry is:

```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=<REF>&read_only=true&features=database,docs,development"
    }
  }
}
```

## Verify the registration

```bash
# Inside the Supabase repo: present and, after the /mcp grant, Connected.
claude mcp get supabase
claude mcp list | grep supabase

# From a non-Supabase repo: it must NOT appear (project-scope isolation working).
claude mcp list | grep supabase || echo "correctly absent here"
```

## Feature group reference

| Group | Tools | In the hardened default? |
|-------|-------|--------------------------|
| `database` | list_tables, list_extensions, list_migrations, apply_migration, execute_sql | Yes (writes blocked by `read_only`) |
| `docs` | search_docs | Yes |
| `development` | get_project_url, get_publishable_keys, generate_typescript_types | Yes |
| `debugging` | get_logs, get_advisors | No (add when triaging) |
| `account` | list/get/create/pause/restore projects, org, cost | No (high blast radius) |
| `functions` (Edge Functions) | list/get/deploy_edge_function | No |
| `branching` | create/list/delete/merge/reset/rebase_branch | No |
| `storage` | list_storage_buckets, get/update_storage_config | No (disabled by default) |

## Per-project `project_ref`

Every Supabase project has its own `project_ref`, so the URL is repo-specific by
construction. Fill the placeholder from the Supabase dashboard (Project Settings)
when registering. Do not share one committed URL across repos that target
different Supabase projects.
