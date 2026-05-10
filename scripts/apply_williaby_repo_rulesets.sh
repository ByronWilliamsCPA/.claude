#!/usr/bin/env bash
# Apply per-repo rulesets to every non-exempt williaby repo.
#
# Iterates the catalog, picks the universal or python-tier template based on
# repositoryType, and shells out to setup_repo_rulesets.py for each repo.
#
# Environment variables:
#   CATALOG      Path to the repo catalog JSON. Default: docs/reference/github-repos.json
#   ENFORCEMENT  Ruleset enforcement mode (active, evaluate, disabled). Default: evaluate
#   DRY_RUN      If "true", pass --dry-run to setup_repo_rulesets.py. Default: false
#   LOG          Path to the run log. Default: backups/williaby-rulesets-YYYY-MM-DD.log
#
# Exit codes:
#   0   all repos applied (or dry-run completed) successfully
#   1   one or more repos failed; remaining repos still attempted
#   2   missing dependency, invalid input, or precondition failure
#
# Idempotency: setup_repo_rulesets.py PUTs an existing ruleset by name, so
# re-running after a transient failure converges without manual cleanup.

set -euo pipefail

# Resolve repo root from this script's location so the sweep works regardless
# of the caller's current working directory (or from a symlinked install).
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

CATALOG="${CATALOG:-docs/reference/github-repos.json}"
ENFORCEMENT="${ENFORCEMENT:-evaluate}"
DRY_RUN="${DRY_RUN:-false}"
LOG="${LOG:-backups/williaby-rulesets-$(date +%Y-%m-%d).log}"

# Validate ENFORCEMENT before any work so a typo fails fast with a clear message
# instead of producing a confusing downstream argparse error.
case "$ENFORCEMENT" in
  active|evaluate|disabled) ;;
  *)
    echo "ERROR: invalid ENFORCEMENT='$ENFORCEMENT' (expected: active, evaluate, or disabled)" >&2
    exit 2
    ;;
esac

# Preconditions
for cmd in jq uv; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' not found on PATH" >&2
    exit 2
  fi
done

if [[ ! -f "$CATALOG" ]]; then
  echo "ERROR: catalog not found at $CATALOG" >&2
  exit 2
fi

mkdir -p "$(dirname "$LOG")"
: > "$LOG"

PYTHON_TYPES=("python-package" "python-app" "python-script")
TEMPLATE_DIR="docs/reference/repo-rulesets"
UNIVERSAL_BODY="$TEMPLATE_DIR/_williaby-template-universal.json"
PYTHON_BODY="$TEMPLATE_DIR/_williaby-template-python.json"

for body in "$UNIVERSAL_BODY" "$PYTHON_BODY"; do
  if [[ ! -f "$body" ]]; then
    echo "ERROR: template body missing: $body" >&2
    exit 2
  fi
done

is_python_type() {
  local candidate="$1"
  for t in "${PYTHON_TYPES[@]}"; do
    [[ "$candidate" == "$t" ]] && return 0
  done
  return 1
}

ok_count=0
fail_count=0
failed_repos=()

while IFS= read -r repo; do
  repo_type=$(jq -r --arg r "$repo" \
    '.repos[] | select(.org=="williaby" and .name==$r) | .repositoryType' "$CATALOG")

  # jq emits the literal string "null" when the field is missing. Warn so a
  # silent universal-tier fallback does not hide a catalog data gap.
  if [[ -z "$repo_type" || "$repo_type" == "null" ]]; then
    echo "WARN williaby/$repo: repositoryType missing in catalog; routing to universal tier" \
      | tee -a "$LOG" >&2
    repo_type=""
  fi

  if is_python_type "$repo_type"; then
    body="$PYTHON_BODY"
    tier="python"
  else
    body="$UNIVERSAL_BODY"
    tier="universal"
  fi

  echo "Applying $tier ruleset to williaby/$repo (enforcement=$ENFORCEMENT)" | tee -a "$LOG"
  args=(--repo "williaby/$repo" --body "$body" --enforcement "$ENFORCEMENT")
  if [[ "$DRY_RUN" == "true" ]]; then
    args+=(--dry-run)
  fi

  # PYTHONPATH=. is required because setup_repo_rulesets.py imports
  # scripts.setup_org_rulesets at module scope and scripts/ is not a package.
  # Use `set +e` around the subprocess so a single failure does not abort
  # the sweep; record the failure and continue to the next repo.
  set +e
  PYTHONPATH=. uv run python scripts/setup_repo_rulesets.py "${args[@]}" >>"$LOG" 2>&1
  rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "OK williaby/$repo" | tee -a "$LOG"
    ok_count=$((ok_count + 1))
  else
    fail_count=$((fail_count + 1))
    failed_repos+=("williaby/$repo (exit $rc)")
    echo "FAIL williaby/$repo (exit $rc)" | tee -a "$LOG" >&2
  fi
done < <(jq -r '.repos[] | select(.org == "williaby" and (.branchProtectionExempt != true)) | .name' "$CATALOG")

echo "DONE: applied=$ok_count failed=$fail_count log=$LOG" | tee -a "$LOG"

if [[ "$fail_count" -gt 0 ]]; then
  {
    echo "Failed repos:"
    for entry in "${failed_repos[@]}"; do
      echo "  $entry"
    done
  } | tee -a "$LOG" >&2
  exit 1
fi
