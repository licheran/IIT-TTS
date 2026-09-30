"""C6 `same_day` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res


def dataset(scope: str = "code:e1,e2,e3", hard: bool = False, days: int = 3):
    """One period a day, and e1 and e2 share t1, so they are never on the same day."""
    return make_dataset(
        days=days,
        periods=1,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        constraints=[rule("same_day", scope, hard=hard)],
    )


def test_verify_accepts_events_on_one_day() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d2", "p1"), at("e3", "d1", "p1"))
    assert penalty(dataset("code:e1,e3"), result) == 0


def test_verify_counts_the_event_on_another_day() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d2", "p1"), at("e3", "d1", "p1"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_event_but_one_when_all_differ() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d2", "p1"), at("e3", "d3", "p1"))
    assert penalty(dataset(), result) == 2


def test_solver_puts_the_free_event_with_one_of_the_others() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 1


def test_solver_finds_one_day_when_it_can() -> None:
    _, found = solve_and_compare(dataset("code:e2,e3"))
    assert found == 0


def test_hard_same_day_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(hard=True))
