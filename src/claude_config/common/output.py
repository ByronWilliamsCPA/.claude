"""Byte-stable stdout and stderr writers for CLI entrypoints.

These replace bare ``print`` calls, which the strict ``src`` ruleset bans via
``T20``, while preserving exact output bytes. Each writer appends a single
trailing newline and performs no wrapping or styling, so payloads piped to
other tools are unchanged from the previous ``print`` behavior.
"""

from __future__ import annotations

import sys


def out(message: str = "") -> None:
    """Write ``message`` and a trailing newline to standard output.

    Args:
        message: Payload line to emit to stdout.
    """
    sys.stdout.write(f"{message}\n")


def err(message: str = "") -> None:
    """Write ``message`` and a trailing newline to standard error.

    Args:
        message: Diagnostic line to emit to stderr.
    """
    sys.stderr.write(f"{message}\n")
