#!/usr/bin/env bats
# =============================================================================
# Encodes the blocking contract for scripts/sensitive-file-guard.sh.
#
# Copied verbatim (per docs/audits/harness-architecture-review-2026-07-02.md
# section 10.3) except for the fifth case, added for the Task 25 secrets
# baseline tie-in. This guard is believed correct as shipped; a failure here
# is a real regression in the hook, not a test defect.
#
# The hook reads its target path from the CLAUDE_FILE_PATH environment
# variable (not stdin), so no piping helper is needed: the env-var-prefixed
# `run` invocation exports CLAUDE_FILE_PATH for that single command only.
# =============================================================================

setup() { SCRIPT="$BATS_TEST_DIRNAME/../../scripts/sensitive-file-guard.sh"; }

@test "blocks .env write" {
  CLAUDE_FILE_PATH="/repo/.env" run bash "$SCRIPT"
  [ "$status" -eq 2 ]
}

@test "blocks nested aws credentials" {
  CLAUDE_FILE_PATH="/home/u/.aws/credentials" run bash "$SCRIPT"
  [ "$status" -eq 2 ]
}

@test "allows ssh public key" {
  CLAUDE_FILE_PATH="/home/u/.ssh/id_ed25519.pub" run bash "$SCRIPT"
  [ "$status" -eq 0 ]
}

@test "allows ordinary source file" {
  CLAUDE_FILE_PATH="/repo/src/app.py" run bash "$SCRIPT"
  [ "$status" -eq 0 ]
}

@test "blocks secrets baseline overwrite" {
  CLAUDE_FILE_PATH="/repo/.secrets.baseline" run bash "$SCRIPT"
  [ "$status" -eq 2 ]
}
