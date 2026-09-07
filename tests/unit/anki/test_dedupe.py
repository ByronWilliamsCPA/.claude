"""Tests for near-duplicate detection."""

import pytest

from claude_config.anki.cards import Card
from claude_config.anki.dedupe import (
    DEFAULT_THRESHOLD,
    find_duplicates,
    find_internal_duplicates,
    first_field,
    normalize,
    similarity,
    tokens,
)

REWORDED = (
    "Which enzyme catalyzes the rate-limiting step of glycolysis?",
    "What enzyme catalyzes glycolysis's rate-limiting step?",
)


class TestNormalize:
    def test_strips_html_tags(self):
        assert normalize("<b>PFK-1</b> is<br>an enzyme") == "pfk 1 is an enzyme"

    def test_unwraps_cloze_markers(self):
        assert normalize("Activated by {{c1::AMP}}.") == "activated by amp"

    def test_unwraps_cloze_hints(self):
        assert normalize("{{c1::AMP::the hint}} works") == "amp works"

    def test_decodes_nbsp(self):
        assert normalize("a&nbsp;b") == "a b"

    def test_collapses_whitespace(self):
        assert normalize("  a   \n  b  ") == "a b"


class TestTokens:
    def test_drops_stopwords(self):
        assert tokens("the enzyme of glycolysis") == frozenset({"enzyme", "glycolysis"})

    def test_empty_text_yields_no_tokens(self):
        assert tokens("the of and") == frozenset()


class TestSimilarity:
    def test_identical_text_scores_one(self):
        assert (
            similarity("PFK-1 regulates glycolysis", "PFK-1 regulates glycolysis")
            == 1.0
        )

    def test_reworded_duplicate_clears_the_threshold(self):
        assert similarity(*REWORDED) >= DEFAULT_THRESHOLD

    def test_unrelated_text_scores_low(self):
        score = similarity(
            "Which enzyme catalyzes the rate-limiting step of glycolysis?",
            "Name the three bones of the middle ear.",
        )
        assert score < DEFAULT_THRESHOLD

    def test_cloze_and_prose_forms_of_one_fact_match(self):
        score = similarity(
            "PFK-1 is activated by {{c1::AMP}} and inhibited by {{c2::ATP}}.",
            "PFK-1 is activated by AMP and inhibited by ATP.",
        )
        assert score == 1.0

    def test_stopword_only_text_is_not_treated_as_identical(self):
        assert similarity("the of and", "the of and") == 0.0

    def test_empty_against_content_scores_zero(self):
        assert similarity("", "enzyme kinetics") == 0.0

    @pytest.mark.parametrize("swapped", [False, True])
    def test_similarity_is_symmetric(self, swapped):
        left, right = REWORDED if not swapped else REWORDED[::-1]
        assert similarity(left, right) == similarity(right, left)


class TestFirstField:
    def test_picks_the_lowest_order_field(self):
        note = {
            "fields": {
                "Back": {"value": "answer", "order": 1},
                "Front": {"value": "question", "order": 0},
            }
        }
        assert first_field(note) == "question"

    def test_missing_fields_yields_empty(self):
        assert first_field({}) == ""

    def test_empty_fields_mapping_yields_empty(self):
        assert first_field({"fields": {}}) == ""

    def test_non_dict_entries_are_skipped(self):
        assert first_field({"fields": {"Front": "raw string"}}) == ""

    def test_missing_order_defaults_to_zero(self):
        note = {"fields": {"Front": {"value": "q"}}}
        assert first_field(note) == "q"


class TestFindDuplicates:
    def test_flags_a_reworded_existing_card(self):
        cards = [Card(kind="basic", front=REWORDED[0], back="PFK-1")]
        matches = find_duplicates(cards, [(7, REWORDED[1])])
        assert 1 in matches
        assert matches[1].note_id == 7
        assert matches[1].score >= DEFAULT_THRESHOLD

    def test_leaves_distinct_cards_alone(self):
        cards = [Card(kind="basic", front="Name the ear bones.", back="x")]
        assert find_duplicates(cards, [(1, REWORDED[1])]) == {}

    def test_empty_collection_flags_nothing(self):
        cards = [Card(kind="basic", front=REWORDED[0], back="x")]
        assert find_duplicates(cards, []) == {}

    def test_keeps_the_strongest_match(self):
        cards = [Card(kind="basic", front=REWORDED[0], back="x")]
        weaker = "Which enzyme catalyzes the committed step of glycolysis?"
        existing = [(1, weaker), (2, REWORDED[1])]
        best = find_duplicates(cards, existing, threshold=0.5)[1]
        assert best.note_id == 2
        assert best.score == 1.0

    def test_threshold_is_respected(self):
        cards = [Card(kind="basic", front=REWORDED[0], back="x")]
        assert find_duplicates(cards, [(1, REWORDED[1])], threshold=1.01) == {}

    def test_indexes_are_one_based(self):
        cards = [
            Card(kind="basic", front="Name the ear bones.", back="x"),
            Card(kind="basic", front=REWORDED[0], back="x"),
        ]
        assert list(find_duplicates(cards, [(1, REWORDED[1])])) == [2]


class TestFindInternalDuplicates:
    def test_flags_the_later_of_a_repeated_pair(self):
        cards = [
            Card(kind="basic", front=REWORDED[0], back="x"),
            Card(kind="basic", front=REWORDED[1], back="y"),
        ]
        matches = find_internal_duplicates(cards)
        assert list(matches) == [2]

    def test_distinct_batch_is_clean(self):
        cards = [
            Card(kind="basic", front="Name the ear bones.", back="x"),
            Card(kind="basic", front=REWORDED[0], back="y"),
        ]
        assert find_internal_duplicates(cards) == {}

    def test_single_card_batch_is_clean(self):
        assert find_internal_duplicates([Card(kind="basic", front="a", back="b")]) == {}
