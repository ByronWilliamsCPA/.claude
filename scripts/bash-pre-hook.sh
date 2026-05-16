#!/usr/bin/env bash
# =============================================================================
# Bash Pre-Hook -- PreToolUse Hook
# =============================================================================
# Intercepts Bash tool calls to:
#   1. Block bypass flags that defeat branch protection / commit hygiene:
#        - gh pr merge --admin           (bypasses required status checks)
#        - git ... --no-verify           (bypasses pre-commit/pre-push hooks)
#        - git ... --no-gpg-sign         (bypasses required commit signing)
#        - git -c commit.gpgsign=false   (inline signing bypass)
#        - git -c tag.gpgsign=false      (inline tag signing bypass)
#   2. Block force-pushes to main or master (exit 2 with BLOCKED message)
#   3. Write a timing start timestamp to ${HOME}/.claude/tmp_cleanup/bash-start
#      for the post-hook notification script to compute command duration.
#      The marker lives under the user's home (audit H-01) to avoid the
#      symlink-race window of a fixed /tmp path.
#
# The timestamp is written ONLY when the command is allowed through.
#
# Exit codes:
#   0 -- allow tool call to proceed
#   2 -- block tool call; stdout message fed back to Claude
# =============================================================================

set -uo pipefail
# Note: -e is intentionally omitted. This is a PreToolUse hook that must never
# exit non-zero unexpectedly (exit 2 is reserved for the block signal). Any
# unhandled error must fall through to the allow path.

# Security (audit H-01): timing state lives under the user's home directory,
# not world-writable /tmp. This eliminates the TOCTOU symlink-attack window
# that existed when the previous fixed path /tmp/claude-bash-start.tmp could
# be pre-created by any local user.
TMP_DIR="${HOME}/.claude/tmp_cleanup"
START_FILE="${TMP_DIR}/bash-start"
if ! mkdir -p "${TMP_DIR}" 2>/dev/null; then
    # Cannot create user-scoped temp dir; fall back to a no-op marker rather
    # than reverting to /tmp (audit H-01 prohibits the world-writable path).
    TMP_DIR=""
    START_FILE=""
fi
[[ -n "$TMP_DIR" ]] && chmod 700 "${TMP_DIR}" 2>/dev/null

LOG_FILE="${HOME}/.claude/logs/bash-pre-hook.log"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || LOG_FILE=/dev/null
# Security (audit M-07): bash logs may capture commands with inline tokens or
# connection strings; restrict permissions on first creation. Surface the
# fallback to stderr so the operator notices when the permission backstop
# silently failed (e.g., DrvFs mount in WSL2).
if [[ "$LOG_FILE" != "/dev/null" && ! -f "$LOG_FILE" ]]; then
    : > "$LOG_FILE"
    if ! chmod 600 "$LOG_FILE" 2>/dev/null; then
        echo "[bash-pre-hook] WARN: chmod 600 ${LOG_FILE} failed; redaction is the only secret defense" >&2
    fi
fi

# Redact common credential-pattern strings from log lines. Pinned LC_ALL=C so
# multibyte sequences cannot crash sed; on any sed failure return a sentinel
# rather than the raw input or an empty string (audit pr-fix follow-up).
redact() {
    local out
    if ! out=$(printf '%s' "$1" | LC_ALL=C sed -E \
        -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]"]+/\1[REDACTED]/gi' \
        -e 's/(password[[:space:]]*[:=][[:space:]]*)[^[:space:]&"]+/\1[REDACTED]/gi' \
        -e 's/((api[_-]?key|token|secret)[[:space:]]*[:=][[:space:]]*)[^[:space:]&"]+/\1[REDACTED]/gi' \
        -e 's|://([^:/@[:space:]]+):[^[:space:]]*@|://\1:[REDACTED]@|g' 2>/dev/null); then
        printf '[REDACT_FAILED]'
        return 0
    fi
    printf '%s' "$out"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $(redact "$*")" >> "$LOG_FILE"
}

# Atomically write the timing start timestamp to START_FILE.
# Uses mktemp inside the same directory so the rename stays on one filesystem.
# On mktemp/rename failure the temp file is cleaned up so tmp_cleanup/ does
# not accumulate orphans, and the failure is logged so a user investigating
# missing notifications has a breadcrumb.
write_start_marker() {
    [[ -z "$START_FILE" ]] && return 0
    local tmp
    if ! tmp=$(mktemp "${START_FILE}.XXXXXX" 2>/dev/null); then
        log "WARN: mktemp failed under ${TMP_DIR}; bash-notify timing disabled this run"
        return 0
    fi
    if ! printf '%s' "$(date +%s)" > "$tmp" 2>/dev/null; then
        log "WARN: write to ${tmp} failed; cleaning up"
        rm -f "$tmp"
        return 0
    fi
    if ! mv "$tmp" "$START_FILE" 2>/dev/null; then
        log "WARN: mv ${tmp} -> ${START_FILE} failed; cleaning up orphan"
        rm -f "$tmp"
    fi
}

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
    log "ERROR: jq not found; cannot parse hook context -- passing through"
    write_start_marker
    exit 0
fi

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    write_start_marker
    exit 0
fi

# Extract command from tool input
CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT")

if [[ -z "$CMD" ]]; then
    write_start_marker
    exit 0
fi

# ---------------------------------------------------------------------------
# Bypass-flag guards (run for any Bash command, not just git push)
#
# These flags defeat the branch-protection / commit-hygiene model:
#
#   gh pr merge --admin
#     Bypasses required status checks. Only repo admins can use it, which
#     means solo-dev repos can't rely on branch protection to stop Claude.
#     If checks are failing, fix them. Never merge admin-style.
#
#   git ... --no-verify
#     Skips client-side hooks (pre-commit, pre-push, commit-msg). CLAUDE.md
#     global rule: never skip hooks unless the user explicitly requests it.
#     If a hook is failing, fix the underlying issue.
#
#   git ... --no-gpg-sign / -c commit.gpgsign=false / -c tag.gpgsign=false
#     Bypasses required commit signing. Every ByronWilliamsCPA / williaby
#     repo requires signed commits; an unsigned commit pushed by Claude would
#     either fail the ruleset or pollute history. If signing is broken, fix
#     the agent (GPG/SSH key setup), not the commit.
#
# Each guard blocks with a clear remediation path. If the user genuinely
# needs to use one of these flags, they can run the command from a terminal
# outside of Claude.
# ---------------------------------------------------------------------------

# Strip everything inside single- or double-quoted strings before flag matching
# so that quoted documentation (e.g., a commit message that contains the word
# "--admin" or "--no-verify") does not trigger a false-positive block.
# LC_ALL=C pins sed locale so multibyte input cannot crash the regex engine.
STRIPPED_CMD=$(printf '%s' "$CMD" | LC_ALL=C sed -E \
    -e "s/'[^']*'/''/g" \
    -e 's/"[^"]*"/""/g' 2>/dev/null) || STRIPPED_CMD="$CMD"

# Guard 1: gh pr merge --admin
# Detect gh pr merge anywhere in the (stripped) command paired with --admin.
# Handles compound commands (foo && gh pr merge ... --admin) and flag-order
# variants (gh pr merge --admin --squash | gh pr merge --squash --admin).
if echo "$STRIPPED_CMD" | grep -qE '\bgh\s+pr\s+merge\b' && \
   echo "$STRIPPED_CMD" | grep -qE '(^|[[:space:]])--admin\b'; then
    log "BLOCKED gh pr merge --admin: CMD=${CMD}"
    cat >&2 <<'EOF'
BLOCKED: 'gh pr merge --admin' bypasses required status checks.

If checks are failing, fix the underlying issue. Do not merge admin-style
just because you have the permission. If you genuinely need to admin-merge
(e.g., a stuck required check), run the command yourself from a terminal
outside Claude.
EOF
    exit 2
fi

# Guard 2: git --no-verify
# Matches --no-verify paired with any git subcommand (commit, push, merge,
# rebase, cherry-pick, etc.). Bare `--no-verify` outside of git is harmless,
# so we require a `git` token to anchor the match.
if echo "$STRIPPED_CMD" | grep -qE '\bgit\b' && \
   echo "$STRIPPED_CMD" | grep -qE '(^|[[:space:]])--no-verify\b'; then
    log "BLOCKED git --no-verify: CMD=${CMD}"
    cat >&2 <<'EOF'
BLOCKED: '--no-verify' skips pre-commit / pre-push / commit-msg hooks.

Per CLAUDE.md: never skip hooks unless the user explicitly requests it. If
a hook is failing, investigate and fix the underlying issue. Common fixes:
  - pre-commit run --all-files     # see the actual failure
  - pre-commit autoupdate          # if hook versions are out of date
  - Address the lint / format / type / security violation the hook flagged
EOF
    exit 2
fi

# Guard 3: signing-bypass flags
# Matches --no-gpg-sign anywhere, or inline config that disables commit/tag
# signing (-c commit.gpgsign=false, -c tag.gpgsign=false). The inline-config
# match is anchored to the gpgsign key to avoid accidental matches on
# unrelated `=false` config tokens.
if echo "$STRIPPED_CMD" | grep -qE '\bgit\b' && \
   echo "$STRIPPED_CMD" | grep -qE '(^|[[:space:]])--no-gpg-sign\b|(commit|tag)\.gpgsign[[:space:]]*=[[:space:]]*false\b'; then
    log "BLOCKED signing bypass: CMD=${CMD}"
    cat >&2 <<'EOF'
BLOCKED: signing bypass flag detected.

All ByronWilliamsCPA / williaby repos require signed commits. An unsigned
commit will be rejected by the ruleset or pollute the audit trail. If
signing is broken, fix the agent setup, not the commit:
  - gpg --list-secret-keys                # confirm the signing key exists
  - git config --global user.signingkey   # confirm the key is configured
  - ssh-add -L                            # if using SSH signing
EOF
    exit 2
fi

# ---------------------------------------------------------------------------
# Force-push guard
# Block: git push with --force, -f, or --force-with-lease when:
#   (a) the explicit branch target is main or master, OR
#   (b) no branch token is present at all (bare force push), OR
#   (c) parsing is ambiguous (safe fallback: block)
#
# Three bypass vectors are handled:
#
#   Bypass 1 -- URL-format remote names:
#     git push git@github.com:org/repo main --force
#     A URL remote defeats simple alphanumeric sed stripping. Detected by
#     checking for "://" or "@" in the remote position and blocked (ambiguous
#     parse is treated as the safe fallback).
#
#   Bypass 2 -- Interleaved flags:
#     git push -f -u origin main  OR  git push origin -f main
#     Fixed by stripping ALL flag tokens first, then reading remote and branch
#     positionally from the remaining non-flag arguments.
#
#   Bypass 3 -- Compound commands:
#     ls; git push --force origin main  OR  git status && git push --force
#     Fixed by extracting only the "git push ..." segment before any analysis.
# ---------------------------------------------------------------------------

# Only check force-push for git push commands
if ! echo "$CMD" | grep -qE 'git\s+push'; then
    write_start_marker
    exit 0
fi

# ---------------------------------------------------------------------------
# Bypass 3: Extract only the git push segment from compound commands.
# Strip everything before the last "git push" occurrence so that prefix
# commands (ls; git push, git status && git push, etc.) do not pollute the
# argument list used for branch extraction below.
# ---------------------------------------------------------------------------
PUSH_SEGMENT=$(echo "$CMD" | grep -oE 'git\s+push.*' | tail -1)

if [[ -z "$PUSH_SEGMENT" ]]; then
    # grep -oE found nothing; fall through to allow
    write_start_marker
    exit 0
fi

# Now check for force flags within the extracted push segment
if echo "$PUSH_SEGMENT" | grep -qE '(--force|--force-with-lease(=[^\s]+)?|-f)(\s|$)'; then

    # -----------------------------------------------------------------------
    # Bypass 2: Strip all flags first, then read positional args in order.
    #
    # 1. Remove "git push" prefix.
    # 2. Strip every token that starts with "-" (flags, including -f, -u,
    #    --force, --force-with-lease=..., etc.).
    # 3. The first remaining token is the remote; the second is the branch.
    #    If there is no remote or no branch, treat as bare/ambiguous and block.
    # -----------------------------------------------------------------------
    ARGS_ONLY=$(echo "$PUSH_SEGMENT" | sed -E 's/^git\s+push\s*//')

    # Build an array of positional (non-flag) tokens
    declare -a POS_ARGS=()
    for token in $ARGS_ONLY; do
        if [[ "$token" != -* ]]; then
            POS_ARGS+=("$token")
        fi
    done

    REMOTE_TOKEN="${POS_ARGS[0]:-}"
    BRANCH_TOKEN="${POS_ARGS[1]:-}"

    # -----------------------------------------------------------------------
    # Bypass 1: Detect URL-format remote names.
    # If the remote looks like a URL (contains "://" or starts with git@),
    # parsing the branch is ambiguous; block as the safe fallback.
    # -----------------------------------------------------------------------
    if [[ -n "$REMOTE_TOKEN" ]] && \
       (echo "$REMOTE_TOKEN" | grep -qE '://|^git@'); then
        log "BLOCKED force-push (URL remote, ambiguous parse): CMD=${CMD}"
        echo "BLOCKED: force-push with a URL remote cannot be safely validated. Use a named remote and a PR instead."
        exit 2
    fi

    # Extract destination ref from refspec forms (HEAD:main, :main, src:dest).
    # ${BRANCH_TOKEN##*:} strips the source ref; if no colon, returns BRANCH_TOKEN.
    DEST_TOKEN="${BRANCH_TOKEN##*:}"

    # Normalize common Git ref prefixes so fully-qualified refs such as
    # refs/heads/main and refs/main are treated the same as main.
    NORMALIZED_BRANCH_TOKEN="${BRANCH_TOKEN#refs/heads/}"
    NORMALIZED_BRANCH_TOKEN="${NORMALIZED_BRANCH_TOKEN#refs/}"
    NORMALIZED_DEST_TOKEN="${DEST_TOKEN#refs/heads/}"
    NORMALIZED_DEST_TOKEN="${NORMALIZED_DEST_TOKEN#refs/}"

    # Block if: no branch token (bare force push), explicit branch is main/master,
    # or destination ref extracted from a refspec is main/master.
    if [[ -z "$BRANCH_TOKEN" ]] || \
       echo "$NORMALIZED_BRANCH_TOKEN" | grep -qE '^(main|master)$' || \
       echo "$NORMALIZED_DEST_TOKEN" | grep -qE '^(main|master)$'; then
        log "BLOCKED force-push: CMD=${CMD}"
        echo "BLOCKED: force-push to main/master (or bare force-push) is prohibited. Use a PR instead."
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# Command is allowed -- write timing start timestamp via write_start_marker
# (audit H-01: atomic write to ${HOME}/.claude/tmp_cleanup/, not /tmp)
# ---------------------------------------------------------------------------
write_start_marker
log "Allowed: ${CMD}"
exit 0
