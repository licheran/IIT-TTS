"""C5 `same_start` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res


def dataset(scope: str = "code:e1,e2,e3", hard: bool = False):
    """e1 and e2 share t1, so they can never start together; e3 is free."""
    return make_dataset(
        days=2,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        constraints=[rule("same_start", scope, hard=hard)],
    )


def test_verify_accepts_events_that_start_together() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p1"))
    assert penalty(dataset("code:e1,e3"), result) == 0


def test_verify_counts_the_event_away_from_the_common_start() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p1"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_event_but_one_when_all_differ() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d2", "p1"))
    assert penalty(dataset(), result) == 2


def test_solver_starts_the_free_event_with_one_of_the_others() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 1


def test_solver_finds_a_common_start_when_one_exists() -> None:
    _, found = solve_and_compare(dataset("code:e1,e3"))
    assert found == 0


def test_hard_common_start_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(hard=True))
