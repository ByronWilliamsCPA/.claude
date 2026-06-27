#!/usr/bin/env python3
"""Measure the two session-length signals from Claude Code transcripts.

Reads Claude Code transcript JSONL files and, for each main-thread assistant
turn, computes the context size carried, the fill percentage against the model's
window, the output produced, and the carry ratio (context tokens per output
token). From that it derives two independently-calibrated signals:

Setting 1, force compaction (within a session). The carry-ratio knee: the fill
percentage at which the smoothed carry ratio first reaches a multiple of its
early-session baseline, where a fresh session stops paying off. This informs the
compaction threshold (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`).

Setting 2, start a new session (across compactions). A compaction leaves no
marker record in the transcript, but it shows as a sustained drop in carried
context. Counting those drops per session gives how many compactions a session
typically absorbs before it was abandoned, which informs when to offer /handoff.

The window is auto-detected per session from the model id (1M for the current
Opus/Sonnet/Fable models, 200K for Haiku); override with --window. Sidechain
(sub-agent) turns are excluded so their smaller context does not masquerade as a
compaction.

See docs/development/session-length-trigger.md for the method and how to apply
the result.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

DEFAULT_GLOB = str(Path.home() / ".claude" / "projects" / "**" / "*.jsonl")
FALLBACK_WINDOW = 200_000

# Context window per model family, in tokens. Source: the claude-api skill's
# Models catalog (shared/models.md) / the Models API. The current Claude 4.x and
# Fable/Mythos 5 models expose a 1M window; Haiku 4.5 is 200K. Matched by prefix
# so dated snapshots (e.g. claude-haiku-4-5-20251001) still resolve.
MODEL_WINDOWS: dict[str, int] = {
    "claude-fable-5": 1_000_000,
    "claude-mythos-5": 1_000_000,
    "claude-opus-4-8": 1_000_000,
    "claude-opus-4-7": 1_000_000,
    "claude-opus-4-6": 1_000_000,
    "claude-opus-4-5": 1_000_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-haiku-4-5": 200_000,
}


@dataclass(frozen=True)
class AnalysisConfig:
    """Tunable thresholds for one analysis run."""

    window: int | None
    min_turns: int
    knee_mult: float
    smooth_window: int
    drop_threshold: int


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
    """Per-session summary: the knee fill (Setting 1) and compactions (Setting 2)."""

    name: str
    turns: int
    peak_fill: float
    inflection_fill: float | None
    window: int
    model: str | None
    n_compactions: int
    compaction_fills: list[float]


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
        default=None,
        help=(
            "Context window in tokens; overrides per-model auto-detect "
            f"(fallback {FALLBACK_WINDOW:,} when the model is unknown)"
        ),
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
        "--compaction-drop",
        type=int,
        default=50_000,
        help="Min context drop (tokens) that counts as a compaction (default: 50000)",
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


def window_for_model(model: str | None) -> int | None:
    """Return the context window for a model id, or None if unrecognized."""
    if not model:
        return None
    for prefix, window in MODEL_WINDOWS.items():
        if model.startswith(prefix):
            return window
    return None


def fmt_window(window: int) -> str:
    """Render a token window as a compact label such as '1M' or '200K'."""
    if window >= 1_000_000:
        return f"{window // 1_000_000}M"
    return f"{window // 1000}K"


def detect_model(path: str) -> str | None:
    """Return the model id from the first main-thread assistant turn, or None."""
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, TypeError):
                continue
            if not isinstance(record, dict) or record.get("type") != "assistant":
                continue
            if record.get("isSidechain"):
                continue
            message = record.get("message")
            if isinstance(message, dict):
                model = message.get("model")
                if isinstance(model, str):
                    return model
    return None


def iter_usage(path: str) -> Iterator[dict[str, object]]:
    """Yield the usage block of each main-thread assistant turn (skip sidechains)."""
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
            if record.get("type") != "assistant" or record.get("isSidechain"):
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
    if isinstance(value, int | float):
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


def find_compactions(turns: list[Turn], drop_threshold: int) -> list[int]:
    """Return indices where context dropped by >= drop_threshold and stayed down.

    A compaction summarizes history, so the carried context falls sharply and
    does not immediately recover. A one-turn dip that bounces straight back is
    not counted.
    """
    boundaries: list[int] = []
    for i in range(1, len(turns)):
        if turns[i].context_size - turns[i - 1].context_size > -drop_threshold:
            continue
        recovered = (
            i + 1 < len(turns)
            and turns[i + 1].context_size >= turns[i - 1].context_size - drop_threshold
        )
        if not recovered:
            boundaries.append(i)
    return boundaries


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


def resolve_window(window: int | None, model: str | None, name: str) -> int:
    """Resolve the window to use for one session, warning on an unknown model."""
    if window is not None:
        return window
    detected = window_for_model(model)
    if detected is not None:
        return detected
    print(
        f"warning: unknown model {model!r} for {name}; assuming "
        f"{FALLBACK_WINDOW:,}-token window (pass --window to override)",
        file=sys.stderr,
    )
    return FALLBACK_WINDOW


def analyze_session(path: str, cfg: AnalysisConfig) -> SessionResult | None:
    """Analyze one transcript file; return None if it has too few turns."""
    model = detect_model(path)
    name = Path(path).name
    resolved = resolve_window(cfg.window, model, name)
    turns = build_turns(path, resolved)
    if len(turns) < cfg.min_turns:
        return None
    peak_fill = max(t.fill for t in turns)
    if peak_fill > 1.0:
        print(
            f"warning: {name} peak fill {peak_fill * 100:.0f}% exceeds the "
            f"{resolved:,}-token window; the window is likely wrong for "
            f"{model!r} (pass --window)",
            file=sys.stderr,
        )
    boundaries = find_compactions(turns, cfg.drop_threshold)
    # The carry-ratio knee is measured on the first segment (before any
    # compaction reset) so it reflects when a fresh session stops paying off.
    knee_turns = turns[: boundaries[0]] if boundaries else turns
    return SessionResult(
        name=name,
        turns=len(turns),
        peak_fill=peak_fill,
        inflection_fill=find_inflection(knee_turns, cfg.knee_mult, cfg.smooth_window),
        window=resolved,
        model=model,
        n_compactions=len(boundaries),
        compaction_fills=[turns[b - 1].fill for b in boundaries],
    )


def quartiles(pct: list[float]) -> tuple[float, float, float]:
    """Return (p25, median, p75) of a list of values."""
    ordered = sorted(pct)
    median = statistics.median(ordered)
    if len(ordered) >= 2:
        q = statistics.quantiles(ordered, n=4)
        return q[0], median, q[2]
    return median, median, median


def recommend(fracs: list[float]) -> dict[str, float]:
    """Derive an offer floor and recommend line from knee fill fractions."""
    p25, median, p75 = quartiles([f * 100 for f in fracs])
    # Offer a little below p25; recommend near the median; never exceed the 80%
    # autocompact ceiling.
    return {
        "p25": p25,
        "median": median,
        "p75": p75,
        "offer_floor": max(0.0, min(p25 - 5.0, 75.0)),
        "recommend_line": min(median, 78.0),
    }


def pct_summary(pct: list[float]) -> dict[str, float]:
    """Return a p25/median/p75 summary of a list of percentages."""
    p25, median, p75 = quartiles(pct)
    return {"p25": p25, "median": median, "p75": p75}


def count_summary(counts: list[int]) -> dict[str, float] | None:
    """Summarize the compaction count across sessions, or None if empty."""
    if not counts:
        return None
    return {
        "min": min(counts),
        "median": statistics.median(counts),
        "max": max(counts),
        "mean": round(statistics.mean(counts), 2),
        "sessions_compacted": sum(1 for c in counts if c > 0),
        "total_sessions": len(counts),
    }


@dataclass
class Recommendation:
    """The two-setting recommendation assembled from all sessions."""

    setting1_knee: dict[str, float] | None
    setting1_compaction_fill: dict[str, float] | None
    setting2_compactions_per_session: dict[str, float] | None


def build_recommendation(results: list[SessionResult]) -> Recommendation:
    """Assemble the two-setting recommendation from all session results."""
    knee_fracs = [r.inflection_fill for r in results if r.inflection_fill is not None]
    comp_fill_pct = [f * 100 for r in results for f in r.compaction_fills]
    counts = [r.n_compactions for r in results]
    return Recommendation(
        setting1_knee=recommend(knee_fracs) if knee_fracs else None,
        setting1_compaction_fill=pct_summary(comp_fill_pct) if comp_fill_pct else None,
        setting2_compactions_per_session=count_summary(counts),
    )


def print_sessions(results: list[SessionResult]) -> None:
    """Print one compact line per session."""
    print(f"Analyzed {len(results)} session(s)\n")
    for r in sorted(results, key=lambda x: x.name):
        knee = f"{r.inflection_fill * 100:.0f}%" if r.inflection_fill else "none"
        print(
            f"  {r.name}: {r.turns} turns, {fmt_window(r.window)} window, "
            f"peak {r.peak_fill * 100:.0f}%, knee {knee}, "
            f"{r.n_compactions} compaction(s)"
        )


def print_setting1(
    knee: dict[str, float] | None, comp_fill: dict[str, float] | None
) -> None:
    """Print the force-compaction (Setting 1) signals."""
    print("Setting 1 - force compaction (within a session)")
    if knee is None:
        print("  carry-ratio knee: none detected (sessions stayed efficient or short)")
    else:
        print(
            f"  carry-ratio knee (fill where a fresh session stops paying off): "
            f"p25={knee['p25']:.0f}%  median={knee['median']:.0f}%  "
            f"p75={knee['p75']:.0f}%"
        )
        print(
            "    -> set the compaction threshold near this; "
            "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE is 80%, far above the knee on 1M windows"
        )
    if comp_fill is not None:
        print(
            f"  empirical: sessions actually compacted at fill "
            f"p25={comp_fill['p25']:.0f}%  median={comp_fill['median']:.0f}%  "
            f"p75={comp_fill['p75']:.0f}%"
        )


def print_setting2(summary: dict[str, float] | None) -> None:
    """Print the new-session (Setting 2) signal."""
    print("Setting 2 - start a new session (across compactions)")
    if summary is None or summary["total_sessions"] == 0:
        print("  no sessions analyzed")
        return
    print(
        f"  compactions per session: min={summary['min']:g}  "
        f"median={summary['median']:g}  max={summary['max']:g}  "
        f"mean={summary['mean']:g}"
    )
    print(
        f"  {summary['sessions_compacted']:g} of {summary['total_sessions']:g} "
        f"sessions compacted at least once"
    )
    print(
        "  -> offer /handoff + a fresh session after about the median compaction "
        "count, gated on a finished task unit"
    )


def print_human(results: list[SessionResult], rec: Recommendation) -> None:
    """Print the per-session lines and the two-setting recommendation."""
    print_sessions(results)
    print()
    print_setting1(rec.setting1_knee, rec.setting1_compaction_fill)
    print()
    print_setting2(rec.setting2_compactions_per_session)


def main() -> int:
    """Entry point: analyze sessions and print the two-setting recommendation."""
    args = parse_args()
    cfg = AnalysisConfig(
        window=args.window,
        min_turns=args.min_turns,
        knee_mult=args.knee_mult,
        smooth_window=args.smooth,
        drop_threshold=args.compaction_drop,
    )
    paths = expand_paths(args.paths)
    if not paths:
        print("No transcript files matched. Pass paths or check the default glob.")
        return 1

    results: list[SessionResult] = []
    for path in paths:
        result = analyze_session(path, cfg)
        if result is not None:
            results.append(result)

    if not results:
        print(f"No sessions with >= {cfg.min_turns} assistant turns matched.")
        return 1

    rec = build_recommendation(results)
    if args.json:
        payload = {"sessions": [vars(r) for r in results], "recommendation": vars(rec)}
        print(json.dumps(payload, indent=2))
        return 0

    print_human(results, rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
