---
paths:
  - "**/pyproject.toml"
  - "**/requirements*.txt"
  - "**/uv.lock"
---

# Snyk MCP: Dependency Review Rule

When a dependency is added or upgraded in a file this rule matches:

1. After the change is written, invoke the `snyk_test` MCP tool on the project root.
2. If `snyk_test` returns HIGH or CRITICAL findings on the newly added package,
   surface the finding to the user before proceeding.
3. Do NOT invoke `snyk_monitor` automatically.
4. Do NOT block the edit based solely on `snyk_test` output; report findings and
   let the user decide.

When `snyk_test` is not available (SNYK_TOKEN not set or MCP server not configured),
note the gap and continue without blocking.

**Full setup instructions:** `~/.claude/standards/snyk-mcp-setup.md`
