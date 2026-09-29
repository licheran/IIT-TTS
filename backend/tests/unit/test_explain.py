"""Infeasibility explanations (spec 05 section 5): cores, minimality and messages."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from ortools.sat.python import cp_model
from test_verifier_cases import CASES

from fixtures import ev, make_dataset, pool, res, unavailable
from tts.core.model import Dataset, Pin, Ref
from tts.core.run import RunParams
from tts.solver.compile import compile_model
from tts.solver.context import RuleSet
from tts.solver.explain import Core, explain, find_core, solve_with
from tts.solver.solve import solve

ONE = RunParams(time_limit_s=10, num_workers=1, seed=0)


def overloaded() -> Dataset:
    """Three one-period events for t1 in a four-period day, two periods of which it is away."""
    return make_dataset(
        days=1,
        periods=4,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "t1"), ("e2", "t1"), ("e3", "t1")],
        availability=[unavailable("t1", "d1", "p1"), unavailable("t1", "d1", "p2")],
    )


def pinned_together() -> Dataset:
    return make_dataset(
        resources=[res("g1"), res("g2"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "g1"), ("e2", "g2")],
        pooled=[pool("e1"), pool("e2")],
        pins=[
            Pin(event="e1", day="d1", start_period="p1", resources=("r1",)),
            Pin(event="e2", day="d1", start_period="p1", resources=("r1",)),
        ],
    )


def pigeonhole() -> Dataset:
    """Three events that each need a room, two rooms, one period. Pre-flight only warns."""
    return make_dataset(
        days=1,
        periods=1,
        resources=[res("g1"), res("g2"), res("g3"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "g1"), ("e2", "g2"), ("e3", "g3")],
        pooled=[pool("e1"), pool("e2"), pool("e3")],
    )


def groups_of(core: Core | None) -> list[RuleSet]:
    assert core is not None
    return list(core.rule_sets)


# --- Cores ------------------------------------------------------------------------------------


def test_an_overloaded_resource_is_explained_by_its_absences_and_its_no_overlap() -> None:
    core = find_core(overloaded())
    assert groups_of(core) == [
        RuleSet("availability", ("t1", "d1", "p1")),
        RuleSet("availability", ("t1", "d1", "p2")),
        RuleSet("no_overlap", ("t1",)),
    ]
    assert core is not None and core.minimal


def test_two_pins_on_one_resource_and_slot_are_the_core() -> None:
    assert groups_of(find_core(pinned_together())) == [
        RuleSet("no_overlap", ("r1",)),
        RuleSet("pin", ("e1", "0")),
        RuleSet("pin", ("e2", "0")),
    ]


def test_a_pigeonhole_needs_every_requirement_and_every_resource() -> None:
    assert groups_of(find_core(pigeonhole())) == [
        RuleSet("no_overlap", ("r1",)),
        RuleSet("no_overlap", ("r2",)),
        RuleSet("requirement", ("e1", "0")),
        RuleSet("requirement", ("e2", "0")),
        RuleSet("requirement", ("e3", "0")),
    ]


def test_an_event_that_fits_nowhere_is_its_own_core() -> None:
    ds = make_dataset(days=1, periods=2, events=[ev("e1", duration=3)])
    assert groups_of(find_core(ds)) == [RuleSet("starts", ("e1",))]


def test_a_requirement_nothing_can_serve_is_its_own_core() -> None:
    ds = make_dataset(
        resources=[res("r1", "R", kind="a")],
        events=[ev("e1")],
        pooled=[pool("e1", filter="tag:kind=b")],
    )
    assert groups_of(find_core(ds)) == [RuleSet("requirement", ("e1", "0"))]


def test_a_pin_onto_an_absence_is_explained_by_both() -> None:
    ds = make_dataset(
        resources=[res("t1", "T")],
        events=[ev("e1")],
        fixed=[("e1", "t1")],
        availability=[unavailable("t1", "d1", "p1")],
        pins=[Pin(event="e1", day="d1", start_period="p1")],
    )
    assert groups_of(find_core(ds)) == [
        RuleSet("availability", ("t1", "d1", "p1")),
        RuleSet("pin", ("e1", "0")),
    ]


def test_a_pooled_resource_absence_counts_too() -> None:
    ds = make_dataset(
        days=1,
        periods=1,
        resources=[res("r1", "R")],
        events=[ev("e1")],
        pooled=[pool("e1")],
        availability=[unavailable("r1", "d1", "p1")],
    )
    assert groups_of(find_core(ds)) == [
        RuleSet("availability", ("r1", "d1", "p1")),
        RuleSet("requirement", ("e1", "0")),
    ]


def test_a_feasible_dataset_has_nothing_to_explain() -> None:
    assert find_core(CASES["pooled_double_booking"]().dataset) is None
    assert explain(CASES["pooled_double_booking"]().dataset) is None


# --- Minimality -------------------------------------------------------------------------------


@pytest.mark.parametrize("build", [overloaded, pinned_together, pigeonhole])
def test_the_core_alone_is_infeasible_and_dropping_any_group_makes_it_feasible(build) -> None:  # type: ignore[no-untyped-def]
    ds = build()
    core = groups_of(find_core(ds))
    ctx = compile_model(ds, explain=True)
    status, _ = solve_with(ctx, core, 5)
    assert status == cp_model.INFEASIBLE
    for rule_set in core:
        status, _ = solve_with(ctx, [g for g in core if g != rule_set], 5)
        assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), rule_set


def test_a_search_that_runs_out_of_budget_says_so() -> None:
    core = find_core(pigeonhole(), budget_s=0)
    assert core is not None and not core.minimal


# --- Messages ---------------------------------------------------------------------------------


def test_the_message_names_the_absences_merged_and_the_load() -> None:
    labels = {"T": "Person"}
    found = explain(overloaded(), label=lambda c: labels.get(c, c))
    assert found is not None
    assert found.kind == "infeasible_core"
    assert found.severity == "error"
    assert found.message == (
        "Conflicting rules: Person t1 unavailable d1 p1–p2; "
        "3 events of 1 periods for t1; no_overlap(t1)"
    )
    assert found.refs == (Ref(kind="resource", code="t1"),)
    assert found.minimal


def test_whole_days_are_merged_into_a_range() -> None:
    ds = make_dataset(
        days=3,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev(f"e{i}") for i in range(3)],
        fixed=[(f"e{i}", "t1") for i in range(3)],
        availability=[unavailable("t1", d, p) for d in ("d2", "d3") for p in ("p1", "p2")],
    )
    found = explain(ds)
    assert found is not None
    assert found.details[0].startswith("T t1 unavailable ")
    assert found.message.startswith("Conflicting rules: T t1 unavailable ")


def test_pins_and_requirements_are_described_with_their_events() -> None:
    found = explain(pinned_together())
    assert found is not None
    assert found.details == (
        "pin of e1 to d1 p1 r1",
        "pin of e2 to d1 p1 r1",
        "no_overlap(r1)",
    )
    assert Ref(kind="event", code="e1") in found.refs
    assert Ref(kind="resource", code="r1") in found.refs
    found = explain(pigeonhole())
    assert found is not None
    assert 'e1 needs 1 R matching "all"' in found.details


# --- Guarded and normal models agree ----------------------------------------------------------


def _feasible(status: cp_model.CpSolverStatus) -> bool:
    return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def _agree(ds: Dataset) -> None:
    normal = solve(ds, ONE)
    ctx = compile_model(ds, explain=True)
    status, _ = solve_with(ctx, sorted(ctx.guards), 10)
    assert normal.status in ("optimal", "feasible", "infeasible")
    assert (normal.status != "infeasible") == _feasible(status), (normal.status, status)


@pytest.mark.parametrize("name", CASES)
def test_the_guarded_model_agrees_with_the_normal_one_on_every_case(name: str) -> None:
    _agree(CASES[name]().dataset)


@pytest.mark.parametrize("build", [overloaded, pinned_together, pigeonhole])
def test_the_guarded_model_agrees_on_infeasible_cases(build) -> None:  # type: ignore[no-untyped-def]
    _agree(build())


@st.composite
def small_datasets(draw) -> Dataset:  # type: ignore[no-untyped-def]
    periods = draw(st.integers(1, 3))
    rule_sets = [f"g{i}" for i in range(draw(st.integers(1, 3)))]
    rooms = [f"r{i}" for i in range(draw(st.integers(0, 2)))]
    events, fixed, pooled, pins = [], [], [], []
    for i in range(draw(st.integers(1, 4))):
        code = f"e{i}"
        events.append(ev(code, duration=draw(st.integers(1, 2))))
        fixed.append((code, draw(st.sampled_from(rule_sets))))
        if rooms and draw(st.booleans()):
            pooled.append(pool(code))
        if draw(st.integers(0, 3)) == 0:
            pins.append(
                Pin(
                    event=code,
                    day="d1",
                    start_period=f"p{draw(st.integers(1, periods))}",
                    resources=(draw(st.sampled_from(rooms)),) if rooms and pooled else (),
                )
            )
    blocks = [
        unavailable(
            draw(st.sampled_from(rule_sets + rooms)), "d1", f"p{draw(st.integers(1, periods))}"
        )
        for _ in range(draw(st.integers(0, 2)))
    ]
    return make_dataset(
        days=1,
        periods=periods,
        resources=[res(g) for g in rule_sets] + [res(r, "R") for r in rooms],
        events=events,
        fixed=fixed,
        pooled=pooled,
        pins=pins,
        availability=blocks,
        validate=False,
    )


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(small_datasets())
def test_every_infeasible_dataset_gets_a_core_that_really_is_infeasible(ds: Dataset) -> None:
    if ds.validate_invariants():
        return  # for example a pin on a resource the event never asks for twice
    normal = solve(ds, ONE)
    core = find_core(ds)
    if normal.status != "infeasible":
        assert core is None
        return
    assert core is not None
    ctx = compile_model(ds, explain=True)
    status, _ = solve_with(ctx, core.rule_sets, 10)
    assert status == cp_model.INFEASIBLE
