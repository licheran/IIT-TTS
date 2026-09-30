"""The shared, read-only view of a dataset and a result that every `verify` uses.

Built once by the verifier so the hierarchy, time grid and selectors are not rebuilt per
constraint. Building never fails on a bad result: an assignment that cannot be decoded (unknown
day or period) simply has no placement, and the placement rule (H0) reports it.
"""

from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property

from tts.core.hierarchy import Hierarchy
from tts.core.model import (
    Assignment,
    Dataset,
    Event,
    PooledRequirement,
    Ref,
    Resource,
    Result,
)
from tts.core.selectors import Selectors
from tts.core.timegrid import TimeGrid, TimeGridError


@dataclass(frozen=True, slots=True)
class Placement:
    """Where an event was placed. `slots` are the slots it covers, from `start`."""

    event: str
    start: int
    slots: tuple[int, ...]


class VerifyContext:
    def __init__(self, dataset: Dataset, result: Result, base: Dataset | None = None) -> None:
        self.dataset = dataset
        self.base = dataset if base is None else base  # before created events were made real
        self.result = result
        self.hierarchy = Hierarchy(dataset)
        self.grid = TimeGrid(dataset.time)
        self.selectors = Selectors(dataset, self.hierarchy)
        self._allowed: dict[tuple[str, int], frozenset[int]] = {}
        self.events: dict[str, Event] = {e.code: e for e in dataset.events}
        self.resources: dict[str, Resource] = {r.code: r for r in dataset.resources}

        pooled: dict[str, list[PooledRequirement]] = defaultdict(list)
        for q in dataset.pooled:  # sorted by (event, ordinal)
            pooled[q.event].append(q)
        self.pooled: dict[str, tuple[PooledRequirement, ...]] = {
            event: tuple(reqs) for event, reqs in pooled.items()
        }

        by_event: dict[str, list[Assignment]] = defaultdict(list)
        for a in result.assignments:
            by_event[a.event].append(a)
        self.assignments: dict[str, tuple[Assignment, ...]] = {
            event: tuple(items) for event, items in by_event.items()
        }

        self.placements: dict[str, Placement] = {}
        for code, event in self.events.items():
            assignment = self.assignment(code)
            if assignment is None:
                continue
            try:
                start = self.grid.slot(assignment.day, assignment.start_period)
            except TimeGridError:
                continue
            slots = tuple(range(start, start + event.duration))
            self.placements[code] = Placement(code, start, slots)

    def assignment(self, event: str) -> Assignment | None:
        """The event's assignment. With duplicates, the first (the placement rule reports them)."""
        items = self.assignments.get(event)
        return items[0] if items else None

    def chosen(self, event: str) -> dict[int, tuple[str, ...]]:
        """Chosen pooled resources by requirement ordinal (first assignment only)."""
        assignment = self.assignment(event)
        if assignment is None:
            return {}
        return {c.ordinal: c.resources for c in assignment.chosen}

    def chosen_resources(self, event: str) -> tuple[str, ...]:
        return tuple(r for resources in self.chosen(event).values() for r in resources)

    def occupied(self, event: str) -> frozenset[str]:
        """Everything the event occupies (occupancy rule), including its chosen resources."""
        return self.hierarchy.occupied_resources(event, self.chosen_resources(event))

    def occupied_exclusive(self, event: str) -> frozenset[str]:
        return self.hierarchy.occupied_exclusive(event, self.chosen_resources(event))

    def allowed_starts(self, event: Event) -> frozenset[int]:
        """The event's allowed start slots. Raises `TimeGridError` for an unknown pattern."""
        key = (event.start_pattern, event.duration)
        cached = self._allowed.get(key)
        if cached is None:
            cached = frozenset(self.grid.allowed_starts(event))
            self._allowed[key] = cached
        return cached

    def slot_ref(self, t: int) -> Ref:
        day, period = self.grid.codes(t)
        return Ref(kind="slot", code=f"{day}/{period}")

    @cached_property
    def unavailable_slots(self) -> dict[str, frozenset[int]]:
        return self._availability("unavailable")

    @cached_property
    def avoid_slots(self) -> dict[str, frozenset[int]]:
        return self._availability("avoid")

    @cached_property
    def occupancy(self) -> dict[str, dict[int, tuple[str, ...]]]:
        """For each resource, the non-break slots it is occupied in and the events occupying them.

        This is `occ` of spec 04 section 0 (occupancy rule of spec 02 section 3).
        """
        found: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
        for code, placement in self.placements.items():
            slots = [
                t for t in placement.slots if t < self.grid.slot_count and not self.grid.is_break(t)
            ]
            for resource in self.occupied(code):
                for t in slots:
                    found[resource][t].append(code)
        return {
            resource: {t: tuple(sorted(events)) for t, events in by_slot.items()}
            for resource, by_slot in found.items()
        }

    def occ(self, resource: str, day: int) -> list[int]:
        """The ordered period indexes of day `day` in which `resource` is occupied (non-break)."""
        periods = self.grid.periods_per_day
        slots = self.occupancy.get(resource, {})
        return sorted(t - day * periods for t in slots if t // periods == day)

    def events_of(self, resource: str) -> list[str]:
        """The placed events that occupy `resource`, by code."""
        return sorted(c for c in self.placements if resource in self.occupied(c))

    def non_break_periods(self) -> list[int]:
        return [i for i in range(self.grid.periods_per_day) if not self.grid.is_break(i)]

    def _availability(self, status: str) -> dict[str, frozenset[int]]:
        found: dict[str, set[int]] = defaultdict(set)
        for a in self.dataset.availability:
            if a.status != status:
                continue
            try:
                found[a.resource].add(self.grid.slot(a.day, a.period))
            except TimeGridError:
                continue  # an unresolved reference: reported by Dataset.validate_invariants
        return {resource: frozenset(slots) for resource, slots in found.items()}


def ensure_context(
    dataset: Dataset, result: Result, context: VerifyContext | None
) -> VerifyContext:
    """Reuse the caller's context, or build one for a standalone call."""
    return context if context is not None else VerifyContext(dataset, result)
