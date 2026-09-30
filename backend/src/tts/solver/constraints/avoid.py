"""C13 `avoid` (semantics in `core/constraints/avoid.py`)."""

from tts.core.constraints.avoid import Params
from tts.core.model import Constraint
from tts.core.timegrid import TimeGridError
from tts.solver.constraints.base import Term, finish, load
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    targets = set(instance.targets)
    terms: list[Term] = []
    for row in ctx.dataset.availability:
        if row.status != "avoid" or row.resource not in targets:
            continue
        try:
            t = ctx.grid.slot(row.day, row.period)
        except TimeGridError:
            continue
        if ctx.grid.is_break(t):
            continue
        occupied = ctx.occupied(row.resource, t)
        if occupied is not None:
            terms.append(occupied)
    finish(ctx, constraint, terms)
