from datetime import datetime, time

import pytest
from workbooks import (
    add_column,
    base_sheets,
    drop_column,
    edited,
    load,
    messages,
    set_cell,
    to_raw,
)

from tts.core.model import CapacityRule
from tts.io.importer import import_raw

# --- A valid workbook ---------------------------------------------------------------------------


def test_the_base_workbook_imports_cleanly() -> None:
    outcome = load(base_sheets())
    assert messages(outcome) == []
    assert outcome.ok
    assert outcome.data is not None
    assert outcome.data.dataset.validate_invariants() == []
    assert outcome.data.dataset.preset == "academic_weekly"
    assert outcome.data.meta == {"institution": "Test Institute"}
    assert outcome.summary["Groups"] == 2
    assert outcome.summary["Activities"] == 2


def test_resources_take_their_type_from_the_sheet_and_their_fields_from_the_columns() -> None:
    ds = load(base_sheets()).data.dataset  # type: ignore[union-attr]
    by_code = {r.code: r for r in ds.resources}
    assert (by_code["G1"].type, by_code["G1"].parent, by_code["G1"].capacity) == (
        "StudentGroup",
        "PR1",
        30,
    )
    assert by_code["G1"].name == "Group 1"
    assert by_code["G2"].name == ""
    assert dict(by_code["G2"].tags) == {"batch": "b"}
    assert (by_code["R1"].type, by_code["R1"].parent, by_code["R1"].capacity) == ("Room", "B1", 60)
    assert dict(by_code["R1"].tags) == {"room_type": "lab"}
    assert dict(by_code["R2"].tags) == {"floor": "2", "room_type": "hall"}
    assert by_code["B1"].attribute("abbreviation") == "BLD"
    assert by_code["T1"].type == "Teacher"


def test_modules_become_references_with_attributes() -> None:
    ds = load(base_sheets()).data.dataset  # type: ignore[union-attr]
    (module,) = ds.references
    assert (module.code, module.type, module.name) == ("M1", "Module", "Module 1")
    assert dict(module.attributes) == {"programme": "PR1"}


def test_time_model() -> None:
    tm = load(base_sheets()).data.dataset.time  # type: ignore[union-attr]
    assert [(d.code, d.label, d.order) for d in tm.days] == [
        ("Mon", "Monday", 1),
        ("Tue", "Tuesday", 2),
    ]
    assert [(p.code, p.is_break) for p in tm.periods] == [
        ("P1", False),
        ("P2", False),
        ("P3", True),
        ("P4", False),
    ]
    assert tm.periods[0].start == time(8, 0)
    assert tm.periods[3].end == time(12, 0)
    two_hour = next(s for s in tm.start_patterns if s.code == "2H")
    assert (two_hour.duration, two_hour.start_periods, two_hour.days) == (2, ("P1", "P2"), None)


def test_activities_become_events_with_fixed_and_pooled_requirements() -> None:
    ds = load(base_sheets()).data.dataset  # type: ignore[union-attr]
    events = {e.code: e for e in ds.events}
    assert (events["A1"].kind, events["A1"].duration, events["A1"].reference) == ("LEC", 2, "M1")
    assert events["A1"].delivery == "in_person"  # the default
    assert events["A2"].delivery == "online"
    assert dict(events["A2"].tags) == {"note": "hi"}
    assert sorted((f.event, f.resource) for f in ds.fixed) == [
        ("A1", "G1"),
        ("A1", "G2"),
        ("A1", "T1"),
        ("A2", "G1"),
    ]
    (room,) = ds.pooled
    assert (room.event, room.resource_type, room.ordinal, room.count) == ("A1", "Room", 0, 1)
    assert room.filter == "tag:room_type=lab"
    assert room.capacity_rule == CapacityRule.parse("sum_of_fixed:StudentGroup")


def test_availability_star_expands_to_every_period() -> None:
    ds = load(base_sheets()).data.dataset  # type: ignore[union-attr]
    rows = [(a.resource, a.day, a.period, a.status) for a in ds.availability]
    assert rows == [
        ("R1", "Tue", "P1", "avoid"),
        ("T1", "Mon", "P1", "unavailable"),
        ("T1", "Mon", "P2", "unavailable"),
        ("T1", "Mon", "P3", "unavailable"),
        ("T1", "Mon", "P4", "unavailable"),
    ]


def test_constraints_and_pins() -> None:
    ds = load(base_sheets()).data.dataset  # type: ignore[union-attr]
    (constraint,) = ds.constraints
    assert (constraint.code, constraint.type, constraint.scope) == (
        "C1",
        "max_gaps",
        "type:StudentGroup",
    )
    assert constraint.params == {"max": 2, "per": "day"}
    assert (constraint.hard, constraint.weight, constraint.active) == (False, 5, True)
    (pin,) = ds.pins
    assert (pin.event, pin.day, pin.start_period, pin.resources, pin.source) == (
        "A1",
        "Mon",
        "P1",
        ("R1",),
        "user",
    )


def test_defaults_apply_when_columns_or_cells_are_blank() -> None:
    sheets = edited(
        Constraints=[["code", "type", "scope"], ["C1", "max_days", "type:Teacher"]],
        Pins=[["activity"], ["A1"]],
    )
    ds = load(sheets).data.dataset  # type: ignore[union-attr]
    (constraint,) = ds.constraints
    assert (constraint.hard, constraint.weight, constraint.active, constraint.params) == (
        True,
        1,
        True,
        {},
    )
    (pin,) = ds.pins
    assert (pin.day, pin.start_period, pin.resources, pin.source) == (None, None, (), "user")
    periods = ds.time.periods
    assert not any(p.is_break for p in periods if p.code != "P3")


def test_column_order_is_free_on_import() -> None:
    sheets = base_sheets()
    rows = sheets["Rooms"]
    sheets["Rooms"] = [list(reversed(r)) for r in rows]
    assert load(sheets).data == load(base_sheets()).data


def test_optional_sheets_may_be_missing() -> None:
    sheets = edited(Availability=None, Constraints=None, Pins=None, Buildings=None)
    sheets["Rooms"] = [["code", "room_type"], ["R1", "lab"]]
    outcome = load(sheets)
    assert messages(outcome) == []
    assert outcome.data.dataset.availability == ()  # type: ignore[union-attr]


def test_extra_columns_starting_with_x_are_notes() -> None:
    sheets = add_column(base_sheets(), "Teachers", "x_comment", ["hello"])
    sheets = add_column(sheets, "Activities", "x_owner", ["ann", None])
    outcome = load(sheets)
    assert messages(outcome) == []
    notes = outcome.data.notes  # type: ignore[union-attr]
    assert notes == {
        ("Teachers", "T1"): {"x_comment": "hello"},
        ("Activities", "A1"): {"x_owner": "ann"},
    }


def test_the_engine_ignores_notes() -> None:
    plain = load(base_sheets()).data.dataset  # type: ignore[union-attr]
    noted = load(add_column(base_sheets(), "Teachers", "x_comment", ["hello"])).data.dataset  # type: ignore[union-attr]
    assert plain == noted


def test_join_sheets_add_to_the_convenience_lists_without_duplicates() -> None:
    sheets = edited(
        ActivityGroups=[["activity", "group"], ["A1", "G1"], ["A2", "G2"], ["A2", "G2"]],
        ActivityTeachers=[["activity", "teacher"], ["A2", "T1"]],
    )
    ds = load(sheets).data.dataset  # type: ignore[union-attr]
    assert sorted((f.event, f.resource) for f in ds.fixed) == [
        ("A1", "G1"),
        ("A1", "G2"),
        ("A1", "T1"),
        ("A2", "G1"),
        ("A2", "G2"),
        ("A2", "T1"),
    ]


def test_activity_groups_may_name_a_programme_or_level() -> None:
    sheets = edited(
        Levels=[["code"], ["L1"]],
        ActivityGroups=[["activity", "group"], ["A2", "PR1"], ["A2", "L1"]],
    )
    ds = load(sheets).data.dataset  # type: ignore[union-attr]
    assert {(f.event, f.resource) for f in ds.fixed if f.event == "A2"} == {
        ("A2", "G1"),
        ("A2", "PR1"),
        ("A2", "L1"),
    }


# --- Typed cells as spreadsheets store them ------------------------------------------------------


def test_native_spreadsheet_types_are_accepted() -> None:
    sheets = base_sheets()
    sheets = set_cell(sheets, "Groups", 2, "size", 30.0)  # a number stored as a float
    sheets = set_cell(sheets, "Periods", 2, "start", time(8, 0))
    sheets = set_cell(sheets, "Periods", 2, "end", datetime(1900, 1, 1, 9, 0))
    sheets = set_cell(sheets, "Periods", 3, "start", 0.375)  # 09:00 as a day fraction
    sheets = set_cell(sheets, "Periods", 4, "is_break", "TRUE")
    sheets = set_cell(sheets, "Periods", 5, "is_break", 0)
    sheets = set_cell(sheets, "Teachers", 2, "code", 101)  # a numeric code
    sheets = set_cell(sheets, "Activities", 2, "teachers", "101")
    sheets = set_cell(sheets, "Availability", 2, "resource", 101)
    outcome = load(sheets)
    assert messages(outcome) == []
    ds = outcome.data.dataset  # type: ignore[union-attr]
    by_code = {r.code: r for r in ds.resources}
    assert by_code["G1"].capacity == 30
    assert "101" in by_code
    p1, p2, p3, p4 = ds.time.periods
    assert (p1.start, p1.end) == (time(8, 0), time(9, 0))
    assert p2.start == time(9, 0)
    assert (p3.is_break, p4.is_break) == (True, False)


def test_text_is_trimmed_and_blank_rows_are_not_data() -> None:
    sheets = set_cell(base_sheets(), "Teachers", 2, "code", "  T1  ")
    sheets = set_cell(sheets, "Activities", 2, "teachers", " T1 ; ")
    outcome = load(sheets)
    assert messages(outcome) == []
    assert "T1" in {r.code for r in outcome.data.dataset.resources}  # type: ignore[union-attr]


# --- Errors, one rule at a time ------------------------------------------------------------------


def test_a_missing_required_column() -> None:
    sheets = drop_column(base_sheets(), "Rooms", "room_type")
    assert "Rooms!R1 [room_type]: missing column" in messages(load(sheets))


def test_a_blank_required_value() -> None:
    sheets = set_cell(base_sheets(), "Activities", 2, "kind", None)
    assert messages(load(sheets)) == ["Activities!R2C3 [kind]: required"]


def test_a_duplicate_code_names_the_first_row() -> None:
    sheets = edited(Teachers=[["code", "name"], ["T1", "a"], ["T2", "b"], ["T1", "c"]])
    assert messages(load(sheets)) == ['Teachers!R4C1 [code]: duplicate "T1" (first at R2)']


def test_resource_codes_are_unique_across_sheets() -> None:
    sheets = edited(Teachers=[["code", "name"], ["T1", "one"], ["G1", "clash"]])
    assert messages(load(sheets)) == ['Teachers!R3C1 [code]: duplicate "G1" (first at Groups!R2)']


def test_an_unknown_reference() -> None:
    sheets = set_cell(base_sheets(), "Activities", 2, "teachers", "T1;HAWEE")
    assert messages(load(sheets)) == ['Activities!R2C11 [teachers]: unknown code "HAWEE"']


def test_an_unknown_reference_in_a_join_sheet() -> None:
    sheets = edited(ActivityTeachers=[["activity", "teacher"], ["A1", "T1"], ["A1", "HAWEE"]])
    assert messages(load(sheets)) == ['ActivityTeachers!R3C2 [teacher]: unknown code "HAWEE"']


def test_a_reference_must_name_a_code_from_the_right_sheet() -> None:
    sheets = set_cell(base_sheets(), "Rooms", 2, "building", "T1")  # a teacher, not a building
    assert messages(load(sheets)) == ['Rooms!R2C3 [building]: unknown code "T1"']


@pytest.mark.parametrize(
    ("sheet", "row", "column", "value", "message"),
    [
        ("Rooms", 3, "capacity", "thirty", 'expected integer ≥ 0, got "thirty"'),
        ("Rooms", 3, "capacity", -1, 'expected integer ≥ 0, got "-1"'),
        ("Rooms", 3, "capacity", 2.5, 'expected integer ≥ 0, got "2.5"'),
        ("Activities", 2, "duration", 0, 'expected integer ≥ 1, got "0"'),
        ("Days", 2, "order", "first", 'expected integer, got "first"'),
        ("Periods", 2, "is_break", "maybe", 'expected true or false, got "maybe"'),
        ("Periods", 2, "start", "8h30", 'expected HH:MM, got "8h30"'),
        ("Periods", 2, "start", "25:00", 'expected HH:MM, got "25:00"'),
        ("Constraints", 2, "params", "{bad", "expected a JSON object, got invalid JSON"),
        ("Constraints", 2, "params", "[1, 2]", "expected a JSON object"),
        ("Constraints", 2, "hard", "sometimes", 'expected true or false, got "sometimes"'),
        ("Groups", 3, "tags", "novalue", "expected key=value pairs"),
        ("Groups", 3, "tags", "a=1;a=2", 'duplicate key "a"'),
        ("Pins", 2, "source", "robot", "expected one of user, lock"),
        ("Availability", 3, "status", "busy", "expected one of unavailable, avoid"),
    ],
)
def test_a_badly_typed_cell(sheet: str, row: int, column: str, value: object, message: str) -> None:
    found = messages(load(set_cell(base_sheets(), sheet, row, column, value)))
    position = f"{sheet}!R{row}C{base_sheets()[sheet][0].index(column) + 1} [{column}]: "
    assert any(m.startswith(position + message) for m in found), found


def test_a_bad_selector_names_the_clause() -> None:
    sheets = set_cell(base_sheets(), "Constraints", 2, "scope", "teacher:x")
    assert messages(load(sheets)) == ['Constraints!R2C3 [scope]: unknown clause "teacher:"']


def test_a_scope_must_select_the_kind_of_target_of_its_type() -> None:
    sheets = set_cell(base_sheets(), "Constraints", 2, "scope", "kind:LEC")
    assert messages(load(sheets)) == [
        'Constraints!R2C3 [scope]: clause "kind:" does not select resources'
    ]
    sheets = set_cell(base_sheets(), "Constraints", 2, "type", "same_day")
    sheets = set_cell(sheets, "Constraints", 2, "scope", "type:Teacher")
    assert messages(load(sheets)) == [
        'Constraints!R2C3 [scope]: clause "type:" does not select events'
    ]


def test_an_unknown_constraint_type() -> None:
    sheets = set_cell(base_sheets(), "Constraints", 2, "type", "max_gap")
    assert messages(load(sheets)) == ['Constraints!R2C2 [type]: "max_gap" is not in the catalogue']


def test_a_hierarchy_cycle_is_reported_at_the_parent_cell() -> None:
    sheets = edited(
        Groups=[
            ["code", "parent", "size"],
            ["G1", "G2", 30],
            ["G2", "G3", 30],
            ["G3", "G1", 30],
            ["G4", "PR1", 30],
        ]
    )
    assert messages(load(sheets)) == ["Groups!R2C2 [parent]: cycle G1 → G2 → G3 → G1"]


def test_a_group_may_have_a_group_as_parent() -> None:
    sheets = edited(
        Groups=[["code", "parent", "size"], ["G1", "PR1", 30], ["G1a", "G1", 15], ["G2", "PR1", 25]]
    )
    assert messages(load(sheets)) == []


def test_a_period_must_end_after_it_starts() -> None:
    sheets = set_cell(base_sheets(), "Periods", 2, "end", "07:00")
    assert messages(load(sheets)) == ["Periods!R2C3 [end]: end must be after start"]


def test_a_template_needs_a_batch_size_only_when_batched() -> None:
    header = [
        "code", "module", "kind", "mode", "groups", "batch_size", "duration", "start_pattern",
        "room_type",
    ]  # fmt: skip
    ok = [header, ["TP1", "M1", "LEC", "joint", "type:StudentGroup", None, 2, "2H", "lab"]]
    assert messages(load(edited(Templates=ok))) == []
    batched = [header, ["TP1", "M1", "TUT", "batched", "type:StudentGroup", None, 1, "1H", "lab"]]
    assert messages(load(edited(Templates=batched))) == [
        'Templates!R2C6 [batch_size]: required when mode is "batched"'
    ]
    bad_mode = [header, ["TP1", "M1", "TUT", "weekly", "type:StudentGroup", None, 1, "1H", None]]
    assert (
        "expected one of joint, per_group, batched" in messages(load(edited(Templates=bad_mode)))[0]
    )


def test_template_rows_are_expanded_once_into_activities_and_dropped() -> None:
    header = [
        "code", "module", "kind", "mode", "groups", "teachers", "duration", "start_pattern",
        "room_type", "sessions_per_week",
    ]  # fmt: skip
    rows = [
        header,
        ["TP1", "M1", "LEC", "joint", "under:PR1", "T1", 2, "2H", "lab", 2],
        ["TP2", "M1", "LEC", "per_group", "type:StudentGroup", None, 1, "1H", None, None],
    ]
    ds = load(edited(Templates=rows)).data.dataset  # type: ignore[union-attr]
    assert ds.templates == ()  # the application keeps no templates (ADR-0007)
    made = [e for e in ds.events if e.code.startswith("M1-LEC-")]
    assert [(e.duration, e.template) for e in made] == [(2, None), (2, None), (1, None), (1, None)]
    # TP1 is joint for the groups under PR1 and taught by T1, twice a week, in a lab.
    first = {f.resource for f in ds.fixed if f.event == "M1-LEC-01"}
    assert first == {"G1", "G2", "T1"}
    (spec,) = [q for q in ds.pooled if q.event == "M1-LEC-01"]
    assert (spec.resource_type, spec.count, spec.filter) == ("Room", 1, "tag:room_type=lab")
    assert not [q for q in ds.pooled if q.event == "M1-LEC-03"]  # TP2 names no room type
    assert {f.resource for f in ds.fixed if f.event == "M1-LEC-03"} == {"G1"}  # one group each


def test_a_template_selector_must_select_resources() -> None:
    header = ["code", "module", "kind", "mode", "groups", "duration", "start_pattern"]
    rows = [header, ["TP1", "M1", "LEC", "joint", "kind:LEC", 2, "2H"]]
    assert messages(load(edited(Templates=rows))) == [
        'Templates!R2C5 [groups]: clause "kind:" does not select resources'
    ]


@pytest.mark.parametrize(
    ("delivery", "room_type", "room_count", "message"),
    [
        (
            "online",
            "lab",
            None,
            "Activities!R3C7 [room_type]: an online activity cannot have a room type",
        ),
        ("online", None, 1, "Activities!R3C8 [room_count]: an online activity cannot have rooms"),
        (None, None, None, "Activities!R3C7 [room_type]: required unless room_count is 0"),
        (None, None, 2, "Activities!R3C7 [room_type]: required unless room_count is 0"),
        (
            None,
            "lab",
            0,
            "Activities!R3C8 [room_count]: expected integer ≥ 1 when room_type is set",
        ),
    ],
)
def test_room_columns_must_agree_with_delivery(
    delivery: object, room_type: object, room_count: object, message: str
) -> None:
    sheets = set_cell(base_sheets(), "Activities", 3, "delivery", delivery)
    sheets = set_cell(sheets, "Activities", 3, "room_type", room_type)
    sheets = set_cell(sheets, "Activities", 3, "room_count", room_count)
    assert any(m.startswith(message) for m in messages(load(sheets))), messages(load(sheets))


def test_an_in_person_activity_may_need_no_room() -> None:
    sheets = set_cell(base_sheets(), "Activities", 3, "delivery", "in_person")
    sheets = set_cell(sheets, "Activities", 3, "room_count", 0)
    outcome = load(sheets)
    assert messages(outcome) == []
    assert {q.event for q in outcome.data.dataset.pooled} == {"A1"}  # type: ignore[union-attr]


def test_a_room_count_above_one_is_a_pooled_count() -> None:
    sheets = set_cell(base_sheets(), "Activities", 2, "room_count", 2)
    (room,) = load(sheets).data.dataset.pooled  # type: ignore[union-attr]
    assert room.count == 2


def test_a_tag_that_has_its_own_column_cannot_also_be_in_tags() -> None:
    sheets = set_cell(base_sheets(), "Rooms", 2, "tags", "room_type=hall")
    assert messages(load(sheets)) == [
        'Rooms!R2C6 [tags]: tag "room_type" has its own column, room_type'
    ]


def test_the_format_version_is_checked() -> None:
    sheets = set_cell(base_sheets(), "_meta", 2, "value", 3)
    assert messages(load(sheets)) == ["_meta: format_version 3 not supported (max 2)"]
    sheets = set_cell(base_sheets(), "_meta", 2, "value", "one")
    assert messages(load(sheets)) == ['_meta: format_version must be an integer, got "one"']


def test_meta_must_exist_and_name_a_known_preset() -> None:
    assert messages(load(edited(_meta=None))) == ["_meta: sheet is missing"]
    assert messages(load(edited(_meta=[["key", "value"], ["format_version", 1]]))) == [
        '_meta: "preset" is required'
    ]
    sheets = set_cell(base_sheets(), "_meta", 3, "value", "nonsense")
    assert messages(load(sheets)) == ['_meta: unknown preset "nonsense"']


def test_unknown_sheets_and_columns_are_errors_but_helper_sheets_are_ignored() -> None:
    sheets = edited(Scratch=[["a"], [1]], _refs=[["a"], [1]])
    assert messages(load(sheets)) == ["Scratch: unknown sheet"]
    sheets = add_column(base_sheets(), "Teachers", "nickname", ["tee"])
    assert messages(load(sheets)) == ["Teachers!R1C4 [nickname]: unknown column"]


def test_a_duplicate_column_is_an_error() -> None:
    sheets = add_column(base_sheets(), "Teachers", "name", ["again"])
    assert messages(load(sheets)) == ["Teachers!R1C4 [name]: duplicate column (first at C2)"]


def test_a_star_needs_periods_only_where_it_is_allowed() -> None:
    sheets = set_cell(base_sheets(), "Availability", 2, "day", "*")
    assert messages(load(sheets)) == ['Availability!R2C2 [day]: unknown code "*"']


def test_all_the_errors_are_collected_and_nothing_is_built() -> None:
    sheets = base_sheets()
    sheets = set_cell(sheets, "Rooms", 2, "capacity", "many")
    sheets = set_cell(sheets, "Activities", 2, "teachers", "NOBODY")
    sheets = set_cell(sheets, "Constraints", 2, "scope", "bogus:x")
    outcome = load(sheets)
    assert not outcome.ok
    assert outcome.data is None
    assert len(outcome.errors) == 3
    assert messages(outcome) == [
        'Rooms!R2C4 [capacity]: expected integer ≥ 0, got "many"',
        'Activities!R2C11 [teachers]: unknown code "NOBODY"',
        'Constraints!R2C3 [scope]: unknown clause "bogus:"',
    ]


def test_errors_are_ordered_by_sheet_then_row() -> None:
    sheets = base_sheets()
    sheets = set_cell(sheets, "Groups", 3, "size", "x")
    sheets = set_cell(sheets, "Groups", 2, "size", "y")
    found = [e for e in load(sheets).errors]
    assert [(e.sheet, e.row) for e in found] == [("Groups", 2), ("Groups", 3)]


# --- Assignments ---------------------------------------------------------------------------------


ASSIGNMENT_HEADER = ["run", "activity", "day", "start", "rooms"]


def test_an_assignments_sheet_becomes_a_result() -> None:
    rows = [
        ASSIGNMENT_HEADER,
        ["r1", "A1", "Mon", "08:00", "R1"],
        ["r1", "A2", "Tue", "11:00", None],
    ]
    outcome = load(edited(Assignments=rows))
    assert messages(outcome) == []
    data = outcome.data
    assert data is not None and data.result is not None
    first, second = data.result.assignments
    assert (first.event, first.day, first.start_period) == ("A1", "Mon", "P1")
    assert first.chosen[0].resources == ("R1",)
    assert (second.event, second.day, second.start_period, second.chosen) == ("A2", "Tue", "P4", ())
    assert data.run == "r1"


def test_assignment_rows_are_validated() -> None:
    rows = [
        ASSIGNMENT_HEADER,
        ["r1", "A1", "Mon", "08:15", "R1"],
        ["r1", "A2", None, "09:00", None],
        ["r1", "NOPE", "Mon", "09:00", None],
    ]
    found = messages(load(edited(Assignments=rows)))
    assert "Assignments!R2C4 [start]: no period starts at 08:15" in found
    assert "Assignments!R3 [day]: required" in found or "Assignments!R3C3 [day]: required" in found
    assert 'Assignments!R4C2 [activity]: unknown code "NOPE"' in found


def test_several_runs_in_one_sheet_are_an_error() -> None:
    rows = [ASSIGNMENT_HEADER, ["a", "A1", "Mon", "08:00", "R1"], ["b", "A2", "Tue", "11:00", None]]
    assert messages(load(edited(Assignments=rows))) == ["Assignments: contains several runs (a, b)"]


def test_derived_assignment_columns_are_accepted_and_ignored() -> None:
    header = [
        "run",
        "activity",
        "module",
        "kind",
        "day",
        "start",
        "end",
        "rooms",
        "groups",
        "teachers",
        "buildings",
    ]
    rows = [header, ["r1", "A1", "M1", "LEC", "Mon", "08:00", "10:00", "R1", "G1;G2", "T1", "B1"]]
    outcome = load(edited(Assignments=rows))
    assert messages(outcome) == []


def test_raw_sheets_can_be_imported_with_an_explicit_preset() -> None:
    from tts.presets import get_preset

    sheets = base_sheets()
    sheets["_meta"] = [["key", "value"], ["format_version", 1], ["preset", "ignored"]]
    assert import_raw(to_raw(sheets), get_preset("academic_weekly", 1)).ok
