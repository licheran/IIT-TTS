import json
from collections import Counter
from datetime import time
from pathlib import Path

import pytest

from tts.core.model import Dataset, Result
from tts.io.fet_html import (
    Assumptions,
    FetConversionError,
    FetTimetable,
    parse_fet_groups_html,
    to_dataset,
)
from tts.presets.academic_weekly import PRESET_NAME, types

L6 = Path(__file__).resolve().parents[1] / "fixtures" / "l6"


@pytest.fixture(scope="module")
def fet() -> FetTimetable:
    return parse_fet_groups_html(L6 / "fet-groups-export.html")


@pytest.fixture(scope="module")
def converted(fet: FetTimetable) -> tuple[Dataset, Result]:
    return to_dataset(fet)


@pytest.fixture(scope="module")
def expected() -> dict[str, object]:
    return json.loads((L6 / "expected.json").read_text("utf-8"))  # type: ignore[no-any-return]


def by_type(ds: Dataset, resource_type: str) -> dict[str, object]:
    return {r.code: r for r in ds.resources if r.type == resource_type}


def test_the_dataset_is_sound_and_uses_the_academic_preset(
    converted: tuple[Dataset, Result],
) -> None:
    ds, _ = converted
    assert ds.preset == PRESET_NAME
    assert ds.validate_invariants() == []
    assert ds.resource_types == tuple(sorted(types.RESOURCE_TYPES, key=lambda t: t.code))


def test_level_programmes_and_groups_form_a_hierarchy(converted: tuple[Dataset, Result]) -> None:
    ds, _ = converted
    resources = {r.code: r for r in ds.resources}
    assert set(by_type(ds, types.LEVEL)) == {"L6"}
    assert set(by_type(ds, types.PROGRAMME)) == {"L6 SE", "L6 CS"}
    assert resources["L6 SE"].parent == "L6"
    groups = [r for r in ds.resources if r.type == types.STUDENT_GROUP]
    assert len(groups) == 30
    assert all(g.capacity == 30 for g in groups)
    assert resources["L6 SE / G1"].parent == "L6 SE"
    assert resources["L6 CS / G19"].parent == "L6 CS"
    assert Counter(g.parent for g in groups) == {"L6 SE": 11, "L6 CS": 19}


def test_rooms_sit_in_one_building_of_one_campus_with_assumed_capacity(
    converted: tuple[Dataset, Result], expected: dict[str, object]
) -> None:
    ds, _ = converted
    resources = {r.code: r for r in ds.resources}
    assert set(by_type(ds, types.CAMPUS)) == {"MAIN"}
    assert set(by_type(ds, types.BUILDING)) == {"GP"}
    assert resources["GP"].parent == "MAIN"
    rooms = [r for r in ds.resources if r.type == types.ROOM]
    assert len(rooms) == 10
    assert all(r.parent == "GP" for r in rooms)
    for room in rooms:
        most = expected["rooms"][room.code]["max_groups_in_one_event"]  # type: ignore[index]
        if room.code == "Auditorium":
            assert (room.capacity, room.tag("room_type")) == (250, "auditorium")
        else:
            assert (room.capacity, room.tag("room_type")) == (30 * most, "lab")
    assert resources["[2LA] -GP"].capacity == 90


def test_teachers_and_modules(converted: tuple[Dataset, Result]) -> None:
    ds, _ = converted
    assert len(by_type(ds, types.TEACHER)) == 57
    assert {r.code for r in ds.references} == {
        "6BUIS019C",
        "6CCGD007C",
        "6COSC020C",
        "6COSC021C",
        "6COSC023C",
        "6ELEN018C",
        "6MMCS009C",
        "6SENG005C",
        "6SENG006C",
        "6SENG010W",
    }
    assert all(r.type == types.MODULE for r in ds.references)


def test_time_model(converted: tuple[Dataset, Result], expected: dict[str, object]) -> None:
    ds, _ = converted
    tm = ds.time
    assert [d.code for d in tm.days] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    assert [d.label for d in tm.days] == expected["time"]["days"]  # type: ignore[index]
    assert [p.code for p in tm.periods] == [f"P{i:02d}" for i in range(1, 15)]
    assert (tm.periods[0].start, tm.periods[0].end) == (time(8, 30), time(9, 30))
    assert (tm.periods[-1].start, tm.periods[-1].end) == (time(21, 30), time(22, 30))
    assert [p.code for p in tm.periods if p.is_break] == ["P05"]
    assert tm.periods[4].start == time(12, 30)
    (pattern,) = tm.start_patterns
    assert (pattern.code, pattern.duration) == ("2H", 2)
    assert pattern.start_periods == ("P01", "P03", "P06", "P08", "P10")
    assert pattern.days is None


def test_the_start_pattern_covers_exactly_the_starts_used_in_the_export(
    converted: tuple[Dataset, Result], expected: dict[str, object]
) -> None:
    ds, result = converted
    periods = {p.code: p.start.strftime("%H:%M") for p in ds.time.periods}
    (pattern,) = ds.time.start_patterns
    assert {periods[c] for c in pattern.start_periods} == set(
        expected["time"]["start_periods_used"]  # type: ignore[index]
    )
    assert {periods[a.start_period] for a in result.assignments} == {
        periods[c] for c in pattern.start_periods
    }


def test_events(converted: tuple[Dataset, Result], expected: dict[str, object]) -> None:
    ds, _ = converted
    assert len(ds.events) == 77
    assert Counter(e.kind for e in ds.events) == expected["counts"]["events_by_kind"]  # type: ignore[index]
    assert {e.duration for e in ds.events} == {2}
    assert {e.start_pattern for e in ds.events} == {"2H"}
    assert Counter(e.delivery for e in ds.events) == {"in_person": 76, "online": 1}
    assert all(e.reference is not None for e in ds.events)


def test_event_codes_are_module_kind_number_and_unique(converted: tuple[Dataset, Result]) -> None:
    ds, _ = converted
    codes = [e.code for e in ds.events]
    assert len(set(codes)) == 77
    assert "6SENG005C-LEC-01" in codes
    assert "6SENG005C-TUT-11" in codes
    for e in ds.events:
        assert e.code.startswith(f"{e.reference}-{e.kind}-")
    per_kind = Counter((e.reference, e.kind) for e in ds.events)
    for (module, kind), count in per_kind.items():
        assert {c for c in codes if c.startswith(f"{module}-{kind}-")} == {
            f"{module}-{kind}-{n:02d}" for n in range(1, count + 1)
        }


def test_groups_and_teachers_are_fixed_and_a_room_is_pooled(
    converted: tuple[Dataset, Result],
) -> None:
    ds, _ = converted
    resources = {r.code: r for r in ds.resources}
    fixed_types = Counter(resources[f.resource].type for f in ds.fixed)
    assert set(fixed_types) == {types.STUDENT_GROUP, types.TEACHER}
    assert len(ds.pooled) == 76  # every event but the online one
    online = {e.code for e in ds.events if e.delivery == "online"}
    assert {q.event for q in ds.pooled}.isdisjoint(online)
    for q in ds.pooled:
        assert q.resource_type == types.ROOM
        assert (q.ordinal, q.count) == (0, 1)
        assert q.filter in {"tag:room_type=lab", "tag:room_type=auditorium"}
        assert str(q.capacity_rule) == "sum_of_fixed:StudentGroup"


def test_the_result_holds_the_original_placements(converted: tuple[Dataset, Result]) -> None:
    ds, result = converted
    assert len(result.assignments) == 77
    assert {a.event for a in result.assignments} == {e.code for e in ds.events}
    pooled_events = {q.event for q in ds.pooled}
    for a in result.assignments:
        assert (len(a.chosen) == 1) == (a.event in pooled_events)
    first = next(a for a in result.assignments if a.event == "6SENG010W-LEC-01")
    assert (first.day, first.start_period) == ("Tue", "P01")
    assert first.chosen[0].resources == ("Auditorium",)


def test_the_online_session_keeps_its_label_as_a_note(converted: tuple[Dataset, Result]) -> None:
    ds, _ = converted
    (online,) = [e for e in ds.events if e.delivery == "online"]
    assert online.reference == "6CCGD007C"
    assert dict(online.tags) == {"fet_label": "6.00pm -8.00pm"}


def test_conversion_is_deterministic(fet: FetTimetable) -> None:
    first, second = to_dataset(fet), to_dataset(fet)
    assert first == second
    assert first[0].model_dump_json() == second[0].model_dump_json()


# --- Assumptions ------------------------------------------------------------------------------


def test_assumptions_can_be_replaced(fet: FetTimetable) -> None:
    ds, _ = to_dataset(fet, assumptions=Assumptions(group_size=25, auditorium_capacity=300))
    resources = {r.code: r for r in ds.resources}
    assert resources["L6 SE / G1"].capacity == 25
    assert resources["Auditorium"].capacity == 300
    assert resources["[2LA] -GP"].capacity == 75


def test_assumptions_are_described_for_the_workbook_metadata() -> None:
    text = Assumptions().describe()
    for fragment in ("Group size: 30", "250", "auditorium", "12:30", "08:30, 10:30, 13:30"):
        assert fragment in text


def test_a_start_time_that_is_not_a_period_is_an_error(fet: FetTimetable) -> None:
    with pytest.raises(FetConversionError, match=r"start times \['09:00'\]"):
        to_dataset(fet, assumptions=Assumptions(start_times=("09:00",)))


def test_an_unsupported_preset_is_an_error(fet: FetTimetable) -> None:
    with pytest.raises(FetConversionError, match='unsupported preset "exams"'):
        to_dataset(fet, preset="exams")


def test_a_group_name_without_a_programme_is_an_error(fet: FetTimetable) -> None:
    broken = FetTimetable(
        institution=fet.institution,
        days=fet.days,
        periods=fet.periods,
        groups=("G1",),
        sessions=(),
        anomalies=(),
    )
    with pytest.raises(FetConversionError, match="<programme> / <group>"):
        to_dataset(broken)
