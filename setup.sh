#!/usr/bin/env bash
# setup.sh: Bootstrap ~/.claude/ symlinks for this Claude config repo
#
# Run once after cloning:
#   git clone --recurse-submodules https://github.com/ByronWilliamsCPA/.claude.git ~/dev/.claude
#   cd ~/dev/.claude && ./setup.sh
#
# Options:
#   --dry-run   Print what would change without making any edits
#   --doctor    Print the resolved symlink topology and check for broken links
#   --help      Show this help message
#
# Safe to re-run. All actions are idempotent.

set -euo pipefail

# ---------- Paths ----------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
CONFIG_DIR="${REPO_DIR}/.claude"

# ---------- Flags ----------
DRY_RUN=0
DOCTOR=0
for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=1 ;;
        --doctor)   DOCTOR=1 ;;
        --help|-h)
            sed -n '/^# setup\.sh/,/^# Safe to re-run/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown flag: $arg (try --help)" >&2
            exit 2
            ;;
    esac
done

# ---------- Logging helpers ----------
# Each function ends with `return 0` to satisfy SonarQube shelldre:S7682
# ("Add an explicit return statement at the end of the function"). The
# explicit return also prevents a false non-zero exit status from bubbling
# up under `set -e` when an `echo` is the last command in a pipeline that
# somewhere fails.
log_info()  { echo "  [info] $*"; return 0; }
log_ok()    { echo "  [ok]   $*"; return 0; }
log_skip()  { echo "  [skip] $*"; return 0; }
log_warn()  { echo "  [warn] $*" >&2; return 0; }
log_error() { echo "  [err]  $*" >&2; return 0; }

run_or_dry() {
    if (( DRY_RUN )); then
        echo "  [dry]  $*"
    else
        "$@"
    fi
    return 0
}

# ---------- Preflight ----------
# Hard requirements (needed for symlink install): ln, git. Without these,
# setup.sh cannot run at all.
# Soft requirement (needed only for settings.json merge steps): jq. If jq
# is absent, the symlinks are still created, but the hooks and
# claudeMdExcludes merge steps are skipped with a warning. This matches the
# pre-refactor behavior and avoids a regression where jq-less systems
# couldn't bootstrap symlinks.
preflight() {
    local missing=()
    for cmd in ln git; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        log_error "Missing required commands: ${missing[*]}"
        log_error "Install them and re-run setup.sh"
        exit 3
    fi
    if ! command -v jq &>/dev/null; then
        log_warn "jq not found. Symlinks will be created, but hooks and"
        log_warn "claudeMdExcludes merges into ~/.claude/settings.json will be"
        log_warn "skipped. Install jq (apt install jq / brew install jq) and"
        log_warn "re-run to finish the install."
    fi
    return 0
}

# ---------- Doctor mode ----------
doctor() {
    echo "Claude Config Topology"
    echo "======================"
    echo ""
    echo "Repo:        ${REPO_DIR}"
    echo "User config: ${CLAUDE_DIR}"
    echo ""
    echo "Expected symlinks:"

    local targets=(
        "${CLAUDE_DIR}/CLAUDE.md:${REPO_DIR}/CLAUDE.md"
        "${CLAUDE_DIR}/agents:${CONFIG_DIR}/agents"
        "${CLAUDE_DIR}/skills:${CONFIG_DIR}/skills"
        "${CLAUDE_DIR}/commands:${CONFIG_DIR}/commands"
        "${CLAUDE_DIR}/rules:${CONFIG_DIR}/rules"
        "${CLAUDE_DIR}/standards:${CONFIG_DIR}/standards"
        "${CLAUDE_DIR}/reference-library:${REPO_DIR}/.submodules/reference-library"
        "${CLAUDE_DIR}/scripts:${REPO_DIR}/scripts"
    )

    local broken=0
    for entry in "${targets[@]}"; do
        local link="${entry%%:*}"
        local expected="${entry##*:}"
        if [[ -L "$link" ]]; then
            local actual
            actual="$(readlink "$link")"
            if [[ "$actual" != "$expected" ]]; then
                printf "  [drift] %-40s -> %s (expected %s)\n" \
                    "${link/#$HOME/~}" "${actual/#$HOME/~}" "${expected/#$HOME/~}"
                broken=$((broken + 1))
            elif [[ ! -e "$link" ]]; then
                # Symlink points at the expected path, but that path does
                # not exist (dangling). Common cause: submodules not
                # initialized or a referenced directory was removed.
                printf "  [dangle] %-40s -> %s (target missing)\n" \
                    "${link/#$HOME/~}" "${expected/#$HOME/~}"
                broken=$((broken + 1))
            else
                printf "  [ok]   %-40s -> %s\n" "${link/#$HOME/~}" "${expected/#$HOME/~}"
            fi
        elif [[ -e "$link" ]]; then
            printf "  [real]  %-40s (regular file, not symlink)\n" "${link/#$HOME/~}"
            broken=$((broken + 1))
        else
            printf "  [miss]  %-40s (not present)\n" "${link/#$HOME/~}"
            broken=$((broken + 1))
        fi
    done

    echo ""
    echo "Settings (${CLAUDE_DIR}/settings.json):"
    if [[ -f "${CLAUDE_DIR}/settings.json" ]]; then
        # Structural hooks drift check: flatten both hooks.json and
        # settings.json .hooks to (event, matcher, command) triples and
        # report drift in BOTH directions. Key-existence alone is not
        # enough: a clobbered .hooks key still "exists" while missing
        # entries (senior review 2026-07-01, Critical finding).
        if ! command -v jq &>/dev/null; then
            log_warn "jq not found; cannot check hooks drift"
            broken=$((broken + 1))
        elif [[ ! -f "${REPO_DIR}/hooks.json" ]]; then
            log_warn "hooks.json not found at ${REPO_DIR}/hooks.json; cannot check hooks drift"
            broken=$((broken + 1))
        else
            local drift_json line drift_found=0
            if ! drift_json="$(jq -n \
                --slurpfile repo "${REPO_DIR}/hooks.json" \
                --slurpfile live "${CLAUDE_DIR}/settings.json" '
                def triples($obj): [ ($obj // {}) | to_entries[] as $e
                    | $e.value[]? as $g | ($g.matcher // "") as $m
                    | $g.hooks[]? | "\($e.key)[\($m)] \(.command)" ];
                (triples($repo[0])) as $r
                | (triples($live[0].hooks)) as $l
                | {repo_not_live: ($r - $l), live_not_repo: ($l - $r)}')"; then
                log_warn "could not parse hooks.json or settings.json; hooks drift check skipped"
                broken=$((broken + 1))
                drift_json='{"repo_not_live":[],"live_not_repo":[]}'
                drift_found=1
            fi

            while IFS= read -r line; do
                [[ -n "$line" ]] || continue
                log_warn "hook in hooks.json but not live: ${line} (run setup.sh)"
                broken=$((broken + 1))
                drift_found=1
            done < <(jq -r '.repo_not_live[]' <<< "$drift_json")

            # Live-only entries referencing a repo script mean a repo-owned
            # hook was registered directly in settings.json and never
            # backported; that is exactly the drift class that caused the
            # 2026-07-01 incident. Other live-only entries belong to
            # foreign installers (e.g. codebase-memory-mcp) and are
            # expected: the union merge preserves them.
            while IFS= read -r line; do
                [[ -n "$line" ]] || continue
                if [[ "$line" == *"/.claude/scripts/"* ]]; then
                    log_warn "live-only hook references a repo script (backport to hooks.json): ${line}"
                    broken=$((broken + 1))
                else
                    log_info "live-only hook (foreign installer, preserved by merge): ${line}"
                fi
                drift_found=1
            done < <(jq -r '.live_not_repo[]' <<< "$drift_json")

            if (( drift_found == 0 )); then
                log_ok "hooks in sync with hooks.json"
            fi
        fi
        if jq -e '.claudeMdExcludes' "${CLAUDE_DIR}/settings.json" >/dev/null 2>&1; then
            log_ok "claudeMdExcludes present"
        else
            log_warn "claudeMdExcludes missing (run setup.sh to add repo-path excludes)"
        fi
    else
        log_warn "settings.json not found"
    fi

    echo ""
    echo "Hook sources (scripts/check-hook-sources.sh):"
    if command -v jq &>/dev/null; then
        # Exit 1 means an unreviewed hook-injection source is live; exit 2
        # means the checker could not run. Both need attention.
        if ! "${REPO_DIR}/scripts/check-hook-sources.sh"; then
            broken=$((broken + 1))
        fi
    else
        log_warn "jq not found; skipping hook-source drift check"
    fi

    echo ""
    echo "Vendored plugins (claude plugin list):"
    if command -v claude >/dev/null 2>&1; then
        local expected_plugins=(
            "superpowers@superpowers-dev"
            "document-skills@anthropic-agent-skills"
            "example-skills@anthropic-agent-skills"
            "claude-api@anthropic-agent-skills"
            "claude-code-setup@claude-plugins-official"
            "claude-md-management@claude-plugins-official"
            "session-report@claude-plugins-official"
            "hookify@claude-plugins-official"
            "pr-review-toolkit@claude-plugins-official"
            "code-review@claude-plugins-official"
        )
        local installed
        local missing=0
        if ! installed="$(claude plugin list 2>/dev/null)"; then
            log_warn "claude plugin list failed; cannot verify installed plugins"
            missing=${#expected_plugins[@]}
        else
            for pkg in "${expected_plugins[@]}"; do
                if grep -qF "$pkg" <<< "$installed"; then
                    log_ok "${pkg}"
                else
                    log_warn "${pkg} NOT installed"
                    missing=$((missing + 1))
                fi
            done
        fi
        if (( missing > 0 )); then
            log_warn "${missing} plugin(s) missing. Run ${REPO_DIR}/scripts/install-vendored-plugins.sh"
            broken=$((broken + missing))
        fi
    else
        log_warn "claude CLI not found; install Claude Code to enable plugin verification"
        broken=$((broken + 1))
    fi

    echo ""
    if (( broken > 0 )); then
        log_warn "${broken} item(s) need attention. See messages above."
        exit 1
    fi
    log_ok "All checks passed."
    return 0
}

# ---------- Symlink management ----------
ensure_symlink() {
    local target="$1"
    local source="$2"
    local rel_target="${target/#$HOME/~}"

    if [[ -L "$target" && "$(readlink "$target")" == "$source" ]]; then
        log_skip "${rel_target} already linked"
        return 0
    fi

    if [[ -e "$target" && ! -L "$target" ]]; then
        log_warn "${rel_target} exists as a real file/dir. Back it up and re-run to replace"
        return 1
    fi

    # -s: symlink, -f: force replace, -n: do not follow directory symlinks
    run_or_dry ln -sfn "$source" "$target"
    log_ok "${rel_target} -> ${source/#$HOME/~}"
}

ensure_submodules() {
    if [[ ! -f "${REPO_DIR}/.submodules/reference-library/agents/document-drafter.md" ]]; then
        log_info "Initializing submodules"
        run_or_dry git -C "${REPO_DIR}" submodule update --init --recursive
    fi
    return 0
}

# Refresh the plugin cache for plugins backed by local submodules. Plugin
# install copies files from the submodule into ~/.claude/plugins/cache/ at
# install time, so submodule updates do NOT propagate automatically. This
# closes that gap. Plugins from the remote claude-plugins-official
# marketplace update from GitHub on their own and are skipped here.
sync_local_plugins() {
    local local_plugins=(
        "superpowers@superpowers-dev"
        "document-skills@anthropic-agent-skills"
        "example-skills@anthropic-agent-skills"
        "claude-api@anthropic-agent-skills"
    )

    if ! command -v claude >/dev/null 2>&1; then
        log_skip "claude CLI not found; skipping plugin cache sync"
        return 0
    fi

    local installed
    if ! installed="$(claude plugin list 2>/dev/null)"; then
        log_warn "claude plugin list failed; skipping plugin cache sync"
        return 1
    fi

    for pkg in "${local_plugins[@]}"; do
        if ! grep -qF "$pkg" <<< "$installed"; then
            log_skip "${pkg} not installed; run ${REPO_DIR}/scripts/install-vendored-plugins.sh"
            continue
        fi
        if (( DRY_RUN )); then
            echo "  [dry]  claude plugin update ${pkg}"
            continue
        fi
        local err_output=""
        if ! err_output="$(claude plugin update "$pkg" 2>&1)"; then
            log_warn "failed to sync ${pkg}: ${err_output}"
        else
            log_ok "synced ${pkg}"
        fi
    done
    return 0
}

# ---------- Settings merge ----------
backup_settings() {
    local settings="$1"
    if [[ -f "$settings" ]]; then
        local backup
        backup="${settings}.bak.$(date +%Y%m%d-%H%M%S)"
        run_or_dry cp "$settings" "$backup"
        log_ok "backup -> ${backup/#$HOME/~}"
    fi
    return 0
}

# Union-merge repo hooks.json into settings.json .hooks without deleting
# entries written by other installers.
#
# #CRITICAL: ~/.claude/settings.json .hooks has MULTIPLE WRITERS: this
# script, codebase-memory-mcp's installer (SessionStart entries and the
# Grep|Glob code-discovery gate), and occasional direct edits. This merge
# must never remove an entry it does not recognize; a previous
# replace-assignment here (`.hooks = $h[0]`) silently deleted live
# security-control hooks (senior review 2026-07-01, Critical finding).
# #VERIFY: tests/test_setup_hooks.bats asserts foreign entries survive and
# the merge is idempotent; `setup.sh --doctor` reports drift in both
# directions between hooks.json and settings.json.
#
# Semantics: hook identity is the pair (group matcher, hook command).
# Repo groups are emitted verbatim per event type (repo is authoritative
# for its own entries, so timeout/statusMessage edits propagate); settings
# groups follow with repo-known hooks filtered out, emptied groups
# dropped. Event types present only in settings pass through untouched.
# Removing a hook from hooks.json therefore never removes it from a live
# settings.json; deliberate removals show up in `--doctor` as live-only
# drift and are handled manually.
merge_hooks() {
    local hooks_source="${REPO_DIR}/hooks.json"
    local settings="${CLAUDE_DIR}/settings.json"

    if ! command -v jq &>/dev/null; then
        log_warn "jq not found, skipping hooks merge"
        return 0
    fi

    if [[ ! -f "$hooks_source" ]]; then
        log_warn "hooks.json not found at ${hooks_source}"
        return 0
    fi

    if (( DRY_RUN )); then
        echo "  [dry]  jq union-merge hooks.json -> ${settings/#$HOME/~} (preserves foreign entries)"
        return 0
    fi

    if [[ ! -f "$settings" ]]; then
        jq -n --slurpfile h "$hooks_source" '{hooks: $h[0]}' > "$settings"
        log_ok "settings.json created with hooks"
        return 0
    fi

    jq --slurpfile h "$hooks_source" '
        ($h[0]) as $repo
        | (.hooks // {}) as $live
        | .hooks = (
            (($repo | keys) + ($live | keys) | unique)
            | map(
                . as $ev
                | ($repo[$ev] // []) as $rg
                | ($live[$ev] // []) as $lg
                | ([ $rg[] as $g | ($g.matcher // "") as $m
                     | $g.hooks[]? | [$m, .command] ]) as $rid
                | ($lg
                   | map( . as $g
                          | ($g.matcher // "") as $m
                          | $g + { hooks: (($g.hooks // []) | map(
                                .command as $c
                                | select(([$m, $c] | IN($rid[])) | not)
                            )) }
                        )
                   | map(select(.hooks | length > 0))
                  ) as $foreign
                | { key: $ev, value: ($rg + $foreign) }
              )
            | from_entries
          )
    ' "$settings" > "${settings}.tmp" || {
        rm -f "${settings}.tmp"
        log_error "hooks merge failed (invalid JSON in settings.json or hooks.json); settings.json left unchanged"
        exit 4
    }

    if cmp -s "$settings" "${settings}.tmp"; then
        rm -f "${settings}.tmp"
        log_skip "settings.json hooks already current"
    else
        mv "${settings}.tmp" "$settings"
        log_ok "settings.json hooks union-merged from hooks.json (foreign entries preserved)"
    fi
}

# Merge repo-specific claudeMdExcludes into the existing array, preserving
# any user-defined excludes already present and deduplicating the result.
# Uses jq to: normalize the existing key to an array (default to empty if
# missing or wrong type), append the two repo-specific patterns, then pass
# the combined array through `unique` so duplicates collapse.
merge_claude_md_excludes() {
    local settings="${CLAUDE_DIR}/settings.json"

    if ! command -v jq &>/dev/null; then
        log_warn "jq not found, skipping claudeMdExcludes merge"
        return 0
    fi

    if [[ ! -f "$settings" ]]; then
        log_warn "settings.json missing, skipping claudeMdExcludes merge"
        return 0
    fi

    if (( DRY_RUN )); then
        echo "  [dry]  jq merge .claudeMdExcludes += [\"${REPO_DIR}/CLAUDE.md\", \"${REPO_DIR}/.claude/**\"] (dedupe)"
        return 0
    fi

    jq --arg repo "$REPO_DIR" \
        '.claudeMdExcludes = (
            (((.claudeMdExcludes // []) | if type == "array" then . else [] end)
             + [$repo + "/CLAUDE.md", $repo + "/.claude/**"])
            | unique
        )' \
        "$settings" > "${settings}.tmp" \
        && mv "${settings}.tmp" "$settings"
    log_ok "settings.json claudeMdExcludes merged for ${REPO_DIR/#$HOME/~}"
}

# ---------- Main ----------
preflight

if (( DOCTOR )); then
    doctor
    exit 0
fi

echo "Repo:   ${REPO_DIR}"
echo "Config: ${CLAUDE_DIR}"
if (( DRY_RUN )); then
    echo "Mode:   DRY RUN (no changes will be applied)"
fi
echo ""

ensure_submodules
sync_local_plugins

run_or_dry mkdir -p "$CLAUDE_DIR"

# Symlink CLAUDE.md, agents, skills, commands, rules, standards
ensure_symlink "${CLAUDE_DIR}/CLAUDE.md"  "${REPO_DIR}/CLAUDE.md"
for dir in agents skills commands rules standards; do
    ensure_symlink "${CLAUDE_DIR}/${dir}" "${CONFIG_DIR}/${dir}"
done

# Symlink reference-library and scripts
ensure_symlink "${CLAUDE_DIR}/reference-library" "${REPO_DIR}/.submodules/reference-library"
ensure_symlink "${CLAUDE_DIR}/scripts"           "${REPO_DIR}/scripts"

# Settings merge (backup -> hooks -> claudeMdExcludes)
backup_settings "${CLAUDE_DIR}/settings.json"
merge_hooks
merge_claude_md_excludes

echo ""
echo "Done. Verify with: ./setup.sh --doctor"
echo ""
echo "Note: agents in reference-library use {{LIBRARY_PATH}} as a placeholder."
echo "      Resolve it to: ~/.claude/reference-library"
