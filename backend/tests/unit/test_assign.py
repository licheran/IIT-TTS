"""Default choices for small pools: the load is balanced before the search (solver/assign.py)."""

import pytest
from constraint_helpers import ONE

from fixtures import demand, ev, make_dataset, pool, res
from tts.core.model import CapacityRule, Pin, PooledSpec
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.solver import decompose
from tts.solver.assign import pooled_candidates, preassigned
from tts.solver.compile import compile_model
from tts.solver.decompose import solve_dataset
from tts.solver.solve import solve_model

PARAMS = RunParams(time_limit_s=30, num_workers=1, seed=0)


def teachers(n: int = 4, duration: int = 1, filters=None, periods: int = 4):  # type: ignore[no-untyped-def]
    filters = filters or ["all"] * n
    return make_dataset(
        days=1,
        periods=periods,
        resources=[
            *(res(f"g{i}") for i in range(n)),
            *(res(f"t{i}", "T") for i in (1, 2)),
            *(res(f"r{i}", "R") for i in range(1, 4)),
        ],
        events=[ev(f"e{i}", duration=duration) for i in range(n)],
        fixed=[(f"e{i}", f"g{i}") for i in range(n)],
        pooled=[pool(f"e{i}", "T", filter=f) for i, f in enumerate(filters)],
        validate=False,
    )


def chosen(ds):  # type: ignore[no-untyped-def]
    return {k: v for k, v in pooled_candidates(ds).items()}


def test_events_with_the_same_small_pool_share_it_evenly() -> None:
    ds = preassigned(teachers(4), up_to=5)
    held = [codes for codes in chosen(ds).values()]
    assert sorted(held) == [("t1",), ("t1",), ("t2",), ("t2",)]


def test_the_load_counts_periods_so_a_long_event_balances_two_short_ones() -> None:
    ds = teachers(3)
    ds = ds.model_copy(
        update={
            "events": (
                ds.events[0].model_copy(update={"duration": 2}),
                *ds.events[1:],
            )
        }
    )
    held = chosen(preassigned(ds, up_to=5))
    assert held[("e0", 0)] != held[("e1", 0)] and held[("e1", 0)] == held[("e2", 0)]


def test_a_requirement_for_several_resources_takes_the_least_loaded_ones() -> None:
    ds = teachers(2)
    ds = ds.model_copy(
        update={
            "resources": (*ds.resources, res("t3", "T")),
            "pooled": (ds.pooled[0].model_copy(update={"count": 2}), ds.pooled[1]),
        }
    )
    held = chosen(preassigned(ds, up_to=5))
    assert len(held[("e0", 0)]) == 2
    assert held[("e1", 0)] not in (held[("e0", 0)],)  # the other event takes the remaining one


def test_a_pool_bigger_than_the_limit_is_left_to_the_search() -> None:
    ds = teachers(2)
    assert preassigned(ds, up_to=1) is ds


def test_an_event_whose_pin_names_resources_is_left_alone() -> None:
    ds = teachers(2)
    ds = ds.model_copy(update={"pins": (Pin(event="e0", resources=("t2",)),)})
    held = chosen(preassigned(ds, up_to=5))
    assert held[("e0", 0)] == ("t1", "t2")  # untouched
    assert len(held[("e1", 0)]) == 1


def test_the_first_half_counts_the_narrowed_pools_and_names_the_choice() -> None:
    """Four one-period events, two teachers, two periods: two each, so they fit."""
    ds = teachers(4, periods=2)
    first = solve_model(compile_model(ds, times_only=True, preassign_up_to=5), PARAMS)
    assert first.result is not None
    named = {a.event: [r for c in a.chosen for r in c.resources] for a in first.result.assignments}
    assert sorted(sum(named.values(), [])) == ["t1", "t1", "t2", "t2"]


def test_the_balanced_pools_do_not_fit_when_the_time_is_too_short() -> None:
    """Four events at one period each, two teachers, one period: the balance puts two events on one
    teacher, and both would have to be at the same time."""
    ds = teachers(4, periods=1)
    first = solve_model(compile_model(ds, times_only=True, preassign_up_to=5), PARAMS)
    assert first.status == "infeasible"


def configured():
    """Two demands of two groups each, with a pool of two teachers, so each demand makes one session
    a week."""
    pooled = (
        PooledSpec(
            resource_type="R", ordinal=0, capacity_rule=CapacityRule.parse("sum_of_fixed:G")
        ),
        PooledSpec(resource_type="T", ordinal=1, filter="code:t1,t2"),
    )
    return make_dataset(
        days=2,
        periods=3,
        resources=[
            *(res(f"g{i}", "G", capacity=10) for i in range(1, 5)),
            res("t1", "T"),
            res("t2", "T"),
            res("r1", "R", capacity=40),
        ],
        demands=[
            demand("d1", participants=("g1", "g2"), limit=1, pooled=pooled),
            demand("d2", participants=("g3", "g4"), limit=1, pooled=pooled),
        ],
        validate=False,
    )


def test_a_large_configured_dataset_tries_the_balanced_pools_before_the_free_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(decompose, "DECOMPOSE_ABOVE", 0)
    ds = configured()
    outcome = solve_dataset(ds, PARAMS)
    assert outcome.result is not None
    assert hard_violations(verify(ds, outcome.result)) == []
    assert any("balancing their load" in w for w in outcome.warnings)


def test_a_small_dataset_is_left_to_the_solver() -> None:
    outcome = solve_dataset(configured(), ONE)
    assert outcome.result is not None
    assert not any("balancing" in w for w in outcome.warnings)
