#!/usr/bin/env bash
# =============================================================================
# Bash Pre-Hook -- PreToolUse Hook
# =============================================================================
# Intercepts Bash tool calls to:
#   1. Block bypass flags that defeat branch protection / commit hygiene:
#        - gh pr merge --admin                          (bypasses required checks via CLI)
#        - gh api ... /pulls/N/merge                    (bypasses required checks via REST)
#        - git ... --no-verify                          (bypasses pre-commit/pre-push hooks)
#        - git ... --no-gpg-sign                        (bypasses required commit signing)
#        - git -c commit.gpgsign=<falsy>                (inline signing bypass, any case,
#                                                        falsy = false|0|no|off)
#        - git -c tag.gpgsign=<falsy>                   (inline tag signing bypass)
#        - shell redirection into a credential-bearing path (.env, .aws/credentials,
#                                                        .netrc, .npmrc, .pypirc, SSH
#                                                        private keys, .pem files)
#        - git add -A / --all / bare `git add .`        (blanket staging; concurrent
#                                                        sessions share this working tree)
#      The guards run per command segment (split on &&, ||, ;, |) so a bypass
#      flag is only blocked when it belongs to the principal git/gh invocation,
#      not to an unrelated tool that shares the command line. Indirection
#      wrappers (eval, bash -c, sh -c, zsh -c) are unwrapped one level deep so
#      flags inside the inner argument are still detected.
#   2. Block force-pushes to main, master, or develop (exit 2 with BLOCKED message)
#   3. Block `git reset --hard` when HEAD is on a protected branch
#      (main / master / develop); feature-branch hard resets are allowed
#   4. Block `git checkout -B <branch>` when <branch> (the mutated target) is
#      a protected branch; naming a protected branch as the START-POINT
#      (`git checkout -B feature main`) stays allowed
#   5. Write a timing start timestamp to ${HOME}/.claude/tmp_cleanup/bash-start
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
# unhandled error must fall through to the allow path. This hook is an early-
# warning UX layer; the authoritative enforcement of signed-commit, required-
# status-check, and force-push policy lives in the GitHub rulesets, so a hook
# failure degrades UX (slower feedback) rather than security. Do not "harden"
# the script to fail-closed: that would brick Claude's Bash tool on any
# transient sed/grep/jq glitch with no security gain.

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

# Single exit point for every allowed command. Guard clauses that decide a
# command is out of scope must call this rather than open-coding
# `write_start_marker; exit 0`, which skips the audit-log write and leaves the
# log recording only blocks and git-push allows (roughly 1% of commands).
# CMD is deliberately expanded with a default: three of the call sites below
# run before CMD is assigned (jq missing, empty stdin, unparseable input), and
# `set -u` would turn an unguarded expansion into a fatal error in a hook whose
# contract is to never fail unexpectedly.
allow_and_exit() {
    write_start_marker
    log "Allowed: ${CMD:-<no command parsed>}"
    exit 0
}

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
    log "ERROR: jq not found; cannot parse hook context -- passing through"
    allow_and_exit
fi

# Read JSON context from stdin
CONTEXT=$(cat)

if [[ -z "$CONTEXT" ]]; then
    allow_and_exit
fi

# Extract command from tool input
CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT")

if [[ -z "$CMD" ]]; then
    allow_and_exit
fi

# ---------------------------------------------------------------------------
# Bypass-flag guards
#
# These flags defeat the branch-protection / commit-hygiene model:
#
#   gh pr merge --admin / gh api .../pulls/N/merge
#     Bypass required status checks (CLI and REST forms, respectively). Only
#     repo admins can use either, which means solo-dev repos can't rely on
#     branch protection to stop Claude. If checks are failing, fix them.
#
#   git ... --no-verify
#     Skips client-side hooks (pre-commit, pre-push, commit-msg). CLAUDE.md
#     global rule: never skip hooks unless the user explicitly requests it.
#
#   git ... --no-gpg-sign / -c commit.gpgsign=<falsy> / -c tag.gpgsign=<falsy>
#     Bypasses required commit signing. Every BW/williaby repo requires signed
#     commits; an unsigned commit would either fail the ruleset or pollute
#     history. The match is case-insensitive (git config keys are case-
#     insensitive) and accepts every falsy boolean (false, 0, no, off).
#
# Detection design (rewritten in PR #105 follow-up):
#
#   * Only -m / --message argument VALUES are blanked, not all quoted spans.
#     The shell strips quotes before exec, so `git commit "--no-verify"` is
#     functionally identical to `git commit --no-verify`; broad quote
#     stripping creates a false-negative class. Narrow message-arg stripping
#     keeps documentation-text false positives away while leaving flag
#     tokens visible to the regex.
#
#   * The command is split into segments at &&, ||, ;, |, and subshell
#     delimiters. Each guard inspects one segment so a bypass flag is only
#     blocked when the principal command is git or gh, not when an
#     unrelated tool elsewhere in the pipeline happens to share the line.
#
#   * Indirection wrappers (eval, bash -c, sh -c, zsh -c) are unwrapped one
#     level deep so a `bash -c "git commit --no-verify"` still trips the
#     guard. Deeper or runtime-constructed indirection (e.g., backtick
#     command substitution that yields the flag at execution) is not
#     detectable by static analysis and is documented as a known limitation.
#
# Each guard blocks with a clear remediation path. If the user genuinely
# needs one of these flags, they can run the command from a terminal outside
# Claude.
# ---------------------------------------------------------------------------

# Helper: normalize the command string for guard inspection. Two passes:
#
# Pass 1 (message-arg blanking): blank ONLY the VALUE of -m / --message
# arguments so a commit message containing flag-shaped documentation text
# does not trip the guards. Handles `-m "msg"`, `-m 'msg'`, `-m"msg"`,
# `--message="msg"`, `--message 'msg'`.
#
# Pass 2 (token-quote stripping): strip surrounding quotes from any
# remaining quoted token that contains no spaces. Bash strips these quotes
# before exec, so `"--no-verify"` is semantically identical to `--no-verify`;
# without this step, every guard regex would emit a false negative on the
# trivially-quoted form. Spaces inside the quotes (e.g., commit message
# fragments not already blanked) disqualify the token, preserving the
# default false-positive prevention for any non-arg quoted text.
#
# Order matters: message-arg blanking runs first so a single-word commit
# message like `-m "fix"` is blanked to `-m ""` BEFORE the token-quote
# pass would otherwise see `"fix"` and strip its quotes (which would be
# harmless here but wastes the safety margin elsewhere).
#
# LC_ALL=C pins sed locale against multibyte input.
blank_message_args() {
    LC_ALL=C sed -E \
        -e 's/(^|[[:space:]])(-m|--message)[[:space:]]+"[^"]*"/\1\2 ""/g' \
        -e "s/(^|[[:space:]])(-m|--message)[[:space:]]+'[^']*'/\1\2 ''/g" \
        -e 's/(^|[[:space:]])(-m|--message)="[^"]*"/\1\2=""/g' \
        -e "s/(^|[[:space:]])(-m|--message)='[^']*'/\1\2=''/g" \
        -e 's/(^|[[:space:]])-m"[^"]*"/\1-m""/g' \
        -e "s/(^|[[:space:]])-m'[^']*'/\1-m''/g" \
        -e 's/"([^"[:space:]]+)"/\1/g' \
        -e "s/'([^'[:space:]]+)'/\1/g" 2>/dev/null
}

# Helper: split a command string into top-level segments at shell operators.
# Operators handled: &&, ||, ;, |, and the parens / braces of subshell or
# brace groups. Best effort; pathological nested quoting cannot be perfectly
# parsed in sed and is documented as a known limitation.
split_segments() {
    LC_ALL=C sed -E 's/&&|\|\||;|\||\(|\)|\{|\}/\n/g' 2>/dev/null
}

# Helper: if the segment is an indirection wrapper (eval / bash -c / sh -c /
# zsh -c), return the inner argument with surrounding quotes removed. One
# level deep only. Otherwise returns the segment unchanged.
unwrap_indirection() {
    local seg="$1" arg
    if arg=$(printf '%s' "$seg" | LC_ALL=C sed -nE \
        -e 's/^[[:space:]]*eval[[:space:]]+(.*)$/\1/p' \
        -e 's/^[[:space:]]*(ba|z)?sh[[:space:]]+-c[[:space:]]+(.*)$/\2/p' \
        2>/dev/null) && [[ -n "$arg" ]]; then
        # Strip a single layer of surrounding single or double quotes.
        arg="${arg#\"}"; arg="${arg%\"}"
        arg="${arg#\'}"; arg="${arg%\'}"
        printf '%s' "$arg"
    else
        printf '%s' "$seg"
    fi
}

# Per-segment scanners. Each returns 0 (true) when the segment violates
# the policy, 1 (false) otherwise. The principal-command check ensures the
# bypass flag belongs to the actual git/gh invocation, not to an unrelated
# tool sharing the command line.

violates_gh_pr_merge_admin() {
    local seg
    seg=$(unwrap_indirection "$1")
    echo "$seg" | grep -qE '(^|[[:space:]])gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)' \
        && echo "$seg" | grep -qE '(^|[[:space:]])--admin([[:space:]]|=|$)'
}

violates_gh_api_merge() {
    local seg
    seg=$(unwrap_indirection "$1")
    echo "$seg" | grep -qE '(^|[[:space:]])gh[[:space:]]+api([[:space:]]|$)' \
        && echo "$seg" | grep -qE '/pulls?/[0-9]+/merge'
}

violates_git_no_verify() {
    local seg
    seg=$(unwrap_indirection "$1")
    echo "$seg" | grep -qE '(^|[[:space:]])git([[:space:]]|$)' \
        && echo "$seg" | grep -qE '(^|[[:space:]])--no-verify([[:space:]]|=|$)'
}

violates_git_no_sign() {
    local seg
    seg=$(unwrap_indirection "$1")
    echo "$seg" | grep -qE '(^|[[:space:]])git([[:space:]]|$)' || return 1
    # Case 1: --no-gpg-sign flag (CLI flag, case-sensitive in git).
    if echo "$seg" | grep -qE '(^|[[:space:]])--no-gpg-sign([[:space:]]|=|$)'; then
        return 0
    fi
    # Case 2: inline -c key=value with case-insensitive git config key and any
    # falsy boolean. Left-anchored so `notag.gpgsign=...` does NOT match.
    echo "$seg" | grep -qiE '(^|[[:space:]])(commit|tag)\.gpgsign[[:space:]]*=[[:space:]]*(false|0|no|off)([[:space:]]|$)'
}

# Sensitive-redirect guard (review 5.6): shell redirection into a
# credential-bearing path is the Bash-tool equivalent of an Edit/Write to a
# guarded sensitive file. Catches `>`, `>>`, and `tee [-a]` into .env,
# .aws/credentials, .netrc, .npmrc, .pypirc, SSH private keys, or .pem files.
# Every alternative carries a right-hand boundary: end-of-token or whitespace,
# plus a dot-suffix for the rc-file family so .env.production still blocks.
# Without the boundary, unrelated names like config.environment.yaml,
# my.netrcfile.txt, .npmrcignore, and id_rsa_public_key_notes.md would
# false-positive (security review finding, task 25 rework).
violates_sensitive_redirect() {
    local seg
    seg=$(unwrap_indirection "$1")
    echo "$seg" | grep -qE '(>>?|tee[[:space:]]+(-a[[:space:]]+)?)[[:space:]]*[^[:space:]]*((\.env|\.netrc|\.npmrc|\.pypirc)(\.[^[:space:]]+)?([[:space:]]|$)|\.aws/credentials([[:space:]]|$)|id_(rsa|dsa|ecdsa|ed25519)([[:space:]]|$)|\.pem([[:space:]]|$))'
}

# Blanket-staging guard (review R-13): `git add -A` / `git add --all` /
# bare `git add .` stage every change in the working tree, including edits
# from a concurrent session sharing this working tree. The bare-dot arm also
# matches dot-slash spellings (`git add ./`, `git add ./.`), which are the
# same blanket stage (security review finding, task 25 rework). Explicit-path
# forms (`git add src/app.py`, `git add ./src/app.py`) are unaffected.
violates_git_add_all() {
    local seg
    seg=$(unwrap_indirection "$1")
    echo "$seg" | grep -qE '(^|[[:space:]])git[[:space:]]+add([[:space:]]|$)' || return 1
    if echo "$seg" | grep -qE '(^|[[:space:]])(-A|--all)([[:space:]]|=|$)'; then
        return 0
    fi
    echo "$seg" | grep -qE '(^|[[:space:]])git[[:space:]]+add[[:space:]]+\.[./]*([[:space:]]|$)'
}

# Pre-scan the command: blank message-arg values so documentation text inside
# a commit message does not cause false-positive blocks.
PRE_SCAN=$(printf '%s' "$CMD" | blank_message_args)
if [[ -z "$PRE_SCAN" ]]; then
    # blank_message_args returned empty (sed failed). Fall back to raw $CMD.
    # This is fail-SAFE: real bypass flags sit outside message values and are
    # still detected by the per-segment scanners. The only regression is a
    # possible false-positive on a commit message containing flag-shaped text,
    # which is acceptable for a security guard. Surface the fallback so a
    # persistent sed failure is visible in the audit log.
    PRE_SCAN="$CMD"
    log "WARN: blank_message_args returned empty; using raw CMD for guard scan"
fi

# Iterate segments; emit the first violation found and exit. Multiple
# violations in the same command produce a single block message (the user
# only needs to fix the command to move forward).
#
# `|| [[ -n "$SEGMENT" ]]` is the standard idiom that processes the final
# segment even when split_segments emits no trailing newline (the common
# single-segment case, where sed produces no operator-replacement and
# therefore no terminating \n). Without this, single-segment bypasses like
# `git push --no-verify origin feature` would be silently allowed.
while IFS= read -r SEGMENT || [[ -n "$SEGMENT" ]]; do
    [[ -z "$SEGMENT" ]] && continue

    if violates_gh_pr_merge_admin "$SEGMENT"; then
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

    if violates_gh_api_merge "$SEGMENT"; then
        log "BLOCKED gh api admin-merge endpoint: CMD=${CMD}"
        cat >&2 <<'EOF'
BLOCKED: 'gh api .../pulls/N/merge' is the REST form of 'gh pr merge --admin'
and bypasses required status checks when the caller has admin rights.

If checks are failing, fix the underlying issue. Do not merge through the
REST API just because the CLI form is blocked. Run the merge yourself from
a terminal outside Claude if you have manually verified the gate is stuck.
EOF
        exit 2
    fi

    if violates_git_no_verify "$SEGMENT"; then
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

    if violates_git_no_sign "$SEGMENT"; then
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

    if violates_sensitive_redirect "$SEGMENT"; then
        log "BLOCKED sensitive redirect: CMD=${CMD}"
        cat >&2 <<'EOF'
BLOCKED: shell redirection into a credential-bearing path.
Sensitive files are guarded for Edit/Write; Bash redirection is the same
operation. If this is intentional, run it from a terminal outside Claude.
EOF
        exit 2
    fi

    if violates_git_add_all "$SEGMENT"; then
        log "BLOCKED blanket git add: CMD=${CMD}"
        cat >&2 <<'EOF'
BLOCKED: blanket staging (git add -A / git add .) is prohibited.
Concurrent sessions share this working tree; stage only the files you
changed: git add <paths>.
EOF
        exit 2
    fi
done < <(printf '%s' "$PRE_SCAN" | split_segments)

# ---------------------------------------------------------------------------
# Hard-reset guard (git-guardrails)
# Block `git reset --hard` when the CURRENT branch is a protected branch
# (main / master / develop). A hard reset there discards committed or
# working-tree state that should only change through a reviewed PR.
#
# Feature-branch hard resets are intentionally ALLOWED. Resyncing an
# in-progress feature branch with `git reset --hard origin/<branch>` is a
# normal workflow and must not be blocked; the guard only fires when HEAD is
# on a protected branch.
#
# Detection mirrors the force-push normalization so `git -C <dir> reset --hard`
# is still caught. Operates on PRE_SCAN (message-arg values already blanked) so
# a commit message that merely mentions "git reset --hard" cannot false-trip.
#
# Fail-open: if the current branch cannot be determined, allow the command.
# Per this script's design (see header), authoritative protection lives in the
# GitHub rulesets; this hook is an early-warning UX layer and must never brick
# the Bash tool on a transient git error.
# ---------------------------------------------------------------------------
HR_CMD=$(printf '%s' "$PRE_SCAN" | sed -E ':loop
s/(^|[^[:alnum:]_])git[[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--git-dir=[^[:space:]]+|--work-tree=[^[:space:]]+|--namespace=[^[:space:]]+|--exec-path=[^[:space:]]+|--bare|-p|-P|--paginate|--no-pager|--no-replace-objects|--literal-pathspecs|--no-optional-locks)[[:space:]]+/\1git /
tloop')

if echo "$HR_CMD" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+reset([[:space:]]|$)' \
   && echo "$HR_CMD" | grep -qE '(^|[[:space:]])--hard([[:space:]]|=|$)'; then
    # Honor `git -C <dir>` for the branch check so it reads the repo the reset
    # actually targets, not the hook's cwd. Without this, `git -C /path reset
    # --hard` run from outside /path reads the wrong repo (or none) and the
    # guard fails open even when /path is on a protected branch. Extract the
    # dir from a `git -C <dir> ... reset` invocation (no command separator
    # between -C and reset).
    HR_DIR=$(printf '%s' "$PRE_SCAN" \
        | grep -oE '(^|[^[:alnum:]_])git[[:space:]]+-C[[:space:]]+[^[:space:]]+[^;&|]*reset' \
        | sed -E 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+).*/\1/' \
        | head -n1)
    if [ -n "$HR_DIR" ]; then
        CURRENT_BRANCH=$(git -C "$HR_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)
    else
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
    fi
    if echo "$CURRENT_BRANCH" | grep -qE '^(main|master|develop)$'; then
        log "BLOCKED git reset --hard on protected branch ${CURRENT_BRANCH}: CMD=${CMD}"
        cat >&2 <<EOF
BLOCKED: 'git reset --hard' on protected branch '${CURRENT_BRANCH}'.

A hard reset here discards state that should only change through a reviewed PR.
For feature work, switch to a feature branch first (git checkout -b fix/...).
If you are intentionally resyncing a protected branch to its remote, run the
command yourself from a terminal outside Claude.
EOF
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# checkout -B guard (closes the gap documented in rules/git-workflow.md).
# `git checkout -B <branch> [<start-point>]` force-moves <branch>, which is
# a hard mutation of <branch>. Block only when the MUTATED branch (the -B
# target) is protected. Naming a protected branch as the START-POINT
# (`git checkout -B feature main`) is the documented squash-orphan rebuild
# recipe and stays allowed.
# ---------------------------------------------------------------------------
if echo "$HR_CMD" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+checkout([[:space:]]|$)' \
   && echo "$HR_CMD" | grep -qE '(^|[[:space:]])-B([[:space:]]|$)'; then
    CB_TARGET=$(printf '%s' "$HR_CMD" \
        | sed -nE 's/.*[[:space:]]-B[[:space:]]+([^[:space:]]+).*/\1/p' | head -n1)
    if echo "$CB_TARGET" | grep -qE '^(main|master|develop)$'; then
        log "BLOCKED git checkout -B onto protected branch ${CB_TARGET}: CMD=${CMD}"
        echo "BLOCKED: 'git checkout -B ${CB_TARGET}' rewrites protected branch '${CB_TARGET}'. Rebuild feature branches instead; protected branches change only through PRs."
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# Force-push guard
# Block: git push with --force, -f, or --force-with-lease when:
#   (a) the explicit branch target is main, master, or develop, OR
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

# ---------------------------------------------------------------------------
# Bypass 4: git global options between `git` and the subcommand.
# `git -C <dir> push --force main`, `git -c k=v push -f main`, and
# `git --git-dir=… push` all defeated the adjacency-based `git push` detection
# below, skipping the guard entirely (verified live 2026-05-30). Normalize by
# collapsing `git <globals> push` -> `git push` before any analysis. The
# arg-taking globals -C and -c consume the following token; the long options
# take an attached =value. The loop removes multiple stacked globals. The
# pattern only strips a global when it sits immediately after `git`, so the
# commit-level `-C` in `git commit -C HEAD` (reuse message) is left untouched.
FP_CMD=$(printf '%s' "$CMD" | sed -E ':loop
s/(^|[^[:alnum:]_])git[[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--git-dir=[^[:space:]]+|--work-tree=[^[:space:]]+|--namespace=[^[:space:]]+|--exec-path=[^[:space:]]+|--bare|-p|-P|--paginate|--no-pager|--no-replace-objects|--literal-pathspecs|--no-optional-locks)[[:space:]]+/\1git /
tloop')

# Only check force-push for git push commands
if ! echo "$FP_CMD" | grep -qE 'git\s+push'; then
    allow_and_exit
fi

# ---------------------------------------------------------------------------
# Bypass 3: Extract only the git push segment from compound commands.
# Strip everything before the last "git push" occurrence so that prefix
# commands (ls; git push, git status && git push, etc.) do not pollute the
# argument list used for branch extraction below.
# ---------------------------------------------------------------------------
PUSH_SEGMENT=$(echo "$FP_CMD" | grep -oE 'git\s+push.*' | tail -1)

if [[ -z "$PUSH_SEGMENT" ]]; then
    # grep -oE found nothing; fall through to allow
    allow_and_exit
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
       echo "$NORMALIZED_BRANCH_TOKEN" | grep -qE '^(main|master|develop)$' || \
       echo "$NORMALIZED_DEST_TOKEN" | grep -qE '^(main|master|develop)$'; then
        log "BLOCKED force-push: CMD=${CMD}"
        echo "BLOCKED: force-push to main/master/develop (or bare force-push) is prohibited. Use a PR instead."
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
