"""C10 `travel_gap`: time to move between locations.

An event's location is the set of resources of type `level` above the pooled resources chosen for
it (for example the buildings of its rooms); an event with no such resource has no location and
never counts. For a selected resource, two of its events a and b on the same day form a
transition when b starts at or after a ends and every non-break period between them is free for
the resource. A transition between different locations needs at least `min_periods` of those
free periods. Each event is its own block, so two back-to-back events in different buildings
count. Penalty: the number of transitions that break the rule.
"""

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import event_ref, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import Instance, instances
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Result, Violation

TYPE = "travel_gap"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_periods: int = Field(ge=0)
    level: str


def problems(dataset: Dataset, instance: Instance[Params]) -> list[str]:
    if instance.params.level not in {t.code for t in dataset.resource_types}:
        return [f'level "{instance.params.level}" is not a resource type']
    return []


def locations(
    hierarchy: Hierarchy, types: dict[str, str], resource: str, level: str
) -> frozenset[str]:
    """The resources of type `level` at or above `resource`."""
    found = {a for a in hierarchy.ancestors(resource) if types.get(a) == level}
    if types.get(resource) == level:
        found.add(resource)
    return frozenset(found)


def gap_slots(ctx: VerifyContext, end: int, start: int) -> list[int]:
    """The non-break slots from `end` up to (not including) `start`."""
    return [t for t in range(end, start) if not ctx.grid.is_break(t)]


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    types = {r.code: r.type for r in dataset.resources}
    for instance in found:
        need, level = instance.params.min_periods, instance.params.level
        for resource in instance.targets:
            events = ctx.events_of(resource)
            where = {
                e: frozenset().union(
                    *(locations(ctx.hierarchy, types, r, level) for r in ctx.chosen_resources(e))
                )
                for e in events
            }
            busy = ctx.occupancy.get(resource, {})
            bad = []
            for a in events:
                for b in events:
                    if a == b or not where[a] or not where[b] or where[a] == where[b]:
                        continue
                    pa, pb = ctx.placements[a], ctx.placements[b]
                    end = pa.start + ctx.events[a].duration
                    if ctx.grid.day_index(pa.start) != ctx.grid.day_index(pb.start):
                        continue
                    if pb.start < end:
                        continue
                    gap = gap_slots(ctx, end, pb.start)
                    if len(gap) < need and not any(t in busy for t in gap):
                        bad.append((a, b))
            if bad:
                out.append(
                    instance.violation(
                        len(bad),
                        f"{resource} changes location without {need} free period(s): "
                        + ", ".join(f"{a} to {b}" for a, b in bad),
                        resource_ref(resource),
                        *(event_ref(e) for e in sorted({e for pair in bad for e in pair})),
                    )
                )
    return out
