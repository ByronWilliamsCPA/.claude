# MCP Server Configuration Templates

This directory contains Model Context Protocol (MCP) server configuration templates for reference and documentation purposes.

## Overview

**IMPORTANT**: These JSON files are templates only. The current setup uses `claude mcp add` commands to install servers directly.

- **User-level servers**: Use `~/.claude/scripts/mcp-manager.sh` to install globally
- **Project-level servers**: Use `~/.claude/scripts/setup-project-mcp.sh` per project
- **Manual installation**: Use `claude mcp add -s user|project <name> <command>`

## Configuration Files

### Core Servers

- `zen-server.json.disabled` - Legacy orchestration server (replaced by PAL MCP server)
- `dev-tools-servers.json` - Development utilities (sequential-thinking, git, time)
- `github-server.json` - GitHub API integration

### Search & AI Servers

- `common-servers.json` - External APIs (perplexity, tavily, context7, sentry)
- `context7-http.json` / `context7-sse.json` - Context7 transport variants

### Specialized Servers

- `serena-server.json` - Advanced NLP capabilities
- `serena-auto-server.json` - Automated Serena configuration
- `zapier-server.json` - Workflow automation

### Disabled Servers (`mcp/disabled/`)

The `mcp/disabled/` subdirectory holds server configs that are parked but kept
for reference. Nothing loads them; each is inert until moved back into `mcp/`
with the `.disabled` suffix removed.

- `context7-http.json.disabled` - Context7 HTTP transport; superseded by the active stdio Context7 entry, kept as a fallback
- `context7-sse.json.disabled` - Context7 SSE transport; SSE deprecated upstream
- `serena-server.json.disabled` / `serena-auto-server.json.disabled` - Serena (manual and auto-start); not in the active loadout, retained for evaluation
- `dev-tools-servers.json.disabled` - sequential-thinking, git, time bundle; parked pending per-tool review
- `common-servers.json.2.disabled` - alternate common-servers bundle (perplexity, tavily, context7, sentry); kept while the primary set is active
- `zapier-server.json.disabled` - Zapier bridge; parked to avoid an idle remote dependency

To re-enable any of these, move the file up to `mcp/`, drop the `.disabled`
suffix, and restart Claude Code.

## Required Environment Variables

Many MCP servers require environment variables to function. Ensure these are set in your shell or `.env` files:

### Development Tools

```bash
export GIT_REPO_PATH="/path/to/default/repository"
```

### GitHub Integration

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_xxxxxxxxxxxx"
```

### Serena NLP

```bash
export SERENA_INSTALL_PATH="/path/to/serena-mcp-server"
export SERENA_PROJECT_PATH="/path/to/current/project"
```

### External APIs

```bash
export PERPLEXITY_API_KEY="pplx-xxxxxxxxxxxx"
export TAVILY_API_KEY="tvly-xxxxxxxxxxxx"
export UPSTASH_REDIS_REST_URL="https://xxxxx.upstash.io"
export UPSTASH_REDIS_REST_TOKEN="xxxxxxxxxxxx"
export SENTRY_AUTH_TOKEN="xxxxxxxxxxxx"
export SENTRY_ORG="your-org"
export SENTRY_PROJECT="your-project"
```

## Installation Requirements

### Zen MCP Server

The server is our maintained fork (`williaby/zen-mcp-server`), kept in sync with upstream
`BeehiveInnovations/pal-mcp-server` (the rebrand of the original zen-mcp-server). It is registered
under the name `zen` in `settings.json`, so its tools are invoked with the `mcp__zen__*` prefix
(e.g., `mcp__zen__codereview`, `mcp__zen__chat`). We keep the `zen` name because our config and tool
identifiers point at the fork; do not rename these references to `pal`. See
`.claude/rules/mcp-strategy.md` for the full naming rationale and cost-lane guidance.

### Docker-based Servers

Some servers like GitHub MCP run via Docker and require Docker to be installed and running.

### Python/Node Servers

Various servers use `uvx`, `npx`, or `uv run` commands and require the respective package managers.

## Troubleshooting

### No MCP Servers Loading

1. Verify `enableAllProjectMcpServers: true` in `settings/base-settings.json`
2. Check that environment variables are set
3. Ensure required executables (python, docker, node, uvx) are available
4. Check Claude Code logs for specific error messages

### Specific Server Not Loading

1. Test the command manually: `${command} ${args[0]} ${args[1]} ...`
2. Verify environment variables for that specific server
3. Check if paths in the configuration file exist

### Common Issues

- **Consolidated config not found**: Ensure `~/.claude/mcp-servers.json` exists
- **Individual configs not merged**: Changes to individual JSON files won't take effect until merged into `mcp-servers.json`
- **Incorrect paths**: Server installation paths may differ from configuration
- **Missing API keys**: External services require valid API credentials
- **Permission issues**: Ensure execute permissions on server binaries

## Configuration Management

### Updating MCP Servers

1. Edit individual JSON files in `/mcp` directory for organization
2. Merge changes into `~/.claude/mcp-servers.json` for Claude Code to load them
3. Test with `claude mcp list`

### Validation Script

Run the validation script to check your environment:

```bash
~/.claude/scripts/validate-mcp-env.sh
```

This will verify:

- Required executables are installed
- Environment variables are set
- File paths exist
- Claude Code configuration is correct

### Testing

Test MCP server loading with:

```bash
claude mcp list
```

Should show all configured and available servers from `mcp-servers.json`.
