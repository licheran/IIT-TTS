"""Phase 8 acceptance on L6: the academic defaults make the timetable better, and no worse at
the hard rules (all judged by the verifier)."""

import pytest

from tts.core.model import Dataset
from tts.core.run import RunParams
from tts.core.score import score
from tts.core.verifier import hard_violations, verify
from tts.presets.academic_weekly.defaults import default_constraints, with_defaults
from tts.solver.solve import solve

PARAMS = RunParams(time_limit_s=20, num_workers=4, seed=0)

pytestmark = pytest.mark.integration


def test_the_defaults_give_l6_a_lower_penalty_than_the_hard_only_solution(
    l6_dataset: Dataset,
) -> None:
    with_rules = with_defaults(l6_dataset)
    hard_only = solve(l6_dataset, PARAMS)
    soft = solve(with_rules, PARAMS)
    assert hard_only.result is not None and soft.result is not None

    hard_only_violations = verify(with_rules, hard_only.result)
    soft_violations = verify(with_rules, soft.result)
    assert hard_violations(soft_violations) == []
    assert hard_violations(hard_only_violations) == []
    assert score(with_rules, soft_violations).total < score(with_rules, hard_only_violations).total


def test_the_defaults_follow_spec_04() -> None:
    from pathlib import Path

    from tts.io.fet_html import parse_fet_groups_html, to_dataset

    fet = Path(__file__).parent / "fet-groups-export.html"
    time = to_dataset(parse_fet_groups_html(fet))[0].time
    rules = {c.code: c for c in default_constraints(time)}
    assert set(rules) == {"AC-GAPS", "AC-TGAPS", "AC-TRAVEL", "AC-SAT"}
    assert rules["AC-GAPS"].params == {"max": 2, "per": "day"} and rules["AC-GAPS"].weight == 5
    assert rules["AC-TGAPS"].params == {"max": 3, "per": "day"} and rules["AC-TGAPS"].weight == 2
    assert rules["AC-TRAVEL"].active is False and rules["AC-TRAVEL"].weight == 10
    slots = rules["AC-SAT"].params["slots"]
    assert (
        isinstance(slots, list) and len(slots) == 5 * 13
    )  # Mon-Fri, 13 periods that are not breaks
    assert not any(str(s).startswith("Sat") for s in slots)
    assert all(not c.hard for c in rules.values())


def test_the_defaults_are_not_added_twice(l6_dataset: Dataset) -> None:
    once = with_defaults(l6_dataset)
    assert with_defaults(once) == once
