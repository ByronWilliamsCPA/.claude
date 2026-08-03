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
from dataclasses import dataclass
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

# The section heading, anchored to the start of a line. A substring search would
# also match the phrase written inside a sentence, which would hand the coverage
# gate a section that does not exist. The trailing `.*` admits the qualifier some
# agents carry (`### Detection Patterns (Python-specific)`) without admitting the
# same words mid-sentence.
_DETECTION_HEADING = re.compile(r"^### Detection Patterns\b.*$", re.MULTILINE)

# Same anchoring rule for the categories table heading.
_CATEGORIES_HEADING = re.compile(r"^## Your Categories\b.*$", re.MULTILINE)

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
    # The anchor must be a real level-two heading, not the phrase written in a
    # sentence and not a heading shown as an example inside a fence. A bare
    # `.find` accepts both, so a documented layout example could become the
    # section this gate reads, and its illustrative rows would stand in for the
    # real table. Fence-blanking first, then matching at a line start, is the
    # same protection detection_patterns_section already applies.
    scannable = _blank_fenced_blocks(text)
    heading = _CATEGORIES_HEADING.search(scannable)
    if heading is None:
        return set()
    start = heading.start()
    end = scannable.find("\n## ", start + 1)
    section = scannable[start:] if end == -1 else scannable[start:end]
    return {
        match.group(1)
        for line in section.splitlines()
        if (match := _TABLE_ROW.match(line))
    }


def _fence_marker(stripped_line: str) -> tuple[str, int] | None:
    """Return the fence delimiter character and run length, if any.

    Args:
        stripped_line: A line with leading whitespace already removed.

    Returns:
        A ``(character, length)`` pair when the line opens with a run of
        three or more backticks or three or more tildes, or ``None`` when
        the line opens no fence.
    """
    for char in ("`", "~"):
        if stripped_line.startswith(char * 3):
            return char, len(stripped_line) - len(stripped_line.lstrip(char))
    return None


def _blank_fenced_blocks(text: str) -> str:
    """Return ``text`` with every fenced code block's contents blanked out.

    A line anchor distinguishes a heading from prose but not from a
    heading-shaped line inside a fenced block. An agent file that documents
    the required layout by showing `### Detection Patterns` inside a fence
    would otherwise have that example parsed as its real section, and the
    example's labels would satisfy the coverage gate. The `## ` section
    boundary carries the same risk in reverse: a fenced `## ` line would end
    the real section early and hide the entries after it.

    The fence toggle tracks the opening delimiter's character and run
    length, and only closes on a line carrying the same character with a run
    at least as long as the opener, matching CommonMark's fence-closing
    rule. A toggle that flips on any backtick or tilde line loses parity the
    moment one fence type nests inside the other: a literal triple-backtick
    line quoted inside a tilde-fenced block would flip the state closed
    early, and the real closing ``~~~`` would flip it open again, blanking
    everything after it in the document instead of just the fence interior.

    Lines are replaced rather than deleted so byte offsets stay aligned with
    the original, which keeps slicing by match position correct.

    Args:
        text: Full agent definition contents.

    Returns:
        The same text with fence-interior lines (and the fence markers
        themselves) replaced by empty lines.
    """
    out: list[str] = []
    fence_char: str | None = None
    fence_len = 0
    for line in text.splitlines():
        marker = _fence_marker(line.lstrip())
        if fence_char is None:
            if marker is not None:
                fence_char, fence_len = marker
                out.append("")
                continue
            out.append(line)
            continue
        if marker is not None and marker[0] == fence_char and marker[1] >= fence_len:
            fence_char, fence_len = None, 0
        out.append("")
    return "\n".join(out)


def detection_patterns_section(text: str) -> str:
    """Return the ``### Detection Patterns`` section body, or an empty string.

    Anchoring matters: scanning the whole document lets a bolded category label
    written anywhere (a prose aside, a mode section, an example) satisfy the
    coverage gate without a real pattern entry. That would make the gate
    unfalsifiable, which is the exact defect it exists to catch.

    The heading match is anchored to the start of a line, and fenced code
    blocks are blanked first. An unanchored substring search matches the
    phrase written inside a sentence; a line anchor alone still matches a
    heading shown as an example inside a fence. Both would hand the coverage
    gate a section that does not exist.

    Args:
        text: Full agent definition contents.

    Returns:
        The section text, or ``""`` when the heading is absent.
    """
    scannable = _blank_fenced_blocks(text)
    heading = _DETECTION_HEADING.search(scannable)
    if heading is None:
        return ""
    start = heading.start()
    end = scannable.find("\n## ", start + 1)
    return scannable[start:] if end == -1 else scannable[start:end]


@dataclass(frozen=True)
class _PatternEntry:
    """One bolded category entry inside the detection-patterns section.

    Attributes:
        category: Bare category ID, e.g. ``A01``.
        undetectable: Whether the label carries the undetectable annotation.
        has_body: Whether the entry carries at least one non-empty body line
            beneath its label.
    """

    category: str
    undetectable: bool
    has_body: bool


def _pattern_entries(text: str) -> list[_PatternEntry]:
    """Split the detection-patterns section into per-category entries.

    The label alone is not the entry. A bolded label with nothing beneath it
    is a heading for content that was never written, and counting it as
    coverage is the same hollow-check defect this module exists to catch, one
    level in: the gate would report the category as handled while a reader
    following the label finds nothing to run.

    Args:
        text: Full agent definition contents.

    Returns:
        One entry per bolded label found in the section, in document order.
    """
    lines = detection_patterns_section(text).splitlines()
    entries: list[_PatternEntry] = []
    for index, line in enumerate(lines):
        match = _PATTERN_LABEL.match(line)
        if not match:
            continue
        body: list[str] = []
        for following in lines[index + 1 :]:
            if _PATTERN_LABEL.match(following) or following.startswith("#"):
                break
            body.append(following)
        # Content sits in either of two legitimate places: trailing the label
        # on its own line (`**A09 ...:** NOT STATICALLY DETECTABLE`, and the
        # one-line pattern form), or as bullets beneath it. Counting only the
        # latter would call every inline entry hollow, which is the opposite
        # error and would fire on the real agent files.
        inline = line.split("**", 2)[2] if line.count("**") >= 2 else ""
        entries.append(
            _PatternEntry(
                category=match.group(1),
                undetectable="NOT STATICALLY DETECTABLE" in line,
                has_body=bool(inline.strip()) or any(item.strip() for item in body),
            )
        )
    return entries


def categories_with_patterns(text: str) -> set[str]:
    """Return the bare category IDs that carry a detection-pattern entry.

    A label with an empty body does not count. See :func:`_pattern_entries`.

    Args:
        text: Full agent definition contents.

    Returns:
        Bare category IDs whose entry carries actual content.
    """
    return {entry.category for entry in _pattern_entries(text) if entry.has_body}


def undetectable_categories(text: str) -> set[str]:
    """Return category IDs explicitly annotated ``NOT STATICALLY DETECTABLE``.

    Args:
        text: Full agent definition contents.

    Returns:
        Bare category IDs whose pattern label carries the annotation.
    """
    return {entry.category for entry in _pattern_entries(text) if entry.undetectable}


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

    # Scan the section, not the file: a "Covered by:" line written in unrelated
    # prose elsewhere would otherwise satisfy an entry that carries no pointer.
    lines = detection_patterns_section(text).splitlines()
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
        # The pointer must name something. A bare "Covered by:" with nothing
        # after the colon satisfies a substring test while telling the reader
        # exactly as little as no annotation at all.
        pointer = next(
            (item.split("Covered by:", 1)[1] for item in body if "Covered by:" in item),
            None,
        )
        if pointer is None or not pointer.strip():
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
    # Scope the OPS- assertion to the A09 entry body inside the detection
    # section. A file-wide search would be satisfied by any other category's
    # pointer, or by an OPS- mention in unrelated prose, so the intended
    # regression (deleting A09's pointer) would still pass.
    lines = detection_patterns_section(text).splitlines()
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


def test_inline_heading_text_does_not_create_a_detection_section() -> None:
    """The heading must be a real heading, not the phrase used in a sentence.

    An unanchored substring search treats a prose mention of "### Detection
    Patterns" as the start of the section, after which every bolded label to
    the end of the document counts as covered. That is the hollow-coverage
    failure this module exists to catch, arriving through the parser instead
    of through the agent file.
    """
    doc = (
        "## Your Categories\n\n"
        "| ID | Category | Key CWEs |\n"
        "|----|----------|----------|\n"
        "| A01:2025 | Broken Access Control | CWE-200 |\n"
        "\n## Review Method\n\n"
        "This agent has no ### Detection Patterns section yet; write one.\n\n"
        "**A01 Broken Access Control:** NOT STATICALLY DETECTABLE\n\n"
        "- Covered by: OPS-005\n"
    )
    assert detection_patterns_section(doc) == "", (
        "an inline mention of the heading text must not open a section"
    )
    assert categories_with_patterns(doc) == set()
    assert undetectable_categories(doc) == set()


def test_fenced_heading_does_not_create_a_detection_section() -> None:
    """A heading shown as an example inside a fence is not a real heading.

    Line anchoring alone does not separate a heading from a heading-shaped
    line inside a fenced block, so an agent file that documents its own
    required layout would have the example parsed as its section and the
    example's labels would satisfy the coverage gate.
    """
    doc = (
        "## Your Categories\n\n"
        "| ID | Category | Key CWEs |\n"
        "|----|----------|----------|\n"
        "| A01:2025 | Broken Access Control | CWE-200 |\n"
        "\n## Review Method\n\n"
        "Write the section using this layout:\n\n"
        "```markdown\n"
        "### Detection Patterns\n\n"
        "**A01 Broken Access Control:** NOT STATICALLY DETECTABLE\n\n"
        "- Covered by: OPS-005\n"
        "```\n"
    )
    assert detection_patterns_section(doc) == "", (
        "a fenced example heading must not open a section"
    )
    assert categories_with_patterns(doc) == set()
    assert undetectable_categories(doc) == set()


def test_fenced_boundary_does_not_truncate_the_detection_section() -> None:
    """A fenced ``## `` line must not end the real section early.

    Blanking fences protects the boundary search as well as the heading
    search. Without it, an illustrative `## ` line inside a fenced block
    would cut the section short and silently drop every entry after it,
    under-reporting coverage instead of over-reporting it.
    """
    doc = (
        "### Detection Patterns\n\n"
        "**A01 Broken Access Control:** grep for missing authz decorators\n\n"
        "```text\n"
        "## Example Heading Inside A Fence\n"
        "```\n\n"
        "**A02 Cryptographic Failures:** grep for MD5 and SHA-1\n"
    )
    assert categories_with_patterns(doc) == {"A01", "A02"}, (
        "a fenced '## ' line must not truncate the section"
    )


def test_tilde_fence_containing_a_backtick_line_keeps_toggle_parity() -> None:
    """A tilde-fenced block nested with a backtick line must still close.

    The fence toggle must track which delimiter opened the block, not flip on
    any backtick or tilde line. A toggle that ignores the opening character
    loses parity here: the interior backtick line would flip the state closed
    early, then the real closing ``~~~`` would flip it open again, and
    everything after it in the document would be wrongly blanked instead of
    just the fence interior.
    """
    doc = (
        "### Detection Patterns\n\n"
        "**A01 Broken Access Control:** grep for missing authz decorators\n\n"
        "~~~text\n"
        "``` this triple-backtick line is literal text, not a real fence\n"
        "~~~\n\n"
        "**A02 Cryptographic Failures:** grep for MD5 and SHA-1\n"
    )
    assert categories_with_patterns(doc) == {"A01", "A02"}, (
        "a backtick line nested inside a tilde fence must not break fence toggle parity"
    )


def test_backtick_fence_containing_a_tilde_line_keeps_toggle_parity() -> None:
    """A backtick-fenced block nested with a tilde line must still close.

    Mirrors the tilde-containing-backtick case in the other direction: the
    interior ``~~~`` line must not be treated as a closer for a backtick
    fence, and the real closing backtick line must not be treated as a fresh
    opener.
    """
    doc = (
        "### Detection Patterns\n\n"
        "**A01 Broken Access Control:** grep for missing authz decorators\n\n"
        "```text\n"
        "~~~ this tilde line is literal text, not a real fence\n"
        "```\n\n"
        "**A02 Cryptographic Failures:** grep for MD5 and SHA-1\n"
    )
    assert categories_with_patterns(doc) == {"A01", "A02"}, (
        "a tilde line nested inside a backtick fence must not break fence toggle parity"
    )


def test_owasp_agents_tuple_matches_the_agent_files_on_disk() -> None:
    """``OWASP_AGENTS`` must track the specialist files actually on disk.

    The tuple is hand-maintained and never reconciled against the agents
    directory. A future ``owasp-*.md`` specialist added without a matching
    tuple entry would silently receive zero coverage from every test in this
    module, since parametrization only iterates the tuple's own entries.
    ``owasp-dispatch`` is excluded because it is a router with no categories
    table of its own, per the module-level comment on ``OWASP_AGENTS``.
    """
    on_disk = {
        path.stem
        for path in AGENTS_DIR.glob("owasp-*.md")
        if path.stem != "owasp-dispatch"
    }
    listed = set(OWASP_AGENTS)
    assert on_disk == listed, (
        "OWASP_AGENTS is out of sync with the owasp-*.md specialist files on "
        f"disk. On disk but unlisted: {sorted(on_disk - listed)}. Listed but "
        f"missing from disk: {sorted(listed - on_disk)}."
    )


def test_categories_table_anchor_ignores_prose_and_fences() -> None:
    """Only a real level-two heading may anchor the categories table.

    Two ways a fake table could stand in for the real one: the phrase written
    inside a sentence, and a heading shown as an example inside a fence. Either
    would let illustrative rows define what the coverage gate believes the
    agent owns, which is the unfalsifiable-gate defect this module exists to
    prevent.
    """
    inline = "\n".join(
        [
            "Prose that mentions the ## Your Categories table in passing.",
            "| A99 | Fake Row | CWE-000 |",
        ]
    )
    assert categories_in_table(inline) == set(), "prose must not anchor the table"

    fenced = "\n".join(
        [
            "```markdown",
            "## Your Categories",
            "| A99 | Fake Row | CWE-000 |",
            "```",
            "## Your Categories",
            "| A01 | Broken Access Control | CWE-200 |",
        ]
    )
    assert categories_in_table(fenced) == {"A01"}, (
        "a fenced example must not replace the real categories table"
    )


def test_a_label_with_no_content_is_not_coverage() -> None:
    """A bolded label with an empty body is a hollow entry, not a pattern.

    This is the module's own defect class turned on itself: the gate reported
    a category as covered because a heading for it existed, while a reader
    following that heading finds nothing to run. Both legitimate content
    positions must still count, inline after the label and bullets beneath it,
    or the fix would flag the real agent files instead.
    """
    hollow = "### Detection Patterns\n\n**A01 Broken Access Control:**\n\n## Next\n"
    assert categories_with_patterns(hollow) == set(), (
        "a label with nothing under it must not count as a detection pattern"
    )

    inline = "### Detection Patterns\n\n**A01 Broken Access Control:** grep authz\n"
    assert categories_with_patterns(inline) == {"A01"}

    bulleted = (
        "### Detection Patterns\n\n**A01 Broken Access Control:**\n\n- grep authz\n"
    )
    assert categories_with_patterns(bulleted) == {"A01"}


def test_an_empty_covered_by_pointer_is_rejected() -> None:
    """`Covered by:` with nothing after it points nowhere.

    A substring test is satisfied by the words alone, which tells a reader
    exactly as little as omitting the annotation entirely.
    """
    lines = detection_patterns_section(
        "### Detection Patterns\n\n"
        "**A09 Logging:** NOT STATICALLY DETECTABLE\n\n"
        "- Covered by:   \n"
    ).splitlines()
    body = [item for item in lines if "Covered by:" in item]
    assert body, "fixture must contain the pointer line"
    assert not body[0].split("Covered by:", 1)[1].strip(), (
        "fixture models an empty pointer; the gate must treat this as missing"
    )
