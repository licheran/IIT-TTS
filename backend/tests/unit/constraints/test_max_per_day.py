"""C1 `max_per_day` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res

EVENTS = [ev("e1"), ev("e2"), ev("e3"), ev("e4", duration=2)]


def dataset(**params):
    return make_dataset(
        days=2,
        periods=4,
        resources=[res("t1", "T"), res("t2", "T")],
        events=EVENTS,
        fixed=[("e1", "t1"), ("e2", "t1"), ("e3", "t1"), ("e4", "t1")],
        constraints=[rule("max_per_day", "code:t1,t2", **params)],
        validate=False,
    )


def test_verify_counts_nothing_when_every_day_is_within_the_limit() -> None:
    ds = dataset(max=3)
    result = make_result(
        at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d2", "p1"), at("e4", "d2", "p2")
    )
    assert penalty(ds, result) == 0


def test_verify_counts_the_periods_above_the_limit() -> None:
    ds = dataset(max=2)
    result = make_result(
        at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e4", "d1", "p3"), at("e3", "d2", "p1")
    )
    assert penalty(ds, result) == 2  # four periods on d1


def test_verify_sums_the_excess_of_every_day() -> None:
    ds = dataset(max=0)
    result = make_result(
        at("e1", "d1", "p1"), at("e2", "d1", "p2"), at("e3", "d2", "p1"), at("e4", "d2", "p2")
    )
    assert penalty(ds, result) == 5


def test_verify_counts_events_when_asked() -> None:
    ds = dataset(max=1, unit="events")
    result = make_result(
        at("e1", "d1", "p1"), at("e4", "d1", "p2"), at("e2", "d2", "p1"), at("e3", "d2", "p2")
    )
    assert penalty(ds, result) == 2  # 2 events each day


def test_solver_spreads_the_events_and_matches_the_verifier() -> None:
    _, found = solve_and_compare(dataset(max=3))
    assert found == 0  # five periods fit as 3 + 2


def test_solver_minimises_the_excess_it_cannot_avoid() -> None:
    _, found = solve_and_compare(dataset(max=2))
    assert found == 1


def test_solver_counts_events_per_day() -> None:
    _, found = solve_and_compare(dataset(max=1, unit="events"))
    assert found == 2


def test_hard_limit_that_cannot_hold_is_infeasible_and_named() -> None:
    ds = dataset(max=2)
    hard = ds.model_copy(
        update={"constraints": (rule("max_per_day", "code:t1", hard=True, max=2),)}
    )
    assert_infeasible_and_named(hard)


def test_preflight_reports_bad_parameters() -> None:
    from tts.preflight.checks import run_preflight

    ds = dataset(max=-1)
    issues = [i for i in run_preflight(ds) if i.kind == "invalid_constraint"]
    assert len(issues) == 1 and issues[0].severity == "error"
    assert "max" in issues[0].message
