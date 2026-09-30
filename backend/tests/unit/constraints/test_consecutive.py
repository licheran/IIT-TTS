"""C8 `consecutive` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result
from tts.core.model import Pin


def dataset(sequence=("e1", "e2"), pins=(), breaks=(), hard: bool = False):
    return make_dataset(
        days=2,
        periods=4,
        breaks=breaks,
        events=[ev("e1"), ev("e2"), ev("e3")],
        pins=pins,
        constraints=[rule("consecutive", "code:e1,e2,e3", hard=hard, sequence=list(sequence))],
    )


def test_verify_accepts_events_back_to_back() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d2", "p1"))
    assert penalty(dataset(), result) == 0


def test_verify_counts_a_free_period_between_them() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p3"), at("e3", "d2", "p1"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_a_break_between_them() -> None:
    result = make_result(at("e1", "d1", "p2"), at("e2", "d1", "p4"), at("e3", "d2", "p1"))
    assert penalty(dataset(breaks=[3]), result) == 1


def test_verify_counts_every_broken_pair() -> None:
    result = make_result(at("e1", "d1", "p4"), at("e2", "d2", "p1"), at("e3", "d1", "p1"))
    assert penalty(dataset(sequence=("e1", "e2", "e3")), result) == 2


def test_solver_puts_the_events_back_to_back() -> None:
    _, found = solve_and_compare(dataset(sequence=("e1", "e2", "e3")))
    assert found == 0


def test_solver_keeps_the_pair_a_pin_at_the_end_of_the_day_breaks() -> None:
    _, found = solve_and_compare(dataset(pins=[Pin(event="e1", day="d1", start_period="p4")]))
    assert found == 1


def test_hard_sequence_that_cannot_hold_is_infeasible_and_named() -> None:
    pins = [Pin(event="e1", day="d1", start_period="p4")]
    assert_infeasible_and_named(dataset(pins=pins, hard=True))
