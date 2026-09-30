"""Clashes between timetables of different datasets (P10.3, spec 01 section 2.3).

A timetable is conflict-free only within its own dataset. When several datasets share resources
(the same code, for example one teacher in two faculties' datasets), `cross_clashes` finds the
periods where an exclusive shared resource is used by more than one of them. Days and periods
are matched by code. Clashes inside one timetable are the verifier's job and are not repeated.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Result
from tts.core.timegrid import TimeGrid, TimeGridError


class Clash(BaseModel):
    """A shared resource used in one period by events of several timetables."""

    model_config = ConfigDict(frozen=True)

    resource: str
    day: str
    period: str
    uses: tuple[tuple[str, str], ...]  # (timetable label, event code), sorted


def _usage(dataset: Dataset, result: Result) -> dict[str, dict[tuple[str, str], list[str]]]:
    """Exclusive resource -> (day, period) -> events using it."""
    grid = TimeGrid(dataset.time)
    hierarchy = Hierarchy(dataset)
    durations = {e.code: e.duration for e in dataset.events}
    found: dict[str, dict[tuple[str, str], list[str]]] = {}
    for a in result.assignments:
        if a.event not in durations:
            continue
        try:
            start = grid.slot(a.day, a.start_period)
        except TimeGridError:
            continue
        chosen = [r for choice in a.chosen for r in choice.resources]
        for resource in hierarchy.occupied_exclusive(a.event, chosen):
            for t in range(start, min(start + durations[a.event], grid.slot_count)):
                found.setdefault(resource, {}).setdefault(grid.codes(t), []).append(a.event)
    return found


def cross_clashes(timetables: Sequence[tuple[str, Dataset, Result]]) -> list[Clash]:
    """Every period in which a resource is used by events of two or more of the timetables."""
    usage = [(label, _usage(dataset, result)) for label, dataset, result in timetables]
    by_slot: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    for label, used in usage:
        for resource, slots in used.items():
            for (day, period), events in slots.items():
                entry = by_slot.setdefault((resource, day, period), set())
                entry.update((label, e) for e in events)
    clashes = []
    for (resource, day, period), uses in sorted(by_slot.items()):
        if len({label for label, _ in uses}) > 1:
            clashes.append(
                Clash(resource=resource, day=day, period=period, uses=tuple(sorted(uses)))
            )
    return clashes
