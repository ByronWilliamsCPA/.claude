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
    indent=$(printf "%26s" '')

    while IFS=: read -r linenum _; do
        [[ -z "$linenum" ]] && continue
        FINDINGS+=("  ${label} line ${linenum}: ${description}")
        FINDINGS+=("${indent}Fix: ${fix}")
        log "FINDING ${label} line=${linenum} file=${FILE_PATH}"
    done < <(grep -nP "$pattern" "$FILE_PATH" 2>/dev/null || true)
}

# Floor — Python 3.11+ required, breaks 3.10 floor
run_grep "[FLOOR 3.11+]" \
    'datetime\.UTC\b|from datetime import[^#\n]*\bUTC\b' \
    "\`datetime.UTC\` — requires Python 3.11+" \
    "use \`datetime.timezone.utc\` or a compat layer"

run_grep "[FLOOR 3.11+]" \
    '^(import tomllib|from tomllib\b)' \
    "\`tomllib\` — stdlib module requires Python 3.11+" \
    "use \`import tomli as tomllib\` inside try/except ImportError"

run_grep "[FLOOR 3.11+]" \
    '\b(ExceptionGroup|BaseExceptionGroup)\b' \
    "\`ExceptionGroup\` / \`BaseExceptionGroup\` — requires Python 3.11+ (check is best-effort)" \
    "install and use the \`exceptiongroup\` backport package"

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

for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module == 'typing':
        for alias in (node.names or []):
            if alias.name == 'Self':
                print(f"FLOOR_TYPING_SELF:{node.lineno}")
            if alias.name == 'LiteralString':
                print(f"FLOOR_TYPING_LITERALSTRING:{node.lineno}")
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
                FLOOR_TYPING_SELF:*)
                    lineno="${line#FLOOR_TYPING_SELF:}"
                    FINDINGS+=("  [FLOOR 3.11+] line ${lineno}: \`Self\` from \`typing\` — requires Python 3.11+")
                    FINDINGS+=("$(printf "%26s" '')Fix: use \`from typing_extensions import Self\`")
                    log "FINDING FLOOR_TYPING_SELF line=${lineno} file=${FILE_PATH}"
                    ;;
                FLOOR_TYPING_LITERALSTRING:*)
                    lineno="${line#FLOOR_TYPING_LITERALSTRING:}"
                    FINDINGS+=("  [FLOOR 3.11+] line ${lineno}: \`LiteralString\` from \`typing\` — requires Python 3.11+")
                    FINDINGS+=("$(printf "%26s" '')Fix: use \`from typing_extensions import LiteralString\`")
                    log "FINDING FLOOR_TYPING_LITERALSTRING line=${lineno} file=${FILE_PATH}"
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
    echo "  Note: Self/LiteralString detection from \`typing\` requires python3 (AST scan)"
fi

echo ""
echo "Fix all items above before committing. Python 3.10 (floor) and 3.14 (ceiling) compatibility required."

exit 0
