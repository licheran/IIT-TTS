"""H4 `requirement_match`: a chosen pooled resource has the required type and matches the filter."""

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.model import Dataset, Result, Violation
from tts.core.selectors import SelectorError

CODE = "H4"
TYPE = "requirement_match"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found = []
    matches: dict[str, frozenset[str] | None] = {}  # filter text -> matching codes (None: invalid)

    for event in sorted(ctx.events):
        chosen = ctx.chosen(event)
        for q in ctx.pooled.get(event, ()):
            if q.filter not in matches:
                try:
                    matches[q.filter] = ctx.selectors.resources(q.filter)
                except SelectorError as error:
                    matches[q.filter] = None
                    found.append(
                        hard(
                            TYPE,
                            CODE,
                            f'filter "{q.filter}" of requirement {event}#{q.ordinal} is invalid:'
                            f" {error.message}",
                            event_ref(event),
                        )
                    )
            matching = matches[q.filter]
            for code in sorted(set(chosen.get(q.ordinal, ()))):
                resource = ctx.resources.get(code)
                if resource is None:
                    continue  # reported by the placement rule
                if resource.type != q.resource_type:
                    found.append(
                        hard(
                            TYPE,
                            CODE,
                            f'"{code}" is of type "{resource.type}", but requirement'
                            f' {event}#{q.ordinal} needs type "{q.resource_type}"',
                            event_ref(event),
                            resource_ref(code),
                        )
                    )
                elif matching is not None and code not in matching:
                    found.append(
                        hard(
                            TYPE,
                            CODE,
                            f'"{code}" does not match filter "{q.filter}" of requirement'
                            f" {event}#{q.ordinal}",
                            event_ref(event),
                            resource_ref(code),
                        )
                    )
    return found
