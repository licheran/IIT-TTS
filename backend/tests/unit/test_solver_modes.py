"""The `mode` of `RunParams` (spec 05 section 4.4): optimise, feasible and two_phase."""

from constraint_helpers import rule

from fixtures import ev, make_dataset, res
from tts.core.run import RunParams
from tts.core.score import score
from tts.core.verifier import hard_violations, verify
from tts.presets.academic_weekly.defaults import with_defaults
from tts.solver.solve import solve


def gappy():
    """Six one-period events for t1 over three days; the soft rule wants them on one day."""
    return make_dataset(
        days=3,
        periods=6,
        resources=[res("t1", "T")],
        events=[ev(f"e{i}") for i in range(6)],
        fixed=[(f"e{i}", "t1") for i in range(6)],
        constraints=[rule("max_days", "code:t1", weight=3, max=1)],
    )


def params(mode: str, limit: float = 20, workers: int = 1) -> RunParams:
    return RunParams(time_limit_s=limit, num_workers=workers, seed=0, mode=mode)  # type: ignore[arg-type]


def scored(dataset, mode: str, limit: float = 20, workers: int = 1) -> int:
    outcome = solve(dataset, params(mode, limit, workers))
    assert outcome.result is not None
    violations = verify(dataset, outcome.result)
    assert hard_violations(violations) == []
    return score(dataset, violations).total


def test_two_phase_reaches_the_same_optimum_as_optimise() -> None:
    assert scored(gappy(), "two_phase") == scored(gappy(), "optimise") == 0


def test_feasible_stops_at_the_first_solution() -> None:
    outcome = solve(gappy(), params("feasible"))
    assert outcome.status in ("feasible", "optimal")
    assert outcome.stats.solutions == 1


def test_two_phase_without_soft_rules_is_a_plain_solve() -> None:
    plain = gappy().model_copy(update={"constraints": ()})
    outcome = solve(plain, params("two_phase"))
    assert outcome.status == "optimal"
    assert hard_violations(verify(plain, outcome.result)) == []  # type: ignore[arg-type]


def test_two_phase_improves_on_the_first_solution_of_l6(l6_dataset) -> None:
    with_rules = with_defaults(l6_dataset)
    # Four workers, as the soft search on L6 needs them (one worker is far slower; see STATUS).
    first = scored(with_rules, "feasible", limit=10, workers=4)
    better = scored(with_rules, "two_phase", limit=10, workers=4)
    assert better <= first
    assert better < 202  # the hard-only timetable's score under the same rules (P8.3)
