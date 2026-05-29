#!/usr/bin/env bash
# check-steering-secrets.sh -- CLAUDE-014 verifier.
#
# Defense-in-depth scan for embedded credentials on the agent config surface:
# CLAUDE.md, AGENTS.md, GEMINI.md, and .claude/settings.json. The primary
# control is the pre-commit detect-secrets / trufflehog hooks; this script is
# a belt-and-suspenders gate that runs independently of git staging state.
#
# Exit 0 when no pattern matches; exit 1 (and print redacted offending lines)
# when any credential pattern is found. A missing file is skipped, not failed:
# the parity and presence checks own file-existence assertions.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

FILES=(
    "CLAUDE.md"
    "AGENTS.md"
    "GEMINI.md"
    ".claude/settings.json"
)

# Pattern set per the CLAUDE-014 verify hint. Each entry is a basic-ERE that
# grep -E understands. The generic hex token is bounded to 32 or more chars to
# avoid matching short commit shas in prose.
PATTERNS=(
    'gh[pousr]_[A-Za-z0-9]{36,}'
    'sk-[A-Za-z0-9]{32,}'
    'AIza[A-Za-z0-9_-]{35}'
    '[0-9a-fA-F]{32,}'
    'password[[:space:]]*[:=][[:space:]]*[^[:space:]]+'
)

found=0

# redact: keep the first 4 characters of a match, replace the rest with a fixed
# mask so the report shows where the hit landed without leaking the secret.
redact() {
    sed -E 's/([A-Za-z0-9_-]{4})[A-Za-z0-9_:=-]+/\1********/g'
}

for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "skip: $file not present"
        continue
    fi
    for pattern in "${PATTERNS[@]}"; do
        # grep -n for line numbers; tolerate no-match (exit 1) without aborting.
        while IFS= read -r hit; do
            [[ -z "$hit" ]] && continue
            redacted=$(printf '%s' "$hit" | redact)
            echo "SECRET: $file: $redacted (pattern: $pattern)"
            found=1
        done < <(grep -nE "$pattern" "$file" 2>/dev/null || true)
    done
done

if [[ "$found" -ne 0 ]]; then
    echo "FAIL: credential patterns detected on the agent config surface." >&2
    exit 1
fi

echo "PASS: no credential patterns found in steering files or settings.json."
exit 0
