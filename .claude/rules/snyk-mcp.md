---
paths:
  - "**/pyproject.toml"
  - "**/requirements*.txt"
  - "**/uv.lock"
---

# Snyk MCP: Dependency Review Rule

When a dependency is added or upgraded in a file this rule matches:

1. Before writing the change, invoke `snyk_package_health_check` on the package
   being added or upgraded to surface advisory, popularity, and known-issue
   signal. After the change is written, when a deeper project-wide scan is
   warranted, invoke `snyk_sca_scan` on the directory containing the nearest
   ancestor `pyproject.toml` or `requirements*.txt`; fall back to the git
   repository root (`git rev-parse --show-toplevel`) when no closer anchor exists.
2. If either tool returns any HIGH or CRITICAL findings, surface them to the user
   before proceeding.
3. Do NOT run `snyk monitor` automatically (it is a CLI-only command, not an MCP
   tool, and it creates persistent dashboard entries).
4. Do NOT block the edit based solely on Snyk output; report findings, then
   continue unless the user explicitly asks you to stop.

When these tools are not available (MCP server not configured or `SNYK_TOKEN` not
exported in the current shell), note the gap and continue without blocking.

**Full setup instructions:** `~/.claude/standards/snyk-mcp-setup.md`
**Always-on authoring rule:** `~/.claude/rules/snyk-secure-at-inception.md`
