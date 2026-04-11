---
title: "Global Settings Hardening 2026-04-11"
schema_type: common
status: published
owner: core-maintainer
purpose: "Record of global Claude Code settings hardening and skill cleanup applied on 2026-04-11."
tags:
  - development
  - configuration
---

Record of the configuration changes applied to `~/.claude/settings.json`
alongside skill cleanup in this repo. The live settings file is not git-tracked,
so this document is the canonical record of what changed, why, and how to roll
it back.

## Change summary

Branch: `chore/global-settings-hardening`

1. Expanded `env` block with reasoning, compaction, tool search, and timeout
   controls
2. Added `permissions.defaultMode: "acceptEdits"` to address `.claude/skills/`
   editing friction
3. Expanded `permissions.allow` from 5 entries to 30 calibrated for the 1,327
   Bash invocations over the 2026-03-13 to 2026-04-11 usage window
4. Added `permissions.deny` rules for secrets paths
5. Added `permissions.ask` rules for destructive git and gh operations
6. Flipped `enableAllProjectMcpServers` from `true` to `false`
7. Removed `postgres` from global `enabledMcpjsonServers` (will be enabled
   per-repo as needed)
8. Changed top-level `effortLevel` from `"max"` to `"high"` for schema
   compliance (`CLAUDE_CODE_EFFORT_LEVEL=max` in env block provides the actual
   max effort)
9. Removed duplicate skills `testing-variant-b-r2` and `test-coverage-variant-b`
   that were completed benchmark variants registered under the same names as
   the canonical skills

## Rationale by setting

### Env block

| Variable | Value | Rationale |
| --- | --- | --- |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | `1` | Official Anthropic workaround for the Opus 4.6 adaptive-thinking under-allocation bug. Forces fixed reasoning budget. |
| `CLAUDE_CODE_EFFORT_LEVEL` | `max` | Env var form is more reliable than top-level `effortLevel`. Schema only validates `low`/`medium`/`high` at the top level, but `max` is valid for the env var on Opus 4.6. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `75` | Lowered from default ~83.5% to preserve decision context earlier in multi-phase sessions. |
| `ENABLE_TOOL_SEARCH` | `auto:5` | Lowers MCP tool deferral threshold from 10% to 5% of context. Addresses the 7.5k PAL MCP overhead observed in the `/context` audit. |
| `BASH_DEFAULT_TIMEOUT_MS` | `300000` | Aligned with CI/CD workloads. Default 120s was hitting the 93 Command Failed errors in the usage report. |
| `BASH_MAX_TIMEOUT_MS` | `600000` | Ceiling for explicit long-running operations. |
| `API_TIMEOUT_MS` | `600000` | v2.1.101 fixed the hardcoded 5-minute API timeout. Setting this explicitly ensures the fix takes effect. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `1` | Reduces background chatter. Relevant because 25% of messages occur during parallel sessions where bandwidth matters. |

### Permissions

`defaultMode: acceptEdits` addresses the skills-editing friction where
`skipDangerousModePermissionPrompt: true` is broken for `.claude/skills/` paths
since v2.1.78. The `acceptEdits` mode is the recommended replacement that
auto-approves file writes without triggering the protected-directory prompts.

`allow` entries prioritize exact commands (`Bash(git status)`, `Bash(git log)`)
over wildcards where possible. Per the security review, shell metacharacters
(`&&`, `;`, `|`, `$()`) are not filtered by prefix-matching rules, so wildcard
patterns like `Bash(git *)` provide weaker guarantees than they appear to.
`Bash(git commit:*)` and `Bash(git add:*)` are auto-approved because the user
commits frequently (55 commits in 30 days) and commit prompts add friction
without meaningfully reducing risk.

`deny` entries for `.env`, SSH, AWS, GPG, and common secrets paths are
defense-in-depth against Read-tool accidents. They do not prevent Bash
exfiltration (e.g., `cat .env` still works), so treat them as an audit signal
layer, not a security boundary.

### MCP

`enableAllProjectMcpServers: false` closes the Trail of Bits supply-chain
vector where cloned repos can auto-load arbitrary MCP servers via project-level
`.mcp.json`. Globally configured MCP servers in `~/.claude/settings.json`
continue to work unchanged.

`postgres` removed from global list. Will be enabled per-repo via project-level
`.mcp.json` when a project actually uses it, reducing always-on MCP overhead.

Kept without change: `zen`, `context7`, `github`, `sonarqube`,
`sonarqube-williaby`, `playwright`, `sentry`, `mermaid`, `docker`,
`uml-mcp-server` — all map to observed work areas.

### Skill removal

`testing-variant-b-r2/` and `test-coverage-variant-b/` had SKILL.md frontmatter
that exactly matched the canonical `testing/` and `test-coverage/` skills,
causing them to register under duplicate names in every session's context.
Verified by comparing `name:` frontmatter fields before removal.

`testing-workspace-r2/` and `test-coverage-workspace/` are NOT removed because
they contain benchmark data that may still be valuable.

## Rollback steps

### Reverting env vars

Remove the eight new keys from `~/.claude/settings.json` `env` object, leaving
only `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.

### Reverting permissions

Restore the original 5-entry allow list:

```json
"allow": ["Bash(poetry run ruff:*)", "WebSearch", "WebFetch", "Read", "Agent"]
```

Remove `deny`, `ask`, and `defaultMode` keys entirely.

### Reverting MCP changes

Restore `enableAllProjectMcpServers: true` and add `postgres` back to
`enabledMcpjsonServers`.

### Reverting skill removals

Variant-b skill directories were local untracked workspace artifacts, not
git-tracked. Recreate them from the `testing-workspace-r2/` and
`test-coverage-workspace/` benchmark outputs if needed.

## Open follow-ups

These are intentionally not in this commit. Track as separate workstreams.

### PAL MCP review

The PAL MCP server (<https://github.com/BeehiveInnovations/pal-mcp-server/>)
currently consumes ~7.5k tokens per session across 16 tools. Originally the zen
MCP server, renamed to PAL.

Known usage:

- `chat` — heavily used
- `consensus` — heavily used
- `tiered_consensus` — desired but currently unstable

Currently underused (may be replaceable by agents and skills after the
overhaul):

- `refactor`
- `codereview`

Action: clone and review the PAL repo to understand each tool. Evaluate whether
each tool is still useful after the global Claude setup changes land, and
whether some can be pruned or deferred. `ENABLE_TOOL_SEARCH=auto:5` in this
commit should reduce their overhead in the meantime.

Launch location also needs confirmation — likely running from the WSL instance
where PAL was cloned, but the exact path is undocumented.

### CLAUDE.md refactor

`/home/byron/.claude/CLAUDE.md` currently consumes ~3.5k tokens loaded on every
session start. The compass artifact guidance is to keep CLAUDE.md under 50
lines. Actions to consider:

- Move content into `.claude/rules/*.md` files referenced from CLAUDE.md
  (already partially done)
- Trim the global resource catalog table because it is a directory, not
  operating instructions
- Add a dedicated "Compact Instructions" section per the compaction research,
  since CLAUDE.md is re-injected verbatim after compaction and is the only
  component guaranteed to survive intact

This is a separate workstream and should not be bundled with the settings
commit.

## Verification after applying

Checks to run after this change lands:

1. `claude --version` confirms v2.1.101 or later
2. Start a new session and run `/context` to confirm `ENABLE_TOOL_SEARCH=auto:5`
   reduces PAL MCP footprint
3. Edit a file in `.claude/skills/` and confirm no permission prompt fires
   (validates `acceptEdits` mode is working)
4. Check that multi-phase sessions hit compaction earlier and preserve more
   decision context than before
