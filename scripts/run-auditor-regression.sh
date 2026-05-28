#!/usr/bin/env bash
# Run the compliance auditor against the regression fixture corpus and assert
# that each defect fixture FAILS its target check while the control PASSES it.
#
# This covers the checks the local auditor can evaluate by file inspection
# (no GitHub API calls): FOUND-001, FOUND-002, CI-028, CI-043, CI-061, CI-018.
# Checks that require the full LLM auditor or live API state are out of scope
# here; run those manually with `/repo-audit <fixture-path>` and compare the
# findings by hand.
#
# Usage:  bash scripts/run-auditor-regression.sh
# Exit:   0 = every assertion held, 1 = at least one regression.
set -euo pipefail

FIXTURE_ROOT="data/test_fixtures/compliance_auditor"
SCRIPT="scripts/check-repo-compliance.py"
FAILURES=0

# Assert that the auditor reports `expect` (pass|fail) for `check_id` on
# `fixture`. A non-zero auditor exit is expected for a FAIL result, so the
# capture is guarded; a true crash yields no JSON status and is flagged.
run_check() {
  local fixture="$1" check_id="$2" expect="$3"
  local result status
  result=$(uv run python "$SCRIPT" \
    --local-path "$FIXTURE_ROOT/$fixture" \
    --check-id "$check_id" \
    --output json) || true
  status=$(printf '%s' "$result" \
    | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" \
    2>/dev/null || echo "error")
  if [[ "$status" != "$expect" ]]; then
    echo "REGRESSION: $check_id on $fixture expected $expect, got $status"
    echo "  raw: $result"
    FAILURES=$((FAILURES + 1))
  else
    echo "OK: $check_id on $fixture -> $status"
  fi
}

run_check control          FOUND-001 pass
run_check defect_FOUND-001 FOUND-001 fail
run_check control          FOUND-002 pass
run_check defect_FOUND-002 FOUND-002 fail
run_check control          CI-028    pass
run_check defect_CI-028    CI-028    fail
run_check control          CI-043    pass
run_check defect_CI-043    CI-043    fail
run_check control          CI-061    pass
run_check defect_CI-061    CI-061    fail
run_check control          CI-018    pass
run_check defect_CI-018    CI-018    fail

if [[ $FAILURES -gt 0 ]]; then
  echo ""
  echo "AUDITOR REGRESSION: $FAILURES assertion(s) failed."
  exit 1
fi
echo ""
echo "All auditor regression assertions passed."
