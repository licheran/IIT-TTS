"""C12 `preferred_resources` (semantics in `core/constraints/preferred_resources.py`)."""

from tts.core.constraints.preferred_resources import Params, matching
from tts.core.model import Constraint
from tts.core.selectors import SelectorError
from tts.solver.constraints.base import Term, finish, load
from tts.solver.context import CompileContext
from tts.solver.registry import UnsupportedConstraintError


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    try:
        allowed = matching(ctx.selectors, instance.params.filter)
    except SelectorError as error:
        message = f'constraint "{constraint.code}": filter "{instance.params.filter}": {error}'
        if constraint.hard:
            raise UnsupportedConstraintError(message) from None
        ctx.warnings.append(f"{message}; it was ignored")
        return
    targets = set(instance.targets)
    terms: list[Term] = [
        literal
        for (event, _, resource), literal in ctx.use.items()
        if event in targets and resource not in allowed
    ]
    finish(ctx, constraint, terms)
