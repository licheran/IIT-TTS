"""H3 `capacity`: a chosen pooled resource offers at least the capacity the event needs."""

from collections.abc import Mapping

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Resource, Result, Violation

CODE = "H3"
TYPE = "capacity"
Params = NoParams


def required_capacity(
    hierarchy: Hierarchy, resources: Mapping[str, Resource], event: str, resource_type: str
) -> int:
    """The rule `sum_of_fixed:<resource_type>` for one event.

    Sums the capacities of the event's fixed resources of that type. A fixed resource of another
    type stands for its exclusive descendants of that type (a grouping node). Each resource counts
    once, and a missing capacity counts as 0.
    """
    counted: set[str] = set()
    for code in hierarchy.fixed_resources(event):
        resource = resources.get(code)
        if resource is None:
            continue
        if resource.type == resource_type:
            counted.add(code)
        else:
            counted |= {
                d
                for d in hierarchy.exclusive_descendants(code)
                if resources[d].type == resource_type
            }
    return sum(resources[c].capacity or 0 for c in counted)


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found = []
    for event in sorted(ctx.events):
        chosen = ctx.chosen(event)
        for q in ctx.pooled.get(event, ()):
            rule = q.capacity_rule
            if rule.resource_type is None:
                continue
            needed = required_capacity(ctx.hierarchy, ctx.resources, event, rule.resource_type)
            for code in sorted(set(chosen.get(q.ordinal, ()))):
                resource = ctx.resources.get(code)
                if resource is None:
                    continue  # reported by the placement rule
                offered = resource.capacity or 0
                if offered < needed:
                    found.append(
                        hard(
                            TYPE,
                            CODE,
                            f'"{code}" offers capacity {offered} but "{event}" needs {needed}',
                            event_ref(event),
                            resource_ref(code),
                        )
                    )
    return found
