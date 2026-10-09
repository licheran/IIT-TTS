"""C17 `same_resource`: the events of a resource use the same resource of another type.

For each resource of type `per` (for example a group), its events in the scope should all use the
same resource of type `type` (for example a teacher), fixed or chosen. Penalty: for each such
resource, its events in the scope minus the number that use the most common one, summed.
"""

from collections import Counter

from pydantic import BaseModel, ConfigDict

from tts.core.constraints.base import event_ref, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "same_resource"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str
    per: str


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        kind, per = instance.params.type, instance.params.per
        placed = [e for e in instance.targets if e in ctx.placements]
        used = {
            e: frozenset(r for r in ctx.occupied(e) if ctx.resources[r].type == kind)
            for e in placed
        }
        for owner in sorted(r.code for r in dataset.resources if r.type == per):
            events = [e for e in placed if owner in ctx.occupied(e)]
            if len(events) < 2:
                continue
            counts = Counter(r for e in events for r in used[e])
            common, most = (
                min(counts.items(), key=lambda kv: (-kv[1], kv[0])) if counts else ("", 0)
            )
            apart = sorted(e for e in events if common not in used[e])
            if apart:
                out.append(
                    instance.violation(
                        len(events) - most,
                        f"{owner} does not keep {common or 'one ' + kind}: " + ", ".join(apart),
                        resource_ref(owner),
                        *(event_ref(e) for e in apart),
                    )
                )
    return out
