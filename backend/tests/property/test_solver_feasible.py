"""Property: a dataset built around a hidden valid timetable always solves, with no violations.

The hidden timetable is placed event by event, and the verifier is the oracle that accepts each
placement. Then unavailability and pins are added that the hidden timetable respects, so the
dataset is feasible by construction.
"""

from typing import Any

from hypothesis import HealthCheck, given, reject, settings
from hypothesis import strategies as st

from fixtures import at, ev, make_dataset, make_result, pick, pool, res, unavailable
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Event, Pin, Result
from tts.core.run import RunParams
from tts.core.timegrid import TimeGrid, covered_slots
from tts.core.verifier import hard_violations, verify
from tts.solver.solve import solve

QUICK = RunParams(time_limit_s=30, num_workers=1, seed=0)
PROPERTY = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)


def _valid(dataset: Dataset, result: Result) -> bool:
    return hard_violations(verify(dataset, result)) == []


def _restricted(dataset: Dataset, events: list[Event]) -> Dataset:
    codes = {e.code for e in events}
    return dataset.model_copy(
        update={
            "events": tuple(events),
            "fixed": tuple(f for f in dataset.fixed if f.event in codes),
            "pooled": tuple(q for q in dataset.pooled if q.event in codes),
        }
    )


@st.composite
def feasible_cases(draw: Any) -> tuple[Dataset, Result]:
    """A dataset and a timetable that is valid for it."""
    days = draw(st.integers(1, 3))
    periods = draw(st.integers(3, 6))
    breaks = draw(st.sets(st.integers(1, periods), max_size=1))
    grouped = draw(st.booleans())
    group_codes = [f"g{i}" for i in range(draw(st.integers(1, 4)))]
    teacher_codes = [f"t{i}" for i in range(draw(st.integers(0, 2)))]
    room_specs = [
        (f"r{i}", draw(st.integers(10, 80)), draw(st.sampled_from(["a", "b"])))
        for i in range(draw(st.integers(1, 3)))
    ]

    resources = [
        res(g, parent="top" if grouped else None, capacity=draw(st.integers(5, 30)))
        for g in group_codes
    ]
    if grouped:
        resources.append(res("top", "N"))
    resources += [res(t, "T") for t in teacher_codes]
    resources += [res(code, "R", capacity=cap, kind=kind) for code, cap, kind in room_specs]

    events, fixed, pooled = [], [], []
    for i in range(draw(st.integers(1, 6))):
        code = f"e{i}"
        events.append(ev(code, duration=draw(st.integers(1, 2))))
        targets = draw(st.lists(st.sampled_from(group_codes), min_size=1, max_size=2, unique=True))
        if grouped and draw(st.integers(0, 4)) == 0:
            targets = ["top"]  # a grouping node: occupies every group under it
        targets += (
            draw(st.lists(st.sampled_from(teacher_codes), max_size=1)) if teacher_codes else []
        )
        fixed += [(code, t) for t in targets]
        if draw(st.booleans()):
            pooled.append(
                pool(
                    code,
                    filter=draw(st.sampled_from(["all", "tag:kind=a", "tag:kind=b"])),
                    rule=draw(st.sampled_from(["none", "sum_of_fixed:G"])),
                )
            )

    dataset = make_dataset(
        days=days, periods=periods, breaks=breaks,
        resources=resources, events=events, fixed=fixed, pooled=pooled, validate=False,
    )  # fmt: skip
    grid = TimeGrid(dataset.time)
    rooms = [code for code, _, _ in room_specs]
    randomiser = draw(st.randoms(use_true_random=False))

    # Place the events one at a time, with the verifier deciding what is allowed.
    placed: list[Event] = []
    assignments = []
    for event in dataset.events:
        options: list[tuple[int, str | None]] = []
        needs_room = any(q.event == event.code for q in dataset.pooled)
        for start in grid.allowed_starts(event):
            for room in rooms if needs_room else [None]:
                options.append((start, room))
        randomiser.shuffle(options)
        for start, room in options:
            day, period = grid.codes(start)
            choices = (pick(0, room),) if room else ()
            trial = [*assignments, at(event.code, day, period, *choices)]
            if _valid(_restricted(dataset, [*placed, event]), make_result(*trial)):
                placed.append(event)
                assignments = trial
                break
        else:
            reject()
    hidden = make_result(*assignments)
    if not _valid(dataset, hidden):
        reject()

    # Unavailability the hidden timetable respects.
    hierarchy = Hierarchy(dataset)
    used: dict[str, set[int]] = {}
    for a in hidden.assignments:
        event = next(e for e in dataset.events if e.code == a.event)
        start = grid.slot(a.day, a.start_period)
        for r in hierarchy.occupied_resources(a.event, [x for c in a.chosen for x in c.resources]):
            used.setdefault(r, set()).update(covered_slots(start, event.duration))
    blocks = []
    for _ in range(draw(st.integers(0, 4))):
        resource = draw(st.sampled_from([r.code for r in dataset.resources]))
        slot = draw(st.integers(0, grid.slot_count - 1))
        if slot not in used.get(resource, set()):
            day, period = grid.codes(slot)
            blocks.append(unavailable(resource, day, period))

    # Pins the hidden timetable satisfies.
    pins = []
    for a in hidden.assignments:
        if draw(st.integers(0, 2)) == 0:
            rooms_used = tuple(x for c in a.chosen for x in c.resources)
            pins.append(
                Pin(
                    event=a.event,
                    day=a.day if draw(st.booleans()) else None,
                    start_period=a.start_period if draw(st.booleans()) else None,
                    resources=rooms_used if draw(st.booleans()) else (),
                    source=draw(st.sampled_from(["user", "lock"])),
                )
            )
    dataset = dataset.model_copy(update={"availability": tuple(blocks), "pins": tuple(pins)})
    if not _valid(dataset, hidden):
        reject()
    return dataset, hidden


@PROPERTY
@given(feasible_cases())
def test_a_dataset_with_a_valid_timetable_always_solves_with_no_violations(
    case: tuple[Dataset, Result],
) -> None:
    dataset, hidden = case
    outcome = solve(dataset, QUICK)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    assert hard_violations(verify(dataset, outcome.result)) == []
    assert len(outcome.result.assignments) == len(dataset.events)
    assert hidden.assignments  # the premise: a valid timetable exists


@PROPERTY
@given(feasible_cases())
def test_locking_every_event_reproduces_the_hidden_timetable_exactly(
    case: tuple[Dataset, Result],
) -> None:
    dataset, hidden = case
    locks = tuple(
        Pin(
            event=a.event,
            day=a.day,
            start_period=a.start_period,
            resources=tuple(r for c in a.chosen for r in c.resources),
            source="lock",
        )
        for a in hidden.assignments
    )
    locked = dataset.model_copy(update={"pins": locks})
    outcome = solve(locked, QUICK)
    assert outcome.result == hidden


@PROPERTY
@given(feasible_cases())
def test_the_same_seed_and_one_worker_always_give_the_same_result(
    case: tuple[Dataset, Result],
) -> None:
    dataset, _ = case
    first = solve(dataset, QUICK).result
    again = solve(dataset, QUICK).result
    assert first == again
