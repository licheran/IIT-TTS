"""C15 `max_load` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, pick, pool, res


def dataset(unit: str = "periods", hard: bool = False, **params):
    """t1 has e1 (one period) and e2 (two periods) fixed; e3 and e4 each take r1 or r2."""
    return make_dataset(
        days=2,
        periods=3,
        resources=[res("t1", "T"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1"), ev("e2", duration=2), ev("e3"), ev("e4")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        pooled=[pool("e3"), pool("e4")],
        constraints=[rule("max_load", "code:t1,r1,r2", hard=hard, unit=unit, **params)],
        validate=False,
    )


def placed(first: str, second: str):
    return make_result(
        at("e1", "d1", "p1"),
        at("e2", "d2", "p1"),
        at("e3", "d1", "p2", pick(0, first)),
        at("e4", "d2", "p3", pick(0, second)),
    )


def test_verify_accepts_a_load_within_the_limit() -> None:
    assert penalty(dataset(max=3), placed("r1", "r2")) == 0  # t1 has 3 periods


def test_verify_counts_the_periods_above_the_limit() -> None:
    assert penalty(dataset(max=2), placed("r1", "r2")) == 1


def test_verify_adds_the_excess_of_every_resource() -> None:
    assert penalty(dataset(max=0), placed("r1", "r1")) == 3 + 2  # t1 3 periods, r1 2


def test_verify_can_count_events_instead_of_periods() -> None:
    assert penalty(dataset("events", max=1), placed("r1", "r1")) == 1 + 1  # t1 2 events, r1 2


def test_solver_spreads_the_pooled_events_over_the_resources() -> None:
    _, found = solve_and_compare(dataset("events", max=1))
    assert found == 1  # t1 has two events whatever the solver does; r1 and r2 take one each


def test_solver_matches_the_verifier_for_periods() -> None:
    _, found = solve_and_compare(dataset(max=1))
    assert found == 2  # t1 has 3 periods; the pooled events are spread one to each resource


def test_hard_limit_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(hard=True, max=2))
