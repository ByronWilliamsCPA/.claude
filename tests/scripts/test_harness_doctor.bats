#!/usr/bin/env bats
setup() { SCRIPT="$BATS_TEST_DIRNAME/../../scripts/harness-doctor.sh"; }

@test "doctor always exits zero" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "doctor prints a live inventory line" {
    run bash "$SCRIPT"
    [[ "$output" == *"[harness-doctor] live:"* ]]
}
