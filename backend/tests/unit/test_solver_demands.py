"""The solver splits demands into sessions (ADR-0007, spec 05 sections 2.2 and 4.1a).

Every test judges the result with the independent verifier, not with the solver's status.
"""

from collections import Counter

from constraint_helpers import ONE

from fixtures import demand, ev, make_dataset, res, unavailable
from tts.core.model import CapacityRule, Dataset, Event, Pin, PooledSpec, Result
from tts.core.verifier import hard_violations, verify
from tts.solver.solve import solve


def groups(*sizes: int) -> tuple:  # type: ignore[type-arg]
    return tuple(res(f"g{i}", "G", capacity=s) for i, s in enumerate(sizes, 1))


def build(
    *demands, resources=(), events=(), fixed=(), pins=(), days=2, periods=4, **more
) -> Dataset:  # type: ignore[no-untyped-def]
    return make_dataset(
        days=days,
        periods=periods,
        resources=resources,
        events=events,
        fixed=fixed,
        pins=pins,
        demands=demands,
        validate=False,
        **more,
    )


def solved(ds: Dataset) -> Result:
    outcome = solve(ds, ONE)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    assert [v.message for v in hard_violations(verify(ds, outcome.result))] == []
    return outcome.result


def blocks_of(result: Result, demand_code: str = "d1") -> list[tuple[str, ...]]:
    return sorted(c.participants for c in result.created if c.demand == demand_code)


def test_the_solver_splits_participants_into_even_blocks() -> None:
    gs = groups(10, 10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2),
        resources=(*gs, res("r1", "R", capacity=20)),
    )
    result = solved(ds)
    blocks = blocks_of(result)
    assert sorted(len(b) for b in blocks) == [2, 2]
    assert sorted(p for b in blocks for p in b) == ["g1", "g2", "g3", "g4"]


def test_ten_participants_with_a_limit_of_three_split_three_three_two_two() -> None:
    gs = groups(*[10] * 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=3),
        resources=(*gs, res("r1", "R", capacity=30)),
    )
    sizes = sorted((len(b) for b in blocks_of(solved(ds))), reverse=True)
    assert sizes == [3, 3, 2, 2]


def test_the_room_must_seat_every_participant_of_a_block() -> None:
    """The 25-seat group cannot share a 30-seat room with anyone, so it is alone."""
    gs = groups(10, 10, 10, 10, 25)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2),
        resources=(*gs, res("r1", "R", capacity=30)),
    )
    blocks = blocks_of(solved(ds))
    assert ("g5",) in blocks
    assert sorted(len(b) for b in blocks) == [1, 2, 2]


def test_a_group_keeps_its_companions_every_time_a_session_repeats() -> None:
    gs = groups(10, 10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2, repeat=2),
        resources=(*gs, res("r1", "R", capacity=20)),
    )
    result = solved(ds)
    counted = Counter(c.participants for c in result.created)
    assert sorted(counted.values()) == [2, 2]  # two blocks, two sessions each


def test_one_block_for_everyone_when_there_is_no_limit() -> None:
    gs = groups(10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=None, repeat=2),
        resources=(*gs, res("r1", "R", capacity=30)),
    )
    assert blocks_of(solved(ds)) == [("g1", "g2", "g3")] * 2


def test_blocks_of_one_are_one_per_participant() -> None:
    gs = groups(10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=1),
        resources=(*gs, res("r1", "R", capacity=10)),
    )
    assert blocks_of(solved(ds)) == [("g1",), ("g2",), ("g3",)]


def test_created_events_are_named_by_the_block_of_the_lowest_participant() -> None:
    gs = groups(10, 10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2, kind="TUT"),
        resources=(*gs, res("r1", "R", capacity=20)),
    )
    result = solved(ds)
    by_code = {c.code: c.participants for c in result.created}
    assert sorted(by_code) == ["d1-TUT-01", "d1-TUT-02"]
    assert "g1" in by_code["d1-TUT-01"]


def test_a_teacher_is_chosen_from_the_pool_and_never_teaches_two_sessions_at_once() -> None:
    gs = groups(10, 10, 10, 10)
    teachers = PooledSpec(resource_type="T", ordinal=1, filter="code:t1,t2")
    rooms = PooledSpec(resource_type="R", capacity_rule=CapacityRule.parse("sum_of_fixed:G"))
    ds = build(
        demand(participants=[g.code for g in gs], limit=1, pooled=(rooms, teachers)),
        resources=(
            *gs,
            res("r1", "R", capacity=10),
            res("r2", "R", capacity=10),
            res("t1", "T"),
            res("t2", "T"),
        ),
        days=1,
        periods=2,
    )
    result = solved(ds)
    picked = {a.event: dict((c.ordinal, c.resources) for c in a.chosen) for a in result.assignments}
    assert all(set(v[1]) <= {"t1", "t2"} for v in picked.values())


def test_an_edit_is_kept_and_the_rest_is_solved_around_it() -> None:
    gs = groups(10, 10, 10, 10)
    kept = Event(code="kept", kind="K", duration=1, start_pattern="all", demand="d1")
    ds = build(
        demand(participants=[g.code for g in gs], limit=2),
        resources=(*gs, res("r1", "R", capacity=20)),
        events=(kept,),
        fixed=(("kept", "g1"), ("kept", "g2")),
        pins=(Pin(event="kept", day="d2", start_period="p3"),),
    )
    result = solved(ds)
    placed = next(a for a in result.assignments if a.event == "kept")
    assert (placed.day, placed.start_period) == ("d2", "p3")
    assert blocks_of(result) == [("g3", "g4")]


def test_a_participant_is_not_placed_when_it_is_unavailable() -> None:
    gs = groups(10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=1),
        resources=(*gs, res("r1", "R", capacity=10)),
        days=1,
        periods=2,
        availability=[unavailable("g1", "d1", "p1")],
    )
    result = solved(ds)
    first = next(a for a in result.assignments if a.event.endswith("-01"))
    assert first.start_period == "p2"  # g1's session cannot be at p1


def test_the_same_data_gives_the_same_timetable_with_one_worker() -> None:
    gs = groups(10, 10, 10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2),
        resources=(*gs, res("r1", "R", capacity=20)),
    )
    assert solved(ds) == solved(ds)


def test_more_sessions_than_periods_is_infeasible() -> None:
    gs = groups(10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2, repeat=5),
        resources=(*gs, res("r1", "R", capacity=20)),
        days=1,
        periods=4,
    )
    outcome = solve(ds, ONE)
    assert outcome.result is None
    assert outcome.status == "infeasible"


def test_an_edit_that_cannot_be_part_of_a_valid_split_is_infeasible_with_a_reason() -> None:
    gs = groups(10, 10, 10, 10, 10)
    kept = Event(code="kept", kind="K", duration=1, start_pattern="all", demand="d1")
    ds = build(
        demand(participants=[g.code for g in gs], limit=2),  # 3 blocks of 1 or 2
        resources=(*gs, res("r1", "R", capacity=50)),
        events=(kept,),
        fixed=(("kept", "g1"), ("kept", "g2"), ("kept", "g3")),
    )
    outcome = solve(ds, ONE)
    assert outcome.status == "infeasible"
    assert any("edited block" in p for p in outcome.problems)


def test_hand_made_events_still_solve_as_before() -> None:
    gs = groups(10, 10)
    ds = make_dataset(
        resources=(*gs, res("r1", "R", capacity=20)),
        events=(ev("e1"), ev("e2")),
        fixed=(("e1", "g1"), ("e2", "g1")),
    )
    result = solved(ds)
    assert result.created == ()
    assert {a.event for a in result.assignments} == {"e1", "e2"}


def test_a_result_with_created_events_places_each_of_them() -> None:
    gs = groups(10, 10, 10)
    ds = build(
        demand(participants=[g.code for g in gs], limit=2),
        resources=(*gs, res("r1", "R", capacity=20)),
    )
    result = solved(ds)
    placed = {a.event for a in result.assignments}
    assert placed == {c.code for c in result.created}


# --- symmetry breaking (P20.2) ---------------------------------------------------------------


def availability_split() -> Dataset:
    """Only one split is possible: {g1, g3} and {g2, g4} (g1 and g3 cannot do p1, g2 and g4 p2)."""
    gs = groups(10, 10, 10, 10)
    return build(
        demand(participants=[g.code for g in gs], limit=2),
        resources=(*gs, res("r1", "R", capacity=20)),
        days=1,
        periods=2,
        availability=[
            unavailable("g1", "d1", "p1"),
            unavailable("g3", "d1", "p1"),
            unavailable("g2", "d1", "p2"),
            unavailable("g4", "d1", "p2"),
        ],
    )


def test_the_only_possible_split_is_found() -> None:
    assert blocks_of(solved(availability_split())) == [("g1", "g3"), ("g2", "g4")]


def test_the_answer_does_not_depend_on_symmetry_breaking(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from tts.solver import compile as compile_module

    with_breaking = blocks_of(solved(availability_split()))
    monkeypatch.setattr(compile_module, "BREAK_SYMMETRY", False)
    assert blocks_of(solved(availability_split())) == with_breaking


# --- decomposition: times first, then rooms and teachers (P20.7) -----------------------------


def decomposable_dataset() -> Dataset:
    gs = groups(10, 10, 10, 10, 10, 10)
    rooms = tuple(res(f"r{i}", "R", capacity=40) for i in range(1, 4))
    return build(
        demand(participants=[g.code for g in gs], limit=3, repeat=2, kind="LEC"),
        demand("d2", participants=[g.code for g in gs], limit=1, kind="TUT"),
        resources=(*gs, *rooms),
        days=3,
        periods=4,
    )


def test_a_decomposed_solve_gives_a_timetable_the_verifier_accepts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from tts.solver import decompose

    monkeypatch.setattr(decompose, "DECOMPOSE_ABOVE", 0)
    ds = decomposable_dataset()
    outcome = decompose.solve_dataset(ds, ONE)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    assert [v.message for v in hard_violations(verify(ds, outcome.result))] == []
    assert any("two steps" in w for w in outcome.warnings)
    assert len(outcome.result.created) == 2 * 2 + 6  # two lecture blocks twice, six tutorials


def test_a_decomposed_solve_keeps_the_sessions_and_groups_of_the_times_step(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from tts.solver import decompose

    monkeypatch.setattr(decompose, "DECOMPOSE_ABOVE", 0)
    ds = decomposable_dataset()
    result = decompose.solve_dataset(ds, ONE).result
    assert result is not None
    assert {a.event for a in result.assignments} == {c.code for c in result.created}
    lectures = [c.participants for c in result.created if c.demand == "d1"]
    assert sorted(len(p) for p in lectures) == [3, 3, 3, 3]
    assert Counter(lectures) == Counter({p: 2 for p in set(lectures)})  # same companions twice


# --- large datasets: the obvious split first, then the solver's own (P20.7) --------------------


def test_a_large_dataset_tries_the_default_split_first(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from tts.solver import decompose

    monkeypatch.setattr(decompose, "DECOMPOSE_ABOVE", 0)
    ds = decomposable_dataset()
    outcome = decompose.solve_dataset(ds, ONE)
    assert outcome.result is not None
    assert any("default split" in w for w in outcome.warnings)
    lectures = sorted(c.participants for c in outcome.result.created if c.demand == "d1")
    assert lectures == [("g1", "g2", "g3")] * 2 + [("g4", "g5", "g6")] * 2  # in order of code


def test_when_the_default_split_cannot_work_the_solver_finds_another(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """g1 and g3 cannot meet in p1 and g2 and g4 cannot meet in p2: only {g1, g3} with
    {g2, g4} works, not the default {g1, g2} with {g3, g4}."""
    from tts.solver import decompose

    monkeypatch.setattr(decompose, "DECOMPOSE_ABOVE", 0)
    ds = availability_split()
    outcome = decompose.solve_dataset(ds, ONE)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    assert [v.message for v in hard_violations(verify(ds, outcome.result))] == []
    assert blocks_of(outcome.result) == [("g1", "g3"), ("g2", "g4")]
    assert not any("default split" in w for w in outcome.warnings)


def test_a_small_dataset_lets_the_solver_choose_the_split_at_once() -> None:
    outcome = solve(availability_split(), ONE)
    assert outcome.result is not None
    assert blocks_of(outcome.result) == [("g1", "g3"), ("g2", "g4")]
