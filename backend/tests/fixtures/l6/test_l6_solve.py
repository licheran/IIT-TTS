"""P4.7: the L6 regression through the solver. Every claim is checked by the verifier."""

import time

from tts.core.model import Dataset, Pin, Result
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.solver.compile import compile_model
from tts.solver.solve import solve, solve_model

NFR_1_SECONDS = 30.0  # spec 01 section 5: L6 hard-constraint solve, no pins, 4 cores


def locks_of(result: Result) -> tuple[Pin, ...]:
    """A lock for every placement: its day, start and rooms."""
    return tuple(
        Pin(
            event=a.event,
            day=a.day,
            start_period=a.start_period,
            resources=tuple(r for c in a.chosen for r in c.resources),
            source="lock",
        )
        for a in result.assignments
    )


def test_with_every_event_locked_the_solver_reproduces_the_original_exactly(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    locked = l6_dataset.model_copy(update={"pins": locks_of(l6_locked_result)})
    outcome = solve(locked, RunParams(time_limit_s=30, num_workers=1))
    assert outcome.result == l6_locked_result
    assert hard_violations(verify(locked, outcome.result)) == []


def test_with_no_pins_it_places_all_77_events_with_no_hard_violation_in_time(
    l6_dataset: Dataset,
) -> None:
    started = time.perf_counter()
    outcome = solve(l6_dataset, RunParams(time_limit_s=NFR_1_SECONDS, num_workers=4))
    elapsed = time.perf_counter() - started

    assert outcome.status in ("optimal", "feasible"), (outcome.status, outcome.problems)
    assert outcome.result is not None
    assert len(outcome.result.assignments) == 77
    assert {a.event for a in outcome.result.assignments} == {e.code for e in l6_dataset.events}
    assert hard_violations(verify(l6_dataset, outcome.result)) == []
    assert elapsed <= NFR_1_SECONDS, f"took {elapsed:.1f} s"


def test_the_unpinned_solution_is_not_just_the_original_replayed(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    outcome = solve(l6_dataset, RunParams(time_limit_s=30, num_workers=1))
    assert outcome.result is not None
    assert outcome.result != l6_locked_result  # the search found its own timetable


def test_the_same_seed_and_one_worker_give_the_same_timetable(l6_dataset: Dataset) -> None:
    params = RunParams(time_limit_s=30, num_workers=1, seed=11)
    first = solve(l6_dataset, params)
    again = solve(l6_dataset, params)
    assert first.result is not None
    assert first.result == again.result
    assert first.status == again.status


def test_other_seeds_give_other_valid_timetables(l6_dataset: Dataset) -> None:
    results = []
    for seed in (1, 2, 3):
        outcome = solve(l6_dataset, RunParams(time_limit_s=30, num_workers=1, seed=seed))
        assert outcome.result is not None
        assert hard_violations(verify(l6_dataset, outcome.result)) == []
        results.append(outcome.result)
    assert len(results) == 3


def test_the_model_compiles_without_problems_and_quickly(l6_dataset: Dataset) -> None:
    started = time.perf_counter()
    ctx = compile_model(l6_dataset)
    assert time.perf_counter() - started < 5.0
    assert ctx.problems == [] and ctx.warnings == []
    assert len(ctx.start) == 77
    assert len(ctx.candidates) == 76  # every event but the online one has a room requirement
    assert all(len(c) >= 1 for c in ctx.candidates.values())


def test_every_room_requirement_has_the_rooms_the_original_used(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    """The candidate filter must not rule out the room the real timetable used."""
    ctx = compile_model(l6_dataset)
    for a in l6_locked_result.assignments:
        for choice in a.chosen:
            assert set(choice.resources) <= set(ctx.candidates[(a.event, choice.ordinal)])


def test_a_pinned_model_can_be_solved_again_from_the_compiled_context(
    l6_dataset: Dataset,
) -> None:
    ctx = compile_model(l6_dataset)
    first = solve_model(ctx, RunParams(time_limit_s=30, num_workers=1, seed=0))
    again = solve_model(ctx, RunParams(time_limit_s=30, num_workers=1, seed=0))
    assert first.result == again.result
