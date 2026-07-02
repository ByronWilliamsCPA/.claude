"""Linter for .claude/agents/*.md frontmatter (review 6.3)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINTER = ROOT / "scripts" / "lint-agent-frontmatter.py"


def run_linter(tmp_path, content, name="probe.md"):
    agent = tmp_path / name
    agent.write_text(content)
    return subprocess.run(
        [sys.executable, str(LINTER), str(agent)],
        capture_output=True,
        text=True,
        check=False,
    )


GOOD = """---
name: probe
description: Probe agent. Invoke when testing the linter.
model: sonnet
tools: ["Read", "Grep"]
---
Body.
"""

NO_MODEL = GOOD.replace("model: sonnet\n", "")

INHERIT_REVIEWER = GOOD.replace("model: sonnet", "model: inherit").replace(
    "Probe agent.", "Adversarial code reviewer."
)

WRITE_REVIEWER = GOOD.replace(
    'tools: ["Read", "Grep"]', 'tools: ["Read", "Write"]'
).replace("Probe agent.", "Reviews and audits diffs.")


def test_good_agent_passes(tmp_path):
    assert run_linter(tmp_path, GOOD).returncode == 0


def test_missing_model_fails(tmp_path):
    result = run_linter(tmp_path, NO_MODEL)
    assert result.returncode != 0
    assert "R1" in result.stdout


def test_inherit_reviewer_fails(tmp_path):
    result = run_linter(tmp_path, INHERIT_REVIEWER)
    assert result.returncode != 0
    assert "R3" in result.stdout


def test_write_granting_reviewer_warns(tmp_path):
    result = run_linter(tmp_path, WRITE_REVIEWER)
    assert result.returncode == 0
    assert "R4" in result.stdout


def test_real_agents_tree_passes():
    files = sorted((ROOT / ".claude" / "agents").glob("*.md"))
    result = subprocess.run(
        [sys.executable, str(LINTER), *map(str, files)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
