#!/usr/bin/env bats
# Tests for setup.sh merge_hooks() and the doctor() hooks drift check.
#
# Guards the Critical finding from the 2026-07-01 senior review: the old
# merge (`.hooks = $h[0]`) wholesale-replaced settings.json's .hooks key,
# silently deleting hooks written by other installers (codebase-memory-mcp
# SessionStart entries, direct edits). These tests pin the union-merge
# semantics: repo hooks.json entries are authoritative for their own
# (matcher, command) identities; everything else in settings.json survives.

load 'helpers/test_helper'

SETUP_SH="${BATS_TEST_DIRNAME}/../setup.sh"
HOOKS_JSON="${BATS_TEST_DIRNAME}/../hooks.json"

setup() {
    export TEST_TMP_DIR="${BATS_TEST_TMPDIR:-$(mktemp -d)}"
    export HOME="$TEST_TMP_DIR"
    mkdir -p "$HOME/.claude"
    # Neutralize side-effectful steps: git (submodule init) and claude
    # (plugin list/update). jq stays real; the merge under test needs it.
    mock_command "git" 0 "git version 2.40.0"
    mock_command "claude" 0 ""
}

teardown() {
    teardown_test_environment
}

seed_foreign_settings() {
    # Simulates the live drift that triggered the incident: foreign
    # installer entries (cbm SessionStart x2, Grep|Glob gate) plus an
    # unrelated top-level key that the merge must not disturb.
    cat > "$HOME/.claude/settings.json" << 'EOF'
{
  "model": "opus",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Grep|Glob",
        "hooks": [
          {"type": "command", "command": "~/.claude/hooks/cbm-code-discovery-gate", "timeout": 5}
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{"type": "command", "command": "~/.claude/hooks/cbm-session-reminder"}]
      },
      {
        "matcher": "resume",
        "hooks": [{"type": "command", "command": "~/.claude/hooks/cbm-session-reminder"}]
      }
    ]
  }
}
EOF
}

# =============================================================================
# merge_hooks: preservation of foreign entries
# =============================================================================

@test "merge preserves foreign installer entries and adds repo hooks" {
    seed_foreign_settings
    run bash "$SETUP_SH"
    assert_success

    local settings="$HOME/.claude/settings.json"

    # Foreign entries survive
    run jq -r '[.hooks.SessionStart[].matcher] | sort | join(",")' "$settings"
    assert_output_contains "resume,startup"
    run jq -r '[.hooks.PreToolUse[] | select(.matcher == "Grep|Glob") | .hooks[].command] | length' "$settings"
    assert_output_contains "1"

    # Repo hooks arrived
    run jq -r '[.hooks.PreToolUse[] | .hooks[].command] | map(select(contains("bash-pre-hook.sh"))) | length' "$settings"
    assert_output_contains "1"
    run jq -r '[.hooks.Stop[] | .hooks[].command] | map(select(contains("session-length-warning.sh"))) | length' "$settings"
    assert_output_contains "1"

    # Unrelated top-level keys untouched
    run jq -r '.model' "$settings"
    assert_output_contains "opus"
}

@test "merge is a union: every hooks.json triple is present after merge" {
    seed_foreign_settings
    run bash "$SETUP_SH"
    assert_success

    run jq -n \
        --slurpfile repo "$HOOKS_JSON" \
        --slurpfile live "$HOME/.claude/settings.json" '
        def triples($obj): [ ($obj // {}) | to_entries[] as $e
            | $e.value[]? as $g | ($g.matcher // "") as $m
            | $g.hooks[]? | [$e.key, $m, .command] ];
        (triples($repo[0]) - triples($live[0].hooks)) | length'
    assert_output_contains "0"
}

# =============================================================================
# merge_hooks: repo is authoritative for its own entries
# =============================================================================

@test "repo hooks.json wins on shared (matcher, command) identity" {
    # Seed a repo-known hook with drifted timeout/statusMessage; the merge
    # must emit the repo version and not duplicate the entry.
    cat > "$HOME/.claude/settings.json" << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "bash $HOME/.claude/scripts/bash-pre-hook.sh", "timeout": 99, "statusMessage": "STALE"}
        ]
      }
    ]
  }
}
EOF
    run bash "$SETUP_SH"
    assert_success

    run jq -r '[.hooks.PreToolUse[] | .hooks[] | select(.command | contains("bash-pre-hook.sh"))] | length' \
        "$HOME/.claude/settings.json"
    assert_output_contains "1"
    run jq -r '[.hooks.PreToolUse[] | .hooks[] | select(.command | contains("bash-pre-hook.sh"))][0].timeout' \
        "$HOME/.claude/settings.json"
    assert_output_contains "10"
}

@test "mixed group splits: foreign hook survives when it shares a group with a repo hook" {
    # Reproduces the live Stop-event shape: one matcher-less group holding
    # both a foreign hook and a repo-known hook. The repo-known hook must
    # dedupe; the foreign one must survive.
    local repo_stop_cmd
    repo_stop_cmd="$(jq -r '.Stop[0].hooks[-1].command' "$HOOKS_JSON")"
    jq -n --arg cmd "$repo_stop_cmd" '{
        hooks: { Stop: [ { hooks: [
            {type: "command", command: "echo foreign-stop-hook"},
            {type: "command", command: $cmd, timeout: 10}
        ] } ] }
    }' > "$HOME/.claude/settings.json"

    run bash "$SETUP_SH"
    assert_success

    run jq -r --arg cmd "$repo_stop_cmd" \
        '[.hooks.Stop[] | .hooks[] | select(.command == $cmd)] | length' \
        "$HOME/.claude/settings.json"
    assert_output_contains "1"
    run jq -r '[.hooks.Stop[] | .hooks[] | select(.command == "echo foreign-stop-hook")] | length' \
        "$HOME/.claude/settings.json"
    assert_output_contains "1"
}

# =============================================================================
# merge_hooks: idempotency and creation
# =============================================================================

@test "second run is idempotent and reports hooks already current" {
    seed_foreign_settings
    run bash "$SETUP_SH"
    assert_success

    local before
    before="$(sha256sum "$HOME/.claude/settings.json" | cut -d' ' -f1)"

    run bash "$SETUP_SH"
    assert_success
    assert_output_contains "settings.json hooks already current"

    local after
    after="$(sha256sum "$HOME/.claude/settings.json" | cut -d' ' -f1)"
    [[ "$before" == "$after" ]] || {
        echo "settings.json changed on second run: $before != $after"
        return 1
    }
}

@test "fresh settings.json is created with hooks.json content verbatim" {
    [[ ! -f "$HOME/.claude/settings.json" ]]
    run bash "$SETUP_SH"
    assert_success

    run jq -n \
        --slurpfile repo "$HOOKS_JSON" \
        --slurpfile live "$HOME/.claude/settings.json" \
        '$repo[0] == $live[0].hooks'
    assert_output_contains "true"
}

# =============================================================================
# doctor: bidirectional drift reporting
# =============================================================================

@test "doctor reports repo hooks missing from live settings" {
    # Settings with the repo's Bash guard deleted
    bash "$SETUP_SH" > /dev/null
    jq '.hooks.PreToolUse |= map(select(.matcher != "Bash"))' \
        "$HOME/.claude/settings.json" > "$HOME/.claude/settings.json.tmp"
    mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"

    run bash "$SETUP_SH" --doctor
    assert_output_contains "hook in hooks.json but not live"
    assert_output_contains "bash-pre-hook.sh"
}

@test "doctor flags live-only repo-script hooks as unbackported" {
    bash "$SETUP_SH" > /dev/null
    jq '.hooks.PostToolUse += [{matcher: "Write", hooks: [
            {type: "command", command: "bash $HOME/.claude/scripts/not-in-hooks-json.sh"}
        ]}]' \
        "$HOME/.claude/settings.json" > "$HOME/.claude/settings.json.tmp"
    mv "$HOME/.claude/settings.json.tmp" "$HOME/.claude/settings.json"

    run bash "$SETUP_SH" --doctor
    assert_output_contains "backport to hooks.json"
    assert_output_contains "not-in-hooks-json.sh"
}

@test "doctor treats foreign live-only hooks as informational" {
    seed_foreign_settings
    bash "$SETUP_SH" > /dev/null

    run bash "$SETUP_SH" --doctor
    assert_output_contains "live-only hook (foreign installer, preserved by merge)"
    assert_output_contains "cbm-session-reminder"
    assert_output_not_contains "hook in hooks.json but not live"
}

@test "doctor reports hooks in sync when no drift exists" {
    bash "$SETUP_SH" > /dev/null

    run bash "$SETUP_SH" --doctor
    assert_output_contains "hooks in sync with hooks.json"
}

# =============================================================================
# dry run
# =============================================================================

@test "dry run does not modify settings.json" {
    seed_foreign_settings
    local before
    before="$(sha256sum "$HOME/.claude/settings.json" | cut -d' ' -f1)"

    run bash "$SETUP_SH" --dry-run
    assert_success
    assert_output_contains "union-merge hooks.json"

    local after
    after="$(sha256sum "$HOME/.claude/settings.json" | cut -d' ' -f1)"
    [[ "$before" == "$after" ]]
}
