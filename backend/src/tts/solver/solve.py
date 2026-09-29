"""Running CP-SAT on a compiled model (spec 05 sections 1 and 4.4).

The stages stay separate: `compile_model`, `solve_model`, `decode`, then the verifier. `solve` runs
the first three. Every result must still be checked by `tts.core.verifier.verify`, because the
solver's own status is not evidence that a timetable is valid.
"""

from dataclasses import dataclass
from typing import Literal

from ortools.sat.python import cp_model

from tts.core.model import Dataset, Result
from tts.core.run import RunParams
from tts.solver.compile import compile_model
from tts.solver.context import CompileContext
from tts.solver.decode import decode

SolveStatus = Literal["optimal", "feasible", "infeasible", "unknown", "invalid"]

_STATUS: dict[cp_model.CpSolverStatus, SolveStatus] = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.MODEL_INVALID: "invalid",
    cp_model.UNKNOWN: "unknown",
}


@dataclass(frozen=True, slots=True)
class SolveStats:
    wall_time_s: float
    conflicts: int
    branches: int
    workers: int
    seed: int
    objective: float | None
    best_bound: float | None


@dataclass(frozen=True, slots=True)
class SolveOutcome:
    """The solver's answer. `result` is set exactly for `optimal` and `feasible`.

    `problems` are reasons found while compiling that already make a solution impossible (an
    event with no start left, a requirement with too few candidates). `warnings` are things
    that were ignored.
    """

    status: SolveStatus
    result: Result | None
    stats: SolveStats
    problems: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def has_solution(self) -> bool:
        return self.result is not None


def solve_model(ctx: CompileContext, params: RunParams) -> SolveOutcome:
    """Solve a compiled model with the given parameters and decode the solution."""
    solver = cp_model.CpSolver()
    workers = params.num_workers if params.num_workers is not None else _cpu_count()
    solver.parameters.max_time_in_seconds = params.time_limit_s
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = params.seed
    if params.mode == "feasible":
        solver.parameters.stop_after_first_solution = True

    status = _STATUS.get(solver.solve(ctx.model), "unknown")
    has_solution = status in ("optimal", "feasible")
    has_objective = ctx.model.has_objective()
    return SolveOutcome(
        status=status,
        result=decode(ctx, solver) if has_solution else None,
        stats=SolveStats(
            wall_time_s=solver.wall_time,
            conflicts=solver.num_conflicts,
            branches=solver.num_branches,
            workers=workers,
            seed=params.seed,
            objective=solver.objective_value if has_solution and has_objective else None,
            best_bound=solver.best_objective_bound if has_solution and has_objective else None,
        ),
        problems=tuple(ctx.problems),
        warnings=tuple(ctx.warnings),
    )


def solve(dataset: Dataset, params: RunParams | None = None) -> SolveOutcome:
    """Compile, solve and decode. Does not verify: call `tts.core.verifier.verify` on the result."""
    return solve_model(compile_model(dataset), params or RunParams())


def _cpu_count() -> int:
    import os

    return os.cpu_count() or 1
