"""C8 `consecutive` (semantics in `core/constraints/consecutive.py`)."""

from tts.core.constraints.consecutive import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    sequence = instance.params.sequence
    terms: list[Term] = []
    for a, b in zip(sequence, sequence[1:], strict=False):
        if a not in ctx.events or b not in ctx.events:
            continue
        v = violated(ctx, f"c8_{constraint.code}_{a}_{b}")
        ok = v.Not()
        ctx.model.add(ctx.start[b] == ctx.start[a] + ctx.events[a].duration).only_enforce_if(ok)
        ctx.model.add(ctx.day_var(a) == ctx.day_var(b)).only_enforce_if(ok)
        terms.append(v)
    finish(ctx, constraint, terms)
