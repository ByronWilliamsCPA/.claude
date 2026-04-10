---
schema_type: planning
title: "Python Version Compatibility Hook Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for the PostToolUse hook that detects Python 3.10 floor and 3.14 ceiling violations after Edit or Write tool calls."
component: Development-Tools
source: "docs/superpowers/specs/2026-04-09-py310-compat-hook-design.md"
tags:
  - automation
  - tooling
  - ci_cd
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PostToolUse hook that warns Claude immediately after any `.py` edit when the file contains patterns that violate Python 3.10 floor or 3.14 ceiling compatibility boundaries.

**Architecture:** A bash script (`scripts/py310-compat-check.sh`) reads the modified file path from stdin JSON, skips non-`.py` files silently, runs a grep tier (API/import patterns) and a Python AST tier (syntactic patterns) in sequence, and prints structured warnings to stdout. A new `PostToolUse` entry in `~/.claude/settings.json` fires it on every `Edit` or `Write`.

**Tech Stack:** Bash, grep (PCRE via `-P`), Python 3 `ast` module, jq, `~/.claude/settings.json`

---

## File Structure

| File | Action | Responsibility |
| ---- | ------ | -------------- |
| `dev/.claude/scripts/py310-compat-check.sh` | Create | Hook script — grep + AST scan, structured output |
| `~/.claude/settings.json` | Modify | Wire PostToolUse hook on Edit\|Write matcher |

Note: `~/.claude/scripts/` is a symlink to `dev/.claude/scripts/`, so writing the script to
`dev/.claude/scripts/` makes it immediately available at the path referenced in `settings.json`.

---

### Task 1: Write the test harness

**Files:**
- Create: `/tmp/py310_hook_tests.sh` (temporary — not committed)

Verify the script contract before writing the implementation. This test harness pipes
mock PostToolUse JSON payloads to the script and checks stdout.

- [ ] **Step 1: Create the test harness**

```bash
cat > /tmp/py310_hook_tests.sh << 'TESTS'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$HOME/.claude/scripts/py310-compat-check.sh"
PASS=0
FAIL=0

check() {
    local name="$1"
    local expected="$2"   # "found" or "silent"
    local output="$3"

    if [[ "$expected" == "found" ]] && echo "$output" | grep -q "⚠"; then
        echo "PASS: $name"
        (( PASS++ )) || true
    elif [[ "$expected" == "silent" ]] && [[ -z "$output" ]]; then
        echo "PASS: $name"
        (( PASS++ )) || true
    else
        echo "FAIL: $name"
        echo "  expected=$expected"
        echo "  output='$output'"
        (( FAIL++ )) || true
    fi
}

hook_json() {
    local filepath="$1"
    echo "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"${filepath}\"}}"
}

# Test 1: floor violation — datetime.UTC
cat > /tmp/t1_floor.py << 'EOF'
from datetime import datetime, UTC
result = datetime.now(UTC)
EOF
out=$(hook_json /tmp/t1_floor.py | bash "$SCRIPT" 2>/dev/null)
check "floor violation (datetime.UTC)" "found" "$out"

# Test 2: ceiling violation — datetime.utcnow()
cat > /tmp/t2_ceiling.py << 'EOF'
import datetime
now = datetime.datetime.utcnow()
EOF
out=$(hook_json /tmp/t2_ceiling.py | bash "$SCRIPT" 2>/dev/null)
check "ceiling violation (utcnow)" "found" "$out"

# Test 3: clean Python file
cat > /tmp/t3_clean.py << 'EOF'
import datetime
now = datetime.datetime.now(datetime.timezone.utc)
EOF
out=$(hook_json /tmp/t3_clean.py | bash "$SCRIPT" 2>/dev/null)
check "clean Python file (no output)" "silent" "$out"

# Test 4: non-Python file
cat > /tmp/t4_readme.md << 'EOF'
Use datetime.UTC for UTC times.
EOF
out=$(hook_json /tmp/t4_readme.md | bash "$SCRIPT" 2>/dev/null)
check "non-Python file (no output)" "silent" "$out"

# Test 5: AST pattern — match statement
cat > /tmp/t5_match.py << 'EOF'
def handle(command):
    match command:
        case "quit":
            return False
        case _:
            return True
EOF
out=$(hook_json /tmp/t5_match.py | bash "$SCRIPT" 2>/dev/null)
check "AST pattern (match statement)" "found" "$out"

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
TESTS
chmod +x /tmp/py310_hook_tests.sh
echo "Test harness written to /tmp/py310_hook_tests.sh"
```

- [ ] **Step 2: Run the tests — confirm they all fail**

```bash
bash /tmp/py310_hook_tests.sh
```

Expected: `bash: /home/byron/.claude/scripts/py310-compat-check.sh: No such file or directory`
or `FAIL` on all five tests. This confirms the tests are exercising the real script path.

---

### Task 2: Write the hook script

**Files:**
- Create: `dev/.claude/scripts/py310-compat-check.sh`

- [ ] **Step 1: Write the script**

```bash
cat > /home/byron/dev/.claude/scripts/py310-compat-check.sh << 'SCRIPT'
#!/usr/bin/env bash
# =============================================================================
# Python Version Compatibility Check — PostToolUse Hook
# =============================================================================
# Fires after Edit or Write tool calls. Scans modified .py files for patterns
# that violate Python 3.10 floor or 3.14 ceiling compatibility boundaries.
#
# Tier 1: grep scan — floor (3.11+ APIs/imports) and ceiling (3.14 removed)
# Tier 2: Python AST scan — syntactic patterns (match/case, except*)
#
# Both tiers always run. Output goes to stdout (Claude reads it). Findings
# also appended to ~/.claude/logs/py310-compat-check.log.
#
# Exit codes: always 0 — PostToolUse hooks must never fail
# =============================================================================

set -euo pipefail

LOG_FILE="${HOME}/.claude/logs/py310-compat-check.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# ---- jq guard ----------------------------------------------------------------
if ! command -v jq &>/dev/null; then
    log "WARN jq not found — py310 compat check skipped"
    exit 0
fi

# ---- Read hook context from stdin --------------------------------------------
CONTEXT=$(cat)
[[ -z "$CONTEXT" ]] && exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null <<< "$CONTEXT")
[[ -z "$FILE_PATH" ]] && exit 0

# ---- Guards ------------------------------------------------------------------
# Only check Python files
[[ "$FILE_PATH" != *.py ]] && exit 0

# File must exist (could have been deleted)
[[ ! -f "$FILE_PATH" ]] && exit 0

# ============================================================
# TIER 1: grep scan — API/import patterns
# ============================================================
FINDINGS=()

# run_grep <label> <pcre_pattern> <description> <fix>
run_grep() {
    local label="$1"
    local pattern="$2"
    local description="$3"
    local fix="$4"
    local indent
    indent=$(printf "%$((${#label} + 11))s" '')

    while IFS=: read -r linenum _; do
        [[ -z "$linenum" ]] && continue
        FINDINGS+=("  ${label} line ${linenum}: ${description}")
        FINDINGS+=("${indent}Fix: ${fix}")
        log "FINDING ${label} line=${linenum} file=${FILE_PATH}"
    done < <(grep -nP "$pattern" "$FILE_PATH" 2>/dev/null || true)
}

# Floor — Python 3.11+ required, breaks 3.10 floor
run_grep "[FLOOR 3.11+]" \
    'datetime\.UTC' \
    "\`datetime.UTC\` — requires Python 3.11+" \
    "use \`datetime.timezone.utc\` or a compat layer"

run_grep "[FLOOR 3.11+]" \
    '^(import tomllib|from tomllib\b)' \
    "\`tomllib\` — stdlib module requires Python 3.11+" \
    "use \`import tomli as tomllib\` inside try/except ImportError"

run_grep "[FLOOR 3.11+]" \
    '\b(ExceptionGroup|BaseExceptionGroup)\b' \
    "\`ExceptionGroup\` / \`BaseExceptionGroup\` — requires Python 3.11+" \
    "install and use the \`exceptiongroup\` backport package"

run_grep "[FLOOR 3.11+]" \
    'from typing import[^#\n]*\bSelf\b' \
    "\`Self\` from \`typing\` — requires Python 3.11+" \
    "use \`from typing_extensions import Self\`"

run_grep "[FLOOR 3.11+]" \
    'from typing import[^#\n]*\bLiteralString\b' \
    "\`LiteralString\` from \`typing\` — requires Python 3.11+" \
    "use \`from typing_extensions import LiteralString\`"

run_grep "[FLOOR 3.11+]" \
    "fromisoformat\(.*Z['\"]" \
    "\`fromisoformat\` with Z suffix — Z parsing requires Python 3.11+ (best-effort)" \
    "normalize first: replace trailing Z with +00:00 before calling fromisoformat"

# Ceiling — deprecated 3.12, removed 3.14
run_grep "[CEILING 3.14]" \
    'datetime\.utcnow\(\)' \
    "\`datetime.utcnow()\` — deprecated in 3.12, removed in 3.14" \
    "use \`datetime.datetime.now(datetime.timezone.utc)\`"

run_grep "[CEILING 3.14]" \
    'datetime\.utcfromtimestamp\(' \
    "\`datetime.utcfromtimestamp()\` — deprecated in 3.12, removed in 3.14" \
    "use \`datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)\`"

# ============================================================
# TIER 2: Python AST scan — syntactic patterns
# ============================================================
AST_SKIP_REASON=""

if ! command -v python3 &>/dev/null; then
    AST_SKIP_REASON="python3 not in PATH"
    log "WARN python3 not found — AST scan skipped for ${FILE_PATH}"
else
    AST_OUTPUT=$(python3 - "$FILE_PATH" 2>/dev/null <<'PYEOF'
import ast, sys

try:
    source = open(sys.argv[1]).read()
    tree = ast.parse(source, filename=sys.argv[1])
except SyntaxError as e:
    print(f"AST_ERROR:{e.lineno or 0}")
    sys.exit(0)
except Exception:
    print("AST_ERROR:0")
    sys.exit(0)

for node in ast.walk(tree):
    # match/case — structural pattern matching, Python 3.10+ syntax node
    if type(node).__name__ == "Match":
        print(f"FLOOR_MATCH:{node.lineno}")
    # except* — exception groups, Python 3.11+ TryStar node
    if type(node).__name__ == "TryStar":
        print(f"FLOOR_EXCEPT_STAR:{node.lineno}")
PYEOF
    )

    if [[ "$AST_OUTPUT" == AST_ERROR:* ]]; then
        err_line="${AST_OUTPUT#AST_ERROR:}"
        log "WARN AST parse failed at line ${err_line} in ${FILE_PATH}"
        AST_SKIP_REASON="AST parse failed (syntax error at line ${err_line})"
    else
        while IFS= read -r line; do
            [[ -z "$line" ]] && continue
            case "$line" in
                FLOOR_MATCH:*)
                    lineno="${line#FLOOR_MATCH:}"
                    FINDINGS+=("  [FLOOR 3.10+] line ${lineno}: \`match\` statement — requires Python 3.10+ syntax")
                    FINDINGS+=("$(printf "%26s" '')Fix: rewrite as if/elif chain for 3.10 floor compatibility")
                    log "FINDING FLOOR_MATCH line=${lineno} file=${FILE_PATH}"
                    ;;
                FLOOR_EXCEPT_STAR:*)
                    lineno="${line#FLOOR_EXCEPT_STAR:}"
                    FINDINGS+=("  [FLOOR 3.11+] line ${lineno}: \`except*\` — requires Python 3.11+")
                    FINDINGS+=("$(printf "%26s" '')Fix: restructure to standard try/except handlers")
                    log "FINDING FLOOR_EXCEPT_STAR line=${lineno} file=${FILE_PATH}"
                    ;;
            esac
        done <<< "$AST_OUTPUT"
    fi
fi

# ============================================================
# Output
# ============================================================
if [[ ${#FINDINGS[@]} -eq 0 ]]; then
    exit 0
fi

echo ""
echo "⚠ Python compatibility issue(s) detected: ${FILE_PATH}"
echo ""
for finding in "${FINDINGS[@]}"; do
    echo "$finding"
done

if [[ -n "$AST_SKIP_REASON" ]]; then
    echo ""
    echo "  Note: AST scan skipped (${AST_SKIP_REASON}) — syntactic patterns not checked"
fi

echo ""
echo "Fix all items above before committing. Python 3.10 (floor) and 3.14 (ceiling) compatibility required."

exit 0
SCRIPT
```

- [ ] **Step 2: Make the script executable**

```bash
chmod +x /home/byron/dev/.claude/scripts/py310-compat-check.sh
```

- [ ] **Step 3: Run the test harness — all five tests must pass**

```bash
bash /tmp/py310_hook_tests.sh
```

Expected output:
```text
PASS: floor violation (datetime.UTC)
PASS: ceiling violation (utcnow)
PASS: clean Python file (no output)
PASS: non-Python file (no output)
PASS: AST pattern (match statement)

Results: 5 passed, 0 failed
```

If Test 5 fails, check the Python version: `python3 --version`. The `ast.Match` node
exists in Python 3.10+. If `python3` is 3.9, Test 5 will fail — the AST tier will skip
match detection, which is expected degradation behaviour (not a bug).

- [ ] **Step 4: Verify the output format for a floor violation looks correct**

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/t1_floor.py"}}' \
    | bash /home/byron/dev/.claude/scripts/py310-compat-check.sh
```

Expected:
```text

⚠ Python compatibility issue(s) detected: /tmp/t1_floor.py

  [FLOOR 3.11+] line 1: `datetime.UTC` — requires Python 3.11+
                         Fix: use `datetime.timezone.utc` or a compat layer

Fix all items above before committing. Python 3.10 (floor) and 3.14 (ceiling) compatibility required.
```

- [ ] **Step 5: Verify silence on a clean file**

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/t3_clean.py"}}' \
    | bash /home/byron/dev/.claude/scripts/py310-compat-check.sh
echo "exit code: $?"
```

Expected: no output, `exit code: 0`

- [ ] **Step 6: Commit the script**

```bash
cd /home/byron/dev/.claude
git add scripts/py310-compat-check.sh
git commit -m "feat: add Python 3.10/3.14 compat PostToolUse hook script

Two-tier check: grep for API/import patterns (floor 3.11+, ceiling 3.14)
and Python AST scan for syntactic patterns (match/case, except*).
Degrades gracefully when jq or python3 are unavailable. Always exits 0.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Wire the PostToolUse hook in settings.json

**Files:**
- Modify: `/home/byron/.claude/settings.json`

Note: this file is a direct file at `~/.claude/settings.json`, not a symlink from the dev
repo. Edit it in place. The current `hooks` object contains only `PreToolUse`.

- [ ] **Step 1: Add the PostToolUse entry**

Open `/home/byron/.claude/settings.json`. The current `hooks` block is:

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Skill",
      "hooks": [
        {
          "type": "command",
          "command": "bash $HOME/.claude/scripts/planning-bridge-gate.sh"
        }
      ]
    }
  ]
},
```

Replace it with:

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Skill",
      "hooks": [
        {
          "type": "command",
          "command": "bash $HOME/.claude/scripts/planning-bridge-gate.sh"
        }
      ]
    }
  ],
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
},
```

- [ ] **Step 2: Validate the JSON is well-formed**

```bash
python3 -m json.tool /home/byron/.claude/settings.json > /dev/null && echo "JSON valid"
```

Expected: `JSON valid`

- [ ] **Step 3: Reload Claude Code**

The settings file is read at session start. Restart the Claude Code session (close and
reopen the terminal, or start a new Claude Code session) to pick up the new hook.

- [ ] **Step 4: Run a live smoke test in the reloaded session**

In the new session, ask Claude to edit a temp file with a known violation:

```
Edit /tmp/smoke_test.py to add this line at the top: import datetime; x = datetime.datetime.utcnow()
```

Expected: After the edit, Claude Code surfaces a PostToolUse annotation containing
`⚠ Python compatibility issue(s) detected` with `[CEILING 3.14]` warning for `utcnow`.

---

### Task 4: Clean up and verify log output

**Files:**
- No new files — verification only

- [ ] **Step 1: Check the log file was created with correct entries**

After running the smoke test in Task 3, verify:

```bash
cat ~/.claude/logs/py310-compat-check.log
```

Expected: entries like:
```text
[2026-04-09 14:xx:xx] FINDING [CEILING 3.14] line=1 file=/tmp/smoke_test.py
```

- [ ] **Step 2: Verify log stays empty on clean edits**

```bash
# Note current log size
wc -l ~/.claude/logs/py310-compat-check.log

# Edit a clean Python file (no violations)
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/t3_clean.py"}}' \
    | bash ~/.claude/scripts/py310-compat-check.sh

# Log size must be unchanged
wc -l ~/.claude/logs/py310-compat-check.log
```

Expected: line count identical before and after.

- [ ] **Step 3: Remove temp test fixtures**

```bash
rm -f /tmp/t1_floor.py /tmp/t2_ceiling.py /tmp/t3_clean.py \
       /tmp/t4_readme.md /tmp/t5_match.py /tmp/smoke_test.py \
       /tmp/py310_hook_tests.sh
```

- [ ] **Step 4: Final commit summary**

```bash
cd /home/byron/dev/.claude
git log --oneline -3
```

Expected: the script commit from Task 2 Step 6 in the log. No additional commit needed
for `settings.json` — it is not tracked in the dev repo.

---

## Known Limitations

- **Parenthesized `with` statements**: The Python AST does not distinguish
  `with (a, b):` (3.10+ syntax) from `with a, b:` (valid since 2.7) — both produce
  identical AST nodes. This pattern is omitted from detection to avoid false positives.
  The spec listed it under Tier 2 but accurate detection is not achievable via AST alone.

- **`fromisoformat` Z-suffix detection**: Tier 1 uses a best-effort grep
  (`fromisoformat(.*Z['"]`) that matches literal Z in string arguments. Dynamic strings
  (e.g. `fromisoformat(some_var)`) are not detected.

- **AST scan on Python < 3.10**: `ast.Match` nodes are only parseable when the
  running `python3` is 3.10+. If the system Python is 3.9, `match` statement detection
  silently degrades. The script logs a warning and Tier 1 results still surface.
