#!/usr/bin/env python3
"""Lint .claude/agents/*.md frontmatter against the reviewer-pin policy.

Rules (review 6.3). R5 (description lacks an invocation cue) was dropped
before adoption: it fired on 47 of the 63 agents, and a check that noisy
trains readers to ignore the entire report.

  R1 error  name, description, model, tools all present; demoted to a
            "vendored: " WARN when the file is a symlink, because vendored
            frontmatter is upstream-owned per the submodule-isolation policy
            (see the vendored-agent exception in .claude/rules/supervisor.md)
  R2 error  model in {haiku, sonnet, opus, fable, inherit}; demoted to a
            "vendored: " WARN for symlinks, same rationale as R1
  R3 error  reviewer-shaped agents must not use model: inherit,
            unless symlinked from .submodules/ and named in VENDOR_EXCEPTIONS
            (four sanctioned exceptions; see the vendored-agent exception in
            .claude/rules/supervisor.md)
  R4 warn   reviewer-shaped agents granting Write or Edit
Exit 1 on any error; warnings print but exit 0. Non-symlinked files keep
all rules at full strength.
"""

import re
import sys
from pathlib import Path

MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}
VENDOR_EXCEPTIONS = {
    "silent-failure-hunter",
    "type-design-analyzer",
    "comment-analyzer",
    "pr-test-analyzer",
}
REVIEWER_SHAPE = re.compile(r"\breview|audit|validat|verif", re.IGNORECASE)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the YAML-ish frontmatter block from an agent markdown file.

    Args:
        text: Full file contents of the agent markdown file.

    Returns:
        A dict mapping frontmatter field names to their raw string values.
    """
    if not text.startswith("---"):
        return {}
    try:
        block = text.split("---", 2)[1]
    except IndexError:
        return {}
    fields = {}
    for line in block.splitlines():
        match = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def lint(path: Path) -> tuple[list[str], list[str]]:
    """Lint a single agent markdown file against rules R1-R4.

    R1 and R2 are demoted from error to a "vendored: "-prefixed warning when
    the file is a symlink (vendored, upstream-owned frontmatter). R3-R4 apply
    identically to symlinked and regular files.

    Args:
        path: Path to the agent markdown file to lint.

    Returns:
        A tuple of (errors, warnings) lists of human-readable finding strings.
    """
    errors, warnings = [], []
    if path.name == "CLAUDE.md":
        return errors, warnings
    vendored = path.is_symlink()
    if vendored and not path.exists():
        # Dangling symlink: the submodule is not checked out. CI does not pass
        # submodules: true to actions/checkout, so every vendored agent link
        # dangles there. Returning early keeps the linter usable in that
        # context instead of raising FileNotFoundError on the first one.
        return errors, warnings
    prefix = "vendored: " if vendored else ""
    # encoding is explicit because agent frontmatter contains non-ASCII text.
    # Path.read_text() otherwise defaults to the locale encoding, which is
    # cp1252 on Windows runners and raises UnicodeDecodeError there while
    # passing on Linux and macOS.
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    missing = [k for k in ("name", "description", "model", "tools") if k not in fm]
    if missing:
        finding = f"R1 {path.name}: {prefix}missing {', '.join(missing)}"
        if vendored:
            warnings.append(finding)
        else:
            errors.append(finding)
            return errors, warnings
    model = fm.get("model")
    if model is not None and model not in MODELS:
        finding = f"R2 {path.name}: {prefix}unknown model '{model}'"
        (warnings if vendored else errors).append(finding)
    description = fm.get("description", "")
    reviewerish = bool(REVIEWER_SHAPE.search(description))
    if reviewerish and model == "inherit":
        stem = path.name.removesuffix(".md")
        if not (vendored and stem in VENDOR_EXCEPTIONS):
            errors.append(f"R3 {path.name}: reviewer on model: inherit")
    if reviewerish and re.search(r'"(Write|Edit)"', fm.get("tools", "")):
        warnings.append(f"R4 {path.name}: reviewer granted Write/Edit")
    return errors, warnings


def main(argv: list[str]) -> int:
    """Lint all agent markdown files given on the command line.

    Args:
        argv: List of file path arguments (typically .claude/agents/*.md).

    Returns:
        1 if any file produced an error finding, 0 otherwise.
    """
    all_errors, all_warnings = [], []
    for arg in argv:
        errors, warnings = lint(Path(arg))
        all_errors += errors
        all_warnings += warnings
    for line in all_warnings:
        print(f"WARN {line}")
    for line in all_errors:
        print(f"ERROR {line}")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
