"""C17 `same_resource` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, pick, pool, res

SLOTS = [("d1", "p1"), ("d1", "p2"), ("d1", "p3"), ("d2", "p1"), ("d2", "p2")]


def dataset(first: str = "all", second: str = "all", hard: bool = False, scope: str = "all"):
    """Group g1 attends e1, e2 and e3, group g2 attends e4 and e5. Each takes one teacher."""
    return make_dataset(
        days=2,
        periods=3,
        resources=[res("g1"), res("g2"), res("t1", "T"), res("t2", "T"), res("t3", "T")],
        events=[ev("e1"), ev("e2"), ev("e3"), ev("e4"), ev("e5")],
        fixed=[("e1", "g1"), ("e2", "g1"), ("e3", "g1"), ("e4", "g2"), ("e5", "g2")],
        pooled=[
            pool("e1", "T", filter=first),
            pool("e2", "T", filter=second),
            pool("e3", "T"),
            pool("e4", "T"),
            pool("e5", "T"),
        ],
        constraints=[rule("same_resource", scope, hard=hard, type="T", per="G")],
        validate=False,
    )


def teachers(*chosen: str):
    return make_result(
        *(
            at(f"e{i + 1}", day, period, pick(0, who))
            for i, ((day, period), who) in enumerate(zip(SLOTS, chosen, strict=True))
        )
    )


def test_verify_accepts_a_group_that_keeps_its_teacher() -> None:
    assert penalty(dataset(), teachers("t1", "t1", "t1", "t2", "t2")) == 0


def test_verify_counts_the_events_away_from_the_most_common_teacher() -> None:
    assert penalty(dataset(), teachers("t1", "t1", "t2", "t3", "t3")) == 1


def test_verify_adds_up_every_group() -> None:
    # g1: t1, t2, t3 -> 2 apart; g2: t1, t2 -> 1 apart
    assert penalty(dataset(), teachers("t1", "t2", "t3", "t1", "t2")) == 3


def test_verify_only_looks_at_the_events_in_scope() -> None:
    scoped = dataset(scope="code:e1,e2,e4,e5")
    assert penalty(scoped, teachers("t1", "t1", "t2", "t3", "t3")) == 0


def test_solver_gives_a_group_one_teacher_when_it_can() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 0


def test_solver_pays_for_a_split_it_cannot_avoid() -> None:
    # e1 can only have t1 and e2 only t2, so g1 has two teachers for two of its events
    _, found = solve_and_compare(dataset(first="code:t1", second="code:t2"))
    assert found == 1


def test_hard_continuity_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(first="code:t1", second="code:t2", hard=True))
