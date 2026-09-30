"""C7 `order`: each event of `sequence` starts after the previous one ends.

With `same_day`, adjacent events must also be on the same day. Penalty: the number of adjacent
pairs that break the rule. `sequence` names the events; the scope must select events (spec 04)
but does not change which ones are ordered. A pair with an unplaced event is left to H0.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import Instance, instances
from tts.core.model import Dataset, Result, Violation

TYPE = "order"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: list[str] = Field(min_length=2)
    same_day: bool = False


def unknown_events(dataset: Dataset, sequence: Sequence[str]) -> list[str]:
    """Problems with the events a sequence names (used by pre-flight)."""
    known = {e.code for e in dataset.events}
    return [f'sequence names unknown event "{code}"' for code in sequence if code not in known]


def problems(dataset: Dataset, instance: Instance[Params]) -> list[str]:
    return unknown_events(dataset, instance.params.sequence)


def adjacent_pairs(ctx: VerifyContext, sequence: Sequence[str]) -> list[tuple[str, str]]:
    """Adjacent pairs of a sequence whose two events are placed."""
    return [
        (a, b)
        for a, b in zip(sequence, sequence[1:], strict=False)
        if a in ctx.placements and b in ctx.placements
    ]


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        broken = []
        for a, b in adjacent_pairs(ctx, instance.params.sequence):
            first, second = ctx.placements[a], ctx.placements[b]
            late = second.start < first.start + ctx.events[a].duration
            apart = instance.params.same_day and ctx.grid.day_index(
                first.start
            ) != ctx.grid.day_index(second.start)
            if late or apart:
                broken.append((a, b))
        if broken:
            out.append(
                instance.violation(
                    len(broken),
                    "out of order: " + ", ".join(f"{b} does not follow {a}" for a, b in broken),
                    *(event_ref(e) for e in sorted({e for pair in broken for e in pair})),
                )
            )
    return out
