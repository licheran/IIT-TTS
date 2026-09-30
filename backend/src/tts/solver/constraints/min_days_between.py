"""C4 `min_days_between` (semantics in `core/constraints/min_days_between.py`)."""

from itertools import combinations

from tts.core.constraints.min_days_between import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    gap = instance.params.min
    terms: list[Term] = []
    if gap > 0:
        events = [e for e in instance.targets if e in ctx.events]
        top = max(ctx.grid.day_count - 1, 0)
        for a, b in combinations(events, 2):
            v = violated(ctx, f"c4_{constraint.code}_{a}_{b}")
            distance = ctx.model.new_int_var(0, top, f"c4d_{constraint.code}_{a}_{b}")
            ctx.model.add_abs_equality(distance, ctx.day_var(a) - ctx.day_var(b))
            ctx.model.add(distance >= gap).only_enforce_if(v.Not())
            terms.append(v)
    finish(ctx, constraint, terms)
