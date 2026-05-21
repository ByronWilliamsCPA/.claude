#!/usr/bin/env python3
"""Check that files using | union syntax have 'from __future__ import annotations'.

This script enforces a code quality standard to ensure that Python files using
the modern | union type syntax (introduced in Python 3.10) also include the
future annotations import for clarity and consistency.

NOTE: Python 3.14 deprecates 'from __future__ import annotations' (PEP 649),
but it will remain functional until at least Python 3.13 EOL in 2029. This
script will be updated when the ecosystem transitions to PEP 649's deferred
annotation evaluation. For now, continue using the future import for Python
3.10+ compatibility.

Usage:
    python scripts/check_type_hints.py [--fix]

Exit codes:
    0: All checks passed
    1: Violations found (or other errors)
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


class UnionSyntaxVisitor(ast.NodeVisitor):
    """AST visitor to detect | union syntax in type annotations."""

    def __init__(self) -> None:
        self.has_union_syntax = False

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """Visit binary operations to detect | in type contexts."""
        if isinstance(node.op, ast.BitOr):
            # Check if this is likely a type annotation context
            # This is a heuristic - it will catch most cases
            self.has_union_syntax = True
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        """Visit function arguments with annotations."""
        if node.annotation:
            self.visit(node.annotation)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments."""
        if node.annotation:
            self.visit(node.annotation)
        self.generic_visit(node)

    def _visit_function_def(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Shared visitor logic for sync and async function definitions."""
        if node.returns:
            self.visit(node.returns)
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation:
                self.visit(arg.annotation)
        if node.args.vararg and node.args.vararg.annotation:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation:
            self.visit(node.args.kwarg.annotation)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions with return annotations."""
        self._visit_function_def(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self._visit_function_def(node)


def has_future_annotations_import(content: str) -> bool:
    """Check if file has 'from __future__ import annotations'."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False

    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in ast.walk(tree)
    )


def has_union_pipe_syntax(content: str) -> bool:
    """Check if file uses | union syntax in type hints.

    Uses multiple detection methods:
    1. AST parsing to detect BinOp with BitOr in annotation contexts
    2. Regex pattern matching for common type hint patterns
    """
    # Method 1: AST-based detection
    try:
        tree = ast.parse(content)
        visitor = UnionSyntaxVisitor()
        visitor.visit(tree)
        if visitor.has_union_syntax:
            return True
    except SyntaxError:
        pass

    # Method 2: Regex patterns for common type hint usage
    # Match patterns like: ": int | str", "-> bool | None", "[int | float]"
    patterns = [
        r":\s*\w+\s*\|\s*\w+",  # : Type | Type
        r"->\s*\w+\s*\|\s*\w+",  # -> Type | Type
        r"\[\s*\w+\s*\|\s*\w+",  # [Type | Type
        r"=\s*\w+\s*\|\s*\w+",  # = Type | Type (in function params)
    ]

    for pattern in patterns:
        if re.search(pattern, content):
            return True

    return False


def check_file(file_path: Path) -> tuple[bool, str]:
    """Check a single Python file for union syntax compliance.

    Returns:
        (is_compliant, message): Tuple indicating compliance and message
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Error reading file: {e}"

    has_union = has_union_pipe_syntax(content)
    has_import = has_future_annotations_import(content)

    if has_union and not has_import:
        return False, "Uses | union syntax without 'from __future__ import annotations'"

    return True, "OK"


def _advance_past_future_imports(lines: list[str], start: int) -> int:
    """Return the index of the first non-future-import, non-comment line at or after start.

    Scans lines beginning at start, skipping over 'from __future__ import ...'
    lines and blank lines. Stops at the first line that is non-empty and is not
    a future import or a comment. Returns the index of that stopping line, or
    start if no such line exists before end of file.

    Args:
        lines: All lines of the source file.
        start: Index to begin scanning from (inclusive).

    Returns:
        Index of the first content line after any future imports, or start if
        none is found.
    """
    for i, line in enumerate(lines[start:], start=start):
        stripped = line.strip()
        if stripped.startswith("from __future__ import"):
            continue
        if stripped and not stripped.startswith("#"):
            return i
    return start


def _find_insert_index(lines: list[str], content: str) -> int:
    """Find the line index at which to insert 'from __future__ import annotations'.

    Skips past any shebang, module docstring, and existing __future__ imports.
    Returns the integer index at which the new import line should be inserted.

    Args:
        lines: All lines of the source file (with line endings preserved).
        content: Full source file text (used for AST parsing to locate docstrings).

    Returns:
        Integer index at which the new import line should be inserted.
    """
    insert_index = 0

    if lines and lines[0].startswith("#!"):
        insert_index = 1

    tree = ast.parse(content)
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
    ):
        docstring_end = tree.body[0].end_lineno or 0
        insert_index = max(insert_index, docstring_end)

    insert_index = _advance_past_future_imports(lines, insert_index)

    # Clamp to list length; docstring-only files with no trailing newline can
    # leave insert_index equal to len(lines), which is a valid insertion point
    # but must not exceed it.
    return min(insert_index, len(lines))


def add_future_import(file_path: Path) -> bool:
    """Add 'from __future__ import annotations' to a file.

    Returns:
        True if the import was added, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        insert_index = _find_insert_index(lines, content)

        import_line = "from __future__ import annotations\n"
        if insert_index > 0 and not lines[insert_index - 1].strip():
            lines.insert(insert_index, import_line)
        else:
            lines.insert(insert_index, import_line)
            lines.insert(insert_index + 1, "\n")

        # Security: resolve and validate containment, then reconstruct the write
        # target from the trusted CWD base so the written path is not derived
        # from user-controlled input (S2083).
        cwd = Path.cwd()
        resolved_path = file_path.resolve()
        if not resolved_path.is_relative_to(cwd):
            print(
                f"Security: Path {file_path} is outside current directory",
                file=sys.stderr,
            )
            return False
        safe_path = cwd / resolved_path.relative_to(cwd)
        # sonar: false positive pythonsecurity:S2083 (AZ1eBjvzS1usNdOdvc1l): path reconstructed from trusted CWD
        safe_path.write_text("".join(lines), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error adding import to {file_path}: {e}", file=sys.stderr)
        return False


def _collect_python_files(args: argparse.Namespace) -> list[Path]:
    """Collect Python files to check based on parsed arguments.

    Args:
        args: Parsed argparse namespace with src_dir and include_tests fields.

    Returns:
        List of Path objects for Python files to check.
    """
    python_files: list[Path] = []

    if args.src_dir.exists():
        python_files.extend(args.src_dir.rglob("*.py"))

    if args.include_tests:
        tests_dir = Path("tests")
        if tests_dir.exists():
            python_files.extend(tests_dir.rglob("*.py"))

    return python_files


def _handle_violation(
    file_path: Path,
    message: str,
    fix: bool,
) -> tuple[tuple[Path, str] | None, Path | None]:
    """Apply fix or record violation for a single non-compliant file.

    Args:
        file_path: Path to the non-compliant Python file.
        message: Compliance message describing the violation.
        fix: If True, attempt to auto-fix the file.

    Returns:
        Tuple of (violation, fixed_path). Exactly one element is non-None.
        violation is (path, message) when the file was not fixed; fixed_path
        is the path when the file was successfully auto-fixed.
    """
    if fix:
        if add_future_import(file_path):
            print(f"✓ Fixed: {file_path}")
            return None, file_path
        print(f"✗ Failed to fix: {file_path}: {message}", file=sys.stderr)
        return (file_path, message), None
    print(f"✗ {file_path}: {message}", file=sys.stderr)
    return (file_path, message), None


def _process_files(
    python_files: list[Path], fix: bool
) -> tuple[list[tuple[Path, str]], list[Path]]:
    """Check and optionally fix each Python file for future annotations compliance.

    Args:
        python_files: List of Python file paths to process.
        fix: If True, attempt to auto-fix non-compliant files.

    Returns:
        Tuple of (violations, fixed) where violations is a list of (path, message)
        pairs and fixed is a list of successfully auto-fixed paths.
    """
    violations: list[tuple[Path, str]] = []
    fixed: list[Path] = []

    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue
        is_compliant, message = check_file(file_path)
        if not is_compliant:
            violation, fixed_path = _handle_violation(file_path, message, fix)
            if fixed_path is not None:
                fixed.append(fixed_path)
            if violation is not None:
                violations.append(violation)

    return violations, fixed


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for | union syntax with future annotations import"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically add 'from __future__ import annotations' to files",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=Path("src"),
        help="Source directory to check (default: src)",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Also check test files",
    )
    args = parser.parse_args()

    python_files = _collect_python_files(args)
    if not python_files:
        print(f"No Python files found in {args.src_dir}", file=sys.stderr)
        return 1

    violations, fixed = _process_files(python_files, args.fix)

    print()
    if violations:
        print(f"Found {len(violations)} violation(s):")
        for file_path, message in violations:
            print(f"  - {file_path}: {message}")
        print()
        print("Run with --fix to automatically add the import")
        return 1
    if fixed:
        print(f"Fixed {len(fixed)} file(s)")
        return 0
    print("All files compliant ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
