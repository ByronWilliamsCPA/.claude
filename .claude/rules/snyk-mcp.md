---
paths:
  - "**/pyproject.toml"
  - "**/requirements*.txt"
  - "**/uv.lock"
---

# Snyk MCP: Dependency Review Rule

When a dependency is added or upgraded in a file this rule matches:

1. After the change is written, invoke `snyk_test` on the directory containing the
   nearest ancestor `pyproject.toml` or `requirements*.txt`; fall back to the git
   repository root (`git rev-parse --show-toplevel`) when no closer anchor exists.
2. If `snyk_test` returns any HIGH or CRITICAL findings, surface them to the user
   before proceeding.
3. Do NOT invoke `snyk_monitor` automatically.
4. Do NOT block the edit based solely on `snyk_test` output; report findings,
   then continue unless the user explicitly asks you to stop.

When `snyk_test` is not available (MCP server not configured or `SNYK_TOKEN` not
exported in the current shell), note the gap and continue without blocking.

**Full setup instructions:** `~/.claude/standards/snyk-mcp-setup.md`
