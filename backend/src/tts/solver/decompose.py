"""Times first, then pooled resources (spec 05 section 7, strategy 3). Measured in P10.4.

On a large dataset most of the model is the choice of pooled resources (one literal per event
and candidate), although that choice is a matching once the times are known. So:

1. **Times.** Solve start times only (`compile_model(times_only=True)`): every rule on fixed
   resources, the soft rules, and for pooled resources only each pool's capacity at any time.
2. **Resources.** Pin every event to its time and solve the full model. With the times fixed it
   is a small assignment problem.
3. **Fallback.** If step 2 finds no assignment (the pool capacities are necessary, not always
   sufficient), solve the full model, hinted with the step 1 times, for the time that is left.

It is used only when nothing but the requirements depends on which pooled resource is chosen:
a pin that names resources must decide its event's only requirement exactly (as the locks of an
earlier stage do), no pooled candidate has unavailable periods, and no declared constraint looks
at pooled choices or at resources that can be chosen. Otherwise, and for small models,
`solve_dataset` solves the full model directly. Every result is verified by the caller as usual.
"""

import dataclasses
import time
from collections.abc import Callable

from tts.core.candidates import Candidates
from tts.core.constraints.catalogue import CATALOGUE
from tts.core.constraints.declared import InvalidConstraintError, parse_instance
from tts.core.constraints.registry import declared_type
from tts.core.demands import materialise, realise
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Pin
from tts.core.run import RunParams
from tts.core.selectors import SelectorError, Selectors
from tts.solver.compile import compile_model
from tts.solver.solve import SolveControl, SolveOutcome, SolveProgress, SolveStats, solve_model

# Below this many candidate literals the full model is fast enough (L6 has about 700).
DECOMPOSE_ABOVE = 20_000

# Declared types whose penalty depends on which pooled resource is chosen.
_LOOKS_AT_CHOICES = frozenset({"preferred_resources", "travel_gap"})

Progress = Callable[[SolveProgress], None]


def pooled_candidates(dataset: Dataset) -> dict[tuple[str, int], tuple[str, ...]]:
    """The static candidates of every pooled requirement (type, filter and capacity)."""
    hierarchy = Hierarchy(dataset)
    static = Candidates(dataset, hierarchy, Selectors(dataset, hierarchy))
    found = {}
    for q in dataset.pooled:
        try:
            found[(q.event, q.ordinal)] = static.of(q).codes
        except SelectorError:
            found[(q.event, q.ordinal)] = ()
    return found


def _pins_decide(dataset: Dataset, candidates: dict[tuple[str, int], tuple[str, ...]]) -> bool:
    """True when every pin that names resources decides its event's only requirement exactly
    (as locks from an earlier stage do): the times step then treats those resources as taken."""
    requirements: dict[str, list[tuple[int, int]]] = {}
    for q in dataset.pooled:
        requirements.setdefault(q.event, []).append((q.ordinal, q.count))
    for pin in dataset.pins:
        if not pin.resources:
            continue
        needs = requirements.get(pin.event, [])
        if len(needs) != 1:
            return False
        ordinal, count = needs[0]
        usable = set(candidates.get((pin.event, ordinal), ()))
        if len(pin.resources) != count or not set(pin.resources) <= usable:
            return False
    return True


def decomposable(dataset: Dataset) -> bool:
    """True when only the requirements (and locks that decide them) depend on the choice of
    pooled resources."""
    candidates = pooled_candidates(dataset)
    if not _pins_decide(dataset, candidates):
        return False
    choosable = {r for codes in candidates.values() for r in codes}
    if any(a.resource in choosable and a.status == "unavailable" for a in dataset.availability):
        return False
    selectors = Selectors(dataset)
    for c in dataset.constraints:
        if not c.active:
            continue
        if c.type in _LOOKS_AT_CHOICES:
            return False
        if CATALOGUE.get(c.type) == "resource":
            implementation = declared_type(c.type)
            if implementation is None:
                return False
            try:
                instance = parse_instance(dataset, c, implementation.Params, selectors)
            except InvalidConstraintError:
                return False
            if choosable & set(instance.targets):
                return False
    return True


def candidate_count(dataset: Dataset) -> int:
    return sum(len(codes) for codes in pooled_candidates(dataset).values())


def solve_dataset(
    dataset: Dataset,
    params: RunParams,
    on_progress: Progress | None = None,
    control: SolveControl | None = None,
) -> SolveOutcome:
    """Solve a dataset, decomposing it when that is safe and worthwhile."""
    # For demands, the analysis looks at the sessions the solver will create (ADR-0007).
    materialised = materialise(dataset) if dataset.demands else None
    analysed = materialised.dataset if materialised is not None else dataset
    large = candidate_count(analysed) > DECOMPOSE_ABOVE
    split = large and decomposable(analysed)
    if large and materialised is not None and materialised.free:
        # Choosing who shares a session adds a great many choices, so a large dataset first
        # tries the default split. If no timetable exists with it, the solver chooses (below).
        started = time.monotonic()
        first = params.model_copy(update={"time_limit_s": params.time_limit_s / 2})
        tried = (
            solve_decomposed(dataset, first, on_progress, control, greedy=True)
            if split
            else solve_model(compile_model(dataset, greedy=True), first, on_progress, control)
        )
        if tried.result is not None or (control is not None and control.stopped):
            note = (
                "participants were split by the default split (even blocks, in order of code); "
                "the solver did not search other splits"
            )
            return dataclasses.replace(tried, warnings=(*tried.warnings, note))
        left = max(params.time_limit_s - (time.monotonic() - started), 0.05)
        params = params.model_copy(update={"time_limit_s": left})
    if split:
        return solve_decomposed(dataset, params, on_progress, control)
    return solve_model(compile_model(dataset), params, on_progress, control)


def solve_decomposed(
    dataset: Dataset,
    params: RunParams,
    on_progress: Progress | None = None,
    control: SolveControl | None = None,
    greedy: bool = False,
) -> SolveOutcome:
    started = time.monotonic()

    def left() -> float:
        return max(params.time_limit_s - (time.monotonic() - started), 0.05)

    times = solve_model(
        compile_model(dataset, times_only=True, greedy=greedy), params, on_progress, control
    )
    if times.result is None or (control is not None and control.stopped):
        return times  # infeasible, out of time or cancelled: no timetable either way
    decided = {p.event: p.resources for p in dataset.pins if p.resources}
    pins = tuple(
        Pin(
            event=a.event,
            day=a.day,
            start_period=a.start_period,
            resources=decided.get(a.event, ()),
            source="lock",
        )
        for a in times.result.assignments
    )
    # With demands, the times step also chose the blocks: the sessions it created become
    # ordinary events here, so the second step only chooses rooms and teachers.
    pinned = realise(dataset, times.result).model_copy(update={"pins": pins})
    resources = solve_model(
        compile_model(pinned), params.model_copy(update={"time_limit_s": left()}), None, control
    )
    if resources.result is not None:
        kept = resources.result.model_copy(update={"created": times.result.created})
        resources = dataclasses.replace(resources, result=kept)
        return _combined(times, resources, time.monotonic() - started, "decomposed")

    # The capacities were not enough for a matching: solve everything, starting from the times.
    full = compile_model(dataset, greedy=greedy)
    for a in times.result.assignments:
        if a.event in full.start:  # sessions the solver creates have other names in the model
            full.model.add_hint(full.start[a.event], full.grid.slot(a.day, a.start_period))
    fallback = solve_model(
        full, params.model_copy(update={"time_limit_s": left()}), on_progress, control
    )
    return _combined(times, fallback, time.monotonic() - started, "decomposition fell back")


def _combined(first: SolveOutcome, second: SolveOutcome, wall: float, note: str) -> SolveOutcome:
    """One outcome for both steps. After a fallback the full model's status stands alone;
    otherwise the result is optimal only if both steps were (the first fixes the score)."""
    stats = second.stats
    status = second.status
    if note == "decomposed" and second.status == "optimal" and first.status != "optimal":
        status = "feasible"
    return SolveOutcome(
        status=status,
        result=second.result,
        stats=SolveStats(
            wall_time_s=wall,
            conflicts=first.stats.conflicts + stats.conflicts,
            branches=first.stats.branches + stats.branches,
            workers=stats.workers,
            seed=stats.seed,
            objective=stats.objective,
            best_bound=first.stats.best_bound,
            solutions=first.stats.solutions + stats.solutions,
        ),
        problems=second.problems,
        warnings=(*second.warnings, f"solved in two steps ({note}): times, then resources"),
        penalties=second.penalties,
    )
