"""C7 `order` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result
from tts.core.model import Pin
from tts.preflight.checks import run_preflight

SEQUENCE = ["e1", "e2", "e3"]


def dataset(days: int = 1, pins=(), hard: bool = False, **params):
    params.setdefault("sequence", SEQUENCE)
    return make_dataset(
        days=days,
        periods=3,
        events=[ev("e1"), ev("e2"), ev("e3")],
        pins=pins,
        constraints=[rule("order", "code:e1,e2,e3", hard=hard, **params)],
    )


def test_verify_accepts_events_in_order() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p3"))
    assert penalty(dataset(), result) == 0


def test_verify_counts_the_pair_out_of_order() -> None:
    result = make_result(at("e3", "d1", "p1"), at("e1", "d1", "p2"), at("e2", "d1", "p3"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_reversed_pair() -> None:
    result = make_result(at("e1", "d1", "p3"), at("e2", "d1", "p2"), at("e3", "d1", "p1"))
    assert penalty(dataset(), result) == 2


def test_verify_requires_the_same_day_when_asked() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d2", "p1"), at("e3", "d2", "p2"))
    assert penalty(dataset(days=2), result) == 0
    assert penalty(dataset(days=2, same_day=True), result) == 1


def test_solver_orders_the_events_and_matches_the_verifier() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 0


def test_solver_keeps_the_one_pair_a_pin_forces_out_of_order() -> None:
    _, found = solve_and_compare(dataset(pins=[Pin(event="e3", day="d1", start_period="p1")]))
    assert found == 1


def test_hard_order_that_cannot_hold_is_infeasible_and_named() -> None:
    pins = [Pin(event="e3", day="d1", start_period="p1")]
    assert_infeasible_and_named(dataset(pins=pins, hard=True))


def test_preflight_reports_an_unknown_event_in_the_sequence() -> None:
    issues = run_preflight(dataset(sequence=["e1", "nope"]))
    assert [i.kind for i in issues] == ["invalid_constraint"]
    assert "nope" in issues[0].message
