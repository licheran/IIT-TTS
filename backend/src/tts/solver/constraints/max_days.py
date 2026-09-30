"""C3 `max_days` (semantics in `core/constraints/max_days.py`).

A busy-day literal is at least "an event occupying the resource starts that day"; the busy days
above `max` are the penalty.
"""

from ortools.sat.python import cp_model

from tts.core.constraints.max_days import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, excess, finish, load
from tts.solver.context import CompileContext


def busy_literals(ctx: CompileContext, resource: str, name: str) -> list[cp_model.IntVar]:
    """One literal per day that can be busy, at least 1 when the resource is used that day."""
    occupants = ctx.occupying_events(resource)
    found = []
    for day in range(ctx.grid.day_count):
        possible = [
            (event, needs)
            for event, needs in occupants
            if any(ctx.grid.day_index(t) == day for t in ctx.domains[event])
        ]
        if not possible:
            continue
        busy = ctx.model.new_bool_var(f"{name}_{day}")
        for event, needs in possible:
            on_day = ctx.day_is(event, day)
            if needs is None:
                ctx.model.add_implication(on_day, busy)
            else:
                ctx.model.add_bool_or([on_day.Not(), needs.Not(), busy])
        found.append(busy)
    return found


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    limit = instance.params.max
    terms: list[Term] = []
    for resource in instance.targets:
        name = f"c3_{constraint.code}_{resource}"
        busy = busy_literals(ctx, resource, name)
        if len(busy) > limit:
            terms.append(excess(ctx, sum(busy), limit, len(busy), f"{name}_x"))
    finish(ctx, constraint, terms)
