"""Every skill directory and agent file must appear in AGENTS-AND-SKILLS.md.

Encodes the registration rule from .claude/skills/CLAUDE.md that 19 skills
currently violate (review 4.7-1).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = (ROOT / "AGENTS-AND-SKILLS.md").read_text()


def test_all_skills_registered():
    """Every directory under .claude/skills/ must be named in the catalog."""
    missing = [
        p.name
        for p in sorted((ROOT / ".claude" / "skills").iterdir())
        if p.is_dir() and p.name not in CATALOG
    ]
    assert not missing, f"skills absent from AGENTS-AND-SKILLS.md: {missing}"


def test_all_agents_registered():
    """Every agent file under .claude/agents/ must be named in the catalog."""
    missing = [
        p.stem
        for p in sorted((ROOT / ".claude" / "agents").glob("*.md"))
        if p.name != "CLAUDE.md" and p.stem not in CATALOG
    ]
    assert not missing, f"agents absent from AGENTS-AND-SKILLS.md: {missing}"
