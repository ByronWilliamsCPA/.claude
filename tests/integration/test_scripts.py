"""Integration tests for scripts/check_type_hints.py and tools/validate_front_matter.py.

These tests exercise the scripts' core functions using real files in temporary
directories, covering happy paths, autofixes, and the CWD-based security guard.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import types

import pytest

# ---------------------------------------------------------------------------
# Module loading helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent


def _load_module(file_path: Path) -> types.ModuleType:
    """Load a Python file as a module by absolute path.

    Args:
        file_path: Absolute path to the Python file to load.

    Returns:
        Loaded module object.
    """
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module_name = f"_test_loaded_{file_path.stem}"
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="module")
def check_type_hints() -> types.ModuleType:
    """Load scripts/check_type_hints.py as a module.

    Returns:
        The check_type_hints module.
    """
    return _load_module(_REPO_ROOT / "scripts" / "check_type_hints.py")


@pytest.fixture(scope="module")
def validate_front_matter() -> types.ModuleType:
    """Load tools/validate_front_matter.py as a module.

    Adds tools/ to sys.path so frontmatter_contract (a sibling package) is
    importable during module load.

    Returns:
        The validate_front_matter module.
    """
    tools_dir = str(_REPO_ROOT / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    return _load_module(_REPO_ROOT / "tools" / "validate_front_matter.py")


# ---------------------------------------------------------------------------
# check_type_hints integration tests
# ---------------------------------------------------------------------------


class TestCheckTypeHints:
    """Integration tests for scripts/check_type_hints.py."""

    @pytest.mark.integration
    def test_violation_detected_without_future_import(
        self,
        tmp_path: Path,
        check_type_hints: types.ModuleType,
    ) -> None:
        """Verify check_file detects union syntax missing the future import.

        Args:
            tmp_path: Pytest temporary directory.
            check_type_hints: Loaded check_type_hints module.
        """
        py_file = tmp_path / "violation.py"
        py_file.write_text(
            'def greet(name: str | None) -> str:\n    return name or ""\n'
        )

        is_compliant, message = check_type_hints.check_file(py_file)

        assert not is_compliant
        assert "future" in message.lower() or "union" in message.lower()

    @pytest.mark.integration
    def test_compliant_with_future_import(
        self,
        tmp_path: Path,
        check_type_hints: types.ModuleType,
    ) -> None:
        """Verify check_file passes when the future import accompanies union syntax.

        Args:
            tmp_path: Pytest temporary directory.
            check_type_hints: Loaded check_type_hints module.
        """
        py_file = tmp_path / "compliant.py"
        py_file.write_text(
            "from __future__ import annotations\n\n"
            'def greet(name: str | None) -> str:\n    return name or ""\n'
        )

        is_compliant, message = check_type_hints.check_file(py_file)

        assert is_compliant
        assert message == "OK"

    @pytest.mark.integration
    def test_no_union_syntax_passes(
        self,
        tmp_path: Path,
        check_type_hints: types.ModuleType,
    ) -> None:
        """Verify check_file passes a file with no union syntax.

        Args:
            tmp_path: Pytest temporary directory.
            check_type_hints: Loaded check_type_hints module.
        """
        py_file = tmp_path / "no_union.py"
        py_file.write_text("def greet(name: str) -> str:\n    return name\n")

        is_compliant, _ = check_type_hints.check_file(py_file)

        assert is_compliant

    @pytest.mark.integration
    def test_add_future_import_fixes_violation(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        check_type_hints: types.ModuleType,
    ) -> None:
        """Verify add_future_import inserts the future import into a violating file.

        Args:
            tmp_path: Pytest temporary directory.
            monkeypatch: Pytest monkeypatch fixture.
            check_type_hints: Loaded check_type_hints module.
        """
        monkeypatch.chdir(tmp_path)
        py_file = tmp_path / "fix_me.py"
        py_file.write_text(
            'def greet(name: str | None) -> str:\n    return name or ""\n'
        )

        assert not check_type_hints.check_file(py_file)[0], (
            "precondition: file is non-compliant"
        )

        result = check_type_hints.add_future_import(py_file)

        assert result is True
        assert check_type_hints.check_file(py_file)[0], (
            "file should be compliant after fix"
        )
        assert "from __future__ import annotations" in py_file.read_text()

    @pytest.mark.integration
    def test_add_future_import_rejects_path_outside_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        check_type_hints: types.ModuleType,
    ) -> None:
        """Verify add_future_import rejects paths outside the current directory.

        Args:
            tmp_path: Pytest temporary directory.
            monkeypatch: Pytest monkeypatch fixture.
            check_type_hints: Loaded check_type_hints module.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        outside_file = tmp_path / "outside.py"
        outside_file.write_text("x: int | str = 1\n")

        result = check_type_hints.add_future_import(outside_file)

        assert result is False
        assert "from __future__ import annotations" not in outside_file.read_text()


# ---------------------------------------------------------------------------
# validate_front_matter integration tests
# ---------------------------------------------------------------------------


class TestValidateFrontMatter:
    """Integration tests for tools/validate_front_matter.py."""

    @pytest.mark.integration
    def test_parse_front_matter_valid_file(
        self,
        tmp_path: Path,
        validate_front_matter: types.ModuleType,
    ) -> None:
        """Verify parse_front_matter extracts metadata from a valid file.

        Args:
            tmp_path: Pytest temporary directory.
            validate_front_matter: Loaded validate_front_matter module.
        """
        md_file = tmp_path / "doc.md"
        md_file.write_text(
            "---\ntitle: Test Doc\npurpose: A test document.\n---\n\nBody text.\n"
        )

        meta, content = validate_front_matter.parse_front_matter(md_file)

        assert meta is not None
        assert meta.get("title") == "Test Doc"
        assert "Body text." in content

    @pytest.mark.integration
    def test_parse_front_matter_no_front_matter(
        self,
        tmp_path: Path,
        validate_front_matter: types.ModuleType,
    ) -> None:
        """Verify parse_front_matter returns empty dict for a file with no front matter.

        Args:
            tmp_path: Pytest temporary directory.
            validate_front_matter: Loaded validate_front_matter module.
        """
        md_file = tmp_path / "bare.md"
        md_file.write_text("# Just a heading\n\nNo front matter here.\n")

        meta, _ = validate_front_matter.parse_front_matter(md_file)

        assert meta == {}

    @pytest.mark.integration
    def test_autofix_normalizes_hyphenated_tags(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        validate_front_matter: types.ModuleType,
    ) -> None:
        """Verify autofix_front_matter converts hyphenated tags to snake_case.

        Args:
            tmp_path: Pytest temporary directory.
            monkeypatch: Pytest monkeypatch fixture.
            validate_front_matter: Loaded validate_front_matter module.
        """
        monkeypatch.chdir(tmp_path)
        md_file = tmp_path / "tags.md"
        md_file.write_text(
            "---\ntitle: Test\ntags:\n  - ci-cd\n  - my tag\n---\n\nBody.\n"
        )

        changed = validate_front_matter.autofix_front_matter(md_file)

        assert changed is True
        content = md_file.read_text()
        assert "ci_cd" in content
        assert "my_tag" in content

    @pytest.mark.integration
    def test_autofix_adds_terminal_punctuation_to_purpose(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        validate_front_matter: types.ModuleType,
    ) -> None:
        """Verify autofix_front_matter appends a period to a bare purpose value.

        Args:
            tmp_path: Pytest temporary directory.
            monkeypatch: Pytest monkeypatch fixture.
            validate_front_matter: Loaded validate_front_matter module.
        """
        monkeypatch.chdir(tmp_path)
        md_file = tmp_path / "purpose.md"
        md_file.write_text("---\ntitle: Test\npurpose: A test document\n---\n\nBody.\n")

        changed = validate_front_matter.autofix_front_matter(md_file)

        assert changed is True
        assert "A test document." in md_file.read_text()

    @pytest.mark.integration
    def test_autofix_rejects_path_outside_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        validate_front_matter: types.ModuleType,
    ) -> None:
        """Verify autofix_front_matter rejects paths outside the current directory.

        Args:
            tmp_path: Pytest temporary directory.
            monkeypatch: Pytest monkeypatch fixture.
            validate_front_matter: Loaded validate_front_matter module.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        outside_file = tmp_path / "outside.md"
        outside_file.write_text("---\ntitle: Test\ntags:\n  - ci-cd\n---\n\nBody.\n")

        result = validate_front_matter.autofix_front_matter(outside_file)

        assert result is False
        assert "ci-cd" in outside_file.read_text(), "original file should be unchanged"
