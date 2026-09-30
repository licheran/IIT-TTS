"""L6 written as configuration and solved by the solver (P20.8, ADR-0007).

Every test judges the timetable with the verifier. The numbers below are facts of the real L6
data: 20 module and kind pairs, made of 72 sessions once groups share by the original limits.
"""

from collections import Counter

import pytest
from l6_config import configured_l6

from tts.core.model import Dataset, Result
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.preflight.checks import run_preflight
from tts.solver.solve import solve

FOUR_WORKERS = RunParams(time_limit_s=120, num_workers=4, seed=0)  # the P20.8 target: 120 s


@pytest.fixture(scope="module")
def configured(l6_dataset: Dataset) -> Dataset:
    return configured_l6(l6_dataset)


@pytest.fixture(scope="module")
def solved(configured: Dataset) -> Result:
    outcome = solve(configured, FOUR_WORKERS)
    assert outcome.result is not None, (outcome.status, outcome.problems)
    return outcome.result


def test_the_configuration_is_sound_and_has_no_pre_flight_error(configured: Dataset) -> None:
    assert configured.validate_invariants() == []
    assert [i for i in run_preflight(configured) if i.severity == "error"] == []
    assert configured.events == () and len(configured.demands) == 20


def test_the_solver_finds_a_timetable_the_verifier_accepts(
    configured: Dataset, solved: Result
) -> None:
    assert hard_violations(verify(configured, solved)) == []
    assert len(solved.created) == 72
    assert len(solved.assignments) == 72


def test_every_group_attends_each_of_its_modules_sessions_once(
    configured: Dataset, solved: Result
) -> None:
    attended: dict[tuple[str, str], int] = Counter()
    for created in solved.created:
        for group in created.participants:
            attended[(created.demand, group)] += 1
    for demand in configured.demands:
        for group in demand.participants:
            assert attended[(demand.code, group)] == demand.repeat, (demand.code, group)


def test_no_session_has_more_groups_than_its_limit_and_blocks_are_even(
    configured: Dataset, solved: Result
) -> None:
    for demand in configured.demands:
        sizes = [len(c.participants) for c in solved.created if c.demand == demand.code]
        assert max(sizes) <= (demand.max_participants or len(demand.participants))
        assert max(sizes) - min(sizes) <= 1, (demand.code, sizes)


def test_every_teacher_is_one_of_the_modules_teachers(configured: Dataset, solved: Result) -> None:
    pools = {
        d.code: set(d.pooled[-1].filter.removeprefix("code:").split(","))
        for d in configured.demands
        if d.pooled
    }
    owner = {c.code: c.demand for c in solved.created}
    teachers = {r.code for r in configured.resources if r.type == "Teacher"}
    for assignment in solved.assignments:
        picked = {r for choice in assignment.chosen for r in choice.resources if r in teachers}
        assert picked and picked <= pools[owner[assignment.event]]


def test_the_timetable_is_the_same_on_every_run_with_one_worker(configured: Dataset) -> None:
    one = RunParams(time_limit_s=120, num_workers=1, seed=0)
    first, second = solve(configured, one).result, solve(configured, one).result
    assert first is not None and first == second
