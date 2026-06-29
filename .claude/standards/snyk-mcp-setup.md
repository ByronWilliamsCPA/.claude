# Snyk MCP Server Setup

> **Status**: Active | Standard
> **Version**: 2.0.0
> **Last Updated**: 2026-06-29
> **References**: `rules/snyk-mcp.md`, `rules/snyk-secure-at-inception.md`, `rules/mcp-strategy.md`, `standards/mcp-minimal-bloat.md`

Snyk MCP Server enables Claude Code to invoke `snyk_sca_scan` (SCA) and
`snyk_code_scan` (SAST) inline during authoring, before any commit exists. This
closes the vulnerability detection gap between writing code and pushing it to
GitHub. The server is registered always-on at user scope so the agent can call
these tools in every session (see `rules/mcp-strategy.md` and
`rules/snyk-secure-at-inception.md`).

## One-time setup (per workstation)

The Snyk platform binary is already installed globally on this workstation, so
use the global `snyk` command directly. Do NOT use the `npx -y snyk@latest ...`
form: it re-downloads the platform binary on every run (which stalls), and the
goal here is to register the already-installed binary, not fetch another copy.

```bash
# Authenticate (browser opens; use GitHub SSO or personal token)
snyk auth

# Configure the MCP Server for Claude Code using the installed global binary
snyk mcp configure --tool=claude-cli

# Verify the installed version (record for audit/pinning reference)
snyk --version
```

### What `snyk mcp configure` writes (and what to clean up)

The configure command has two side effects you must be aware of:

1. **It registers the `Snyk` server at USER scope in `~/.claude.json`**, NOT in
   `~/.claude/settings.json`. `~/.claude.json` is runtime-managed Claude Code
   state; it is not part of this tracked repo and is not committed. The server
   entry points at the local binary (machine-specific path), so it stays out of
   any committed `.mcp.json` for the same reason the localhost-bound sonarqube
   entry does.

2. **It also injects a global "always apply" rule block into `~/.claude/CLAUDE.md`.**
   On this workstation `~/.claude/CLAUDE.md` is a symlink into the tracked
   standards repo, so that auto-injected block would land in version control as
   a malformed rule. Remove the auto-injected block and rely on our curated
   Secure-at-Inception rule (`rules/snyk-secure-at-inception.md`) instead, which
   carries the correct tool names and a bounded significant-change trigger.

   ```bash
   # Confirm the injected block is gone from the tracked CLAUDE.md
   grep -c 'BEGIN SNYK' ~/.claude/CLAUDE.md   # must print 0
   ```

After setup, Snyk is an always-on authoring server: `snyk_code_scan` and
`snyk_package_health_check` are callable inline in every session.

> **Version pinning:** the global binary installs the current release. To pin a
> specific version for reproducibility, install that version of the Snyk CLI and
> re-run `snyk mcp configure --tool=claude-cli` after upgrading.

## Verify the MCP entry

After running the configure command, confirm the server is registered and
connected:

```bash
# The Snyk server should appear and report Connected
claude mcp list

# The Snyk key should be present in runtime-managed user-scope config
grep -c '"Snyk"' ~/.claude.json        # >= 1

# The tracked CLAUDE.md must NOT carry an auto-injected SNYK block
grep -c 'BEGIN SNYK' ~/.claude/CLAUDE.md   # 0
```

If the server is missing, re-run `snyk mcp configure --tool=claude-cli`. If the
auto-injected CLAUDE.md block reappears, remove it again; the curated rule is the
single source of authoring guidance.

## Snyk MCP tools

Snyk MCP Server exposes multiple tools. Per `standards/mcp-minimal-bloat.md`,
only tools that earn their token cost are documented here. The tool names below
are verified by direct `tools/list` introspection of the running server.

| Tool | Purpose | When to invoke |
|------|---------|----------------|
| `snyk_code_scan` | SAST: scans specified file paths for code vulnerabilities | After a SIGNIFICANT change to first-party code (auth, secrets handling, user-input processing); not after every edit |
| `snyk_package_health_check` | Pre-add package health: advisory, popularity, and known-issue signal for a package | Before adding or upgrading a dependency |
| `snyk_sca_scan` | SCA: checks the project against the Snyk advisory database | When a deeper project-wide dependency scan is warranted (the `security-auditor` bundle path) |

Additional tools the server exposes but that we do not invoke from rules or
hooks: `snyk_iac_scan`, `snyk_container_scan`, `snyk_aibom`, `snyk_sbom_scan`,
`snyk_send_feedback` (optional; see below), `snyk_auth`, `snyk_trust`,
`snyk_version`, `snyk_logout`.

## Secrets Detection (CLI)

For pre-push secrets scanning without running a full SAST pass, use the CLI directly:

```bash
snyk code test --detection-type=secrets .
```

This scans the working tree for hardcoded secrets only. It is faster than a full
`snyk code test` run and suitable for use as a pre-push gate. This is distinct
from `snyk_code_scan` (the MCP tool), which runs the full SAST suite on specified
paths.

Requires `SNYK_TOKEN` to be set or `snyk auth` to have been run.

## When to invoke snyk_package_health_check

Invoke `snyk_package_health_check` on a package before:

- A new package is added via `uv add`, `pip install`, or direct requirements edit.
- A dependency is upgraded in pyproject.toml, requirements*.txt, or uv.lock.
- Reviewing a PR that adds new MCP tool dependencies.

If the health check surfaces HIGH or CRITICAL signal on the package, surface it
to the user before proceeding. Do not block the edit unilaterally; report and let
the user decide.

If `SNYK_TOKEN` is not set or the MCP server is not configured, note the gap and
continue without blocking.

## When to invoke snyk_code_scan

Invoke `snyk_code_scan` on the changed files after a SIGNIFICANT first-party code
change, before committing:

- A new authentication or session-handling module.
- A module that processes user-supplied input.
- A module that handles secrets, tokens, or credentials.

Pass the changed file paths as the argument (e.g., the output of `git diff
--cached --name-only` filtered to relevant files), not the project root. The
significant-change trigger (not every edit) bounds Snyk hosted-test quota usage;
see `rules/snyk-secure-at-inception.md`.

If `snyk_code_scan` returns HIGH or CRITICAL findings, surface them to the user
before committing. Do not block the commit unilaterally; report and let the user
decide.

If `SNYK_TOKEN` is not set or the MCP server is not configured, note the gap and
continue without blocking.

## snyk monitor is CLI-only; never invoke it automatically

`snyk monitor` is a CLI-only command (it is NOT an MCP tool). It creates a
persistent project entry in the Snyk organization dashboard; automatic calls
accumulate entries that require manual cleanup. Rules and hooks in this config do
NOT call `snyk monitor`. Run it only when deliberately registering a project for
ongoing Snyk monitoring.

## Snyk MCP Scan (pre-GA as of 2026-06)

Snyk MCP Scan scans MCP configuration files for prompt-injection risks. It is
not generally available yet. When it reaches GA, add a pre-push hook that runs
`snyk mcp-scan` on `~/.claude.json` and any project-local MCP configuration
files. Track the GA announcement at https://docs.snyk.io/snyk-cli/mcp.

## Dual-enforcement design

Two independent mechanisms reinforce the same behavior, covering different failure modes:

| Mechanism | How it works | What it covers |
|-----------|-------------|----------------|
| Always-on rule `rules/snyk-secure-at-inception.md` | Loaded into Claude's context every session; instructs Claude when to call `snyk_code_scan` and `snyk_package_health_check` | Significant first-party changes and dependency adds where Claude can act proactively |
| PostToolUse hook `scripts/snyk-dep-reminder.sh` | Fires after every Edit/Write/MultiEdit; prints a reminder if the file is `pyproject.toml`, `uv.lock`, or `requirements*.txt` | Unplanned edits or sessions where the rule was not loaded |

The rule provides proactive guidance; the hook provides a reactive safety net.
Neither blocks the edit unilaterally; both surface the same recommendation: run a
Snyk scan before committing.

## Tier placement

Snyk MCP Server is an always-on authoring server, registered at user scope in
`~/.claude.json` (see `rules/mcp-strategy.md`). The `security-auditor` agent
bundle still surfaces `snyk_sca_scan` and `snyk_code_scan` for deep on-demand
scans. The always-on rule `rules/snyk-secure-at-inception.md` and the PostToolUse
hook in `settings.json` serve as the proactive and reactive enforcement points
during authoring.
