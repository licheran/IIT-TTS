"""C4 `min_days_between`: every two selected events are at least `min` days apart.

Penalty: the number of pairs closer than `min` days. Events without a placement are left to H0.
"""

from itertools import combinations

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "min_days_between"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    min: int = Field(ge=0)


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        placed = [e for e in instance.targets if e in ctx.placements]
        day = {e: ctx.grid.day_index(ctx.placements[e].start) for e in placed}
        close = [
            (a, b) for a, b in combinations(placed, 2) if abs(day[a] - day[b]) < instance.params.min
        ]
        if close:
            pairs = ", ".join(f"{a}/{b}" for a, b in close)
            events = sorted({e for pair in close for e in pair})
            out.append(
                instance.violation(
                    len(close),
                    f"{len(close)} pair(s) less than {instance.params.min} day(s) apart ({pairs})",
                    *(event_ref(e) for e in events),
                )
            )
    return out
