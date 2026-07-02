"""No capability or rule file may reference retired MCP tools.

Encodes review finding 5.5: the zen/pal servers are frozen or absent;
references to their tools dispatch into a void. The /panel skill is the
replacement. CHANGELOG, audits, and plans may mention the old names as
history; live capability files may not.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEAD_TOKENS = re.compile(
    r"mcp__pal__|mcp__zen__|mcp__context7__get-library-docs"
    r"|zen\.(secaudit|codereview|testgen|docgen|precommit|challenge"
    r"|planner|consensus|debug)"
)

SCAN_DIRS = [".claude/agents", ".claude/skills", ".claude/rules", ".claude/commands"]

ALLOWED = {
    # Historical mentions only; each must carry a superseded/frozen marker.
    ".claude/rules/mcp-strategy.md",
}


def live_files():
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            if path.is_symlink():
                continue  # vendored content is upstream-owned
            yield path


def test_no_dead_tool_references():
    offenders = []
    for path in live_files():
        rel = str(path.relative_to(ROOT))
        if rel in ALLOWED:
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if DEAD_TOKENS.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()[:80]}")
    assert not offenders, "dead tool references:\n" + "\n".join(offenders)


def test_allowed_files_carry_superseded_marker():
    for rel in ALLOWED:
        text = (ROOT / rel).read_text().lower()
        assert "panel" in text and ("frozen" in text or "supersed" in text), (
            f"{rel} is allowlisted for historical zen/pal mentions but does "
            "not mark them as superseded by /panel"
        )
