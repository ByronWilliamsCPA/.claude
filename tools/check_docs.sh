#!/usr/bin/env bash
# check_docs.sh — local documentation validation gate
#
# Runs four checks:
#   1. Frontmatter schema validation (new docs directories only; legacy dirs exempt)
#   2. MkDocs strict build (broken links, missing files)
#   3. Required new-docs directories exist
#   4. Diagram SVG files present
#
# Usage: bash tools/check_docs.sh
# Exit 0 if all pass, 1 if any fail.
#
# Exempt from frontmatter validation (legacy directories, left buildable-but-unlinked):
#   docs/guides/, docs/development/, docs/planning/, docs/superpowers/,
#   docs/content_reviews/, docs/ADRs/

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FAILURES=0

check() {
    local label="$1"
    local result="$2"  # "ok" or error message
    printf "  %-52s" "$label"
    if [[ "$result" == "ok" ]]; then
        echo "PASS"
    else
        echo "FAIL"
        echo "$result" | sed 's/^/    /'
        FAILURES=$((FAILURES + 1))
    fi
    return 0
}

echo ""
echo "docs validation"
echo "============================================================"

# 1. Frontmatter schema — scoped to new persona directories only
# Legacy dirs (docs/development/, docs/guides/, etc.) are explicitly exempt per ADR-007.
NEW_DOC_DIRS=(
    docs/getting-started
    docs/architecture
    docs/reference
    docs/contributing
    docs/frontmatter-standard.md
)
fm_out=$(uv run python tools/validate_front_matter.py "${NEW_DOC_DIRS[@]}" 2>&1)
fm_errors=$(echo "$fm_out" | grep -v ": OK$" | grep -v "^$" || true)
if [[ -z "$fm_errors" ]]; then
    check "frontmatter schema (new dirs)" "ok"
else
    check "frontmatter schema (new dirs)" "$fm_errors"
fi

# 2. MkDocs strict build — suppress known-benign noise:
#    - git-revision-date timestamp ordering warnings (cosmetic, not structural)
#    - MkDocs 2 deprecation banner (framework-level, not docs-level)
mkdocs_out=$(DISABLE_MKDOCS_2_WARNING=true uv run mkdocs build --strict 2>&1 || true)
mkdocs_errors=$(echo "$mkdocs_out" \
    | grep -E "^(WARNING|ERROR|CRITICAL)" \
    | grep -v "git-revision-date-localized-plugin" \
    | grep -v "^WARNING:root:" \
    | grep -v "MkDocs may break" \
    || true)
if [[ -z "$mkdocs_errors" ]]; then
    check "mkdocs strict build" "ok"
else
    check "mkdocs strict build" "$mkdocs_errors"
fi

# 3. Required directories exist
dir_errors=""
for dir in docs/getting-started docs/architecture docs/architecture/adr \
           docs/architecture/diagrams docs/reference docs/contributing; do
    if [[ ! -d "$REPO_ROOT/$dir" ]]; then
        dir_errors+="Missing: $dir"$'\n'
    fi
done
if [[ -z "$dir_errors" ]]; then
    check "new doc directories present" "ok"
else
    check "new doc directories present" "$dir_errors"
fi

# 4. Diagram SVGs present
svg_errors=""
for svg in install_layer hook_pipeline agent_skill_dispatch mcp_tier_loading; do
    path="docs/architecture/diagrams/${svg}.svg"
    if [[ ! -f "$REPO_ROOT/$path" ]]; then
        svg_errors+="Missing: $path"$'\n'
    fi
done
if [[ -z "$svg_errors" ]]; then
    check "diagram SVGs present" "ok"
else
    check "diagram SVGs present" "$svg_errors"
fi

echo "============================================================"
if [[ $FAILURES -eq 0 ]]; then
    echo "All checks passed."
else
    printf "%d check(s) failed.\n" "$FAILURES"
fi
echo ""

exit $FAILURES
