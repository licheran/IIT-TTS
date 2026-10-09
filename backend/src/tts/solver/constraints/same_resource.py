"""C17 `same_resource` (semantics in `core/constraints/same_resource.py`).

For each resource of type `per`, one literal picks the resource of type `type` that its events
should share; `same` is at most the number of its events that use the picked one. The events
minus `same` is at least the penalty, and the minimiser (or the hard `== 0`) makes it equal.
"""

from ortools.sat.python import cp_model

from tts.core.constraints.same_resource import Params
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load
from tts.solver.context import CompileContext


def _both(
    ctx: CompileContext, member: cp_model.IntVar | None, used: cp_model.IntVar | bool, name: str
) -> Term | None:
    """`member and used`, as a literal or the constant 1; None when it can never hold."""
    if used is True:
        return 1 if member is None else member
    assert not isinstance(used, bool)
    return used if member is None else ctx.both(member, used, name)


def _uses(ctx: CompileContext, event: str, resource: str) -> cp_model.IntVar | bool | None:
    """True if the event always uses the resource, a literal if it may, None if it never can."""
    if event in ctx.fixed_occupants(resource):
        return True
    return ctx.uses(event, resource)


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    kind, per = instance.params.type, instance.params.per
    scope = set(instance.targets)
    choices = sorted(code for code, r in ctx.resources.items() if r.type == kind)
    terms: list[Term] = []
    for owner in sorted(code for code, r in ctx.resources.items() if r.type == per):
        members = [(e, needs) for e, needs in ctx.occupying_events(owner) if e in scope]
        if len(members) < 2:
            continue
        name = f"c17_{constraint.code}_{owner}"
        counts: dict[str, list[Term]] = {}
        for resource in choices:
            parts: list[Term] = []
            for event, needs in members:
                used = _uses(ctx, event, resource)
                if used is None:
                    continue
                joined = _both(ctx, needs, used, f"{name}_{event}_{resource}")
                if joined is not None:
                    parts.append(joined)
            if parts:
                counts[resource] = parts
        same = ctx.model.new_int_var(0, len(members), f"{name}_same")
        if counts:
            picks = {r: ctx.model.new_bool_var(f"{name}_pick_{r}") for r in counts}
            ctx.model.add_exactly_one(picks.values())
            for resource, parts in counts.items():
                ctx.model.add(same <= sum(parts)).only_enforce_if(picks[resource])
        else:
            ctx.model.add(same == 0)
        terms.append(sum(1 if needs is None else needs for _, needs in members) - same)
    finish(ctx, constraint, terms)
