#!/usr/bin/env python3
"""session-length-nudge.py.

UserPromptSubmit hook that mechanically checks carried context against the
CLAUDE.md "Session length" soft nudge (~100K carried tokens) and injects a
reminder once the session crosses into a new 50K-token band past that
threshold. Exists because the soft nudge is advisory prose Claude must notice
and act on; this hook makes the check happen every turn instead of depending
on the assistant remembering to look.

Carried-token computation mirrors ``scripts/analyze-session-inflection.py``'s
``iter_usage``: the most recent main-thread (non-sidechain) assistant turn's
``input_tokens + cache_read_input_tokens + cache_creation_input_tokens``.

Protocol: reads a JSON event from stdin (expects ``transcript_path`` and
``session_id``), writes JSON to stdout with an optional ``systemMessage``
field. Exits 0 on any exception raised by its own logic (never blocks the
prompt); any read, parse, or I/O failure degrades to a silent no-op rather
than surfacing an error.

Env vars:
    SESSION_LENGTH_SOFT_TARGET: soft-nudge threshold in tokens (default
        100000). Keep in sync with the "Below ~100K" bullet in CLAUDE.md
        "Session length" -- this script cannot read that prose, so the
        number is necessarily duplicated here.
    SESSION_LENGTH_NUDGE_DISABLED: set to "1" to disable this hook entirely.

Installation: referenced from ``hooks.json`` under ``UserPromptSubmit``, so
``setup.sh`` merges it into ``~/.claude/settings.json`` on install.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DEFAULT_SOFT_TARGET = 100_000
BAND_SIZE = 50_000

STATE_DIR = Path.home() / ".claude" / "tmp_cleanup" / ".session-length-nudge"

# session_id is expected to be a UUID-like token from Claude Code, but treat
# it as untrusted input: strip anything that is not safe in a filename so a
# malformed event can never escape STATE_DIR via path traversal.
# #EDGE: a session_id containing only unsafe characters collapses to an
# empty string; _state_file returns None for that case and the hook no-ops.
# #VERIFY: pass session_id="../../etc/passwd" through _state_file and confirm
# the resolved path stays under STATE_DIR.
_UNSAFE_ID_CHARS = re.compile(r"[^A-Za-z0-9_-]")


def _read_event() -> dict:
    """Read the hook event JSON from stdin, tolerating malformed input."""
    try:
        data = sys.stdin.read()
    except OSError:
        return {}
    if not data.strip():
        return {}
    try:
        parsed = json.loads(data)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_int(value: object) -> int:
    """Coerce a JSON numeric value to int; treat missing or odd values as 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int | float):
        return int(value)
    return 0


def _last_carried_tokens(transcript_path: str) -> int | None:
    """Return carried tokens for the most recent main-thread assistant turn.

    Returns None if the transcript is missing, unreadable, or contains no
    matching turn. Scans from the end of the transcript so a hit near the
    tail (the common case) skips parsing the earlier bulk of the session.
    """
    path = Path(transcript_path)
    try:
        if not path.is_file():
            return None
        with path.open(encoding="utf-8") as handle:
            lines = handle.readlines()
    except (OSError, UnicodeDecodeError):
        return None

    for raw in reversed(lines):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("type") != "assistant" or record.get("isSidechain"):
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if isinstance(usage, dict):
            return (
                _as_int(usage.get("input_tokens"))
                + _as_int(usage.get("cache_read_input_tokens"))
                + _as_int(usage.get("cache_creation_input_tokens"))
            )

    return None


def _state_file(session_id: str) -> Path | None:
    """Return the per-session state file path, or None for an empty id."""
    safe_id = _UNSAFE_ID_CHARS.sub("", session_id)
    if not safe_id:
        return None
    return STATE_DIR / safe_id


def _last_notified_bucket(state_path: Path) -> int:
    """Read the last-notified band from the state file.

    Returns -1 (a sentinel below any valid non-negative bucket) if the state
    file is absent or invalid, so a real first crossing whose bucket floors
    to 0 (carried tokens below BAND_SIZE) is never mistaken for "already
    notified".
    """
    try:
        return int(state_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return -1


def _record_notified_bucket(state_path: Path, bucket: int) -> None:
    """Persist the newly-notified band; failures are non-fatal (best effort)."""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(str(bucket), encoding="utf-8")
    except OSError:
        # State persistence is best-effort: a write failure here only means
        # the reminder may repeat next turn instead of once per band, which
        # is consistent with this hook's silent-no-op-on-I/O-failure contract.
        pass


def _reminder_message(bucket: int, threshold: int) -> str:
    """Build the reminder text for crossing into a newly-notified band."""
    display = max(bucket, threshold)
    return (
        f"[session-length-nudge] This session has crossed ~{display:,} carried "
        f'tokens, past the CLAUDE.md "Session length" soft nudge (~{threshold:,}). '
        "At the next finished task boundary (never mid-task), offer the user the "
        "graduated choice from that section: `/handoff` for a clean break, or "
        "`/compact [instructions]` to shed stale context in place. If you already "
        "offered this and the user declined, do not re-offer until context has "
        "grown materially past this point."
    )


def main() -> None:
    """Run the hook. Always exits 0; never blocks the prompt."""
    if os.environ.get("SESSION_LENGTH_NUDGE_DISABLED") == "1":
        print(json.dumps({}))
        return

    try:
        threshold = int(
            os.environ.get("SESSION_LENGTH_SOFT_TARGET", str(DEFAULT_SOFT_TARGET))
        )
    except ValueError:
        threshold = DEFAULT_SOFT_TARGET
    if threshold <= 0:
        threshold = DEFAULT_SOFT_TARGET

    event = _read_event()
    transcript_path = event.get("transcript_path")
    session_id = event.get("session_id")

    if not isinstance(transcript_path, str) or not isinstance(session_id, str):
        print(json.dumps({}))
        return

    carried = _last_carried_tokens(transcript_path)
    if carried is None or carried < threshold:
        print(json.dumps({}))
        return

    bucket = (carried // BAND_SIZE) * BAND_SIZE

    state_path = _state_file(session_id)
    if state_path is None:
        print(json.dumps({}))
        return

    if bucket <= _last_notified_bucket(state_path):
        print(json.dumps({}))
        return

    _record_notified_bucket(state_path, bucket)
    print(json.dumps({"systemMessage": _reminder_message(bucket, threshold)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            print(json.dumps({}))
        except OSError:
            pass
