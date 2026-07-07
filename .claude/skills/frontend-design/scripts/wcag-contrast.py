#!/usr/bin/env python3
"""Compute WCAG 2.x contrast ratios for hex color pairs.

Exists because an LLM estimating contrast by eye produced five undetected AA
failures in a real design task (2026-07-07 A/B trial, see
docs/tool-evals/claude-design-system-prompt.md). Contrast is a deterministic
computation; verify it with this script instead of asserting a ratio from
memory or visual estimation.

Usage:
    wcag-contrast.py FG BG [--large] [--label TEXT]
        Check one foreground/background hex pair.

    wcag-contrast.py --batch pairs.json
        Check many pairs at once. pairs.json is a JSON array of objects:
        [{"fg": "#2c1a0e", "bg": "#f8f3e8", "large": false, "label": "body text"}, ...]
        Include every text/background AND UI-component/state color pairing
        actually used in the deliverable -- resting, hover, active, and focus
        states each get their own entry, not just the resting state.

Exit code is 1 if any checked pair fails its required threshold (AA: 4.5:1
normal text, 3:1 large text/UI components), 0 if all pass. Always prints one
line per pair with the computed ratio, threshold, and pass/fail.
"""

import argparse
import json
import sys


def _linearize(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = _linearize(r), _linearize(g), _linearize(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_pair(fg: str, bg: str, large: bool, label: str) -> bool:
    ratio = contrast_ratio(fg, bg)
    threshold = 3.0 if large else 4.5
    passed = ratio >= threshold
    status = "PASS" if passed else "FAIL"
    tag = f" ({label})" if label else ""
    print(f"{status}: {fg} on {bg}{tag} = {ratio:.2f}:1 (need >= {threshold}:1)")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fg", nargs="?", help="Foreground hex color")
    parser.add_argument("bg", nargs="?", help="Background hex color")
    parser.add_argument(
        "--large",
        action="store_true",
        help="Use the 3:1 large-text/UI-component threshold",
    )
    parser.add_argument("--label", default="", help="Context label for this pair")
    parser.add_argument(
        "--batch", help="Path to a JSON file of {fg, bg, large, label} objects"
    )
    args = parser.parse_args()

    if args.batch:
        with open(args.batch) as f:
            pairs = json.load(f)
        results = [
            check_pair(p["fg"], p["bg"], p.get("large", False), p.get("label", ""))
            for p in pairs
        ]
        sys.exit(0 if all(results) else 1)

    if not args.fg or not args.bg:
        parser.error("fg and bg are required unless --batch is used")

    ok = check_pair(args.fg, args.bg, args.large, args.label)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
