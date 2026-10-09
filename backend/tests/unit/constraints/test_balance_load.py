"""C16 `balance_load` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, pick, pool, res


def dataset(unit: str = "periods", hard: bool = False, scope: str = "type:R"):
    """Four events each take one of three resources of equal standing."""
    return make_dataset(
        days=2,
        periods=3,
        resources=[res("r1", "R"), res("r2", "R"), res("r3", "R")],
        events=[ev("e1"), ev("e2", duration=2), ev("e3"), ev("e4")],
        pooled=[pool("e1"), pool("e2"), pool("e3"), pool("e4")],
        constraints=[rule("balance_load", scope, hard=hard, unit=unit)],
        validate=False,
    )


def placed(a: str, b: str, c: str, d: str):
    return make_result(
        at("e1", "d1", "p1", pick(0, a)),
        at("e2", "d2", "p1", pick(0, b)),
        at("e3", "d1", "p2", pick(0, c)),
        at("e4", "d2", "p3", pick(0, d)),
    )


def test_verify_accepts_equal_loads() -> None:
    ds = dataset("events", scope="code:r1,r2")
    assert penalty(ds, placed("r1", "r2", "r1", "r2")) == 0


def test_verify_counts_the_gap_between_the_most_and_the_least_loaded() -> None:
    # r1: e1 + e3 = 2 periods, r2: e2 = 2 periods, r3: e4 = 1 period
    assert penalty(dataset(), placed("r1", "r2", "r1", "r3")) == 1


def test_verify_measures_the_whole_spread() -> None:
    # r1 has 5 periods, r2 and r3 none
    assert penalty(dataset(), placed("r1", "r1", "r1", "r1")) == 5


def test_verify_counts_events_when_asked() -> None:
    assert penalty(dataset("events"), placed("r1", "r1", "r1", "r2")) == 3  # 3, 1, 0


def test_solver_shares_the_events_out() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 1  # five periods over three resources: 2, 2, 1


def test_solver_balances_events_exactly_when_it_can() -> None:
    ds = dataset("events", scope="code:r1,r2")
    _, found = solve_and_compare(ds)
    assert found == 0


def test_hard_balance_that_cannot_hold_is_infeasible_and_named() -> None:
    hard = make_dataset(
        days=1,
        periods=2,
        resources=[res("r1", "R"), res("r2", "R")],
        events=[ev("e1")],
        fixed=[("e1", "r1")],
        constraints=[rule("balance_load", "code:r1,r2", hard=True)],
        validate=False,
    )
    assert_infeasible_and_named(hard)
