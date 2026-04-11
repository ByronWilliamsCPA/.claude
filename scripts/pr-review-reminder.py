#!/usr/bin/env python3
"""pr-review-reminder.py.

UserPromptSubmit hook that detects when the user's prompt mentions a pull
request or asks for a review, and injects a system message reminding Claude
to ask the user whether they want the structured ``/code-review`` command
invoked explicitly.

Rationale: ``/code-review`` is a Claude Code plugin command (at
``.submodules/anthropics-plugins/plugins/code-review/``), not a skill. Commands
do not have auto-activation triggers like skills do, so prose phrasings such
as "review this PR" or "look at PR #14" will not automatically invoke the
structured 5-agent parallel review. This hook catches those cases and nudges
Claude to confirm with the user before doing an ad-hoc review.

Protocol: reads a JSON event from stdin, writes JSON to stdout with an
optional ``systemMessage`` field. Exits 0 always (never blocks the prompt).
The user can disable this hook by setting ``PR_REVIEW_REMINDER_DISABLED=1``
in the environment.

Installation: referenced from ``hooks.json`` under ``UserPromptSubmit``, so
``setup.sh`` merges it into ``~/.claude/settings.json`` on install.
"""

from __future__ import annotations

import json
import os
import re
import sys

# Strict GitHub PR URL pattern. Matches the canonical PR link format.
PR_URL_RE = re.compile(
    r"https?://github\.com/[^/\s]+/[^/\s]+/pull/\d+",
    re.IGNORECASE,
)

# Natural-language review-intent phrases. Each pattern is a regex intended
# to catch how a user would verbally ask for a PR review without invoking
# the slash command. Keep these narrow to minimize false positives.
PR_PHRASE_PATTERNS = [
    re.compile(r"\breview\s+(this\s+|the\s+)?(pull\s+request|pr\b)", re.IGNORECASE),
    re.compile(r"\blook\s+at\s+(this\s+|the\s+)?(pull\s+request|pr\s*#?\s*\d+)", re.IGNORECASE),
    re.compile(r"\bcheck\s+(this\s+|the\s+)?(pull\s+request|pr\s*#?\s*\d+)", re.IGNORECASE),
    re.compile(r"\breview\s+pr\s*#?\s*\d+", re.IGNORECASE),
    re.compile(r"\bpr\s+review\b", re.IGNORECASE),
]

# If the user already typed the slash command, stay silent. This matches
# ``/code-review`` optionally followed by arguments. Word-boundary anchored
# on the right via a lookahead so it does not match ``/code-reviewer`` or
# similar extended forms.
EXPLICIT_COMMAND_RE = re.compile(r"/code-review(?![a-zA-Z0-9_-])")

REMINDER_MESSAGE = (
    "[pr-review-reminder] The user's prompt mentions a pull request or asks "
    "for a review. The /code-review command is a Claude Code plugin command "
    "(at .submodules/anthropics-plugins/plugins/code-review/), not a skill, "
    "so prose phrasings do NOT auto-activate the structured 5-agent review "
    "pipeline. Before doing an ad-hoc review, ask the user explicitly: "
    '"Did you want me to run /code-review on this PR for the structured '
    '5-agent parallel review with confidence scoring?" If the user declines, '
    "proceed with a lightweight review using your own tools. If the user "
    "types /code-review themselves, this reminder is a false positive and "
    "should be ignored."
)


def _read_event() -> dict:
    """Read the hook event JSON from stdin, tolerating malformed input.

    Returns:
        The parsed event dict, or an empty dict if parsing fails.
    """
    try:
        data = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not data.strip():
        return {}
    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _extract_prompt(event: dict) -> str:
    """Extract the user prompt string from the hook event.

    Tries the common field names Claude Code and hookify use. Returns an
    empty string if no prompt is present.

    Args:
        event: The parsed hook event dictionary.

    Returns:
        The prompt string, or empty string if not found.
    """
    for key in ("user_prompt", "prompt", "userPrompt"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _should_remind(prompt: str) -> bool:
    """Decide whether to inject the reminder for this prompt.

    Returns False if the prompt is empty, already contains an explicit
    ``/code-review`` invocation, or does not match any PR-intent pattern.

    Args:
        prompt: The user's submitted prompt text.

    Returns:
        True if the reminder should be injected, False otherwise.
    """
    if not prompt:
        return False
    if EXPLICIT_COMMAND_RE.search(prompt):
        return False
    if PR_URL_RE.search(prompt):
        return True
    if any(pat.search(prompt) for pat in PR_PHRASE_PATTERNS):
        return True
    return False


def main() -> int:
    """Run the hook. Always exits 0; never blocks the prompt.

    Returns:
        Always 0.
    """
    if os.environ.get("PR_REVIEW_REMINDER_DISABLED") == "1":
        print(json.dumps({}))
        return 0

    event = _read_event()
    prompt = _extract_prompt(event)

    if _should_remind(prompt):
        print(json.dumps({"systemMessage": REMINDER_MESSAGE}))
    else:
        print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
