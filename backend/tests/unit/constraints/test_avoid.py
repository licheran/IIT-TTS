"""C13 `avoid` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res, unavailable


def dataset(periods: int = 4, hard: bool = False):
    """t1 would rather not work in p1 and p2."""
    return make_dataset(
        days=1,
        periods=periods,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        availability=[
            unavailable("t1", "d1", "p1", status="avoid"),
            unavailable("t1", "d1", "p2", status="avoid"),
        ],
        constraints=[rule("avoid", "code:t1", hard=hard)],
    )


def test_verify_accepts_work_outside_the_avoided_periods() -> None:
    assert penalty(dataset(), make_result(at("e1", "d1", "p3"), at("e2", "d1", "p4"))) == 0


def test_verify_counts_an_avoided_period_in_use() -> None:
    assert penalty(dataset(), make_result(at("e1", "d1", "p1"), at("e2", "d1", "p3"))) == 1


def test_verify_counts_every_avoided_period_in_use() -> None:
    assert penalty(dataset(), make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"))) == 2


def test_solver_avoids_the_periods_when_it_can() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 0


def test_solver_uses_one_avoided_period_when_it_must() -> None:
    _, found = solve_and_compare(dataset(periods=3))
    assert found == 1


def test_hard_avoidance_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(periods=3, hard=True))
