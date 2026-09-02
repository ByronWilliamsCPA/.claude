"""Near-duplicate detection against notes already in the collection.

Anki's own duplicate check compares the first field byte-for-byte, so it
catches a re-pushed identical card but not the same fact asked a second way.
Across a term that reworded-duplicate case is the common one: two lectures
cover the same pathway and the pipeline drafts the same fact twice.

Detection is stopword-stripped Jaccard similarity on word tokens. Stripping
stopwords first is what makes it work: "Which enzyme catalyzes the
rate-limiting step of glycolysis?" against "What enzyme catalyzes glycolysis's
rate-limiting step?" scores 0.55 on raw tokens, which no usable threshold
catches, and 1.0 once stopwords are gone.

#ASSUME A 0.75 threshold separates rewordings from genuinely distinct cards.
#VERIFY Push reports every match with its score and skips rather than
    silently dropping, so a wrong threshold is visible in the run report and
    correctable with --duplicate-threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from claude_config.anki.cards import Card

DEFAULT_THRESHOLD: Final = 0.75

_HTML_TAG: Final = re.compile(r"<[^>]+>")
_CLOZE_WRAPPER: Final = re.compile(r"\{\{c\d+::(?P<inner>.*?)(?:::.*?)?\}\}")
_NON_WORD: Final = re.compile(r"[^a-z0-9\s]+")
_WHITESPACE: Final = re.compile(r"\s+")

_STOPWORDS: Final = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "which",
        "who",
        "why",
        "with",
        "was",
        "were",
        "will",
        "would",
        "can",
        "could",
        "s",
    }
)


@dataclass(frozen=True)
class DuplicateMatch:
    """A drafted card that closely matches a note already in the collection.

    Attributes:
        card_index (int): 1-based position of the drafted card in its batch.
        score (float): Jaccard similarity in the range 0.0 to 1.0.
        existing_text (str): First-field text of the matching existing note.
        note_id (int | None): Anki note id of the match, when known.
    """

    card_index: int
    score: float
    existing_text: str
    note_id: int | None = None


def normalize(text: str) -> str:
    """Reduce card text to comparable plain words.

    Strips HTML, unwraps cloze markers to their answer text, drops
    punctuation, lowercases, and collapses whitespace.

    Args:
        text (str): Raw card or note field text.

    Returns:
        str: Normalized text.
    """
    unwrapped = _CLOZE_WRAPPER.sub(lambda m: m.group("inner"), text)
    stripped = _HTML_TAG.sub(" ", unwrapped).replace("&nbsp;", " ")
    lowered = _NON_WORD.sub(" ", stripped.lower())
    return _WHITESPACE.sub(" ", lowered).strip()


def tokens(text: str) -> frozenset[str]:
    """Tokenize ``text`` into meaningful words.

    Args:
        text (str): Raw card or note field text.

    Returns:
        frozenset[str]: Lowercased words with stopwords removed.
    """
    return frozenset(word for word in normalize(text).split() if word not in _STOPWORDS)


def similarity(left: str, right: str) -> float:
    """Compute stopword-stripped Jaccard similarity between two texts.

    Args:
        left (str): First text.
        right (str): Second text.

    Returns:
        float: Similarity in the range 0.0 to 1.0. Two texts that reduce to no
            tokens at all are treated as dissimilar rather than identical.
    """
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def first_field(note: dict[str, object]) -> str:
    """Extract a note's first field value from an AnkiConnect note record.

    AnkiConnect returns fields as ``{"Front": {"value": ..., "order": 0}}``.
    The field with the lowest ``order`` is the one Anki treats as the note's
    identity, so that is the one compared.

    Args:
        note (dict[str, object]): One record from ``notesInfo``.

    Returns:
        str: First field's value, or an empty string when absent.
    """
    fields = note.get("fields")
    if not isinstance(fields, dict) or not fields:
        return ""
    best_order = None
    best_value = ""
    for entry in fields.values():
        if not isinstance(entry, dict):
            continue
        order = entry.get("order", 0)
        order = order if isinstance(order, int) else 0
        if best_order is None or order < best_order:
            best_order = order
            best_value = str(entry.get("value", ""))
    return best_value


def find_duplicates(
    cards: list[Card],
    existing: list[tuple[int | None, str]],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[int, DuplicateMatch]:
    """Match drafted cards against existing note texts.

    Args:
        cards (list[Card]): Drafted cards, in batch order.
        existing (list[tuple[int | None, str]]): Note id and first-field text
            for each note already in the destination deck.
        threshold (float): Minimum similarity to count as a duplicate.

    Returns:
        dict[int, DuplicateMatch]: Best match per duplicate card, keyed by
            1-based card index. Cards with no match are absent.
    """
    matches: dict[int, DuplicateMatch] = {}
    for index, card in enumerate(cards, start=1):
        best: DuplicateMatch | None = None
        for note_id, text in existing:
            score = similarity(card.dedupe_key, text)
            if score >= threshold and (best is None or score > best.score):
                best = DuplicateMatch(
                    card_index=index,
                    score=score,
                    existing_text=text,
                    note_id=note_id,
                )
        if best is not None:
            matches[index] = best
    return matches


def find_internal_duplicates(
    cards: list[Card],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[int, DuplicateMatch]:
    """Match drafted cards against each other within one batch.

    A batch that asks the same fact twice wastes two of a small card budget,
    so this runs even when the destination deck is empty.

    Args:
        cards (list[Card]): Drafted cards, in batch order.
        threshold (float): Minimum similarity to count as a duplicate.

    Returns:
        dict[int, DuplicateMatch]: The later card of each duplicate pair,
            keyed by its 1-based index.
    """
    matches: dict[int, DuplicateMatch] = {}
    for index, card in enumerate(cards, start=1):
        for earlier_index in range(1, index):
            score = similarity(card.dedupe_key, cards[earlier_index - 1].dedupe_key)
            if score >= threshold:
                matches[index] = DuplicateMatch(
                    card_index=index,
                    score=score,
                    existing_text=cards[earlier_index - 1].dedupe_key,
                )
                break
    return matches
