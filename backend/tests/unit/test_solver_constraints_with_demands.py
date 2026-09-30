"""Every declared type compiled over sessions the solver creates (ADR-0007, spec 04 section 5).

Four groups are split into two blocks (limit 2), each block meeting twice a week, so the solver
creates four sessions and decides who is in which block. For each type the solver's own penalty
term must equal the verifier's penalty for the timetable it found.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest
from constraint_helpers import penalty, rule, solve_and_compare

from fixtures import demand, make_dataset, res, unavailable
from tts.core.constraints.registry import DECLARED
from tts.core.model import Availability, Dataset


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
    Case("max_per_day", "type:G", {"max": 1, "unit": "events"}, 1, 4, 4),
    Case("max_gaps", "type:G", {"max": 0, "per": "day"}, 1, 4, 0),
    Case("max_days", "type:G", {"max": 1}, 2, 4, 0),
    Case("max_span", "type:G", {"max": 2}, 1, 4, 0),
    Case(
        "avoid",
        "type:G",
        {},
        1,
        4,
        0,
        [
            unavailable("g1", "d1", "p1", status="avoid"),
            unavailable("g3", "d1", "p2", status="avoid"),
        ],
    ),
    Case("travel_gap", "type:G", {"min_periods": 1, "level": "N"}, 1, 4, 0),
    Case("min_days_between", "kind:K", {"min": 1}, 1, 4, 6),
    Case("same_start", "kind:K", {}, 2, 4, 2),  # a block's two sessions cannot coincide
    Case("same_day", "kind:K", {}, 2, 4, 0),
    Case("not_overlapping", "kind:K", {}, 1, 4, 0),
    Case("preferred_times", "kind:K", {"slots": ["d1:p1"]}, 1, 4, 2),
    Case("preferred_resources", "kind:K", {"filter": "code:r1"}, 1, 4, 0),
]

# `order` and `consecutive` name events by code in their parameters, and the codes of sessions the
# solver creates do not exist before solving, so they apply to declared events only.
NAMES_EVENTS = {"order", "consecutive"}


def scenario(case: Case, hard: bool = False) -> Dataset:
    groups = [res(f"g{i}", "G", capacity=10) for i in (1, 2, 3, 4)]
    return make_dataset(
        days=case.days,
        periods=case.periods,
        resources=[
            *groups,
            res("b1", "N"),
            res("b2", "N"),
            res("r1", "R", parent="b1", capacity=20),
            res("r2", "R", parent="b2", capacity=20),
        ],
        demands=[demand(participants=[g.code for g in groups], limit=2, repeat=2)],
        availability=case.availability,
        constraints=[rule(case.type_name, case.scope, hard=hard, **case.params)],
        validate=False,
    )


def test_every_type_is_covered_or_names_events() -> None:
    assert {c.type_name for c in CASES} | NAMES_EVENTS == set(DECLARED)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.type_name)
def test_the_solver_and_the_verifier_agree_on_created_sessions(case: Case) -> None:
    outcome, found = solve_and_compare(scenario(case))
    assert found == case.expected
    assert outcome.result is not None
    assert len(outcome.result.created) == 4


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.type_name)
def test_the_verifier_counts_the_same_on_the_result(case: Case) -> None:
    ds = scenario(case)
    outcome, _ = solve_and_compare(ds)
    assert outcome.result is not None
    assert penalty(ds, outcome.result) == case.expected
