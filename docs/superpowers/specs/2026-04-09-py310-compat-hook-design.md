---
schema_type: common
title: "Python Version Compatibility Hook — Design Spec"
status: published
owner: core-maintainer
purpose: "Design specification for a PostToolUse hook that detects Python 3.10 floor and 3.14 ceiling compatibility violations immediately after Edit or Write tool calls."
tags:
  - automation
  - tooling
  - specifications
  - ci_cd
---

> **Date**: 2026-04-09
> **Status**: Approved
> **Scope**: Global `~/.claude` tooling (dev repo at `~/dev/.claude`)

## Problem

Ruff's `UP017` auto-fix introduced `datetime.UTC` across 130+ files in a Python 3.10-target
project, requiring a bulk revert. The root cause: no automated check existed to catch 3.11+
patterns after Claude edits a file. A PostToolUse hook closes this gap by warning Claude
immediately — before any commit — whenever a `.py` file contains patterns that violate either
the floor (Python 3.10) or ceiling (Python 3.14) compatibility boundaries.

## Goals

- Warn Claude immediately after any `Edit` or `Write` on a `.py` file
- Cover both boundaries: 3.11+ patterns that break the 3.10 floor, and deprecated patterns
  removed in 3.14
- Zero false-positives on non-Python files (silent skip)
- Produce structured, actionable output so Claude can fix everything in one pass
- Degrade gracefully when optional dependencies (`python3`, `jq`) are unavailable

## Non-Goals

- Does not block edits (PostToolUse hooks cannot block tool calls)
- Does not scan entire repositories — file-level only, triggered per edit
- Does not parse `pyproject.toml` for per-project version targets (Option C: single
  conservative floor applied globally)
- Does not replace ruff or pre-commit — complements them with real-time feedback

## Architecture

```text
Edit/Write tool fires
      ↓
PostToolUse hook (settings.json) → bash $HOME/.claude/scripts/py310-compat-check.sh
      ↓
  Parse file path from stdin JSON via jq
      ↓
  Guard: not a .py file → exit 0 (silent)
  Guard: file does not exist → exit 0 (silent)
      ↓
  Tier 1: grep scan — always runs
    Floor patterns (3.11+ APIs/imports that break Python 3.10)
    Ceiling patterns (deprecated in 3.12, removed in 3.14)
      ↓
  Tier 2: Python AST scan — runs if python3 in PATH, always alongside Tier 1
    Syntactic patterns grep cannot reliably detect
    (match/case, except*, parenthesized with statements)
      ↓
  Merge all findings
  No findings → exit 0 (silent, no log entry)
  Findings present → print structured warning to stdout, log to file
```

Claude Code surfaces PostToolUse stdout as a tool result annotation. Claude reads it
immediately after the edit and can fix all violations before proceeding.

## Components

### 1. `scripts/py310-compat-check.sh`

Single bash script. Lives in `dev/.claude/scripts/`, referenced via symlink as
`$HOME/.claude/scripts/py310-compat-check.sh`.

**Structure:**

```text
Header + set -euo pipefail
Log setup → ~/.claude/logs/py310-compat-check.log
Parse stdin JSON → extract file_path via jq
Guards (non-.py, missing file)
Tier 1: grep loop over pattern table
Tier 2: python3 AST heredoc (skipped with logged warning if python3 unavailable)
Merge findings array
Format and print output if findings present
exit 0
```

### 2. Hook entry in `settings.json`

Add `PostToolUse` array to the existing `hooks` object:

```json
"PostToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [
      {
        "type": "command",
        "command": "bash $HOME/.claude/scripts/py310-compat-check.sh"
      }
    ]
  }
]
```

## Pattern Inventory

### Tier 1 — grep patterns

| Label | Pattern (regex) | Boundary | Recommended fix |
| ----- | --------------- | -------- | --------------- |
| `[FLOOR 3.11+]` | `datetime\.UTC` | Requires 3.11+ | `datetime.timezone.utc` or compat layer |
| `[FLOOR 3.11+]` | `^import tomllib` / `from tomllib` | Requires 3.11+ | `tomli` with conditional import |
| `[FLOOR 3.11+]` | `ExceptionGroup\|BaseExceptionGroup` | Requires 3.11+ | `exceptiongroup` backport |
| `[FLOOR 3.11+]` | `from typing import.*\bSelf\b` | Requires 3.11+ | `typing_extensions.Self` |
| `[FLOOR 3.11+]` | `from typing import.*\bLiteralString\b` | Requires 3.11+ | `typing_extensions.LiteralString` |
| `[FLOOR 3.11+]` | `fromisoformat.*Z["']` | Z suffix requires 3.11+ (best-effort: matches literal Z strings only) | Normalize to `+00:00` first |
| `[CEILING 3.14]` | `datetime\.utcnow\(\)` | Deprecated 3.12, removed 3.14 | `datetime.now(timezone.utc)` |
| `[CEILING 3.14]` | `datetime\.utcfromtimestamp\(` | Deprecated 3.12, removed 3.14 | `datetime.fromtimestamp(ts, datetime.timezone.utc)` |

### Tier 2 — Python AST patterns

| Label | AST node | Boundary | Recommended fix |
| ----- | -------- | -------- | --------------- |
| `[FLOOR 3.11+]` | `TryStar` (`except*`) | Requires 3.11+ | Restructure error handling |
| `[FLOOR 3.11+]` | `typing.Self` / `typing.LiteralString` | Requires 3.11+ | Use `typing_extensions` |

Note: `match/case` (`ast.Match`) is **not** flagged. Structural pattern matching was
introduced in Python 3.10, which is the project's floor. `match` statements are valid
throughout the supported range (3.10–3.14).

Note: Parenthesized `with` statements are not detectable via AST alone (both
`with (a, b):` and `with a, b:` produce identical AST nodes), so this pattern is omitted.

## Output Format

**No findings** — no output, no log entry. Hook is invisible.

**Findings present:**

```text
⚠ Python compatibility issue(s) detected: src/pipeline/processor.py

  [FLOOR 3.11+] line 14: `import tomllib` — requires Python 3.11+
                          Fix: use `import tomli as tomllib` with a try/except
  [FLOOR 3.11+] line 42: `datetime.UTC` — requires Python 3.11+
                          Fix: use `datetime.timezone.utc` or a compat layer
  [CEILING 3.14] line 88: `datetime.utcnow()` — deprecated 3.12, removed 3.14
                           Fix: use `datetime.datetime.now(datetime.timezone.utc)`

Fix all items above before committing. Python 3.10 (floor) and 3.14 (ceiling) compatibility required.
```

## Error Handling

| Condition | Behavior |
| --------- | -------- |
| File is not `.py` | `exit 0`, no output, no log |
| File does not exist | `exit 0`, no output, no log |
| `jq` not found | Log warning, `exit 0` — never block Claude on missing tooling |
| `python3` not in PATH | Log warning, emit Tier 1 results only, note AST skipped in output |
| AST parse fails (syntax error in file) | Log error, emit Tier 1 results only |
| Any unexpected error | `exit 0` — hook must never cause Claude to stop working |

The script never exits non-zero. PostToolUse hooks that exit non-zero are treated as
infrastructure failures by Claude Code.

## Logging

Findings and degradation events are appended to `~/.claude/logs/py310-compat-check.log`:

```text
[2026-04-09 14:23:01] FINDING floor:datetime.UTC line=42 file=src/pipeline/processor.py
[2026-04-09 14:23:01] FINDING ceiling:utcnow line=88 file=src/pipeline/processor.py
[2026-04-09 14:23:01] WARN python3 not found — AST scan skipped
```

Clean runs produce no log entries (log file stays small).

## Testing

Five test cases to verify before shipping:

1. **Floor violation**: Edit a `.py` file to include `datetime.UTC` — hook should print the
   floor warning with correct line number
2. **Ceiling violation**: Edit a `.py` file to include `datetime.datetime.utcnow()` — hook
   should print the ceiling warning (pattern matches both `datetime.utcnow()` and
   `datetime.datetime.utcnow()` as a substring)
3. **Clean file**: Edit a `.py` file with no violations — hook should produce no output
4. **Non-Python file**: Edit a `.md` file — hook should produce no output
5. **AST pattern**: Edit a `.py` file to include `except*` — Tier 2 should detect it as
   a 3.11+ floor violation (`match/case` is intentionally not flagged — valid at 3.10 floor)

## File Locations

| File | Purpose |
| ---- | ------- |
| `dev/.claude/scripts/py310-compat-check.sh` | The hook script |
| `~/.claude/scripts/py310-compat-check.sh` | Symlink created by `setup.sh` |
| `~/.claude/settings.json` | PostToolUse hook registration |
| `~/.claude/logs/py310-compat-check.log` | Runtime log (findings + degradation events) |
