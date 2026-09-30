"""Shared steps of the declared-constraint compilers (spec 05 section 4.3).

A compiler builds non-negative terms whose sum is the penalty `p` of its instance, with the
semantics of the matching `core/constraints/<type>.py`. `finish` then makes the instance hard
(`p == 0`, guarded for explanations) or soft (a penalty variable in the objective). Terms may be
lower bounds of the true violation as long as the minimum over the auxiliary variables equals it,
because the objective only pushes them down; a hard `p == 0` then forces the true value to 0.
"""

from collections.abc import Iterable

from ortools.sat.python import cp_model
from pydantic import BaseModel

from tts.core.constraints.declared import Instance, InvalidConstraintError, parse_instance
from tts.core.model import Constraint
from tts.solver.context import CompileContext
from tts.solver.registry import UnsupportedConstraintError

Term = cp_model.LinearExprT


def load[P: BaseModel](
    ctx: CompileContext, constraint: Constraint, params_model: type[P]
) -> Instance[P] | None:
    """The instance, or None when it is invalid and soft (ignored with a warning).

    An invalid hard instance raises: ignoring it could break a rule the user declared.
    """
    try:
        return parse_instance(ctx.dataset, constraint, params_model, ctx.selectors)
    except InvalidConstraintError as error:
        if constraint.hard:
            raise UnsupportedConstraintError(str(error)) from None
        ctx.warnings.append(f"{error}; it was ignored")
        return None


def finish(ctx: CompileContext, constraint: Constraint, terms: Iterable[Term]) -> None:
    """Make `sum(terms)` the instance's penalty: required to be 0 if hard, minimised if soft."""
    items = list(terms)
    if constraint.hard:
        if not items:
            return
        rule = ctx.model.add(sum(items) == 0)
        guard = ctx.constraint_guard(constraint.code)
        if guard is not None:
            rule.only_enforce_if(guard)
        return
    penalty = ctx.penalty(constraint.code)
    ctx.model.add(penalty == sum(items) if items else penalty == 0)


def excess(ctx: CompileContext, amount: Term, limit: int, upper: int, name: str) -> cp_model.IntVar:
    """A variable at least `amount - limit` and at least 0 (the minimiser makes it the maximum)."""
    var = ctx.model.new_int_var(0, max(upper - limit, 0), name)
    ctx.model.add(var >= amount - limit)
    return var


def violated(ctx: CompileContext, name: str) -> cp_model.IntVar:
    """A literal that is 1 when a pair or event breaks the rule (0 forces the rule to hold)."""
    return ctx.model.new_bool_var(name)
