"""Shared helpers for the compliance master log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from claude_config.common.output import err

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION: int = 1

DedupeKey = tuple[str, str]

# Fields every persisted entry must carry. The append path validates
# this set up front so schema drift surfaces with a clear error rather
# than an opaque KeyError deep in the rewrite path.
REQUIRED_ENTRY_KEYS: frozenset[str] = frozenset(
    {"schema_version", "session_date", "session_id", "repo"}
)


class SchemaError(ValueError):
    """Raised when an entry is missing required schema fields."""


def repo_root_from(script_path: Path) -> Path:
    """Resolve the repo root by searching upward for ``pyproject.toml``.

    Args:
        script_path: A path inside the repository, typically a module's
            ``__file__``. It is resolved through symlinks first so the
            search works whether the caller runs from ``~/.claude/`` or a
            direct clone.

    Returns:
        The nearest ancestor directory that contains ``pyproject.toml``.

    Raises:
        FileNotFoundError: If no ``pyproject.toml`` marker exists in any
            ancestor. Every real caller (the renderer under
            ``src/claude_config/compliance/`` and the shims under
            ``scripts/``) resolves inside the repo, whose root carries
            ``pyproject.toml``, so a missing marker signals a broken
            deployment. Failing loudly is preferred to silently rendering
            into a guessed directory.
    """
    resolved = script_path.resolve()
    for parent in resolved.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    msg = f"repo root (pyproject.toml) not found above {resolved}"
    raise FileNotFoundError(msg)


def make_dedupe_key(entry: dict[str, Any]) -> DedupeKey:
    """Return ``(session_date, repo)`` for use as a dedupe key.

    Args:
        entry: Parsed session entry; must carry ``session_date`` and
            ``repo`` keys.

    Returns:
        The ``(session_date, repo)`` tuple identifying the entry's dedupe
        group.
    """
    return (entry["session_date"], entry["repo"])


def validate_entry(entry: dict[str, Any]) -> None:
    """Check that an entry carries every required schema field.

    Args:
        entry: Parsed session entry dictionary.

    Raises:
        SchemaError: If any of :data:`REQUIRED_ENTRY_KEYS` is missing
            from ``entry``. The exception message names the missing
            keys so callers can render a useful error to the agent.
    """
    missing = sorted(REQUIRED_ENTRY_KEYS - entry.keys())
    if missing:
        msg = f"entry missing required schema field(s): {', '.join(missing)}"
        raise SchemaError(msg)


def ensure_header(jsonl_path: Path) -> None:
    """Write a header sentinel line if the target file does not yet exist.

    Args:
        jsonl_path: Path to the target JSONL file.

    The header records the current ``schema_version`` and a UTC
    creation date so a fresh log carries a real timestamp on day one.
    Used by both the append and reconcile paths so the two producers
    cannot drift on header content (a historical bug).
    """
    if jsonl_path.exists():
        return
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    header = {
        "type": "header",
        "schema_version": SCHEMA_VERSION,
        "created": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
    }
    jsonl_path.write_text(json.dumps(header) + "\n", encoding="utf-8")


def load_entries(
    jsonl_path: Path,
    *,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """Load JSONL entries, skipping the header sentinel line.

    Args:
        jsonl_path: Path to the JSONL master log.
        strict: When True, any malformed JSON line raises ``ValueError``
            with file:line context. When False (default), malformed
            lines are skipped with a single ``WARNING:`` to stderr so
            one bad row does not wedge appends downstream.

    Returns:
        List of entry dicts, header excluded. Empty list if the file
        does not exist.

    Raises:
        ValueError: When ``strict=True`` and a JSON line cannot be
            parsed; the message names the file and the 1-based line
            number so callers can point operators at the offending row.
    """
    if not jsonl_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line_num, raw in enumerate(
        jsonl_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            msg = f"{jsonl_path}:{line_num}: malformed JSON: {exc}"
            if strict:
                raise ValueError(msg) from exc
            err(f"WARNING: {msg}")
            continue
        if obj.get("type") == "header":
            continue
        entries.append(obj)
    return entries


def resolve_canonical_per_key(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select the canonical entry per ``(session_date, repo)`` key.

    Args:
        entries: All loaded entries, including any that have been
            superseded.

    Returns:
        One canonical entry per ``(session_date, repo)`` group. Entries
        whose ``superseded_by`` is non-null are discarded first; within
        each remaining group the entry with the lexicographically
        greatest ``session_id`` is chosen.
    """
    active = [e for e in entries if e.get("superseded_by") is None]

    by_key: dict[DedupeKey, dict[str, Any]] = {}
    for entry in active:
        key = make_dedupe_key(entry)
        existing = by_key.get(key)
        if existing is None or entry["session_id"] > existing["session_id"]:
            by_key[key] = entry

    return list(by_key.values())
