"""C9 `not_overlapping` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result


def dataset(scope: str = "code:e1,e2,e3", hard: bool = False, periods: int = 2):
    """Events with no resource at all: only the rule keeps them apart."""
    return make_dataset(
        days=1,
        periods=periods,
        events=[ev("e1"), ev("e2"), ev("e3")],
        constraints=[rule("not_overlapping", scope, hard=hard)],
    )


def test_verify_accepts_events_in_different_slots() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p2"))
    assert penalty(dataset("code:e1,e2"), result) == 0


def test_verify_counts_the_overlapping_pair() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d1", "p2"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_overlapping_pair() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p1"), at("e3", "d1", "p1"))
    assert penalty(dataset(), result) == 3


def test_solver_separates_the_events_when_there_is_room() -> None:
    _, found = solve_and_compare(dataset(periods=3))
    assert found == 0


def test_solver_keeps_the_one_overlap_it_cannot_avoid() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 1


def test_hard_separation_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(hard=True))
