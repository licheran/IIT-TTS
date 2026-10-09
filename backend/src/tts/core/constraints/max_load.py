"""C15 `max_load`: each selected resource has at most `max` events (or occupied periods) a week.

Penalty: for each resource, the amount above `max`, summed.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "max_load"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max: int = Field(ge=0)
    unit: Literal["events", "periods"] = "periods"


def weekly_load(ctx: VerifyContext, resource: str, unit: str) -> int:
    """The events (or occupied periods) of `resource` over the week."""
    if unit == "events":
        return len(ctx.events_of(resource))
    return sum(len(ctx.occ(resource, d)) for d in range(ctx.grid.day_count))


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        limit, unit = instance.params.max, instance.params.unit
        for resource in instance.targets:
            load = weekly_load(ctx, resource, unit)
            if load > limit:
                out.append(
                    instance.violation(
                        load - limit,
                        f"{resource} has {load} {unit} in the week, more than {limit}",
                        resource_ref(resource),
                    )
                )
    return out
