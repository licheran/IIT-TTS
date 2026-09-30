"""Running CP-SAT on a compiled model (spec 05 sections 1 and 4.4).

The stages stay separate: `compile_model`, `solve_model`, `decode`, then the verifier. `solve` runs
the first three. Every result must still be checked by `tts.core.verifier.verify`, because the
solver's own status is not evidence that a timetable is valid.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
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
    solutions: int = 0


@dataclass(frozen=True, slots=True)
class SolveProgress:
    """What the search has reached so far (spec 05 section 4.5)."""

    objective: float | None
    best_bound: float | None
    elapsed_s: float
    solutions: int


class SolveControl:
    """Lets another thread stop a running search. `stop` is safe to call at any time."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stopped = False
        self._solver: cp_model.CpSolver | None = None

    def attach(self, solver: cp_model.CpSolver) -> None:
        with self._lock:
            self._solver = solver
            if self._stopped:
                solver.stop_search()

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            if self._solver is not None:
                self._solver.stop_search()

    @property
    def stopped(self) -> bool:
        return self._stopped


class _Progress(cp_model.CpSolverSolutionCallback):
    """Reports each new solution, at most once per `interval_s` (the first always)."""

    def __init__(
        self,
        on_progress: Callable[[SolveProgress], None] | None,
        has_objective: bool,
        interval_s: float = 1.0,
    ) -> None:
        super().__init__()
        self._on_progress = on_progress
        self._has_objective = has_objective
        self._interval = interval_s
        self._last = float("-inf")
        self.solutions = 0

    def on_solution_callback(self) -> None:
        self.solutions += 1
        now = time.monotonic()
        if self._on_progress is None or now - self._last < self._interval:
            return
        self._last = now
        self._on_progress(
            SolveProgress(
                objective=self.objective_value if self._has_objective else None,
                best_bound=self.best_objective_bound if self._has_objective else None,
                elapsed_s=self.wall_time,
                solutions=self.solutions,
            )
        )


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
    penalties: dict[str, int] = field(default_factory=dict)  # soft instance code -> its `p`

    @property
    def has_solution(self) -> bool:
        return self.result is not None


def solve_model(
    ctx: CompileContext,
    params: RunParams,
    on_progress: Callable[[SolveProgress], None] | None = None,
    control: SolveControl | None = None,
) -> SolveOutcome:
    """Solve a compiled model with the given parameters and decode the solution.

    `on_progress` is called at most once a second while solutions improve. `control.stop()` from
    another thread ends the search and keeps the best solution found so far.
    """
    solver = cp_model.CpSolver()
    workers = params.num_workers if params.num_workers is not None else _cpu_count()
    solver.parameters.max_time_in_seconds = params.time_limit_s
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = params.seed
    if params.mode == "feasible":
        solver.parameters.stop_after_first_solution = True

    has_objective = ctx.model.has_objective()
    callback = _Progress(on_progress, has_objective)
    if control is not None:
        control.attach(solver)
    status = _STATUS.get(solver.solve(ctx.model, callback), "unknown")
    has_solution = status in ("optimal", "feasible")
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
            solutions=callback.solutions,
        ),
        problems=tuple(ctx.problems),
        warnings=tuple(ctx.warnings),
        penalties=(
            {name: int(solver.value(var)) for name, var in ctx.penalties.items()}
            if has_solution
            else {}
        ),
    )


def solve(dataset: Dataset, params: RunParams | None = None) -> SolveOutcome:
    """Compile, solve and decode. Does not verify: call `tts.core.verifier.verify` on the result."""
    return solve_model(compile_model(dataset), params or RunParams())


def _cpu_count() -> int:
    import os

    return os.cpu_count() or 1
