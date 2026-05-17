#!/usr/bin/env python3
"""Render the compliance master JSONL log to a Markdown view.

Pure transform: JSONL in, Markdown out. Called by the
compliance-retrospective agent after every append and by the
compliance-rollup reconciler after backfill operations.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.compliance_log_common import (
    load_entries,
    resolve_canonical_per_key,
)

DEFAULT_JSONL = (
    Path.home() / ".claude" / "docs" / "compliance-reports" / "master-log.jsonl"
)
DEFAULT_MD = Path.home() / ".claude" / "docs" / "compliance-reports" / "master-log.md"


def _format_summary_header(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return (
            "**Total sessions:** 0\n"
            "**Distinct repos:** 0\n"
            "**Oldest entry:** n/a\n"
            "**Newest entry:** n/a\n"
            "**Open fleet actions:** 0\n"
        )

    dates = sorted(e["session_date"] for e in entries)
    repos = {e["repo"] for e in entries}
    open_fleet = sum(
        1
        for e in entries
        for proposal in e.get("fleet_action_proposals", [])
        if proposal
    )
    return (
        f"**Total sessions:** {len(entries)}\n"
        f"**Distinct repos:** {len(repos)}\n"
        f"**Newest entry:** {dates[-1]}\n"
        f"**Oldest entry:** {dates[0]}\n"
        f"**Open fleet actions:** {open_fleet}\n"
    )


def _format_month_section(month: str, entries: list[dict[str, Any]]) -> str:
    lines = [f"\n## {month}\n", ""]
    lines.append(
        "| Date | Repo | Mode | Critical | Important | Suggested | "
        "Candidates | Reconciled | Report |"
    )
    lines.append(
        "|------|------|------|---------:|----------:|----------:|"
        "-----------:|:----------:|--------|"
    )

    by_date_then_repo = sorted(
        entries,
        key=lambda e: (e["session_date"], e["repo"]),
        reverse=True,
    )

    for e in by_date_then_repo:
        t = e.get("totals", {})
        flag = "yes" if e.get("reconciled") else ""
        link = e.get("links", {}).get("lessons_learned", "")
        report = f"[report]({link})" if link else ""
        lines.append(
            f"| {e['session_date']} | {e['repo']} | "
            f"{e['audit_mode']} | "
            f"{t.get('critical', 0)} | {t.get('important', 0)} | "
            f"{t.get('suggested', 0)} | "
            f"{t.get('unclassified_candidates', 0)} | {flag} | {report} |"
        )

    return "\n".join(lines) + "\n"


def render(jsonl_path: Path | None = None, md_path: Path | None = None) -> None:
    """Read JSONL, write Markdown view. Pure function on filesystem."""
    jsonl_path = jsonl_path or DEFAULT_JSONL
    md_path = md_path or DEFAULT_MD

    all_entries = load_entries(jsonl_path)
    canonical = resolve_canonical_per_key(all_entries)

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in canonical:
        month_key = e["session_date"][:7]
        by_month[month_key].append(e)

    parts = [
        "---\n",
        "title: Compliance Master Log\n",
        "schema_type: common\n",
        "status: published\n",
        "owner: core-maintainer\n",
        'purpose: "Fleet-wide rollup of per-repo compliance retrospectives and action items."\n',
        "tags:\n",
        "  - compliance\n",
        "---\n\n",
        _format_summary_header(canonical),
    ]
    parts.extend(
        _format_month_section(month, by_month[month])
        for month in sorted(by_month.keys(), reverse=True)
    )

    rendered_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    parts.append(
        f"\n---\n*Rendered {rendered_at} "
        f"from {jsonl_path.name} by compliance_log_render.py.*\n"
    )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    """Entry point for CLI execution against the default paths."""
    render()


if __name__ == "__main__":
    main()
