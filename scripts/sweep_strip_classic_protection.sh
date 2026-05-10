#!/usr/bin/env bash
set -euo pipefail

CATALOG=docs/reference/github-repos.json
BACKUP_DIR=backups/branch-protection-$(date +%Y-%m-%d)
LOG=backups/sweep-$(date +%Y-%m-%d).log
# Canaries already migrated; excluded by migrationPhase==dual filter, listed here as safety net
CANARIES="ByronWilliamsCPA/.claude williaby/.claude"

mkdir -p backups "$BACKUP_DIR"
: > "$LOG"

while IFS= read -r repo; do
  org=${repo%%/*}; name=${repo##*/}
  case " $CANARIES " in *" $repo "*) echo "skip canary $repo" | tee -a "$LOG"; continue;; esac

  branch=$(jq -r --arg r "$repo" \
    '.repos[] | select(.org+"/"+.name==$r) | .defaultBranch' "$CATALOG")
  if [[ -z "$branch" || "$branch" == "null" ]]; then
    echo "ERROR $repo: no defaultBranch in catalog" | tee -a "$LOG"; exit 1
  fi

  test -s "$BACKUP_DIR/${org}__${name}.json" || { echo "MISSING BACKUP $repo" | tee -a "$LOG"; exit 1; }

  echo "Stripping $repo:$branch" | tee -a "$LOG"
  delete_err=""
  if ! delete_err=$(gh api -X DELETE "repos/$repo/branches/$branch/protection" 2>&1); then
    if echo "$delete_err" | grep -qi "404\|Not Found"; then
      echo "NOTE $repo: no classic protection to delete" | tee -a "$LOG"
    else
      echo "ERROR $repo: DELETE failed: $delete_err" | tee -a "$LOG"; exit 1
    fi
  fi

  # Verify classic protection is gone (expect 404 from the API)
  protection_err=""
  if protection_err=$(gh api "repos/$repo/branches/$branch/protection" 2>&1); then
    echo "DRIFT $repo: classic protection still active" | tee -a "$LOG"; exit 1
  elif ! echo "$protection_err" | grep -qi "404\|Not Found"; then
    echo "ERROR $repo: network failure during drift check: $protection_err" | tee -a "$LOG"; exit 1
  fi

  # Verify org ruleset coverage is active (at least one rule type present)
  ruleset_json=""
  if ! ruleset_json=$(gh api "repos/$repo/rules/branches/$branch" 2>>"$LOG"); then
    echo "ERROR $repo: failed to fetch ruleset rules" | tee -a "$LOG"; exit 1
  fi
  ruleset_count=$(echo "$ruleset_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>>"$LOG" || echo -1)
  if [[ "$ruleset_count" -le 0 ]]; then
    echo "DRIFT $repo: no ruleset rules active (count=$ruleset_count)" | tee -a "$LOG"; exit 1
  fi

  echo "OK $repo" | tee -a "$LOG"
done < <(jq -r '.repos[] | select(.migrationPhase == "dual") | .org+"/"+.name' "$CATALOG")

ok_count=$(grep -c "^OK" "$LOG" || true)
echo "SWEEP COMPLETE: $ok_count repos stripped"
