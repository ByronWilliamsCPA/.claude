"""Tests for first-run setup verification."""

import pytest

from claude_config.anki.connect import AnkiActionError, AnkiUnreachableError
from claude_config.anki.doctor import (
    CheckResult,
    blocking_failures,
    check_anki,
    check_export_dir,
    check_source_root,
    find_config_repo,
    find_git_root,
    run_checks,
)


def by_name(results, name):
    return next(r for r in results if r.name == name)


def make_config_repo(root):
    """Create the three markers that identify the public config repo."""
    (root / "CLAUDE.md").write_text("x")
    (root / ".claude" / "skills").mkdir(parents=True)
    (root / ".git").mkdir()
    return root


@pytest.fixture
def source_repo(tmp_path, monkeypatch):
    """A private card-source repo with cards in a `cards/` subdirectory."""
    repo = tmp_path / "premed-anki-source"
    (repo / ".git").mkdir(parents=True)
    cards = repo / "cards"
    cards.mkdir()
    monkeypatch.setenv("ANKI_SOURCE_ROOT", str(cards))
    return cards


class TestFindConfigRepo:
    def test_detects_a_config_repo_root(self, tmp_path):
        make_config_repo(tmp_path)
        assert find_config_repo(tmp_path) == tmp_path

    def test_detects_a_config_repo_from_a_nested_path(self, tmp_path):
        make_config_repo(tmp_path)
        nested = tmp_path / "anki-source" / "bisc-220"
        nested.mkdir(parents=True)
        assert find_config_repo(nested) == tmp_path

    def test_a_home_directory_is_not_a_config_repo(self, tmp_path):
        """Regression: ~/.claude/skills exists after setup.sh, so a home
        directory holding a ~/CLAUDE.md matched the first two markers and
        wrongly blocked a card source anywhere beneath it. A home directory
        is not a git checkout."""
        (tmp_path / "CLAUDE.md").write_text("x")
        (tmp_path / ".claude" / "skills").mkdir(parents=True)
        repo = tmp_path / "dev" / "premed-anki-source"
        (repo / ".git").mkdir(parents=True)
        assert find_config_repo(repo / "cards") is None

    def test_returns_none_outside_a_config_repo(self, tmp_path):
        plain = tmp_path / "somewhere"
        plain.mkdir()
        assert find_config_repo(plain) is None

    def test_one_marker_alone_is_not_a_config_repo(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("x")
        assert find_config_repo(tmp_path) is None

    def test_a_plain_git_repo_is_not_a_config_repo(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert find_config_repo(tmp_path) is None


class TestCheckSourceRoot:
    def test_healthy_repo_passes_every_check(self, source_repo):
        results = check_source_root()
        assert all(r.ok for r in results)

    def test_unset_variable_warns_without_blocking(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANKI_SOURCE_ROOT", raising=False)
        result = by_name(check_source_root(), "ANKI_SOURCE_ROOT")
        assert result.ok is False
        assert result.fatal is False
        assert "shell profile" in result.detail

    def test_missing_folder_with_no_repo_above_it_blocks(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANKI_SOURCE_ROOT", str(tmp_path / "absent"))
        folder = by_name(check_source_root(), "card source folder")
        assert folder.ok is False
        assert folder.fatal is True
        assert "no git repository above it" in folder.detail

    def test_missing_cards_folder_inside_a_repo_only_warns(self, monkeypatch, tmp_path):
        """The cards folder is created on the first `anki-cards new`, so a
        freshly cloned repo that has no cards yet is not a blocker."""
        repo = tmp_path / "premed-anki-source"
        (repo / ".git").mkdir(parents=True)
        monkeypatch.setenv("ANKI_SOURCE_ROOT", str(repo / "cards"))
        results = check_source_root()
        folder = by_name(results, "card source folder")
        assert folder.ok is False
        assert folder.fatal is False
        assert "created on the first" in folder.detail
        assert blocking_failures(results) == []

    def test_folder_outside_any_repo_blocks(self, monkeypatch, tmp_path):
        root = tmp_path / "plain"
        root.mkdir()
        monkeypatch.setenv("ANKI_SOURCE_ROOT", str(root))
        result = by_name(check_source_root(), "card source is in a git repo")
        assert result.ok is False
        assert result.fatal is True
        assert "not inside a git repository" in result.detail

    def test_git_repo_check_names_the_enclosing_repo(self, source_repo):
        result = by_name(check_source_root(), "card source is in a git repo")
        assert result.ok is True
        assert str(source_repo.parent) in result.detail

    def test_source_inside_the_public_config_repo_blocks(self, monkeypatch, tmp_path):
        make_config_repo(tmp_path)
        root = tmp_path / "anki-source" / "cards"
        root.mkdir(parents=True)
        monkeypatch.setenv("ANKI_SOURCE_ROOT", str(root))
        result = by_name(
            check_source_root(), "card source is separate from the config repo"
        )
        assert result.ok is False
        assert result.fatal is True
        assert "public" in result.detail


class TestFindGitRoot:
    def test_finds_the_repo_from_a_subdirectory(self, tmp_path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "cards" / "bisc-220" / "fall-2026"
        nested.mkdir(parents=True)
        assert find_git_root(nested) == tmp_path

    def test_finds_the_repo_at_the_path_itself(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert find_git_root(tmp_path) == tmp_path

    def test_returns_none_outside_a_repo(self, tmp_path):
        plain = tmp_path / "plain"
        plain.mkdir()
        assert find_git_root(plain) is None

    def test_finds_the_repo_for_a_path_that_does_not_exist_yet(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert find_git_root(tmp_path / "cards") == tmp_path

    def test_a_git_file_counts_as_a_repo(self, tmp_path):
        """Worktrees and submodules carry a .git file, not a directory."""
        (tmp_path / ".git").write_text("gitdir: /elsewhere")
        assert find_git_root(tmp_path / "cards") == tmp_path


class TestCheckExportDir:
    def test_ready_folder_passes(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANKI_EXPORT_DIR", str(tmp_path))
        assert check_export_dir().ok is True

    def test_unset_warns_without_blocking(self, monkeypatch):
        monkeypatch.delenv("ANKI_EXPORT_DIR", raising=False)
        result = check_export_dir()
        assert (result.ok, result.fatal) == (False, False)

    def test_absent_folder_warns_without_blocking(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANKI_EXPORT_DIR", str(tmp_path / "not-yet"))
        result = check_export_dir()
        assert (result.ok, result.fatal) == (False, False)
        assert "created on first export" in result.detail


class TestCheckAnki:
    def test_healthy_collection_passes(self, fake_anki, monkeypatch):
        monkeypatch.delenv("ANKI_ROOT_DECK", raising=False)
        fake_anki.models = ["Basic", "Cloze"]
        results = check_anki(fake_anki)
        assert by_name(results, "Anki connection").ok is True
        assert by_name(results, "note types").ok is True
        assert by_name(results, "root deck").ok is True

    def test_unreachable_anki_short_circuits(self, fake_anki):
        def boom():
            raise AnkiUnreachableError("Anki is not answering. Open Anki.")

        fake_anki.preflight = boom
        results = check_anki(fake_anki)
        assert len(results) == 1
        assert results[0].ok is False
        assert "Open Anki" in results[0].detail

    def test_renamed_note_types_block_with_an_explanation(self, fake_anki):
        fake_anki.models = ["Einfach", "Lucke"]
        result = by_name(check_anki(fake_anki), "note types")
        assert result.ok is False
        assert result.fatal is True
        assert "another language" in result.detail
        assert "Basic" in result.detail

    def test_missing_cloze_alone_is_reported(self, fake_anki):
        fake_anki.models = ["Basic"]
        result = by_name(check_anki(fake_anki), "note types")
        assert result.ok is False
        assert "Cloze" in result.detail

    def test_missing_root_deck_only_warns(self, fake_anki, monkeypatch):
        monkeypatch.setenv("ANKI_ROOT_DECK", "Nonexistent")
        result = by_name(check_anki(fake_anki), "root deck")
        assert (result.ok, result.fatal) == (False, False)
        assert "created on the first push" in result.detail

    def test_absent_export_action_only_warns(self, fake_anki):
        fake_anki._supports = False
        result = by_name(check_anki(fake_anki), "exportPackage action")
        assert (result.ok, result.fatal) == (False, False)
        assert "Update AnkiConnect" in result.detail


class TestAnkiErrorsInsideChecks:
    def test_note_type_lookup_failure_is_reported(self, fake_anki):
        def boom():
            raise AnkiActionError("collection is not open")

        fake_anki.model_names = boom
        result = by_name(check_anki(fake_anki), "note types")
        assert result.ok is False
        assert "collection is not open" in result.detail

    def test_deck_lookup_failure_warns_without_blocking(self, fake_anki):
        def boom():
            raise AnkiActionError("collection is not open")

        fake_anki.deck_names = boom
        result = by_name(check_anki(fake_anki), "root deck")
        assert (result.ok, result.fatal) == (False, False)
        assert "collection is not open" in result.detail


class TestBlockingFailures:
    def test_selects_only_fatal_failures(self):
        results = [
            CheckResult(name="a", ok=True, detail=""),
            CheckResult(name="b", ok=False, detail="", fatal=False),
            CheckResult(name="c", ok=False, detail="", fatal=True),
        ]
        assert [r.name for r in blocking_failures(results)] == ["c"]

    def test_all_passing_yields_nothing(self):
        assert blocking_failures([CheckResult(name="a", ok=True, detail="")]) == []


class TestRunChecks:
    def test_fully_configured_machine_has_no_blockers(
        self, fake_anki, source_repo, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("ANKI_EXPORT_DIR", str(tmp_path / "onedrive"))
        monkeypatch.delenv("ANKI_ROOT_DECK", raising=False)
        assert blocking_failures(run_checks(fake_anki)) == []

    def test_filesystem_checks_run_even_when_anki_is_closed(
        self, fake_anki, source_repo
    ):
        def boom():
            raise AnkiUnreachableError("closed")

        fake_anki.preflight = boom
        results = run_checks(fake_anki)
        assert by_name(results, "card source folder").ok is True
        assert by_name(results, "Anki connection").ok is False
