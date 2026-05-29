#!/usr/bin/env bash
# check-steering-refs.sh -- CLAUDE-011 verifier.
#
# Confirms that file paths and shell commands referenced in CLAUDE.md and
# AGENTS.md resolve against the current repository. A dangling reference is the
# signature of a file move or rename that was not propagated to the steering
# file, which then silently misleads every agent that reads it.
#
# Scope (per the work package gotcha): paths and commands only. This is not a
# prose, style, or completeness gate. Extraction is constrained to the explicit
# patterns below so that ordinary sentences are not parsed as candidate paths.
#
# Extracted references:
#   1. DSL-style path arguments: file_exists:, content_present:,
#      section_present:, content_absent_any:, em_dash_absent:, ai_patterns_absent:
#   2. Global paths under ~/.claude/ and ~/dev/.claude/ (resolved against the
#      repo root, which is the symlink target of ~/.claude/).
#   3. Bare relative paths inside backticks that look like repo files
#      (contain a slash and a file extension, e.g. `.claude/rules/python.md`).
#   4. Single-token commands at the start of a backtick span (e.g. `ruff format`,
#      `pre-commit run`): the leading word must resolve on PATH.
#
# Exit 0 when every extracted reference resolves; exit 1 (listing each broken
# reference) otherwise.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

# Global paths written as ~/.claude/... refer to the installed config tree,
# which is the symlink target of ~/.claude (canonically ~/dev/.claude). That
# tree carries gitignored runtime directories (for example skill-observations/)
# that are not part of a fresh worktree checkout, so resolve global references
# against it when it exists, falling back to the current repo root otherwise.
GLOBAL_ROOT="${HOME}/dev/.claude"
[[ -d "$GLOBAL_ROOT" ]] || GLOBAL_ROOT="$REPO_ROOT"

SOURCES=(
    "CLAUDE.md"
    "AGENTS.md"
)

# Commands that are intentionally not asserted on PATH: they are either project
# runners invoked through uv, or example placeholders, or shell builtins that
# grep would not find as executables. Keeping this list explicit avoids false
# negatives on environments that legitimately lack an optional tool.
ALLOWED_MISSING_COMMANDS=(
    "uv"
    "activate_skill"
)

broken=0

is_allowed_missing() {
    local cmd="$1" allowed
    for allowed in "${ALLOWED_MISSING_COMMANDS[@]}"; do
        [[ "$cmd" == "$allowed" ]] && return 0
    done
    return 1
}

# resolve_path REF
# Normalizes a reference and reports whether it exists on disk. Global
# ~/.claude and ~/dev/.claude references resolve against GLOBAL_ROOT (the
# installed config tree); other references resolve against the repo root.
resolve_path() {
    local ref="$1" candidate base
    candidate="$ref"
    base="$REPO_ROOT"
    case "$candidate" in
        "~/.claude/"*)     candidate="${candidate#\~/.claude/}";     base="$GLOBAL_ROOT" ;;
        "~/dev/.claude/"*) candidate="${candidate#\~/dev/.claude/}"; base="$GLOBAL_ROOT" ;;
        "./"*)             candidate="${candidate#./}" ;;
    esac
    [[ -e "$base/$candidate" ]]
}

check_path() {
    local ref="$1" src="$2"
    if ! resolve_path "$ref"; then
        echo "BROKEN PATH: $src references '$ref' which does not exist."
        broken=1
    fi
}

check_command() {
    local cmd="$1" src="$2"
    is_allowed_missing "$cmd" && return 0
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "MISSING COMMAND: $src references '$cmd' which is not on PATH."
        broken=1
    fi
}

for src in "${SOURCES[@]}"; do
    [[ -f "$src" ]] || continue

    # 1. DSL-style path arguments. Capture the token after the verb prefix,
    #    take the first comma-separated field, and trim whitespace.
    while IFS= read -r ref; do
        [[ -z "$ref" ]] && continue
        check_path "$ref" "$src"
    done < <(
        grep -oE '(file_exists|content_present|section_present|content_absent_any|em_dash_absent|ai_patterns_absent):[[:space:]]*[^,`"'\'']+' "$src" \
            | sed -E 's/^[a-z_]+:[[:space:]]*//' \
            | sed -E 's/[[:space:]]+$//'
    )

    # 2. Global ~/.claude and ~/dev/.claude path references in backticks.
    while IFS= read -r ref; do
        [[ -z "$ref" ]] && continue
        # Skip directory-only references that legitimately may not exist as a
        # file but should exist as a dir; resolve_path handles both via -e.
        check_path "$ref" "$src"
    done < <(
        grep -oE '`~?/?(dev/)?\.claude/[A-Za-z0-9._/-]+`' "$src" \
            | tr -d '`'
    )

    # 3. Bare relative repo paths in backticks: contain a slash and a dotted
    #    extension. This deliberately ignores tokens without an extension to
    #    avoid matching command fragments or prose.
    while IFS= read -r ref; do
        [[ -z "$ref" ]] && continue
        # Ignore URLs, globs, and ./-prefixed scope-hierarchy examples. A
        # leading ./ in the steering files marks an illustrative scope path
        # (for example ./src/CLAUDE.md in the scope-hierarchy note), not a
        # reference to a tracked file.
        case "$ref" in
            http*|*"*"*|"./"*) continue ;;
        esac
        check_path "$ref" "$src"
    done < <(
        grep -oE '`[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+`' "$src" \
            | tr -d '`' \
            | grep -vE '^~?/?(dev/)?\.claude/'
    )

    # 4. Known shell commands referenced in backticks. Restrict to an explicit
    #    allowlist of command leaders the steering files use, so prose in
    #    backticks is not misread as a command.
    for cmd in "ruff" "pre-commit" "pip-audit" "basedpyright" "git" "gh" "python3"; do
        if grep -qE "\`${cmd}([[:space:]][^\`]*)?\`" "$src"; then
            check_command "$cmd" "$src"
        fi
    done
done

if [[ "$broken" -ne 0 ]]; then
    echo "FAIL: one or more steering-file references do not resolve." >&2
    exit 1
fi

echo "PASS: all extracted paths and commands in steering files resolve."
exit 0
