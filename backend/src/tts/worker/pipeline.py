"""The run pipeline (spec 05 section 1): expand, pre-flight, compile, solve, decode, verify.

`run_pipeline` is a plain function of a dataset and parameters. The worker calls it and stores what
it returns, so the same code serves the queue, tests and any future caller.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from tts.core.model import Dataset, Diagnostic, Ref, Result
from tts.core.run import RunParams
from tts.core.score import score as score_of
from tts.core.verifier import hard_violations, verify
from tts.preflight.checks import has_errors, run_preflight
from tts.presets import labeller
from tts.solver.compile import compile_model
from tts.solver.explain import explain
from tts.solver.registry import UnsupportedConstraintError
from tts.solver.solve import SolveControl, SolveProgress, solve_model

ProgressFn = Callable[[dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class PipelineOutcome:
    """What a run ends with. `status` is one of the run statuses of spec 06 section 4."""

    status: str
    result: Result | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    score: float | None = None
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    progress: dict[str, Any] = field(default_factory=dict)


def _progress_dict(progress: SolveProgress) -> dict[str, Any]:
    return {
        "objective": progress.objective,
        "best_bound": progress.best_bound,
        "elapsed_s": round(progress.elapsed_s, 2),
        "solutions": progress.solutions,
    }


def expand_dataset(dataset: Dataset) -> Dataset:
    """The expand stage: templates become events (a no-op on an already expanded dataset)."""
    from tts.api.expansion import expand_with_preset

    return expand_with_preset(dataset).dataset


def run_pipeline(
    dataset: Dataset,
    params: RunParams,
    control: SolveControl | None = None,
    on_progress: ProgressFn | None = None,
) -> PipelineOutcome:
    label = labeller(dataset.preset)
    dataset = expand_dataset(dataset)

    issues = run_preflight(dataset, label)
    diagnostics = [
        Diagnostic(
            kind=i.kind,
            severity="error" if i.severity == "error" else "warning",
            message=i.message,
            refs=i.refs,
        )
        for i in issues
    ]
    if has_errors(issues):
        return PipelineOutcome("blocked", diagnostics=tuple(diagnostics))

    def report(progress: SolveProgress) -> None:
        if on_progress is not None:
            on_progress(_progress_dict(progress))

    try:
        outcome = solve_model(compile_model(dataset), params, report, control)
    except UnsupportedConstraintError as error:
        diagnostics.append(Diagnostic(kind="unsupported_constraint", message=str(error)))
        return PipelineOutcome("failed", diagnostics=tuple(diagnostics))

    stats = outcome.stats
    final = {
        "objective": stats.objective,
        "best_bound": stats.best_bound,
        "elapsed_s": round(stats.wall_time_s, 2),
        "solutions": stats.solutions,
        "solver_status": outcome.status,
    }
    diagnostics.extend(
        Diagnostic(kind="solver_warning", severity="warning", message=w) for w in outcome.warnings
    )
    cancelled = control is not None and control.stopped

    if outcome.result is None:
        if cancelled:
            return PipelineOutcome("cancelled", diagnostics=tuple(diagnostics), progress=final)
        if outcome.status == "infeasible":
            diagnostics.extend(
                Diagnostic(kind="infeasible_reason", message=p) for p in outcome.problems
            )
            core = explain(dataset, label)
            if core is not None:
                diagnostics.append(core)
            return PipelineOutcome("infeasible", diagnostics=tuple(diagnostics), progress=final)
        diagnostics.append(
            Diagnostic(
                kind="no_solution",
                message=f"no timetable found within {params.time_limit_s:g} s "
                f"(solver status: {outcome.status})",
            )
        )
        return PipelineOutcome("failed", diagnostics=tuple(diagnostics), progress=final)

    violations = verify(dataset, outcome.result)
    bad = hard_violations(violations)
    diagnostics.extend(
        Diagnostic(
            kind="violation",
            severity="error" if v.severity == "hard" else "warning",
            message=v.message,
            refs=tuple(Ref(kind=r.kind, code=r.code) for r in v.refs),
            details=(v.constraint_code,),
        )
        for v in violations
        if v.severity != "soft"
    )
    scored = score_of(dataset, violations)
    breakdown = {code: line.model_dump() for code, line in scored.breakdown.items()}
    status = "invalid" if bad else "cancelled_partial" if cancelled else "succeeded"
    return PipelineOutcome(
        status,
        outcome.result,
        tuple(diagnostics),
        score=scored.total,
        score_breakdown=breakdown,
        progress=final,
    )
