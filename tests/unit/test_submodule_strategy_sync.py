"""Guard against drift between .gitmodules and the submodule strategy doc.

The senior architecture review of 2026-07-01 found that
docs/architecture/submodule-strategy.md documented 5 of 8 submodules; the
gap persisted because nothing failed when .gitmodules grew. These tests
enforce admission bar item 5 of that doc: every submodule path declared in
.gitmodules must appear in the strategy doc's inventory table with the
upstream slug .gitmodules declares, and the doc must not reference
submodule paths that no longer exist in .gitmodules.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GITMODULES = REPO_ROOT / ".gitmodules"
STRATEGY_DOC = REPO_ROOT / "docs" / "architecture" / "submodule-strategy.md"

INVENTORY_HEADING = "## Submodule Inventory"


def parse_gitmodules(path: Path = GITMODULES) -> dict[str, str]:
    """Parse a .gitmodules file into a path-to-upstream-slug mapping.

    Args:
        path: The .gitmodules file to parse; defaults to this repo's.

    Returns:
        Mapping from each section's ``path`` value (for example
        ``.submodules/superpowers``) to the ``org/repo`` slug derived from
        its ``url`` value, or ``""`` when the section declares no url.
    """
    assert path.is_file(), f"{path} missing"
    parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    parser.read(path, encoding="utf-8")
    entries: dict[str, str] = {}
    for section in parser.sections():
        if "path" not in parser[section]:
            continue
        url = parser[section].get("url", "")
        slug = re.sub(r"\.git$", "", url.rsplit("github.com/", 1)[-1])
        entries[parser[section]["path"]] = slug
    return entries


def parse_inventory_rows(doc_path: Path = STRATEGY_DOC) -> dict[str, str]:
    """Extract inventory-table rows keyed by the submodule path each names.

    Only lines under the "## Submodule Inventory" heading (up to the next
    level-two heading) are scanned, and only the first backtick-quoted
    ``.submodules/...`` token per row counts as the row's path column;
    later columns may legitimately mention other submodule paths.

    Args:
        doc_path: The strategy doc to parse; defaults to this repo's.

    Returns:
        Mapping from ``.submodules/<name>`` (trailing slash stripped) to
        the full text of the table row that names it.
    """
    assert doc_path.is_file(), f"{doc_path} missing"
    text = doc_path.read_text(encoding="utf-8")
    assert INVENTORY_HEADING in text, (
        f"{doc_path.name} lacks the '{INVENTORY_HEADING}' heading; the "
        f"sync guard cannot locate the inventory table"
    )
    section = text.split(INVENTORY_HEADING, 1)[1]
    section = re.split(r"^## ", section, maxsplit=1, flags=re.MULTILINE)[0]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        match = re.search(r"`(\.submodules/[^`]+?)/?`", line)
        if match:
            rows.setdefault(match.group(1), line)
    return rows


def test_every_gitmodules_entry_is_documented() -> None:
    """Each .gitmodules path must appear in the inventory table."""
    missing = set(parse_gitmodules()) - set(parse_inventory_rows())
    assert not missing, (
        f"Submodules declared in .gitmodules but absent from the inventory "
        f"table in {STRATEGY_DOC.relative_to(REPO_ROOT)}: {sorted(missing)}. "
        f"Per the Submodule Admission Bar, the PR adding a submodule must "
        f"add its row (purpose, wiring, trust level) in the same PR; this "
        f"test verifies only that the path appears."
    )


def test_no_stale_doc_entries() -> None:
    """The inventory table must not reference removed submodules."""
    stale = set(parse_inventory_rows()) - set(parse_gitmodules())
    assert not stale, (
        f"Inventory table rows in {STRATEGY_DOC.relative_to(REPO_ROOT)} "
        f"reference submodule paths not present in .gitmodules: "
        f"{sorted(stale)}. Remove the row or restore the submodule."
    )


def test_upstream_slugs_match() -> None:
    """Each row must name the upstream slug .gitmodules declares for it."""
    rows = parse_inventory_rows()
    mismatched = [
        f"{path}: table row does not mention `{slug}`"
        for path, slug in parse_gitmodules().items()
        if slug and path in rows and slug not in rows[path]
    ]
    assert not mismatched, (
        f"Inventory rows in {STRATEGY_DOC.relative_to(REPO_ROOT)} disagree "
        f"with .gitmodules upstream urls: {mismatched}. Update the row's "
        f"Upstream column or the .gitmodules url."
    )


def test_fixtures_present() -> None:
    """Both sources must parse non-empty so no sync check vacuously passes."""
    assert GITMODULES.is_file(), ".gitmodules missing at repo root"
    assert STRATEGY_DOC.is_file(), "submodule-strategy.md missing"
    assert parse_gitmodules(), ".gitmodules parsed to zero submodule paths"
    assert parse_inventory_rows(), (
        "submodule-strategy.md inventory table parsed to zero rows; check "
        "the table format against parse_inventory_rows()"
    )


_FIXTURE_GITMODULES = """\
[submodule ".submodules/alpha"]
\tpath = .submodules/alpha
\turl = https://github.com/example/alpha.git
[submodule ".submodules/beta"]
\tpath = .submodules/beta
\turl = https://github.com/example/beta.git
"""

_FIXTURE_DOC = """\
# Fixture

## Submodule Inventory

| Submodule path | Upstream |
| --- | --- |
| `.submodules/alpha/` | `example/alpha` |

## Next Section

| `.submodules/outside-inventory/` | `example/outside` |
"""


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    """Write the synthetic drift fixtures and return their paths.

    Args:
        tmp_path: pytest-provided temporary directory.

    Returns:
        Tuple of (gitmodules path, strategy doc path). The pair
        deliberately omits ``.submodules/beta`` from the doc so the
        missing-entry direction has a real gap to detect.
    """
    gitmodules = tmp_path / ".gitmodules"
    gitmodules.write_text(_FIXTURE_GITMODULES, encoding="utf-8")
    doc = tmp_path / "strategy.md"
    doc.write_text(_FIXTURE_DOC, encoding="utf-8")
    return gitmodules, doc


def test_guard_detects_undocumented_submodule(tmp_path: Path) -> None:
    """The missing-entry direction must fail on a real gap."""
    gitmodules, doc = _write_fixtures(tmp_path)
    missing = set(parse_gitmodules(gitmodules)) - set(parse_inventory_rows(doc))
    assert missing == {".submodules/beta"}


def test_guard_detects_stale_doc_entry(tmp_path: Path) -> None:
    """The stale-entry direction must fail when the doc outlives .gitmodules."""
    gitmodules, doc = _write_fixtures(tmp_path)
    gitmodules.write_text(
        _FIXTURE_GITMODULES.replace(".submodules/alpha", ".submodules/gamma"),
        encoding="utf-8",
    )
    stale = set(parse_inventory_rows(doc)) - set(parse_gitmodules(gitmodules))
    assert stale == {".submodules/alpha"}


def test_inventory_scope_excludes_other_sections(tmp_path: Path) -> None:
    """Rows outside the inventory section must not count as inventory."""
    _, doc = _write_fixtures(tmp_path)
    assert ".submodules/outside-inventory" not in parse_inventory_rows(doc)
