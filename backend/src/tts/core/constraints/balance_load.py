"""C16 `balance_load`: the selected resources carry the same weekly load.

The load is the events (or occupied periods) of a resource over the week. Penalty: the load of the
most loaded resource minus that of the least loaded. With fewer than two resources there is
nothing to balance.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from tts.core.constraints.base import resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.constraints.max_load import weekly_load
from tts.core.model import Dataset, Result, Violation

TYPE = "balance_load"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    unit: Literal["events", "periods"] = "periods"


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        if len(instance.targets) < 2:
            continue
        unit = instance.params.unit
        loads = {r: weekly_load(ctx, r, unit) for r in instance.targets}
        most = max(instance.targets, key=lambda r: (loads[r], r))
        least = min(instance.targets, key=lambda r: (loads[r], r))
        spread = loads[most] - loads[least]
        if spread:
            out.append(
                instance.violation(
                    spread,
                    f"{most} has {loads[most]} {unit} and {least} has {loads[least]}",
                    resource_ref(most),
                    resource_ref(least),
                )
            )
    return out
