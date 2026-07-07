#!/usr/bin/env bash
# =============================================================================
# Test-Skip-Marker Guard -- PostToolUse Hook (Edit, Write, MultiEdit)
# =============================================================================
# Fires after every Edit/Write/MultiEdit call. When the touched file's path
# looks like a test file, greps its current (post-edit) contents for a
# test-skip or test-ignore marker.
#
# CLAUDE.md's code-quality rule states: never propose `pytest.mark.skip` (or
# an equivalent skip/ignore marker) to silence a failing test; fix the actual
# issue instead. That rule has no automated check today; this hook is it.
#
# Markers checked: .skip(, xit(, xdescribe(, @pytest.mark.skip, #[ignore],
# t.Skip(
#
# Exit codes:
#   0 -- not a test file, or no marker found (silent)
#   2 -- marker found; stderr is fed back to Claude, who must justify the
#        marker (predates this edit, tracked exception) or fix it
#
# Fail-safe: any internal error (missing jq, empty stdin, unreadable file)
# exits 0. A bug in this guard must never block a legitimate edit.
#
# Smoke test (match case):
#   printf '%s\n' "def test_x():" "    pytest.mark.skip" > /tmp/x_test.py
#   echo '{"tool_input":{"file_path":"/tmp/x_test.py"}}' | bash test-skip-guard.sh; echo "exit=$?"
# Smoke test (pass-through case):
#   printf '%s\n' "def test_x(): assert True" > /tmp/x_test.py
#   echo '{"tool_input":{"file_path":"/tmp/x_test.py"}}' | bash test-skip-guard.sh; echo "exit=$?"
# =============================================================================

set -uo pipefail

if ! command -v jq &>/dev/null; then
    exit 0
fi

CONTEXT=$(cat 2>/dev/null || true)
[[ -z "$CONTEXT" ]] && exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null <<< "$CONTEXT")
[[ -z "$FILE_PATH" ]] && exit 0
[[ -f "$FILE_PATH" ]] || exit 0

# Does the path look like a test file?
case "$FILE_PATH" in
    *test*|*spec*|*_test.*|*.test.*)
        ;;
    *)
        exit 0
        ;;
esac

MATCH=$(grep -nE '(\.skip\(|xit\(|xdescribe\(|@pytest\.mark\.skip|#\[ignore\]|t\.Skip\()' "$FILE_PATH" 2>/dev/null || true)

[[ -z "$MATCH" ]] && exit 0

cat >&2 <<EOF
Test-skip marker detected in ${FILE_PATH}:

${MATCH}

CLAUDE.md's code-quality rule: never propose pytest.mark.skip (or an
equivalent .skip()/xit()/xdescribe()/#[ignore]/t.Skip() marker) to silence a
failing test; fix the actual issue instead. This hook is the mechanical
enforcement of that rule.

If this marker predates this edit or is a documented, tracked exception
(ticket or issue reference), say so. Otherwise remove the marker and fix the
underlying failure.
EOF

exit 2
