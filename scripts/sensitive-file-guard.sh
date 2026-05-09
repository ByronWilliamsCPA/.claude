#!/usr/bin/env bash
# =============================================================================
# Sensitive File Guard -- PreToolUse Hook (Edit, Write, MultiEdit)
# =============================================================================
# Blocks Claude Code from editing or writing files whose paths match
# high-value credential or secret-bearing patterns. Replaces the inline guard
# previously embedded in hooks.json (audit findings H-05 and I-02).
#
# Patterns blocked:
#   .env files, settings.local.json (existing coverage)
#   SSH private keys: id_rsa, id_dsa, id_ecdsa, id_ed25519 (with id_*.pub allowed)
#   AWS credentials: .aws/credentials and .aws/config (any depth)
#   Package and registry tokens: .netrc, .npmrc, .pypirc, .docker/config.json
#   TLS / GPG private material: *.pem, *.key, *.p12, *.pfx, *.kdbx, gpg keyring files
#   Secrets baselines: *secrets.baseline (overwrite would suppress detection)
#   gcloud credentials: application_default_credentials.json, credentials.db
#
# Patterns are intentionally case-sensitive (Linux convention). The previous
# version used `shopt -s nocasematch` which made id_rsa.PUB match the .pub
# carve-out even if the file was actually a privately-named private key.
#
# All credential dotfile patterns now match both bare relative names
# (.netrc) and absolute or nested paths (/home/user/.netrc) by using *suffix
# style without a leading slash requirement.
#
# Each block emits a BLOCKED message AND a stderr audit log entry so an
# operator can later confirm the guard fired (audit pr-fix follow-up).
#
# Always exits 2 on a match (BLOCKED) so Claude Code surfaces the message and
# refuses the operation. Exits 0 on no match.
# =============================================================================

set -uo pipefail

FILE="${CLAUDE_FILE_PATH:-}"
[[ -z "$FILE" ]] && exit 0

AUDIT_LOG="${HOME}/.claude/logs/sensitive-file-guard.log"
mkdir -p "$(dirname "$AUDIT_LOG")" 2>/dev/null || true
[[ -f "$AUDIT_LOG" ]] || { : > "$AUDIT_LOG"; chmod 600 "$AUDIT_LOG" 2>/dev/null || true; }

block() {
    local reason="$1"
    echo "BLOCKED: ${reason}: ${FILE}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] BLOCKED ${reason}: ${FILE}" >> "$AUDIT_LOG" 2>/dev/null || true
    exit 2
}

case "$FILE" in
    # Existing coverage. *.env* covers .env, .env.local, .env.production, etc.
    *.env*|*settings.local.json)
        block "secrets file (.env or settings.local.json)"
        ;;
    # SSH private keys. Carve out id_*.pub specifically, not any *.pub, so a
    # file deceptively named id_rsa.pub_old that is actually private material
    # is still blocked.
    *id_rsa.pub|*id_dsa.pub|*id_ecdsa.pub|*id_ed25519.pub)
        ;;  # known SSH public-key suffix, allow
    *id_rsa|*id_rsa.*|*id_dsa|*id_dsa.*|*id_ecdsa|*id_ecdsa.*|*id_ed25519|*id_ed25519.*)
        block "SSH private key path"
        ;;
    # AWS, gcloud, container, package credential paths. Suffix patterns match
    # both bare relative paths (.netrc) and any nested form (/home/user/.netrc).
    *.aws/credentials|*.aws/config|*.netrc|*.npmrc|*.pypirc|*.docker/config.json)
        block "cloud or package registry credential path"
        ;;
    *application_default_credentials.json|*gcloud/credentials.db)
        block "gcloud credential file"
        ;;
    # TLS / private key file extensions
    *.pem|*.key|*.p12|*.pfx|*.kdbx)
        block "private-key or password-database file"
        ;;
    # GPG keyring locations
    *.gnupg/*|*secring.gpg|*private-keys-v1.d/*)
        block "GPG keyring path"
        ;;
    # detect-secrets baseline: overwriting it suppresses all future findings
    *secrets.baseline)
        block "secrets baseline edit (requires explicit user action)"
        ;;
esac

exit 0
