# Snyk MCP Server Setup

> **Status**: Active | Standard
> **Version**: 1.0.0
> **Last Updated**: 2026-06-27
> **References**: `rules/snyk-mcp.md` (pending Task 3), `rules/mcp-strategy.md`, `standards/mcp-minimal-bloat.md`

Snyk MCP Server enables Claude Code to invoke `snyk test` and `snyk code test`
inline during authoring, before any commit exists. This closes the vulnerability
detection gap between writing code and pushing it to GitHub.

## One-time setup (per workstation)

```bash
# Install Snyk CLI globally
npm install -g snyk
# Alternative on macOS: brew install snyk

# Authenticate (browser opens; use GitHub SSO or personal token)
snyk auth

# Configure MCP Server for Claude Code
npx -y snyk@latest mcp configure --tool=claude-cli
```

The configure command writes a `snyk-mcp` entry to `~/.claude/settings.json`
automatically.

## Verify the MCP entry

After running the configure command, open `~/.claude/settings.json` and confirm
a `snyk-mcp` block appears under `mcpServers`. If the entry is missing, re-run
the configure command.

## Snyk MCP tools

Snyk MCP Server exposes multiple tools. Per `standards/mcp-minimal-bloat.md`,
only tools that earn their token cost are documented here.

| Tool | Purpose | When to invoke |
|------|---------|----------------|
| `snyk_test` | SCA: checks the project against the Snyk advisory database | After adding or upgrading a dependency in pyproject.toml, requirements*.txt, or uv.lock |
| `snyk_code_test` | SAST: scans specified file paths for code vulnerabilities | Before committing a new authentication module, secrets handler, or user-input processor |
| `snyk_monitor` | Pushes a snapshot to the Snyk org dashboard | **Manual only; do not invoke automatically** (see below) |

## When to invoke snyk_test

Invoke `snyk_test` on the project root when:

- A new package is added via `uv add`, `pip install`, or direct requirements edit.
- A dependency is upgraded in pyproject.toml, requirements*.txt, or uv.lock.
- Reviewing a PR that adds new MCP tool dependencies.

If `snyk_test` returns HIGH or CRITICAL findings on the newly added package,
surface the finding to the user before proceeding. Do not block the edit
unilaterally; report and let the user decide.

If `SNYK_TOKEN` is not set or the MCP server is not configured, note the gap
and continue without blocking.

## When to invoke snyk_code_test

Invoke `snyk_code_test` on the changed files before committing:

- A new authentication or session-handling module.
- A module that processes user-supplied input.
- A module that handles secrets, tokens, or credentials.

Pass the changed file paths as the argument (e.g., the output of `git diff --cached --name-only`
filtered to relevant files), not the project root.

If `snyk_code_test` returns HIGH or CRITICAL findings, surface them to the user
before committing. Do not block the commit unilaterally; report and let the user decide.

If `SNYK_TOKEN` is not set or the MCP server is not configured, note the gap
and continue without blocking.

## snyk_monitor: manual only

`snyk_monitor` creates a persistent project entry in the Snyk organization
dashboard. Automatic calls accumulate entries that require manual cleanup.
Rules and hooks in this config do NOT call `snyk_monitor`. Use it only when
deliberately registering a project for ongoing Snyk monitoring.

## Snyk MCP Scan (pre-GA as of 2026-06)

Snyk MCP Scan scans MCP configuration files for prompt-injection risks. It is
not generally available yet. When it reaches GA, add a pre-push hook that runs
`snyk mcp-scan` on `.claude/settings.json` and any project-local MCP
configuration files. Track the GA announcement at
https://docs.snyk.io/snyk-cli/mcp.

## Tier placement

Snyk MCP Server is Tier 2 (on-demand) per `rules/mcp-strategy.md`. It is
NOT in the always-loaded `mcpServers` block. The path-scoped rule
`rules/snyk-mcp.md` (pending Task 3) and the PostToolUse hook in `settings.json` serve as
reminder enforcement points during authoring.
