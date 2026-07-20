#!/usr/bin/env python3
"""Stop hook: block turn end once when a task-oriented session logged nothing.

Registered under hooks.Stop. Canonical source is hooks.json in this repo;
setup.sh merge_hooks() regenerates the live ~/.claude/settings.json block from
it, so edit hooks.json rather than the live file.

Why this exists as a hook and not as skill prose: the task-observer flush
checkpoint was bound to TodoWrite completions, so a session that never called
TodoWrite had no trigger at all. Its companion SessionStart hook
(scripts/hooks/task-observer-reminder.sh) records the observation count at
session start; this script compares the live count against that baseline.

Blocking contract: emitting {"decision": "block", "reason": ...} on stdout
keeps the turn alive and shows `reason` to the model. Documented at
https://code.claude.com/docs/en/hooks.

This hook fails open in every path. Any missing input, unreadable file, or
unexpected error exits 0 with no output, which lets the turn end normally. A
hook that exists to catch a bookkeeping lapse must never be able to wedge a
session.
"""

import json
import re
import sys
from pathlib import Path

OBS_DIR = Path.home() / ".claude" / "skill-observations"
STATE_DIR = OBS_DIR / ".state"
LOG = OBS_DIR / "log.md"

SESSION_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,128}")
OBSERVATION_RE = re.compile(r"^### Observation ", re.MULTILINE)
TOOL_USE_RE = re.compile(r'"type"\s*:\s*"tool_use"')
MUTATING_TOOL_RE = re.compile(r'"name"\s*:\s*"(?:Edit|Write|NotebookEdit)"')

# A session must look substantial before this hook is willing to interrupt it.
# Both conditions must hold. The floor exists because a noisy check trains its
# reader to ignore it, which is the same reasoning that dropped rule R5 from
# scripts/lint-agent-frontmatter.py.
MIN_TOOL_USES = 20
MIN_MUTATIONS = 1

REASON = (
    "This session did substantial work but wrote no entries to "
    "~/.claude/skill-observations/log.md.\n"
    "Before ending: review the session for observations worth logging (user "
    "corrections, methodology insights, skill friction, techniques that "
    "worked well). If any exist, append them now, following the numbering "
    "protocol in the task-observer skill: read the highest existing "
    "'### Observation N' from the log first, never rely on session memory for "
    "the next number, and re-check for duplicates after writing because "
    "parallel sessions append to the same file.\n"
    "If nothing is worth logging, say so in one line and stop. This check "
    "fires at most once per session and will not ask again."
)


def read_text(path: Path) -> str:
    """Read a file as UTF-8, returning an empty string when unreadable.

    Args:
        path: File to read.

    Returns:
        The file contents, or "" if the file is missing or cannot be read.
    """
    # encoding is explicit: Path.read_text() otherwise uses the locale default,
    # which is cp1252 on Windows and raises UnicodeDecodeError on the non-ASCII
    # text these logs contain. errors="replace" keeps counting possible even if
    # the file carries undecodable bytes.
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def session_id_from(payload: dict[str, object]) -> str:
    """Extract a filesystem-safe session id from the hook payload.

    Args:
        payload: Parsed Stop-hook stdin JSON.

    Returns:
        The session id, or "" when absent or failing the character allowlist.
    """
    raw = payload.get("session_id", "")
    if not isinstance(raw, str):
        return ""
    return raw if SESSION_ID_RE.fullmatch(raw) else ""


def session_is_task_oriented(transcript: Path) -> bool:
    """Report whether the transcript shows deliverable-producing work.

    Read-only or conversational sessions are deliberately excluded: the
    task-observer skill scopes observation to sessions that use tools to
    produce deliverables, and a check that fires on casual sessions would be
    ignored within a week.

    Args:
        transcript: Path to the session transcript JSONL.

    Returns:
        True when the session made enough tool calls, including at least one
        file mutation, to count as task-oriented.
    """
    tool_uses = 0
    mutations = 0
    # Streamed with an early exit rather than read whole: this hook runs on
    # every turn end, and a long session's transcript is the largest file it
    # touches. A task-oriented session stops scanning within the first few
    # hundred lines.
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                tool_uses += len(TOOL_USE_RE.findall(line))
                mutations += len(MUTATING_TOOL_RE.findall(line))
                if tool_uses >= MIN_TOOL_USES and mutations >= MIN_MUTATIONS:
                    return True
    except OSError:
        return False
    return False


def observations_logged(baseline_file: Path) -> bool:
    """Report whether the log grew since this session started.

    Args:
        baseline_file: State file holding the session-start observation count.

    Returns:
        True when the live count exceeds the baseline, or when the baseline is
        missing or unparseable (fail open: no baseline means no verdict).
    """
    raw = read_text(baseline_file).strip()
    if not raw:
        return True
    try:
        baseline = int(raw)
    except ValueError:
        return True
    return len(OBSERVATION_RE.findall(read_text(LOG))) > baseline


def main() -> int:
    """Decide whether to block turn end, and emit the decision.

    Returns:
        Always 0. Blocking is signalled by JSON on stdout, never by exit code,
        so a crash can never wedge the session.
    """
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0

    # `stop_hook_active` appears in the hooks overview but not the reference
    # schema, so it is treated as a bonus guard only. The marker file below is
    # the load-bearing re-entry guard.
    if payload.get("stop_hook_active") is True:
        return 0

    session_id = session_id_from(payload)
    if not session_id:
        return 0

    nudged = STATE_DIR / f"{session_id}.nudged"
    baseline_file = STATE_DIR / f"{session_id}.baseline"
    # No baseline means the SessionStart hook never ran for this session (it
    # was added mid-session, or the id was unusable). Without a baseline there
    # is no honest before-and-after, so stay silent.
    if nudged.exists() or not baseline_file.exists():
        return 0

    if observations_logged(baseline_file):
        return 0

    transcript = payload.get("transcript_path", "")
    if not isinstance(transcript, str) or not transcript:
        return 0
    if not session_is_task_oriented(Path(transcript)):
        return 0

    # Mark before emitting: if the write fails, stay silent rather than risk a
    # block that cannot record that it already fired.
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        nudged.write_text("1\n", encoding="utf-8")
    except OSError:
        return 0

    json.dump({"decision": "block", "reason": REASON}, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Deliberate catch-all. This hook runs on every turn end; an unhandled
        # traceback here would surface as a hook error on every single turn.
        # Failing open is the correct posture for a bookkeeping reminder.
        sys.exit(0)
