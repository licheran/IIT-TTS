"""Teacher fairness on L6 written as configuration (Phase 25 acceptance, ADR-0008)."""

import pytest
from make_config import build  # type: ignore[import-not-found]

from tts.api.expansion import prepare_with_preset
from tts.core.constraints.context import VerifyContext
from tts.core.constraints.max_load import weekly_load
from tts.core.demands import realise
from tts.core.model import Dataset, Result
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.presets import derive_demands, with_defaults
from tts.solver.decompose import solve_dataset

CAP = 12  # periods a week; the unconstrained timetable has teachers above it


def with_max_hours(dataset: Dataset, hours: int) -> Dataset:
    teachers = tuple(
        r.model_copy(update={"attributes": (*r.attributes, ("max_hours", hours))})
        if r.type == "Teacher"
        else r
        for r in dataset.resources
    )
    return dataset.model_copy(update={"resources": teachers})


def loads(dataset: Dataset, result: Result) -> dict[str, int]:
    context = VerifyContext(realise(dataset, result), result, base=dataset)
    return {
        r.code: weekly_load(context, r.code, "periods")
        for r in dataset.resources
        if r.type == "Teacher"
    }


def soft_by_rule(dataset: Dataset, result: Result) -> dict[str, int]:
    found: dict[str, int] = {}
    for v in verify(dataset, result):
        if v.severity == "soft":
            rule = v.constraint_code.split("-")[0]
            found[rule] = found.get(rule, 0) + v.penalty
    return found


def test_no_teacher_goes_over_max_hours() -> None:
    prepared = prepare_with_preset(with_max_hours(build(), CAP))
    assert sum(c.code.startswith("LOAD-") for c in prepared.constraints) == sum(
        r.type == "Teacher" for r in prepared.resources
    )
    params = RunParams(time_limit_s=120, num_workers=4, seed=0, mode="feasible")
    outcome = solve_dataset(prepared, params)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    assert hard_violations(verify(prepared, outcome.result)) == []
    assert max(loads(prepared, outcome.result).values()) <= CAP


@pytest.mark.scale
def test_the_fairness_rules_improve_the_balance_against_a_run_without_them() -> None:
    base = with_max_hours(with_defaults(build()), CAP)
    without = base.model_copy(update={"demands": derive_demands(base)})
    full = prepare_with_preset(base)
    params = RunParams(time_limit_s=120, num_workers=4, seed=0, mode="optimise")
    plain = solve_dataset(without, params)
    fair = solve_dataset(full, params)
    assert plain.result is not None and fair.result is not None
    assert hard_violations(verify(full, plain.result)) == []
    assert hard_violations(verify(full, fair.result)) == []
    before = soft_by_rule(full, plain.result).get("FAIR", 0)
    after = soft_by_rule(full, fair.result).get("FAIR", 0)
    assert after < before, (before, after)
