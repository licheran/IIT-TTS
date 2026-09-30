"""C8 `consecutive`: each event of `sequence` starts in the slot right after the previous one ends,
on the same day.

Penalty: the number of adjacent pairs that break the rule. "Right after" is literal: the next slot,
so a break or the end of the day between two events breaks it.
"""

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import Instance, instances
from tts.core.constraints.order import adjacent_pairs, unknown_events
from tts.core.model import Dataset, Result, Violation

TYPE = "consecutive"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: list[str] = Field(min_length=2)


def problems(dataset: Dataset, instance: Instance[Params]) -> list[str]:
    return unknown_events(dataset, instance.params.sequence)


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        broken = []
        for a, b in adjacent_pairs(ctx, instance.params.sequence):
            first, second = ctx.placements[a], ctx.placements[b]
            follows = second.start == first.start + ctx.events[a].duration
            same_day = ctx.grid.day_index(first.start) == ctx.grid.day_index(second.start)
            if not (follows and same_day):
                broken.append((a, b))
        if broken:
            out.append(
                instance.violation(
                    len(broken),
                    "not back to back: " + ", ".join(f"{b} after {a}" for a, b in broken),
                    *(event_ref(e) for e in sorted({e for pair in broken for e in pair})),
                )
            )
    return out
