#!/usr/bin/env bash
set -euo pipefail

CATALOG=docs/reference/github-repos.json
BACKUP_DIR=backups/branch-protection-2026-05-09
LOG=backups/sweep-$(date +%Y-%m-%d).log
# Canaries already migrated; excluded by migrationPhase==dual filter, listed here as safety net
CANARIES="ByronWilliamsCPA/.claude williaby/.claude"

> "$LOG"

while IFS= read -r repo; do
  org=${repo%%/*}; name=${repo##*/}
  case " $CANARIES " in *" $repo "*) echo "skip canary $repo" | tee -a "$LOG"; continue;; esac

  branch=$(jq -r --arg r "$repo" \
    '.repos[] | select(.org+"/"+.name==$r) | .defaultBranch' "$CATALOG")

  test -s "$BACKUP_DIR/${org}__${name}.json" || { echo "MISSING BACKUP $repo" | tee -a "$LOG"; exit 1; }

  echo "Stripping $repo:$branch" | tee -a "$LOG"
  gh api -X DELETE "repos/$repo/branches/$branch/protection" 2>>"$LOG" || true

  # Verify classic protection is gone (expect 404)
  if gh api "repos/$repo/branches/$branch/protection" >>"$LOG" 2>&1; then
    echo "DRIFT $repo: classic protection still active" | tee -a "$LOG"; exit 1
  fi

  # Verify org ruleset coverage is active (at least one rule type present)
  ruleset_count=$(gh api "repos/$repo/rules/branches/$branch" 2>/dev/null \
    | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
  [ "$ruleset_count" -gt 0 ] || { echo "DRIFT $repo: no ruleset rules active" | tee -a "$LOG"; exit 1; }

  echo "OK $repo" | tee -a "$LOG"
done < <(jq -r '.repos[] | select(.migrationPhase == "dual") | .org+"/"+.name' "$CATALOG")

echo "SWEEP COMPLETE: $(grep -c "^OK" "$LOG") repos stripped"
