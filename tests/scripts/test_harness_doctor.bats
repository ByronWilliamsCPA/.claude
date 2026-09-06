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

# The hooks.json vs settings.json drift probe. It exists because three hooks
# were committed to hooks.json and never propagated to the live settings,
# staying inert for 32 days. A detector that cannot be shown to fire is worth
# nothing, so both directions are asserted.

# Builds a fake HOME whose settings.json contains only the hook commands
# passed as arguments, and echoes the directory.
_fake_home() {
    local home
    home=$(mktemp -d)
    mkdir -p "$home/.claude/agents" "$home/.claude/skills"
    local cmds='[]'
    if [ "$#" -gt 0 ]; then
        cmds=$(printf '%s\n' "$@" | jq -R . | jq -sc .)
    fi
    jq -n --argjson cmds "$cmds" \
        '{hooks: {SessionStart: [{matcher: "startup",
          hooks: ($cmds | map({type: "command", command: .}))}]}}' \
        > "$home/.claude/settings.json"
    printf '%s' "$home"
}

# Every command hooks.json declares, so a "fully propagated" settings.json can
# be synthesised without hardcoding a list that would go stale.
_declared_commands() {
    jq -r '[(.hooks // .) | to_entries[] | .value[]? | .hooks[]? | .command]
           | unique[]' "$BATS_TEST_DIRNAME/../../hooks.json"
}

@test "drift probe reports hooks declared in hooks.json but absent from settings" {
    local home
    home=$(_fake_home)
    run env HOME="$home" bash "$SCRIPT"
    rm -rf "$home"
    [ "$status" -eq 0 ]
    [[ "$output" == *"not live in settings.json"* ]]
    [[ "$output" == *"run setup.sh"* ]]
}

@test "drift probe stays silent when every declared hook is live" {
    local home
    mapfile -t cmds < <(_declared_commands)
    home=$(_fake_home "${cmds[@]}")
    run env HOME="$home" bash "$SCRIPT"
    rm -rf "$home"
    [ "$status" -eq 0 ]
    [[ "$output" != *"not live in settings.json"* ]]
}

@test "drift probe ignores live-only hooks from foreign installers" {
    local home
    mapfile -t cmds < <(_declared_commands)
    cmds+=("bash /opt/some-plugin/hooks/foreign.sh")
    home=$(_fake_home "${cmds[@]}")
    run env HOME="$home" bash "$SCRIPT"
    rm -rf "$home"
    [ "$status" -eq 0 ]
    [[ "$output" != *"not live in settings.json"* ]]
}

@test "drift probe degrades quietly when settings.json is unreadable" {
    local home
    home=$(mktemp -d)
    mkdir -p "$home/.claude/agents" "$home/.claude/skills"
    run env HOME="$home" bash "$SCRIPT"
    rm -rf "$home"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[harness-doctor] live:"* ]]
}
