"""Anchor ids of the multi-grid HTML export: readable, and never repeated."""

from tts.io.export_html import anchor_ids


def test_anchors_keep_letters_and_digits_only() -> None:
    assert anchor_ids(["L6 SE / G1", "[2LA] -GP"]) == ["r-l6-se-g1", "r-2la-gp"]


def test_codes_that_give_the_same_anchor_get_distinct_ones() -> None:
    ids = anchor_ids(["A/1", "A 1", "a-1", "A1"])
    assert ids == ["r-a-1", "r-a-1-2", "r-a-1-3", "r-a1"]
    assert len(set(ids)) == len(ids)


def test_a_code_with_no_letters_or_digits_still_gets_an_anchor() -> None:
    assert anchor_ids(["///", "--"]) == ["r-item", "r-item-2"]


def test_the_prefix_separates_kinds_of_anchors() -> None:
    assert anchor_ids(["Teacher"], prefix="type") == ["type-teacher"]
