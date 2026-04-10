#!/usr/bin/env bash
# setup.sh — Bootstrap ~/.claude/ symlinks for this Claude config repo
#
# Run once after cloning:
#   git clone --recurse-submodules https://github.com/ByronWilliamsCPA/.claude.git ~/dev/.claude
#   cd ~/dev/.claude && ./setup.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
CONFIG_DIR="${REPO_DIR}/.claude"

echo "Repo:   ${REPO_DIR}"
echo "Config: ${CLAUDE_DIR}"
echo ""

# Verify submodules are initialized
if [ ! -f "${REPO_DIR}/.submodules/reference-library/agents/document-drafter.md" ]; then
    echo "Submodules not initialized. Running: git submodule update --init --recursive"
    git -C "${REPO_DIR}" submodule update --init --recursive
fi

# Create ~/.claude/ if it doesn't exist
mkdir -p "${CLAUDE_DIR}"

# Symlink the three Claude-consumable directories
for dir in agents skills commands; do
    target="${CLAUDE_DIR}/${dir}"
    source="${CONFIG_DIR}/${dir}"

    if [ -L "${target}" ]; then
        echo "  [skip] ~/.claude/${dir} already symlinked"
    elif [ -d "${target}" ]; then
        echo "  [warn] ~/.claude/${dir} exists as a real directory — back it up and re-run to replace"
    else
        ln -s "${source}" "${target}"
        echo "  [ok]   ~/.claude/${dir} -> ${source}"
    fi
done

# Symlink reference-library at a stable, predictable path.
# Agents in reference-library use {{LIBRARY_PATH}} as a placeholder; this symlink
# makes ~/.claude/reference-library the resolved value on every machine — no
# per-machine substitution required.
RL_TARGET="${CLAUDE_DIR}/reference-library"
RL_SOURCE="${REPO_DIR}/.submodules/reference-library"
if [ -L "${RL_TARGET}" ]; then
    echo "  [skip] ~/.claude/reference-library already symlinked"
elif [ -d "${RL_TARGET}" ]; then
    echo "  [warn] ~/.claude/reference-library exists as a real directory — back it up and re-run to replace"
else
    ln -s "${RL_SOURCE}" "${RL_TARGET}"
    echo "  [ok]   ~/.claude/reference-library -> ${RL_SOURCE}"
fi

# Symlink scripts/ so $HOME/.claude/scripts/... hook paths resolve correctly.
SCRIPTS_TARGET="${CLAUDE_DIR}/scripts"
SCRIPTS_SOURCE="${REPO_DIR}/scripts"
if [ -L "${SCRIPTS_TARGET}" ]; then
    echo "  [skip] ~/.claude/scripts already symlinked"
elif [ -d "${SCRIPTS_TARGET}" ]; then
    echo "  [warn] ~/.claude/scripts exists as a real directory — back it up and re-run to replace"
else
    ln -s "${SCRIPTS_SOURCE}" "${SCRIPTS_TARGET}"
    echo "  [ok]   ~/.claude/scripts -> ${SCRIPTS_SOURCE}"
fi

# Merge canonical hooks into ~/.claude/settings.json
# hooks.json is the source of truth for global Claude Code hooks.
# Running setup.sh is idempotent — it replaces the hooks key each time.
HOOKS_SOURCE="${REPO_DIR}/hooks.json"
SETTINGS="${CLAUDE_DIR}/settings.json"

if ! command -v jq &>/dev/null; then
    echo "  [warn] jq not found — install it and re-run to apply hooks"
    echo "         Or manually copy .hooks from ${HOOKS_SOURCE} into ${SETTINGS}"
elif [[ ! -f "${HOOKS_SOURCE}" ]]; then
    echo "  [warn] hooks.json not found at ${HOOKS_SOURCE}"
else
    if [[ -f "${SETTINGS}" ]]; then
        jq --slurpfile h "${HOOKS_SOURCE}" '.hooks = $h[0]' "${SETTINGS}" > "${SETTINGS}.tmp" \
            && mv "${SETTINGS}.tmp" "${SETTINGS}"
        echo "  [ok]   ~/.claude/settings.json hooks updated from hooks.json"
    else
        jq -n --slurpfile h "${HOOKS_SOURCE}" '{hooks: $h[0]}' > "${SETTINGS}"
        echo "  [ok]   ~/.claude/settings.json created with hooks"
    fi
fi

echo ""
echo "Done. Verify with: ls -la ~/.claude/"
echo ""
echo "Note: agents in reference-library use {{LIBRARY_PATH}} as a placeholder."
echo "      Resolve it to: ~/.claude/reference-library"
