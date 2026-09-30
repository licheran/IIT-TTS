"""C2 `max_gaps` (semantics in `core/constraints/max_gaps.py`).

For each non-break period i of a day, `before_i` and `after_i` are at least "something is occupied
earlier (later) that day"; a gap literal is at least `before_i + after_i - occupied_i - 1`. The
minimiser keeps `before` and `after` at their true values, so the gaps are exact at the optimum.
"""

from ortools.sat.python import cp_model

from tts.core.constraints.max_gaps import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, excess, finish, load
from tts.solver.context import CompileContext


def day_gaps(ctx: CompileContext, resource: str, day: int, name: str) -> list[cp_model.IntVar]:
    """Gap literals of one resource on one day (empty when no gap is possible)."""
    periods = ctx.grid.periods_per_day
    usable = [p for p in range(periods) if not ctx.grid.is_break(p)]
    occ = [ctx.occupied(resource, day * periods + p) for p in usable]
    if sum(o is not None for o in occ) < 2:
        return []
    model = ctx.model
    n = len(usable)
    before: list[cp_model.IntVar | None] = [None] * n
    after: list[cp_model.IntVar | None] = [None] * n
    for i in range(1, n):
        sources = [s for s in (before[i - 1], occ[i - 1]) if s is not None]
        if sources:
            b = before[i] = model.new_bool_var(f"{name}_b{i}")
            for source in sources:
                model.add_implication(source, b)
    for i in range(n - 2, -1, -1):
        sources = [s for s in (after[i + 1], occ[i + 1]) if s is not None]
        if sources:
            a = after[i] = model.new_bool_var(f"{name}_a{i}")
            for source in sources:
                model.add_implication(source, a)
    found = []
    for i in range(1, n - 1):
        b, a, o = before[i], after[i], occ[i]
        if b is None or a is None:
            continue
        g = model.new_bool_var(f"{name}_g{i}")
        model.add(g >= b + a - (o if o is not None else 0) - 1)
        found.append(g)
    return found


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    limit, per = instance.params.max, instance.params.per
    terms: list[Term] = []
    for resource in instance.targets:
        weekly: list[cp_model.IntVar] = []
        for day in range(ctx.grid.day_count):
            name = f"c2_{constraint.code}_{resource}_{day}"
            found = day_gaps(ctx, resource, day, name)
            if per == "week":
                weekly.extend(found)
            elif len(found) > limit:
                terms.append(excess(ctx, sum(found), limit, len(found), f"{name}_x"))
        if per == "week" and len(weekly) > limit:
            name = f"c2_{constraint.code}_{resource}_w"
            terms.append(excess(ctx, sum(weekly), limit, len(weekly), name))
    finish(ctx, constraint, terms)
