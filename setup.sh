#!/usr/bin/env bash
# setup.sh — Bootstrap ~/.claude/ symlinks for this Claude config repo
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
log_info()  { echo "  [info] $*"; }
log_ok()    { echo "  [ok]   $*"; }
log_skip()  { echo "  [skip] $*"; }
log_warn()  { echo "  [warn] $*" >&2; }
log_error() { echo "  [err]  $*" >&2; }

run_or_dry() {
    if (( DRY_RUN )); then
        echo "  [dry]  $*"
    else
        "$@"
    fi
}

# ---------- Preflight ----------
preflight() {
    local missing=()
    for cmd in jq ln git; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        log_error "Missing required commands: ${missing[*]}"
        log_error "Install them and re-run setup.sh"
        exit 3
    fi
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
            if [[ "$actual" == "$expected" ]]; then
                printf "  [ok]   %-40s -> %s\n" "${link/#$HOME/~}" "${expected/#$HOME/~}"
            else
                printf "  [drift] %-40s -> %s (expected %s)\n" \
                    "${link/#$HOME/~}" "${actual/#$HOME/~}" "${expected/#$HOME/~}"
                broken=$((broken + 1))
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
        if jq -e '.hooks' "${CLAUDE_DIR}/settings.json" >/dev/null 2>&1; then
            log_ok "hooks merged"
        else
            log_warn "hooks missing (run setup.sh to merge from hooks.json)"
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
    if (( broken > 0 )); then
        log_warn "${broken} symlink(s) need attention. Run ./setup.sh to fix."
        exit 1
    fi
    log_ok "All checks passed."
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
}

merge_hooks() {
    local hooks_source="${REPO_DIR}/hooks.json"
    local settings="${CLAUDE_DIR}/settings.json"

    if [[ ! -f "$hooks_source" ]]; then
        log_warn "hooks.json not found at ${hooks_source}"
        return 0
    fi

    if (( DRY_RUN )); then
        echo "  [dry]  jq merge hooks.json -> ${settings/#$HOME/~}"
        return 0
    fi

    if [[ -f "$settings" ]]; then
        jq --slurpfile h "$hooks_source" '.hooks = $h[0]' "$settings" > "${settings}.tmp" \
            && mv "${settings}.tmp" "$settings"
        log_ok "settings.json hooks updated from hooks.json"
    else
        jq -n --slurpfile h "$hooks_source" '{hooks: $h[0]}' > "$settings"
        log_ok "settings.json created with hooks"
    fi
}

merge_claude_md_excludes() {
    local settings="${CLAUDE_DIR}/settings.json"

    if [[ ! -f "$settings" ]]; then
        log_warn "settings.json missing, skipping claudeMdExcludes merge"
        return 0
    fi

    if (( DRY_RUN )); then
        echo "  [dry]  jq set .claudeMdExcludes = [\"${REPO_DIR}/CLAUDE.md\", \"${REPO_DIR}/.claude/**\"]"
        return 0
    fi

    jq --arg repo "$REPO_DIR" \
        '.claudeMdExcludes = [$repo + "/CLAUDE.md", $repo + "/.claude/**"]' \
        "$settings" > "${settings}.tmp" \
        && mv "${settings}.tmp" "$settings"
    log_ok "settings.json claudeMdExcludes set for ${REPO_DIR/#$HOME/~}"
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
