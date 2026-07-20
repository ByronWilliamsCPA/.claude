#!/usr/bin/env bash
# SessionStart hook: activate task-observer and record the observation-log
# baseline that this session will later be measured against.
#
# Registered under hooks.SessionStart with matchers startup|resume|clear|compact.
# Canonical source: hooks.json in this repo; setup.sh merge_hooks() regenerates
# the live ~/.claude/settings.json hooks block from it, so edit hooks.json, not
# the live file. Stdout becomes session context; keep it short.
#
# Companion: scripts/hooks/task-observer-flush-check.py (Stop) reads the
# baseline written here and blocks turn end once when a task-oriented session
# logged nothing. CLAUDE.md ("Task observation") carries the prose; this pair
# is what enforces it, because prose alone did not.
set -uo pipefail

OBS_DIR="$HOME/.claude/skill-observations"
STATE_DIR="$OBS_DIR/.state"
LOG="$OBS_DIR/log.md"

# #ASSUME: SessionStart stdin carries `session_id`, a documented common hook
# field. The Stop-side check needs it to correlate baseline with session.
# #EDGE: absent stdin, malformed JSON, or a session_id failing the character
# allowlist all resolve to an empty id, which skips baseline recording and
# leaves the Stop hook inert. That degrades to today's behaviour rather than
# failing the session.
# #VERIFY: start a session, then confirm a file appears under
# ~/.claude/skill-observations/.state/ named for the current session id.
SESSION_ID=""
if [ ! -t 0 ]; then
  SESSION_ID=$(timeout 3 python3 -c '
import json
import re
import sys

try:
    raw = json.load(sys.stdin).get("session_id", "")
except (ValueError, OSError):
    raw = ""
sid = raw if isinstance(raw, str) else ""
# Allowlist guards against a hostile or malformed id escaping the state path.
print(sid if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", sid) else "")
' 2>/dev/null) || SESSION_ID=""
fi

if [ -n "$SESSION_ID" ]; then
  if mkdir -p "$STATE_DIR" 2>/dev/null; then
    # Baseline is the observation count at session start. The Stop hook
    # compares the live count against it to decide whether anything was logged.
    if [ -r "$LOG" ]; then
      count=$(grep -c '^### Observation ' "$LOG" 2>/dev/null) || count=0
    else
      count=0
    fi
    printf '%s\n' "$count" >"$STATE_DIR/$SESSION_ID.baseline" 2>/dev/null

    # Bound the state directory. Sessions leave two small files each and never
    # clean up after themselves, so prune anything older than two weeks.
    find "$STATE_DIR" -type f -mtime +14 -delete 2>/dev/null
  fi
fi

cat <<'EOF'
TASK OBSERVATION (active this session):
- Invoke the task-observer skill before starting task-oriented work, and read
  ~/.claude/skill-observations/log.md for OPEN observations tagged to any
  skill you load.
- Write each observation to the log in the turn it occurs. Do not hold them in
  memory to batch at the end; the act of writing is the checkpoint.
- A Stop hook checks at turn end whether a task-oriented session logged
  anything, so an unwritten observation is surfaced rather than lost.
EOF
