"""Tests for the card model and the on-disk markdown format."""

from datetime import date
from pathlib import Path

import pytest

from claude_config.anki.cards import (
    BASIC_MODEL,
    CLOZE_MODEL,
    MAX_CARDS,
    Card,
    CardBatch,
    CardFormatError,
    parse_batch,
    parse_cards,
    read_batch,
    render_batch,
    slugify,
    today,
)

VALID = """---
course: bisc-220
term: fall-2026
lecture: Glycolysis Regulation
date: 2026-09-02
deck: Ariannah::BISC 220::Fall 2026
tags: [bisc-220, metabolism]
status: approved
---

## Card 1
**Q:** Which enzyme catalyzes the rate-limiting step of glycolysis?
**A:** Phosphofructokinase-1

## Card 2
**Cloze:** PFK-1 is activated by {{c1::AMP}}.
**Extra:** Allosteric regulation.
"""


class TestSlugify:
    def test_lowercases_and_hyphenates(self):
        assert slugify("Glycolysis Regulation") == "glycolysis-regulation"

    def test_strips_punctuation_and_edges(self):
        assert slugify("  The Krebs Cycle!!  ") == "the-krebs-cycle"

    def test_empty_input_falls_back(self):
        assert slugify("   ") == "untitled"

    def test_collapses_runs_of_separators(self):
        assert slugify("A -- B__C") == "a-b-c"


class TestParseBatch:
    def test_reads_frontmatter(self):
        batch = parse_batch(VALID)
        assert batch.course == "bisc-220"
        assert batch.term == "fall-2026"
        assert batch.date == date(2026, 9, 2)
        assert batch.deck == "Ariannah::BISC 220::Fall 2026"
        assert batch.tags == ["bisc-220", "metabolism"]
        assert batch.approved is True

    def test_reads_both_card_kinds(self):
        cards = parse_batch(VALID).cards
        assert [c.kind for c in cards] == ["basic", "cloze"]
        assert cards[0].back == "Phosphofructokinase-1"
        assert cards[1].extra == "Allosteric regulation."

    def test_missing_frontmatter_is_rejected(self):
        with pytest.raises(CardFormatError, match="frontmatter"):
            parse_batch("## Card 1\n**Q:** a\n**A:** b\n")

    def test_missing_required_key_is_rejected(self):
        text = VALID.replace("course: bisc-220\n", "")
        with pytest.raises(CardFormatError, match="'course'"):
            parse_batch(text)

    def test_non_iso_date_is_rejected(self):
        text = VALID.replace("date: 2026-09-02", "date: sometime tuesday")
        with pytest.raises(CardFormatError, match="ISO date"):
            parse_batch(text)

    def test_malformed_yaml_is_rejected(self):
        with pytest.raises(CardFormatError, match="valid YAML"):
            parse_batch("---\ncourse: [unclosed\n---\n\n## Card 1\n")

    def test_scalar_frontmatter_is_rejected(self):
        with pytest.raises(CardFormatError, match="mapping"):
            parse_batch("---\njust a string\n---\n")

    def test_status_defaults_to_draft(self):
        text = VALID.replace("status: approved\n", "")
        assert parse_batch(text).approved is False

    def test_status_is_case_insensitive(self):
        text = VALID.replace("status: approved", "status: APPROVED")
        assert parse_batch(text).approved is True


class TestParseCards:
    def test_multiline_answer_is_joined(self):
        body = "## Card 1\n**Q:** Why?\n**A:** First line\nsecond line\n"
        card = parse_cards(body)[0]
        assert card.back == "First line\nsecond line"

    def test_question_with_cloze_marker_becomes_cloze(self):
        body = "## Card 1\n**Q:** The {{c1::liver}} stores glycogen.\n"
        assert parse_cards(body)[0].kind == "cloze"

    def test_long_form_labels_are_accepted(self):
        body = "## Card 1\n**Question:** Why?\n**Answer:** Because.\n"
        card = parse_cards(body)[0]
        assert (card.kind, card.front, card.back) == ("basic", "Why?", "Because.")

    def test_text_label_is_treated_as_cloze(self):
        body = "## Card 1\n**Text:** A {{c1::b}} c.\n"
        assert parse_cards(body)[0].kind == "cloze"

    def test_incomplete_card_is_rejected(self):
        with pytest.raises(CardFormatError, match="Card 1 is incomplete"):
            parse_cards("## Card 1\n**Q:** Question with no answer\n")

    def test_empty_blocks_are_ignored(self):
        assert parse_cards("## Card 1\n\n## Card 2\n**Q:** a\n**A:** b\n") == [
            Card(kind="basic", front="a", back="b")
        ]

    def test_prose_before_first_heading_is_ignored(self):
        body = "Some notes here.\n\n## Card 1\n**Q:** a\n**A:** b\n"
        assert len(parse_cards(body)) == 1

    def test_no_headings_yields_no_cards(self):
        assert parse_cards("just prose\n") == []


class TestRoundTrip:
    def test_render_then_parse_preserves_cards(self):
        original = parse_batch(VALID)
        reparsed = parse_batch(render_batch(original))
        assert reparsed.cards == original.cards

    def test_render_then_parse_preserves_metadata(self):
        original = parse_batch(VALID)
        reparsed = parse_batch(render_batch(original))
        assert (reparsed.course, reparsed.term, reparsed.date, reparsed.deck) == (
            original.course,
            original.term,
            original.date,
            original.deck,
        )

    def test_rendered_file_carries_the_review_prompt(self):
        assert "approved" in render_batch(parse_batch(VALID))

    def test_rendered_file_ends_in_one_newline(self):
        rendered = render_batch(parse_batch(VALID))
        assert rendered.endswith("\n")
        assert not rendered.endswith("\n\n")


class TestCardBatch:
    def _batch(self, count):
        return CardBatch(
            course="bisc-220",
            term="fall-2026",
            lecture="Glycolysis Regulation",
            date=date(2026, 9, 2),
            deck="D",
            cards=[
                Card(kind="basic", front=f"q{i}", back=f"a{i}") for i in range(count)
            ],
        )

    def test_relative_path_uses_course_term_date_slug(self):
        assert self._batch(1).relative_path() == Path(
            "bisc-220/fall-2026/2026-09-02-glycolysis-regulation.md"
        )

    def test_target_volume_has_no_warnings(self):
        assert self._batch(12).volume_warnings() == []

    def test_over_cap_warns(self):
        warnings = self._batch(MAX_CARDS + 1).volume_warnings()
        assert len(warnings) == 1
        assert "over the" in warnings[0]

    def test_under_target_warns_without_blocking(self):
        warnings = self._batch(4).volume_warnings()
        assert len(warnings) == 1
        assert "warning, not a blocker" in warnings[0]

    def test_boundaries_are_inclusive(self):
        assert self._batch(10).volume_warnings() == []
        assert self._batch(MAX_CARDS).volume_warnings() == []


class TestToNote:
    def test_basic_card_uses_basic_model(self):
        note = Card(kind="basic", front="q", back="a").to_note("D", ["t"])
        assert note["modelName"] == BASIC_MODEL
        assert note["fields"] == {"Front": "q", "Back": "a"}
        assert note["deckName"] == "D"
        assert note["tags"] == ["t"]

    def test_cloze_card_uses_cloze_model(self):
        note = Card(kind="cloze", front="{{c1::x}}", extra="e").to_note("D", [])
        assert note["modelName"] == CLOZE_MODEL
        assert note["fields"] == {"Text": "{{c1::x}}", "Back Extra": "e"}

    def test_basic_extra_is_appended_to_the_answer(self):
        note = Card(kind="basic", front="q", back="a", extra="note").to_note("D", [])
        assert note["fields"]["Back"] == "a<br><br><i>note</i>"

    def test_duplicate_checking_is_requested_deck_scoped(self):
        note = Card(kind="basic", front="q", back="a").to_note("D", [])
        assert note["options"]["allowDuplicate"] is False
        assert note["options"]["duplicateScope"] == "deck"
        assert note["options"]["duplicateScopeOptions"]["deckName"] == "D"

    def test_dedupe_key_is_the_first_field(self):
        assert Card(kind="basic", front="q", back="a").dedupe_key == "q"


class TestReadBatch:
    def test_reads_from_disk_and_records_the_path(self, tmp_path):
        path = tmp_path / "cards.md"
        path.write_text(VALID, encoding="utf-8")
        batch = read_batch(path)
        assert batch.source_path == path
        assert len(batch.cards) == 2

    def test_missing_file_is_rejected(self, tmp_path):
        with pytest.raises(CardFormatError, match="No card file"):
            read_batch(tmp_path / "nope.md")


def test_today_returns_a_date():
    assert isinstance(today(), date)


class TestDateCoercion:
    def test_yaml_timestamp_is_reduced_to_a_date(self):
        text = VALID.replace("date: 2026-09-02", "date: 2026-09-02 10:30:00")
        assert parse_batch(text).date == date(2026, 9, 2)

    def test_quoted_iso_string_is_accepted(self):
        text = VALID.replace("date: 2026-09-02", 'date: "2026-09-02"')
        assert parse_batch(text).date == date(2026, 9, 2)
