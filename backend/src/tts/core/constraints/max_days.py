"""C3 `max_days`: a selected resource is busy on at most `max` days.

A busy day is a day on which the resource is occupied in at least one non-break period. Penalty:
for each resource, the busy days above `max`.
"""

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "max_days"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max: int = Field(ge=0)


def busy_days(ctx: VerifyContext, resource: str) -> list[int]:
    return [d for d in range(ctx.grid.day_count) if ctx.occ(resource, d)]


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        limit = instance.params.max
        for resource in instance.targets:
            busy = busy_days(ctx, resource)
            if len(busy) > limit:
                days = ", ".join(ctx.grid.codes(d * ctx.grid.periods_per_day)[0] for d in busy)
                out.append(
                    instance.violation(
                        len(busy) - limit,
                        f"{resource} is busy on {len(busy)} days ({days}), more than {limit}",
                        resource_ref(resource),
                    )
                )
    return out
