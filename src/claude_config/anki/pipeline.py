"""Draft, push and export orchestration for the card pipeline.

Three operations, deliberately separate:

``draft``
    Write a card batch to a markdown file under the card-source root. Touches
    no Anki state, so it is safe to run without Anki open.
``push``
    Read an approved card file, check it against the destination deck, and add
    the surviving cards. Refuses a batch whose ``status`` is still ``draft``.
``export``
    Write an ``.apkg`` snapshot of a deck tree, for a restore path that depends
    on neither git nor AnkiWeb.

The card-source root is the ``cards`` folder of a separate private git
repository, not this one. This repo is public; a student's course list, lecture
cadence and study record are not things to publish. Cards sit under ``cards/``
rather than at that repo's root so the repo can also hold other premed material
without the two tangling. The root is resolved from ``ANKI_SOURCE_ROOT``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from claude_config.anki.cards import (
    CardBatch,
    CardFormatError,
    render_batch,
    slugify,
    today,
)
from claude_config.anki.dedupe import (
    DEFAULT_THRESHOLD,
    DuplicateMatch,
    find_duplicates,
    find_internal_duplicates,
    first_field,
)

if TYPE_CHECKING:
    from claude_config.anki.connect import AnkiConnectClient

DEFAULT_SOURCE_ROOT: Final = "~/dev/premed-anki-source/cards"
SOURCE_ROOT_ENV: Final = "ANKI_SOURCE_ROOT"
EXPORT_DIR_ENV: Final = "ANKI_EXPORT_DIR"
ROOT_DECK_ENV: Final = "ANKI_ROOT_DECK"
DEFAULT_ROOT_DECK: Final = "Ariannah"


class PipelineError(RuntimeError):
    """A pipeline step could not proceed."""


@dataclass
class PushReport:
    """Outcome of a push run.

    Attributes:
        deck (str): Destination deck.
        added (list[int]): Note ids Anki created.
        skipped (dict[int, DuplicateMatch]): Cards skipped as near-duplicates,
            keyed by 1-based card index.
        rejected (list[int]): 1-based indexes Anki itself declined, normally
            because the card already exists in the deck.
        warnings (list[str]): Non-fatal advisories, including volume warnings.
        synced (bool): Whether an AnkiWeb sync was triggered afterwards.
        dry_run (bool): Whether the run stopped short of writing.
    """

    deck: str
    added: list[int] = field(default_factory=list)
    skipped: dict[int, DuplicateMatch] = field(default_factory=dict)
    rejected: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    synced: bool = False
    dry_run: bool = False

    @property
    def added_count(self) -> int:
        """Count the notes actually created.

        Returns:
            int: Number of non-null note ids returned by Anki.
        """
        return len(self.added)


def card_source_root() -> Path:
    """Resolve the card-source repository root.

    Returns:
        Path: Expanded path from ``ANKI_SOURCE_ROOT``, or the default.
    """
    raw = os.environ.get(SOURCE_ROOT_ENV) or DEFAULT_SOURCE_ROOT
    return Path(raw).expanduser()


def root_deck() -> str:
    """Resolve the top-level deck used for full exports.

    Returns:
        str: Deck name from ``ANKI_ROOT_DECK``, or the default.
    """
    return os.environ.get(ROOT_DECK_ENV) or DEFAULT_ROOT_DECK


def write_draft(
    batch: CardBatch,
    root: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Write ``batch`` to its file under the card-source root.

    Args:
        batch (CardBatch): Batch to write.
        root (Path | None): Card-source root. Defaults to
            :func:`card_source_root`.
        overwrite (bool): Whether to replace an existing file.

    Returns:
        Path: The file written.

    Raises:
        PipelineError: The target exists and ``overwrite`` is False.
    """
    base = root if root is not None else card_source_root()
    target = base / batch.relative_path()
    if target.exists() and not overwrite:
        msg = (
            f"{target} already exists. Pass --overwrite to replace it, or "
            "change the lecture title or date."
        )
        raise PipelineError(msg)
    target.parent.mkdir(parents=True, exist_ok=True)
    batch.source_path = target
    target.write_text(render_batch(batch), encoding="utf-8")
    return target


def deck_query(deck: str) -> str:
    """Build an Anki search query scoped to ``deck`` and its subdecks.

    Args:
        deck (str): Fully qualified deck name.

    Returns:
        str: Anki browser search string.
    """
    safe = deck.replace('"', "")
    return f'deck:"{safe}"'


def existing_notes(
    client: AnkiConnectClient,
    deck: str,
) -> list[tuple[int | None, str]]:
    """Fetch first-field text for every note already in ``deck``.

    Args:
        client (AnkiConnectClient): Live client.
        deck (str): Destination deck.

    Returns:
        list[tuple[int | None, str]]: Note id and first-field text per note.
    """
    note_ids = client.find_notes(deck_query(deck))
    records = client.notes_info(note_ids)
    collected: list[tuple[int | None, str]] = []
    for record in records:
        note_id = record.get("noteId")
        collected.append(
            (note_id if isinstance(note_id, int) else None, first_field(record))
        )
    return collected


def ensure_deck(client: AnkiConnectClient, deck: str) -> bool:
    """Create ``deck`` when it is missing.

    Args:
        client (AnkiConnectClient): Live client.
        deck (str): Fully qualified deck name.

    Returns:
        bool: True when the deck had to be created.
    """
    if deck in client.deck_names():
        return False
    client.create_deck(deck)
    return True


def _collect_duplicates(
    batch: CardBatch,
    client: AnkiConnectClient,
    threshold: float,
) -> dict[int, DuplicateMatch]:
    """Find both in-batch and in-deck near-duplicates.

    Args:
        batch (CardBatch): Batch being pushed.
        client (AnkiConnectClient): Live client.
        threshold (float): Similarity threshold.

    Returns:
        dict[int, DuplicateMatch]: Matches keyed by 1-based card index.
    """
    matches = find_internal_duplicates(batch.cards, threshold)
    against_deck = find_duplicates(
        batch.cards, existing_notes(client, batch.deck), threshold
    )
    matches.update(against_deck)
    return matches


def push_batch(
    client: AnkiConnectClient,
    batch: CardBatch,
    threshold: float = DEFAULT_THRESHOLD,
    dry_run: bool = False,
    force_duplicates: bool = False,
    allow_overflow: bool = False,
    sync: bool = True,
) -> PushReport:
    """Push an approved batch into the collection.

    Args:
        client (AnkiConnectClient): Live client.
        batch (CardBatch): Batch to push.
        threshold (float): Near-duplicate similarity threshold.
        dry_run (bool): Report what would happen without writing.
        force_duplicates (bool): Add cards flagged as near-duplicates anyway.
        allow_overflow (bool): Permit a batch larger than the per-lecture cap.
            Kept separate from ``force_duplicates`` on purpose: waving through
            a duplicate must not also quietly raise the volume ceiling that
            keeps daily review inside its time budget.
        sync (bool): Trigger an AnkiWeb sync after a successful push.

    Returns:
        PushReport: What happened, including everything skipped and why.

    Raises:
        PipelineError: The batch has not been approved, or is over the card cap.
    """
    if not batch.approved:
        source = batch.source_path or "this batch"
        msg = (
            f"{source} is still marked 'status: draft'.\n"
            "Read the cards, edit anything that is wrong, then change the "
            "status line to 'approved' and run push again."
        )
        raise PipelineError(msg)
    report = PushReport(deck=batch.deck, dry_run=dry_run)
    report.warnings.extend(batch.volume_warnings())
    over_cap = [w for w in report.warnings if "over the" in w]
    if over_cap and not allow_overflow:
        raise PipelineError(over_cap[0])
    client.preflight()
    if not dry_run:
        ensure_deck(client, batch.deck)
    if not force_duplicates:
        report.skipped = _collect_duplicates(
            batch=batch, client=client, threshold=threshold
        )
    keep = [
        (index, card)
        for index, card in enumerate(batch.cards, start=1)
        if index not in report.skipped
    ]
    if not keep or dry_run:
        return report
    notes = [card.to_note(batch.deck, batch.tags) for _, card in keep]
    results = client.add_notes(notes)
    for (index, _), note_id in zip(keep, results, strict=True):
        if isinstance(note_id, int):
            report.added.append(note_id)
        else:
            report.rejected.append(index)
    if sync and report.added:
        client.sync()
        report.synced = True
    return report


def export_collection(
    client: AnkiConnectClient,
    dest_dir: Path | None = None,
    deck: str | None = None,
) -> Path:
    """Write an ``.apkg`` snapshot of a deck tree.

    Args:
        client (AnkiConnectClient): Live client.
        dest_dir (Path | None): Destination directory. Defaults to
            ``ANKI_EXPORT_DIR``.
        deck (str | None): Deck to export, including its subdecks. Defaults to
            :func:`root_deck`.

    Returns:
        Path: The ``.apkg`` file written.

    Raises:
        PipelineError: No destination is configured, the deck is missing, the
            running add-on lacks ``exportPackage``, or the write failed.
    """
    target_deck = deck or root_deck()
    raw_dest = dest_dir or os.environ.get(EXPORT_DIR_ENV)
    if not raw_dest:
        msg = (
            "No export folder configured. Set ANKI_EXPORT_DIR to the OneDrive "
            "folder you want snapshots written to, or pass --dest."
        )
        raise PipelineError(msg)
    destination = Path(raw_dest).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    client.preflight()
    if not client.supports("exportPackage"):
        msg = (
            "This AnkiConnect version does not expose 'exportPackage'. Update "
            "the add-on (Tools > Add-ons > Check for Updates), or export "
            "manually with File > Export in Anki."
        )
        raise PipelineError(msg)
    if target_deck not in client.deck_names():
        msg = f"No deck named {target_deck!r} in this collection."
        raise PipelineError(msg)
    out_path = destination / f"{slugify(target_deck)}-{today().isoformat()}.apkg"
    if not client.export_package(target_deck, str(out_path), include_sched=True):
        msg = f"Anki reported that the export to {out_path} did not succeed."
        raise PipelineError(msg)
    return out_path


def resolve_card_file(reference: str, root: Path | None = None) -> Path:
    """Resolve a card-file reference to a path.

    Accepts a path that exists as given, or one relative to the card-source
    root, so the operator can pass either.

    Args:
        reference (str): Path or root-relative path to a card file.
        root (Path | None): Card-source root. Defaults to
            :func:`card_source_root`.

    Returns:
        Path: The resolved file.

    Raises:
        CardFormatError: Neither interpretation names an existing file.
    """
    direct = Path(reference).expanduser()
    if direct.is_file():
        return direct
    base = root if root is not None else card_source_root()
    candidate = base / reference
    if candidate.is_file():
        return candidate
    msg = f"No card file at {direct} or {candidate}."
    raise CardFormatError(msg)
