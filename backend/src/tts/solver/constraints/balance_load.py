"""C16 `balance_load` (semantics in `core/constraints/balance_load.py`).

`hi` is at least every load and `lo` at most every load, so `hi - lo` is at least the spread; the
minimiser (or the hard `== 0`) makes it equal to it.
"""

from tts.core.constraints.balance_load import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load
from tts.solver.constraints.max_load import load_items
from tts.solver.context import CompileContext


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    terms: list[Term] = []
    if len(instance.targets) >= 2:
        loads = [load_items(ctx, r, instance.params.unit) for r in instance.targets]
        top = max(len(items) for items in loads)
        name = f"c16_{constraint.code}"
        hi = ctx.model.new_int_var(0, top, f"{name}_hi")
        lo = ctx.model.new_int_var(0, top, f"{name}_lo")
        for items in loads:
            ctx.model.add(hi >= sum(items))
            ctx.model.add(lo <= sum(items))
        terms.append(hi - lo)
    finish(ctx, constraint, terms)
