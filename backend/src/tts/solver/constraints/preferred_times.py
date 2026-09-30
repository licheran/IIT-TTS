"""C11 `preferred_times` (semantics in `core/constraints/preferred_times.py`)."""

from ortools.sat.python import cp_model

from tts.core.constraints.preferred_times import Params, slot_set
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext
from tts.solver.registry import UnsupportedConstraintError


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    try:
        wanted = slot_set(ctx.grid, instance.params.slots)
    except ValueError as error:
        message = f'constraint "{constraint.code}" ({constraint.type}): {error}'
        if constraint.hard:
            raise UnsupportedConstraintError(message) from None
        ctx.warnings.append(f"{message}; it was ignored")
        return
    terms: list[Term] = []
    for e in instance.targets:
        if e not in ctx.events:
            continue
        domain = ctx.domains[e]
        good = [t for t in domain if t in wanted]
        if len(good) == len(domain):
            continue  # every possible start is preferred
        if not good:
            terms.append(1)  # no preferred start is possible at all
            continue
        v = violated(ctx, f"c11_{constraint.code}_{e}")
        ctx.model.add_linear_expression_in_domain(
            ctx.start[e], cp_model.Domain.from_values(good)
        ).only_enforce_if(v.Not())
        terms.append(v)
    finish(ctx, constraint, terms)
