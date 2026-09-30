"""Every declared constraint type, checked on events the solver created (ADR-0007, spec 04 s.5).

The verifier makes created events real first, so each type counts them like declared events. One
scenario per type: a demand of two participants, three sessions a week (`e1`, `e2`, `e3`, one
block), placed by hand, with the penalty the catalogue gives for that placement.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest
from constraint_helpers import penalty, rule

from fixtures import at, demand, make_dataset, pick, res, unavailable
from tts.core.constraints.registry import DECLARED
from tts.core.model import Availability, CreatedEvent, Result

Slot = tuple[str, str, str, str]  # day, period, room (by event code in `placements`)


@dataclass
class Case:
    type_name: str
    scope: str
    params: dict[str, Any]
    placements: dict[str, Slot]  # event -> (day, period, room)
    expected: int
    availability: list[Availability] = field(default_factory=list)


def place(e1: Slot, e2: Slot, e3: Slot) -> dict[str, Slot]:
    return {"e1": e1, "e2": e2, "e3": e3}


D1P1 = ("d1", "p1", "r1")
D1P2 = ("d1", "p2", "r1")
D1P3 = ("d1", "p3", "r1")
D1P4 = ("d1", "p4", "r1")
D2P1 = ("d2", "p1", "r1")

CASES = [
    Case("max_per_day", "code:g1", {"max": 1, "unit": "events"}, place(D1P1, D1P2, D2P1), 1),
    Case("max_gaps", "code:g1", {"max": 0, "per": "day"}, place(D1P1, D1P3, D2P1), 1),
    Case("max_days", "code:g1", {"max": 1}, place(D1P1, D1P2, D2P1), 1),
    Case("min_days_between", "kind:K", {"min": 1}, place(D1P1, D1P2, D2P1), 1),
    Case("same_start", "kind:K", {}, place(D1P1, D1P2, D1P2), 1),
    Case("same_day", "kind:K", {}, place(D1P1, D1P2, D2P1), 1),
    Case("order", "kind:K", {"sequence": ["e1", "e2"]}, place(D1P2, D1P1, D2P1), 1),
    Case("consecutive", "kind:K", {"sequence": ["e1", "e2"]}, place(D1P1, D1P3, D2P1), 1),
    Case("not_overlapping", "kind:K", {}, place(D1P1, D1P1, D2P1), 1),
    Case(
        "travel_gap",
        "code:g1",
        {"min_periods": 1, "level": "N"},
        place(D1P1, ("d1", "p2", "r2"), D2P1),
        1,
    ),
    Case("preferred_times", "kind:K", {"slots": ["d1:p1"]}, place(D1P1, D1P2, D2P1), 2),
    Case(
        "preferred_resources",
        "kind:K",
        {"filter": "code:r1"},
        place(D1P1, ("d1", "p2", "r2"), D2P1),
        1,
    ),
    Case("max_span", "code:g1", {"max": 2}, place(D1P1, D1P4, D2P1), 2),
    Case(
        "avoid",
        "code:g1",
        {},
        place(D1P1, D1P2, D2P1),
        1,
        availability=[unavailable("g1", "d1", "p1", status="avoid")],
    ),
]


def scenario(case: Case):  # type: ignore[no-untyped-def]
    ds = make_dataset(
        days=2,
        periods=4,
        resources=[
            res("g1", "G", capacity=10),
            res("g2", "G", capacity=10),
            res("b1", "N"),
            res("b2", "N"),
            res("r1", "R", parent="b1", capacity=40),
            res("r2", "R", parent="b2", capacity=40),
        ],
        demands=[demand(participants=("g1", "g2"), limit=2, repeat=3)],
        availability=case.availability,
        constraints=[rule(case.type_name, case.scope, **case.params)],
        validate=False,
    )
    result = Result(
        created=tuple(
            CreatedEvent(code=c, demand="d1", participants=("g1", "g2")) for c in case.placements
        ),
        assignments=tuple(
            at(code, day, period, pick(0, room))
            for code, (day, period, room) in case.placements.items()
        ),
    )
    return ds, result


def test_there_is_one_scenario_for_every_declared_type() -> None:
    assert sorted(c.type_name for c in CASES) == sorted(DECLARED)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.type_name)
def test_the_type_counts_created_events(case: Case) -> None:
    ds, result = scenario(case)
    assert penalty(ds, result) == case.expected


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.type_name)
def test_the_same_placement_of_declared_events_gives_the_same_penalty(case: Case) -> None:
    """Created events are not treated differently from declared ones."""
    from fixtures import ev, pool

    ds, result = scenario(case)
    declared = make_dataset(
        days=2,
        periods=4,
        resources=list(ds.resources),
        events=[ev(c) for c in case.placements],
        fixed=[(c, p) for c in case.placements for p in ("g1", "g2")],
        pooled=[pool(c) for c in case.placements],
        availability=ds.availability,
        constraints=list(ds.constraints),
        validate=False,
    )
    assert penalty(declared, Result(assignments=result.assignments)) == case.expected
