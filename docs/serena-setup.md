---
schema_type: common
title: "Serena MCP Server Setup Guide"
status: published
owner: core-maintainer
purpose: "Setup and configuration guide for the Serena MCP server integration with Claude Code."
tags:
  - setup
  - configuration
  - integration
---

Serena is an AI-powered development assistant that integrates with Claude Code through the MCP protocol.

## Installation Prerequisites

1. Install Serena locally:

   ```bash
   git clone https://github.com/oraios/serena.git ~/dev/serena
   cd ~/dev/serena
   uv pip install -e .
   ```

2. Configure environment variables in `~/.claude/.env`:

   ```bash
   # Path to your Serena installation
   SERENA_INSTALL_PATH=/home/your-username/dev/serena

   # Default project path (can be overridden)
   SERENA_PROJECT_PATH=/home/your-username/dev/current-project
   ```

## Usage Modes

### 1. Standard Mode (stdio - Recommended)

The global configuration uses stdio mode by default. To use Serena with your current project:

```bash
# Option 1: Update .env with current project
echo "SERENA_PROJECT_PATH=$(pwd)" >> ~/.claude/.env

# Option 2: Create project-specific override
echo "SERENA_PROJECT_PATH=$(pwd)" >> .env.local
```

### 2. SSE Mode (HTTP-based)

For SSE mode, you need to:

1. Start Serena server manually:

   ```bash
   uv run --directory ~/dev/serena serena-mcp-server \
     --transport sse \
     --port 8000 \
     --context ide-assistant \
     --project $(pwd)
   ```

2. Use the SSE configuration:

   ```bash
   # Copy the SSE example to your project
   cp ~/.claude/mcp/serena-sse-server.json.example .mcp.json
   ```

## Context Options

Serena supports different contexts for different use cases:

- `ide-assistant` - Best for Claude Code integration
- `desktop-app` - For desktop application development
- `agent` - For autonomous agent workflows

## Project-Specific Configuration

To override the global Serena configuration for a specific project:

1. Create a project-specific `.mcp.json`:

   ```json
   {
     "mcpServers": {
       "serena": {
         "command": "uv",
         "args": [
           "run",
           "--directory",
           "/home/your-username/dev/serena",
           "serena-mcp-server",
           "--context",
           "ide-assistant",
           "--project",
           "."
         ]
       }
     }
   }
   ```

2. Or use a project-specific environment variable:

   ```bash
   # In your project directory
   echo "SERENA_PROJECT_PATH=$(pwd)" > .env.serena
   source .env.serena
   ```

## First Steps After Connection

1. Ask Claude: "Read the initial instructions"
2. Let Claude activate and index your project
3. The Serena dashboard will be available at: `http://localhost:24282/dashboard/index.html`

## Troubleshooting

### Serena not starting

- Check if `SERENA_INSTALL_PATH` is correct
- Verify Serena is installed: `uv run --directory $SERENA_INSTALL_PATH serena-mcp-server --help`

### Project not found

- Ensure `SERENA_PROJECT_PATH` points to a valid directory
- Use absolute paths instead of relative paths

### Connection issues

- Check if another instance is running on the same port (for SSE mode)
- Verify Claude Code has permission to execute the command

## Advanced Usage

### Multiple Projects

Create aliases for different projects:

```bash
# In ~/.bashrc or ~/.zshrc
alias serena-project1='export SERENA_PROJECT_PATH=/path/to/project1'
alias serena-project2='export SERENA_PROJECT_PATH=/path/to/project2'
```

### Custom Modes

Serena supports multiple modes that can be combined:

- `planning` - For project planning and architecture
- `editing` - For code editing assistance
- `one-shot` - For single-task execution
- `interactive` - For ongoing conversation (default)

Example:

```json
"args": [
  "...",
  "--mode", "planning,editing"
]
```
