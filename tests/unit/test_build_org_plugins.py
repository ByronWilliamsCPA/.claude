"""Unit tests for scripts/org-plugins/build_org_plugins.py.

Covers the manifest-shape validation, the source-containment guard, the
output-directory guard, and a consistency check that every source the real
manifest names still resolves (the pre-commit hook runs that last test).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import types

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "org-plugins" / "build_org_plugins.py"


def _load() -> types.ModuleType:
    """Load build_org_plugins.py as a module by absolute path."""
    spec = importlib.util.spec_from_file_location("build_org_plugins", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_test_build_org_plugins"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod() -> types.ModuleType:
    """The build_org_plugins module, loaded once per test module."""
    return _load()


def _write_manifest(tmp_path: Path, text: str) -> Path:
    """Write a manifest fixture and return its path."""
    path = tmp_path / "manifest.yaml"
    path.write_text(text)
    return path


def test_load_manifest_rejects_non_mapping(
    mod: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A top-level sequence is not a valid manifest."""
    monkeypatch.setattr(mod, "MANIFEST_PATH", _write_manifest(tmp_path, "- a\n- b\n"))
    with pytest.raises(ValueError, match="must be a mapping"):
        mod.load_manifest()


def test_load_manifest_rejects_missing_keys(
    mod: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Omitting a required top-level key fails with a clear message."""
    monkeypatch.setattr(mod, "MANIFEST_PATH", _write_manifest(tmp_path, "skills: {}\n"))
    with pytest.raises(ValueError, match="missing required keys"):
        mod.load_manifest()


def test_load_manifest_rejects_bad_classification(
    mod: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unrecognised skill classification is rejected."""
    text = "agents: []\nplugins: {}\nskills:\n  foo: sometimes\n"
    monkeypatch.setattr(mod, "MANIFEST_PATH", _write_manifest(tmp_path, text))
    with pytest.raises(ValueError, match="invalid skill classifications"):
        mod.load_manifest()


def test_load_manifest_accepts_valid(
    mod: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A well-formed manifest loads and round-trips its keys."""
    text = "agents: []\nplugins: {}\nskills:\n  foo: portable\n"
    monkeypatch.setattr(mod, "MANIFEST_PATH", _write_manifest(tmp_path, text))
    manifest = mod.load_manifest()
    assert manifest["skills"] == {"foo": "portable"}


def test_reject_unsafe_source_escapes_repo(mod: types.ModuleType) -> None:
    """A source resolving outside the repo is refused."""
    with pytest.raises(ValueError, match="outside the repository"):
        mod._reject_unsafe_source(Path("/etc/passwd"), "evil")


def test_reject_unsafe_source_vendored(mod: types.ModuleType) -> None:
    """A source resolving into .submodules is refused."""
    vendored = mod.SUBMODULES_DIR / "superpowers" / "skills" / "brainstorming"
    with pytest.raises(ValueError, match=r"\.submodules"):
        mod._reject_unsafe_source(vendored, "brainstorming")


def test_reject_unsafe_source_in_repo_ok(mod: types.ModuleType) -> None:
    """An in-repo, non-vendored source passes the guard."""
    mod._reject_unsafe_source(mod.SKILLS_DIR / "receiving-code-review", "ok")


def test_prepare_out_dir_refuses_repo_root(mod: types.ModuleType) -> None:
    """--out at the repository root is refused (rmtree footgun)."""
    with pytest.raises(ValueError, match="repository root or an ancestor"):
        mod._prepare_out_dir(_REPO_ROOT)


def test_prepare_out_dir_refuses_home(mod: types.ModuleType) -> None:
    """--out at the home directory (an ancestor of the repo) is refused."""
    with pytest.raises(ValueError, match="repository root or an ancestor"):
        mod._prepare_out_dir(Path.home())


def test_prepare_out_dir_creates_dedicated_dir(
    mod: types.ModuleType, tmp_path: Path
) -> None:
    """A dedicated build directory is accepted and (re)created."""
    target = tmp_path / "build"
    result = mod._prepare_out_dir(target)
    assert result.is_dir()
    assert result == target.resolve()


def test_validate_sources_flags_missing_file(mod: types.ModuleType) -> None:
    """A manifest naming an agent with no file fails validation."""
    manifest = {"agents": ["does-not-exist-xyz"], "skills": {}, "plugins": {}}
    with pytest.raises(FileNotFoundError):
        mod.validate_sources(manifest)


def test_validate_sources_counts_zero_when_all_excluded(
    mod: types.ModuleType,
) -> None:
    """Excluded skills and no agents yield a zero shippable count."""
    manifest = {"agents": [], "skills": {"foo": "exclude"}, "plugins": {}}
    assert mod.validate_sources(manifest) == 0


def test_real_manifest_sources_resolve(mod: types.ModuleType) -> None:
    """Every source the committed manifest names must still exist.

    This is the consistency guard the org-plugin-manifest-consistency
    pre-commit hook runs: a change that deletes an agent or skill the
    manifest still lists (for example a concurrent cleanup PR) fails here
    instead of breaking the post-merge build.
    """
    count = mod.validate_sources(mod.load_manifest())
    assert count > 0
