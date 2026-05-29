# 02 - Legacy Code Patterns

The Python surface is modern. Zero old `typing` generics (`List`/`Dict`/`Optional`), zero `.format()` or `%` formatting, zero `os.path` (pathlib in 47 files, matching the PTH house standard), zero deprecated stdlib APIs, zero commented-out code blocks, and all 20 lint suppressions carry rule codes. `ruff check --statistics` exited 0 with no output. The only legacy debt is two committed run artifacts and eight stale config toggles. Git history is shallow (50 commits since 2026-05-24), which bounds any age claim.

## LEG-01 - Two session-report HTML files committed at repo root

- Severity: Medium
- Effort: S (gitignore entry plus `git rm --cached`; basis: two files, one ignore rule)
- Evidence: `session-report-20260521-2145.html` (187KB) and `session-report-20260521-2204.html` (277KB), 464KB combined, committed in `dd2bdcd`. `git check-ignore` returns exit 1 (not ignored); `.gitignore` covers `htmlcov/`, `reports/`, and `pytest-html-report/` but not root session reports. A bounded grep found 2 and 12 `secret|password|bearer` token hits respectively, likely audit prose rather than live credentials; content classification is referred to the security domain (see SEC findings).
- Recommendation: Add `session-report-*.html` to `.gitignore` and `git rm --cached` both files. Confirm with the security domain that neither file leaks a live credential before removing from history.

## LEG-02 - Eight `.disabled` MCP config files retained as dead toggles

- Severity: Low
- Effort: S (document or delete; basis: eight small files)
- Evidence: Eight files, 32KB total: `mcp/zen-server.json.disabled` plus seven under `mcp/disabled/`. No loader script references them. Only `mcp/zen-server.json.disabled` is documented (`mcp/README.md:17,73`, zen replaced by PAL); the seven under `mcp/disabled/` are undocumented.
- Recommendation: Document the `mcp/disabled/` directory in `mcp/README.md`, or delete the seven undocumented files (git history preserves them).

## Clean areas

- Old typing generics: 0. Pre-f-string formatting (`.format`/`%`): 0. `os.path` usage: 0 (pathlib in 47 files). Deprecated stdlib APIs: 0.
- Commented-out code blocks: 0. Deferred-work markers (TODO/FIXME/HACK/XXX): 0 in scope. Bare lint suppressions: 0 (all 20 carry rule codes). Vendored-copy candidates: none.

## Machine-readable findings

```json
[
  {"id": "LEG-01", "title": "Two session-report HTML files committed at repo root", "domain": "legacy-code", "severity": "Medium", "effort": "S", "files": ["session-report-20260521-2145.html", "session-report-20260521-2204.html", ".gitignore"], "evidence": "464KB combined, committed dd2bdcd; git check-ignore exit 1 (not ignored); .gitignore lacks a root session-report rule", "recommendation": "Add session-report-*.html to .gitignore and git rm --cached both; confirm no live credential with the security domain first.", "cve": ""},
  {"id": "LEG-02", "title": "Eight .disabled MCP config files retained as dead toggles", "domain": "legacy-code", "severity": "Low", "effort": "S", "files": ["mcp/zen-server.json.disabled", "mcp/disabled/"], "evidence": "8 files, 32KB; no loader references them; 7 under mcp/disabled/ undocumented, only zen-server documented in mcp/README.md:17,73", "recommendation": "Document mcp/disabled/ in mcp/README.md or delete the seven undocumented files.", "cve": ""}
]
```
