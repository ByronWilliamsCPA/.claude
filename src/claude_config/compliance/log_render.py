"""Render the compliance master JSONL log to a Markdown view.

Idempotent except for the rendered-at timestamp in the footer.
Called by the compliance-retrospective agent after every append and by
the compliance-rollup reconciler after backfill operations.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_config.compliance.log_common import (
    load_entries,
    repo_root_from,
    resolve_canonical_per_key,
)

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
        raw_totals = e.get("totals")
        totals: Mapping[str, int] = (
            raw_totals if isinstance(raw_totals, Mapping) else {}
        )
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
        jsonl_path (Path | None): Optional path to the source JSONL log.
            Defaults to the production master log under
            docs/compliance-reports/.
        md_path (Path | None): Optional path to the output Markdown view.
            Defaults to the production master-log.md alongside the JSONL.

    The output is idempotent except for the rendered-at timestamp in
    the footer; rendering the same input twice produces identical
    bytes apart from that timestamp.
    """
    # #CRITICAL security: render() is the real filesystem sink (read_text via
    # load_entries, mkdir, write_text). It does NOT confine its path arguments;
    # confinement lives in main()'s _validated_override gate. Direct callers that
    # forward untrusted path overrides MUST pre-validate them against a trusted
    # root, or they reopen the S8707 path-injection hole the CLI gate closed.
    # #VERIFY any new caller of render() passing externally-influenced paths runs
    # _validated_override (or equivalent containment) first.
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


def _validated_override(
    parser: argparse.ArgumentParser,
    candidate: Path | None,
    *,
    base_dir: Path,
) -> Path | None:
    """Canonicalize a CLI path override and confirm it stays in ``base_dir``.

    The ``--jsonl`` and ``--md`` overrides are untrusted input when this
    CLI is driven by an automated agent: a prompt-injected agent could
    pass ``../../../etc/passwd`` to read or clobber files outside the
    repository. Following the secure-by-design order (normalize, then
    validate, then use), the candidate is resolved with
    :meth:`~pathlib.Path.resolve` (collapsing ``..`` segments and
    symlinks) and rejected unless the result lands inside the repository
    root.

    Args:
        parser (argparse.ArgumentParser): The active parser, used to emit
            a usage error and exit non-zero when the path escapes
            ``base_dir``.
        candidate (Path | None): The raw ``Path`` produced by argparse, or
            ``None`` to accept the production default downstream.
        base_dir (Path): The trusted root every override must stay within.

    Returns:
        Path | None: The canonicalized path, or ``None`` when ``candidate``
            is ``None``.
    """
    if candidate is None:
        return None
    base = base_dir.resolve()
    # ``base / candidate`` resolves a relative override under the repo
    # root; an absolute candidate is kept as-is by pathlib and still has
    # to clear the containment check below.
    resolved = (base / candidate).resolve()
    if not resolved.is_relative_to(base):
        parser.error(f"path '{candidate}' escapes repository root {base}")
    return resolved


def main() -> None:
    """Entry point for CLI execution.

    Accepts optional ``--jsonl`` and ``--md`` overrides so callers can
    redirect the source and destination away from the production paths
    (used by tests and by the reconciler when ``--jsonl`` was supplied).
    Both overrides are canonicalized and confined to the repository root
    before any filesystem access, so a malformed or hostile argument
    cannot escape into the wider filesystem.
    """
    parser = argparse.ArgumentParser(description="Render compliance master log.")
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--md", type=Path, default=None)
    args = parser.parse_args()
    jsonl_path = _validated_override(parser, args.jsonl, base_dir=_REPO_ROOT)
    md_path = _validated_override(parser, args.md, base_dir=_REPO_ROOT)
    render(jsonl_path=jsonl_path, md_path=md_path)


if __name__ == "__main__":
    main()
