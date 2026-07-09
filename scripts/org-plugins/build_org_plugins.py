#!/usr/bin/env python3
"""Build the wff-code and wff-chat plugin trees from manifest.yaml.

Reads scripts/org-plugins/manifest.yaml and copies the listed first-party
agents and skills out of .claude/agents/ and .claude/skills/ into a
marketplace-shaped output directory:

    <out>/.claude-plugin/marketplace.json
    <out>/plugins/<plugin-name>/.claude-plugin/plugin.json
    <out>/plugins/<plugin-name>/agents/*.md      (wff-code only)
    <out>/plugins/<plugin-name>/skills/<name>/...

The manifest is the only source of truth for what ships; this script does not
infer classification from file contents. See
docs/architecture/org-plugin-distribution.md for the full design.

Usage:
    python3 scripts/org-plugins/build_org_plugins.py --out /path/to/build/dir
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "scripts" / "org-plugins" / "manifest.yaml"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
OWNER_NAME = "Byron Williams"


def load_manifest() -> dict:
    """Load and lightly validate the classification manifest."""
    manifest = yaml.safe_load(MANIFEST_PATH.read_text())
    valid_skill_values = {"portable", "claude-code-only", "exclude"}
    bad = {k: v for k, v in manifest["skills"].items() if v not in valid_skill_values}
    if bad:
        raise ValueError(f"manifest.yaml has invalid skill classifications: {bad}")
    return manifest


def copy_agent(name: str, dest_dir: Path) -> None:
    """Copy one agent .md file, following symlinks to their real content."""
    src = (AGENTS_DIR / f"{name}.md").resolve(strict=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / f"{name}.md")


def copy_skill(name: str, dest_dir: Path) -> None:
    """Copy one skill directory, following symlinks to their real content."""
    src = (SKILLS_DIR / name).resolve(strict=True)
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(
            f"skill '{name}' resolved to {src}, which has no SKILL.md"
        )
    dest = dest_dir / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def build_plugin(
    plugin_name: str, plugin_spec: dict, manifest: dict, out_dir: Path
) -> dict:
    """Build one plugin's directory tree; return its marketplace entry."""
    plugin_dir = out_dir / "plugins" / plugin_name

    write_json(
        plugin_dir / ".claude-plugin" / "plugin.json",
        {
            "name": plugin_name,
            "description": plugin_spec["description"],
            "author": {"name": OWNER_NAME},
        },
    )

    agent_count = 0
    if plugin_spec.get("include_agents"):
        for agent_name in manifest["agents"]:
            copy_agent(agent_name, plugin_dir / "agents")
            agent_count += 1

    allowed = set(plugin_spec["skill_classifications"])
    skill_count = 0
    for skill_name, classification in manifest["skills"].items():
        if classification in allowed:
            copy_skill(skill_name, plugin_dir / "skills")
            skill_count += 1

    print(f"  {plugin_name}: {agent_count} agents, {skill_count} skills")

    return {
        "name": plugin_name,
        "source": f"./plugins/{plugin_name}",
        "description": plugin_spec["description"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output directory for the built marketplace tree",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    out_dir: Path = args.out.resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    print(f"Building plugins into {out_dir}")
    plugin_entries = [
        build_plugin(name, spec, manifest, out_dir)
        for name, spec in manifest["plugins"].items()
    ]

    write_json(
        out_dir / ".claude-plugin" / "marketplace.json",
        {
            "name": "wff-plugins",
            "owner": {"name": OWNER_NAME},
            "description": "Internal Williams Family Fund Claude Code and claude.ai distribution",
            "plugins": plugin_entries,
        },
    )

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
