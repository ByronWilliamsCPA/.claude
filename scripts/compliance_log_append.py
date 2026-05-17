#!/usr/bin/env python3
"""Append a JSON entry to the compliance master log, with supersede handling.

Reads a single JSON object from stdin and:
1. Resolves the central master-log.jsonl path via repo discovery.
2. If (session_date, repo) already exists, marks the existing entry
   superseded_by the new session_id (atomic rewrite via temp file).
3. Appends the new entry (atomic append for sub-PIPE_BUF writes).
4. Invokes the renderer to regenerate master-log.md.

Intended to be invoked by the compliance-retrospective agent at the
end of every audit session. Decouples the agent prompt from the
relative-path trap.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.compliance_log_common import (
    SCHEMA_VERSION,
    load_entries,
    make_dedupe_key,
    repo_root_from,
)

_REPO_ROOT = repo_root_from(Path(__file__))
DEFAULT_JSONL = _REPO_ROOT / "docs" / "compliance-reports" / "master-log.jsonl"
RENDERER_SCRIPT = Path(__file__).resolve().parent / "compliance_log_render.py"


def _ensure_header(jsonl_path: Path) -> None:
    """Write a header sentinel line if the target file does not yet exist."""
    if jsonl_path.exists():
        return
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    header = {
        "type": "header",
        "schema_version": SCHEMA_VERSION,
        "created": "<seeded-by-append>",
    }
    jsonl_path.write_text(json.dumps(header) + "\n", encoding="utf-8")


def _rewrite_with_supersede(
    jsonl_path: Path,
    key: tuple[str, str],
    new_session_id: str,
) -> None:
    """Mark the prior entry with this key as superseded_by new_session_id.

    Reads the entire file, finds the matching active entry (latest by
    session_id with superseded_by==None), updates it, and rewrites the
    file via temp file + atomic rename.
    """
    lines = jsonl_path.read_text(encoding="utf-8").splitlines(keepends=True)
    parsed: list[tuple[str, dict[str, object] | None]] = []
    for line in lines:
        if not line.strip():
            parsed.append((line, None))
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            parsed.append((line, None))
            continue
        parsed.append((line, obj))

    target_idx: int | None = None
    target_session: str = ""
    for idx, (_, obj) in enumerate(parsed):
        if obj is None or obj.get("type") == "header":
            continue
        if make_dedupe_key(obj) != key:
            continue
        if obj.get("superseded_by") is not None:
            continue
        session_id = obj["session_id"]
        if target_idx is None or session_id > target_session:
            target_idx = idx
            target_session = session_id

    if target_idx is None:
        return  # nothing to supersede

    obj = parsed[target_idx][1]
    assert obj is not None
    obj["superseded_by"] = new_session_id
    parsed[target_idx] = (json.dumps(obj) + "\n", obj)

    fd, tmp_path = tempfile.mkstemp(
        prefix=".master-log.", suffix=".tmp", dir=str(jsonl_path.parent)
    )
    os.close(fd)
    Path(tmp_path).write_text("".join(line for line, _ in parsed), encoding="utf-8")
    os.replace(tmp_path, jsonl_path)


def _invoke_renderer() -> None:
    """Invoke the Markdown renderer; failures are non-fatal for append."""
    subprocess.run(  # noqa: S603 -- static args
        [sys.executable, str(RENDERER_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )


def append_entry(entry: dict[str, object], jsonl_path: Path | None = None) -> None:
    """Append a session entry to the master log, handling supersede.

    Args:
        entry: Parsed session entry dictionary conforming to the schema.
        jsonl_path: Optional override of the target JSONL path; defaults
            to the central master log resolved via repo discovery.
    """
    target = jsonl_path or DEFAULT_JSONL
    _ensure_header(target)

    key = make_dedupe_key(entry)
    new_session_id = entry["session_id"]

    existing_keys = {
        make_dedupe_key(e)
        for e in load_entries(target)
        if e.get("superseded_by") is None
    }
    if key in existing_keys:
        assert isinstance(new_session_id, str)
        _rewrite_with_supersede(target, key, new_session_id)

    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    _invoke_renderer()


def main() -> int:
    """Read a JSON entry from stdin and append it to the central log."""
    raw = sys.stdin.read().strip()
    if not raw:
        print("ERROR: no JSON entry on stdin", file=sys.stderr)
        return 1
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON on stdin: {exc}", file=sys.stderr)
        return 1
    append_entry(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
