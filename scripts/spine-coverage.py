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
would only pressure people into mapping checks dishonestly. This extends to
the manifest read itself: a missing file, malformed YAML, a non-mapping
root, or an absent PyYAML dependency all degrade to a stderr warning and a
zero-check report instead of a crash, since a diagnostic that dies on a bad
input is worse than one that says plainly what it could not read.

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

# This report is a diagnostic that must never crash the caller. Deferred
# import so a missing PyYAML degrades to a stderr warning in load_checks()
# instead of failing the whole script at import time, mirroring the same
# guard in check-repo-compliance.py.
try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover - pyyaml is optional for this diagnostic
    _YAML_AVAILABLE = False

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

    Degrades to an empty list, with a warning on stderr, instead of raising
    when PyYAML is unavailable, the manifest file cannot be read, the YAML is
    malformed, or the parsed document is not a mapping. A crash here would
    contradict the module's documented contract of always exiting 0, and an
    empty list printed with no explanation would look like a clean "nothing
    mapped" result instead of "the manifest could not be read".

    Returns:
        Every check mapping under the ``checks`` key, or an empty list when
        the manifest could not be parsed.
    """
    if not _YAML_AVAILABLE:
        print(
            "warning: pyyaml is not installed, spine coverage cannot be "
            "computed; install pyyaml to restore this report",
            file=sys.stderr,
        )
        return []
    try:
        with MANIFEST_PATH.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except OSError as exc:
        print(
            f"warning: manifest at {MANIFEST_PATH} could not be read: {exc}",
            file=sys.stderr,
        )
        return []
    except yaml.YAMLError as exc:
        print(
            f"warning: manifest at {MANIFEST_PATH} is malformed YAML: {exc}",
            file=sys.stderr,
        )
        return []
    # safe_load returns whatever the document is: a list, a scalar, or None
    # for an empty file. Only a mapping has `.get`, so anything else must
    # exit here or the report dies on AttributeError instead of degrading to
    # a zero-check result.
    if not isinstance(data, dict):
        print(
            f"warning: manifest at {MANIFEST_PATH} has a non-mapping root "
            f"({type(data).__name__}), no checks loaded",
            file=sys.stderr,
        )
        return []
    checks = data.get("checks") or []
    # The root guard above stops one layer short: `checks: not-a-list` and a
    # list of bare scalars (`- CI-001` instead of `- id: CI-001`) both survive
    # it and then die on `.get` inside build_coverage. The second is a
    # plausible hand-edit, not a contrived input, so the contract is enforced
    # where it is declared rather than trusted downstream.
    if not isinstance(checks, list) or not all(
        isinstance(check, dict) for check in checks
    ):
        print(
            f"warning: manifest at {MANIFEST_PATH} has a `checks` value that is "
            "not a list of mappings, no checks loaded",
            file=sys.stderr,
        )
        return []
    return checks


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

    A manifest that cannot be read or parsed (missing file, malformed YAML,
    non-mapping root, or PyYAML absent) does not raise: ``load_checks``
    degrades to an empty list and prints a warning to stderr, and this
    function still renders and exits normally on the resulting zero-check
    report.

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
