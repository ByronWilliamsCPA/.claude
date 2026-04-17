#!/usr/bin/env bash
# install-vendored-plugins.sh
#
# Register local marketplaces from the vendored submodules and install the
# plugins they provide. Idempotent: safe to re-run.
#
# Required because Claude Code treats a skill loaded via symlink
# (~/.claude/skills/<name>) and a skill loaded via plugin
# (<plugin>:<name>) as DIFFERENT identifiers. Several skills hand off work
# using the namespaced form (e.g. writing-plans tells the next session to
# use superpowers:subagent-driven-development). Without plugin
# registration, that namespaced invocation silently falls through.
#
# Scope: "user", so the plugins are available across every project, matching
# the global config pattern used by this repo's symlink topology.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Marketplaces to register: <local-path>:<expected-marketplace-name>
# The marketplace name is taken from the submodule's
# .claude-plugin/marketplace.json "name" field.
MARKETPLACES=(
    "${REPO_DIR}/.submodules/superpowers:superpowers-dev"
    "${REPO_DIR}/.submodules/anthropics-skills:anthropic-agent-skills"
)

# Plugins to install: <plugin>@<marketplace>
# claude-plugins-official is already registered by the user scope defaults;
# these plugins exist in that remote marketplace, so we install from there
# rather than re-registering the anthropics-plugins submodule under a
# conflicting name.
PLUGINS=(
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

log_info() { echo "  [info] $*"; }
log_ok()   { echo "  [ok]   $*"; }
log_skip() { echo "  [skip] $*"; }
log_err()  { echo "  [err]  $*" >&2; }

command -v claude >/dev/null 2>&1 || {
    log_err "claude CLI not found in PATH. Install Claude Code first."
    exit 1
}

# ---------- Marketplaces ----------
echo "Registering marketplaces..."
existing_markets="$(claude plugin marketplace list 2>/dev/null || true)"

for entry in "${MARKETPLACES[@]}"; do
    path="${entry%%:*}"
    name="${entry##*:}"

    if [ ! -d "$path" ]; then
        log_err "Missing submodule: $path"
        log_err "  Run: git submodule update --init --recursive"
        exit 1
    fi

    if grep -qE "^\s*❯?\s*${name}\b" <<< "$existing_markets"; then
        log_skip "marketplace $name already registered"
        continue
    fi

    if claude plugin marketplace add "$path" --scope user >/dev/null 2>&1; then
        log_ok "marketplace added: $name ($path)"
    else
        log_err "marketplace add failed for $name"
        exit 1
    fi
done

# ---------- Plugins ----------
echo ""
echo "Installing plugins..."
existing_plugins="$(claude plugin list 2>/dev/null || true)"

for pkg in "${PLUGINS[@]}"; do
    if grep -qE "^\s*❯?\s*${pkg}\b" <<< "$existing_plugins"; then
        log_skip "plugin $pkg already installed"
        continue
    fi

    if claude plugin install "$pkg" --scope user >/dev/null 2>&1; then
        log_ok "plugin installed: $pkg"
    else
        log_err "plugin install failed for $pkg"
        exit 1
    fi
done

echo ""
echo "Done. Verify with: claude plugin list"
