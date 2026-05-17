# scripts/compliance_log_common.py
"""Shared helpers for the compliance master log."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION: int = 1

DedupeKey = tuple[str, str]


def make_dedupe_key(entry: dict[str, Any]) -> DedupeKey:
    """Return (session_date, repo) for use as a dedupe key."""
    return (entry["session_date"], entry["repo"])


def load_entries(jsonl_path: Path) -> list[dict[str, Any]]:
    """Load JSONL entries, skipping the header sentinel line.

    Returns an empty list if the file does not exist.
    Raises ValueError on malformed JSON.
    """
    if not jsonl_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if obj.get("type") == "header":
            continue
        entries.append(obj)
    return entries


def resolve_canonical_per_key(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select the canonical entry per (date, repo) key.

    Rules:
    1. Discard entries whose ``superseded_by`` is non-null.
    2. Group remaining entries by (session_date, repo).
    3. Within each group, the canonical entry is the one with the
       lexicographically greatest ``session_id``.
    """
    active = [e for e in entries if e.get("superseded_by") is None]

    by_key: dict[DedupeKey, dict[str, Any]] = {}
    for entry in active:
        key = make_dedupe_key(entry)
        existing = by_key.get(key)
        if existing is None or entry["session_id"] > existing["session_id"]:
            by_key[key] = entry

    return list(by_key.values())
