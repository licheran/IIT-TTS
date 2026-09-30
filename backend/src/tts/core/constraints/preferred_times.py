"""C11 `preferred_times`: each selected event starts in one of the listed `Day:Period` slots.

Penalty: one for each placed event that starts elsewhere.
"""

from pydantic import BaseModel, ConfigDict, Field

from tts.core.constraints.base import event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import INVALID, Instance, instances, parse_slot
from tts.core.model import Dataset, Ref, Result, Violation
from tts.core.timegrid import TimeGrid

TYPE = "preferred_times"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slots: list[str] = Field(min_length=1)


def slot_set(grid: TimeGrid, slots: list[str]) -> frozenset[int]:
    """The listed slots. Raises `ValueError` naming the first bad one."""
    return frozenset(parse_slot(grid, text) for text in slots)


def problems(dataset: Dataset, instance: Instance[Params]) -> list[str]:
    grid = TimeGrid(dataset.time)
    found = []
    for text in instance.params.slots:
        try:
            parse_slot(grid, text)
        except ValueError as error:
            found.append(str(error))
    return found


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        try:
            wanted = slot_set(ctx.grid, instance.params.slots)
        except ValueError as error:
            out.append(
                Violation(
                    code=INVALID,
                    constraint_code=instance.code,
                    severity="warning",
                    refs=(Ref(kind="constraint", code=instance.code),),
                    message=f'constraint "{instance.code}" ({TYPE}): {error}; it was not checked',
                )
            )
            continue
        elsewhere = [
            e
            for e in instance.targets
            if e in ctx.placements and ctx.placements[e].start not in wanted
        ]
        if elsewhere:
            out.append(
                instance.violation(
                    len(elsewhere),
                    f"{len(elsewhere)} event(s) outside the preferred times: "
                    + ", ".join(elsewhere),
                    *(event_ref(e) for e in elsewhere),
                )
            )
    return out
