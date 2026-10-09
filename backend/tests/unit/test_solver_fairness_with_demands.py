"""The workload rules, and the resource-scoped types, over teachers the solver chooses (P25.5).

Four groups are split into two blocks (limit 2), each block meeting twice a week, so the solver
creates four sessions, decides who is in which block and which of two teachers takes each. For
every rule the solver's own penalty term must equal the verifier's penalty for the timetable it
found, and that penalty must be the optimum.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest
from constraint_helpers import penalty, rule, solve_and_compare

from fixtures import demand, make_dataset, res, unavailable
from tts.core.model import Availability, CapacityRule, Dataset, PooledSpec


@dataclass
class Case:
    type_name: str
    scope: str
    params: dict[str, Any]
    days: int
    periods: int
    expected: int  # the optimum penalty
    availability: list[Availability] = field(default_factory=list)


CASES = [
    # four sessions over two teachers: two each is the best split
    Case("max_load", "type:T", {"max": 2, "unit": "events"}, 2, 4, 0),
    Case("max_load", "type:T", {"max": 1, "unit": "events"}, 2, 4, 2),
    Case("max_load", "code:t1", {"max": 1, "unit": "periods"}, 2, 4, 0),
    Case("balance_load", "type:T", {"unit": "events"}, 2, 4, 0),
    Case("balance_load", "type:T", {"unit": "periods"}, 2, 4, 0),
    # a block's two sessions can have one teacher, so every group keeps its teacher
    Case("same_resource", "kind:K", {"type": "T", "per": "G"}, 2, 4, 0),
    # the resource-scoped types over teachers who may be chosen
    Case("max_per_day", "type:T", {"max": 1, "unit": "events"}, 2, 4, 0),
    Case("max_gaps", "type:T", {"max": 0, "per": "day"}, 2, 4, 0),
    Case("max_days", "type:T", {"max": 1}, 2, 4, 0),
    Case("max_span", "type:T", {"max": 2}, 2, 4, 0),
    Case("avoid", "type:T", {}, 1, 4, 0, [unavailable("t1", "d1", "p1", status="avoid")]),
]


def scenario(case: Case, hard: bool = False) -> Dataset:
    groups = [res(f"g{i}", "G", capacity=10) for i in (1, 2, 3, 4)]
    pooled = (
        PooledSpec(
            resource_type="R", ordinal=0, capacity_rule=CapacityRule.parse("sum_of_fixed:G")
        ),
        PooledSpec(resource_type="T", ordinal=1, filter="code:t1,t2"),
    )
    return make_dataset(
        days=case.days,
        periods=case.periods,
        resources=[
            *groups,
            res("t1", "T"),
            res("t2", "T"),
            res("r1", "R", capacity=20),
            res("r2", "R", capacity=20),
        ],
        demands=[demand(participants=[g.code for g in groups], limit=2, repeat=2, pooled=pooled)],
        availability=case.availability,
        constraints=[rule(case.type_name, case.scope, hard=hard, **case.params)],
        validate=False,
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.type_name}-{c.scope}-{c.expected}")
def test_the_solver_and_the_verifier_agree_on_chosen_teachers(case: Case) -> None:
    ds = scenario(case)
    outcome, found = solve_and_compare(ds)
    assert found == case.expected
    assert outcome.result is not None
    assert len(outcome.result.created) == 4
    assert penalty(ds, outcome.result) == case.expected


def test_a_weekly_cap_is_never_exceeded_when_it_is_hard() -> None:
    case = Case("max_load", "type:T", {"max": 2, "unit": "events"}, 2, 4, 0)
    outcome, found = solve_and_compare(scenario(case, hard=True))
    assert found == 0
    assert outcome.result is not None
    teachers = [
        r
        for a in outcome.result.assignments
        for choice in a.chosen
        if choice.ordinal == 1
        for r in choice.resources
    ]
    assert len(teachers) == 4
    assert teachers.count("t1") <= 2 and teachers.count("t2") <= 2
