"""C10 `travel_gap` (spec 04 section 2).

Places b1 and b2 (type N) each hold one pooled resource (r1, r2). The group g1 attends every event.
"""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, pick, pool, res
from tts.preflight.checks import run_preflight


def dataset(periods: int = 4, filters=("all", "all", "all"), hard: bool = False, **params):
    params.setdefault("min_periods", 1)
    params.setdefault("level", "N")
    return make_dataset(
        days=1,
        periods=periods,
        resources=[
            res("g1"),
            res("b1", "N"),
            res("b2", "N"),
            res("r1", "R", parent="b1"),
            res("r2", "R", parent="b2"),
        ],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "g1"), ("e2", "g1"), ("e3", "g1")],
        pooled=[pool(e, filter=f) for e, f in zip(("e1", "e2", "e3"), filters, strict=True)],
        constraints=[rule("travel_gap", "code:g1", hard=hard, **params)],
    )


def room(event: str, period: str, place: str):
    return at(event, "d1", period, pick(0, place))


def test_verify_accepts_back_to_back_events_in_one_place() -> None:
    result = make_result(room("e1", "p1", "r1"), room("e2", "p2", "r1"), room("e3", "p4", "r2"))
    assert penalty(dataset(), result) == 0  # p3 is free before the move to r2


def test_verify_counts_a_move_with_no_free_period() -> None:
    result = make_result(room("e1", "p1", "r1"), room("e2", "p2", "r2"), room("e3", "p4", "r2"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_rushed_move() -> None:
    result = make_result(room("e1", "p1", "r1"), room("e2", "p2", "r2"), room("e3", "p3", "r1"))
    assert penalty(dataset(), result) == 2


def test_verify_only_counts_moves_between_neighbouring_events() -> None:
    result = make_result(room("e1", "p1", "r1"), room("e3", "p2", "r1"), room("e2", "p3", "r2"))
    assert penalty(dataset(min_periods=2), result) == 1  # e3 to e2; e1 to e2 has e3 between


def test_solver_leaves_a_free_period_when_there_is_room() -> None:
    filters = ("under:b1", "under:b2", "under:b1")
    _, found = solve_and_compare(dataset(periods=5, filters=filters))
    assert found == 0


def test_solver_keeps_the_moves_it_cannot_avoid() -> None:
    filters = ("under:b1", "under:b2", "under:b1")
    _, found = solve_and_compare(dataset(periods=3, filters=filters))
    assert found == 1  # e1, e3 (both at b1), then e2: one move with no free period


def test_hard_travel_time_that_cannot_hold_is_infeasible_and_named() -> None:
    filters = ("under:b1", "under:b2", "under:b1")
    assert_infeasible_and_named(dataset(periods=3, filters=filters, hard=True))


def test_preflight_reports_an_unknown_level() -> None:
    issues = run_preflight(dataset(level="Nope"))
    assert [i.kind for i in issues] == ["invalid_constraint"]
