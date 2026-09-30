"""C9 `not_overlapping` (semantics in `core/constraints/not_overlapping.py`)."""

from itertools import combinations

from tts.core.constraints.not_overlapping import Params
from tts.core.model import Constraint
from tts.core.timegrid import covered_slots
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext


def _can_overlap(ctx: CompileContext, a: str, b: str) -> bool:
    def reach(e: str) -> set[int]:
        duration = ctx.events[e].duration
        return {t for s in ctx.domains[e] for t in covered_slots(s, duration)}

    return bool(reach(a) & reach(b))


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    events = [e for e in instance.targets if e in ctx.events]
    terms: list[Term] = []
    for a, b in combinations(events, 2):
        if not _can_overlap(ctx, a, b):
            continue
        name = f"c9_{constraint.code}_{a}_{b}"
        v = violated(ctx, name)
        a_first = ctx.model.new_bool_var(f"{name}_first")
        end_a = ctx.start[a] + ctx.events[a].duration
        end_b = ctx.start[b] + ctx.events[b].duration
        ctx.model.add(end_a <= ctx.start[b]).only_enforce_if([a_first, v.Not()])
        ctx.model.add(end_b <= ctx.start[a]).only_enforce_if([a_first.Not(), v.Not()])
        terms.append(v)
    finish(ctx, constraint, terms)
