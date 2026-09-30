"""Times first, then pooled resources (`solver/decompose.py`, P10.4)."""

import pytest
from constraint_helpers import rule

from fixtures import ev, make_dataset, pool, res, unavailable
from tts.core.model import Pin
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.solver import decompose
from tts.solver.decompose import decomposable, solve_dataset, solve_decomposed

PARAMS = RunParams(time_limit_s=20, num_workers=1, seed=0)


def rooms_dataset(periods: int = 2, **changes):
    """Four events of two cohorts, each needing one of two rooms."""
    ds = make_dataset(
        days=1,
        periods=periods,
        resources=[res("g1"), res("g2"), res("r1", "R", capacity=10), res("r2", "R", capacity=10)],
        events=[ev(f"e{i}") for i in range(4)],
        fixed=[("e0", "g1"), ("e1", "g1"), ("e2", "g2"), ("e3", "g2")],
        pooled=[pool(f"e{i}") for i in range(4)],
    )
    return ds.model_copy(update=changes)


def test_a_dataset_where_only_requirements_look_at_the_choice_is_decomposable() -> None:
    assert decomposable(rooms_dataset())
    assert decomposable(rooms_dataset(constraints=(rule("max_gaps", "type:G", max=1),)))


@pytest.mark.parametrize(
    "change",
    [
        {"pins": (Pin(event="e0", resources=("r1", "r2")),)},
        {"availability": (unavailable("r1", "d1", "p1"),)},
        {"constraints": (rule("preferred_resources", "all", filter="code:r1"),)},
        {"constraints": (rule("max_per_day", "type:R", max=1),)},
    ],
    ids=["pin naming too many", "unavailable candidate", "choice rule", "rule on candidates"],
)
def test_anything_that_looks_at_the_choice_prevents_decomposition(change) -> None:
    assert not decomposable(rooms_dataset(**change))


def test_locks_that_decide_the_choice_keep_it_decomposable_and_are_kept() -> None:
    lock = Pin(event="e0", day="d1", start_period="p2", resources=("r2",), source="lock")
    ds = rooms_dataset(pins=(lock,))
    assert decomposable(ds)
    outcome = solve_decomposed(ds, PARAMS)
    assert outcome.result is not None
    e0 = next(a for a in outcome.result.assignments if a.event == "e0")
    assert (e0.start_period, e0.chosen[0].resources) == ("p2", ("r2",))
    assert hard_violations(verify(ds, outcome.result)) == []


def test_the_decomposed_solve_is_valid() -> None:
    ds = rooms_dataset()
    outcome = solve_decomposed(ds, PARAMS)
    assert outcome.result is not None and outcome.status == "optimal"
    assert hard_violations(verify(ds, outcome.result)) == []
    assert any("two steps" in w for w in outcome.warnings)


def test_pools_that_overlap_can_need_the_fallback_and_it_still_finds_a_timetable() -> None:
    """Pools {r1,r2}, {r3,r4}, {r2,r3}: five events fit the pool capacities at one time but not
    four rooms, so the resource step may fail and the full model must take over."""
    ds = make_dataset(
        days=1,
        periods=2,
        resources=[*(res(f"g{i}") for i in range(5)), *(res(f"r{i}", "R") for i in range(1, 5))],
        events=[ev(f"e{i}") for i in range(5)],
        fixed=[(f"e{i}", f"g{i}") for i in range(5)],
        pooled=[pool("e0", filter="code:r1,r2"), pool("e1", filter="code:r1,r2"),
                pool("e2", filter="code:r3,r4"), pool("e3", filter="code:r3,r4"),
                pool("e4", filter="code:r2,r3")],
    )  # fmt: skip
    outcome = solve_decomposed(ds, PARAMS)
    assert outcome.result is not None
    assert hard_violations(verify(ds, outcome.result)) == []


def test_an_infeasible_dataset_stays_infeasible() -> None:
    ds = rooms_dataset(periods=1)  # two events per cohort, one period
    assert solve_decomposed(ds, PARAMS).result is None


def test_small_datasets_use_the_full_model(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []
    monkeypatch.setattr(decompose, "solve_decomposed", lambda *a, **k: called.append(1))
    outcome = solve_dataset(rooms_dataset(), PARAMS)
    assert called == [] and outcome.result is not None
    monkeypatch.setattr(decompose, "DECOMPOSE_ABOVE", 0)
    solve_dataset(rooms_dataset(), PARAMS)
    assert called == [1]
