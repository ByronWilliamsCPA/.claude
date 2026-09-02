"""Card batch model and the on-disk markdown format.

One markdown file holds one lecture's cards. The file is the review gate: a
batch is only eligible to be pushed once its ``status`` reads ``approved``, so
the generated cards always pass under a human's eye before they reach the
collection. That gate exists because the editing pass is where the learning
happens; automating it away would be a regression, not an improvement.

The format is YAML frontmatter followed by ``## Card N`` blocks::

    ---
    course: bisc-220
    term: fall-2026
    lecture: Glycolysis regulation
    date: 2026-09-02
    deck: Ariannah::BISC 220::Fall 2026
    tags: [bisc-220, glycolysis]
    status: draft
    ---

    ## Card 1
    **Q:** Which enzyme catalyzes the rate-limiting step of glycolysis?
    **A:** Phosphofructokinase-1 (PFK-1)

    ## Card 2
    **Cloze:** PFK-1 is activated by {{c1::AMP}}, inhibited by {{c2::ATP}}.
    **Extra:** Allosteric, not covalent.

Field values may run across several lines; a value ends at the next ``**Label:**``
or at the end of the block. A card is treated as cloze when it carries a
``Cloze`` field or when its text contains a ``{{cN::...}}`` marker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Final, Literal

import yaml

MIN_CARDS: Final = 10
MAX_CARDS: Final = 15

BASIC_MODEL: Final = "Basic"
CLOZE_MODEL: Final = "Cloze"

STATUS_DRAFT: Final = "draft"
STATUS_APPROVED: Final = "approved"

_CLOZE_MARKER: Final = re.compile(r"\{\{c\d+::")
_FIELD_LINE: Final = re.compile(r"^\*\*(?P<label>[A-Za-z ]+):\*\*\s?(?P<value>.*)$")
_CARD_HEADING: Final = re.compile(r"^##\s+")
_FRONTMATTER: Final = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n?", re.DOTALL)
_SLUG_STRIP: Final = re.compile(r"[^a-z0-9]+")

_REVIEW_BANNER: Final = (
    "<!-- Read every card. Fix anything that is wrong or vague. "
    "When you are happy with them, change status above to: approved -->"
)


class CardFormatError(ValueError):
    """A card source file could not be parsed or is internally inconsistent."""


@dataclass(frozen=True)
class Card:
    """A single Anki note in pipeline form.

    Attributes:
        kind (Literal["basic", "cloze"]): Which Anki note type to create.
        front (str): Question text for a basic card, or the full cloze text.
        back (str): Answer text for a basic card. Empty for a cloze card.
        extra (str): Optional supporting note shown on the answer side.
    """

    kind: Literal["basic", "cloze"]
    front: str
    back: str = ""
    extra: str = ""

    @property
    def dedupe_key(self) -> str:
        """Return the text that identifies this card for duplicate checks.

        Returns:
            str: Question text for a basic card, cloze text for a cloze card.
        """
        return self.front

    def to_note(self, deck: str, tags: list[str]) -> dict[str, Any]:
        """Render this card as an AnkiConnect ``addNotes`` payload.

        Args:
            deck (str): Fully qualified destination deck name.
            tags (list[str]): Tags to attach to the note.

        Returns:
            dict[str, Any]: One note entry in ``addNotes`` shape.
        """
        if self.kind == "cloze":
            fields = {"Text": self.front, "Back Extra": self.extra}
            model = CLOZE_MODEL
        else:
            fields = {"Front": self.front, "Back": self._basic_back()}
            model = BASIC_MODEL
        return {
            "deckName": deck,
            "modelName": model,
            "fields": fields,
            "tags": list(tags),
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": deck,
                    "checkChildren": True,
                    "checkAllModels": False,
                },
            },
        }

    def _basic_back(self) -> str:
        """Return the answer side, appending ``extra`` when present.

        Returns:
            str: Answer text with the optional extra note appended.
        """
        if not self.extra:
            return self.back
        return f"{self.back}<br><br><i>{self.extra}</i>"


@dataclass
class CardBatch:
    """One lecture's worth of cards plus the metadata that routes them.

    Attributes:
        course (str): Course slug, for example ``bisc-220``.
        term (str): Term slug, for example ``fall-2026``.
        lecture (str): Human-readable lecture title.
        date (date): Lecture date, used for the filename and ordering.
        deck (str): Fully qualified destination deck name.
        tags (list[str]): Tags applied to every card in the batch.
        status (str): ``draft`` or ``approved``. Only ``approved`` may push.
        cards (list[Card]): The cards themselves.
        source_path (Path | None): File this batch was read from, if any.
    """

    course: str
    term: str
    lecture: str
    date: date
    deck: str
    tags: list[str] = field(default_factory=list)
    status: str = STATUS_DRAFT
    cards: list[Card] = field(default_factory=list)
    source_path: Path | None = None

    @property
    def approved(self) -> bool:
        """Report whether this batch has cleared the human review gate.

        Returns:
            bool: True when ``status`` is ``approved``.
        """
        return self.status.strip().lower() == STATUS_APPROVED

    def relative_path(self) -> Path:
        """Return this batch's path within the card-source root.

        The layout is ``<course>/<term>/<YYYY-MM-DD>-<lecture-slug>.md``.

        Returns:
            Path: Path relative to the card-source root.
        """
        name = f"{self.date.isoformat()}-{slugify(self.lecture)}.md"
        return Path(self.course) / self.term / name

    def volume_warnings(self) -> list[str]:
        """Check the batch against the daily-review volume budget.

        Returns:
            list[str]: Human-readable problems, empty when the count is fine.
        """
        count = len(self.cards)
        if count > MAX_CARDS:
            return [
                f"{count} cards is over the {MAX_CARDS}-card cap for one "
                "lecture. Trim the weakest ones so daily review stays "
                "inside 20-30 minutes."
            ]
        if count < MIN_CARDS:
            return [
                f"Only {count} cards; the target is {MIN_CARDS}-{MAX_CARDS} "
                "per lecture. This is a warning, not a blocker."
            ]
        return []


def slugify(text: str) -> str:
    """Reduce ``text`` to a lowercase hyphenated filename fragment.

    Args:
        text (str): Arbitrary human-readable text.

    Returns:
        str: Lowercase slug containing only letters, digits and hyphens.
    """
    return _SLUG_STRIP.sub("-", text.strip().lower()).strip("-") or "untitled"


def today() -> date:
    """Return the current local date.

    Returns:
        date: Today in the machine's local timezone.
    """
    return datetime.now(tz=timezone.utc).astimezone().date()


def _parse_field_block(block: str) -> dict[str, str]:
    """Parse one ``## Card`` block into its labelled fields.

    Args:
        block (str): Block body, excluding the heading line.

    Returns:
        dict[str, str]: Lowercased label mapped to its joined value.
    """
    fields: dict[str, list[str]] = {}
    current = ""
    for line in block.splitlines():
        match = _FIELD_LINE.match(line.strip())
        if match:
            label: str = str(match.group("label")).strip().lower()
            current = label
            fields[label] = [str(match.group("value")).strip()]
        elif current:
            fields[current].append(line.strip())
    return {
        label: "\n".join(part for part in parts if part).strip()
        for label, parts in fields.items()
    }


def _card_from_fields(fields: dict[str, str], index: int) -> Card:
    """Build a :class:`Card` from one block's parsed fields.

    Args:
        fields (dict[str, str]): Lowercased labels mapped to values.
        index (int): 1-based card position, used in error messages.

    Returns:
        Card: The parsed card.

    Raises:
        CardFormatError: The block carried neither a cloze text nor a
            question-and-answer pair.
    """
    extra = fields.get("extra", "")
    cloze = fields.get("cloze") or fields.get("text")
    if cloze:
        return Card(kind="cloze", front=cloze, extra=extra)
    question = fields.get("q") or fields.get("question", "")
    answer = fields.get("a") or fields.get("answer", "")
    if question and _CLOZE_MARKER.search(question) and not answer:
        return Card(kind="cloze", front=question, extra=extra)
    if not question or not answer:
        msg = (
            f"Card {index} is incomplete. A card needs either "
            "'**Q:**' and '**A:**' lines, or a '**Cloze:**' line."
        )
        raise CardFormatError(msg)
    return Card(kind="basic", front=question, back=answer, extra=extra)


def parse_cards(body: str) -> list[Card]:
    """Parse the ``## Card`` blocks of a card source file body.

    Propagates :class:`CardFormatError` when a block cannot be parsed into a
    card.

    Args:
        body (str): Everything after the YAML frontmatter.

    Returns:
        list[Card]: Cards in file order.
    """
    blocks: list[str] = []
    buffer: list[str] = []
    started = False
    for line in body.splitlines():
        if _CARD_HEADING.match(line):
            if started:
                blocks.append("\n".join(buffer))
            buffer = []
            started = True
            continue
        if started:
            buffer.append(line)
    if started:
        blocks.append("\n".join(buffer))
    cards: list[Card] = []
    for position, block in enumerate(blocks, start=1):
        fields = _parse_field_block(block)
        if not fields:
            continue
        cards.append(_card_from_fields(fields, position))
    return cards


def _require_str(meta: dict[str, Any], key: str, source: str) -> str:
    """Read a required string key out of parsed frontmatter.

    Args:
        meta (dict[str, Any]): Parsed frontmatter mapping.
        key (str): Key to read.
        source (str): File description, used in error messages.

    Returns:
        str: The key's value as a string.

    Raises:
        CardFormatError: The key was missing or empty.
    """
    value = meta.get(key)
    if value is None or str(value).strip() == "":
        msg = f"{source}: frontmatter is missing required key '{key}'."
        raise CardFormatError(msg)
    return str(value).strip()


def _coerce_date(value: Any, source: str) -> date:
    """Coerce a frontmatter date value into a :class:`datetime.date`.

    Args:
        value (Any): Raw value from the frontmatter.
        source (str): File description, used in error messages.

    Returns:
        date: The parsed date.

    Raises:
        CardFormatError: The value was absent or not an ISO date.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        msg = f"{source}: 'date' must be an ISO date like 2026-09-02, got {value!r}."
        raise CardFormatError(msg) from exc


def parse_batch(text: str, source: str = "card file") -> CardBatch:
    """Parse a complete card source file.

    Args:
        text (str): Full file contents.
        source (str): File description, used in error messages.

    Returns:
        CardBatch: The parsed batch.

    Raises:
        CardFormatError: The frontmatter was missing, malformed, or incomplete.
    """
    match = _FRONTMATTER.match(text)
    if match is None:
        msg = f"{source}: file must start with a '---' YAML frontmatter block."
        raise CardFormatError(msg)
    try:
        meta = yaml.safe_load(match.group("yaml")) or {}
    except yaml.YAMLError as exc:
        msg = f"{source}: frontmatter is not valid YAML: {exc}"
        raise CardFormatError(msg) from exc
    if not isinstance(meta, dict):
        msg = f"{source}: frontmatter must be a mapping of keys to values."
        raise CardFormatError(msg)
    raw_tags = meta.get("tags") or []
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    return CardBatch(
        course=_require_str(meta, "course", source),
        term=_require_str(meta, "term", source),
        lecture=_require_str(meta, "lecture", source),
        date=_coerce_date(meta.get("date"), source),
        deck=_require_str(meta, "deck", source),
        tags=tags,
        status=str(meta.get("status", STATUS_DRAFT)).strip().lower(),
        cards=parse_cards(text[match.end() :]),
    )


def read_batch(path: Path) -> CardBatch:
    """Read and parse a card source file from disk.

    Args:
        path (Path): Card source file to read.

    Returns:
        CardBatch: The parsed batch, with ``source_path`` set.

    Raises:
        CardFormatError: The file does not exist or could not be parsed.
    """
    if not path.is_file():
        msg = f"No card file at {path}."
        raise CardFormatError(msg)
    batch = parse_batch(path.read_text(encoding="utf-8"), source=str(path))
    batch.source_path = path
    return batch


def _render_card(card: Card, index: int) -> str:
    """Render one card as a markdown block.

    Args:
        card (Card): Card to render.
        index (int): 1-based card position.

    Returns:
        str: Markdown block including its heading.
    """
    lines = [f"## Card {index}"]
    if card.kind == "cloze":
        lines.append(f"**Cloze:** {card.front}")
    else:
        lines.append(f"**Q:** {card.front}")
        lines.append(f"**A:** {card.back}")
    if card.extra:
        lines.append(f"**Extra:** {card.extra}")
    return "\n".join(lines)


def render_batch(batch: CardBatch) -> str:
    """Render a batch back to the on-disk markdown format.

    Args:
        batch (CardBatch): Batch to render.

    Returns:
        str: Full file contents, ending in a single newline.
    """
    meta = {
        "course": batch.course,
        "term": batch.term,
        "lecture": batch.lecture,
        "date": batch.date.isoformat(),
        "deck": batch.deck,
        "tags": list(batch.tags),
        "status": batch.status,
    }
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    blocks = [_render_card(card, i) for i, card in enumerate(batch.cards, start=1)]
    body = "\n\n".join(blocks)
    return f"---\n{front}\n---\n\n{_REVIEW_BANNER}\n\n{body}\n"
