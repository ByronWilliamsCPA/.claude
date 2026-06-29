# Snyk Secure-at-Inception Rule

> Always-on authoring rule. Loaded every session (no path scope). Replaces the
> malformed block that `snyk mcp configure` auto-injects into CLAUDE.md.

Snyk MCP Server is registered always-on at user scope (see
`~/.claude/rules/mcp-strategy.md` and `~/.claude/standards/snyk-mcp-setup.md`).
Weave security feedback into authoring rather than deferring it to CI.

## When to scan

1. **After a SIGNIFICANT change to first-party code**, before committing, invoke
   `snyk_code_scan` on the changed paths (pass the changed files, e.g. the output
   of `git diff --cached --name-only` filtered to relevant files, not the project
   root). A significant change means new or materially-reworked logic such as
   authentication, session handling, secrets or credential handling, user-input
   processing, deserialization, subprocess or shell execution, or file/path
   handling. Do NOT scan after every trivial edit (typo fixes, comment changes,
   formatting): the significant-change trigger bounds Snyk hosted-test quota.

2. **Before adding or upgrading a dependency**, invoke
   `snyk_package_health_check` on the package to surface advisory, popularity, and
   known-issue signal.

## Fix and rescan

If a scan returns findings, fix the underlying issue in first-party code (or pick
a healthier package / version) and rescan until the relevant paths are clean. Do
not suppress findings to make the scan pass.

## Surface, do not block

Surface any HIGH or CRITICAL finding to the user before proceeding. Do not block
the edit or commit unilaterally; report the finding and let the user decide.

## Quota and availability

- High-frequency and provenance data come from local unlimited tools
  (`osv-scanner`, `pip-audit`, `uv tree`, `npm why`); reserve the hosted Snyk
  scans for the significant-change and pre-add triggers above.
- If the MCP server is not configured or `SNYK_TOKEN` is not exported in the
  current shell, note the gap and continue without blocking.
- `snyk_send_feedback` is optional: use it only to record prevented/fixed deltas
  (telemetry on issues Snyk caught at authoring time), never as a required step.
- `snyk monitor` is a CLI-only command, not an MCP tool; never invoke it
  automatically.

**Full setup and tool reference:** `~/.claude/standards/snyk-mcp-setup.md`
