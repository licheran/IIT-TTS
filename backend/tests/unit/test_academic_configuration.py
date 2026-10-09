"""From configuration to demands, and the mistakes only the preset can see (P21.2, ADR-0007)."""

from academic_config import dataset, module, replaced, session_type, with_sessions

from tts.core.model import Dataset
from tts.presets.academic_weekly.configuration import (
    configuration_issues,
    demands,
    parse_teacher_item,
    split_list,
)


def by_code(ds: Dataset):  # type: ignore[no-untyped-def]
    return {d.code: d for d in demands(ds)}


# --- reading the columns ---------------------------------------------------------------------


def test_lists_are_split_on_semicolons_and_trimmed() -> None:
    assert split_list(" A ; B;;C ") == ("A", "B", "C")
    assert split_list(None) == () and split_list("") == ()


def test_a_teacher_item_is_a_module_with_an_optional_kind() -> None:
    assert parse_teacher_item("M1") == ("M1", None)
    assert parse_teacher_item("M1:TUT") == ("M1", "TUT")


# --- demands ---------------------------------------------------------------------------------


def test_each_session_row_makes_one_demand() -> None:
    assert sorted(by_code(dataset())) == ["M1-LEC", "M1-TUT", "M2-TUT", "M3-LEC"]


def test_a_mandatory_module_is_taken_by_every_group_of_its_programmes() -> None:
    found = by_code(dataset())
    assert found["M1-LEC"].participants == ("P1/G1", "P1/G2", "P2/G1")  # blank: every programme
    assert found["M3-LEC"].participants == ("P2/G1",)  # limited to P2


def test_an_optional_module_is_taken_only_by_groups_that_list_it() -> None:
    assert by_code(dataset())["M2-TUT"].participants == ("P1/G1",)


def test_the_session_type_sets_the_blocks_and_the_rest() -> None:
    lecture = by_code(dataset())["M1-LEC"]
    assert (lecture.kind, lecture.reference) == ("LEC", "M1")
    assert (lecture.max_participants, lecture.repeat, lecture.duration) == (3, 1, 2)
    assert lecture.start_pattern == "2H" and lecture.delivery == "in_person"
    assert lecture.blocks == 1
    assert by_code(dataset())["M1-TUT"].blocks == 3  # one group each


def test_the_room_must_be_of_the_type_and_seat_every_group() -> None:
    room, teacher = by_code(dataset())["M1-LEC"].pooled
    assert (room.resource_type, room.ordinal, room.filter) == ("Room", 0, "tag:room_type=lab")
    assert str(room.capacity_rule) == "sum_of_fixed:StudentGroup"
    assert (teacher.resource_type, teacher.ordinal, teacher.count) == ("Teacher", 1, 1)


def test_the_teacher_pool_is_the_teachers_that_list_the_module() -> None:
    found = by_code(dataset())
    assert found["M1-LEC"].pooled[1].filter == "code:T1"  # T2 teaches only tutorials of M1
    assert found["M1-TUT"].pooled[1].filter == "code:T1,T2"
    assert found["M2-TUT"].pooled[1].filter == "code:T2"


def test_with_nobody_listed_the_pool_matches_nothing() -> None:
    ds = replaced(dataset(), "T3", modules="")
    assert by_code(ds)["M3-LEC"].pooled[1].filter == 'code:"(nobody)"'


def test_an_online_session_type_needs_no_room() -> None:
    ds = dataset(
        references=(*dataset().references, session_type("SEM", delivery="online", room_type=""))
    )
    ds = with_sessions(ds, "M1", "SEM")
    (only,) = [d for d in demands(ds) if d.code == "M1-SEM"]
    assert only.delivery == "online"
    assert [p.resource_type for p in only.pooled] == ["Teacher"]


def test_zero_teachers_means_no_teacher_requirement() -> None:
    ds = replaced(dataset(), "TUT", teachers=0)
    assert [p.resource_type for p in by_code(ds)["M1-TUT"].pooled] == ["Room"]


def test_a_module_can_override_the_session_type() -> None:
    ds = with_sessions(dataset(), "M1", ("LEC", {"max_groups": 2, "weekly": 2}), "TUT")
    lecture = by_code(ds)["M1-LEC"]
    assert (lecture.max_participants, lecture.repeat, lecture.blocks) == (2, 2, 2)


def test_a_blank_limit_puts_all_groups_in_one_block() -> None:
    ds = replaced(dataset(), "LEC", max_groups=None)
    demand = by_code(replaced(ds, "LEC", max_groups=""))["M1-LEC"]
    assert demand.blocks == 1


def test_a_demand_of_a_configured_dataset_is_a_sound_core_demand() -> None:
    ds = dataset()
    ds = ds.model_copy(update={"demands": demands(ds)})
    assert [i.message for i in ds.validate_invariants() if i.table == "demand"] == []


def test_a_row_for_an_unknown_session_type_makes_no_demand() -> None:
    ds = with_sessions(dataset(), "M1", "LEC", "LAB", "TUT")
    assert sorted(by_code(ds)) == ["M1-LEC", "M1-TUT", "M2-TUT", "M3-LEC"]


def test_a_module_with_no_rows_makes_no_demand() -> None:
    assert sorted(by_code(with_sessions(dataset(), "M1"))) == ["M2-TUT", "M3-LEC"]


def test_a_blank_cell_takes_the_session_types_value() -> None:
    demand = by_code(dataset())["M1-LEC"]
    assert (demand.max_participants, demand.repeat, demand.start_pattern) == (3, 1, "2H")
    assert [p.resource_type for p in demand.pooled] == ["Room", "Teacher"]


def test_a_filled_cell_overrides_every_setting_for_that_module_only() -> None:
    ds = with_sessions(
        dataset(),
        "M1",
        (
            "LEC",
            {
                "start_pattern": "3H",
                "room_type": "hall",
                "max_groups": 2,
                "teachers": 2,
                "weekly": 2,
            },
        ),
        "TUT",
    )
    found = by_code(ds)
    lecture = found["M1-LEC"]
    assert (lecture.start_pattern, lecture.duration) == ("3H", 3)
    assert (lecture.max_participants, lecture.repeat) == (2, 2)
    room, teacher = lecture.pooled
    assert room.filter == "tag:room_type=hall" and teacher.count == 2
    other = found["M3-LEC"]  # the same session type, another module, keeps the type's values
    assert (other.max_participants, other.repeat, other.start_pattern) == (3, 1, "2H")


def test_an_online_row_never_gets_a_room_even_if_its_session_type_has_a_room_type() -> None:
    ds = with_sessions(dataset(), "M1", ("LEC", {"delivery": "online"}), "TUT")
    lecture = by_code(ds)["M1-LEC"]
    assert lecture.delivery == "online"
    assert [p.resource_type for p in lecture.pooled] == ["Teacher"]


def test_an_in_person_row_of_an_online_session_type_gets_the_room_it_names() -> None:
    ds = dataset(
        references=(*dataset().references, session_type("SEM", delivery="online", room_type=""))
    )
    ds = with_sessions(ds, "M1", ("SEM", {"delivery": "in_person", "room_type": "lab"}))
    seminar = by_code(ds)["M1-SEM"]
    assert seminar.delivery == "in_person"
    assert seminar.pooled[0].filter == "tag:room_type=lab"


# --- mistakes --------------------------------------------------------------------------------


def issues(ds: Dataset) -> list[tuple[str, str, str, str]]:
    return [(i.sheet, i.code, i.column, i.message) for i in configuration_issues(ds)]


def test_a_sound_configuration_has_no_issue() -> None:
    assert issues(dataset()) == []


def test_a_programme_at_another_level_is_reported() -> None:
    ds = replaced(dataset(), "M1", programmes="P1;P5")
    assert issues(ds) == [
        ("Modules", "M1", "programmes", 'programme "P5" belongs to level "L5", not "L6"')
    ]


def test_a_module_taken_by_groups_but_without_rows_is_a_warning() -> None:
    ds = with_sessions(dataset(), "M3")
    (found,) = configuration_issues(ds)
    assert (found.sheet, found.code, found.warning) == ("Modules", "M3", True)
    assert found.message == (
        'module "M3" is taken by 1 groups but has no Session rows, so nothing is scheduled for it'
    )


def test_a_module_nobody_takes_needs_no_rows() -> None:
    ds = dataset(references=(*dataset().references, module("M6", level="L5")))
    assert issues(ds) == []


def test_an_online_row_with_a_room_type_is_reported() -> None:
    ds = with_sessions(dataset(), "M1", ("LEC", {"delivery": "online", "room_type": "lab"}), "TUT")
    assert issues(ds) == [
        ("Session", "M1-LEC", "room_type", "an online session cannot have a room type")
    ]


def test_an_online_session_types_row_with_a_room_type_is_reported() -> None:
    ds = dataset(
        references=(*dataset().references, session_type("SEM", delivery="online", room_type=""))
    )
    ds = with_sessions(ds, "M1", "LEC", "TUT", ("SEM", {"room_type": "lab"}))
    assert issues(ds) == [
        ("Session", "M1-SEM", "room_type", "an online session cannot have a room type")
    ]


def test_an_in_person_row_without_any_room_type_is_reported() -> None:
    ds = dataset(
        references=(*dataset().references, session_type("SEM", delivery="online", room_type=""))
    )
    ds = with_sessions(ds, "M1", "LEC", "TUT", ("SEM", {"delivery": "in_person"}))
    assert issues(ds) == [
        (
            "Session",
            "M1-SEM",
            "room_type",
            'required: the session is in person and neither the row nor session type "SEM" '
            "gives one",
        )
    ]


def test_a_teacher_for_a_module_that_does_not_exist_is_reported() -> None:
    ds = replaced(dataset(), "T1", modules="M1;M9")
    assert issues(ds) == [("Teachers", "T1", "modules", 'unknown code "M9"')]


def test_a_teacher_for_a_session_type_the_module_lacks_is_reported() -> None:
    ds = replaced(dataset(), "T3", modules="M3:TUT")
    assert issues(ds) == [
        ("Teachers", "T3", "modules", '"M3:TUT": module "M3" has no session type "TUT"')
    ]


def test_an_option_that_is_not_optional_is_reported() -> None:
    ds = replaced(dataset(), "P1/G2", options="M1")
    assert issues(ds) == [("Groups", "P1/G2", "options", 'module "M1" is not optional')]


def test_an_option_at_another_level_is_reported() -> None:
    ds = dataset(
        references=(
            *dataset().references,
            module("M5", level="L5", optional=True),
        )
    )
    ds = replaced(ds, "P1/G2", options="M5")
    assert issues(ds) == [
        ("Groups", "P1/G2", "options", 'module "M5" is at level "L5", the group is at level "L6"')
    ]


def test_an_option_not_offered_to_the_groups_programme_is_reported() -> None:
    ds = replaced(dataset(), "P2/G1", options="M2")  # M2 is offered to P1 only
    assert issues(ds) == [
        ("Groups", "P2/G1", "options", 'module "M2" is not offered to programme "P2"')
    ]


def test_an_online_session_type_with_a_room_type_is_reported() -> None:
    ds = replaced(dataset(), "TUT", delivery="online")
    assert issues(ds) == [
        ("SessionTypes", "TUT", "room_type", "an online session cannot have a room type")
    ]


def test_a_session_carries_its_types_tags_then_its_modules_then_its_rows() -> None:
    ds = dataset()

    def tagged(row, tags):  # type: ignore[no-untyped-def]
        return row.model_copy(update={"tags": tags})

    ds = ds.model_copy(
        update={
            "references": tuple(
                tagged(r, (("block", "a"), ("who", "type")))
                if r.code == "LEC"
                else tagged(r, (("who", "module"), ("side", "module")))
                if r.code == "M1"
                else tagged(r, (("side", "row"),))
                if r.code == "M1-LEC"
                else r
                for r in ds.references
            )
        }
    )
    assert dict(by_code(ds)["M1-LEC"].tags) == {"block": "a", "who": "module", "side": "row"}
