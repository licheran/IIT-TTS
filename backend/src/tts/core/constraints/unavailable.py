"""H2 `unavailable`: no event occupies a resource in a slot marked unavailable.

One violation per (event, resource), listing the unavailable slots the event covers.
"""

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.model import Dataset, Result, Violation

CODE = "H2"
TYPE = "unavailable"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found = []
    for event, placement in sorted(ctx.placements.items()):
        covered = set(placement.slots)
        for resource in sorted(ctx.occupied(event)):
            bad = sorted(covered & ctx.unavailable_slots.get(resource, frozenset()))
            if not bad:
                continue
            refs = [ctx.slot_ref(t) for t in bad]
            where = ", ".join(r.code for r in refs)
            found.append(
                hard(
                    TYPE,
                    CODE,
                    f'event "{event}" occupies "{resource}" while it is unavailable at {where}',
                    event_ref(event),
                    resource_ref(resource),
                    *refs,
                )
            )
    return found
