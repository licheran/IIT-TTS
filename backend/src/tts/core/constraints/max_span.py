"""C14 `max_span`: per day, a selected resource's last occupied period minus its first, plus one,
is at most `max`.

Penalty: the excess, summed over the days and resources. Periods are counted by position, so a
break between the first and the last occupied period counts towards the span.
"""

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "max_span"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max: int = Field(ge=0)


def span(ctx: VerifyContext, resource: str, day: int) -> int:
    occupied = ctx.occ(resource, day)
    return occupied[-1] - occupied[0] + 1 if occupied else 0


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        limit = instance.params.max
        for resource in instance.targets:
            spans = [span(ctx, resource, d) for d in range(ctx.grid.day_count)]
            p = sum(max(0, s - limit) for s in spans)
            if p:
                out.append(
                    instance.violation(
                        p,
                        f"{resource} spans up to {max(spans)} periods a day, more than {limit}",
                        resource_ref(resource),
                    )
                )
    return out
