"""Render the compliance master JSONL log to a Markdown view.

Idempotent except for the rendered-at timestamp in the footer.
Called by the compliance-retrospective agent after every append and by
the compliance-rollup reconciler after backfill operations.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from claude_config.compliance.log_common import (
    load_entries,
    repo_root_from,
    resolve_canonical_per_key,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_REPO_ROOT = repo_root_from(Path(__file__))
DEFAULT_JSONL = _REPO_ROOT / "docs" / "compliance-reports" / "master-log.jsonl"
DEFAULT_MD = _REPO_ROOT / "docs" / "compliance-reports" / "master-log.md"


def _format_summary_header(entries: list[dict[str, Any]]) -> str:
    """Return the rollup header block.

    Date lines are always emitted Newest-before-Oldest regardless of
    whether the entry list is empty, so consumers can rely on a stable
    line order.
    """
    if not entries:
        return (
            "**Total sessions:** 0\n"
            "**Distinct repos:** 0\n"
            "**Newest entry:** n/a\n"
            "**Oldest entry:** n/a\n"
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
    """Return one Markdown month section with a totals row per entry.

    Entries are sorted by (session_date, repo) descending so the most
    recent activity appears at the top of each month.
    """
    lines = [f"\n## {month}\n", ""]
    lines.append(
        "| Date | Repo | Mode | Critical | Important | Suggested | Candidates | Reconciled | Report |"
    )
    lines.append(
        "|------|------|------|---------:|----------:|----------:|-----------:|:----------:|--------|"
    )

    by_date_then_repo = sorted(
        entries,
        key=lambda e: (e["session_date"], e["repo"]),
        reverse=True,
    )

    for e in by_date_then_repo:
        totals = cast("Mapping[str, int]", e.get("totals") or {})
        flag = "yes" if e.get("reconciled") else ""
        link = e.get("links", {}).get("lessons_learned", "")
        report = f"[report]({link})" if link else ""
        crit = totals.get("critical", 0)
        imp = totals.get("important", 0)
        sugg = totals.get("suggested", 0)
        cand = totals.get("unclassified_candidates", 0)
        row = f"| {e['session_date']} | {e['repo']} | {e['audit_mode']} | {crit} | {imp} | {sugg} | {cand} | {flag} | {report} |"
        lines.append(row)

    return "\n".join(lines) + "\n"


def render(jsonl_path: Path | None = None, md_path: Path | None = None) -> None:
    """Read JSONL at jsonl_path and write a Markdown view to md_path.

    Args:
        jsonl_path: Optional path to the source JSONL log. Defaults to
            the production master log under docs/compliance-reports/.
        md_path: Optional path to the output Markdown view. Defaults to
            the production master-log.md alongside the JSONL.

    The output is idempotent except for the rendered-at timestamp in
    the footer; rendering the same input twice produces identical
    bytes apart from that timestamp.
    """
    jsonl_path = jsonl_path or DEFAULT_JSONL
    md_path = md_path or DEFAULT_MD

    all_entries = load_entries(jsonl_path)
    canonical = resolve_canonical_per_key(all_entries)

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in canonical:
        month_key = e["session_date"][:7]
        by_month[month_key].append(e)

    purpose_line = (
        'purpose: "Fleet-wide rollup of per-repo compliance '
        'retrospectives and action items."\n'
    )
    parts = [
        "---\n",
        "title: Compliance Master Log\n",
        "schema_type: common\n",
        "status: published\n",
        "owner: engineering\n",
        purpose_line,
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
        f"\n---\n*Rendered {rendered_at} from {jsonl_path.name} by compliance_log_render.py.*\n"
    )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    """Entry point for CLI execution.

    Accepts optional ``--jsonl`` and ``--md`` overrides so callers can
    redirect the source and destination away from the production paths
    (used by tests and by the reconciler when ``--jsonl`` was supplied).
    """
    parser = argparse.ArgumentParser(description="Render compliance master log.")
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--md", type=Path, default=None)
    args = parser.parse_args()
    render(jsonl_path=args.jsonl, md_path=args.md)


if __name__ == "__main__":
    main()
