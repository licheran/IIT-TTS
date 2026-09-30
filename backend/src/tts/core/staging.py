"""Staged solving and locks (spec 05 section 7, strategy 1; section 4.2, locks).

`stage(dataset, scope, previous)` is the dataset one stage solves: the events its scope selects,
plus every event an earlier stage already placed, now locked where it was (`lock` pins on day,
start and chosen resources). Events of later stages are left out, so they neither need a place
nor block one. Constraints whose `sequence` names a left-out event are made inactive for the
stage (they apply again once every named event is in).

`published_locks(dataset, others)` turns the timetables of other datasets into `unavailable`
availability rows on the resources this dataset shares with them (matched by code, and by day
and period codes). For the solver and the verifier this is the same as the constant intervals of
spec 05 section 4.2, and the verifier checks it without knowing about other datasets.
"""

from collections.abc import Iterable

from tts.core.hierarchy import Hierarchy
from tts.core.model import Availability, Dataset, Pin, Result
from tts.core.selectors import Selectors
from tts.core.timegrid import TimeGrid, TimeGridError


def stage(dataset: Dataset, scope: str, previous: Result | None = None) -> Dataset:
    """The dataset of one stage. Raises `SelectorError` for a scope that does not parse."""
    selected = Selectors(dataset).events(scope)
    known = {e.code for e in dataset.events}
    placed = {a.event: a for a in (previous.assignments if previous else ()) if a.event in known}
    locked = set(placed) - selected
    keep = selected | locked
    dropped = known - keep

    pins = [p for p in dataset.pins if p.event in keep and p.event not in locked]
    for code in sorted(locked):
        a = placed[code]
        resources = tuple(r for choice in a.chosen for r in choice.resources)
        pins.append(
            Pin(
                event=code,
                day=a.day,
                start_period=a.start_period,
                resources=resources,
                source="lock",
            )
        )

    constraints = []
    for c in dataset.constraints:
        sequence = c.params.get("sequence")
        names_dropped = isinstance(sequence, list) and any(s in dropped for s in sequence)
        constraints.append(c.model_copy(update={"active": False}) if names_dropped else c)

    return Dataset.model_validate(
        {
            **dataset.model_dump(),
            "events": [e for e in dataset.events if e.code in keep],
            "fixed": [f for f in dataset.fixed if f.event in keep],
            "pooled": [q for q in dataset.pooled if q.event in keep],
            "pins": pins,
            "constraints": constraints,
        }
    )


def occupied_slots(dataset: Dataset, result: Result) -> dict[str, set[tuple[str, str]]]:
    """For each resource, the (day code, period code) pairs a result occupies it in."""
    grid = TimeGrid(dataset.time)
    hierarchy = Hierarchy(dataset)
    durations = {e.code: e.duration for e in dataset.events}
    found: dict[str, set[tuple[str, str]]] = {}
    for a in result.assignments:
        if a.event not in durations:
            continue
        try:
            start = grid.slot(a.day, a.start_period)
        except TimeGridError:
            continue
        chosen = [r for choice in a.chosen for r in choice.resources]
        slots = [grid.codes(t) for t in range(start, start + durations[a.event])]
        for resource in hierarchy.occupied_resources(a.event, chosen):
            found.setdefault(resource, set()).update(slots)
    return found


def published_locks(
    dataset: Dataset, others: Iterable[tuple[Dataset, Result]]
) -> list[Availability]:
    """`unavailable` rows for this dataset's resources that other timetables already use."""
    mine = {r.code for r in dataset.resources}
    days = {d.code for d in dataset.time.days}
    periods = {p.code for p in dataset.time.periods}
    rows: set[tuple[str, str, str]] = set()
    for other, result in others:
        for resource, slots in occupied_slots(other, result).items():
            if resource not in mine:
                continue
            for day, period in slots:
                if day in days and period in periods:
                    rows.add((resource, day, period))
    return [
        Availability(resource=r, day=d, period=p, status="unavailable") for r, d, p in sorted(rows)
    ]


def with_locks(dataset: Dataset, rows: Iterable[Availability]) -> Dataset:
    """The dataset with extra `unavailable` rows (duplicates dropped)."""
    merged = {(a.resource, a.day, a.period, a.status): a for a in (*dataset.availability, *rows)}
    return dataset.model_copy(update={"availability": tuple(sorted(merged.values(), key=_key))})


def _key(a: Availability) -> tuple[str, str, str, str]:
    return (a.resource, a.day, a.period, a.status)
