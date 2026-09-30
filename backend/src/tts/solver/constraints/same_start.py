"""C5 `same_start` (semantics in `core/constraints/same_start.py`).

A free "common start" variable; each event either starts there or counts one. The minimiser puts
the common start where most events are.
"""

from ortools.sat.python import cp_model

from tts.core.constraints.same_start import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    events = [e for e in instance.targets if e in ctx.events]
    terms: list[Term] = []
    values = sorted({t for e in events for t in ctx.domains[e]})
    if len(events) > 1 and values:
        common = ctx.model.new_int_var_from_domain(
            cp_model.Domain.from_values(values), f"c5_{constraint.code}"
        )
        for e in events:
            v = violated(ctx, f"c5_{constraint.code}_{e}")
            ctx.model.add(ctx.start[e] == common).only_enforce_if(v.Not())
            terms.append(v)
    finish(ctx, constraint, terms)
