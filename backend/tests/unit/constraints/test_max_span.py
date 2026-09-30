"""C14 `max_span` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res
from tts.core.model import Pin


def dataset(breaks=(), pins=(), hard: bool = False, **params):
    return make_dataset(
        days=1,
        periods=5,
        breaks=breaks,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        pins=pins,
        constraints=[rule("max_span", "code:t1", hard=hard, **params)],
    )


def test_verify_accepts_a_short_day() -> None:
    assert penalty(dataset(max=2), make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"))) == 0


def test_verify_counts_the_period_above_the_limit() -> None:
    assert penalty(dataset(max=2), make_result(at("e1", "d1", "p1"), at("e2", "d1", "p3"))) == 1


def test_verify_counts_the_whole_excess() -> None:
    assert penalty(dataset(max=2), make_result(at("e1", "d1", "p1"), at("e2", "d1", "p5"))) == 3


def test_verify_counts_a_break_inside_the_span() -> None:
    result = make_result(at("e1", "d1", "p2"), at("e2", "d1", "p4"))
    assert penalty(dataset(breaks=[3], max=2), result) == 1


def test_solver_keeps_the_day_short() -> None:
    pins = [Pin(event="e1", day="d1", start_period="p1")]
    _, found = solve_and_compare(dataset(pins=pins, max=2))
    assert found == 0


def test_solver_matches_the_verifier_on_a_forced_long_day() -> None:
    pins = [
        Pin(event="e1", day="d1", start_period="p1"),
        Pin(event="e2", day="d1", start_period="p5"),
    ]
    _, found = solve_and_compare(dataset(pins=pins, max=2))
    assert found == 3


def test_hard_span_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(max=1, hard=True))
