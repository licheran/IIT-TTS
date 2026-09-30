"""C5 `same_start`: all selected events start in the same slot.

Penalty: the number of placed events not at the most common start.
"""

from collections import Counter

from tts.core.constraints.base import NoParams, event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "same_start"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        starts = {e: ctx.placements[e].start for e in instance.targets if e in ctx.placements}
        if not starts:
            continue
        common, count = Counter(starts.values()).most_common(1)[0]
        others = sorted(e for e, t in starts.items() if t != common)
        if others:
            out.append(
                instance.violation(
                    len(starts) - count,
                    f"{len(others)} event(s) do not start with the others: " + ", ".join(others),
                    *(event_ref(e) for e in others),
                )
            )
    return out
