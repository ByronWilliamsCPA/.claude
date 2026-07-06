"""Guard against drift between .gitmodules and the submodule strategy doc.

The senior architecture review of 2026-07-01 found that
docs/architecture/submodule-strategy.md documented 5 of 8 submodules; the
gap persisted because nothing failed when .gitmodules grew. This test
enforces admission bar item 5 of that doc: every submodule path declared in
.gitmodules must appear in the strategy doc's inventory table, and the doc
must not reference submodule paths that no longer exist in .gitmodules.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GITMODULES = REPO_ROOT / ".gitmodules"
STRATEGY_DOC = REPO_ROOT / "docs" / "architecture" / "submodule-strategy.md"


def gitmodules_paths() -> set[str]:
    """Parse .gitmodules and return the declared submodule paths.

    Returns:
        Set of submodule paths as declared in each section's ``path`` key,
        for example ``.submodules/superpowers``.
    """
    parser = configparser.ConfigParser()
    parser.read(GITMODULES)
    return {
        parser[section]["path"]
        for section in parser.sections()
        if "path" in parser[section]
    }


def inventory_table_paths() -> set[str]:
    """Extract submodule paths named in the strategy doc's inventory table.

    Returns:
        Set of ``.submodules/<name>`` paths found in table rows, with any
        trailing slash stripped so they compare equal to .gitmodules paths.
    """
    text = STRATEGY_DOC.read_text(encoding="utf-8")
    table_rows = [line for line in text.splitlines() if line.startswith("| `")]
    found: set[str] = set()
    for row in table_rows:
        for match in re.findall(r"`(\.submodules/[^`]+?)/?`", row):
            found.add(match)
    return found


def test_every_gitmodules_entry_is_documented() -> None:
    """Each .gitmodules path must appear in the inventory table."""
    missing = gitmodules_paths() - inventory_table_paths()
    assert not missing, (
        f"Submodules declared in .gitmodules but absent from the inventory "
        f"table in {STRATEGY_DOC.relative_to(REPO_ROOT)}: {sorted(missing)}. "
        f"Per the Submodule Admission Bar, the PR adding a submodule must "
        f"document it (purpose, wiring, trust level) in the same PR."
    )


def test_no_stale_doc_entries() -> None:
    """The inventory table must not reference removed submodules."""
    stale = inventory_table_paths() - gitmodules_paths()
    assert not stale, (
        f"Inventory table rows in {STRATEGY_DOC.relative_to(REPO_ROOT)} "
        f"reference submodule paths not present in .gitmodules: "
        f"{sorted(stale)}. Remove the row or restore the submodule."
    )


def test_fixtures_present() -> None:
    """Both source files must exist so the sync checks cannot vacuously pass."""
    assert GITMODULES.is_file(), ".gitmodules missing at repo root"
    assert STRATEGY_DOC.is_file(), "submodule-strategy.md missing"
    assert gitmodules_paths(), ".gitmodules parsed to zero submodule paths"
