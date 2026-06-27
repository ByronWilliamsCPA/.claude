---
title: "Setting Up codebase-memory-mcp"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Step-by-step setup guide for the codebase-memory-mcp code intelligence MCP server."
tags:
  - getting_started
  - mcp_strategy
  - tools
  - setup
---

codebase-memory-mcp is a code intelligence engine that indexes a repository into a
persistent knowledge graph and exposes it via 14 MCP tools. It replaces chains of
`grep | grep | Read` cycles with single structural queries (`trace_path`,
`search_graph`, `get_architecture`), cutting token consumption by ~120x for code
discovery tasks.

**Why it fits this setup:** It ships as a single static binary (C, zero runtime
dependencies), stores indexes in `~/.cache/codebase-memory-mcp/`, and manages its
own Claude Code wiring (skill, hook, MCP entry) via an `install` command. You do
not manage it through the tiered MCP strategy; it runs alongside that stack.

---

## What the binary installs (once)

| Artifact | Location | Managed by |
|----------|----------|------------|
| MCP server entry | `~/.claude/.mcp.json` | binary `install` / `uninstall` |
| Skill | `~/.claude/skills/codebase-memory/SKILL.md` | binary `install` / `uninstall` |
| Hook script | `~/.claude/hooks/cbm-code-discovery-gate` | binary `install` / `uninstall` |
| Hook wiring (PreToolUse, `Grep\|Glob` matcher) | `~/.claude/settings.json` | binary `install` / `uninstall` |
| Project indexes | `~/.cache/codebase-memory-mcp/` | binary at runtime |

`~/.claude/.mcp.json` is gitignored in this repo (line 333 of `.gitignore`). The
skill and hook script are binary-managed files that live in git-tracked directories
but are not committed; treat them the same as compiled outputs.

---

## Step 1: Install the binary

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

This downloads the static binary to `~/.local/bin/codebase-memory-mcp`, verifies
the SHA-256 checksum against the release manifest, and then automatically runs
`codebase-memory-mcp install` to configure Claude Code.

Verify:

```bash
codebase-memory-mcp --version
```

Check `~/.local/bin` is on `PATH` if the command is not found:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

---

## Step 2: Verify what the install wrote

The `install` command runs non-interactively as part of step 1. Confirm each
artifact landed:

```bash
# MCP entry
cat ~/.claude/.mcp.json

# Skill
ls ~/.claude/skills/codebase-memory/

# Hook script
ls ~/.claude/hooks/cbm-code-discovery-gate

# Hook wiring in settings.json: look for the Grep|Glob PreToolUse entry
python3 -m json.tool ~/.claude/settings.json | grep -A6 "cbm\|codebase-memory\|Grep"
```

If any artifact is missing, run `codebase-memory-mcp install` manually.

---

## Step 3: Restart Claude Code and confirm 14 tools load

Restart Claude Code completely (not just reload). Then verify:

```text
/mcp
```

You should see `codebase-memory-mcp` with 14 tools listed. If it shows 0 tools or
is absent, check that the path in `~/.claude/.mcp.json` points to the installed
binary.

---

## Step 4: Enable auto-index

By default, projects must be indexed manually each session. Auto-index handles this
on first connection per project:

```bash
codebase-memory-mcp config set auto_index true
codebase-memory-mcp config set auto_index_limit 50000
```

After enabling auto-index, previously-indexed projects are registered with the
background watcher for ongoing git-based change detection. New projects get a full
index on first session connection.

---

## Step 5: Index your first repos

Auto-index triggers on the next Claude Code session start per project. To index
immediately without opening a session:

```bash
codebase-memory-mcp cli index_repository '{"repo_path": "/home/byron/dev/.claude"}'
```

Or inside a Claude Code session:

```text
Index this project
```

Verify:

```bash
codebase-memory-mcp cli list_projects
```

---

## Step 6: Per-repo decisions

For each individual project repo (not this global config), decide three things:

### Team-shared graph artifact

Commit `.codebase-memory/graph.db.zst` so teammates skip the full reindex on clone.
The binary auto-creates a `.gitattributes` entry with `merge=ours` to prevent
binary merge conflicts. For solo repos, skip this and add `.codebase-memory/` to
`.gitignore` instead.

```bash
# Solo repos: ignore the artifact
echo '.codebase-memory/' >> .gitignore

# Team repos: commit the artifact after first index
git add .codebase-memory/graph.db.zst
git commit -S -m "chore: add codebase knowledge graph artifact"
```

### Custom extension mappings

Only needed for repos with non-standard extensions:

```json
{"extra_extensions": {".blade.php": "php", ".mjs": "javascript"}}
```

### Custom ignore patterns

Only needed when `.gitignore` alone is insufficient (e.g., large generated files
you want in git but not in the graph):

Place in `.cbmignore` (gitignore syntax) at the repo root:

```gitignore
generated/
vendor/large-stubs/
```

---

## Step 7: How the hook works

The `cbm-code-discovery-gate` hook fires on every `Grep` and `Glob` tool call. It
calls `codebase-memory-mcp hook-augment`, which runs a `search_graph` query
matching the search token and injects results as `additionalContext`. It **never
blocks** a tool call: if the binary is absent, hung, or returns an error, it
exits 0 silently.

The hook complements the skill's instruction to prefer graph tools. For searches
that fall through to Grep/Glob anyway, it automatically enriches results with
structural context.

---

## Keeping up to date

```bash
codebase-memory-mcp update
```

The binary also checks for updates on each startup and notifies on the first tool
call if a newer release is available.

---

## Uninstalling

```bash
codebase-memory-mcp uninstall
```

Removes the skill, hook script, hook wiring from `settings.json`, and the
`~/.claude/.mcp.json` entry. Does not remove the binary or SQLite indexes at
`~/.cache/codebase-memory-mcp/`.

---

## Architecture Decision Records

The `manage_adr` tool stores ADRs in the SQLite graph database per project. They
persist across re-indexes but are not in git by default. To version-control ADRs,
export them to `docs/architecture/` manually to align with the existing ADR
convention in this repo.
