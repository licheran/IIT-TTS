"""C6 `same_day` (semantics in `core/constraints/same_day.py`)."""

from tts.core.constraints.same_day import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    events = [e for e in instance.targets if e in ctx.events]
    terms: list[Term] = []
    if len(events) > 1:
        common = ctx.model.new_int_var(0, max(ctx.grid.day_count - 1, 0), f"c6_{constraint.code}")
        for e in events:
            v = violated(ctx, f"c6_{constraint.code}_{e}")
            ctx.model.add(ctx.day_var(e) == common).only_enforce_if(v.Not())
            terms.append(v)
    finish(ctx, constraint, terms)
