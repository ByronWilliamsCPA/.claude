#!/usr/bin/env python3
"""Report standards-manifest coverage against the assurance spine.

The manifest is a check catalog: it enumerates checks that exist. The assurance
spine (`.claude/standards/assurance-spine.md`) is a coverage denominator: it
enumerates the places a system can fail. A catalog cannot tell you what it is
missing; only the denominator can.

This script joins the two on the `sp_category` field and prints the empty cells.
A spine category with zero manifest checks is a blind spot, and the point of the
spine is that a blind spot should be visible as a category with no rows rather
than as a question nobody asked.

Exit code is 0 always: this is a diagnostic, not a gate. Uncovered categories
are expected while the mapping is incomplete, and failing the build on them
would only pressure people into mapping checks dishonestly.

Usage:
  python3 scripts/spine-coverage.py
  python3 scripts/spine-coverage.py --output json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

MANIFEST_PATH = Path(__file__).parent.parent / "docs/standards-manifest.yaml"

# SP-01..SP-17 with the failure each category names. Kept in sync with
# .claude/standards/assurance-spine.md, which is the source of truth.
SPINE: dict[str, str] = {
    "SP-01": "Identity, Authentication, Session Lifecycle",
    "SP-02": "Authorization and Tenancy Isolation",
    "SP-03": "Input Validation, Encoding, Injection",
    "SP-04": "Business Logic and Abuse Resistance",
    "SP-05": "Client-Side Storage, Offline Sync, Client Surface",
    "SP-06": "API Surface, Egress, SSRF",
    "SP-07": "File, Object Storage, Media",
    "SP-08": "Cryptography, Secrets, Key Management, Transport",
    "SP-09": "Runtime Configuration and Control-Plane Drift",
    "SP-10": "Build and Software Supply Chain",
    "SP-11": "Logging, Audit Integrity, Alerting, Incident Response",
    "SP-12": "Data Lifecycle, Rights, Processors, Transfers",
    "SP-13": "Protected-Population Duties and Age-Appropriate Design",
    "SP-14": "AI and Model Layer: Generation, Prompts, Providers, Output",
    "SP-15": "Human Decision Gates and Publication Integrity",
    "SP-16": "Availability, Resilience, Recovery",
    "SP-17": "Assurance Validity and Change Lifecycle",
}


def load_checks() -> list[dict[str, Any]]:
    """Parse the manifest and return its check list.

    Returns:
        Every check mapping under the ``checks`` key.
    """
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data.get("checks", []) or []


def category_text(check: dict[str, Any]) -> str:
    """Return a check's ``sp_category`` normalized to a comparable string.

    Absence is the only thing that maps to ``""``. A falsey-but-present value
    (``0``, ``False``) is a malformed mapping, not a missing one, so it must
    survive normalization and be reported as invalid rather than quietly
    joining the absent pile. Every caller classifies through this one function
    so the mapped total, the invalid list, and the rendered rows cannot
    disagree about what a given value means.

    Args:
        check: A manifest check mapping.

    Returns:
        The stripped string form of ``sp_category``, or ``""`` when the field
        is absent, null, or blank.
    """
    category = check.get("sp_category")
    return "" if category is None else str(category).strip()


def build_coverage(checks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group check IDs by their declared spine category.

    Args:
        checks: Manifest check mappings.

    Returns:
        Mapping of every SP category to the check IDs claiming it, including
        categories with an empty list.
    """
    coverage: dict[str, list[str]] = defaultdict(list)
    for check in checks:
        # Only known categories count. An unrecognised value (a typo such as
        # SP-99) would otherwise inflate the mapped total while never appearing
        # in any row, hiding an invalid mapping behind a better-looking number.
        category = category_text(check)
        if category in SPINE:
            coverage[category].append(str(check.get("id")))
    return {sp: sorted(coverage.get(sp, [])) for sp in SPINE}


def mapped_count(checks: list[dict[str, Any]]) -> int:
    """Count checks whose ``sp_category`` names a real spine category.

    Args:
        checks: Manifest check mappings.

    Returns:
        The number of checks that land in a row of the report.
    """
    return sum(1 for check in checks if category_text(check) in SPINE)


def invalid_categories(checks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Return check IDs grouped by any ``sp_category`` value not in the spine.

    Args:
        checks: Manifest check mappings.

    Returns:
        Mapping of unrecognised category value to the check IDs using it.
    """
    invalid: dict[str, list[str]] = defaultdict(list)
    for check in checks:
        category = category_text(check)
        if category and category not in SPINE:
            invalid[category].append(str(check.get("id")))
    return {k: sorted(v) for k, v in sorted(invalid.items())}


def render(checks: list[dict[str, Any]], coverage: dict[str, list[str]]) -> list[str]:
    """Render the human-readable coverage report.

    Args:
        checks: Manifest check mappings.
        coverage: Output of :func:`build_coverage`.

    Returns:
        Report lines.
    """
    mapped = mapped_count(checks)
    classes = Counter(
        str(c.get("verification_class", "UNDECLARED"))
        for c in checks
        if category_text(c) in SPINE
    )
    invalid = invalid_categories(checks)
    header = (
        f"manifest checks: {len(checks)}   mapped to a spine category: "
        f"{mapped}   unmapped: {len(checks) - mapped}"
    )
    lines = [
        "ASSURANCE SPINE COVERAGE",
        "=" * 72,
        header,
        "",
        "Verification class of mapped checks:",
    ]
    lines.extend(f"  {cls:<16} {n:>3}" for cls, n in sorted(classes.items()))
    lines.extend(
        ["", f"{'Category':<8} {'Checks':>6}  Failure mode / covering checks", "-" * 72]
    )
    for sp, name in SPINE.items():
        ids = coverage[sp]
        marker = " " if ids else "!"
        lines.append(f"{marker}{sp:<7} {len(ids):>6}  {name}")
        if ids:
            lines.append(f"{'':>16}{', '.join(ids)}")
    uncovered = [sp for sp, ids in coverage.items() if not ids]
    lines.extend(
        [
            "-" * 72,
            (
                f"{len(SPINE) - len(uncovered)}/{len(SPINE)} spine categories "
                f"have at least one mapped check."
            ),
            "",
            "UNCOVERED (marked ! above): these are blind spots, not passes.",
        ]
    )
    lines.extend(f"  {sp}  {SPINE[sp]}" for sp in uncovered)
    if invalid:
        lines.extend(["", "INVALID sp_category VALUES (not in SP-01..SP-17):"])
        lines.extend(f"  {value}  {ids}" for value, ids in invalid.items())
    lines.extend(
        [
            "",
            "A category with no rows is the visible form of a question nobody asked.",
            "Mapping more existing checks will close some of these on paper; the ones",
            "that stay empty after mapping are real gaps.",
        ]
    )
    return lines


def main() -> int:
    """Print the spine coverage report.

    Returns:
        Always 0. This is a diagnostic, not a gate.
    """
    parser = argparse.ArgumentParser(description="Assurance spine coverage report")
    parser.add_argument("--output", choices=["table", "json"], default="table")
    args = parser.parse_args()

    checks = load_checks()
    coverage = build_coverage(checks)

    if args.output == "json":
        print(
            json.dumps(
                {
                    "total_checks": len(checks),
                    "mapped_checks": mapped_count(checks),
                    "invalid_categories": invalid_categories(checks),
                    "coverage": coverage,
                    "uncovered": [sp for sp, ids in coverage.items() if not ids],
                },
                indent=2,
            )
        )
    else:
        print("\n".join(render(checks, coverage)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
