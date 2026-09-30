"""C12 `preferred_resources` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, pick, pool, res


def dataset(scope: str = "code:e1,e2", periods: int = 1, hard: bool = False):
    """Only r1 is preferred. With one period, both events cannot have it."""
    return make_dataset(
        days=1,
        periods=periods,
        resources=[res("r1", "R", kind="a"), res("r2", "R", kind="b")],
        events=[ev("e1"), ev("e2")],
        pooled=[pool("e1"), pool("e2")],
        constraints=[rule("preferred_resources", scope, hard=hard, filter="tag:kind=a")],
    )


def test_verify_accepts_a_preferred_choice() -> None:
    result = make_result(at("e1", "d1", "p1", pick(0, "r1")), at("e2", "d1", "p1", pick(0, "r2")))
    assert penalty(dataset("code:e1"), result) == 0


def test_verify_counts_the_choice_that_does_not_match() -> None:
    result = make_result(at("e1", "d1", "p1", pick(0, "r1")), at("e2", "d1", "p1", pick(0, "r2")))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_choice_that_does_not_match() -> None:
    result = make_result(at("e1", "d1", "p1", pick(0, "r2")), at("e2", "d1", "p2", pick(0, "r2")))
    assert penalty(dataset(periods=2), result) == 2


def test_solver_gives_the_preferred_resource_to_everyone_when_it_can() -> None:
    _, found = solve_and_compare(dataset(periods=2))
    assert found == 0


def test_solver_keeps_the_one_choice_it_cannot_avoid() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 1


def test_hard_preference_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(hard=True))
