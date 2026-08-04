#!/usr/bin/env python3
"""PostToolUse hook: nudge when the orchestrator is doing implementation itself.

Registered under hooks.PostToolUse for `Edit|Write|NotebookEdit`. Canonical
source is hooks.json in this repo; setup.sh merge_hooks() regenerates the live
~/.claude/settings.json block from it, so edit hooks.json rather than the live
file.

Why this exists as a hook and not as prose: the CLAUDE.md delegation rule is
already stated at session start by scripts/hooks/delegation-reminder.sh, but a
session-start reminder cannot observe what the session then does. Transcript
analysis across 16 sessions found the failure bimodal rather than gradual: six
sessions ran at 3.8-to-infinity main-thread edits per subagent dispatch while
six others ran at 0.4-to-2.0, in the same repos with the same tooling. One
session made 122 main-thread edits and dispatched nothing at all. A per-session
habit that either engages early or never does needs a mid-session trigger.

Attribution: subagent turns land in the same transcript as the root thread,
distinguished only by `isSidechain`. Counting this hook's own invocations would
charge subagent edits to the root thread and nudge the sessions that delegate
best, so counts come from the transcript, never from the hook payload.

This hook is advisory and never blocks. Stopping an Edit mid-implementation is
a worse failure than the one being prevented, and the agent may be doing
legitimate orchestration-inline work that no counter can distinguish. It fails
open in every path: any missing input, unreadable file, or unexpected error
prints `{}` and exits 0.

Env vars:
    DELEGATION_NUDGE_DISABLED: set to "1" to disable this hook entirely.
    DELEGATION_NUDGE_FLOOR: minimum main-thread mutations before the hook is
        willing to speak (default 10).
    DELEGATION_NUDGE_RATIO: mutations-per-dispatch ratio that trips the nudge
        (default 3.0).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DEFAULT_FLOOR = 10
DEFAULT_RATIO = 3.0

# Re-arm spacing: main-thread mutations that must accrue since the last nudge
# before another may fire. A session that ignores the nudge escalates every 15
# edits; a session that corrects goes quiet on its own, because the ratio is
# recomputed each time and one dispatch can drop it back under threshold.
#
# Spacing runs from the previous fire, not from fixed bands. Fixed bands put
# the boundary at an absolute edit count, so a session whose ratio first
# crossed at edit 24 fired again at 25. Replaying real transcripts surfaced
# both that and a 10-then-15 double-tap under the original zero-based bands.
REARM_AFTER = 15

# Hard cap on nudges per session. Replaying a 122-edit, zero-dispatch session
# produced nine identical messages under pure band escalation. Past the fourth
# the reader has been told; repeating it only teaches them to skip the prefix.
MAX_FIRES = 4

MUTATING_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
DISPATCH_TOOL = "Agent"

STATE_DIR = Path.home() / ".claude" / "tmp_cleanup" / ".delegation-ratio-nudge"

# session_id is expected to be a UUID-like token from Claude Code, but treat it
# as untrusted input: strip anything unsafe in a filename so a malformed event
# cannot escape STATE_DIR via path traversal.
# #EDGE: an id of only unsafe characters collapses to empty; state_file returns
# None for that case and the hook no-ops.
# #VERIFY: pass session_id="../../etc/passwd" through state_file and confirm the
# resolved path stays under STATE_DIR.
_UNSAFE_ID_CHARS = re.compile(r"[^A-Za-z0-9_-]")


def _env_int(name: str, default: int) -> int:
    """Read a positive int from the environment, falling back on bad input."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _env_float(name: str, default: float) -> float:
    """Read a positive float from the environment, falling back on bad input."""
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def state_file(session_id: str) -> Path | None:
    """Return the per-session state file path, or None for an unusable id.

    Args:
        session_id: Raw session id from the hook payload.

    Returns:
        Path under STATE_DIR, or None when the id sanitises to nothing.
    """
    safe_id = _UNSAFE_ID_CHARS.sub("", session_id)
    if not safe_id:
        return None
    return STATE_DIR / safe_id


def load_state(path: Path) -> dict[str, int]:
    """Read scan state, returning a zeroed state when absent or invalid.

    Args:
        path: State file path.

    Returns:
        Mapping with offset, mutations, dispatches, and last_band keys.
    """
    fresh = {
        "offset": 0,
        "mutations": 0,
        "dispatches": 0,
        "last_fire_at": -1,
        "fires": 0,
    }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fresh
    if not isinstance(raw, dict):
        return fresh
    return {key: int(raw.get(key, fallback)) for key, fallback in fresh.items()}


def save_state(path: Path, state: dict[str, int]) -> None:
    """Persist scan state; failures are non-fatal and leave the hook silent."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        # Best effort, consistent with this hook's fail-open contract. A write
        # failure only means the next invocation recounts from its stale
        # offset, which at worst repeats a nudge.
        pass


def _count_line(line: str, state: dict[str, int]) -> None:
    """Add one transcript line's root-thread tool uses into state, in place."""
    try:
        record = json.loads(line)
    except ValueError:
        return
    if not isinstance(record, dict):
        return
    if record.get("type") != "assistant" or record.get("isSidechain"):
        return
    message = record.get("message")
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name")
        if name in MUTATING_TOOLS:
            state["mutations"] += 1
        elif name == DISPATCH_TOOL:
            state["dispatches"] += 1


def scan(transcript: Path, state: dict[str, int]) -> dict[str, int]:
    """Fold newly-appended transcript lines into the running counts.

    Reads only the bytes past the stored offset, so the per-edit cost is
    proportional to what the session added since the last file mutation rather
    than to total transcript size.

    Args:
        transcript: Path to the session transcript JSONL.
        state: Prior scan state; not mutated.

    Returns:
        Updated state. Returned unchanged when the transcript is unreadable or
        holds no complete new line.
    """
    updated = dict(state)
    try:
        size = transcript.stat().st_size
    except OSError:
        return updated

    # A transcript smaller than the stored offset was rotated or compacted.
    # Trusting the offset would silently skip the new content, so recount.
    if size < updated["offset"]:
        updated.update({"offset": 0, "mutations": 0, "dispatches": 0})

    try:
        with transcript.open("rb") as handle:
            handle.seek(updated["offset"])
            chunk = handle.read()
    except OSError:
        return updated

    # Consume up to the last newline only. The final line may be a partial
    # write still in flight; advancing past it would drop that record forever.
    end = chunk.rfind(b"\n")
    if end == -1:
        return updated

    for line in chunk[: end + 1].decode("utf-8", errors="replace").splitlines():
        if line.strip():
            _count_line(line, updated)
    updated["offset"] += end + 1
    return updated


def should_fire(state: dict[str, int]) -> bool:
    """Decide whether to nudge on the current scan state.

    Args:
        state: Scan state carrying mutations, dispatches, fires, last_fire_at.

    Returns:
        True when the nudge should fire now.
    """
    mutations = state.get("mutations", 0)
    dispatches = state.get("dispatches", 0)

    if state.get("fires", 0) >= MAX_FIRES:
        return False

    # The floor exists because a noisy check trains its reader to ignore it:
    # a session with four edits and no dispatches has an infinite ratio and is
    # entirely fine. Same reasoning as MIN_TOOL_USES in
    # scripts/hooks/task-observer-flush-check.py.
    if mutations < _env_int("DELEGATION_NUDGE_FLOOR", DEFAULT_FLOOR):
        return False
    if mutations / max(dispatches, 1) < _env_float(
        "DELEGATION_NUDGE_RATIO", DEFAULT_RATIO
    ):
        return False

    last_fire_at = state.get("last_fire_at", -1)
    return last_fire_at < 0 or mutations >= last_fire_at + REARM_AFTER


def message(mutations: int, dispatches: int) -> str:
    """Build the advisory text shown to the model."""
    ratio = mutations / max(dispatches, 1)
    return (
        f"[delegation-ratio-nudge] This session has made {mutations} "
        f"main-thread file edits against {dispatches} subagent dispatches "
        f"({ratio:.1f}:1). CLAUDE.md assigns implementation to subagents; the "
        "orchestrator's job is decisions, synthesis, validation, and user "
        "interaction. If the remaining work is a well-specified unit (a "
        "bounded file set, a failing test, a migration step), dispatch it to "
        "general-purpose with model: sonnet rather than editing inline. If "
        "this work is genuinely orchestration-inline, ignore this; it "
        f"re-checks every {REARM_AFTER} edits and goes quiet once you delegate."
    )


def main() -> None:
    """Run the hook. Always prints JSON and exits 0; never blocks."""
    if os.environ.get("DELEGATION_NUDGE_DISABLED") == "1":
        print(json.dumps({}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        print(json.dumps({}))
        return
    if not isinstance(event, dict):
        print(json.dumps({}))
        return

    session_id = event.get("session_id")
    transcript_path = event.get("transcript_path")
    if not isinstance(session_id, str) or not isinstance(transcript_path, str):
        print(json.dumps({}))
        return

    path = state_file(session_id)
    if path is None:
        print(json.dumps({}))
        return

    # #ASSUME: at PostToolUse time the assistant record carrying this tool_use
    # is already flushed to the transcript, so the count includes the edit that
    # triggered this invocation.
    # #VERIFY: log mutations at fire time against a manual transcript grep and
    # confirm any lag is at most one record, never a full turn.
    state = scan(Path(transcript_path), load_state(path))
    if not should_fire(state):
        save_state(path, state)
        print(json.dumps({}))
        return

    state["last_fire_at"] = state["mutations"]
    state["fires"] = state.get("fires", 0) + 1
    save_state(path, state)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message(
                        state["mutations"], state["dispatches"]
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Deliberate catch-all. This hook runs after every file edit; an
        # unhandled traceback would surface as a hook error on every edit.
        # Failing open is the correct posture for an advisory reminder.
        try:
            print(json.dumps({}))
        except OSError:
            pass
        sys.exit(0)
