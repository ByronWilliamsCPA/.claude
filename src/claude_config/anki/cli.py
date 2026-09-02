"""Command line entry point for the Anki card pipeline.

Five commands, in the order they get used::

    anki-cards check                 # is Anki ready?
    anki-cards new  <course> <term> <lecture>   # make an empty card file
    anki-cards validate <file>       # parse and count, no Anki needed
    anki-cards push <file>           # add approved cards to the collection
    anki-cards export                # write an .apkg snapshot

The operator is a student, not a developer, so every failure path prints the
next action to take rather than a stack trace. Anything unexpected still
raises, but the four named error classes are caught and reported plainly.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from claude_config.anki.cards import (
    MAX_CARDS,
    MIN_CARDS,
    STATUS_DRAFT,
    CardBatch,
    CardFormatError,
    read_batch,
    today,
)
from claude_config.anki.connect import AnkiConnectClient, AnkiError
from claude_config.anki.dedupe import DEFAULT_THRESHOLD
from claude_config.anki.pipeline import (
    PipelineError,
    PushReport,
    export_collection,
    push_batch,
    resolve_card_file,
    root_deck,
    write_draft,
)
from claude_config.common.output import err, out

EXIT_OK = 0
EXIT_FAIL = 1


def _client(args: argparse.Namespace) -> AnkiConnectClient:
    """Build a client, letting flags override the environment.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        AnkiConnectClient: Configured client.
    """
    client = AnkiConnectClient.from_env()
    if args.host:
        client.host = args.host
    if args.port:
        client.port = args.port
    return client


def cmd_check(args: argparse.Namespace) -> int:
    """Report whether Anki is reachable and what it contains.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        int: Process exit code.
    """
    client = _client(args)
    version = client.preflight()
    decks = client.deck_names()
    out(f"Anki is running. AnkiConnect API version {version}.")
    out(f"Collection has {len(decks)} deck(s).")
    for deck in sorted(decks):
        out(f"  {deck}")
    if not client.supports("exportPackage"):
        out("")
        out("Note: this add-on version has no 'exportPackage'; backups")
        out("will need File > Export in Anki instead.")
    return EXIT_OK


def cmd_new(args: argparse.Namespace) -> int:
    """Create an empty card file at the conventional path.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        int: Process exit code.
    """
    deck = args.deck or f"{root_deck()}::{args.course}::{args.term}"
    batch = CardBatch(
        course=args.course,
        term=args.term,
        lecture=args.lecture,
        date=args.date or today(),
        deck=deck,
        tags=[args.course],
        status=STATUS_DRAFT,
        cards=[],
    )
    path = write_draft(batch, overwrite=args.overwrite)
    out(f"Created {path}")
    out(f"Add {MIN_CARDS}-{MAX_CARDS} cards, then set status to 'approved'.")
    return EXIT_OK


def _report_volume(batch: CardBatch) -> None:
    """Print the card count and any volume advisories.

    Args:
        batch (CardBatch): Batch to describe.
    """
    out(f"{len(batch.cards)} card(s).")
    for warning in batch.volume_warnings():
        out(f"  Warning: {warning}")


def cmd_validate(args: argparse.Namespace) -> int:
    """Parse a card file and report its contents without touching Anki.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        int: Process exit code.
    """
    path = resolve_card_file(args.file)
    batch = read_batch(path)
    out(f"{path}")
    out(f"Course {batch.course} / {batch.term}, lecture {batch.lecture!r}.")
    out(f"Deck: {batch.deck}")
    out(f"Status: {batch.status}")
    _report_volume(batch)
    basic = sum(1 for card in batch.cards if card.kind == "basic")
    cloze = len(batch.cards) - basic
    out(f"  {basic} question/answer, {cloze} cloze.")
    if not batch.approved:
        out("")
        out("Not approved yet, so push will refuse. Read the cards, edit")
        out("anything wrong, then change status to 'approved'.")
    return EXIT_OK


def _print_push_report(report: PushReport) -> None:
    """Print the outcome of a push run.

    Args:
        report (PushReport): Report to describe.
    """
    if report.skipped:
        out(f"Skipped {len(report.skipped)} near-duplicate(s):")
        for index in sorted(report.skipped):
            match = report.skipped[index]
            excerpt = " ".join(match.existing_text.split())[:70]
            out(f"  Card {index} ({match.score:.0%} match): {excerpt}")
        out("  Pass --force-duplicates to add them anyway.")
    for warning in report.warnings:
        out(f"Warning: {warning}")
    if report.dry_run:
        out("Dry run: nothing written.")
        return
    out(f"Added {report.added_count} card(s) to {report.deck}.")
    if report.rejected:
        listed = ", ".join(str(i) for i in report.rejected)
        out(f"Anki declined card(s) {listed}, normally because they")
        out("already exist in the deck.")
    if report.synced:
        out("Synced to AnkiWeb; your phone will pick the cards up.")
    elif report.added_count:
        out("Not synced. Run a sync in Anki to reach your other devices.")


def cmd_push(args: argparse.Namespace) -> int:
    """Push an approved card file into the collection.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        int: Process exit code.
    """
    path = resolve_card_file(args.file)
    batch = read_batch(path)
    report = push_batch(
        _client(args),
        batch,
        threshold=args.duplicate_threshold,
        dry_run=args.dry_run,
        force_duplicates=args.force_duplicates,
        allow_overflow=args.allow_overflow,
        sync=not args.no_sync,
    )
    _print_push_report(report)
    return EXIT_OK


def cmd_export(args: argparse.Namespace) -> int:
    """Write an ``.apkg`` snapshot of the deck tree.

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        int: Process exit code.
    """
    path = export_collection(
        _client(args),
        dest_dir=Path(args.dest).expanduser() if args.dest else None,
        deck=args.deck,
    )
    out(f"Wrote {path}")
    return EXIT_OK


def _add_connection_flags(parser: argparse.ArgumentParser) -> None:
    """Attach the shared AnkiConnect connection flags.

    Args:
        parser (argparse.ArgumentParser): Subcommand parser to extend.
    """
    parser.add_argument("--host", default=None, help="AnkiConnect host.")
    parser.add_argument("--port", type=int, default=None, help="AnkiConnect port.")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Returns:
        argparse.ArgumentParser: Parser covering every subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="anki-cards",
        description="Turn distilled lecture notes into Anki cards.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check that Anki is reachable.")
    _add_connection_flags(check)
    check.set_defaults(handler=cmd_check)

    new = subparsers.add_parser("new", help="Create an empty card file.")
    new.add_argument("course", help="Course slug, e.g. bisc-220.")
    new.add_argument("term", help="Term slug, e.g. fall-2026.")
    new.add_argument("lecture", help="Lecture title.")
    new.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="Lecture date as YYYY-MM-DD. Defaults to today.",
    )
    new.add_argument("--deck", default=None, help="Override the destination deck.")
    new.add_argument(
        "--overwrite", action="store_true", help="Replace an existing file."
    )
    new.set_defaults(handler=cmd_new)

    validate = subparsers.add_parser("validate", help="Parse a card file.")
    validate.add_argument("file", help="Card file path, absolute or root-relative.")
    validate.set_defaults(handler=cmd_validate)

    push = subparsers.add_parser("push", help="Add approved cards to Anki.")
    push.add_argument("file", help="Card file path, absolute or root-relative.")
    push.add_argument(
        "--dry-run",
        action="store_true",
        help="Report duplicates and counts without writing.",
    )
    push.add_argument(
        "--force-duplicates",
        action="store_true",
        help="Add cards flagged as near-duplicates anyway.",
    )
    push.add_argument(
        "--allow-overflow",
        action="store_true",
        help=f"Permit more than {MAX_CARDS} cards in one batch.",
    )
    push.add_argument(
        "--duplicate-threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Similarity cutoff, 0-1. Default {DEFAULT_THRESHOLD}.",
    )
    push.add_argument(
        "--no-sync", action="store_true", help="Skip the AnkiWeb sync afterwards."
    )
    _add_connection_flags(push)
    push.set_defaults(handler=cmd_push)

    export = subparsers.add_parser("export", help="Write an .apkg snapshot.")
    export.add_argument("--dest", default=None, help="Destination folder.")
    export.add_argument("--deck", default=None, help="Deck to export.")
    _add_connection_flags(export)
    export.set_defaults(handler=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv (list[str] | None): Argument vector, defaulting to ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (AnkiError, CardFormatError, PipelineError) as exc:
        err(str(exc))
        return EXIT_FAIL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
