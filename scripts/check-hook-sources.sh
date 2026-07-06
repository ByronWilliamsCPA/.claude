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
#   check-hook-sources.sh --snapshot   # print live state as allowlist JSON
#
# Exit codes:
#   0  clean (warnings for stale/missing entries are allowed)
#   1  at least one unreviewed hook source found
#   2  missing prerequisite (jq) or bad usage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "${SCRIPT_DIR}")"
CLAUDE_DIR="${CLAUDE_DIR:-${HOME}/.claude}"
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

# jq program fragments shared by every extraction below.
#
# norm: canonicalize a command string so the same hook matches whether it
# was written with $HOME, ${HOME}, ~, or the literal home directory path.
# split/join is used for the literal path (no regex escaping surprises).
#
# flat: flatten a Claude Code hooks object into one TSV line per hook:
#   event <TAB> matcher <TAB> command
# A missing matcher is represented as "*". Prompt-type hooks (no command)
# are keyed on a "prompt:" prefix plus the first 60 chars of the prompt.
# shellcheck disable=SC2016  # single quotes are intentional: this is a jq
# program; $home is a jq variable bound via --arg, not a shell expansion.
JQ_DEFS='
def norm:
  (. // "")
  | gsub("\\$\\{HOME\\}"; "~")
  | gsub("\\$HOME"; "~")
  | split($home) | join("~");
def flat:
  to_entries[]
  | .key as $ev
  | .value[]
  | ((.matcher // "*") | if . == "" then "*" else . end) as $m
  | .hooks[]
  | [$ev, $m, ((.command // ("prompt:" + ((.prompt // "") | .[0:60]))) | norm)]
  | @tsv;
'

# Extract normalized tuples from a hooks OBJECT at a jq path in a file.
tuples_from() {
    local file="$1" path="$2"
    [[ -f "$file" ]] || return 0
    jq -r --arg home "$HOME" "${JQ_DEFS} (${path} // {}) | flat" "$file" 2>/dev/null | sort -u
    return 0
}

# ---------- Gather: settings plane ----------
live_tuples="$(tuples_from "$SETTINGS" '.hooks')"
base_tuples="$(tuples_from "$BASELINE" '.')"

# Allowlisted installer additions: same tuple shape as the live plane.
addn_tuples=""
if [[ -f "$INVENTORY" ]]; then
    addn_tuples="$(jq -r --arg home "$HOME" "${JQ_DEFS}"'
        .settings_additions // []
        | .[]
        | [.event,
           ((.matcher // "*") | if . == "" then "*" else . end),
           (.command | norm)]
        | @tsv
    ' "$INVENTORY" | sort -u)"
fi

# ---------- Gather: plugin plane ----------
enabled_plugins="$(jq -r '.enabledPlugins // {} | to_entries[] | select(.value == true) | .key' \
    "$SETTINGS" 2>/dev/null | sort -u)"

# Live plugin tuples, one stream of "pluginkey<TAB>event<TAB>matcher<TAB>command".
# Multiple cached versions of one plugin are deduplicated; the .codex/
# variant some plugins ship is for Codex, not Claude Code, and is skipped.
plugin_live=""
while IFS= read -r pkey; do
    [[ -n "$pkey" ]] || continue
    name="${pkey%@*}"
    mp="${pkey#*@}"
    for hf in "${PLUGIN_CACHE}/${mp}/${name}"/*/hooks/hooks.json; do
        [[ -f "$hf" ]] || continue
        [[ "$hf" == *"/.codex/"* ]] && continue
        while IFS= read -r line; do
            [[ -n "$line" ]] && plugin_live+="${pkey}	${line}"$'\n'
        done < <(tuples_from "$hf" '.hooks')
    done
done <<< "$enabled_plugins"
plugin_live="$(printf '%s' "$plugin_live" | sort -u)"

plugin_allow=""
if [[ -f "$INVENTORY" ]]; then
    plugin_allow="$(jq -r --arg home "$HOME" "${JQ_DEFS}"'
        .plugins // {}
        | to_entries[]
        | .key as $p
        | .value[]
        | [$p, .event,
           ((.matcher // "*") | if . == "" then "*" else . end),
           (.command | norm)]
        | @tsv
    ' "$INVENTORY" | sort -u)"
fi

# ---------- Snapshot mode ----------
if (( SNAPSHOT )); then
    # Emit live state in hook-inventory.json shape for human review.
    extras="$(comm -23 <(printf '%s\n' "$live_tuples") \
                       <(printf '%s\n' "$base_tuples"))"
    {
        printf '%s\n' "$extras" | jq -R -s '
            split("\n") | map(select(length > 0) | split("\t")
                | {event: .[0], matcher: .[1], command: .[2], source: "UNREVIEWED"})' \
            | jq '{settings_additions: .}'
        printf '%s\n' "$plugin_live" | jq -R -s '
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

echo "Settings hooks (${SETTINGS/#"$HOME"/\~}):"
expected="$(printf '%s\n%s\n' "$base_tuples" "$addn_tuples" | grep -v '^$' | sort -u)"

new_live="$(comm -23 <(printf '%s\n' "$live_tuples" | grep -v '^$') \
                     <(printf '%s\n' "$expected"))"
if [[ -n "$new_live" ]]; then
    while IFS=$'\t' read -r ev m cmd; do
        log_err "UNREVIEWED hook in settings.json: ${ev} [${m}] -> ${cmd}"
        unreviewed=$((unreviewed + 1))
    done <<< "$new_live"
else
    log_ok "no unreviewed hooks in settings.json"
fi

missing_base="$(comm -23 <(printf '%s\n' "$base_tuples" | grep -v '^$') \
                         <(printf '%s\n' "$live_tuples" | grep -v '^$'))"
if [[ -n "$missing_base" ]]; then
    while IFS=$'\t' read -r ev m cmd; do
        log_warn "repo hook not live (run setup.sh): ${ev} [${m}] -> ${cmd}"
        attention=$((attention + 1))
    done <<< "$missing_base"
fi

missing_addn="$(comm -23 <(printf '%s\n' "$addn_tuples" | grep -v '^$') \
                         <(printf '%s\n' "$live_tuples" | grep -v '^$'))"
if [[ -n "$missing_addn" ]]; then
    while IFS=$'\t' read -r ev m cmd; do
        log_warn "allowlisted addition not live (stale entry or wiped by merge): ${ev} [${m}] -> ${cmd}"
        attention=$((attention + 1))
    done <<< "$missing_addn"
fi

# ---------- Verify: plugin plane ----------
echo ""
echo "Plugin hooks (${PLUGIN_CACHE/#"$HOME"/\~}, enabled plugins only):"

new_plugin="$(comm -23 <(printf '%s\n' "$plugin_live" | grep -v '^$') \
                       <(printf '%s\n' "$plugin_allow" | grep -v '^$'))"
if [[ -n "$new_plugin" ]]; then
    while IFS=$'\t' read -r pkey ev m cmd; do
        log_err "UNREVIEWED plugin hook: ${pkey}: ${ev} [${m}] -> ${cmd}"
        unreviewed=$((unreviewed + 1))
    done <<< "$new_plugin"
else
    log_ok "all enabled-plugin hooks are allowlisted"
fi

stale_plugin="$(comm -23 <(printf '%s\n' "$plugin_allow" | grep -v '^$') \
                         <(printf '%s\n' "$plugin_live" | grep -v '^$'))"
if [[ -n "$stale_plugin" ]]; then
    while IFS=$'\t' read -r pkey ev m cmd; do
        log_warn "stale allowlist entry (plugin disabled, removed, or hook changed): ${pkey}: ${ev} [${m}] -> ${cmd}"
        attention=$((attention + 1))
    done <<< "$stale_plugin"
fi

# ---------- Info: dormant plugin caches ----------
dormant=()
if [[ -d "$PLUGIN_CACHE" ]]; then
    while IFS= read -r hf; do
        [[ "$hf" == *"/.codex/"* ]] && continue
        rel="${hf#"${PLUGIN_CACHE}"/}"
        mp="${rel%%/*}"; rest="${rel#*/}"; name="${rest%%/*}"
        pkey="${name}@${mp}"
        if ! grep -qxF "$pkey" <<< "$enabled_plugins"; then
            dormant+=("$pkey")
        fi
    done < <(find "$PLUGIN_CACHE" -name hooks.json -path '*/hooks/hooks.json' 2>/dev/null)
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
