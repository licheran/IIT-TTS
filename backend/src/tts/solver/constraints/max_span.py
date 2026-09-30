"""C14 `max_span` (semantics in `core/constraints/max_span.py`).

For every two occupied positions i <= j of a day too far apart, the day's excess is at least
`(j - i + 1 - max)` when both are occupied. The largest such pair is the true excess.
"""

from tts.core.constraints.max_span import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    limit = instance.params.max
    periods = ctx.grid.periods_per_day
    usable = [p for p in range(periods) if not ctx.grid.is_break(p)]
    terms: list[Term] = []
    for resource in instance.targets:
        for day in range(ctx.grid.day_count):
            occ = {p: ctx.occupied(resource, day * periods + p) for p in usable}
            live = [p for p in usable if occ[p] is not None]
            pairs = [(i, j) for i in live for j in live if i <= j and j - i + 1 > limit]
            if not pairs:
                continue
            top = max(j - i + 1 for i, j in pairs) - limit
            x = ctx.model.new_int_var(0, top, f"c14_{constraint.code}_{resource}_{day}")
            for i, j in pairs:
                oi, oj = occ[i], occ[j]
                assert oi is not None and oj is not None
                over = j - i + 1 - limit
                if i == j:
                    ctx.model.add(x >= over * oi)
                else:
                    ctx.model.add(x >= over * (oi + oj - 1))
            terms.append(x)
    finish(ctx, constraint, terms)
