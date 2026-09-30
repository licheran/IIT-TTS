"""P5.4: the real L6 dataset, broken on purpose. Each variant must fail fast, naming the culprits.

Each variant is a copy of the session's L6 dataset; the fixture itself is never changed.
"""

import time

from tts.core.model import Availability, Constraint, Dataset, Pin, Result
from tts.preflight.checks import Issue, has_errors, run_preflight
from tts.presets import labeller
from tts.solver.explain import explain

LIMIT_S = 60.0  # phase 5 acceptance: no variant runs longer than this
label = labeller("academic_weekly")


def errors_of(issues: list[Issue], kind: str) -> list[Issue]:
    return [i for i in issues if i.severity == "error" and i.kind == kind]


def test_without_the_auditorium_its_events_have_no_candidate_room(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    started = time.perf_counter()
    broken = l6_dataset.model_copy(
        update={"resources": tuple(r for r in l6_dataset.resources if r.code != "Auditorium")}
    )
    issues = run_preflight(broken, label)

    in_auditorium = {
        a.event
        for a in l6_locked_result.assignments
        for c in a.chosen
        if "Auditorium" in c.resources
    }
    assert in_auditorium  # the premise: some events used it
    found = errors_of(issues, "no_candidate")
    assert {i.refs[0].code for i in found} == in_auditorium
    for issue in found:
        assert issue.message.startswith(
            f'{issue.refs[0].code}: no Room matching "tag:room_type=auditorium"'
        )
    assert time.perf_counter() - started < LIMIT_S


def hawe_away_tuesday_to_saturday(ds: Dataset) -> Dataset:
    days = [d.code for d in ds.time.days if d.code != "Mon"]
    rows = [
        Availability(resource="HAWE", day=day, period=p.code, status="unavailable")
        for day in days
        for p in ds.time.periods
    ]
    return ds.model_copy(update={"availability": (*ds.availability, *rows)})


def test_a_teacher_away_all_week_but_monday_is_over_demanded(l6_dataset: Dataset) -> None:
    started = time.perf_counter()
    broken = hawe_away_tuesday_to_saturday(l6_dataset)
    issues = run_preflight(broken, label)
    assert has_errors(issues)
    assert [i.message for i in errors_of(issues, "over_demand")] == [
        "Teacher HAWE: needs 16 periods, 13 available"
    ]
    assert time.perf_counter() - started < LIMIT_S


def test_the_explanation_of_the_absent_teacher_names_the_absence_and_the_load(
    l6_dataset: Dataset,
) -> None:
    started = time.perf_counter()
    diagnostic = explain(hawe_away_tuesday_to_saturday(l6_dataset), label)
    elapsed = time.perf_counter() - started

    assert diagnostic is not None and diagnostic.kind == "infeasible_core"
    assert diagnostic.message.startswith("Conflicting rules: Teacher HAWE unavailable ")
    assert "8 events of 2 periods for HAWE; no_overlap(HAWE)" in diagnostic.message
    assert {r.code for r in diagnostic.refs} == {"HAWE"}  # nothing else is to blame
    assert diagnostic.minimal
    assert elapsed < LIMIT_S


def two_pins_on_one_room(ds: Dataset, placements: Result) -> tuple[Dataset, str, str, str]:
    """Pin two events that used the same room at different times onto one of those times."""
    by_room: dict[str, list[tuple[str, str, str]]] = {}
    for a in placements.assignments:
        for choice in a.chosen:
            for room in choice.resources:
                by_room.setdefault(room, []).append((a.event, a.day, a.start_period))
    room, uses = next((r, u) for r, u in sorted(by_room.items()) if len(u) >= 2)
    (first, day, period), (second, _, _) = uses[0], uses[1]
    pins = (
        Pin(event=first, day=day, start_period=period, resources=(room,)),
        Pin(event=second, day=day, start_period=period, resources=(room,)),
    )
    return ds.model_copy(update={"pins": pins}), room, first, second


def test_two_pins_on_one_room_and_slot_are_refused_before_solving(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    started = time.perf_counter()
    broken, room, first, second = two_pins_on_one_room(l6_dataset, l6_locked_result)
    found = errors_of(run_preflight(broken, label), "conflicting_pins")
    assert found
    clash = next(i for i in found if i.refs[0].code == room)
    assert clash.message.startswith(f"Pins: 2 activities pinned to {room} on ")
    assert {r.code for r in clash.refs if r.kind == "event"} == {first, second}
    assert time.perf_counter() - started < LIMIT_S


def test_the_explanation_of_the_two_pins_names_both_and_the_room(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    started = time.perf_counter()
    broken, room, first, second = two_pins_on_one_room(l6_dataset, l6_locked_result)
    diagnostic = explain(broken, label)
    assert diagnostic is not None
    refs = {(r.kind, r.code) for r in diagnostic.refs}
    assert ("event", first) in refs and ("event", second) in refs
    assert f"no_overlap({room})" in diagnostic.message
    assert time.perf_counter() - started < LIMIT_S


def test_a_hard_max_days_of_one_for_a_group_is_named_in_the_explanation(
    l6_dataset: Dataset,
) -> None:
    started = time.perf_counter()
    rule = Constraint(
        code="C-MAXDAYS", type="max_days", scope='code:"L6 SE / G1"', params={"max": 1}
    )
    broken = l6_dataset.model_copy(update={"constraints": (*l6_dataset.constraints, rule)})
    diagnostic = explain(broken, label)
    assert diagnostic is not None
    assert "constraint C-MAXDAYS (max_days)" in diagnostic.details
    assert time.perf_counter() - started < LIMIT_S
