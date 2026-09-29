"""H1 `no_overlap`: an exclusive resource is never occupied by two events in the same slot.

One violation per (resource, pair of events), listing every slot the pair shares.
"""

from collections import defaultdict

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.model import Dataset, Result, Violation

CODE = "H1"
TYPE = "no_overlap"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)

    users: dict[tuple[str, int], list[str]] = defaultdict(list)
    for event in sorted(ctx.placements):  # sorted, so each bucket is sorted too
        for resource in ctx.occupied_exclusive(event):
            for t in ctx.placements[event].slots:
                users[(resource, t)].append(event)

    shared: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for (resource, t), events in sorted(users.items()):
        for i, first in enumerate(events):
            for second in events[i + 1 :]:
                shared[(resource, first, second)].append(t)

    found = []
    for (resource, first, second), slots in sorted(shared.items()):
        refs = [ctx.slot_ref(t) for t in slots]
        where = ", ".join(r.code for r in refs)
        found.append(
            hard(
                TYPE,
                CODE,
                f'resource "{resource}" is used by "{first}" and "{second}" at {where}',
                resource_ref(resource),
                event_ref(first),
                event_ref(second),
                *refs,
            )
        )
    return found
