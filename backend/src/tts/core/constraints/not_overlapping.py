"""C9 `not_overlapping`: no two selected events share a slot, even without a shared resource.

Penalty: the number of overlapping pairs.
"""

from itertools import combinations

from tts.core.constraints.base import NoParams, event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "not_overlapping"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        placed = [e for e in instance.targets if e in ctx.placements]
        clashing = [
            (a, b)
            for a, b in combinations(placed, 2)
            if set(ctx.placements[a].slots) & set(ctx.placements[b].slots)
        ]
        if clashing:
            out.append(
                instance.violation(
                    len(clashing),
                    "overlapping: " + ", ".join(f"{a}/{b}" for a, b in clashing),
                    *(event_ref(e) for e in sorted({e for pair in clashing for e in pair})),
                )
            )
    return out
