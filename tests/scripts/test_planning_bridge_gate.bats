#!/usr/bin/env bats
# =============================================================================
# Encodes the bridge-mode blocking contract for scripts/planning-bridge-gate.sh.
#
# Confirmed via `grep -n 'jq -r' scripts/planning-bridge-gate.sh`:
#   SKILL=$(echo "$CONTEXT" | jq -r '.tool_input.skill // empty' ...)
# so the payload's skill field is `.tool_input.skill`, matching the brief's
# assumption; no field-name adaptation was needed.
#
# The gate resolves its project directory from $PWD (not an env var), so
# setup() cds into a scratch directory before each test, matching the gate's
# own PROJECT_DIR="${PWD}" assumption.
#
# Mechanics note: the gate reads its JSON envelope from stdin. Piping stdin
# directly into bats' `run` (`payload ... | run bash "$SCRIPT"`) does not
# work under bats-core: `run` expects a single command, not the tail of a
# pipeline. Instead, following the working pattern in
# test_tdd_enforcement_hook.bats, `run` wraps a `bash -c '...'` subshell that
# performs the pipe internally, so `run` captures the subshell's exit status,
# which is the gate's own exit status.
# =============================================================================

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../../scripts/planning-bridge-gate.sh"
    WORK="$(mktemp -d)"
    cd "$WORK"
}

teardown() { cd /; rm -rf "$WORK"; }

# Runs the gate with a Skill-tool JSON envelope for the given skill name.
# Populates $status (bats-captured exit code) and $output.
run_gate() {
    local skill="$1"
    run bash -c 'printf "%s" "$1" | bash "$2"' _ \
        "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"${skill}\"}}" \
        "$SCRIPT"
}

@test "non-planning skill passes" {
    run_gate "quality"
    [ "$status" -eq 0 ]
}

@test "writing-plans with no spec passes" {
    run_gate "writing-plans"
    [ "$status" -eq 0 ]
}

@test "writing-plans with spec but no planning docs blocks" {
    mkdir -p docs/superpowers/specs
    echo spec > docs/superpowers/specs/2026-01-01-x-design.md
    run_gate "writing-plans"
    [ "$status" -eq 2 ]
}

@test "writing-plans with spec and roadmap passes" {
    mkdir -p docs/superpowers/specs docs/planning
    echo spec > docs/superpowers/specs/2026-01-01-x-design.md
    echo roadmap > docs/planning/roadmap.md
    run_gate "writing-plans"
    [ "$status" -eq 0 ]
}
