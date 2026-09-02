"""Tests for draft, push and export orchestration."""

from datetime import date
from pathlib import Path

import pytest

from claude_config.anki.cards import MAX_CARDS, Card, CardBatch, CardFormatError
from claude_config.anki.pipeline import (
    DEFAULT_ROOT_DECK,
    PipelineError,
    card_source_root,
    deck_query,
    ensure_deck,
    existing_notes,
    export_collection,
    push_batch,
    resolve_card_file,
    root_deck,
    write_draft,
)

REWORDED = (
    "Which enzyme catalyzes the rate-limiting step of glycolysis?",
    "What enzyme catalyzes glycolysis's rate-limiting step?",
)


def make_batch(count=12, status="approved", cards=None):
    return CardBatch(
        course="bisc-220",
        term="fall-2026",
        lecture="Glycolysis Regulation",
        date=date(2026, 9, 2),
        deck="Ariannah::BISC 220::Fall 2026",
        tags=["bisc-220"],
        status=status,
        cards=cards
        if cards is not None
        else [
            Card(kind="basic", front=f"Distinct question {i} here?", back=f"Answer {i}")
            for i in range(count)
        ],
    )


class TestConfigResolution:
    def test_source_root_reads_the_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANKI_SOURCE_ROOT", str(tmp_path))
        assert card_source_root() == tmp_path

    def test_source_root_expands_a_tilde(self, monkeypatch):
        monkeypatch.setenv("ANKI_SOURCE_ROOT", "~/cards")
        assert "~" not in str(card_source_root())

    def test_source_root_has_a_default(self, monkeypatch):
        monkeypatch.delenv("ANKI_SOURCE_ROOT", raising=False)
        assert card_source_root().name == "premed-anki-source"

    def test_root_deck_reads_the_env_var(self, monkeypatch):
        monkeypatch.setenv("ANKI_ROOT_DECK", "Custom")
        assert root_deck() == "Custom"

    def test_root_deck_has_a_default(self, monkeypatch):
        monkeypatch.delenv("ANKI_ROOT_DECK", raising=False)
        assert root_deck() == DEFAULT_ROOT_DECK


class TestDeckQuery:
    def test_quotes_the_deck_name(self):
        assert deck_query("A::B") == 'deck:"A::B"'

    def test_strips_embedded_quotes(self):
        assert deck_query('A"B') == 'deck:"AB"'


class TestWriteDraft:
    def test_writes_to_the_conventional_path(self, tmp_path):
        path = write_draft(make_batch(), root=tmp_path)
        assert path.relative_to(tmp_path) == Path(
            "bisc-220/fall-2026/2026-09-02-glycolysis-regulation.md"
        )

    def test_creates_intermediate_directories(self, tmp_path):
        assert write_draft(make_batch(), root=tmp_path).is_file()

    def test_records_the_path_on_the_batch(self, tmp_path):
        batch = make_batch()
        path = write_draft(batch, root=tmp_path)
        assert batch.source_path == path

    def test_refuses_to_clobber_by_default(self, tmp_path):
        write_draft(make_batch(), root=tmp_path)
        with pytest.raises(PipelineError, match="already exists"):
            write_draft(make_batch(), root=tmp_path)

    def test_overwrite_replaces_the_file(self, tmp_path):
        write_draft(make_batch(), root=tmp_path)
        path = write_draft(make_batch(count=11), root=tmp_path, overwrite=True)
        assert "Distinct question 10" in path.read_text()


class TestEnsureDeck:
    def test_creates_a_missing_deck(self, fake_anki):
        assert ensure_deck(fake_anki, "New::Deck") is True
        assert fake_anki.created == ["New::Deck"]

    def test_leaves_an_existing_deck_alone(self, fake_anki):
        assert ensure_deck(fake_anki, "Ariannah") is False
        assert fake_anki.created == []


class TestExistingNotes:
    def test_returns_note_ids_with_first_field_text(self, fake_anki):
        fake_anki.notes = ["question one", "question two"]
        assert existing_notes(fake_anki, "D") == [
            (0, "question one"),
            (1, "question two"),
        ]

    def test_empty_deck_yields_nothing(self, fake_anki):
        assert existing_notes(fake_anki, "D") == []


class TestPushGate:
    def test_draft_status_is_refused(self, fake_anki):
        with pytest.raises(PipelineError, match="still marked 'status: draft'"):
            push_batch(fake_anki, make_batch(status="draft"))

    def test_refusal_names_the_source_file(self, fake_anki, tmp_path):
        batch = make_batch(status="draft")
        batch.source_path = tmp_path / "cards.md"
        with pytest.raises(PipelineError, match=r"cards\.md"):
            push_batch(fake_anki, batch)

    def test_nothing_is_added_when_the_gate_refuses(self, fake_anki):
        with pytest.raises(PipelineError):
            push_batch(fake_anki, make_batch(status="draft"))
        assert fake_anki.added == []


class TestPushVolumeCap:
    def test_over_cap_is_refused(self, fake_anki):
        with pytest.raises(PipelineError, match="over the"):
            push_batch(fake_anki, make_batch(count=MAX_CARDS + 1))

    def test_allow_overflow_permits_it(self, fake_anki):
        report = push_batch(
            fake_anki, make_batch(count=MAX_CARDS + 1), allow_overflow=True
        )
        assert report.added_count == MAX_CARDS + 1

    def test_forcing_duplicates_does_not_lift_the_cap(self, fake_anki):
        with pytest.raises(PipelineError, match="over the"):
            push_batch(
                fake_anki, make_batch(count=MAX_CARDS + 1), force_duplicates=True
            )

    def test_under_target_warns_but_still_pushes(self, fake_anki):
        report = push_batch(fake_anki, make_batch(count=3))
        assert report.added_count == 3
        assert any("warning, not a blocker" in w for w in report.warnings)


class TestPushBehaviour:
    def test_adds_every_card_to_an_empty_deck(self, fake_anki):
        report = push_batch(fake_anki, make_batch())
        assert report.added_count == 12
        assert len(fake_anki.added) == 12

    def test_creates_the_destination_deck(self, fake_anki):
        push_batch(fake_anki, make_batch())
        assert fake_anki.created == ["Ariannah::BISC 220::Fall 2026"]

    def test_tags_and_deck_reach_the_note_payload(self, fake_anki):
        push_batch(fake_anki, make_batch())
        assert fake_anki.added[0]["tags"] == ["bisc-220"]
        assert fake_anki.added[0]["deckName"] == "Ariannah::BISC 220::Fall 2026"

    def test_syncs_after_a_successful_push(self, fake_anki):
        assert push_batch(fake_anki, make_batch()).synced is True

    def test_no_sync_flag_is_respected(self, fake_anki):
        report = push_batch(fake_anki, make_batch(), sync=False)
        assert report.synced is False
        assert fake_anki.synced is False

    def test_no_sync_when_nothing_was_added(self, fake_anki):
        cards = [Card(kind="basic", front=REWORDED[0], back="PFK-1")]
        fake_anki.notes = [REWORDED[1]]
        report = push_batch(fake_anki, make_batch(cards=cards))
        assert report.added_count == 0
        assert fake_anki.synced is False

    def test_skips_a_reworded_duplicate(self, fake_anki):
        cards = [
            Card(kind="basic", front=REWORDED[0], back="PFK-1"),
            Card(kind="basic", front="A totally separate question?", back="x"),
        ]
        fake_anki.notes = [REWORDED[1]]
        report = push_batch(fake_anki, make_batch(cards=cards))
        assert list(report.skipped) == [1]
        assert report.added_count == 1

    def test_force_duplicates_adds_them_anyway(self, fake_anki):
        cards = [Card(kind="basic", front=REWORDED[0], back="PFK-1")]
        fake_anki.notes = [REWORDED[1]]
        report = push_batch(fake_anki, make_batch(cards=cards), force_duplicates=True)
        assert report.skipped == {}
        assert report.added_count == 1

    def test_skips_an_in_batch_repeat(self, fake_anki):
        cards = [
            Card(kind="basic", front=REWORDED[0], back="PFK-1"),
            Card(kind="basic", front=REWORDED[1], back="PFK-1"),
        ]
        report = push_batch(fake_anki, make_batch(cards=cards))
        assert list(report.skipped) == [2]
        assert report.added_count == 1

    def test_threshold_can_be_loosened(self, fake_anki):
        cards = [Card(kind="basic", front="Which step is rate-limiting?", back="x")]
        fake_anki.notes = [REWORDED[1]]
        strict = push_batch(fake_anki, make_batch(cards=cards))
        assert strict.skipped == {}
        loose = push_batch(fake_anki, make_batch(cards=cards), threshold=0.3)
        assert list(loose.skipped) == [1]

    def test_rejection_by_anki_is_reported(self, fake_anki):
        fake_anki.add_notes = lambda notes: [None for _ in notes]
        report = push_batch(fake_anki, make_batch(count=10))
        assert report.added_count == 0
        assert report.rejected == list(range(1, 11))


class TestPushDryRun:
    def test_writes_nothing(self, fake_anki):
        report = push_batch(fake_anki, make_batch(), dry_run=True)
        assert report.dry_run is True
        assert fake_anki.added == []
        assert fake_anki.created == []
        assert fake_anki.synced is False

    def test_still_reports_duplicates(self, fake_anki):
        cards = [Card(kind="basic", front=REWORDED[0], back="PFK-1")]
        fake_anki.notes = [REWORDED[1]]
        report = push_batch(fake_anki, make_batch(cards=cards), dry_run=True)
        assert list(report.skipped) == [1]


class TestExport:
    def test_writes_an_apkg_named_for_deck_and_date(self, fake_anki, tmp_path):
        path = export_collection(fake_anki, dest_dir=tmp_path, deck="Ariannah")
        assert path.parent == tmp_path
        assert path.name.startswith("ariannah-")
        assert path.suffix == ".apkg"

    def test_creates_the_destination_directory(self, fake_anki, tmp_path):
        target = tmp_path / "onedrive" / "anki"
        export_collection(fake_anki, dest_dir=target, deck="Ariannah")
        assert target.is_dir()

    def test_includes_scheduling_state(self, fake_anki, tmp_path):
        export_collection(fake_anki, dest_dir=tmp_path, deck="Ariannah")
        assert fake_anki.exported[0][2] is True

    def test_missing_destination_is_refused(self, fake_anki, monkeypatch):
        monkeypatch.delenv("ANKI_EXPORT_DIR", raising=False)
        with pytest.raises(PipelineError, match="No export folder configured"):
            export_collection(fake_anki, deck="Ariannah")

    def test_destination_falls_back_to_the_env_var(
        self, fake_anki, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("ANKI_EXPORT_DIR", str(tmp_path))
        assert export_collection(fake_anki, deck="Ariannah").parent == tmp_path

    def test_unknown_deck_is_refused(self, fake_anki, tmp_path):
        with pytest.raises(PipelineError, match="No deck named"):
            export_collection(fake_anki, dest_dir=tmp_path, deck="Nope")

    def test_addon_without_export_support_is_refused(self, fake_anki, tmp_path):
        fake_anki._supports = False
        with pytest.raises(PipelineError, match="does not expose 'exportPackage'"):
            export_collection(fake_anki, dest_dir=tmp_path, deck="Ariannah")

    def test_failed_write_is_reported(self, fake_anki, tmp_path):
        fake_anki.export_result = False
        with pytest.raises(PipelineError, match="did not succeed"):
            export_collection(fake_anki, dest_dir=tmp_path, deck="Ariannah")


class TestResolveCardFile:
    def test_accepts_a_direct_path(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_text("x")
        assert resolve_card_file(str(path)) == path

    def test_accepts_a_root_relative_path(self, tmp_path):
        target = tmp_path / "bisc-220" / "fall-2026" / "a.md"
        target.parent.mkdir(parents=True)
        target.write_text("x")
        assert resolve_card_file("bisc-220/fall-2026/a.md", root=tmp_path) == target

    def test_unknown_reference_is_refused(self, tmp_path):
        with pytest.raises(CardFormatError, match="No card file"):
            resolve_card_file("nope.md", root=tmp_path)
