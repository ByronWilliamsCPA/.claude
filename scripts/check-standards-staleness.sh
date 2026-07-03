#!/usr/bin/env bash
# check-standards-staleness.sh -- flag standards whose last-updated date
# is older than the review window (default 180 days; ai-detection-landscape
# declares quarterly, so 90). Advisory; exit 0 always when run as a hook,
# exit 1 with findings when run with --strict (for CI or cron).
set -uo pipefail

STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1
NOW=$(date +%s)
FINDINGS=()

check() {  # $1 file, $2 max-age-days
    local file="$1" max_days="$2" date_str age_days
    date_str=$(grep -oE '(Last Updated|Snapshot)[:* ]+[0-9]{4}-[0-9]{2}-[0-9]{2}' "$file" \
        | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -n1)
    [[ -z "$date_str" ]] && return 0
    age_days=$(( (NOW - $(date -d "$date_str" +%s)) / 86400 ))
    if (( age_days > max_days )); then
        FINDINGS+=("${file}: ${age_days}d old (max ${max_days})")
    fi
}

for f in .claude/standards/*.md; do
    case "$f" in
        *ai-detection-landscape*) check "$f" 90 ;;
        *) check "$f" 180 ;;
    esac
done

if [[ ${#FINDINGS[@]} -gt 0 ]]; then
    printf '[staleness] %s\n' "${FINDINGS[@]}" >&2
    (( STRICT )) && exit 1
fi
exit 0
