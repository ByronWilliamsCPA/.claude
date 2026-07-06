#!/usr/bin/env bash
# check-hook-sources.sh: Enumerate every live hook-injection source and diff
# it against the committed allowlist (hook-inventory.json at repo root).
#
# Claude Code executes hooks from more places than this repo's hooks.json:
#   1. ~/.claude/settings.json .hooks  (repo baseline merged by setup.sh,
#      plus direct writes by tool installers such as codebase-memory-mcp)
#   2. Enabled plugins' own hooks/hooks.json files under
#      ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/hooks/
#   3. Dormant plugin caches (cached but not enabled; reported as info)
#
# Every hook is reduced to a (event, matcher, command) tuple. A tuple is
# authorized if it appears in the repo baseline (hooks.json) or in the
# committed allowlist (hook-inventory.json). Anything live but unlisted is
# an unreviewed injection source and fails the check. Anything allowlisted
# but no longer live is reported as stale.
#
# Usage:
#   check-hook-sources.sh              # verify; exit 1 on unreviewed sources
#   check-hook-sources.sh --snapshot   # print hooks the verify pass would
#                                      # flag, as allowlist-shaped JSON
#
# Exit codes:
#   0  clean (warnings for stale/missing entries are allowed)
#   1  at least one unreviewed hook source found
#   2  missing prerequisite (jq), bad usage, or missing/malformed input

set -euo pipefail

# Byte-stable sort and comm collation regardless of the caller's locale.
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "${SCRIPT_DIR}")"
if [[ -z "${CLAUDE_DIR:-}" ]]; then
    if [[ -z "${HOME:-}" ]]; then
        echo "  [err]  HOME is unset and CLAUDE_DIR is not provided" >&2
        exit 2
    fi
    CLAUDE_DIR="${HOME}/.claude"
fi
SETTINGS="${CLAUDE_DIR}/settings.json"
BASELINE="${REPO_DIR}/hooks.json"
INVENTORY="${REPO_DIR}/hook-inventory.json"
PLUGIN_CACHE="${CLAUDE_DIR}/plugins/cache"

SNAPSHOT=0
for arg in "$@"; do
    case "$arg" in
        --snapshot) SNAPSHOT=1 ;;
        --help|-h)
            sed -n '/^# check-hook-sources/,/^#   2  /p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown flag: $arg (try --help)" >&2
            exit 2
            ;;
    esac
done

if ! command -v jq &>/dev/null; then
    echo "  [err]  jq is required for hook-source checking" >&2
    exit 2
fi

log_ok()   { echo "  [ok]   $*"; return 0; }
log_info() { echo "  [info] $*"; return 0; }
log_warn() { echo "  [warn] $*" >&2; return 0; }
log_err()  { echo "  [err]  $*" >&2; return 0; }

# Abbreviate a path with ~ for display only.
pretty() {
    if [[ -n "${HOME:-}" ]]; then
        printf '%s' "${1/#"$HOME"/\~}"
    else
        printf '%s' "$1"
    fi
}

# #CRITICAL: external resource. This check reads runtime-managed state
# (~/.claude/settings.json) plus two repo files; a missing or malformed
# input must abort loudly (exit 2), never report clean. A silent empty
# extraction here would make an unreviewed hook look authorized.
# #VERIFY: point CLAUDE_DIR at an empty directory and run; expect exit 2
# and an [err] line naming the missing file.
require_file() {
    local file="$1" what="$2"
    if [[ ! -f "$file" ]]; then
        log_err "${what} not found: ${file}"
        exit 2
    fi
}
require_file "$SETTINGS" "live settings"
require_file "$BASELINE" "repo baseline hooks.json"
require_file "$INVENTORY" "allowlist hook-inventory.json"

# jq program fragments shared by every extraction below.
#
# norm: canonicalize a command string so the same hook matches whether it
# was written with $HOME, ${HOME}, ~, or the literal home directory path.
# The bare-$HOME form requires a non-word character after it so that
# $HOMEBREW_PREFIX and similar are left alone. split/join is used for the
# literal path (no regex escaping surprises), guarded against an empty
# $home, where split("") would fan the string out into characters.
#
# flat: flatten a Claude Code hooks object into one TSV line per hook:
#   event <TAB> matcher <TAB> command
# A missing matcher is represented as "*". Prompt-type hooks (no command)
# are keyed on "prompt:" plus the full prompt text. Any other shape with
# neither command nor prompt is keyed on "unknown:" plus its own JSON so
# it can never match an allowlist entry by accident (fail closed).
# shellcheck disable=SC2016  # single quotes are intentional: this is a jq
# program; $home is a jq variable bound via --arg, not a shell expansion.
JQ_DEFS='
def norm:
  (. // "")
  | gsub("\\$\\{HOME\\}"; "~")
  | gsub("\\$HOME(?![A-Za-z0-9_])"; "~")
  | (if ($home | length) > 0 then (split($home) | join("~")) else . end);
def flat:
  to_entries[]
  | .key as $ev
  | .value[]
  | ((.matcher // "*") | if . == "" then "*" else . end) as $m
  | .hooks[]
  | [$ev, $m,
     ((if .command != null then .command
       elif .prompt != null then ("prompt:" + .prompt)
       else ("unknown:" + tojson) end) | norm)]
  | @tsv;
'

# Extract normalized tuples from a hooks OBJECT at a jq path in a file.
# A jq failure (malformed JSON, unexpected shape) aborts the whole check;
# swallowing it would silently drop a plane from the comparison.
tuples_from() {
    local file="$1" path="$2" out
    if ! out="$(jq -r --arg home "${HOME:-}" "${JQ_DEFS} (${path} // {}) | flat" "$file")"; then
        log_err "failed to extract hooks from ${file} (jq path: ${path})"
        exit 2
    fi
    printf '%s\n' "$out" | sort -u
}

# Drop blank lines without grep's nonzero exit on all-blank input.
nonblank() { awk 'NF'; }

# ---------- Gather: settings plane ----------
live_tuples="$(tuples_from "$SETTINGS" '.hooks')"
base_tuples="$(tuples_from "$BASELINE" '.')"

# Allowlisted installer additions: same tuple shape as the live plane.
if ! addn_tuples="$(jq -r --arg home "${HOME:-}" "${JQ_DEFS}"'
    .settings_additions // []
    | .[]
    | [.event,
       ((.matcher // "*") | if . == "" then "*" else . end),
       (.command | norm)]
    | @tsv
' "$INVENTORY")"; then
    log_err "failed to parse settings_additions from ${INVENTORY}"
    exit 2
fi
addn_tuples="$(printf '%s\n' "$addn_tuples" | sort -u)"

# ---------- Gather: plugin plane ----------
if ! enabled_plugins="$(jq -r \
    '.enabledPlugins // {} | to_entries[] | select(.value == true) | .key' \
    "$SETTINGS")"; then
    log_err "failed to read enabledPlugins from ${SETTINGS}"
    exit 2
fi
enabled_plugins="$(printf '%s\n' "$enabled_plugins" | sort -u)"

# Live plugin tuples, one stream of "pluginkey<TAB>event<TAB>matcher<TAB>command".
# #EDGE: several cached versions of one plugin can coexist after updates;
# Claude Code runs the newest, so only the highest version directory
# (sort -V) contributes tuples. Hidden directories (e.g. the .codex/
# variant some plugins ship for Codex) are excluded.
# #VERIFY: cache two version dirs with different hooks; only the newer
# version's hooks should appear in the live set.
plugin_live=""
while IFS= read -r pkey; do
    [[ -n "$pkey" ]] || continue
    # #ASSUME: plugin keys have the form name@marketplace with no path
    # separators; a key containing / or .. would escape the cache dir when
    # interpolated into the path below.
    # #VERIFY: add a key with a slash to enabledPlugins; expect exit 2.
    case "$pkey" in
        */*|*..*)
            log_err "invalid plugin key in enabledPlugins (path characters): ${pkey}"
            exit 2
            ;;
    esac
    name="${pkey%@*}"
    mp="${pkey#*@}"
    plugin_dir="${PLUGIN_CACHE}/${mp}/${name}"
    [[ -d "$plugin_dir" ]] || continue
    newest="$(find "$plugin_dir" -mindepth 1 -maxdepth 1 -type d ! -name '.*' \
        | sort -V | tail -n 1)"
    [[ -n "$newest" ]] || continue
    hf="${newest}/hooks/hooks.json"
    [[ -f "$hf" ]] || continue
    if ! ptuples="$(tuples_from "$hf" '.hooks')"; then
        exit 2  # tuples_from already logged the diagnostic
    fi
    while IFS= read -r line; do
        [[ -n "$line" ]] && plugin_live+="${pkey}"$'\t'"${line}"$'\n'
    done <<< "$ptuples"
done <<< "$enabled_plugins"
plugin_live="$(printf '%s' "$plugin_live" | sort -u)"

if ! plugin_allow="$(jq -r --arg home "${HOME:-}" "${JQ_DEFS}"'
    .plugins // {}
    | to_entries[]
    | .key as $p
    | .value[]
    | [$p, .event,
       ((.matcher // "*") | if . == "" then "*" else . end),
       (.command | norm)]
    | @tsv
' "$INVENTORY")"; then
    log_err "failed to parse plugins from ${INVENTORY}"
    exit 2
fi
plugin_allow="$(printf '%s\n' "$plugin_allow" | sort -u)"

# ---------- Diff all planes ----------
expected="$(printf '%s\n%s\n' "$base_tuples" "$addn_tuples" | nonblank | sort -u)"

new_live="$(comm -23 <(printf '%s\n' "$live_tuples" | nonblank) \
                     <(printf '%s\n' "$expected"))"
missing_base="$(comm -23 <(printf '%s\n' "$base_tuples" | nonblank) \
                         <(printf '%s\n' "$live_tuples" | nonblank))"
missing_addn="$(comm -23 <(printf '%s\n' "$addn_tuples" | nonblank) \
                         <(printf '%s\n' "$live_tuples" | nonblank))"
new_plugin="$(comm -23 <(printf '%s\n' "$plugin_live" | nonblank) \
                       <(printf '%s\n' "$plugin_allow" | nonblank))"
stale_plugin="$(comm -23 <(printf '%s\n' "$plugin_allow" | nonblank) \
                         <(printf '%s\n' "$plugin_live" | nonblank))"

# ---------- Snapshot mode ----------
if (( SNAPSHOT )); then
    # Emit exactly the hooks the verify pass would flag as unreviewed, in
    # hook-inventory.json shape, ready to review and paste into the
    # allowlist. Already-authorized hooks are not re-emitted.
    {
        printf '%s\n' "$new_live" | jq -R -s '
            split("\n") | map(select(length > 0) | split("\t")
                | {event: .[0], matcher: .[1], command: .[2], source: "UNREVIEWED"})' \
            | jq '{settings_additions: .}'
        printf '%s\n' "$new_plugin" | jq -R -s '
            split("\n") | map(select(length > 0) | split("\t"))
            | group_by(.[0])
            | map({key: .[0][0],
                   value: map({event: .[1], matcher: .[2], command: .[3]})})
            | from_entries | {plugins: .}'
    } | jq -s '.[0] * .[1]'
    exit 0
fi

# ---------- Verify: settings plane ----------
attention=0
unreviewed=0

echo "Settings hooks ($(pretty "$SETTINGS")):"

if [[ -n "$new_live" ]]; then
    while IFS=$'\t' read -r ev m cmd; do
        log_err "UNREVIEWED hook in settings.json: ${ev} [${m}] -> ${cmd}"
        unreviewed=$((unreviewed + 1))
    done <<< "$new_live"
else
    log_ok "no unreviewed hooks in settings.json"
fi

if [[ -n "$missing_base" ]]; then
    while IFS=$'\t' read -r ev m cmd; do
        log_warn "repo hook not live (run setup.sh): ${ev} [${m}] -> ${cmd}"
        attention=$((attention + 1))
    done <<< "$missing_base"
fi

if [[ -n "$missing_addn" ]]; then
    while IFS=$'\t' read -r ev m cmd; do
        log_warn "allowlisted addition not live (stale entry or wiped by merge): ${ev} [${m}] -> ${cmd}"
        attention=$((attention + 1))
    done <<< "$missing_addn"
fi

# ---------- Verify: plugin plane ----------
echo ""
echo "Plugin hooks ($(pretty "$PLUGIN_CACHE"), enabled plugins only):"

if [[ -n "$new_plugin" ]]; then
    while IFS=$'\t' read -r pkey ev m cmd; do
        log_err "UNREVIEWED plugin hook: ${pkey}: ${ev} [${m}] -> ${cmd}"
        unreviewed=$((unreviewed + 1))
    done <<< "$new_plugin"
else
    log_ok "all enabled-plugin hooks are allowlisted"
fi

if [[ -n "$stale_plugin" ]]; then
    while IFS=$'\t' read -r pkey ev m cmd; do
        log_warn "stale allowlist entry (plugin disabled, removed, or hook changed): ${pkey}: ${ev} [${m}] -> ${cmd}"
        attention=$((attention + 1))
    done <<< "$stale_plugin"
fi

# ---------- Info: dormant plugin caches ----------
# Depth is pinned to the cache shape <marketplace>/<plugin>/<version>/hooks/
# hooks.json so nested lookalikes (fixtures, .codex variants, vendored test
# data deeper in a plugin tree) are not swept in.
dormant=()
if [[ -d "$PLUGIN_CACHE" ]]; then
    while IFS= read -r hf; do
        rel="${hf#"${PLUGIN_CACHE}"/}"
        mp="${rel%%/*}"; rest="${rel#*/}"; name="${rest%%/*}"
        pkey="${name}@${mp}"
        if ! grep -qxF "$pkey" <<< "$enabled_plugins"; then
            dormant+=("$pkey")
        fi
    done < <(find "$PLUGIN_CACHE" -mindepth 5 -maxdepth 5 \
        -path '*/hooks/hooks.json' -name hooks.json 2>/dev/null)
fi
if (( ${#dormant[@]} > 0 )); then
    log_info "dormant (cached but not enabled) plugins with hooks: $(printf '%s\n' "${dormant[@]}" | sort -u | tr '\n' ' ')"
fi

echo ""
if (( unreviewed > 0 )); then
    log_err "${unreviewed} unreviewed hook source(s). Review each, then either remove it or add it to hook-inventory.json."
    exit 1
fi
if (( attention > 0 )); then
    log_warn "${attention} warning(s); no unreviewed sources."
    exit 0
fi
log_ok "All hook sources match the allowlist."
exit 0
