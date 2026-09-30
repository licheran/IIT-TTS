"""C1 `max_per_day`: each selected resource has at most `max` events (or occupied periods) a day.

Penalty: for each resource and day, the amount above `max`, summed.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "max_per_day"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max: int = Field(ge=0)
    unit: Literal["events", "periods"] = "periods"


def daily_counts(ctx: VerifyContext, resource: str, unit: str) -> list[int]:
    """The events (or occupied periods) of `resource` on each day."""
    days = ctx.grid.day_count
    if unit == "periods":
        return [len(ctx.occ(resource, d)) for d in range(days)]
    counts = [0] * days
    for event in ctx.events_of(resource):
        counts[ctx.grid.day_index(ctx.placements[event].start)] += 1
    return counts


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, warnings = instances(ctx, TYPE, Params)
    for instance in found:
        limit, unit = instance.params.max, instance.params.unit
        for resource in instance.targets:
            counts = daily_counts(ctx, resource, unit)
            over = [(d, n) for d, n in enumerate(counts) if n > limit]
            if over:
                days = ", ".join(
                    f"{ctx.grid.codes(d * ctx.grid.periods_per_day)[0]} {n}" for d, n in over
                )
                warnings.append(
                    instance.violation(
                        sum(n - limit for _, n in over),
                        f"{resource} has more than {limit} {unit} a day ({days})",
                        resource_ref(resource),
                    )
                )
    return warnings
