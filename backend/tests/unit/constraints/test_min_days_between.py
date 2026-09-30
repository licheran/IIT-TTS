"""C4 `min_days_between` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result


def dataset(scope: str = "code:e1,e2,e3", hard: bool = False, **params):
    return make_dataset(
        days=4,
        periods=1,
        events=[ev("e1"), ev("e2"), ev("e3")],
        constraints=[rule("min_days_between", scope, hard=hard, **params)],
    )


def test_verify_accepts_events_far_enough_apart() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d3", "p1"), at("e3", "d4", "p1"))
    assert penalty(dataset("code:e1,e2", min=2), result) == 0


def test_verify_counts_the_pair_that_is_too_close() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d3", "p1"), at("e3", "d4", "p1"))
    assert penalty(dataset(min=2), result) == 1


def test_verify_counts_every_close_pair() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p1"), at("e3", "d1", "p1"))
    assert penalty(dataset(min=1), result) == 3


def test_solver_spreads_the_events_and_matches_the_verifier() -> None:
    _, found = solve_and_compare(dataset(min=1))
    assert found == 0


def test_solver_keeps_the_one_close_pair_it_cannot_avoid() -> None:
    _, found = solve_and_compare(dataset(min=2))  # three events two days apart need five days
    assert found == 1


def test_hard_spacing_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(min=2, hard=True))
