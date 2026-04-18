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

# pwd -P resolves the physical path, handling the ~/.claude/scripts symlink.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

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

log_ok()   { echo "  [ok]   $*"; }
log_skip() { echo "  [skip] $*"; }
log_err()  { echo "  [err]  $*" >&2; }

command -v claude >/dev/null 2>&1 || {
    log_err "claude CLI not found in PATH. Install Claude Code first."
    exit 1
}

# ---------- Marketplaces ----------
echo "Registering marketplaces..."
existing_markets=""
if ! existing_markets="$(claude plugin marketplace list 2>/dev/null)"; then
    log_err "claude plugin marketplace list failed; cannot determine registered marketplaces"
    exit 1
fi

for entry in "${MARKETPLACES[@]}"; do
    path="${entry%%:*}"
    name="${entry##*:}"

    if [ ! -d "$path" ]; then
        log_err "Missing submodule: $path"
        log_err "  Run: git submodule update --init --recursive"
        exit 1
    fi

    if grep -qF "$name" <<< "$existing_markets"; then
        log_skip "marketplace $name already registered"
        continue
    fi

    err_output=""
    if ! err_output="$(claude plugin marketplace add "$path" --scope user 2>&1)"; then
        log_err "marketplace add failed for $name: ${err_output}"
        exit 1
    fi
    log_ok "marketplace added: $name ($path)"
done

# ---------- Plugins ----------
echo ""
echo "Installing plugins..."

# claude-plugins-official is expected pre-registered by Claude Code defaults.
# Verify before attempting remote installs so failures are diagnosed clearly.
if ! grep -qF "claude-plugins-official" <<< "$existing_markets"; then
    log_err "claude-plugins-official marketplace not found; remote plugins cannot be installed"
    log_err "  Check that Claude Code user defaults are intact: claude plugin marketplace list"
    exit 1
fi

existing_plugins=""
if ! existing_plugins="$(claude plugin list 2>/dev/null)"; then
    log_err "claude plugin list failed; cannot determine installed plugins"
    exit 1
fi

for pkg in "${PLUGINS[@]}"; do
    if grep -qF "$pkg" <<< "$existing_plugins"; then
        log_skip "plugin $pkg already installed"
        continue
    fi

    err_output=""
    if ! err_output="$(claude plugin install "$pkg" --scope user 2>&1)"; then
        log_err "plugin install failed for $pkg: ${err_output}"
        exit 1
    fi
    log_ok "plugin installed: $pkg"
done

echo ""
echo "Done. Verify with: claude plugin list"
