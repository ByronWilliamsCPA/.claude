"""Self-consistency gate for the six ``owasp-*`` specialist agent definitions.

Each agent lists the OWASP categories it owns in a ``## Your Categories`` table
and defines greppable signals in a ``### Detection Patterns`` section. Nothing
previously tied the two together, and they had drifted badly: 37 of 60 listed
categories carried no detection pattern at all, and ``owasp-citizen`` had no
detection-patterns section whatsoever.

That drift is not cosmetic. A category listed in the table but absent from the
patterns section makes a review return clean while a reader concludes the
category was evaluated. Two of the five failures in the audit that motivated the
``operations`` domain (log redaction and attack alerting) fall under
``A09:2025``, which was listed by ``owasp-web`` and had zero detection patterns.
A check that is named but cannot fail is worse than a check that is absent: an
absent check leaves a visible hole, a hollow one manufactures false coverage and
stops people looking.

The rule these tests enforce, per
``.claude/standards/owasp-specialist-agents-spec.md``: every category in an
agent's categories table must either carry at least one detection pattern, or be
explicitly annotated ``NOT STATICALLY DETECTABLE`` with a pointer to the control
that does cover it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "agents"

# The six OWASP specialists. `owasp-dispatch` is a router with no categories
# table of its own and is deliberately excluded.
OWASP_AGENTS: tuple[str, ...] = (
    "owasp-web",
    "owasp-api",
    "owasp-llm",
    "owasp-ml",
    "owasp-agent",
    "owasp-citizen",
)

# Table rows look like `| A01:2025 | Broken Access Control | CWE-200, ... |` or
# `| ML01 | Data Poisoning | ... |`. Capture the bare ID, dropping any `:YYYY`
# suffix, because the detection-pattern labels use the bare form.
_TABLE_ROW = re.compile(r"^\|\s*([A-Z]{1,4}\d{2})(?::\d{4})?\s*\|")

# Pattern labels look like `**A01 Broken Access Control:**` or
# `**A09 Security Logging and Alerting Failures:** NOT STATICALLY DETECTABLE`.
_PATTERN_LABEL = re.compile(r"^\*\*([A-Z]{1,4}\d{2})(?::\d{4})?\s")

pytestmark = pytest.mark.unit


def _agent_text(name: str) -> str:
    """Read one agent definition.

    Args:
        name: Agent file stem, e.g. ``owasp-web``.

    Returns:
        Full file contents.
    """
    return (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def categories_in_table(text: str) -> set[str]:
    """Return the bare category IDs listed in the ``## Your Categories`` table.

    Anchored to the categories section so tables elsewhere in the document
    cannot contribute rows. An unanchored scan would make the coverage test
    below unfalsifiable.

    Args:
        text: Full agent definition contents.

    Returns:
        Bare category IDs, e.g. ``{"A01", "A02", ...}``. Empty when the section
        is absent.
    """
    start = text.find("## Your Categories")
    if start == -1:
        return set()
    end = text.find("\n## ", start + 1)
    section = text[start:] if end == -1 else text[start:end]
    return {
        match.group(1)
        for line in section.splitlines()
        if (match := _TABLE_ROW.match(line))
    }


def detection_patterns_section(text: str) -> str:
    """Return the ``### Detection Patterns`` section body, or an empty string.

    Anchoring matters: scanning the whole document lets a bolded category label
    written anywhere (a prose aside, a mode section, an example) satisfy the
    coverage gate without a real pattern entry. That would make the gate
    unfalsifiable, which is the exact defect it exists to catch.

    Args:
        text: Full agent definition contents.

    Returns:
        The section text, or ``""`` when the heading is absent.
    """
    start = text.find("### Detection Patterns")
    if start == -1:
        return ""
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def categories_with_patterns(text: str) -> set[str]:
    """Return the bare category IDs that carry a detection-pattern entry.

    Args:
        text: Full agent definition contents.

    Returns:
        Bare category IDs appearing as a bolded pattern label inside the
        detection-patterns section.
    """
    return {
        match.group(1)
        for line in detection_patterns_section(text).splitlines()
        if (match := _PATTERN_LABEL.match(line))
    }


def undetectable_categories(text: str) -> set[str]:
    """Return category IDs explicitly annotated ``NOT STATICALLY DETECTABLE``.

    Args:
        text: Full agent definition contents.

    Returns:
        Bare category IDs whose pattern label carries the annotation.
    """
    return {
        match.group(1)
        for line in detection_patterns_section(text).splitlines()
        if (match := _PATTERN_LABEL.match(line)) and "NOT STATICALLY DETECTABLE" in line
    }


@pytest.mark.parametrize("agent", OWASP_AGENTS)
def test_every_listed_category_has_a_detection_pattern(agent: str) -> None:
    """No category is listed without a pattern or an explicit undetectable note.

    This is the hollow-category guard. A listed category with neither is a named
    check that cannot fail.
    """
    text = _agent_text(agent)
    listed = categories_in_table(text)
    assert listed, f"{agent}: no categories table found, or it parsed empty"

    covered = categories_with_patterns(text)
    hollow = sorted(listed - covered)
    assert not hollow, (
        f"{agent}: categories listed in the table with no detection pattern and "
        f"no NOT STATICALLY DETECTABLE annotation: {hollow}. Add patterns, or "
        f"annotate them and point at the control that does cover them."
    )


@pytest.mark.parametrize("agent", OWASP_AGENTS)
def test_no_detection_pattern_for_an_unlisted_category(agent: str) -> None:
    """Patterns never reference a category the table does not list.

    Catches the reverse drift: a renumbered or retired category whose pattern
    entry was left behind, which would report findings under an ID the agent no
    longer owns.
    """
    text = _agent_text(agent)
    orphans = sorted(categories_with_patterns(text) - categories_in_table(text))
    assert not orphans, (
        f"{agent}: detection patterns for categories absent from the "
        f"categories table: {orphans}"
    )


@pytest.mark.parametrize("agent", OWASP_AGENTS)
def test_undetectable_categories_name_the_covering_control(agent: str) -> None:
    """An undetectable annotation must point somewhere, not just opt out.

    ``NOT STATICALLY DETECTABLE`` with no pointer is a licence to skip the
    category, which is the same false-coverage outcome as leaving it hollow. The
    annotation is only acceptable when it names the control that does cover the
    gap, so a reader can follow it.
    """
    text = _agent_text(agent)
    undetectable = undetectable_categories(text)
    if not undetectable:
        pytest.skip(f"{agent} annotates no categories as undetectable")

    lines = text.splitlines()
    offenders: list[str] = []
    for index, line in enumerate(lines):
        match = _PATTERN_LABEL.match(line)
        if not match or "NOT STATICALLY DETECTABLE" not in line:
            continue
        # Look at the entry body, up to the next bolded label or heading.
        body: list[str] = []
        for following in lines[index + 1 :]:
            if _PATTERN_LABEL.match(following) or following.startswith("#"):
                break
            body.append(following)
        if "Covered by:" not in "\n".join(body):
            offenders.append(match.group(1))
    assert not offenders, (
        f"{agent}: categories annotated NOT STATICALLY DETECTABLE with no "
        f"'Covered by:' pointer to the control that does cover them: "
        f"{sorted(offenders)}"
    )


def test_a09_is_annotated_undetectable_and_points_at_the_operations_domain() -> None:
    """A09:2025 is the regression case that motivated this whole gate.

    Logging and alerting failures cannot be detected by reading a source tree:
    no static analysis observes a log stream or an outbound alert channel. A09
    was listed by ``owasp-web`` with zero detection patterns, and two of the
    five failures in the motivating audit fall under it. It must be annotated,
    and it must point at the ``operations`` domain that actually covers it.
    """
    text = _agent_text("owasp-web")
    assert "A09" in undetectable_categories(text), (
        "owasp-web must annotate A09 as NOT STATICALLY DETECTABLE; source "
        "analysis cannot observe a log stream or an alerting channel"
    )
    # Scope the OPS- assertion to the A09 entry body. A file-wide search would
    # be satisfied by any other category's pointer, so the intended regression
    # (deleting A09's pointer) would still pass.
    lines = text.splitlines()
    a09_body: list[str] = []
    for index, line in enumerate(lines):
        match = _PATTERN_LABEL.match(line)
        if not (match and match.group(1) == "A09"):
            continue
        for following in lines[index + 1 :]:
            if _PATTERN_LABEL.match(following) or following.startswith("#"):
                break
            a09_body.append(following)
        break
    assert "OPS-" in "\n".join(a09_body), (
        "owasp-web's A09 annotation body must point at the operations domain "
        "(OPS-* checks) that covers the gap"
    )


def test_parsers_are_anchored_and_falsifiable() -> None:
    """Guards the guards: the parsers must not match unrelated content.

    Both helpers above were written to be anchored. If either ever widens, every
    coverage test in this module silently stops failing, which would recreate
    the exact defect the module exists to catch.
    """
    doc = (
        "## Your Categories\n\n"
        "| ID | Category | Key CWEs |\n"
        "|----|----------|----------|\n"
        "| A01:2025 | Broken Access Control | CWE-200 |\n"
        "| A02:2025 | Security Misconfiguration | CWE-16 |\n"
        "\n## Some Other Section\n\n"
        "| ID | Thing |\n"
        "|----|-------|\n"
        "| ZZ99 | should not be picked up |\n"
        "\n### Detection Patterns\n\n"
        "**A01 Broken Access Control:**\n\n"
        "- a signal\n"
        "\n## Mode: review-tests\n\n"
        "**A02 Security Misconfiguration:** NOT STATICALLY DETECTABLE\n\n"
        "- Covered by: OPS-005\n"
    )
    assert categories_in_table(doc) == {"A01", "A02"}, (
        "categories parser must read only the Your Categories section"
    )
    # A02's label and its OPS- pointer sit OUTSIDE the detection section, so
    # neither parser may see them. Before scoping, both did, which meant a
    # deleted pattern could be satisfied by an unrelated mention elsewhere.
    assert categories_with_patterns(doc) == {"A01"}, (
        "pattern parser must ignore labels outside the Detection Patterns section"
    )
    assert undetectable_categories(doc) == set()
    assert "OPS-" not in detection_patterns_section(doc)
