---
schema_type: common
title: "/doc-audit Skill — Documentation Health Audit"
status: draft
owner: core-maintainer
purpose: "Design spec for a /doc-audit skill that runs four check categories across the docs/ directory, outputs a terminal summary table, and writes a persistent audit-report.md."
tags:
  - tooling
  - specifications
  - automation
  - documentation
---

> **Date**: 2026-04-09
> **Status**: Approved
> **Scope**: Global `~/.claude` tooling (dev repo at `~/dev/.claude`)

## Problem

Usage report analysis identified recurring manual work across data governance documentation
sessions: Claude grepped for frontmatter fields, checked cross-references, and scanned for
stale version references ad hoc, with no consistent order and no persistent output. Findings
lived only in the conversation and were re-discovered in the next session.

## Goals

- Run four documentation health checks in a consistent order every time
- Verify count claims against actual codebase for known categories
- Cross-check version references against `pyproject.toml` and a known current-models list
- Print a terminal summary table and write a persistent `docs/audit-report.md`
- Support optional scope narrowing (subdirectory audit)

## Non-Goals

- No inline annotation of source files — findings go to the report only
- No auto-fix — the skill flags issues; Claude or the user decides what to fix
- No incremental mode — always full sweep of the specified scope
- `docs/audit-report.md` is not committed — it is a generated artifact

## Architecture

Two files:

| File | Action |
|------|--------|
| `.claude/skills/doc-audit/SKILL.md` | New skill — orchestrates the script and writes the report |
| `scripts/doc-audit.py` | New Python script — mechanical scanning, outputs JSON to stdout |

`docs/audit-report.md` is written on each run but added to `.gitignore`.

## Script: `scripts/doc-audit.py`

Standalone Python script using stdlib only (`os`, `re`, `json`, `pathlib`, `yaml` via
manual YAML frontmatter parsing — no PyYAML dependency).

### Invocation

```bash
python3 scripts/doc-audit.py --scope docs/
```

`--scope` is optional; defaults to `docs/`.

### Output

JSON to stdout:

```json
{
  "scope": "docs/",
  "generated": "2026-04-09",
  "summary": {
    "frontmatter": {"pass": 50, "warn": 3, "error": 0},
    "links":       {"pass": 57, "warn": 0, "error": 0},
    "counts":      {"pass": 2,  "warn": 2, "error": 0},
    "versions":    {"pass": 0,  "warn": 4, "error": 0}
  },
  "findings": [
    {
      "category": "frontmatter",
      "severity": "WARN",
      "file": "docs/foo.md",
      "line": 1,
      "message": "missing required field 'owner' (schema_type: common)"
    }
  ]
}
```

Severity values: `ERROR` (broken, must fix), `WARN` (needs review), `INFO` (noted).

### Check 1: Frontmatter Validation

For every `.md` file in scope:

1. Check that the file starts with `---`
2. Extract YAML between the first two `---` delimiters
3. Validate `schema_type` is present and is one of: `common`, `planning`, `adr`
4. Validate required fields per schema type:
   - `common`: `schema_type`, `title`, `status`, `owner`, `purpose`, `tags`
   - `planning`: `schema_type`, `title`, `status`, `owner`, `purpose`, `component`, `source`, `tags`
   - `adr`: `schema_type`, `title`, `status`, `owner`, `purpose`, `tags`
5. Validate tags are snake_case and present in `docs/_data/tags.yml`
6. Flag redundant H1 (title in body matches frontmatter `title`)

Missing frontmatter → `ERROR`. Missing field → `WARN`. Invalid tag → `WARN`.

### Check 2: Broken Link Detection

For every `.md` file in scope:

1. Extract all `[text](path)` links via regex: `\[([^\]]+)\]\(([^)]+)\)`
2. Skip external links (starting with `http://` or `https://`)
3. Skip anchor-only links (starting with `#`)
4. Resolve remaining paths relative to the file's directory
5. Check `os.path.exists()` for each resolved path

Missing target → `ERROR`.

### Check 3: Count Claim Verification

Search all `.md` files in scope for patterns matching `\b(\d+)\s+(agents?|skills?|hooks?|docs?)\b`.

For each match, compare the claimed count against the actual count:

| Category | Actual count command |
|----------|---------------------|
| agents | `len(list(Path('.claude/agents').glob('*.md')))` |
| skills | `len(list(Path('.claude/skills').glob('*/SKILL.md')))` |
| hooks | count PreToolUse + PostToolUse hook entries in `~/.claude/settings.json` (read from the live settings file, not the repo) |
| docs | `len(list(Path('docs').rglob('*.md')))` |

Mismatch → `WARN`. Unrecognized category → `INFO` (flagged for manual review).

### Check 4: Version Reference Staleness

**Python version references:**

Search all `.md` files for `Python 3\.\d+` patterns. Read `pyproject.toml`
`requires-python` field (e.g., `>=3.10,<3.15`). Flag any reference to a Python version
outside the declared range as `WARN`.

**Model name references:**

Search all `.md` files for Claude model name patterns
(`claude-[a-z]+-\d+[-\w]*`). Compare against the known current model list:

```text
claude-sonnet-4-6
claude-opus-4-6
claude-haiku-4-5
claude-haiku-4-5-20251001
```

References to models not in this list → `WARN` with message "model may be outdated".

**Schema version references** (`schema_version \d+`): flag for manual review → `INFO`.

## Skill: `.claude/skills/doc-audit/SKILL.md`

### Invocation

```text
/doc-audit [scope]
```

`scope` is optional (default: `docs/`). Examples:
- `/doc-audit` — audit all of `docs/`
- `/doc-audit docs/superpowers/specs` — audit a subdirectory

### Workflow

1. Determine scope from argument or default `docs/`
2. Run: `python3 scripts/doc-audit.py --scope <scope>`
3. Parse JSON output
4. Print terminal summary table:

```text
Doc Audit Summary
─────────────────────────────────────────────────────
Category       Status      Issues
─────────────────────────────────────────────────────
Frontmatter    ⚠️  WARN    3 docs missing required fields
Broken links   ✅ PASS     0 broken internal links
Count claims   ⚠️  WARN    2 counts don't match reality
Version refs   ⚠️  WARN    4 stale Python version refs
─────────────────────────────────────────────────────
9 issues found. Full report: docs/audit-report.md
```

5. Write `docs/audit-report.md` with full findings (overwrite on each run)
6. Completion message:
   - Any `ERROR`: "Audit complete. X errors require attention before next PR."
   - Only `WARN`/`INFO`: "Audit complete. X warnings flagged for review."
   - All clear: "Audit complete. No issues found."

## Output: `docs/audit-report.md`

```markdown
# Doc Audit Report

Generated: 2026-04-09  Scope: docs/

## Summary

| Category     | Pass | Warn | Error |
|-------------|------|------|-------|
| Frontmatter | 54   | 3    | 0     |
| Broken links | 57  | 0    | 0     |
| Count claims | 2   | 2    | 0     |
| Version refs | 0   | 4    | 0     |

## Frontmatter Issues

- `docs/foo.md` line 1: missing required field `owner` (schema_type: common)

## Broken Links

(none)

## Count Drift

- `docs/overview.md` line 14: claims "15 agents" — actual: 18

## Stale Version References

- `docs/setup.md` line 7: `Python 3.10` — pyproject.toml requires >=3.10,<3.15
```

## `.gitignore` Addition

Add `docs/audit-report.md` to `.gitignore` — generated artifact, not source.

## Testing

Three manual scenarios:

1. **Clean repo**: run on a repo with no issues — all categories show `✅ PASS`, report says "No issues found"
2. **Known violation**: add a doc missing a required frontmatter field — frontmatter check reports it
3. **Broken link**: add a markdown link to a non-existent file — broken links check reports it
