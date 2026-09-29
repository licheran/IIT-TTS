"""H5 `pin`: an assignment equals its pin in every field the pin sets.

A pinned event with no assignment is left to the placement rule (H0).
"""

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.model import Dataset, Result, Violation

CODE = "H5"
TYPE = "pin"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found = []
    for pin in dataset.pins:
        assignment = ctx.assignment(pin.event)
        if assignment is None:
            continue
        problems = []
        if pin.day is not None and assignment.day != pin.day:
            problems.append(f'day is "{assignment.day}", pinned to "{pin.day}"')
        if pin.start_period is not None and assignment.start_period != pin.start_period:
            problems.append(f'start is "{assignment.start_period}", pinned to "{pin.start_period}"')
        missing = sorted(set(pin.resources) - set(ctx.chosen_resources(pin.event)))
        if missing:
            problems.append("missing pinned " + ", ".join(f'"{m}"' for m in missing))
        if problems:
            found.append(
                hard(
                    TYPE,
                    CODE,
                    f'event "{pin.event}" ignores its {pin.source} pin: ' + "; ".join(problems),
                    event_ref(pin.event),
                    *(resource_ref(m) for m in missing),
                )
            )
    return found
