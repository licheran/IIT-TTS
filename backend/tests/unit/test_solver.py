"""The compile, solve and decode stages, one rule at a time. Results are judged by the verifier."""

import pytest

from fixtures import ev, make_dataset, pool, res, unavailable
from tts.core.model import Constraint, Dataset, Pin, Result
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.solver import registry
from tts.solver.compile import compile_model
from tts.solver.registry import COMPILERS, UnsupportedConstraintError
from tts.solver.solve import SolveOutcome, solve, solve_model

QUICK = RunParams(time_limit_s=20, num_workers=1, seed=0)


def solved(dataset: Dataset, params: RunParams = QUICK) -> SolveOutcome:
    outcome = solve(dataset, params)
    if outcome.result is not None:
        assert hard_violations(verify(dataset, outcome.result)) == []
    return outcome


def where(result: Result, event: str) -> tuple[str, str]:
    a = next(a for a in result.assignments if a.event == event)
    return a.day, a.start_period


def rooms_of(result: Result, event: str) -> tuple[str, ...]:
    a = next(a for a in result.assignments if a.event == event)
    return tuple(r for c in a.chosen for r in c.resources)


# --- Start domains (H0, H2, H5) -----------------------------------------------------------------


def one_event(**kwargs: object) -> Dataset:
    return make_dataset(resources=[res("g1")], events=[ev("e1")], fixed=[("e1", "g1")], **kwargs)  # type: ignore[arg-type]


def test_a_start_domain_is_the_allowed_starts() -> None:
    ctx = compile_model(one_event())
    assert ctx.domains["e1"] == (0, 1, 2, 3, 4, 5, 6, 7)
    assert ctx.problems == []


def test_unavailable_slots_of_a_fixed_resource_leave_the_domain() -> None:
    ds = one_event(
        availability=[unavailable("g1", "d1", "p2"), unavailable("g1", "d2", "p1", "avoid")]
    )
    assert compile_model(ds).domains["e1"] == (0, 2, 3, 4, 5, 6, 7)  # `avoid` is not hard


def test_a_multi_slot_event_loses_every_start_that_covers_an_unavailable_slot() -> None:
    ds = make_dataset(
        resources=[res("g1")],
        events=[ev("e1", duration=2)],
        fixed=[("e1", "g1")],
        availability=[unavailable("g1", "d1", "p3")],
    )
    assert compile_model(ds).domains["e1"] == (0, 4, 5, 6)  # p2 and p3 would cover it


def test_a_child_being_unavailable_blocks_an_event_on_its_parent() -> None:
    ds = make_dataset(
        resources=[res("top", "N"), res("c1", "G", "top")],
        events=[ev("e1")],
        fixed=[("e1", "top")],
        availability=[unavailable("c1", "d1", "p1")],
    )
    assert 0 not in compile_model(ds).domains["e1"]


@pytest.mark.parametrize(
    ("pin", "domain"),
    [
        (Pin(event="e1", day="d2"), (4, 5, 6, 7)),
        (Pin(event="e1", start_period="p3"), (2, 6)),
        (Pin(event="e1", day="d2", start_period="p3"), (6,)),
    ],
)
def test_a_pin_narrows_the_start_domain(pin: Pin, domain: tuple[int, ...]) -> None:
    ctx = compile_model(one_event(pins=[pin]))
    assert ctx.domains["e1"] == domain


def test_two_pins_on_one_event_both_apply() -> None:
    pins = [Pin(event="e1", day="d2"), Pin(event="e1", start_period="p3", source="lock")]
    assert compile_model(one_event(pins=pins)).domains["e1"] == (6,)


def test_an_event_with_no_start_left_makes_the_model_infeasible_with_a_reason() -> None:
    ds = one_event(
        pins=[Pin(event="e1", day="d1")],
        availability=[unavailable("g1", "d1", p) for p in ("p1", "p2", "p3", "p4")],
    )
    ctx = compile_model(ds)
    assert ctx.problems == ['event "e1" has no start left after availability and pins']
    outcome = solve_model(ctx, QUICK)
    assert outcome.status == "infeasible"
    assert outcome.result is None
    assert not outcome.has_solution
    assert outcome.problems == tuple(ctx.problems)


# --- Pooled resources (H0, H2, H3, H4) ------------------------------------------------------------


def room_dataset(**kwargs: object) -> Dataset:
    defaults: dict[str, object] = {
        "resources": [
            res("g1", capacity=30),
            res("g2", capacity=30),
            res("small", "R", capacity=59, kind="lab"),
            res("exact", "R", capacity=60, kind="lab"),
            res("big", "R", capacity=100, kind="lab"),
            res("hall", "R", capacity=200, kind="hall"),
            res("seat", "T", kind="lab"),
        ],
        "events": [ev("e1")],
        "fixed": [("e1", "g1"), ("e1", "g2")],
        "pooled": [pool("e1", filter="tag:kind=lab", rule="sum_of_fixed:G")],
    }
    return make_dataset(**{**defaults, **kwargs})  # type: ignore[arg-type]


def test_candidates_pass_type_filter_and_capacity() -> None:
    ctx = compile_model(room_dataset())
    # Not "small" (59 < 60), not "hall" (filter), not "seat" (wrong type: it is not a room).
    # Candidates are in resource-code order.
    assert ctx.candidates[("e1", 0)] == ("big", "exact")


def test_no_capacity_rule_means_capacity_is_not_a_filter() -> None:
    ds = room_dataset(pooled=[pool("e1", filter="tag:kind=lab")])
    assert compile_model(ds).candidates[("e1", 0)] == ("big", "exact", "small")


def test_a_requirement_with_too_few_candidates_is_reported() -> None:
    ds = room_dataset(pooled=[pool("e1", count=3, filter="tag:kind=lab", rule="sum_of_fixed:G")])
    ctx = compile_model(ds)
    assert len(ctx.problems) == 1
    assert "e1#0 needs 3 R resource(s) but only 2 can serve it" in ctx.problems[0]
    assert solve_model(ctx, QUICK).status == "infeasible"


def test_an_invalid_filter_is_reported_not_raised() -> None:
    ctx = compile_model(room_dataset(pooled=[pool("e1", filter="bogus:x")]))
    assert any('filter "bogus:x"' in p for p in ctx.problems)
    assert solve_model(ctx, QUICK).status == "infeasible"


def test_the_chosen_pooled_resources_satisfy_capacity_and_filter() -> None:
    outcome = solved(room_dataset())
    assert outcome.status in ("optimal", "feasible")
    assert outcome.result is not None
    assert rooms_of(outcome.result, "e1")[0] in ("exact", "big")


def test_a_pooled_count_above_one_chooses_that_many_distinct_resources() -> None:
    ds = room_dataset(pooled=[pool("e1", count=2, filter="tag:kind=lab", rule="sum_of_fixed:G")])
    outcome = solved(ds)
    assert outcome.result is not None
    assert sorted(rooms_of(outcome.result, "e1")) == ["big", "exact"]


def test_a_pooled_candidate_unavailable_at_the_pinned_start_is_not_chosen() -> None:
    ds = room_dataset(
        pins=[Pin(event="e1", day="d1", start_period="p1")],
        availability=[unavailable("exact", "d1", "p1")],
    )
    outcome = solved(ds)
    assert outcome.result is not None
    assert rooms_of(outcome.result, "e1") == ("big",)


def test_a_candidate_never_available_is_dropped() -> None:
    ds = room_dataset(
        availability=[
            unavailable("exact", d, p) for d in ("d1", "d2") for p in ("p1", "p2", "p3", "p4")
        ]
    )
    assert compile_model(ds).candidates[("e1", 0)] == ("big",)


def test_a_pinned_resource_is_forced() -> None:
    ds = room_dataset(pins=[Pin(event="e1", resources=("big",))])
    outcome = solved(ds)
    assert outcome.result is not None
    assert rooms_of(outcome.result, "e1") == ("big",)


def test_a_pinned_resource_that_cannot_serve_makes_it_infeasible_with_a_reason() -> None:
    ds = room_dataset(pins=[Pin(event="e1", resources=("small",))])  # too small
    ctx = compile_model(ds)
    assert ctx.problems == ['event "e1" is pinned to "small", which no requirement can use']
    assert solve_model(ctx, QUICK).status == "infeasible"


# --- No overlap (H1) -----------------------------------------------------------------------------


def tiny(**kwargs: object) -> Dataset:
    """One day with one period: any two events on one resource must clash."""
    return make_dataset(days=1, periods=1, **kwargs)  # type: ignore[arg-type]


def test_two_events_on_one_resource_cannot_share_a_slot() -> None:
    ds = tiny(resources=[res("g1")], events=[ev("a"), ev("b")], fixed=[("a", "g1"), ("b", "g1")])
    assert solve(ds, QUICK).status == "infeasible"


def test_two_events_on_different_resources_can_share_a_slot() -> None:
    ds = tiny(
        resources=[res("g1"), res("g2")],
        events=[ev("a"), ev("b")],
        fixed=[("a", "g1"), ("b", "g2")],
    )
    assert solved(ds).status in ("optimal", "feasible")


def test_a_parent_event_blocks_its_children() -> None:
    parent = [res("top", "N"), res("c1", "G", "top"), res("c2", "G", "top")]
    clash = tiny(
        resources=parent, events=[ev("whole"), ev("part")], fixed=[("whole", "top"), ("part", "c1")]
    )
    assert solve(clash, QUICK).status == "infeasible"
    siblings = tiny(
        resources=parent, events=[ev("p1"), ev("p2")], fixed=[("p1", "c1"), ("p2", "c2")]
    )
    assert solved(siblings).status in ("optimal", "feasible")


def test_a_joint_event_blocks_every_group_it_serves() -> None:
    ds = tiny(
        resources=[res("g1"), res("g2"), res("g3")],
        events=[ev("joint"), ev("solo")],
        fixed=[("joint", "g1"), ("joint", "g2"), ("joint", "g3"), ("solo", "g3")],
    )
    assert solve(ds, QUICK).status == "infeasible"


def test_a_non_exclusive_resource_may_be_shared() -> None:
    ds = tiny(
        resources=[res("shared", "N")],
        events=[ev("a"), ev("b")],
        fixed=[("a", "shared"), ("b", "shared")],
    )
    assert solved(ds).status in ("optimal", "feasible")


def test_a_pooled_resource_cannot_be_double_booked() -> None:
    def build(room_count: int) -> Dataset:
        return tiny(
            resources=[res("g1"), res("g2"), *[res(f"r{i}", "R") for i in range(room_count)]],
            events=[ev("a"), ev("b")],
            fixed=[("a", "g1"), ("b", "g2")],
            pooled=[pool("a"), pool("b")],
        )

    assert solve(build(1), QUICK).status == "infeasible"
    outcome = solved(build(2))
    assert outcome.result is not None
    assert rooms_of(outcome.result, "a") != rooms_of(outcome.result, "b")


def test_a_multi_slot_event_occupies_every_slot_it_covers() -> None:
    ds = make_dataset(
        days=1,
        periods=3,
        resources=[res("g1")],
        events=[ev("long", duration=2), ev("short")],
        fixed=[("long", "g1"), ("short", "g1")],
    )
    outcome = solved(ds)
    assert outcome.result is not None
    long_start, short_start = where(outcome.result, "long")[1], where(outcome.result, "short")[1]
    # Either the long event first (p1+p2, short at p3) or the short one first (p1, long p2+p3).
    assert (long_start, short_start) in {("p1", "p3"), ("p2", "p1")}


# --- Declared constraints ------------------------------------------------------------------------


def test_a_hard_constraint_with_no_compiler_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(COMPILERS, "max_days")
    ds = one_event(constraints=[Constraint(code="C1", type="max_days", scope="type:G", hard=True)])
    with pytest.raises(UnsupportedConstraintError, match='hard constraint "C1"'):
        compile_model(ds)


def test_a_soft_constraint_with_no_compiler_is_ignored_with_a_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(COMPILERS, "max_days")
    ds = one_event(constraints=[Constraint(code="C1", type="max_days", scope="type:G", hard=False)])
    outcome = solved(ds)
    assert outcome.warnings == (
        'constraint "C1" (max_days) is not supported by the solver yet and was ignored',
    )


def test_an_inactive_constraint_is_skipped() -> None:
    ds = one_event(constraints=[Constraint(code="C1", type="max_days", scope="all", active=False)])
    assert solved(ds).warnings == ()


def test_a_registered_compiler_is_called_and_its_penalties_are_minimised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def prefer_early(ctx: object, instance: Constraint) -> None:
        calls.append(instance.code)
        penalty = ctx.penalty(instance.code)  # type: ignore[attr-defined]
        ctx.model.add(penalty == ctx.start["e1"])  # type: ignore[attr-defined]

    monkeypatch.setitem(registry.COMPILERS, "prefer_early", prefer_early)
    ds = one_event(
        constraints=[Constraint(code="K1", type="prefer_early", scope="all", hard=False, weight=2)],
        availability=[unavailable("g1", "d1", p) for p in ("p1", "p2", "p3")],
    )
    outcome = solved(ds)
    assert calls == ["K1"]
    assert outcome.status == "optimal"
    assert outcome.result is not None
    assert where(outcome.result, "e1") == ("d1", "p4")  # slot 3 is the earliest left
    assert outcome.stats.objective == 2 * 3  # weight x penalty


def test_the_day_literal_tracks_the_day_of_the_start() -> None:
    ctx = compile_model(one_event())
    on_second_day = ctx.day_is("e1", 1)
    assert ctx.day_is("e1", 1) is on_second_day  # built once
    ctx.model.add(on_second_day == 1)
    outcome = solve_model(ctx, QUICK)
    assert outcome.result is not None
    assert where(outcome.result, "e1")[0] == "d2"


# --- Solving and decoding ------------------------------------------------------------------------


def test_the_outcome_carries_the_status_the_result_and_statistics() -> None:
    outcome = solved(one_event())
    assert outcome.status == "optimal"  # no objective, so the first solution is optimal
    assert outcome.has_solution
    assert outcome.stats.workers == 1
    assert outcome.stats.seed == 0
    assert outcome.stats.wall_time_s >= 0
    assert outcome.stats.objective is None
    assert outcome.problems == () and outcome.warnings == ()


def test_the_default_worker_count_is_the_number_of_cpus() -> None:
    import os

    outcome = solved(one_event(), RunParams(time_limit_s=20))
    assert outcome.stats.workers == (os.cpu_count() or 1)


def test_every_event_is_placed_with_the_right_pooled_choices() -> None:
    ds = room_dataset(
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "g1"), ("e2", "g2")],
        pooled=[pool("e1", filter="tag:kind=lab"), pool("e2", filter="tag:kind=hall")],
    )
    outcome = solved(ds)
    assert outcome.result is not None
    assert [a.event for a in outcome.result.assignments] == ["e1", "e2"]
    assert rooms_of(outcome.result, "e2") == ("hall",)
    assert all(len(a.chosen) == 1 and a.chosen[0].ordinal == 0 for a in outcome.result.assignments)


def test_an_event_without_a_pooled_requirement_has_no_choices() -> None:
    outcome = solved(one_event())
    assert outcome.result is not None
    assert outcome.result.assignments[0].chosen == ()


def test_the_feasible_mode_also_returns_a_valid_result() -> None:
    outcome = solved(room_dataset(), RunParams(time_limit_s=20, num_workers=1, mode="feasible"))
    assert outcome.has_solution


def test_the_same_seed_and_one_worker_give_the_same_result() -> None:
    ds = make_dataset(
        resources=[res(f"g{i}") for i in range(4)]
        + [res(f"r{i}", "R", capacity=10) for i in range(3)],
        events=[ev(f"e{i}") for i in range(6)],
        fixed=[(f"e{i}", f"g{i % 4}") for i in range(6)],
        pooled=[pool(f"e{i}") for i in range(6)],
    )
    first = solved(ds, RunParams(time_limit_s=20, num_workers=1, seed=5))
    again = solved(ds, RunParams(time_limit_s=20, num_workers=1, seed=5))
    assert first.result == again.result
    other = solved(ds, RunParams(time_limit_s=20, num_workers=1, seed=6))
    assert other.has_solution


def test_a_dataset_without_events_solves_to_an_empty_result() -> None:
    outcome = solved(make_dataset())
    assert outcome.has_solution
    assert outcome.result == Result()
