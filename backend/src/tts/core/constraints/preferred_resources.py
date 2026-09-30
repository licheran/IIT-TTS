"""C12 `preferred_resources`: every pooled resource chosen for a selected event matches `filter`.

Penalty: the number of chosen resources that do not match.
"""

from pydantic import BaseModel, ConfigDict

from tts.core.constraints.base import event_ref, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.constraints.declared import Instance, instances
from tts.core.model import Dataset, Result, Violation
from tts.core.selectors import SelectorError, Selectors, check_target

TYPE = "preferred_resources"


class Params(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str


def matching(selectors: Selectors, text: str) -> frozenset[str]:
    """The resources the filter selects. Raises `SelectorError`."""
    check_target(text, "resource")
    return selectors.resources(text)


def problems(dataset: Dataset, instance: Instance[Params]) -> list[str]:
    try:
        matching(Selectors(dataset), instance.params.filter)
    except SelectorError as error:
        return [f'filter "{instance.params.filter}": {error}']
    return []


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found, out = instances(ctx, TYPE, Params)
    for instance in found:
        try:
            allowed = matching(ctx.selectors, instance.params.filter)
        except SelectorError:
            continue  # reported by pre-flight; the solver refuses it too
        bad = [
            (e, r)
            for e in instance.targets
            if e in ctx.placements
            for r in ctx.chosen_resources(e)
            if r not in allowed
        ]
        if bad:
            out.append(
                instance.violation(
                    len(bad),
                    "not preferred: " + ", ".join(f"{r} for {e}" for e, r in bad),
                    *(event_ref(e) for e in sorted({e for e, _ in bad})),
                    *(resource_ref(r) for r in sorted({r for _, r in bad})),
                )
            )
    return out
