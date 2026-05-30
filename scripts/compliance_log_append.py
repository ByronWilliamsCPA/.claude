#!/usr/bin/env python3
"""Append a JSON entry to the compliance master log, with supersede handling.

Reads a single JSON object from stdin and:
1. Resolves the central master-log.jsonl path via repo discovery.
2. Acquires an exclusive flock on a sibling .lock file so a concurrent
   agent cannot interleave reads, supersede rewrites, and appends.
3. Validates required schema keys and raises with a clear message on
   schema drift.
4. If (session_date, repo) already exists, marks the existing entry
   superseded_by the new session_id and writes the supersede flag plus
   the new entry as a single atomic rename of a temp file.
5. Otherwise appends the new entry under the held lock.
6. Invokes the renderer to regenerate master-log.md and surfaces any
   non-zero exit so a stale Markdown view does not silently diverge.

Intended to be invoked by the compliance-retrospective agent at the
end of every audit session. Decouples the agent prompt from the
relative-path trap.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from claude_config.compliance.log_common import (
    ensure_header,
    load_entries,
    make_dedupe_key,
    repo_root_from,
    validate_entry,
)

_REPO_ROOT = repo_root_from(Path(__file__))
DEFAULT_JSONL = _REPO_ROOT / "docs" / "compliance-reports" / "master-log.jsonl"
RENDERER_SCRIPT = Path(__file__).resolve().parent / "compliance_log_render.py"


@contextlib.contextmanager
def _locked(jsonl_path: Path):  # type: ignore[no-untyped-def]
    """Acquire an exclusive file lock on a sibling lock file.

    Args:
        jsonl_path: Path to the JSONL file being mutated. The lock
            sits next to it as ``<name>.lock`` so the JSONL itself
            never gains exclusive-mode side effects.

    Yields:
        None. The lock is held for the duration of the ``with`` body.

    The lock guards the entire read-modify-write sequence (header
    ensure, supersede walk, atomic rewrite, append) so two agents
    finishing in the same minute cannot lose an entry.
    """
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = jsonl_path.with_name(jsonl_path.name + ".lock")
    with lock_path.open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def _atomic_supersede_and_append(
    jsonl_path: Path,
    new_entry: dict[str, Any],
) -> None:
    """Rewrite the JSONL with optional supersede and the new entry, atomically.

    Args:
        jsonl_path: Path to the JSONL file. Must be a regular file the
            caller already protected with :func:`_locked`.
        new_entry: The new entry to append. Its ``session_date``,
            ``repo``, and ``session_id`` are used to mark any prior
            active entry with the same key as superseded.

    The function reads the existing file, finds the latest active
    entry for ``(session_date, repo)`` (if any), marks it as
    ``superseded_by`` the new entry's ``session_id``, appends the new
    entry, and writes the result to a temp file in the same directory
    before issuing a single ``os.replace``. Either the entire change
    lands or the file is unmodified; no SIGKILL window can produce a
    dangling supersede.
    """
    key = make_dedupe_key(new_entry)
    new_session_id = new_entry["session_id"]
    if not isinstance(new_session_id, str):
        msg = f"session_id must be str, got {type(new_session_id).__name__}"
        raise TypeError(msg)

    existing_lines: list[tuple[str, dict[str, Any] | None]] = []
    raw = jsonl_path.read_text(encoding="utf-8")
    for line in raw.splitlines(keepends=True):
        if not line.strip():
            existing_lines.append((line, None))
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            existing_lines.append((line, None))
            continue
        existing_lines.append((line, obj))

    target_idx: int | None = None
    target_session: str = ""
    for idx, (_, obj) in enumerate(existing_lines):
        if obj is None or obj.get("type") == "header":
            continue
        if make_dedupe_key(obj) != key:
            continue
        if obj.get("superseded_by") is not None:
            continue
        session_id = obj.get("session_id", "")
        if target_idx is None or session_id > target_session:
            target_idx = idx
            target_session = session_id

    if target_idx is not None:
        target_obj = existing_lines[target_idx][1]
        if target_obj is None:  # defensive; loop guarantees non-None
            msg = "internal: target entry resolved to None during supersede"
            raise RuntimeError(msg)
        target_obj["superseded_by"] = new_session_id
        existing_lines[target_idx] = (json.dumps(target_obj) + "\n", target_obj)

    body = "".join(line for line, _ in existing_lines)
    if body and not body.endswith("\n"):
        body += "\n"
    body += json.dumps(new_entry) + "\n"

    fd, tmp_path = tempfile.mkstemp(
        prefix=".master-log.", suffix=".tmp", dir=str(jsonl_path.parent)
    )
    try:
        os.close(fd)
        Path(tmp_path).write_text(body, encoding="utf-8")
        os.replace(tmp_path, jsonl_path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _invoke_renderer(jsonl_path: Path | None = None) -> int:
    """Invoke the Markdown renderer and return its exit code.

    Args:
        jsonl_path: Optional override of the source JSONL. When set,
            propagated to the renderer as ``--jsonl`` so it renders
            the same file the caller just updated.

    Returns:
        The renderer subprocess return code. Non-zero is surfaced to
        stderr so a stale ``master-log.md`` does not silently diverge
        from the JSONL source of truth.
    """
    args = [sys.executable, str(RENDERER_SCRIPT)]
    if jsonl_path is not None:
        args.extend(["--jsonl", str(jsonl_path)])
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        msg = (
            f"[{ts}] renderer exited with code {completed.returncode}; "
            f"master-log.md may be stale. stderr: {completed.stderr.strip()}"
        )
        print(f"WARNING: {msg}", file=sys.stderr)
    return completed.returncode


def append_entry(
    entry: dict[str, Any],
    jsonl_path: Path | None = None,
    *,
    render: bool = True,
) -> int:
    """Append a session entry to the master log, handling supersede.

    Args:
        entry: Parsed session entry dictionary conforming to the schema.
        jsonl_path: Optional override of the target JSONL path; defaults
            to the central master log resolved via repo discovery.
        render: When True (default), invoke the Markdown renderer against
            the same JSONL after the append. Tests that pass a custom
            jsonl_path keep this enabled so the matching Markdown is
            also produced.

    Returns:
        ``0`` on success. ``2`` when the append succeeded but the
        renderer exited non-zero (``master-log.md`` may be stale).

    Raises:
        SchemaError: If ``entry`` is missing required schema keys.
        TypeError: If ``session_id`` is not a string.
    """
    validate_entry(entry)
    target = jsonl_path or DEFAULT_JSONL

    with _locked(target):
        ensure_header(target)
        key = make_dedupe_key(entry)
        existing_keys = {
            make_dedupe_key(e)
            for e in load_entries(target)
            if e.get("superseded_by") is None
        }
        if key in existing_keys:
            _atomic_supersede_and_append(target, entry)
        else:
            with target.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")

    if not render:
        return 0
    render_rc = _invoke_renderer(jsonl_path=jsonl_path)
    if render_rc != 0:
        return 2
    return 0


def main() -> int:
    """Read a JSON entry from stdin and append it to the central log.

    Returns:
        ``0`` on success.
        ``1`` when stdin was empty or contained invalid JSON, or the
        entry failed schema validation.
        ``2`` when the append succeeded but the renderer reported a
        non-zero exit (``master-log.md`` may be stale).
    """
    raw = sys.stdin.read().strip()
    if not raw:
        print("ERROR: no JSON entry on stdin", file=sys.stderr)
        return 1
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON on stdin: {exc}", file=sys.stderr)
        return 1
    try:
        return append_entry(entry)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
