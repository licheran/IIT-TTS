"""C2 `max_gaps`: a selected resource has at most `max` gaps a day (or in the whole week).

A gap is a non-break period between the resource's first and last occupied period of a day that
is not occupied itself (spec 04 section 0). Penalty: per day, the gaps above `max` summed over
the days; per week, the week's gaps above `max`.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "max_gaps"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max: int = Field(ge=0)
    per: Literal["day", "week"] = "day"


def gaps(ctx: VerifyContext, resource: str, day: int) -> int:
    occupied = ctx.occ(resource, day)
    if len(occupied) < 2:
        return 0
    first, last = occupied[0], occupied[-1]
    inside = [p for p in ctx.non_break_periods() if first < p < last]
    return sum(p not in occupied for p in inside)


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        limit = instance.params.max
        for resource in instance.targets:
            daily = [gaps(ctx, resource, d) for d in range(ctx.grid.day_count)]
            if instance.params.per == "day":
                p = sum(max(0, g - limit) for g in daily)
            else:
                p = max(0, sum(daily) - limit)
            if p:
                out.append(
                    instance.violation(
                        p,
                        f"{resource} has {sum(daily)} gap(s) in the week, more than {limit} a "
                        f"{instance.params.per}",
                        resource_ref(resource),
                    )
                )
    return out
