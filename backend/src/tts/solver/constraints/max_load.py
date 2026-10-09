"""C15 `max_load` (semantics in `core/constraints/max_load.py`).

The load of a resource is the sum of its occupied-period literals (or, for events, of the
literals that each event needs). The amount above `max` is the penalty.
"""

from tts.core.constraints.max_load import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, excess, finish, load
from tts.solver.context import CompileContext


def load_items(ctx: CompileContext, resource: str, unit: str) -> list[Term]:
    """What adds up to the weekly load of `resource`: literals, or 1 for an event it always has."""
    if unit == "periods":
        return [
            occupied
            for t in range(ctx.grid.slot_count)
            if not ctx.grid.is_break(t) and (occupied := ctx.occupied(resource, t)) is not None
        ]
    return [1 if needs is None else needs for _, needs in ctx.occupying_events(resource)]


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    limit, unit = instance.params.max, instance.params.unit
    terms: list[Term] = []
    for resource in instance.targets:
        items = load_items(ctx, resource, unit)
        if len(items) > limit:
            terms.append(
                excess(ctx, sum(items), limit, len(items), f"c15_{constraint.code}_{resource}")
            )
    finish(ctx, constraint, terms)
