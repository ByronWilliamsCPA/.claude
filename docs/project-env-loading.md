---
schema_type: common
title: "Project-Specific Environment Variable Loading"
status: published
owner: core-maintainer
purpose: "Guide for handling project-specific environment variables with global Claude Code configuration."
tags:
  - configuration
  - setup
  - guide
---

This guide explains how to handle project-specific environment variables when using global Claude Code configuration.

## The Challenge

The global `~/.claude/.env` file is loaded by Claude Code at startup, but some MCP servers (like Serena) need project-specific values that change based on your current working directory.

## Solutions

### Solution 1: Project-Specific .mcp.json (Recommended)

Instead of relying on environment variables for project paths, override the MCP server configuration at the project level:

```json
// In your project's .mcp.json
{
  "mcpServers": {
    "serena": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "$HOME/dev/serena",  // Use your actual Serena path
        "serena-mcp-server",
        "--context",
        "ide-assistant",
        "--project",
        "."  // Current directory
      ]
    }
  }
}
```

### Solution 2: Shell Wrapper Script

Create a wrapper script that sets project-specific variables:

1. Create `~/.claude/scripts/serena-wrapper.sh`:

```bash
#!/bin/bash
# Serena wrapper script that uses current directory as project

# Get Serena installation path from global env
SERENA_INSTALL="${SERENA_INSTALL_PATH:-$HOME/dev/serena}"

# Use current working directory as project path
PROJECT_PATH="$(pwd)"

# Launch Serena with the correct paths
exec uv run --directory "$SERENA_INSTALL" serena-mcp-server \
  --context ide-assistant \
  --project "$PROJECT_PATH" \
  "$@"
```

2. Update the global configuration to use the wrapper:

```json
// In ~/.claude/mcp/serena-server.json
{
  "mcpServers": {
    "serena": {
      "command": "/home/your-username/.claude/scripts/serena-wrapper.sh"
    }
  }
}
```

### Solution 3: Dynamic Configuration Script

Create a script that generates the appropriate configuration:

```bash
#!/bin/bash
# ~/.claude/scripts/setup-project-env.sh

# Function to set up project-specific MCP configuration
setup_project_mcp() {
  local project_dir="${1:-$(pwd)}"

  cat > .mcp.json << EOF
{
  "mcpServers": {
    "serena": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${SERENA_INSTALL_PATH}",
        "serena-mcp-server",
        "--context",
        "ide-assistant",
        "--project",
        "${project_dir}"
      ]
    }
  }
}
EOF
  echo "✅ Created .mcp.json for project: $project_dir"
}

# Usage
setup_project_mcp
```

### Solution 4: Claude Code Startup Hook

If Claude Code is started from within a project directory, you can use a startup script:

```bash
#!/bin/bash
# ~/bin/claude-project

# Export project-specific variables
export SERENA_PROJECT_PATH="$(pwd)"

# Start Claude Code
exec claude "$@"
```

Then use `claude-project` instead of `claude` when starting from a project directory.

## Best Practices

1. **Use Project-Specific .mcp.json**: This is the most reliable method as it doesn't depend on environment variable loading order

2. **Avoid Hardcoding Paths**: Use relative paths (`.`) or `$(pwd)` when possible

3. **Document Project Setup**: Add a `.claude/README.md` in your project explaining any special configuration

4. **Git Ignore Local Configs**: Add to `.gitignore`:

   ```
   .mcp.json
   .env.local
   .claude/settings.local.json
   ```

## Example Project Setup

For a typical project:

```bash
my-project/
├── .mcp.json              # Project-specific MCP servers
├── .claude/
│   ├── settings.local.json # Project-specific Claude settings
│   └── README.md          # Project-specific Claude documentation
├── .gitignore             # Ignore local configs
└── ... (project files)
```

## Debugging

To verify environment variables are loaded:

1. Check Claude Code's environment:

   ```bash
   # In Claude, ask it to run:
   echo $SERENA_INSTALL_PATH
   echo $SERENA_PROJECT_PATH
   ```

2. Test MCP server directly:

   ```bash
   # Test if the configuration works
   uv run --directory $SERENA_INSTALL_PATH serena-mcp-server \
     --context ide-assistant \
     --project $(pwd) \
     --help
   ```

## FAQ

**Q: Why doesn't Claude Code load my project's .env file?**
A: Claude Code only loads `~/.claude/.env` globally. For project-specific values, use `.mcp.json` or wrapper scripts.

**Q: Can I chain multiple .env files?**
A: No, Claude Code doesn't support .env file chaining. Use the solutions above for project-specific configuration.

**Q: What takes precedence?**
A: Project `.mcp.json` > Global `~/.claude/mcp/*.json` > Built-in defaults
