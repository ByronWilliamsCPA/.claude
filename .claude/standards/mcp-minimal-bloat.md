# MCP Server Configuration for Minimal Context Bloat

> **Status**: Active | Standard
> **Version**: 1.0.0
> **Last Updated**: 2025-12-12
> **Reference**: [Anthropic Advanced Tool Use Guide](https://www.anthropic.com/engineering/advanced-tool-use)

## The Problem

MCP tools consume context window tokens. A typical setup with 50+ tools consumes ~55-72K tokens upfront, leaving less room for actual conversation and code context.

**Real impact example:**
- 58 tools = ~55K tokens consumed at session start
- With optimization = ~8.7K tokens (85-95% reduction)

## Core Principles

### 1. Keep Always-Loaded Tools to 3-5

Only tools used in nearly every session should load automatically. Everything else should be deferred or triggered on-demand.

**Current Tier 1 (Always Loaded):**

| Server | Tools | Justification |
|--------|-------|---------------|
| zen | thinkdeep, codereview, tiered_consensus, chat | Core reasoning and review |
| context7 | resolve_library_id, get_library_docs | Documentation lookup |
| github | get_file_contents (repos toolset) | Basic file access |

### 2. Defer Everything Else

Tools not needed in every session should be deferred. Claude Code supports this via:
- Not including servers in `mcpServers` (manual activation)
- Using `enabledMcpjsonServers` to selectively enable
- Keeping configs in `mcp/*.json` for reference without loading

### 3. Write Descriptive Tool Descriptions

Poor descriptions cause wrong tool selection. Good descriptions:

```yaml
# BAD
name: query_orders
description: Execute order query

# GOOD
name: search_customer_orders
description: |
  Search for customer orders by date range, status, or total amount.
  Returns: order_id, customer_name, status, total, created_at.
  Use for: order history, sales reports, customer support lookups.
```

### 4. Avoid Similar Tool Names

The most common failures are wrong tool selection when tools have similar names:
- `notification-send-user` vs `notification-send-channel`
- `get_file` vs `get_files` vs `get_file_contents`

**Solution:** Use distinct, action-specific names that clearly differentiate purpose.

## Configuration Strategy

### Recommended settings.json Structure

```json
{
  "mcpServers": {
    // TIER 1 ONLY - Always loaded
    "zen": { /* config */ },
    "context7": { /* config */ }
  },
  // Do NOT list Tier 2/3 servers here
}
```

### Tier 2/3 Servers

Keep configurations in `mcp/*.json` files but **don't** add to `mcpServers`. These serve as:
1. Documentation of available servers
2. Templates for manual activation when needed
3. Reference for environment variables required

### Current Tier Configuration

**Tier 1 - Always Loaded (~3K tokens):**
- `zen` - Core reasoning tools
- `context7` - Library documentation
- `github` - Repository access (consider removing if not always needed)

**Tier 2 - Agent-Bundled (load when specific agents invoked):**

| Agent | Would Load |
|-------|------------|
| security-auditor | zen.secaudit, sentry.*, github.code_security |
| test-engineer | zen.testgen, playwright.* |
| documentation-writer | zen.docgen, mermaid.*, uml.* |
| database-operations | postgres.* |
| devops-deployment | docker.*, github.actions |

**Tier 3 - Keyword-Triggered (load on keyword detection):**

| Keywords | Would Load |
|----------|------------|
| dockerfile, container, k8s | docker.* |
| e2e, browser test, playwright | playwright.* |
| database, sql, postgres | postgres.* |
| diagram, flowchart, mermaid | mermaid.*, uml.* |

## Current Limitation

**Claude Code does not support dynamic tool loading mid-session.**

The tiered strategy is a *design pattern* for when this becomes available. Current workarounds:

1. **Manual activation**: Add server to `mcpServers` when starting a session that needs it
2. **Project-specific configs**: Use `.claude/settings.json` in projects that always need specific tools
3. **Logging for optimization**: Use hooks to track which tools are actually used, then optimize Tier 1

## Implementation Checklist

### Immediate Actions

- [ ] Audit current `mcpServers` - remove anything not used daily
- [ ] Move Tier 2/3 servers out of `mcpServers`
- [ ] Keep Tier 2/3 configs in `mcp/*.json` for documentation
- [ ] Review tool descriptions for clarity

### Hooks for Monitoring

The following hooks track tool usage for future optimization:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "mcp__*",
      "hooks": [{
        "type": "command",
        "command": "$HOME/.claude/scripts/track-mcp-usage.sh"
      }]
    }]
  }
}
```

Review `~/.claude/logs/mcp-usage.log` weekly to identify:
- Tools that should be promoted to Tier 1
- Tools that are never used (candidates for removal)

## Server-Specific Recommendations

### zen (KEEP - Tier 1)

High-value tools for reasoning and code review. Consider requesting the zen-mcp-server maintainer to support `defer_loading` for less-used tools like `docgen`, `secaudit`, `testgen`.

**Always load:** thinkdeep, codereview, chat, tiered_consensus
**Could defer:** debug, precommit, secaudit, testgen, docgen, refactor, analyze

### context7 (KEEP - Tier 1)

Only 2 tools, essential for documentation lookup. Low token cost.

### github (EVALUATE)

Currently loads via Docker with multiple toolsets. Consider:
- If using daily: Keep in Tier 1
- If occasional: Move to Tier 2, activate for PR/issue work

### playwright, postgres, sentry, docker, mermaid, uml (REMOVE from always-loaded)

These should NOT be in `mcpServers` unless the current project specifically requires them. Keep configs in `mcp/*.json` for reference.

## Measuring Success

### Before Optimization
- Count tools loaded: `claude mcp list | wc -l`
- Estimate tokens: ~1K per complex tool, ~500 per simple tool

### After Optimization
- Target: 10-15 tools maximum always-loaded
- Token budget: <10K for tool definitions
- 85%+ of context window preserved for actual work

## Advanced Patterns from Anthropic

### Pattern 1: Tool Search Tool

For 10+ tools, implement a "Tool Search Tool" that:
1. Receives a query about what capability is needed
2. Returns matching tool definitions on-demand
3. Keeps unused tools out of context entirely

**Implementation options:**
```yaml
# search_tools with granularity levels
- name_only: Just tool names (~50 tokens per tool)
- name_description: Names + descriptions (~200 tokens per tool)
- full_schema: Complete definitions (~1000 tokens per tool)
```

### Pattern 2: Filesystem-Based Discovery

From [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp):

Instead of loading all tools upfront, present MCP servers as a filesystem hierarchy:

```text
servers/
├── google-drive/
│   ├── getDocument.ts
│   └── index.ts
├── salesforce/
│   ├── updateRecord.ts
│   └── index.ts
```

Agents can:
1. List available servers (`ls servers/`)
2. Read specific tool definitions only when needed
3. Achieve **98.7% token reduction** (150K → 2K tokens in Anthropic's example)

### Pattern 3: Code-Based Data Processing

**Problem:** Retrieving 10,000 rows through tool calls pollutes context.

**Solution:** Execute filtering/transformation code within the MCP server:

```python
# Instead of returning all rows to Claude
def get_all_orders():
    return db.query("SELECT * FROM orders")  # 10K rows in context

# Filter within the tool
def search_orders(filter_code: str):
    orders = db.query("SELECT * FROM orders")
    # Execute filter_code in sandbox
    return exec_filter(orders, filter_code)  # Only matching rows returned
```

This keeps intermediate results out of Claude's context.

### Pattern 4: Progressive Disclosure

Design MCP servers with layered detail:

1. **Index level:** List of tool names only
2. **Summary level:** Name + one-line description
3. **Detail level:** Full schema with parameters and return types

Claude requests deeper levels only for tools it intends to use.

## Applying These Patterns Today

### What We Can Do Now

| Pattern | Feasibility | Action |
|---------|-------------|--------|
| Reduce always-loaded tools | **High** | Remove servers from `mcpServers` |
| Project-specific configs | **High** | Use per-project `.claude/settings.json` |
| Track usage for optimization | **High** | Already have hooks in place |
| Tool Search Tool | **Low** | Requires MCP server changes |
| Filesystem discovery | **Low** | Requires custom MCP server |
| Progressive disclosure | **Medium** | Could request from zen-mcp-server maintainer |

### Recommended Immediate Changes

Based on Anthropic's guidance, our `settings.json` should only contain:

```json
{
  "mcpServers": {
    "zen": { /* keep - core reasoning */ },
    "context7": { /* keep - documentation */ }
  }
  // Remove: github, playwright, postgres, sentry, docker, mermaid, uml
  // These go in project-specific configs or manual activation
}
```

### For MCP Server Developers

If building or contributing to MCP servers, implement:

1. **`list_tools` endpoint** - Returns tool names only (minimal tokens)
2. **`describe_tool(name)` endpoint** - Returns full schema for one tool
3. **`search_tools(query, detail_level)` endpoint** - Filtered discovery
4. **Data filtering parameters** - Let callers specify what subset they need

### Token Budget Guidelines

| Tool Count | Estimated Tokens | Recommendation |
|------------|------------------|----------------|
| 1-5 | 500-2,500 | Always load |
| 6-15 | 3,000-15,000 | Load for specific projects |
| 16-50 | 8,000-50,000 | Implement Tool Search |
| 50+ | 25,000-100,000+ | Filesystem discovery pattern |

## Quick Reference

```bash
# Check what's currently loaded
claude mcp list

# View usage logs
tail -100 ~/.claude/logs/mcp-usage.log

# Test a Tier 2/3 server standalone
npx -y @playwright/mcp@latest --help
npx -y @crystaldba/postgres-mcp --help

# Temporarily add a server (edit settings.json, reload VS Code)
```

## Related Files

- [mcp_config.yaml](../mcp/mcp_config.yaml) - Full tiered configuration reference
- [mcp-tool-loader.sh](../scripts/mcp-tool-loader.sh) - Dynamic loading script (future use)
- [keyword-tool-trigger.sh](../scripts/keyword-tool-trigger.sh) - Keyword detection hook
- [track-mcp-usage.sh](../scripts/track-mcp-usage.sh) - Usage analytics
