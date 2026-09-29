"""H0 `placement`: each event has exactly one allowed start and the right pooled resources."""

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.model import Dataset, Result, Violation
from tts.core.timegrid import TimeGridError

CODE = "H0"
TYPE = "placement"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found: list[Violation] = []

    for code, items in sorted(ctx.assignments.items()):
        if code not in ctx.events:
            found.append(
                hard(TYPE, CODE, f'assignment for unknown event "{code}"', event_ref(code))
            )
        elif len(items) > 1:
            found.append(
                hard(TYPE, CODE, f'event "{code}" has {len(items)} assignments', event_ref(code))
            )

    for code, event in sorted(ctx.events.items()):
        assignment = ctx.assignment(code)
        if assignment is None:
            found.append(hard(TYPE, CODE, f'event "{code}" has no assignment', event_ref(code)))
            continue

        try:
            start = ctx.grid.slot(assignment.day, assignment.start_period)
            allowed = ctx.allowed_starts(event)
        except TimeGridError as error:
            found.append(hard(TYPE, CODE, f'event "{code}": {error}', event_ref(code)))
        else:
            if start not in allowed:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'event "{code}" starts at {assignment.day}/{assignment.start_period},'
                        " which is not an allowed start",
                        event_ref(code),
                        ctx.slot_ref(start),
                    )
                )

        ordinals = [c.ordinal for c in assignment.chosen]
        for ordinal in sorted({o for o in ordinals if ordinals.count(o) > 1}):
            found.append(
                hard(
                    TYPE,
                    CODE,
                    f'event "{code}" chooses requirement #{ordinal} twice',
                    event_ref(code),
                )
            )

        requirements = {q.ordinal: q for q in ctx.pooled.get(code, ())}
        chosen = ctx.chosen(code)
        for ordinal in sorted(set(chosen) - set(requirements)):
            found.append(
                hard(
                    TYPE,
                    CODE,
                    f'event "{code}" chooses resources for unknown requirement #{ordinal}',
                    event_ref(code),
                )
            )
        for ordinal, q in sorted(requirements.items()):
            resources = chosen.get(ordinal, ())
            distinct = set(resources)
            label = f"{code}#{ordinal}"
            if len(distinct) != len(resources):
                found.append(
                    hard(TYPE, CODE, f"requirement {label} repeats a resource", event_ref(code))
                )
            if len(distinct) != q.count:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f"requirement {label} needs {q.count} resource(s) but has {len(distinct)}",
                        event_ref(code),
                    )
                )
            for resource in sorted(distinct - set(ctx.resources)):
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'requirement {label} names unknown resource "{resource}"',
                        event_ref(code),
                        resource_ref(resource),
                    )
                )
    return found
