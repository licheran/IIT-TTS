"""C13 `avoid`: a selected resource is not occupied in its `avoid` availability slots.

Penalty: the number of occupied avoid-periods, summed over the resources. Only the resource's own
availability rows count.
"""

from tts.core.constraints.base import NoParams, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "avoid"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        for resource in instance.targets:
            avoided = ctx.avoid_slots.get(resource, frozenset())
            used = sorted(t for t in ctx.occupancy.get(resource, {}) if t in avoided)
            if used:
                out.append(
                    instance.violation(
                        len(used),
                        f"{resource} is used in {len(used)} period(s) it prefers to avoid",
                        resource_ref(resource),
                        *(ctx.slot_ref(t) for t in used),
                    )
                )
    return out
