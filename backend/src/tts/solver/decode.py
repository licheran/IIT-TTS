"""Reading a CP-SAT solution back into a `Result` (spec 05 section 1, the `decode` stage)."""

from collections import defaultdict

from ortools.sat.python import cp_model

from tts.core.model import Assignment, CreatedEvent, PooledChoice, Result
from tts.solver.context import CompileContext


def decode(ctx: CompileContext, solver: cp_model.CpSolver) -> Result:
    """The assignments of a solved model: each event's day and start, and its pooled choices.

    Sessions the solver created for demands are named here (`<reference or demand>-<kind>-<nn>`,
    by block in order of its lowest participant, then by start) and listed in `Result.created`
    with their participants.
    """
    chosen: dict[tuple[str, int], list[str]] = defaultdict(list)
    for (event, ordinal, resource), literal in ctx.use.items():
        if solver.boolean_value(literal):
            chosen[(event, ordinal)].append(resource)

    names, created = _created_events(ctx, solver)
    assignments = []
    for code in ctx.events:
        day, period = ctx.grid.codes(solver.value(ctx.start[code]))
        choices = tuple(
            PooledChoice(ordinal=ordinal, resources=tuple(resources))
            for (event, ordinal), resources in sorted(chosen.items())
            if event == code
        )
        assignments.append(
            Assignment(event=names.get(code, code), day=day, start_period=period, chosen=choices)
        )
    return Result(assignments=tuple(assignments), created=tuple(created))


def _created_events(
    ctx: CompileContext, solver: cp_model.CpSolver
) -> tuple[dict[str, str], list[CreatedEvent]]:
    """Final codes for the sessions the solver created, and the events themselves."""
    mat = ctx.materialised
    if mat is None or not mat.blocks:
        return {}, []
    made = {code for b in mat.blocks for code in b.made}
    taken = {code for code in ctx.events if code not in made}
    numbers: dict[tuple[str, str], int] = defaultdict(int)
    names: dict[str, str] = {}
    created: list[CreatedEvent] = []
    for demand in ctx.dataset.demands:
        blocks = []
        for block in mat.blocks:
            if block.demand != demand.code or not block.made:
                continue
            if block.fixed is not None:
                participants = block.fixed
            else:
                members = ctx.block_members[(demand.code, block.index)]
                participants = tuple(p for p, literal in members if solver.boolean_value(literal))
            blocks.append((participants, block))
        blocks.sort(key=lambda item: min(item[0]))
        prefix = demand.reference or demand.code
        for participants, block in blocks:
            for event in sorted(block.made, key=lambda c: (solver.value(ctx.start[c]), c)):
                while True:
                    numbers[(prefix, demand.kind)] += 1
                    final = f"{prefix}-{demand.kind}-{numbers[(prefix, demand.kind)]:02d}"
                    if final not in taken:
                        break
                taken.add(final)
                names[event] = final
                created.append(
                    CreatedEvent(code=final, demand=demand.code, participants=participants)
                )
    return names, created
