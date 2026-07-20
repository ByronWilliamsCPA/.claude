"""No capability or rule file may reference a retired MCP tool name.

Live capability files (agents, skills, rules, commands) are dispatch
instructions: a tool name that no longer exists dispatches into a void.
CHANGELOG entries, audits, and plans may mention retired names as history,
so only the capability directories are scanned.

Scope note: this guard bans tool names that are *gone*, not tool names that
are merely superseded. `mcp__pal__consensus` and `mcp__pal__tiered_consensus`
are superseded by the `/panel` skill but still exist on the pal server, and
`mcp__pal__chat` is still called by the `rad` skill and the mkdocs agents, so
none of them belong here. Add a token only after confirming the tool is
actually absent.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Retired tool namespaces:
#   mcp__zen__ / mcp__zen-core__  -> server is registered as `pal`; the zen
#                                    namespace no longer resolves.
#   mcp__context7__get-library-docs -> renamed upstream to `query-docs`.
DEAD_TOKENS = re.compile(r"mcp__zen[-_]|mcp__context7__get-library-docs")

SCAN_DIRS = [".claude/agents", ".claude/skills", ".claude/rules", ".claude/commands"]


def live_files():
    """Yield every non-symlinked Markdown file under the capability directories."""
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            if path.is_symlink():
                continue  # vendored content is upstream-owned
            yield path


def test_no_dead_tool_references():
    """Capability files must not name an MCP tool that no longer exists."""
    offenders = []
    for path in live_files():
        rel = str(path.relative_to(ROOT))
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if DEAD_TOKENS.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()[:80]}")
    assert not offenders, "dead tool references:\n" + "\n".join(offenders)
