#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Consensus engine CLI: multi-model fan-out via OpenRouter.

Subcommands (all emit JSON on stdout):
    select    Build a band-filtered roster with role assignments for a level/domain.
    estimate  Cost preview for a level without live validation or API calls.
    run       Fan a prompt out to models in parallel; emit raw responses.
    refresh   Diff the curated dataset against the live OpenRouter catalog.

OPENROUTER_API_KEY must be set in the environment for the run subcommand.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_PATH = Path.home() / ".cache" / "consensus-skill" / "openrouter-models.json"
CACHE_TTL_SECONDS = 24 * 3600
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
EST_INPUT_TOKENS = 2000
EST_OUTPUT_TOKENS = 1500
LEVEL_COST_CAPS_USD = {1: 0.50, 2: 1.00, 3: 10.00}
LEVEL_TIER_COUNTS = {
    1: {"free": 3},
    2: {"free": 3, "economy": 3},
    3: {"free": 3, "economy": 3, "premium": 2},
}
TIER_FALLBACK_ORDER = {
    "free": ["free", "economy"],
    "economy": ["economy", "value"],
    "premium": ["premium", "value"],
}
REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0
FREE_COST_EPSILON = 1e-9


@dataclass
class Model:
    """One row of the curated model dataset."""

    name: str
    provider: str
    input_cost: float
    output_cost: float
    humaneval: float
    swe_bench: float
    context: int
    specialization: str


def emit(payload: dict, stream: TextIO | None = None) -> None:
    """Write a JSON payload to stdout (or the given stream)."""
    (stream or sys.stdout).write(json.dumps(payload, indent=2) + "\n")


def parse_context(value: str | int | float | None) -> int:
    """Convert context sizes like '131K' or '1M' to a token count.

    Args:
        value: A string like '131K', '1M', '200000', a numeric value, or None.

    Returns:
        Integer token count, or 0 if the value is None or cannot be parsed.
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().upper()
    multiplier = 1
    if text.endswith("K"):
        multiplier, text = 1_000, text[:-1]
    elif text.endswith("M"):
        multiplier, text = 1_000_000, text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def _parse_model_row(row: dict) -> Model | None:
    """Parse one CSV row into a Model, returning None if the row is malformed.

    Args:
        row: A dict from csv.DictReader representing one data row.

    Returns:
        A Model instance, or None if required fields are missing or invalid.
    """
    if not (row.get("model") or "").strip():
        return None
    try:
        return Model(
            name=row["model"],
            provider=row.get("provider", ""),
            input_cost=float(row.get("input_cost") or 0),
            output_cost=float(row.get("output_cost") or 0),
            humaneval=float(row.get("humaneval_score") or 0),
            swe_bench=float(row.get("swe_bench_score") or 0),
            context=parse_context(row.get("context", 0)),
            specialization=row.get("specialization", "general"),
        )
    except (ValueError, KeyError):
        return None


def load_models(csv_path: Path | None = None) -> list[Model]:
    """Load the curated model dataset from CSV, skipping malformed rows.

    Args:
        csv_path: Optional override path to the models CSV file.

    Returns:
        List of Model instances parsed from the CSV.
    """
    path = csv_path or DATA_DIR / "models.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return [m for row in rows if (m := _parse_model_row(row)) is not None]


def load_bands(path: Path | None = None) -> dict:
    """Load band criteria (cost tiers, org levels) from JSON.

    Args:
        path: Optional override path to the bands_config JSON file.

    Returns:
        Parsed bands configuration dictionary.
    """
    return json.loads((path or DATA_DIR / "bands_config.json").read_text())


def load_roles(path: Path | None = None) -> dict:
    """Load role definitions and per-domain level assignments from JSON.

    Args:
        path: Optional override path to the roles JSON file.

    Returns:
        Parsed roles configuration dictionary.
    """
    return json.loads((path or DATA_DIR / "roles.json").read_text())


def models_in_cost_tier(models: list[Model], tier: str, bands: dict) -> list[Model]:
    """Filter models to a cost tier band, sorted by benchmark scores descending.

    The free tier requires both input and output cost to be zero (within
    FREE_COST_EPSILON); other tiers compare input cost against the band's
    min/max.

    Args:
        models: List of Model instances to filter.
        tier: Cost tier name (e.g. 'free', 'economy', 'value', 'premium').
        bands: Loaded bands configuration (from load_bands).

    Returns:
        Filtered and sorted list of Model instances.
    """
    criteria = bands["cost_tier_bands"][tier]
    max_cost = criteria.get("max_cost")
    min_cost = criteria.get("min_cost")
    kept = []
    for m in models:
        if max_cost is not None:
            if max_cost == 0.0:
                # #ASSUME: curated free models carry costs of exactly 0; epsilon guards
                # against near-zero float artifacts if live pricing ever enters the CSV.
                # #VERIFY: refresh workflow flags any free-tier row with nonzero cost.
                if (
                    m.input_cost > FREE_COST_EPSILON
                    or m.output_cost > FREE_COST_EPSILON
                ):
                    continue
            elif m.input_cost > max_cost:
                continue
        if min_cost is not None and m.input_cost < min_cost:
            continue
        kept.append(m)
    return sorted(kept, key=lambda m: (-m.humaneval, -m.swe_bench))


def role_system_prompt(role: str, roles_data: dict) -> str:
    """Build the system prompt for a professional role.

    Unknown role names are treated as literal system prompts, which is how
    flexible-mode stances ("argue for", "argue against") are passed in.
    """
    definition = roles_data["role_definitions"].get(role)
    if definition is None:
        return role
    return (
        f"You are acting as a {role.replace('_', ' ')}.\n\n"
        f"**Your Focus:** {definition['focus']}\n\n"
        f"**Key Questions to Address:** {definition['questions']}\n\n"
        f"**Your Perspective:** {definition['perspective']}\n\n"
        "Instructions:\n"
        "1. Analyze the question from your professional role's perspective\n"
        "2. Address the key questions relevant to your expertise\n"
        "3. Identify risks, concerns, or opportunities within your domain\n"
        "4. Provide specific, actionable insights\n"
        "5. Be concise but thorough; focus on what matters most from your perspective"
    )


def estimate_model_cost(m: Model) -> float:
    """Estimate one consultation's cost in USD using assumed token counts."""
    return round(
        (m.input_cost * EST_INPUT_TOKENS + m.output_cost * EST_OUTPUT_TOKENS)
        / 1_000_000,
        6,
    )


def enforce_cost_cap(total: float, level: int | None, max_cost: float | None) -> None:
    """Exit with code 2 if the estimated cost exceeds the applicable cap.

    The explicit --max-cost flag overrides the per-level default cap.
    """
    cap = max_cost if max_cost is not None else LEVEL_COST_CAPS_USD.get(level or 0)
    if cap is not None and total > cap:
        emit(
            {
                "error": (
                    f"Estimated cost ${total:.4f} exceeds cap ${cap:.2f}. "
                    "Override with --max-cost if intended."
                )
            },
            stream=sys.stderr,
        )
        raise SystemExit(2)
