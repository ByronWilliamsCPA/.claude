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
SUBMODULES_DIR = (REPO_ROOT / ".submodules").resolve()
OWNER_NAME = "Byron Williams"
REQUIRED_MANIFEST_KEYS = ("agents", "skills", "plugins")
VALID_SKILL_VALUES = {"portable", "claude-code-only", "exclude"}


def load_manifest() -> dict:
    """Load and validate the classification manifest.

    Returns:
        The parsed manifest mapping.

    Raises:
        ValueError: If the manifest is not a mapping, omits a required
            top-level key, or lists an unrecognised skill classification.
    """
    manifest = yaml.safe_load(MANIFEST_PATH.read_text())
    if not isinstance(manifest, dict):
        raise ValueError(
            f"manifest.yaml must be a mapping, got {type(manifest).__name__}"
        )
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        raise ValueError(f"manifest.yaml is missing required keys: {missing}")
    bad = {k: v for k, v in manifest["skills"].items() if v not in VALID_SKILL_VALUES}
    if bad:
        raise ValueError(f"manifest.yaml has invalid skill classifications: {bad}")
    return manifest


def _reject_unsafe_source(resolved_src: Path, name: str) -> None:
    """Reject manifest entries whose resolved path is unsafe to ship.

    A manifest entry may be a symlink; ``resolve(strict=True)`` follows it
    without constraining the target. Refuse two cases after resolution: a
    path that escapes the repository entirely (for example a symlink to
    ``/etc/passwd``), and a path inside a vendored submodule, whose
    redistribution is a separate license question this pipeline does not
    answer.

    Args:
        resolved_src: The symlink-resolved source path.
        name: The manifest entry name, used in the error message.

    Raises:
        ValueError: If ``resolved_src`` is outside the repository or inside
            ``.submodules/``.
    """
    if not resolved_src.is_relative_to(REPO_ROOT):
        raise ValueError(
            f"'{name}' resolves outside the repository ({resolved_src}); "
            "refusing to copy content from an unexpected location"
        )
    if resolved_src.is_relative_to(SUBMODULES_DIR):
        raise ValueError(
            f"'{name}' resolves into .submodules ({resolved_src}); vendored "
            "content must not ship through the org-plugin pipeline"
        )


def copy_agent(name: str, dest_dir: Path) -> None:
    """Copy one agent .md file, following symlinks but rejecting vendored targets."""
    src = (AGENTS_DIR / f"{name}.md").resolve(strict=True)
    _reject_unsafe_source(src, name)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / f"{name}.md")


def copy_skill(name: str, dest_dir: Path) -> None:
    """Copy one skill directory, following symlinks but rejecting vendored targets."""
    src = (SKILLS_DIR / name).resolve(strict=True)
    _reject_unsafe_source(src, name)
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
) -> tuple[dict, int]:
    """Build one plugin's directory tree.

    Args:
        plugin_name: The plugin's marketplace name.
        plugin_spec: The plugin's manifest entry.
        manifest: The full parsed manifest.
        out_dir: The build output root.

    Returns:
        A ``(marketplace_entry, item_count)`` pair where ``item_count`` is the
        number of agents plus skills copied for this plugin.
    """
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

    entry = {
        "name": plugin_name,
        "source": f"./plugins/{plugin_name}",
        "description": plugin_spec["description"],
    }
    return entry, agent_count + skill_count


def validate_sources(manifest: dict) -> int:
    """Resolve every shippable source without copying; return the count.

    Confirms each agent and each non-excluded skill exists, resolves inside
    the repository, and is not vendored. Powers ``--check``, which catches a
    manifest that still names a file another change has moved or deleted,
    before a build (or the downstream rsync --delete) would.

    Args:
        manifest: The parsed manifest.

    Returns:
        The number of shippable items (agents plus non-excluded skills).

    Raises:
        FileNotFoundError: If a listed source does not exist, or a skill has
            no SKILL.md.
    """
    count = 0
    for agent_name in manifest["agents"]:
        src = (AGENTS_DIR / f"{agent_name}.md").resolve(strict=True)
        _reject_unsafe_source(src, agent_name)
        count += 1
    for skill_name, classification in manifest["skills"].items():
        if classification == "exclude":
            continue
        src = (SKILLS_DIR / skill_name).resolve(strict=True)
        _reject_unsafe_source(src, skill_name)
        if not (src / "SKILL.md").is_file():
            raise FileNotFoundError(
                f"skill '{skill_name}' resolved to {src}, which has no SKILL.md"
            )
        count += 1
    return count


def _prepare_out_dir(out: Path) -> Path:
    """Resolve and re-create the output directory, refusing unsafe targets.

    ``--out`` is deleted unconditionally before a build, so a typo such as
    ``--out ~`` or ``--out /`` would destroy far more than a prior build.
    Refuse the home directory, a filesystem or drive root, and the repository
    root or any ancestor of it. The first two are named explicitly rather than
    inferred from the repo location: on a system where the checkout does not
    live under ``~`` (e.g. a Windows runner with the repo on ``D:`` and the
    home on ``C:``), ``REPO_ROOT.is_relative_to(home)`` is false, so an ancestor
    check alone would let ``--out ~`` through and delete the home directory.

    Args:
        out: The requested --out path.

    Returns:
        The resolved, freshly-emptied output directory.

    Raises:
        ValueError: If the target is the home directory, a filesystem/drive
            root, or the repository root or one of its ancestors.
    """
    out_dir = out.resolve()
    home = Path.home().resolve()
    drive_root = Path(out_dir.anchor)
    if out_dir in (home, drive_root) or REPO_ROOT.is_relative_to(out_dir):
        raise ValueError(
            f"refusing to use {out_dir} as --out; it is the home directory, a "
            "filesystem root, or the repository root or an ancestor, and --out "
            "is deleted before every build"
        )
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        help="Output directory for the built marketplace tree",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the manifest and its sources without writing output",
    )
    args = parser.parse_args()

    manifest = load_manifest()

    if args.check:
        count = validate_sources(manifest)
        if count == 0:
            raise ValueError("manifest lists no shippable agents or skills")
        print(f"Manifest OK: {count} shippable sources resolve.")
        return 0

    if args.out is None:
        parser.error("--out is required unless --check is given")
    out_dir = _prepare_out_dir(args.out)

    print(f"Building plugins into {out_dir}")
    plugin_entries: list[dict] = []
    total_items = 0
    for name, spec in manifest["plugins"].items():
        entry, item_count = build_plugin(name, spec, manifest, out_dir)
        plugin_entries.append(entry)
        total_items += item_count
    if total_items == 0:
        raise ValueError(
            "build copied no agents or skills; refusing to emit an empty tree "
            "that a downstream rsync --delete would use to wipe the target repo"
        )

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
