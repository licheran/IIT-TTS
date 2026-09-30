"""C6 `same_day`: all selected events are on the same day.

Penalty: the number of placed events not on the most common day.
"""

from collections import Counter

from tts.core.constraints.base import NoParams, event_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import instances
from tts.core.model import Dataset, Result, Violation

TYPE = "same_day"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        days = {
            e: ctx.grid.day_index(ctx.placements[e].start)
            for e in instance.targets
            if e in ctx.placements
        }
        if not days:
            continue
        common, count = Counter(days.values()).most_common(1)[0]
        others = sorted(e for e, d in days.items() if d != common)
        if others:
            out.append(
                instance.violation(
                    len(days) - count,
                    f"{len(others)} event(s) are not on the same day as the others: "
                    + ", ".join(others),
                    *(event_ref(e) for e in others),
                )
            )
    return out
