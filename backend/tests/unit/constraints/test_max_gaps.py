"""C2 `max_gaps` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res
from tts.core.model import Pin


def dataset(breaks=(), pins=(), days=1, periods=6, **params):
    return make_dataset(
        days=days,
        periods=periods,
        breaks=breaks,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "t1"), ("e2", "t1"), ("e3", "t1")],
        pins=pins,
        constraints=[rule("max_gaps", "code:t1", **params)],
        validate=False,
    )


def pin(event: str, day: str, period: str) -> Pin:
    return Pin(event=event, day=day, start_period=period)


def test_verify_finds_no_gap_in_a_compact_day() -> None:
    result = make_result(at("e1", "d1", "p2"), at("e2", "d1", "p3"), at("e3", "d1", "p4"))
    assert penalty(dataset(max=0), result) == 0


def test_verify_counts_each_idle_period_between_the_first_and_the_last() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p4"))
    assert penalty(dataset(max=0), result) == 1


def test_verify_counts_several_gaps_above_the_limit() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p4"), at("e3", "d1", "p6"))
    assert penalty(dataset(max=1), result) == 2  # gaps p2, p3, p5


def test_verify_does_not_count_a_break_as_a_gap() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p4"))
    assert penalty(dataset(breaks=[3], max=0), result) == 0


def test_verify_sums_the_week_when_asked() -> None:
    ds = dataset(days=2, max=1, per="week")
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p3"), at("e3", "d2", "p1"))
    assert penalty(ds, result) == 0
    spread = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p4"), at("e3", "d2", "p1"))
    assert penalty(ds, spread) == 1


def test_solver_keeps_the_gaps_it_cannot_avoid_and_matches_the_verifier() -> None:
    pins = [pin("e1", "d1", "p1"), pin("e3", "d1", "p6")]
    _, found = solve_and_compare(dataset(pins=pins, max=0))
    assert found == 3  # p1 and p6 with one event between them leave 3 gaps


def test_solver_finds_a_day_with_no_gap_when_one_exists() -> None:
    _, found = solve_and_compare(dataset(pins=[pin("e1", "d1", "p1")], max=0))
    assert found == 0


def test_solver_counts_weekly_gaps() -> None:
    pins = [pin("e1", "d1", "p1"), pin("e2", "d1", "p3"), pin("e3", "d2", "p2")]
    _, found = solve_and_compare(dataset(days=2, pins=pins, max=0, per="week"))
    assert found == 1


def test_hard_limit_that_cannot_hold_is_infeasible_and_named() -> None:
    ds = dataset(pins=[pin("e1", "d1", "p1"), pin("e3", "d1", "p6")], max=0)
    hard = ds.model_copy(update={"constraints": (rule("max_gaps", "code:t1", hard=True, max=2),)})
    assert_infeasible_and_named(hard)
