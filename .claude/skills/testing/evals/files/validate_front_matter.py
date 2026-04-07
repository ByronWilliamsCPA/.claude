"""Front matter parser for Markdown files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter


def parse_front_matter(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Parse YAML front matter from a Markdown file.

    Args:
        path: Path to a Markdown file.

    Returns:
        Tuple of (metadata_dict, content_string).
        Metadata is None if the file has no front matter or cannot be parsed.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        post = frontmatter.load(path)
        meta = post.metadata if isinstance(post.metadata, dict) else {}
        return meta, post.content or ""
    except Exception:
        return None, ""


def extract_title(path: Path) -> str | None:
    """Extract the title field from a file's front matter.

    Args:
        path: Path to a Markdown file.

    Returns:
        The title string, or None if absent or unparseable.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    meta, _ = parse_front_matter(path)
    if meta is None:
        return None
    return meta.get("title")
