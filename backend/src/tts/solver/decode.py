"""Reading a CP-SAT solution back into a `Result` (spec 05 section 1, the `decode` stage)."""

from collections import defaultdict

from ortools.sat.python import cp_model

from tts.core.model import Assignment, PooledChoice, Result
from tts.solver.context import CompileContext


def decode(ctx: CompileContext, solver: cp_model.CpSolver) -> Result:
    """The assignments of a solved model: each event's day and start, and its pooled choices."""
    chosen: dict[tuple[str, int], list[str]] = defaultdict(list)
    for (event, ordinal, resource), literal in ctx.use.items():
        if solver.boolean_value(literal):
            chosen[(event, ordinal)].append(resource)

    assignments = []
    for code in ctx.events:
        day, period = ctx.grid.codes(solver.value(ctx.start[code]))
        choices = tuple(
            PooledChoice(ordinal=ordinal, resources=tuple(resources))
            for (event, ordinal), resources in sorted(chosen.items())
            if event == code
        )
        assignments.append(Assignment(event=code, day=day, start_period=period, chosen=choices))
    return Result(assignments=tuple(assignments))
