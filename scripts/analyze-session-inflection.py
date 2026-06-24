#!/usr/bin/env python3
"""Locate the context-fill inflection point in Claude Code sessions.

Reads Claude Code transcript JSONL files and, for each assistant turn, computes
the context size carried, the fill percentage against the window, the output
produced, and the carry ratio (context tokens per output token). The inflection
point is the fill percentage at which the smoothed carry ratio first reaches a
multiple of its early-session baseline: the knee where a session stops paying
off. Aggregated across sessions, the output recommends a threshold band for the
CLAUDE.md "Session length" trigger.

See docs/development/session-length-trigger.md for the method and how to apply
the result.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

DEFAULT_GLOB = str(Path.home() / ".claude" / "projects" / "**" / "*.jsonl")
DEFAULT_WINDOW = 200_000


@dataclass
class Turn:
    """One assistant model call and its derived context-cost metrics."""

    index: int
    context_size: int
    fill: float
    output_tokens: int
    carry_ratio: float


@dataclass
class SessionResult:
    """Per-session summary including the detected inflection fill, if any."""

    name: str
    turns: int
    peak_fill: float
    inflection_fill: float | None


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help=f"Transcript JSONL paths or globs (default: {DEFAULT_GLOB})",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=DEFAULT_WINDOW,
        help=f"Context window size in tokens (default: {DEFAULT_WINDOW})",
    )
    parser.add_argument(
        "--min-turns",
        type=int,
        default=8,
        help="Skip sessions with fewer assistant turns (default: 8)",
    )
    parser.add_argument(
        "--knee-mult",
        type=float,
        default=2.0,
        help="Carry-ratio multiple over baseline that marks the knee (default: 2.0)",
    )
    parser.add_argument(
        "--smooth",
        type=int,
        default=3,
        help="Rolling-mean window for the carry ratio (default: 3)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    return parser.parse_args()


def expand_paths(patterns: list[str]) -> list[str]:
    """Expand glob patterns into a sorted, de-duplicated list of file paths."""
    if not patterns:
        patterns = [DEFAULT_GLOB]
    found: set[str] = set()
    for pattern in patterns:
        found.update(glob(pattern, recursive=True))
    return sorted(found)


def iter_usage(path: str) -> Iterator[dict[str, object]]:
    """Yield the usage block of each assistant turn in a transcript file."""
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, TypeError):
                continue
            if not isinstance(record, dict):
                continue
            if record.get("type") != "assistant":
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if isinstance(usage, dict):
                yield usage


def _as_int(value: object) -> int:
    """Coerce a JSON numeric value to int; treat missing or odd values as 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def smooth(values: list[float], window: int) -> list[float]:
    """Return a trailing rolling mean of values over the given window."""
    if window <= 1:
        return values
    out: list[float] = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1) : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def build_turns(path: str, window: int) -> list[Turn]:
    """Compute per-turn context-cost metrics for one transcript file."""
    turns: list[Turn] = []
    for index, usage in enumerate(iter_usage(path)):
        context_size = (
            _as_int(usage.get("input_tokens"))
            + _as_int(usage.get("cache_read_input_tokens"))
            + _as_int(usage.get("cache_creation_input_tokens"))
        )
        output_tokens = _as_int(usage.get("output_tokens"))
        if context_size <= 0:
            continue
        turns.append(
            Turn(
                index=index,
                context_size=context_size,
                fill=context_size / window,
                output_tokens=output_tokens,
                carry_ratio=context_size / max(output_tokens, 1),
            )
        )
    return turns


def find_inflection(
    turns: list[Turn], knee_mult: float, smooth_window: int
) -> float | None:
    """Return the fill fraction at the carry-ratio knee, or None if not found."""
    if len(turns) < 4:
        return None
    smoothed = smooth([t.carry_ratio for t in turns], smooth_window)
    baseline_n = max(3, len(turns) // 4)
    baseline = statistics.median(smoothed[:baseline_n])
    if baseline <= 0:
        return None
    threshold = knee_mult * baseline
    for i in range(baseline_n, len(turns)):
        if smoothed[i] >= threshold:
            return turns[i].fill
    return None


def analyze_session(
    path: str, window: int, min_turns: int, knee_mult: float, smooth_window: int
) -> SessionResult | None:
    """Analyze one transcript file; return None if it has too few turns."""
    turns = build_turns(path, window)
    if len(turns) < min_turns:
        return None
    inflection = find_inflection(turns, knee_mult, smooth_window)
    return SessionResult(
        name=Path(path).name,
        turns=len(turns),
        peak_fill=max(t.fill for t in turns),
        inflection_fill=inflection,
    )


def recommend(inflections: list[float]) -> dict[str, float]:
    """Derive an offer floor and recommend line from inflection fills."""
    pct = sorted(f * 100 for f in inflections)
    median = statistics.median(pct)
    if len(pct) >= 2:
        quartiles = statistics.quantiles(pct, n=4)
        p25, p75 = quartiles[0], quartiles[2]
    else:
        p25 = p75 = median
    # Offer a little below p25; recommend near the median; never exceed the 80%
    # autocompact ceiling.
    return {
        "p25": p25,
        "median": median,
        "p75": p75,
        "offer_floor": max(0.0, min(p25 - 5.0, 75.0)),
        "recommend_line": min(median, 78.0),
    }


def main() -> int:
    """Entry point: analyze sessions and print the threshold recommendation."""
    args = parse_args()
    paths = expand_paths(args.paths)
    if not paths:
        print("No transcript files matched. Pass paths or check the default glob.")
        return 1

    results: list[SessionResult] = []
    for path in paths:
        result = analyze_session(
            path, args.window, args.min_turns, args.knee_mult, args.smooth
        )
        if result is not None:
            results.append(result)

    if not results:
        print(f"No sessions with >= {args.min_turns} assistant turns matched.")
        return 1

    inflections = [r.inflection_fill for r in results if r.inflection_fill is not None]
    rec = recommend(inflections) if inflections else None

    if args.json:
        print(
            json.dumps(
                {
                    "sessions": [vars(r) for r in results],
                    "recommendation": rec,
                },
                indent=2,
            )
        )
        return 0

    print(f"Analyzed {len(results)} session(s); window = {args.window:,} tokens\n")
    print(f"{'session':<40} {'turns':>5} {'peak':>6} {'inflection':>10}")
    print("-" * 64)
    for r in sorted(results, key=lambda x: x.name):
        infl = f"{r.inflection_fill * 100:.0f}%" if r.inflection_fill else "none"
        print(f"{r.name:<40} {r.turns:>5} {r.peak_fill * 100:>5.0f}% {infl:>10}")

    print()
    if rec is None:
        print("No inflection detected in any session (sessions stayed efficient).")
        print("Re-run after longer sessions accumulate, or lower --knee-mult.")
        return 0

    print(
        f"Inflection fill across {len(inflections)} session(s): "
        f"p25={rec['p25']:.0f}%  median={rec['median']:.0f}%  p75={rec['p75']:.0f}%"
    )
    print(
        "Suggested band for CLAUDE.md 'Session length' "
        "(keep both under the 80% autocompact ceiling):"
    )
    print(f"  - offer the handoff from ~{rec['offer_floor']:.0f}% fill")
    print(f"  - recommend the break by ~{rec['recommend_line']:.0f}% fill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
