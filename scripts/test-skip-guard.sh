#!/usr/bin/env bash
# =============================================================================
# Test-Skip-Marker Guard -- PostToolUse Hook (Edit, Write, MultiEdit)
# =============================================================================
# Fires after every Edit/Write/MultiEdit call. When the touched file's path
# looks like a test file, checks whether THIS call newly introduced a
# test-skip or test-ignore marker (diff-aware: a marker that already existed
# before the call, and is merely carried through unchanged, does not
# re-trigger).
#
# CLAUDE.md's code-quality rule states: never propose `pytest.mark.skip` (or
# an equivalent skip/ignore marker) to silence a failing test; fix the actual
# issue instead. That rule has no automated check today; this hook is it.
#
# Markers checked: .skip(, xit(, xdescribe(, @pytest.mark.skip, #[ignore],
# t.Skip(
#
# Diff-awareness: the guard counts marker-matching lines before and after
# this call and only blocks when the count rises.
#   - Edit: "before" is tool_input.old_string, "after" is tool_input.new_string.
#   - Write: "before" is the file currently on disk (0 if the file is new),
#     "after" is tool_input.content.
#   - MultiEdit: "before"/"after" are the concatenation of old_string/
#     new_string across tool_input.edits[].
# A pre-existing marker that is left untouched, moved, or reworded (without
# increasing the total count) is allowed through; only a net-new marker
# blocks. This means a single call that removes one marker and adds a
# different one nets to zero and is not caught -- see the #EDGE note below.
#
# Exit codes:
#   0 -- not a test file, marker count did not increase, or tool shape not
#        recognized (silent)
#   2 -- marker newly introduced by this call; stderr is fed back to Claude,
#        who must justify the marker (tracked exception) or fix it
#
# Fail-safe: any internal error (missing jq, empty stdin, unrecognized
# tool_input shape) exits 0. A bug in this guard must never block a
# legitimate edit.
#
# Smoke test (match case: Edit introduces a new skip):
#   echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x_test.py","old_string":"def test_x(): pass","new_string":"@pytest.mark.skip\ndef test_x(): pass"}}' | bash test-skip-guard.sh; echo "exit=$?"
# Smoke test (pass-through case: pre-existing skip carried through unchanged):
#   echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x_test.py","old_string":"@pytest.mark.skip\ndef test_x(): pass","new_string":"@pytest.mark.skip\ndef test_x(): pass  # renamed"}}' | bash test-skip-guard.sh; echo "exit=$?"
# =============================================================================

set -uo pipefail

if ! command -v jq &>/dev/null; then
    exit 0
fi

CONTEXT=$(cat 2>/dev/null || true)
[[ -z "$CONTEXT" ]] && exit 0

TOOL_NAME=$(jq -r '.tool_name // empty' 2>/dev/null <<< "$CONTEXT")
FILE_PATH=$(jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null <<< "$CONTEXT")
[[ -z "$FILE_PATH" ]] && exit 0

# Does the path look like a test file? Match conventional test directories and
# filename patterns specifically, not a bare `*test*`/`*spec*` substring, which
# false-positives on ordinary files whose name happens to contain that
# substring (docs/latest.md, src/contest_rules.py, attestation.md).
# #ASSUME: this fixed list of directory segments and filename suffixes covers
# the test-file conventions actually in use across this repo's supported
# languages (Python, Go, JS/TS, Ruby, Java). A convention outside this list
# (e.g. a Rust `#[cfg(test)]` module, or a nonstandard in-house layout) is
# silently treated as a non-test file and skipped.
# #VERIFY: if a skip marker slips through in a language/layout not listed
# here, add its pattern to one of the two case statements below rather than
# widening the marker regex.
IS_TEST_FILE=0
case "$FILE_PATH" in
    */tests/*|*/test/*|*/__tests__/*|*/spec/*|tests/*|test/*|__tests__/*|spec/*)
        IS_TEST_FILE=1
        ;;
esac

if [[ "$IS_TEST_FILE" -eq 0 ]]; then
    BASENAME="${FILE_PATH##*/}"
    case "$BASENAME" in
        test_*.py|*_test.py|*_test.go|*.test.ts|*.test.tsx|*.test.js|*.test.jsx|*.test.mjs|*.test.cjs|*.spec.ts|*.spec.tsx|*.spec.js|*.spec.jsx|*_spec.rb|Test*.java|*Test.java|*Tests.java)
            IS_TEST_FILE=1
            ;;
    esac
fi

[[ "$IS_TEST_FILE" -eq 0 ]] && exit 0

SKIP_PATTERN='(\.skip\(|xit\(|xdescribe\(|@pytest\.mark\.skip|#\[ignore\]|t\.Skip\()'

# Count marker-matching lines in a string; never fails the script (grep exits
# 1 on no match, which is a normal "zero" result here, not an error).
count_markers() {
    grep -cE "$SKIP_PATTERN" <<< "$1" 2>/dev/null || true
}

# #ASSUME: tool_input carries old_string/new_string for Edit, a per-edit
# `edits[]` array for MultiEdit, and a full-file `content` field for Write --
# the shapes documented for Claude Code's Edit/Write/MultiEdit tools. The
# counts below compare "before this call" against "after this call" using
# those fields directly, instead of re-reading the file from disk, so a
# marker that predates this call and is merely carried through unchanged
# does not re-trigger.
# #VERIFY: if a future Claude Code release changes these field names, the jq
# lookups return empty, OLD_COUNT/NEW_COUNT both resolve to 0, and the branch
# below falls through to the fail-safe (exit 0) rather than blocking on
# malformed input.
case "$TOOL_NAME" in
    Edit)
        OLD_STRING=$(jq -r '.tool_input.old_string // empty' 2>/dev/null <<< "$CONTEXT")
        NEW_STRING=$(jq -r '.tool_input.new_string // empty' 2>/dev/null <<< "$CONTEXT")
        OLD_COUNT=$(count_markers "$OLD_STRING")
        NEW_COUNT=$(count_markers "$NEW_STRING")
        MATCH_SOURCE="$NEW_STRING"
        ;;
    MultiEdit)
        OLD_STRING=$(jq -r '[.tool_input.edits[]?.old_string // ""] | join("\n")' 2>/dev/null <<< "$CONTEXT")
        NEW_STRING=$(jq -r '[.tool_input.edits[]?.new_string // ""] | join("\n")' 2>/dev/null <<< "$CONTEXT")
        OLD_COUNT=$(count_markers "$OLD_STRING")
        NEW_COUNT=$(count_markers "$NEW_STRING")
        MATCH_SOURCE="$NEW_STRING"
        ;;
    Write)
        CONTENT=$(jq -r '.tool_input.content // empty' 2>/dev/null <<< "$CONTEXT")
        # #EDGE: a file that does not yet exist on disk has an implicit
        # pre-existing count of 0, so any marker in `content` counts as
        # newly introduced by this Write.
        if [[ -f "$FILE_PATH" ]]; then
            OLD_COUNT=$(grep -cE "$SKIP_PATTERN" "$FILE_PATH" 2>/dev/null || true)
        else
            OLD_COUNT=0
        fi
        NEW_COUNT=$(count_markers "$CONTENT")
        MATCH_SOURCE="$CONTENT"
        ;;
    *)
        # Unrecognized tool: fail safe rather than guess at the payload shape.
        exit 0
        ;;
esac

# #EDGE: counting rather than presence-checking means a call that removes one
# marker and introduces a different one in the same edit nets to zero and is
# not caught. Accepted trade-off: the guard's purpose is to stop a skip from
# being freshly introduced to silence a failure, not to police every marker
# rewrite; a net-flat count is treated as no new skip being added.
[[ "$NEW_COUNT" -le "$OLD_COUNT" ]] && exit 0

MATCH=$(grep -nE "$SKIP_PATTERN" <<< "$MATCH_SOURCE" 2>/dev/null || true)

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
