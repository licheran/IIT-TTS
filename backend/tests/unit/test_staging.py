"""Staged solving and locks from other timetables (`core/staging.py`, P10.2)."""

from constraint_helpers import rule

from fixtures import at, ev, make_dataset, make_result, pick, pool, res
from tts.core.model import Pin
from tts.core.run import RunParams
from tts.core.staging import occupied_slots, published_locks, stage, with_locks
from tts.core.verifier import hard_violations, verify
from tts.solver.solve import solve


def dataset():
    """Two stages (kinds A and B) that share t1 and the rooms."""
    return make_dataset(
        days=1,
        periods=3,
        resources=[res("g1"), res("g2"), res("t1", "T"), res("r1", "R")],
        events=[ev("a1", kind="A"), ev("a2", kind="A"), ev("b1", kind="B")],
        fixed=[("a1", "g1"), ("a2", "g2"), ("b1", "g1"), ("a1", "t1"), ("b1", "t1")],
        pooled=[pool("a1"), pool("a2"), pool("b1")],
        constraints=[rule("order", "all", sequence=["a1", "b1"])],
    )


def test_a_first_stage_keeps_only_its_events_and_drops_rules_naming_later_ones() -> None:
    staged = stage(dataset(), "kind:A")
    assert [e.code for e in staged.events] == ["a1", "a2"]
    assert {f.event for f in staged.fixed} == {"a1", "a2"}
    (order,) = staged.constraints
    assert order.active is False  # it names b1, which waits for a later stage


def test_a_later_stage_locks_what_the_earlier_one_placed() -> None:
    earlier = make_result(at("a1", "d1", "p1", pick(0, "r1")), at("a2", "d1", "p2", pick(0, "r1")))
    staged = stage(dataset(), "kind:B", earlier)
    assert [e.code for e in staged.events] == ["a1", "a2", "b1"]
    assert staged.pins == (
        Pin(event="a1", day="d1", start_period="p1", resources=("r1",), source="lock"),
        Pin(event="a2", day="d1", start_period="p2", resources=("r1",), source="lock"),
    )
    assert staged.constraints[0].active is True


def test_two_stages_solve_without_clashes() -> None:
    params = RunParams(time_limit_s=10, num_workers=1, seed=0)
    first = solve(stage(dataset(), "kind:A"), params)
    assert first.result is not None
    second_ds = stage(dataset(), "kind:B", first.result)
    second = solve(second_ds, params)
    assert second.result is not None
    assert hard_violations(verify(dataset(), second.result)) == []
    placed = {a.event: a for a in second.result.assignments}
    assert all(placed[a.event] == a for a in first.result.assignments)  # the first stage stayed


def test_other_timetables_become_unavailability_on_shared_resources() -> None:
    other = make_dataset(
        days=1,
        periods=3,
        resources=[res("t1", "T"), res("x9", "T")],
        events=[ev("o1", duration=2)],
        fixed=[("o1", "t1"), ("o1", "x9")],
    )
    theirs = make_result(at("o1", "d1", "p2"))
    assert occupied_slots(other, theirs)["t1"] == {("d1", "p2"), ("d1", "p3")}
    rows = published_locks(dataset(), [(other, theirs)])
    assert [(a.resource, a.period) for a in rows] == [("t1", "p2"), ("t1", "p3")]  # not x9
    assert with_locks(with_locks(dataset(), rows), rows).availability == tuple(rows)


def test_a_solve_with_locks_keeps_off_the_other_timetable() -> None:
    other = make_dataset(
        days=1, periods=3, resources=[res("t1", "T")], events=[ev("o1")], fixed=[("o1", "t1")]
    )
    locked = with_locks(
        dataset(), published_locks(dataset(), [(other, make_result(at("o1", "d1", "p3")))])
    )
    outcome = solve(locked, RunParams(time_limit_s=10, num_workers=1))
    assert outcome.result is not None
    starts = {a.event: a.start_period for a in outcome.result.assignments}
    assert "p3" not in (starts["a1"], starts["b1"])  # the events of t1
    assert hard_violations(verify(locked, outcome.result)) == []
