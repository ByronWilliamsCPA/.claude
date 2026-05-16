#!/usr/bin/env bash
# =============================================================================
# Regression tests for scripts/bash-pre-hook.sh bypass-flag guards.
#
# Drives the hook via its real stdin contract (a JSON envelope with a
# .tool_input.command field) and asserts the exit code. Exit 2 means the
# command was blocked; exit 0 means it was allowed.
#
# Run from the repo root:
#   bash tests/scripts/test_bash_pre_hook_bypass_guards.sh
#
# Returns 0 on full pass, 1 if any case fails.
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="${REPO_ROOT}/scripts/bash-pre-hook.sh"

if [[ ! -x "$HOOK" ]]; then
    echo "FAIL: hook not executable at $HOOK" >&2
    exit 1
fi

PASS=0
FAIL=0
FAILED_CASES=()

# Run the hook with a synthesized JSON envelope. Returns the hook's exit code.
run_hook() {
    local cmd="$1"
    local payload
    payload=$(jq -nc --arg c "$cmd" '{tool_input: {command: $c}}')
    printf '%s' "$payload" | bash "$HOOK" >/dev/null 2>&1
    echo "$?"
}

# Assert blocked: hook should exit 2.
assert_blocked() {
    local label="$1" cmd="$2" rc
    rc=$(run_hook "$cmd")
    if [[ "$rc" == "2" ]]; then
        printf '  PASS  [BLOCK ] %s\n' "$label"
        PASS=$((PASS + 1))
    else
        printf '  FAIL  [BLOCK ] %s (got exit %s, want 2)\n' "$label" "$rc"
        FAIL=$((FAIL + 1))
        FAILED_CASES+=("$label")
    fi
}

# Assert allowed: hook should exit 0.
assert_allowed() {
    local label="$1" cmd="$2" rc
    rc=$(run_hook "$cmd")
    if [[ "$rc" == "0" ]]; then
        printf '  PASS  [ALLOW ] %s\n' "$label"
        PASS=$((PASS + 1))
    else
        printf '  FAIL  [ALLOW ] %s (got exit %s, want 0)\n' "$label" "$rc"
        FAIL=$((FAIL + 1))
        FAILED_CASES+=("$label")
    fi
}

echo "=== Critical: quoted-flag bypass (Sonnet Finding A / Copilot inline) ==="
assert_blocked "git commit \"--no-verify\" -m \"msg\"" \
    'git commit "--no-verify" -m "msg"'
assert_blocked "git commit '--no-verify' -m 'msg'" \
    "git commit '--no-verify' -m 'msg'"
assert_blocked 'gh pr merge "--admin" 999' \
    'gh pr merge "--admin" 999'
assert_blocked 'git commit "--no-gpg-sign"' \
    'git commit "--no-gpg-sign"'
assert_blocked 'git -c "commit.gpgsign=false" commit -m bump' \
    'git -c "commit.gpgsign=false" commit -m bump'

echo ""
echo "=== Critical: case-insensitive gpgsign (Finding D) ==="
assert_blocked 'git -c commit.gpgSign=false commit' \
    'git -c commit.gpgSign=false commit'
assert_blocked 'git -c commit.GPGSIGN=false commit' \
    'git -c commit.GPGSIGN=false commit'
assert_blocked 'git -c tag.GpGsIgN=false tag v1.0' \
    'git -c tag.GpGsIgN=false tag v1.0'

echo ""
echo "=== Critical: boolean synonyms for falsy (Finding E) ==="
assert_blocked 'git -c commit.gpgsign=0 commit' \
    'git -c commit.gpgsign=0 commit'
assert_blocked 'git -c commit.gpgsign=no commit' \
    'git -c commit.gpgsign=no commit'
assert_blocked 'git -c commit.gpgsign=off commit' \
    'git -c commit.gpgsign=off commit'
assert_blocked 'git -c tag.gpgsign=NO tag v1' \
    'git -c tag.gpgsign=NO tag v1'

echo ""
echo "=== Critical: eval / bash -c indirection (Finding F) ==="
assert_blocked 'eval "git push --no-verify origin main"' \
    'eval "git push --no-verify origin main"'
assert_blocked "bash -c 'git commit --no-verify -m x'" \
    "bash -c 'git commit --no-verify -m x'"
assert_blocked 'sh -c "gh pr merge --admin 999"' \
    'sh -c "gh pr merge --admin 999"'
assert_blocked 'zsh -c "git -c commit.gpgsign=0 commit"' \
    'zsh -c "git -c commit.gpgsign=0 commit"'

echo ""
echo "=== Critical: gh api admin-merge endpoint (Finding I) ==="
assert_blocked 'gh api -X PUT /repos/foo/bar/pulls/105/merge -f merge_method=squash' \
    'gh api -X PUT /repos/foo/bar/pulls/105/merge -f merge_method=squash'
assert_blocked 'gh api /repos/foo/bar/pulls/12/merge' \
    'gh api /repos/foo/bar/pulls/12/merge'

echo ""
echo "=== Important: regex anchor (Finding O) ==="
# The substring `tag.gpgsign=false` inside `notag.gpgsign=false` must NOT match.
assert_allowed 'git config notag.gpgsign=false' \
    'git config notag.gpgsign=false'

echo ""
echo "=== Cross-command false positives must be ALLOWED (Finding B) ==="
assert_allowed 'git status && npm install --no-verify' \
    'git status && npm install --no-verify'
assert_allowed 'git log && some-tool --admin foo' \
    'git log && some-tool --admin foo'
assert_allowed 'gh pr merge --squash 999 && other-tool --admin' \
    'gh pr merge --squash 999 && other-tool --admin'
assert_allowed 'git status | grep --color=auto something' \
    'git status | grep --color=auto something'

echo ""
echo "=== Commit-message documentation false positives must be ALLOWED ==="
assert_allowed 'git commit -m "fix: use git commit, not --no-verify"' \
    'git commit -m "fix: use git commit, not --no-verify"'
assert_allowed "git commit -m 'docs: explain --admin behavior'" \
    "git commit -m 'docs: explain --admin behavior'"
assert_allowed 'git commit -m "warn about commit.gpgsign=false"' \
    'git commit -m "warn about commit.gpgsign=false"'

echo ""
echo "=== Direct bypass forms must still BLOCK (regression for existing behavior) ==="
assert_blocked 'gh pr merge --admin 999 --squash' \
    'gh pr merge --admin 999 --squash'
assert_blocked 'gh pr merge --squash --admin 999' \
    'gh pr merge --squash --admin 999'
assert_blocked 'git commit --no-verify -m bump' \
    'git commit --no-verify -m bump'
assert_blocked 'git push --no-verify origin feature' \
    'git push --no-verify origin feature'
assert_blocked 'git commit --no-gpg-sign -m bump' \
    'git commit --no-gpg-sign -m bump'
assert_blocked 'git -c commit.gpgsign=false commit -m bump' \
    'git -c commit.gpgsign=false commit -m bump'

echo ""
echo "=== Force-push guard (pre-existing; must still BLOCK) ==="
assert_blocked 'git push --force origin main' \
    'git push --force origin main'
assert_blocked 'git push -f origin master' \
    'git push -f origin master'

echo ""
echo "=== Innocuous commands must be ALLOWED ==="
assert_allowed 'ls -la' \
    'ls -la'
assert_allowed 'git status' \
    'git status'
assert_allowed 'git commit -m bump' \
    'git commit -m bump'
assert_allowed 'gh pr view 105' \
    'gh pr view 105'
assert_allowed 'gh pr merge --squash 999' \
    'gh pr merge --squash 999'
assert_allowed 'git push origin feature/foo' \
    'git push origin feature/foo'
assert_allowed 'git push --force-with-lease origin feature/foo' \
    'git push --force-with-lease origin feature/foo'

echo ""
echo "=== Summary ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "Failed cases:"
    for c in "${FAILED_CASES[@]}"; do
        echo "  - $c"
    done
    exit 1
fi
exit 0
