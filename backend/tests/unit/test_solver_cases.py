"""Every hand-made case of the verifier suite (Phase 1), solved. Judged by the verifier only."""

import pytest
from test_verifier_cases import CASES

from tts.core.model import Pin, PooledChoice, Result
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.solver.solve import solve

QUICK = RunParams(time_limit_s=20, num_workers=1, seed=0)


@pytest.mark.parametrize("name", CASES)
def test_the_case_is_solvable_and_the_result_has_no_hard_violation(name: str) -> None:
    case = CASES[name]()
    outcome = solve(case.dataset, QUICK)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    assert hard_violations(verify(case.dataset, outcome.result)) == []


@pytest.mark.parametrize("name", CASES)
def test_pinning_the_corrected_result_reproduces_it(name: str) -> None:
    """The corrected twin of each case is one valid answer. Locked in, it is the only one."""
    case = CASES[name]()
    locks = tuple(
        Pin(
            event=a.event,
            day=a.day,
            start_period=a.start_period,
            resources=tuple(r for c in a.chosen for r in c.resources),
            source="lock",
        )
        for a in case.fixed.assignments
    )
    locked = case.dataset.model_copy(update={"pins": (*case.dataset.pins, *locks)})
    outcome = solve(locked, QUICK)
    assert outcome.result == case.fixed


@pytest.mark.parametrize("name", CASES)
def test_the_broken_result_is_not_what_the_solver_returns(name: str) -> None:
    case = CASES[name]()
    outcome = solve(case.dataset, QUICK)
    assert outcome.result is not None
    assert outcome.result != case.broken
    assert verify(case.dataset, case.broken) != []  # ... and it really was broken


def test_pooled_choices_are_decoded_per_requirement() -> None:
    case = CASES["pooled_double_booking"]()
    outcome = solve(case.dataset, QUICK)
    assert outcome.result is not None
    for assignment in outcome.result.assignments:
        assert [c.ordinal for c in assignment.chosen] == [0]
        assert isinstance(assignment.chosen[0], PooledChoice)
    first, second = outcome.result.assignments
    same_slot = (first.day, first.start_period) == (second.day, second.start_period)
    if same_slot:  # one room cannot serve two events at once
        assert first.chosen[0].resources != second.chosen[0].resources
    assert isinstance(outcome.result, Result)
