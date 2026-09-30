"""C1 `max_per_day` (semantics in `core/constraints/max_per_day.py`)."""

from tts.core.constraints.max_per_day import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, excess, finish, load
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    limit, unit = instance.params.max, instance.params.unit
    periods = ctx.grid.periods_per_day
    terms: list[Term] = []
    for resource in instance.targets:
        for day in range(ctx.grid.day_count):
            if unit == "periods":
                items = [
                    occ
                    for p in range(periods)
                    if not ctx.grid.is_break(p)
                    and (occ := ctx.occupied(resource, day * periods + p)) is not None
                ]
            else:
                items = []
                for event, needs in ctx.occupying_events(resource):
                    on_day = ctx.day_is(event, day)
                    items.append(
                        on_day
                        if needs is None
                        else ctx.both(needs, on_day, f"d_{event}_{resource}_{day}")
                    )
            if len(items) > limit:
                terms.append(
                    excess(
                        ctx, sum(items), limit, len(items), f"c1_{constraint.code}_{resource}_{day}"
                    )
                )
    finish(ctx, constraint, terms)
