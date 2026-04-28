---
schema_type: planning
title: "Four New Claude Code Hooks"
status: draft
owner: core-maintainer
purpose: "Add shellcheck, frontmatter validator, force-push guard, and WSL2 notification hooks to ~/.claude/settings.json."
component: Development-Tools
source: "docs/superpowers/specs/"
tags:
  - automation
  - tooling
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire four advisory/guard hooks into the global Claude Code settings so shellcheck, frontmatter validation, force-push blocking, and long-Bash notifications run automatically.

**Architecture:** Hook 1 (shellcheck) is an inline command appended to the existing PostToolUse `Edit|Write` array - no new file. Hooks 2-4 are standalone bash scripts in `scripts/` (symlinked from `~/.claude/scripts/`) each following the stdin-JSON pattern established by `py310-compat-check.sh` and `planning-bridge-gate.sh`. Hooks 3 and 4 share a single PreToolUse Bash script (`bash-pre-hook.sh`) that handles force-push detection and records a start timestamp; a separate PostToolUse script (`bash-notify.sh`) reads that timestamp and fires the notification.

**Tech Stack:** Bash, shellcheck 0.11.0, python3 `re` module, jq, powershell.exe (WSL2 toast), `~/.claude/settings.json`

---

## File Structure

| File | Action | Responsibility |
| ---- | ------ | -------------- |
| `~/.claude/settings.json` | Modify | Wire all four hooks (4 separate edits) |
| `dev/.claude/scripts/validate-frontmatter.sh` | Create | PostToolUse: check SKILL.md / agent .md frontmatter |
| `dev/.claude/scripts/bash-pre-hook.sh` | Create | PreToolUse Bash: force-push guard + write /tmp start timestamp |
| `dev/.claude/scripts/bash-notify.sh` | Create | PostToolUse Bash: read timestamp, notify if duration > 30s |

Note: `~/.claude/scripts/` is a symlink to `dev/.claude/scripts/`, so scripts written to
`dev/.claude/scripts/` are immediately available at `$HOME/.claude/scripts/`.

---

### Task 1: Shellcheck inline hook

**Files:**
- Modify: `~/.claude/settings.json` (PostToolUse `(Edit|Write)` hooks array, add one entry)

No new script. Shellcheck is advisory (`|| true`) - Claude sees the output but the edit is never blocked.

- [ ] **Step 1: Verify shellcheck is installed and the .shellcheckrc is respected**

```bash
echo 'UNASSIGNED_VAR' > /tmp/test_hook.sh
shellcheck --severity=warning /tmp/test_hook.sh 2>&1
rm /tmp/test_hook.sh
```

Expected output: a SC2148 or SC2034 warning proving shellcheck runs. If no output, check `/home/byron/dev/.claude/.shellcheckrc` severity setting.

- [ ] **Step 2: Add the shellcheck entry to settings.json**

Open `/home/byron/.claude/settings.json`. Locate the PostToolUse `(Edit|Write)` hooks array (currently one entry: py310-compat-check.sh). Add a second entry to that same array:

```json
{
  "PostToolUse": [
    {
      "matcher": "(Edit|Write)",
      "hooks": [
        {
          "type": "command",
          "command": "bash $HOME/.claude/scripts/py310-compat-check.sh",
          "timeout": 30,
          "statusMessage": "Checking Python 3.10/3.14 compatibility..."
        },
        {
          "type": "command",
          "command": "if [[ \"$CLAUDE_FILE_PATH\" == *.sh ]]; then shellcheck \"$CLAUDE_FILE_PATH\" 2>&1 || true; fi",
          "timeout": 15,
          "statusMessage": "Running shellcheck..."
        }
      ]
    }
  ]
}
```

- [ ] **Step 3: Smoke-test by editing a shell script with a known issue**

Open `/home/byron/dev/.claude/scripts/validate-frontmatter.sh` (which does not exist yet - create it empty first):

```bash
echo '#!/usr/bin/env bash' > /home/byron/dev/.claude/scripts/validate-frontmatter.sh
echo 'UNUSED_VAR="hello"' >> /home/byron/dev/.claude/scripts/validate-frontmatter.sh
```

Then trigger the hook by using the Edit tool on that file. Expected: Claude receives a shellcheck SC2034 warning about `UNUSED_VAR`.

- [ ] **Step 4: Commit settings.json change**

```bash
cd /home/byron/dev/.claude
git add .claude/settings.json
git commit -m "feat: add shellcheck PostToolUse hook for .sh edits"
```

---

### Task 2: Frontmatter validator script and hook

**Files:**
- Create: `dev/.claude/scripts/validate-frontmatter.sh`
- Modify: `~/.claude/settings.json` (add third entry to PostToolUse `(Edit|Write)` array)

The script reads the edited file path from stdin JSON. If the path matches `*/SKILL.md` or `*/agents/*.md`, it checks that the YAML frontmatter block contains `name:` and `description:` fields. Always exits 0 (advisory).

- [ ] **Step 1: Write the test harness**

```bash
cat > /tmp/test_validate_frontmatter.sh << 'TESTS'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$HOME/.claude/scripts/validate-frontmatter.sh"
PASS=0
FAIL=0

check() {
    local name="$1"
    local expected_pattern="$2"   # grep regex; empty string = expect silent output
    local output="$3"
    local exit_code="$4"

    if [[ $exit_code -ne 0 ]]; then
        echo "FAIL [$name]: script exited $exit_code (must always exit 0)"
        ((FAIL++)); return
    fi

    if [[ -z "$expected_pattern" ]]; then
        if [[ -z "$output" ]]; then
            echo "PASS [$name]"
            ((PASS++))
        else
            echo "FAIL [$name]: expected silence, got: $output"
            ((FAIL++))
        fi
    else
        if echo "$output" | grep -qE "$expected_pattern"; then
            echo "PASS [$name]"
            ((PASS++))
        else
            echo "FAIL [$name]: expected pattern '$expected_pattern', got: $output"
            ((FAIL++))
        fi
    fi
}

# ---------- helper: write a temp SKILL.md and make JSON payload ----------
make_payload() {
    local path="$1"
    echo "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$path\"}}"
}

# Case 1: non-SKILL.md file - silent pass
TMP=$(mktemp /tmp/test_other.py)
OUT=$(make_payload "$TMP" | bash "$SCRIPT" 2>&1); CODE=$?
check "non-skill file silent" "" "$OUT" $CODE
rm -f "$TMP"

# Case 2: valid SKILL.md with name and description - silent pass
TMP=$(mktemp /tmp/test_SKILL.XXXXXX.md)
# rename to match */SKILL.md glob
SKILL_PATH="${TMPDIR:-/tmp}/skills_test_$(date +%s)/SKILL.md"
mkdir -p "$(dirname "$SKILL_PATH")"
cat > "$SKILL_PATH" << 'FM'
---
name: test-skill
description: A test skill for validation
---
# Body
FM
OUT=$(make_payload "$SKILL_PATH" | bash "$SCRIPT" 2>&1); CODE=$?
check "valid SKILL.md silent" "" "$OUT" $CODE
rm -rf "$(dirname "$SKILL_PATH")"

# Case 3: SKILL.md missing name - should warn
SKILL_PATH="${TMPDIR:-/tmp}/skills_missing_$(date +%s)/SKILL.md"
mkdir -p "$(dirname "$SKILL_PATH")"
cat > "$SKILL_PATH" << 'FM'
---
description: Only description present
---
# Body
FM
OUT=$(make_payload "$SKILL_PATH" | bash "$SCRIPT" 2>&1); CODE=$?
check "missing name warns" "WARN.*name" "$OUT" $CODE
rm -rf "$(dirname "$SKILL_PATH")"

# Case 4: SKILL.md missing description - should warn
SKILL_PATH="${TMPDIR:-/tmp}/skills_nodesc_$(date +%s)/SKILL.md"
mkdir -p "$(dirname "$SKILL_PATH")"
cat > "$SKILL_PATH" << 'FM'
---
name: only-name
---
# Body
FM
OUT=$(make_payload "$SKILL_PATH" | bash "$SCRIPT" 2>&1); CODE=$?
check "missing description warns" "WARN.*description" "$OUT" $CODE
rm -rf "$(dirname "$SKILL_PATH")"

# Case 5: SKILL.md no frontmatter at all - should warn
SKILL_PATH="${TMPDIR:-/tmp}/skills_nofm_$(date +%s)/SKILL.md"
mkdir -p "$(dirname "$SKILL_PATH")"
echo "# No frontmatter" > "$SKILL_PATH"
OUT=$(make_payload "$SKILL_PATH" | bash "$SCRIPT" 2>&1); CODE=$?
check "no frontmatter warns" "WARN.*frontmatter" "$OUT" $CODE
rm -rf "$(dirname "$SKILL_PATH")"

# Case 6: agents/*.md file missing description - should warn
AGENT_PATH="${TMPDIR:-/tmp}/agents_test_$(date +%s)/code-reviewer.md"
mkdir -p "$(dirname "$AGENT_PATH")"
cat > "$AGENT_PATH" << 'FM'
---
name: code-reviewer
---
# Agent body
FM
OUT=$(make_payload "$AGENT_PATH" | bash "$SCRIPT" 2>&1); CODE=$?
check "agent missing description warns" "WARN.*description" "$OUT" $CODE
rm -rf "$(dirname "$AGENT_PATH")"

# Case 7: empty stdin - silent pass
OUT=$(echo "" | bash "$SCRIPT" 2>&1); CODE=$?
check "empty stdin silent" "" "$OUT" $CODE

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
TESTS
chmod +x /tmp/test_validate_frontmatter.sh
```

- [ ] **Step 2: Run the test harness against a non-existent script to confirm all tests fail**

```bash
bash /tmp/test_validate_frontmatter.sh 2>&1 | head -20
```

Expected: all cases FAIL (script does not exist yet).

- [ ] **Step 3: Create validate-frontmatter.sh**

```bash
cat > /home/byron/dev/.claude/scripts/validate-frontmatter.sh << 'SCRIPT'
#!/usr/bin/env bash
# =============================================================================
# Frontmatter Validator - PostToolUse Hook
# =============================================================================
# Fires after Edit or Write. Checks that SKILL.md and agents/*.md files
# contain the required frontmatter fields: name and description.
#
# Exit codes: always 0 - advisory only, never blocks
# =============================================================================

set -euo pipefail

if ! command -v jq &>/dev/null; then
    exit 0
fi

CONTEXT=$(cat)
if [[ -z "$CONTEXT" ]]; then
    exit 0
fi

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null <<< "$CONTEXT")
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only act on SKILL.md files and agents/*.md files
if [[ "$FILE_PATH" != */SKILL.md && "$FILE_PATH" != */agents/*.md ]]; then
    exit 0
fi

if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

CONTENT=$(cat "$FILE_PATH")

# Extract frontmatter block between first two --- delimiters
FM=$(echo "$CONTENT" | awk '/^---/{found++; if(found==2) exit} found==1 && !/^---/{print}')

if [[ -z "$FM" ]]; then
    echo "WARN: no frontmatter found in $FILE_PATH"
    exit 0
fi

for FIELD in name description; do
    if ! echo "$FM" | grep -qE "^${FIELD}:"; then
        echo "WARN: missing '${FIELD}:' in frontmatter of $FILE_PATH"
    fi
done

exit 0
SCRIPT
chmod +x /home/byron/dev/.claude/scripts/validate-frontmatter.sh
```

- [ ] **Step 4: Run the test harness and confirm all tests pass**

```bash
bash /tmp/test_validate_frontmatter.sh
```

Expected output:
```text
PASS [non-skill file silent]
PASS [valid SKILL.md silent]
PASS [missing name warns]
PASS [missing description warns]
PASS [no frontmatter warns]
PASS [agent missing description warns]
PASS [empty stdin silent]

Results: 7 passed, 0 failed
```

- [ ] **Step 5: Add the hook entry to settings.json**

In `/home/byron/.claude/settings.json`, append a third entry to the PostToolUse `(Edit|Write)` hooks array (after the shellcheck entry added in Task 1):

```json
{
  "type": "command",
  "command": "bash $HOME/.claude/scripts/validate-frontmatter.sh",
  "timeout": 10,
  "statusMessage": "Validating skill/agent frontmatter..."
}
```

- [ ] **Step 6: Smoke-test by editing a SKILL.md with a missing field**

```bash
# Create a temp SKILL.md missing description
mkdir -p /tmp/smoke_skill
cat > /tmp/smoke_skill/SKILL.md << 'EOF'
---
name: smoke-test
---
# Body
EOF
```

Then use the Edit tool on `/tmp/smoke_skill/SKILL.md` to add a blank line. Expected: Claude receives `WARN: missing 'description:' in frontmatter`.

- [ ] **Step 7: Commit**

```bash
cd /home/byron/dev/.claude
git add scripts/validate-frontmatter.sh .claude/settings.json
git commit -m "feat: add frontmatter validator PostToolUse hook for skills and agents"
```

---

### Task 3: Force-push guard + timing start (bash-pre-hook.sh)

**Files:**
- Create: `dev/.claude/scripts/bash-pre-hook.sh`
- Modify: `~/.claude/settings.json` (add new PreToolUse Bash entry)

The script does two things: (1) block `git push --force` or `push -f` targeting main or master (exit 2), and (2) write a Unix timestamp to `/tmp/claude-bash-start` so Task 4's notification script can compute duration. The force-push check runs first; if it blocks, the timestamp is never written (correct behavior - no dangling start time for a blocked command).

- [ ] **Step 1: Write the test harness**

```bash
cat > /tmp/test_bash_pre_hook.sh << 'TESTS'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$HOME/.claude/scripts/bash-pre-hook.sh"
PASS=0
FAIL=0

check() {
    local name="$1"
    local expected_exit="$2"
    local expected_pattern="$3"   # empty = don't check output
    local output="$4"
    local actual_exit="$5"

    local ok=true
    if [[ $actual_exit -ne $expected_exit ]]; then
        echo "FAIL [$name]: expected exit $expected_exit, got $actual_exit"
        ok=false
    fi
    if [[ -n "$expected_pattern" ]] && ! echo "$output" | grep -qE "$expected_pattern"; then
        echo "FAIL [$name]: expected pattern '$expected_pattern', got: $output"
        ok=false
    fi
    if $ok; then
        echo "PASS [$name]"
        ((PASS++))
    else
        ((FAIL++))
    fi
}

make_payload() {
    local cmd="$1"
    echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$cmd\"}}"
}

# Case 1: normal git push - allow (exit 0)
OUT=$(make_payload "git push origin feat/foo" | bash "$SCRIPT" 2>&1); CODE=$?
check "normal push allowed" 0 "" "$OUT" $CODE

# Case 2: force push to main - block (exit 2)
OUT=$(make_payload "git push --force origin main" | bash "$SCRIPT" 2>&1); CODE=$?
check "force push to main blocked" 2 "BLOCKED" "$OUT" $CODE

# Case 3: -f shorthand to main - block (exit 2)
OUT=$(make_payload "git push -f origin main" | bash "$SCRIPT" 2>&1); CODE=$?
check "force push -f to main blocked" 2 "BLOCKED" "$OUT" $CODE

# Case 4: force push to master - block (exit 2)
OUT=$(make_payload "git push --force origin master" | bash "$SCRIPT" 2>&1); CODE=$?
check "force push to master blocked" 2 "BLOCKED" "$OUT" $CODE

# Case 5: force push to a feature branch - allow (exit 0)
OUT=$(make_payload "git push --force origin feat/my-branch" | bash "$SCRIPT" 2>&1); CODE=$?
check "force push to feature branch allowed" 0 "" "$OUT" $CODE

# Case 6: force-with-lease to main - block (exit 2)
OUT=$(make_payload "git push --force-with-lease origin main" | bash "$SCRIPT" 2>&1); CODE=$?
check "force-with-lease to main blocked" 2 "BLOCKED" "$OUT" $CODE

# Case 7: non-git command - allow (exit 0) and writes timestamp
rm -f /tmp/claude-bash-start
OUT=$(make_payload "pytest tests/" | bash "$SCRIPT" 2>&1); CODE=$?
check "non-git command allowed" 0 "" "$OUT" $CODE
if [[ -f /tmp/claude-bash-start ]]; then
    echo "PASS [timestamp written]"
    ((PASS++))
else
    echo "FAIL [timestamp written]: /tmp/claude-bash-start not found"
    ((FAIL++))
fi

# Case 8: empty stdin - allow (exit 0)
OUT=$(echo "" | bash "$SCRIPT" 2>&1); CODE=$?
check "empty stdin allowed" 0 "" "$OUT" $CODE

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
TESTS
chmod +x /tmp/test_bash_pre_hook.sh
```

- [ ] **Step 2: Run test harness to confirm all tests fail**

```bash
bash /tmp/test_bash_pre_hook.sh 2>&1 | head -15
```

Expected: all cases FAIL (script does not exist).

- [ ] **Step 3: Create bash-pre-hook.sh**

```bash
cat > /home/byron/dev/.claude/scripts/bash-pre-hook.sh << 'SCRIPT'
#!/usr/bin/env bash
# =============================================================================
# Bash PreToolUse Hook
# =============================================================================
# Two responsibilities:
#   1. Block force-push to main/master (exit 2)
#   2. Write start timestamp for bash-notify.sh duration tracking
#
# Exit codes:
#   0  - allow command to proceed
#   2  - block command; stdout message surfaced to Claude
# =============================================================================

set -euo pipefail

if ! command -v jq &>/dev/null; then
    date +%s > /tmp/claude-bash-start
    exit 0
fi

CONTEXT=$(cat)
if [[ -z "$CONTEXT" ]]; then
    date +%s > /tmp/claude-bash-start
    exit 0
fi

CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT")
if [[ -z "$CMD" ]]; then
    date +%s > /tmp/claude-bash-start
    exit 0
fi

# ---- Force-push guard -------------------------------------------------------
# Patterns: push (--force|-f|--force-with-lease) ... main|master
# OR:       push ... main|master ... (--force|-f|--force-with-lease)
if echo "$CMD" | grep -qE 'git\s+push\s.*(--force|--force-with-lease|-f)\s.*\b(main|master)\b' || \
   echo "$CMD" | grep -qE 'git\s+push\s.*\b(main|master)\b.*(--force|--force-with-lease|-f)'; then
    echo "BLOCKED: force-push to main/master is prohibited. Use a PR instead."
    exit 2
fi

# ---- Timing start -----------------------------------------------------------
date +%s > /tmp/claude-bash-start

exit 0
SCRIPT
chmod +x /home/byron/dev/.claude/scripts/bash-pre-hook.sh
```

- [ ] **Step 4: Run the test harness and confirm all tests pass**

```bash
bash /tmp/test_bash_pre_hook.sh
```

Expected output:
```text
PASS [normal push allowed]
PASS [force push to main blocked]
PASS [force push -f to main blocked]
PASS [force push to master blocked]
PASS [force push to feature branch allowed]
PASS [force-with-lease to main blocked]
PASS [non-git command allowed]
PASS [timestamp written]
PASS [empty stdin allowed]

Results: 9 passed, 0 failed
```

- [ ] **Step 5: Add the PreToolUse Bash entry to settings.json**

In `/home/byron/.claude/settings.json`, add a third entry to the `PreToolUse` array (after the existing Skill entry):

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash $HOME/.claude/scripts/bash-pre-hook.sh",
      "timeout": 10,
      "statusMessage": "Checking Bash command safety..."
    }
  ]
}
```

- [ ] **Step 6: Smoke-test force-push blocking**

```bash
# Pipe a mock payload directly to the script
echo '{"tool_name":"Bash","tool_input":{"command":"git push --force origin main"}}' \
  | bash ~/.claude/scripts/bash-pre-hook.sh; echo "exit: $?"
```

Expected output:
```yaml
BLOCKED: force-push to main/master is prohibited. Use a PR instead.
exit: 2
```

- [ ] **Step 7: Commit**

```bash
cd /home/byron/dev/.claude
git add scripts/bash-pre-hook.sh .claude/settings.json
git commit -m "feat: add force-push guard and timing PreToolUse hook for Bash"
```

---

### Task 4: WSL2 notification script and hook (bash-notify.sh)

**Files:**
- Create: `dev/.claude/scripts/bash-notify.sh`
- Modify: `~/.claude/settings.json` (add new PostToolUse Bash entry)

Reads the timestamp written by `bash-pre-hook.sh`. If the elapsed time exceeds 30 seconds, fires a non-blocking Windows toast via `powershell.exe`. The notification shows the duration and a truncated version of the command. Always exits 0.

- [ ] **Step 1: Write the test harness**

```bash
cat > /tmp/test_bash_notify.sh << 'TESTS'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$HOME/.claude/scripts/bash-notify.sh"
PASS=0
FAIL=0

check() {
    local name="$1"
    local expected_pattern="$2"   # empty = expect silent; "NOTIFY" = expect notification log
    local output="$3"
    local exit_code="$4"

    if [[ $exit_code -ne 0 ]]; then
        echo "FAIL [$name]: script exited $exit_code (must always exit 0)"
        ((FAIL++)); return
    fi

    if [[ -z "$expected_pattern" ]]; then
        if [[ -z "$output" ]]; then
            echo "PASS [$name]"
            ((PASS++))
        else
            echo "FAIL [$name]: expected silence, got: $output"
            ((FAIL++))
        fi
    else
        if echo "$output" | grep -qE "$expected_pattern"; then
            echo "PASS [$name]"
            ((PASS++))
        else
            echo "FAIL [$name]: expected pattern '$expected_pattern', got: $output"
            ((FAIL++))
        fi
    fi
}

make_payload() {
    local cmd="$1"
    echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$cmd\"},\"tool_response\":{\"output\":\"\"}}"
}

# Case 1: duration < 30s - silent (no notification)
echo "$(date +%s)" > /tmp/claude-bash-start   # start = now
OUT=$(make_payload "pytest tests/" | bash "$SCRIPT" 2>&1); CODE=$?
check "short command silent" "" "$OUT" $CODE

# Case 2: duration > 30s - notification logged
echo "$(($(date +%s) - 35))" > /tmp/claude-bash-start   # start = 35s ago
OUT=$(make_payload "pytest tests/" | bash "$SCRIPT" 2>&1); CODE=$?
check "long command notifies" "NOTIFY" "$OUT" $CODE

# Case 3: no start file - silent (graceful missing file)
rm -f /tmp/claude-bash-start
OUT=$(make_payload "some command" | bash "$SCRIPT" 2>&1); CODE=$?
check "missing start file silent" "" "$OUT" $CODE

# Case 4: empty stdin - silent
OUT=$(echo "" | bash "$SCRIPT" 2>&1); CODE=$?
check "empty stdin silent" "" "$OUT" $CODE

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
TESTS
chmod +x /tmp/test_bash_notify.sh
```

- [ ] **Step 2: Run test harness to confirm all tests fail**

```bash
bash /tmp/test_bash_notify.sh 2>&1 | head -10
```

Expected: all cases FAIL.

- [ ] **Step 3: Create bash-notify.sh**

```bash
cat > /home/byron/dev/.claude/scripts/bash-notify.sh << 'SCRIPT'
#!/usr/bin/env bash
# =============================================================================
# Bash PostToolUse Notification Hook
# =============================================================================
# Reads the start timestamp written by bash-pre-hook.sh. If the elapsed time
# exceeds NOTIFY_THRESHOLD_SECONDS, sends a non-blocking Windows toast
# notification via powershell.exe (WSL2).
#
# Prints "NOTIFY: ..." to stdout when a notification fires (visible to Claude
# and captured by tests).
#
# Exit codes: always 0 - never blocks
# =============================================================================

set -euo pipefail

NOTIFY_THRESHOLD_SECONDS=30
START_FILE="/tmp/claude-bash-start"
LOG_FILE="${HOME}/.claude/logs/bash-notify.log"

log() {
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# ---- Read start time --------------------------------------------------------
if [[ ! -f "$START_FILE" ]]; then
    exit 0
fi

START=$(cat "$START_FILE" 2>/dev/null || echo "")
if [[ -z "$START" ]] || ! [[ "$START" =~ ^[0-9]+$ ]]; then
    exit 0
fi

NOW=$(date +%s)
DURATION=$((NOW - START))

# Clean up timestamp file regardless of whether we notify
rm -f "$START_FILE"

if [[ $DURATION -le $NOTIFY_THRESHOLD_SECONDS ]]; then
    exit 0
fi

# ---- Extract command for notification text ----------------------------------
CMD=""
if command -v jq &>/dev/null; then
    CONTEXT=$(cat 2>/dev/null || echo "")
    if [[ -n "$CONTEXT" ]]; then
        CMD=$(jq -r '.tool_input.command // empty' 2>/dev/null <<< "$CONTEXT" | head -c 60)
    fi
fi

TITLE="Claude Code"
MSG="Task complete (${DURATION}s)"
if [[ -n "$CMD" ]]; then
    MSG="${MSG}: ${CMD}"
fi

# ---- Send non-blocking toast via powershell.exe ----------------------------
if command -v powershell.exe &>/dev/null; then
    ESCAPED_TITLE="${TITLE//\'/\'\'}"
    ESCAPED_MSG="${MSG//\'/\'\'}"
    powershell.exe -NonInteractive -command "
        Add-Type -AssemblyName System.Windows.Forms
        \$n = New-Object System.Windows.Forms.NotifyIcon
        \$n.Icon = [System.Drawing.SystemIcons]::Application
        \$n.BalloonTipTitle = '${ESCAPED_TITLE}'
        \$n.BalloonTipText = '${ESCAPED_MSG}'
        \$n.Visible = \$true
        \$n.ShowBalloonTip(5000)
        Start-Sleep -Milliseconds 5500
        \$n.Dispose()
    " &>/dev/null &
    disown 2>/dev/null || true
fi

echo "NOTIFY: ${MSG}"
log "notification sent: ${MSG}"

exit 0
SCRIPT
chmod +x /home/byron/dev/.claude/scripts/bash-notify.sh
```

- [ ] **Step 4: Run the test harness and confirm all tests pass**

```bash
bash /tmp/test_bash_notify.sh
```

Expected output:
```text
PASS [short command silent]
PASS [long command notifies]
PASS [missing start file silent]
PASS [empty stdin silent]

Results: 4 passed, 0 failed
```

- [ ] **Step 5: Add the PostToolUse Bash entry to settings.json**

In `/home/byron/.claude/settings.json`, add a second entry to the `PostToolUse` array (the existing entry is the `(Edit|Write)` one - this is a new top-level matcher entry):

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash $HOME/.claude/scripts/bash-notify.sh",
      "timeout": 15,
      "statusMessage": ""
    }
  ]
}
```

The empty `statusMessage` keeps this silent in the UI unless a notification fires.

- [ ] **Step 6: End-to-end test of the notification**

```bash
# Simulate a long-elapsed start time
echo "$(($(date +%s) - 40))" > /tmp/claude-bash-start

# Pipe a mock PostToolUse payload to the script
echo '{"tool_name":"Bash","tool_input":{"command":"pytest tests/ -v"},"tool_response":{"output":""}}' \
  | bash ~/.claude/scripts/bash-notify.sh
```

Expected stdout: `NOTIFY: Task complete (40s): pytest tests/ -v`
Expected side effect: a Windows balloon notification appears in the system tray.

- [ ] **Step 7: Commit**

```bash
cd /home/byron/dev/.claude
git add scripts/bash-notify.sh .claude/settings.json
git commit -m "feat: add WSL2 toast notification PostToolUse hook for long Bash tasks"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
| ----------- | ---- |
| Shellcheck on .sh edits, advisory | Task 1 |
| Frontmatter validator on SKILL.md/agents/*.md | Task 2 |
| Force-push guard to main/master, exit 2 | Task 3 |
| WSL2 notification for Bash > 30s | Task 4 |
| Timing mechanism (PreToolUse writes timestamp) | Task 3 step 3 |
| Notification non-blocking | Task 4 step 3 (`& disown`) |

**Placeholder scan:** No TBD/TODO/placeholder content found.

**Type consistency:** All scripts use consistent variable names (`CONTEXT`, `CMD`, `FILE_PATH`). Timestamp file is `/tmp/claude-bash-start` in both bash-pre-hook.sh and bash-notify.sh.

**Known limitation:** The `NOTIFY` stdout output from `bash-notify.sh` is visible to Claude in the session (it is not a warning - it is informational). If this becomes noisy, change `echo "NOTIFY: ..."` to write to the log file only.
