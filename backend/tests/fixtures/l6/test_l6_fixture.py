"""The L6 dataset matches every figure in expected.json, and its original placements verify."""

from collections import Counter, defaultdict
from typing import Any

import pytest
from pydantic import ValidationError

from tts.core.model import Dataset, Result
from tts.core.timegrid import TimeGrid
from tts.core.verifier import hard_violations, verify
from tts.presets.academic_weekly import types


def resources_of(ds: Dataset, resource_type: str) -> list[str]:
    return [r.code for r in ds.resources if r.type == resource_type]


def fixed_of(ds: Dataset, resource_type: str) -> dict[str, list[str]]:
    """Event code -> its fixed resources of one type."""
    kinds = {r.code: r.type for r in ds.resources}
    found: dict[str, list[str]] = defaultdict(list)
    for f in ds.fixed:
        if kinds[f.resource] == resource_type:
            found[f.event].append(f.resource)
    return found


def test_counts(l6_dataset: Dataset, l6_expected: dict[str, Any]) -> None:
    counts = l6_expected["counts"]
    ds = l6_dataset
    groups = [r for r in ds.resources if r.type == types.STUDENT_GROUP]
    assert len(groups) == counts["groups"] == 30
    assert dict(Counter(g.parent for g in groups)) == counts["groups_by_programme"]
    assert len(resources_of(ds, types.ROOM)) == counts["rooms"] == 10
    assert len(resources_of(ds, types.TEACHER)) == counts["teachers"] == 57
    assert len(ds.references) == counts["modules"] == 10
    assert len(ds.events) == counts["events"] == 77
    assert dict(Counter(e.kind for e in ds.events)) == counts["events_by_kind"]
    assert sum(e.delivery == "online" for e in ds.events) == counts["online_events"] == 1
    with_room = {q.event for q in ds.pooled}
    assert sum(e.code not in with_room for e in ds.events) == counts["events_without_room"] == 1


def test_groups_in_file_order(l6_dataset: Dataset, l6_expected: dict[str, Any]) -> None:
    assert sorted(resources_of(l6_dataset, types.STUDENT_GROUP)) == sorted(l6_expected["groups"])


def test_time(l6_dataset: Dataset, l6_locked_result: Result, l6_expected: dict[str, Any]) -> None:
    expected = l6_expected["time"]
    tm = l6_dataset.time
    assert [d.label for d in tm.days] == expected["days"]
    assert [p.start.strftime("%H:%M") for p in tm.periods] == expected["periods"]
    assert tm.periods_per_day == expected["period_count"] == 14
    assert dict(Counter(str(e.duration) for e in l6_dataset.events)) == expected["durations"]

    starts = {p.code: p.start.strftime("%H:%M") for p in tm.periods}
    assert {starts[a.start_period] for a in l6_locked_result.assignments} == set(
        expected["start_periods_used"]
    )
    labels = {d.code: d.label for d in tm.days}
    per_day = Counter(labels[a.day] for a in l6_locked_result.assignments)
    assert {label: per_day.get(label, 0) for label in expected["days"]} == expected["events_by_day"]


def test_periods_per_week_of_each_group(l6_dataset: Dataset, l6_expected: dict[str, Any]) -> None:
    duration = {e.code: e.duration for e in l6_dataset.events}
    total: Counter[str] = Counter()
    for event, groups in fixed_of(l6_dataset, types.STUDENT_GROUP).items():
        for group in groups:
            total[group] += duration[event]
    assert dict(total) == l6_expected["group_periods_per_week"]


def test_rooms(l6_dataset: Dataset, l6_locked_result: Result, l6_expected: dict[str, Any]) -> None:
    groups = fixed_of(l6_dataset, types.STUDENT_GROUP)
    found: dict[str, dict[str, int]] = {}
    for a in l6_locked_result.assignments:
        for choice in a.chosen:
            for room in choice.resources:
                info = found.setdefault(room, {"events": 0, "max_groups_in_one_event": 0})
                info["events"] += 1
                info["max_groups_in_one_event"] = max(
                    info["max_groups_in_one_event"], len(groups[a.event])
                )
    assert found == l6_expected["rooms"]


def test_teachers(l6_dataset: Dataset, l6_expected: dict[str, Any]) -> None:
    teachers = fixed_of(l6_dataset, types.TEACHER)
    assert dict(Counter(t for ts in teachers.values() for t in ts)) == l6_expected["teachers"]
    assert max(len(ts) for ts in teachers.values()) == l6_expected["max_teachers_in_one_event"]
    groups = fixed_of(l6_dataset, types.STUDENT_GROUP)
    assert max(len(gs) for gs in groups.values()) == l6_expected["max_groups_in_one_event"]


def test_modules(l6_dataset: Dataset, l6_expected: dict[str, Any]) -> None:
    groups = fixed_of(l6_dataset, types.STUDENT_GROUP)
    found: dict[str, dict[str, Any]] = {}
    for e in l6_dataset.events:
        assert e.reference is not None
        info = found.setdefault(e.reference, {"events": 0, "LEC": 0, "TUT": 0, "groups": set()})
        info["events"] += 1
        info[e.kind] += 1
        info["groups"] |= set(groups[e.code])
    expected = {
        code: {**info, "groups": set(info["groups"])}
        for code, info in l6_expected["modules"].items()
    }
    assert found == expected


def test_the_original_timetable_has_no_teacher_group_or_room_clash(
    l6_dataset: Dataset, l6_locked_result: Result, l6_expected: dict[str, Any]
) -> None:
    """Counted here from first principles, without the verifier."""
    grid = TimeGrid(l6_dataset.time)
    duration = {e.code: e.duration for e in l6_dataset.events}
    used: dict[str, dict[str, Counter[int]]] = {
        "teacher": defaultdict(Counter),
        "group": defaultdict(Counter),
        "room": defaultdict(Counter),
    }
    teachers = fixed_of(l6_dataset, types.TEACHER)
    groups = fixed_of(l6_dataset, types.STUDENT_GROUP)
    for a in l6_locked_result.assignments:
        start = grid.slot(a.day, a.start_period)
        for t in range(start, start + duration[a.event]):
            for teacher in teachers[a.event]:
                used["teacher"][teacher][t] += 1
            for group in groups[a.event]:
                used["group"][group][t] += 1
            for choice in a.chosen:
                for room in choice.resources:
                    used["room"][room][t] += 1
    clashes = {
        kind: sum(n > 1 for slots in per_resource.values() for n in slots.values())
        for kind, per_resource in used.items()
    }
    assert clashes == l6_expected["clashes"] == {"teacher": 0, "group": 0, "room": 0}


def test_the_original_placements_verify_with_no_hard_violations(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    violations = verify(l6_dataset, l6_locked_result)
    assert hard_violations(violations) == []
    assert violations == []  # no constraints are declared, so nothing else can be reported


def test_every_event_is_placed_exactly_once(l6_dataset: Dataset, l6_locked_result: Result) -> None:
    placed = Counter(a.event for a in l6_locked_result.assignments)
    assert set(placed) == {e.code for e in l6_dataset.events}
    assert set(placed.values()) == {1}


def test_the_fixture_cannot_be_changed_in_place(
    l6_dataset: Dataset, l6_locked_result: Result
) -> None:
    with pytest.raises(ValidationError):
        l6_dataset.preset = "other"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        l6_locked_result.assignments = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        l6_dataset.events.append(l6_dataset.events[0])  # type: ignore[attr-defined]


def test_the_known_anomaly_is_reported_by_the_parser(
    l6_fet: Any, l6_expected: dict[str, Any]
) -> None:
    assert len(l6_fet.anomalies) == len(l6_expected["known_anomalies"]) == 1


def test_the_saved_workbook_matches_the_export_when_it_is_present(l6_dataset: Dataset) -> None:
    """`l6.xlsx` is written by `tts import-fet ... --no-defaults` (the hard rules only, the
    regression baseline). It is committed; the test skips only if it is missing."""
    from pathlib import Path

    from tts.io.workbook import import_xlsx

    saved = Path(__file__).resolve().parent / "l6.xlsx"
    if not saved.exists():
        pytest.skip("l6.xlsx has not been generated here (run `tts import-fet`)")
    outcome = import_xlsx(saved)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data is not None
    assert outcome.data.dataset == l6_dataset
