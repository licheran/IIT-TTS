"""C3 `max_days` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, pick, pool, res
from tts.core.model import Pin


def dataset(pins=(), **params):
    return make_dataset(
        days=3,
        periods=2,
        resources=[res("t1", "T"), res("r1", "R")],
        events=[ev("e1"), ev("e2"), ev("e3"), ev("e4")],
        fixed=[("e1", "t1"), ("e2", "t1"), ("e3", "t1")],
        pooled=[pool("e4")],
        pins=pins,
        constraints=[rule("max_days", "code:t1,r1", **params)],
        validate=False,
    )


def test_verify_accepts_days_within_the_limit() -> None:
    result = make_result(
        at("e1", "d1", "p1"),
        at("e2", "d1", "p2"),
        at("e3", "d2", "p1"),
        at("e4", "d1", "p1", pick(0, "r1")),
    )
    assert penalty(dataset(max=2), result) == 0


def test_verify_counts_each_busy_day_above_the_limit() -> None:
    result = make_result(
        at("e1", "d1", "p1"),
        at("e2", "d2", "p1"),
        at("e3", "d3", "p1"),
        at("e4", "d1", "p1", pick(0, "r1")),
    )
    assert penalty(dataset(max=2), result) == 1


def test_verify_counts_pooled_occupancy_and_every_resource() -> None:
    result = make_result(
        at("e1", "d1", "p1"),
        at("e2", "d2", "p1"),
        at("e3", "d3", "p1"),
        at("e4", "d2", "p1", pick(0, "r1")),
    )
    assert penalty(dataset(max=0), result) == 4  # t1 on 3 days, r1 on 1


def test_solver_packs_the_events_into_few_days() -> None:
    _, found = solve_and_compare(dataset(max=1))
    assert found == 1  # three events need two days of two periods; r1 fits on one


def test_solver_matches_the_verifier_with_pins() -> None:
    pins = [
        Pin(event="e1", day="d1", start_period="p1"),
        Pin(event="e2", day="d3", start_period="p1"),
    ]
    _, found = solve_and_compare(dataset(pins=pins, max=1))
    assert found == 1


def test_hard_limit_that_cannot_hold_is_infeasible_and_named() -> None:
    hard = dataset().model_copy(
        update={"constraints": (rule("max_days", "code:t1", hard=True, max=1),)}
    )
    assert_infeasible_and_named(hard)
