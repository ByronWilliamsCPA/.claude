"""Tests for the anki-cards command line surface."""

from datetime import date

import pytest

from claude_config.anki import cli
from claude_config.anki.cards import MAX_CARDS
from claude_config.anki.connect import AnkiUnreachableError

APPROVED = """---
course: bisc-220
term: fall-2026
lecture: Glycolysis Regulation
date: 2026-09-02
deck: Ariannah::BISC 220::Fall 2026
tags: [bisc-220]
status: approved
---

## Card 1
**Q:** Which enzyme catalyzes the rate-limiting step of glycolysis?
**A:** Phosphofructokinase-1

## Card 2
**Cloze:** PFK-1 is activated by {{c1::AMP}}.
"""


@pytest.fixture
def card_file(tmp_path):
    path = tmp_path / "cards.md"
    path.write_text(APPROVED, encoding="utf-8")
    return path


@pytest.fixture
def wired(monkeypatch, fake_anki, tmp_path):
    """Point the CLI at the fake client and an isolated source root."""
    monkeypatch.setattr(cli, "_client", lambda args: fake_anki)
    monkeypatch.setenv("ANKI_SOURCE_ROOT", str(tmp_path / "source"))
    return fake_anki


class TestCheck:
    def test_reports_version_and_decks(self, wired, capsys):
        assert cli.main(["check"]) == cli.EXIT_OK
        output = capsys.readouterr().out
        assert "API version 6" in output
        assert "Ariannah" in output

    def test_warns_when_export_is_unsupported(self, wired, capsys):
        wired._supports = False
        cli.main(["check"])
        assert "no 'exportPackage'" in capsys.readouterr().out

    def test_unreachable_anki_exits_nonzero_with_guidance(self, monkeypatch, capsys):
        def boom(args):
            raise AnkiUnreachableError("Anki is not answering. Open Anki.")

        monkeypatch.setattr(cli, "_client", boom)
        assert cli.main(["check"]) == cli.EXIT_FAIL
        assert "Open Anki" in capsys.readouterr().err


class TestNew:
    def test_creates_a_file_at_the_conventional_path(self, wired, capsys, tmp_path):
        code = cli.main(["new", "bisc-220", "fall-2026", "Glycolysis Regulation"])
        assert code == cli.EXIT_OK
        expected = (tmp_path / "source" / "bisc-220" / "fall-2026").glob(
            "*-glycolysis-regulation.md"
        )
        assert list(expected)
        assert "Created" in capsys.readouterr().out

    def test_honours_an_explicit_date(self, wired, tmp_path):
        cli.main(
            [
                "new",
                "bisc-220",
                "fall-2026",
                "Krebs Cycle",
                "--date",
                "2026-10-01",
            ]
        )
        target = (
            tmp_path / "source" / "bisc-220" / "fall-2026" / "2026-10-01-krebs-cycle.md"
        )
        assert target.is_file()

    def test_derives_the_deck_from_course_and_term(self, wired, tmp_path):
        cli.main(["new", "bisc-220", "fall-2026", "Krebs Cycle"])
        written = next(
            (tmp_path / "source" / "bisc-220" / "fall-2026").glob("*.md")
        ).read_text()
        assert "deck: Ariannah::bisc-220::fall-2026" in written

    def test_starts_as_draft(self, wired, tmp_path):
        cli.main(["new", "bisc-220", "fall-2026", "Krebs Cycle"])
        written = next(
            (tmp_path / "source" / "bisc-220" / "fall-2026").glob("*.md")
        ).read_text()
        assert "status: draft" in written

    def test_refusing_to_clobber_exits_nonzero(self, wired, capsys):
        cli.main(["new", "bisc-220", "fall-2026", "Krebs Cycle"])
        code = cli.main(["new", "bisc-220", "fall-2026", "Krebs Cycle"])
        assert code == cli.EXIT_FAIL
        assert "already exists" in capsys.readouterr().err


class TestValidate:
    def test_describes_the_batch_without_touching_anki(self, card_file, capsys):
        assert cli.main(["validate", str(card_file)]) == cli.EXIT_OK
        output = capsys.readouterr().out
        assert "2 card(s)" in output
        assert "1 question/answer, 1 cloze" in output
        assert "bisc-220" in output

    def test_reports_the_under_target_warning(self, card_file, capsys):
        cli.main(["validate", str(card_file)])
        assert "Warning:" in capsys.readouterr().out

    def test_flags_an_unapproved_batch(self, tmp_path, capsys):
        path = tmp_path / "draft.md"
        path.write_text(APPROVED.replace("status: approved", "status: draft"))
        cli.main(["validate", str(path)])
        assert "push will refuse" in capsys.readouterr().out

    def test_malformed_file_exits_nonzero(self, tmp_path, capsys):
        path = tmp_path / "bad.md"
        path.write_text("no frontmatter here\n")
        assert cli.main(["validate", str(path)]) == cli.EXIT_FAIL
        assert "frontmatter" in capsys.readouterr().err

    def test_missing_file_exits_nonzero(self, tmp_path, capsys):
        assert cli.main(["validate", str(tmp_path / "gone.md")]) == cli.EXIT_FAIL
        assert "No card file" in capsys.readouterr().err


class TestPush:
    def test_adds_cards_and_reports_the_sync(self, wired, card_file, capsys):
        assert cli.main(["push", str(card_file)]) == cli.EXIT_OK
        output = capsys.readouterr().out
        assert "Added 2 card(s)" in output
        assert "Synced to AnkiWeb" in output

    def test_dry_run_writes_nothing(self, wired, card_file, capsys):
        cli.main(["push", str(card_file), "--dry-run"])
        assert "Dry run: nothing written." in capsys.readouterr().out
        assert wired.added == []

    def test_draft_is_refused_with_instructions(self, wired, tmp_path, capsys):
        path = tmp_path / "draft.md"
        path.write_text(APPROVED.replace("status: approved", "status: draft"))
        assert cli.main(["push", str(path)]) == cli.EXIT_FAIL
        assert "change the status line to 'approved'" in capsys.readouterr().err

    def test_duplicates_are_listed_with_scores(self, wired, card_file, capsys):
        wired.notes = ["What enzyme catalyzes glycolysis's rate-limiting step?"]
        cli.main(["push", str(card_file)])
        output = capsys.readouterr().out
        assert "Skipped 1 near-duplicate(s)" in output
        assert "--force-duplicates" in output

    def test_no_sync_flag_is_reported(self, wired, card_file, capsys):
        cli.main(["push", str(card_file), "--no-sync"])
        assert "Not synced" in capsys.readouterr().out

    def test_anki_rejection_is_reported(self, wired, card_file, capsys):
        wired.add_notes = lambda notes: [None for _ in notes]
        cli.main(["push", str(card_file)])
        assert "Anki declined card(s) 1, 2" in capsys.readouterr().out

    def test_over_cap_is_refused_and_names_the_flag(self, wired, tmp_path, capsys):
        cards = "\n\n".join(
            f"## Card {i}\n**Q:** Distinct question {i} here?\n**A:** Answer {i}"
            for i in range(MAX_CARDS + 1)
        )
        path = tmp_path / "big.md"
        path.write_text(APPROVED.split("## Card 1", maxsplit=1)[0] + cards + "\n")
        assert cli.main(["push", str(path)]) == cli.EXIT_FAIL
        assert "over the" in capsys.readouterr().err


class TestExport:
    def test_writes_an_apkg_and_reports_the_path(self, wired, tmp_path, capsys):
        code = cli.main(
            ["export", "--dest", str(tmp_path / "onedrive"), "--deck", "Ariannah"]
        )
        assert code == cli.EXIT_OK
        assert ".apkg" in capsys.readouterr().out

    def test_missing_destination_exits_nonzero(self, wired, monkeypatch, capsys):
        monkeypatch.delenv("ANKI_EXPORT_DIR", raising=False)
        assert cli.main(["export", "--deck", "Ariannah"]) == cli.EXIT_FAIL
        assert "No export folder configured" in capsys.readouterr().err


class TestParser:
    def test_a_subcommand_is_required(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args([])

    def test_connection_flags_override_the_environment(self, monkeypatch):
        monkeypatch.delenv("ANKI_CONNECT_HOST", raising=False)
        monkeypatch.delenv("ANKI_CONNECT_PORT", raising=False)
        args = cli.build_parser().parse_args(
            ["check", "--host", "10.0.0.2", "--port", "9000"]
        )
        client = cli._client(args)
        assert (client.host, client.port) == ("10.0.0.2", 9000)

    def test_date_flag_parses_iso_dates(self):
        args = cli.build_parser().parse_args(
            ["new", "c", "t", "L", "--date", "2026-09-02"]
        )
        assert args.date == date(2026, 9, 2)

    def test_bad_date_flag_is_rejected(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["new", "c", "t", "L", "--date", "nope"])


class TestDuplicateReportFormatting:
    def test_multiline_match_is_flattened_to_one_line(self, wired, tmp_path, capsys):
        existing = "The three irreversible steps are\ncatalyzed by hexokinase."
        wired.notes = [existing]
        path = tmp_path / "cards.md"
        path.write_text(
            APPROVED.split("## Card 1", maxsplit=1)[0]
            + "## Card 1\n**Cloze:** The three irreversible steps are\n"
            "catalyzed by {{c1::hexokinase}}.\n"
        )
        cli.main(["push", str(path)])
        lines = capsys.readouterr().out.splitlines()
        card_lines = [line for line in lines if line.startswith("  Card 1 (")]
        assert len(card_lines) == 1
        assert "\n" not in card_lines[0]
        assert "steps are catalyzed by" in card_lines[0]
