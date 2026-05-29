#!/usr/bin/env bash
# check-steering-parity.sh -- CLAUDE-012 verifier.
#
# Verifies the core directive block carries identical content across the
# steering files that exist. The block is delimited by sentinel comments:
#
#     <!-- core-directives:v1 -->
#     ...directives...
#     <!-- /core-directives -->
#
# Architecture is Option B (three files, parity check). Per the work package,
# GEMINI.md is OPTIONAL: a steering file that is absent on disk is skipped, and
# parity is enforced only across the files that are present. A file that exists
# but lacks the sentinel block is a failure (drift, not optionality).
#
# Exit 0 when every present file shares a byte-identical normalized block
# (and at least one block exists); exit 1 on a missing block or a divergence,
# printing a unified diff of the offending pair.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

FILES=(
    "AGENTS.md"
    "CLAUDE.md"
    "GEMINI.md"
)

OPEN_SENTINEL='<!-- core-directives:v1 -->'
CLOSE_SENTINEL='<!-- /core-directives -->'

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# extract_block FILE OUT
# Writes the normalized directive block of FILE to OUT. Normalization trims
# leading and trailing whitespace from each line and drops blank lines so that
# incidental spacing differences do not register as divergence. Returns 1 if
# the file lacks a complete sentinel block.
extract_block() {
    local file="$1" out="$2"
    awk -v opentag="$OPEN_SENTINEL" -v closetag="$CLOSE_SENTINEL" '
        index($0, opentag)  { capture = 1; next }
        index($0, closetag) { capture = 0; found = 1; next }
        capture {
            line = $0
            gsub(/^[[:space:]]+/, "", line)
            gsub(/[[:space:]]+$/, "", line)
            if (line != "") print line
        }
        END { exit (found && capture == 0) ? 0 : 1 }
    ' "$file" > "$out"
}

present_files=()
missing_block=()

for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "skip: $file not present (optional steering file)"
        continue
    fi
    if extract_block "$file" "$WORKDIR/$(basename "$file").block"; then
        present_files+=("$file")
    else
        echo "MISSING BLOCK: $file exists but has no complete $OPEN_SENTINEL block."
        missing_block+=("$file")
    fi
done

if [[ "${#missing_block[@]}" -ne 0 ]]; then
    echo "FAIL: steering files present without a core directive block: ${missing_block[*]}" >&2
    exit 1
fi

if [[ "${#present_files[@]}" -eq 0 ]]; then
    echo "FAIL: no steering file with a core directive block found." >&2
    exit 1
fi

# Compare every present block against the first as the reference.
reference="${present_files[0]}"
ref_block="$WORKDIR/$(basename "$reference").block"
divergent=0

for file in "${present_files[@]:1}"; do
    cur_block="$WORKDIR/$(basename "$file").block"
    if ! diff -u "$ref_block" "$cur_block" \
        --label "$reference (core-directives)" \
        --label "$file (core-directives)"; then
        divergent=1
    fi
done

if [[ "$divergent" -ne 0 ]]; then
    echo "FAIL: core directive blocks diverge across steering files." >&2
    exit 1
fi

echo "PASS: core directive blocks match across ${present_files[*]}."
exit 0
