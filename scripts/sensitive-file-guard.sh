#!/usr/bin/env bash
# =============================================================================
# Sensitive File Guard -- PreToolUse Hook (Edit, Write)
# =============================================================================
# Blocks Claude Code from editing or writing files whose paths match
# high-value credential or secret-bearing patterns. Replaces the inline guard
# previously embedded in hooks.json (audit findings H-05 and I-02).
#
# Patterns blocked:
#   .env files, settings.local.json (existing coverage)
#   SSH private keys: id_rsa, id_dsa, id_ecdsa, id_ed25519
#   AWS credentials: ~/.aws/credentials and ~/.aws/config
#   Cloud / package registry tokens: ~/.netrc, ~/.npmrc, ~/.pypirc, ~/.docker/config.json
#   TLS / GPG private material: *.pem, *.key, *.p12, *.pfx, *.kdbx, gpg keyring files
#   Secrets baselines: *.secrets.baseline (overwrite would suppress detection)
#   Cloud platform creds: gcloud application_default_credentials.json
#
# Always exits 2 on a match (BLOCKED) so Claude Code surfaces the message and
# refuses the operation. Exits 0 on no match.
# =============================================================================

set -uo pipefail

FILE="${CLAUDE_FILE_PATH:-}"
[[ -z "$FILE" ]] && exit 0

# Use case-insensitive shell pattern matching for the path comparisons below.
shopt -s nocasematch

case "$FILE" in
    # Existing coverage. *.env* covers .env, .env.local, .env.production, etc.
    *.env*|*/settings.local.json)
        echo 'BLOCKED: editing secrets file requires explicit confirmation'
        exit 2
        ;;
    # SSH private keys (no _pub suffix needed because public keys do not match these names)
    *id_rsa|*id_rsa.*|*id_dsa|*id_dsa.*|*id_ecdsa|*id_ecdsa.*|*id_ed25519|*id_ed25519.*)
        # Allow public keys: the .pub variant matches *id_rsa.pub which contains
        # ".pub" not just ".*"; refine by excluding *.pub suffix.
        case "$FILE" in
            *.pub) ;;  # public key, allow
            *)
                echo "BLOCKED: SSH private key path detected: $FILE"
                exit 2
                ;;
        esac
        ;;
    # AWS, gcloud, container, package, GPG credential paths
    */.aws/credentials|*/.aws/config|*/.netrc|*/.npmrc|*/.pypirc|*/.docker/config.json)
        echo "BLOCKED: cloud or package registry credential path detected: $FILE"
        exit 2
        ;;
    */application_default_credentials.json|*/gcloud/credentials.db)
        echo "BLOCKED: gcloud credential file detected: $FILE"
        exit 2
        ;;
    # TLS / private key file extensions
    *.pem|*.key|*.p12|*.pfx|*.kdbx)
        echo "BLOCKED: private-key or password-database file detected: $FILE"
        exit 2
        ;;
    # GPG keyring locations
    */.gnupg/*|*/secring.gpg|*/private-keys-v1.d/*)
        echo "BLOCKED: GPG keyring path detected: $FILE"
        exit 2
        ;;
    # detect-secrets baseline: overwriting it suppresses all future findings
    *secrets.baseline)
        echo "BLOCKED: secrets baseline edit requires explicit user action"
        exit 2
        ;;
esac

exit 0
