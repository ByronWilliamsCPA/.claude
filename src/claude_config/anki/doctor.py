"""Setup verification for a fresh machine.

``anki-cards doctor`` is the acceptance test for first-run setup. It answers
one question: will a push work on this machine right now? Each check reports
its own remedy, so the output is usable by whoever ran it without needing to
read the setup guide alongside.

Checks are ordered cheapest first, and the local filesystem checks run before
the ones that need Anki open, so a misconfigured path is reported even when
Anki is closed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from claude_config.anki.cards import BASIC_MODEL, CLOZE_MODEL
from claude_config.anki.connect import AnkiError
from claude_config.anki.pipeline import (
    EXPORT_DIR_ENV,
    SOURCE_ROOT_ENV,
    card_source_root,
    root_deck,
)

if TYPE_CHECKING:
    from claude_config.anki.connect import AnkiConnectClient

CONFIG_REPO_MARKERS: Final = ("CLAUDE.md", ".claude/skills", ".git")


@dataclass(frozen=True)
class CheckResult:
    """One verification result.

    Attributes:
        name (str): Short label for the thing checked.
        ok (bool): Whether the check passed.
        detail (str): What was found, and the remedy when it failed.
        fatal (bool): Whether a failure blocks pushing cards. A non-fatal
            failure is reported as a warning and does not fail the command.
    """

    name: str
    ok: bool
    detail: str
    fatal: bool = True


def find_config_repo(path: Path) -> Path | None:
    """Find the public config repo in ``path`` or any of its parents.

    A config repo carries a top-level ``CLAUDE.md``, a ``.claude/skills``
    directory, and a ``.git`` entry.

    The ``.git`` requirement is what keeps this from misfiring on a home
    directory. After ``setup.sh`` runs, ``~/.claude/skills`` is a symlink and
    therefore exists, so a home directory that also happens to hold a
    ``~/CLAUDE.md`` matches the first two markers on its own. Without the
    third, a perfectly good card source at ``~/dev/premed-anki-source`` would
    be reported as living inside the public repo. A home directory is not a
    git checkout; the config repo always is.

    Args:
        path (Path): Directory to test, along with its ancestors.

    Returns:
        Path | None: The config repo root, or None when ``path`` sits outside
            any config repo.
    """
    for candidate in (path, *path.parents):
        if all((candidate / marker).exists() for marker in CONFIG_REPO_MARKERS):
            return candidate
    return None


def check_source_root() -> list[CheckResult]:
    """Verify the card-source repository is configured and usable.

    Returns:
        list[CheckResult]: Results for configuration, existence, git status
            and the public-repo guard.
    """
    configured = os.environ.get(SOURCE_ROOT_ENV)
    root = card_source_root()
    results = [
        CheckResult(
            name=SOURCE_ROOT_ENV,
            ok=bool(configured),
            detail=(
                f"Set to {root}."
                if configured
                else f"Not set, so the default {root} would be used. "
                f"Export {SOURCE_ROOT_ENV} in your shell profile."
            ),
            fatal=False,
        )
    ]
    if not root.is_dir():
        results.append(
            CheckResult(
                name="card source folder",
                ok=False,
                detail=f"{root} does not exist. Clone the card-source repo there.",
            )
        )
        return results
    results.append(
        CheckResult(name="card source folder", ok=True, detail=f"{root} exists.")
    )
    results.append(_check_is_git_repo(root))
    results.append(_check_not_public_repo(root))
    return results


def _check_is_git_repo(root: Path) -> CheckResult:
    """Verify the card-source root is a git repository.

    Args:
        root (Path): Card-source root.

    Returns:
        CheckResult: Whether ``root`` carries a ``.git`` entry.
    """
    if (root / ".git").exists():
        return CheckResult(
            name="card source is a git repo", ok=True, detail="Version history is on."
        )
    return CheckResult(
        name="card source is a git repo",
        ok=False,
        detail=(
            f"{root} is not a git repository, so card batches would have no "
            "history. Run 'git init' there and add a private remote."
        ),
    )


def _check_not_public_repo(root: Path) -> CheckResult:
    """Verify the card-source root is not inside the public config repo.

    Card content carries a student's course list, lecture cadence and study
    record, so it must never land in a public repository.

    Args:
        root (Path): Card-source root.

    Returns:
        CheckResult: Whether ``root`` sits outside any config repo.
    """
    config_repo = find_config_repo(root)
    if config_repo is None:
        return CheckResult(
            name="card source is separate from the config repo",
            ok=True,
            detail="Card content is outside the public config repo.",
        )
    return CheckResult(
        name="card source is separate from the config repo",
        ok=False,
        detail=(
            f"{root} is inside the config repo at {config_repo}, which is "
            "public. Move the card source to its own private repository and "
            f"repoint {SOURCE_ROOT_ENV}."
        ),
    )


def check_export_dir() -> CheckResult:
    """Verify the ``.apkg`` export destination.

    Returns:
        CheckResult: Whether an export folder is configured and present. Not
            fatal, because pushing cards does not depend on it.
    """
    configured = os.environ.get(EXPORT_DIR_ENV)
    if not configured:
        return CheckResult(
            name=EXPORT_DIR_ENV,
            ok=False,
            detail=(
                "Not set, so 'anki-cards export' will refuse to run. Point it "
                "at the OneDrive folder that holds the family tracker."
            ),
            fatal=False,
        )
    path = Path(configured).expanduser()
    if not path.is_dir():
        return CheckResult(
            name=EXPORT_DIR_ENV,
            ok=False,
            detail=f"{path} does not exist yet. It is created on first export.",
            fatal=False,
        )
    return CheckResult(name=EXPORT_DIR_ENV, ok=True, detail=f"{path} is ready.")


def check_anki(client: AnkiConnectClient) -> list[CheckResult]:
    """Verify Anki is reachable and carries the note types the pipeline uses.

    Args:
        client (AnkiConnectClient): Client to probe with.

    Returns:
        list[CheckResult]: Connection, note-type and export-capability results.
            Returns a single fatal result when Anki cannot be reached, since
            every later check depends on the connection.
    """
    try:
        version = client.preflight()
    except AnkiError as exc:
        return [CheckResult(name="Anki connection", ok=False, detail=str(exc))]
    results = [
        CheckResult(
            name="Anki connection",
            ok=True,
            detail=f"Reachable on {client.host}:{client.port}, API version {version}.",
        )
    ]
    results.append(_check_note_types(client))
    results.append(_check_root_deck(client))
    exportable = client.supports("exportPackage")
    results.append(
        CheckResult(
            name="exportPackage action",
            ok=exportable,
            detail=(
                "Available, so .apkg backups will work."
                if exportable
                else "Not exposed by this add-on version. Update AnkiConnect, "
                "or use File > Export in Anki for backups."
            ),
            fatal=False,
        )
    )
    return results


def _check_note_types(client: AnkiConnectClient) -> CheckResult:
    """Verify the Basic and Cloze note types exist.

    A collection created in another language, or one whose note types were
    renamed, will not carry these names, and every push would fail on an
    unhelpful add-on error. Catching it here names the real problem.

    Args:
        client (AnkiConnectClient): Client to probe with.

    Returns:
        CheckResult: Whether both note types are present.
    """
    try:
        models = set(client.model_names())
    except AnkiError as exc:
        return CheckResult(name="note types", ok=False, detail=str(exc))
    missing = [name for name in (BASIC_MODEL, CLOZE_MODEL) if name not in models]
    if not missing:
        return CheckResult(
            name="note types",
            ok=True,
            detail=f"{BASIC_MODEL} and {CLOZE_MODEL} are both present.",
        )
    return CheckResult(
        name="note types",
        ok=False,
        detail=(
            f"Missing note type(s): {', '.join(missing)}. This collection uses "
            "different note-type names, most often because Anki was set up in "
            "another language. Add note types with these exact names in "
            "Tools > Manage Note Types, or report the names it does have."
        ),
    )


def _check_root_deck(client: AnkiConnectClient) -> CheckResult:
    """Report whether the configured top-level deck exists.

    Args:
        client (AnkiConnectClient): Client to probe with.

    Returns:
        CheckResult: Whether the root deck is present. Not fatal, because
            course decks are created on demand during a push.
    """
    deck = root_deck()
    try:
        decks = set(client.deck_names())
    except AnkiError as exc:
        return CheckResult(name="root deck", ok=False, detail=str(exc), fatal=False)
    if deck in decks:
        return CheckResult(name="root deck", ok=True, detail=f"{deck!r} exists.")
    return CheckResult(
        name="root deck",
        ok=False,
        detail=(
            f"No deck named {deck!r} yet. It is created on the first push, so "
            "this only matters if you expected it to be there already."
        ),
        fatal=False,
    )


def run_checks(client: AnkiConnectClient) -> list[CheckResult]:
    """Run every setup check, filesystem first.

    Args:
        client (AnkiConnectClient): Client to probe Anki with.

    Returns:
        list[CheckResult]: All results, in report order.
    """
    results = check_source_root()
    results.append(check_export_dir())
    results.extend(check_anki(client))
    return results


def blocking_failures(results: list[CheckResult]) -> list[CheckResult]:
    """Select the failures that would stop a push.

    Args:
        results (list[CheckResult]): Results from :func:`run_checks`.

    Returns:
        list[CheckResult]: Fatal failures only.
    """
    return [result for result in results if not result.ok and result.fatal]
