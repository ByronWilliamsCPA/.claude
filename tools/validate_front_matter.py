#!/usr/bin/env python3
"""Front matter validator with autofix capabilities.

Note: T201 (print statement) is intentionally disabled for this CLI tool.
This script outputs structured results to stdout/stderr, making print()
the correct approach rather than logging.

This script validates YAML front matter in Markdown documentation files using
Pydantic models. It supports automatic fixing of common issues and enforces
allow-lists for tags and owners.

Usage:
    python tools/validate_front_matter.py docs [--fix] [--emit-json]

Features:
    - Autofix: Normalizes tags to snake_case, adds punctuation to purpose
    - Strict validation: Enforces Pydantic schema and allow-lists
    - Body H1 detection: Warns about redundant headings
    - JSON output: Machine-readable results for CI integration
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from io import StringIO
from pathlib import Path
from typing import Any

import frontmatter
from frontmatter_contract.models import DiscriminatedFM
from pydantic import TypeAdapter, ValidationError
from ruamel.yaml import YAML

# Regular expression to detect body H1 headings
H1_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)

# Create type adapter for validating discriminated union
FM_ADAPTER: TypeAdapter[DiscriminatedFM] = TypeAdapter(DiscriminatedFM)


def load_allowlists(docroot: Path) -> tuple[set[str], set[str]]:
    """Load tag and owner allow-lists from YAML files.

    Args:
        docroot: Root directory containing _data/ subdirectory.

    Returns:
        Tuple of (allowed_tags, allowed_owners) sets.

    Raises:
        FileNotFoundError: If allow-list files don't exist.
        ValueError: If allow-list files are malformed.
    """
    y = YAML(typ="safe")

    tags_file = docroot / "_data" / "tags.yml"
    owners_file = docroot / "_data" / "owners.yml"

    if not tags_file.exists():
        raise FileNotFoundError(f"Tags allow-list not found: {tags_file}")
    if not owners_file.exists():
        raise FileNotFoundError(f"Owners allow-list not found: {owners_file}")

    try:
        tags_data = y.load(tags_file.read_text())
        owners_data = y.load(owners_file.read_text())

        allowed_tags = set(tags_data.get("allowed", []))
        allowed_owners = set(owners_data.get("owners", {}).keys())

        return allowed_tags, allowed_owners
    except Exception as e:
        raise ValueError(f"Error loading allow-lists: {e}") from e


def parse_front_matter(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Parse YAML front matter from a Markdown file.

    Args:
        path: Path to Markdown file.

    Returns:
        Tuple of (metadata_dict, content_string). Metadata is None if parsing fails.
    """
    try:
        post = frontmatter.load(path)
        meta = post.metadata if isinstance(post.metadata, dict) else {}
        return meta, post.content or ""
    except Exception:
        return None, ""


def _fix_tags(data: dict[str, Any]) -> bool:
    """Normalize tags to snake_case in-place.

    Args:
        data: Parsed YAML front matter dict.

    Returns:
        True if any tag was changed, False otherwise.
    """
    if "tags" not in data or not isinstance(data["tags"], list):
        return False

    fixed_tags = []
    for tag in data["tags"]:
        tag_str = str(tag).strip().replace("-", "_").replace(" ", "_")
        tag_str = re.sub(r"__+", "_", tag_str).lower()
        fixed_tags.append(tag_str)

    if fixed_tags == data["tags"]:
        return False

    data["tags"] = fixed_tags
    return True


def _fix_purpose(data: dict[str, Any]) -> bool:
    """Add terminal punctuation to purpose field if missing.

    Args:
        data: Parsed YAML front matter dict.

    Returns:
        True if the purpose field was changed, False otherwise.
    """
    if "purpose" not in data or not isinstance(data["purpose"], str):
        return False

    purpose = data["purpose"].strip()
    if not purpose or purpose[-1] in ".!?":
        return False

    data["purpose"] = purpose + "."
    return True


def autofix_front_matter(path: Path) -> bool:
    """Automatically fix common front matter issues.

    Fixes:
        - Tags: Normalize to snake_case (replace hyphens/spaces, lowercase)
        - Purpose: Add terminal punctuation if missing

    Args:
        path: Path to Markdown file.

    Returns:
        True if changes were made, False otherwise.
    """
    # Security: Validate file path is within expected directory BEFORE reading
    if not path.resolve().is_relative_to(Path.cwd()):
        print(f"Security: Path {path} is outside current directory", file=sys.stderr)
        return False

    text = path.read_text(encoding="utf-8")

    match = re.search(r"^---\n.*?\n---\n", text, flags=re.DOTALL | re.MULTILINE)
    if not match:
        return False

    yrt = YAML(typ="rt")
    yrt.preserve_quotes = True
    yrt.allow_duplicate_keys = False

    yaml_text = text[match.start() + 4 : match.end() - 4]
    try:
        data = yrt.load(yaml_text)
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    try:
        changed = False
        changed |= _fix_tags(data)
        changed |= _fix_purpose(data)
    except Exception as e:
        print(f"autofix failed for {path}: {e}", file=sys.stderr)
        return False

    if changed:
        out = StringIO()
        yrt.dump(data, out)
        new_yaml = out.getvalue().rstrip()
        new_content = f"---\n{new_yaml}\n---\n{text[match.end() :]}"
        # Path validated above via is_relative_to(Path.cwd()); safe to write
        # sonar: false positive pythonsecurity:S2083 (AZ1eBjxNS1usNdOdvc1m): user input is resolved and bounded
        path.write_text(new_content, encoding="utf-8")

    return changed


def validate_file(
    path: Path,
    allowed_tags: set[str],
    allowed_owners: set[str],
    autofix: bool = False,
) -> dict[str, Any]:
    """Validate a single Markdown file.

    Args:
        path: Path to Markdown file.
        allowed_tags: Set of allowed tag values.
        allowed_owners: Set of allowed owner values.
        autofix: If True, attempt to fix common issues before validation.

    Returns:
        Dictionary with validation results:
            - file: str - File path
            - ok: bool - Whether validation passed
            - errors: list[str] - List of error messages
            - fixed: bool - Whether autofix made changes
    """
    errors: list[str] = []
    fixed = False

    # Autofix if requested
    if autofix:
        fixed = autofix_front_matter(path)

    # Parse front matter
    meta, content = parse_front_matter(path)

    if meta is None:
        errors.append("missing or invalid front matter")
        return {"file": str(path), "ok": False, "errors": errors, "fixed": fixed}

    # Check for redundant body H1 (but skip code blocks)
    # Remove code blocks (3+ backticks/tildes, with optional indentation) before checking for H1
    # Pattern handles varying fence lengths (```, ````, ~~~~~, etc.)
    content_without_code = re.sub(
        r"^\s*(`{3,}|~{3,}).*?^\s*\1", "", content, flags=re.DOTALL | re.MULTILINE
    )
    h1_match = H1_RE.search(content_without_code)
    if h1_match:
        h1_text = h1_match.group(1).strip()
        errors.append(
            f"redundant H1 found: '# {h1_text}' — remove it; 'title' renders automatically"
        )

    # Strict Pydantic validation
    try:
        FM_ADAPTER.validate_python(meta)
    except ValidationError as e:
        for err in e.errors():
            loc = "/".join(map(str, err["loc"]))
            errors.append(f"{loc}: {err['msg']}")

    # Validate tags against allow-list
    if "tags" in meta and isinstance(meta["tags"], list):
        unknown_tags = [t for t in meta["tags"] if t not in allowed_tags]
        if unknown_tags:
            errors.append(f"unknown tag(s): {unknown_tags}")

    # Validate owner against allow-list
    if "owner" in meta and meta["owner"] not in allowed_owners:
        errors.append(f"unknown owner '{meta['owner']}'")

    ok = not errors
    return {"file": str(path), "ok": ok, "errors": errors, "fixed": fixed}


def _collect_md_files(paths: list[str]) -> list[Path]:
    """Collect Markdown files from the given path strings.

    Args:
        paths: List of file or directory path strings.

    Returns:
        List of Path objects for Markdown files found.
    """
    md_files: list[Path] = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_dir():
            md_files.extend(path.rglob("*.md"))
        elif path.suffix.lower() == ".md":
            md_files.append(path)
    return md_files


def _output_results(results: list[dict[str, Any]], emit_json: bool) -> None:
    """Print validation results to stdout.

    Args:
        results: List of per-file validation result dicts.
        emit_json: If True, emit results as a JSON array; otherwise use text format.
    """
    if emit_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for result in results:
            status = "OK" if result["ok"] else "ISSUES"
            fixed_marker = " [FIXED]" if result.get("fixed", False) else ""
            print(f"{result['file']}: {status}{fixed_marker}")
            for error in result["errors"]:
                print(f"  - {error}")


def main() -> int:
    """Main entry point for the validation script.

    Returns:
        Exit code: 0 if all files pass, 1 if any file has errors.
    """
    parser = argparse.ArgumentParser(
        description="Validate and autofix YAML front matter in Markdown files"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to Markdown files or directories to validate",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix common issues (tags, punctuation)",
    )
    parser.add_argument(
        "--emit-json",
        action="store_true",
        help="Output results as JSON for CI integration",
    )
    args = parser.parse_args()

    md_files = _collect_md_files(args.paths)
    if not md_files:
        print("No Markdown files found", file=sys.stderr)
        return 1

    docroot = next(
        (p for p in map(Path, args.paths) if p.name == "docs"),
        Path("docs"),
    )

    try:
        allowed_tags, allowed_owners = load_allowlists(docroot)
    except Exception as e:
        print(f"Error loading allow-lists: {e}", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    failed = False
    for md_file in sorted(md_files):
        result = validate_file(md_file, allowed_tags, allowed_owners, args.fix)
        results.append(result)
        failed |= not result["ok"]

    _output_results(results, args.emit_json)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
