# Git-Trackable Claude Code Configuration

This directory contains a git-trackable Claude Code configuration that allows you to version control your MCP server setups and share them across team members.

## How It Works

Claude Code supports the `CLAUDE_CONFIG_DIR` environment variable to specify an alternative configuration directory. By setting this to `$HOME/.claude`, Claude will use the `.claude.json` file in this directory instead of the default `~/.claude.json`.

## Current Configuration

### MCP Servers
- **zen-core**: Zen MCP server with smart_consensus tool enabled
  - Command: `$HOME/dev/zen-mcp-server/.zen_venv/bin/python`
  - Args: `$HOME/dev/zen-mcp-server/server.py`
  - Environment:
    - `HYBRID_MODE=true`
    - `CORE_TOOLS_ONLY=true`
    - `DISABLED_TOOLS=secaudit,codereview,debug,analyze,refactor,thinkdeep,docgen,testgen,planner,precommit,tracer,layered_consensus`

### Available Tools
- `smart_consensus`: Strategic decision-making tool using multiple AI models
- Various core tools from the zen MCP server

## Usage Options

### Option 1: Environment Variable in Shell
Add to your `~/.bashrc`:
```bash
export CLAUDE_CONFIG_DIR="$HOME/.claude"
```

### Option 2: Startup Script
Use the provided startup script:
```bash
./start-claude.sh
```

### Option 3: Manual Export
Export the variable before running Claude:
```bash
export CLAUDE_CONFIG_DIR=$HOME/.claude && claude
```

## Git Integration

This configuration is now tracked in git and can be:
- ✅ Committed to version control
- ✅ Shared across team members
- ✅ Backed up and restored
- ✅ Modified and tracked through git history

## Files Structure

```
$HOME/.claude/
├── .claude.json              # Main configuration file (git-tracked)
├── settings.json             # Project-specific settings (git-tracked)
├── start-claude.sh          # Startup script (git-tracked)
├── mcp/                     # MCP server configurations (git-tracked)
├── scripts/                 # Hook scripts (git-tracked)
└── README-git-trackable-config.md  # This documentation
```

## Benefits

1. **Version Control**: Track configuration changes over time
2. **Team Sharing**: Share MCP configurations across team members
3. **Backup/Restore**: Easy backup and restoration of configurations
4. **Environment Consistency**: Ensure consistent Claude Code setups across projects
5. **Centralized Management**: Single location for all Claude Code configurations

## Testing

To verify the configuration is working:
```bash
export CLAUDE_CONFIG_DIR=$HOME/.claude
claude mcp list
# Should show: zen-core server connected
```

## Migration Notes

- Original configuration remains in `~/.claude.json` as fallback
- MCP servers have been moved from global config to git-trackable config
- Tool permissions are still managed through `settings.json`