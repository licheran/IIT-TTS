"""From configuration to demands, and the mistakes only the preset can see (P21.2, ADR-0007)."""

import pytest
from academic_config import dataset, module, replaced, session_type

from tts.core.model import Dataset
from tts.presets.academic_weekly.configuration import (
    configuration_issues,
    demands,
    parse_session_item,
    parse_teacher_item,
    split_list,
)


def by_code(ds: Dataset):  # type: ignore[no-untyped-def]
    return {d.code: d for d in demands(ds)}


# --- reading the columns ---------------------------------------------------------------------


def test_lists_are_split_on_semicolons_and_trimmed() -> None:
    assert split_list(" A ; B;;C ") == ("A", "B", "C")
    assert split_list(None) == () and split_list("") == ()


def test_a_session_item_is_a_code_with_optional_settings() -> None:
    assert parse_session_item("LEC").code == "LEC"
    item = parse_session_item("LAB(start_pattern=3H, max_groups=2)")
    assert item.code == "LAB"
    assert item.settings == (("start_pattern", "3H"), ("max_groups", "2"))
    assert item.problem is None


def test_an_unreadable_session_item_says_why() -> None:
    assert parse_session_item("LAB(start_pattern)").problem == (
        'cannot read "LAB(start_pattern)": expected name=value'
    )
    assert parse_session_item("LAB(size=2)").problem == (
        'unknown setting "size" (known: start_pattern, delivery, room_type, max_groups, '
        "teachers, weekly)"
    )


def test_a_teacher_item_is_a_module_with_an_optional_kind() -> None:
    assert parse_teacher_item("M1") == ("M1", None)
    assert parse_teacher_item("M1:TUT") == ("M1", "TUT")


# --- demands ---------------------------------------------------------------------------------


def test_each_module_and_session_type_makes_one_demand() -> None:
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
    ds = replaced(ds, "M1", sessions="SEM")
    (only,) = [d for d in demands(ds) if d.code == "M1-SEM"]
    assert only.delivery == "online"
    assert [p.resource_type for p in only.pooled] == ["Teacher"]


def test_zero_teachers_means_no_teacher_requirement() -> None:
    ds = replaced(dataset(), "TUT", teachers=0)
    assert [p.resource_type for p in by_code(ds)["M1-TUT"].pooled] == ["Room"]


def test_a_module_can_override_the_session_type() -> None:
    ds = replaced(dataset(), "M1", sessions="LEC(max_groups=2,weekly=2);TUT")
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


def test_entries_that_cannot_be_read_make_no_demand() -> None:
    ds = replaced(dataset(), "M1", sessions="NOPE;LAB(size=1);LEC")
    assert sorted(by_code(ds)) == ["M1-LEC", "M2-TUT", "M3-LEC"]


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


def test_an_unknown_session_type_is_reported() -> None:
    ds = replaced(dataset(), "M1", sessions="LEC;LAB;TUT")
    assert issues(ds) == [("Modules", "M1", "sessions", 'unknown code "LAB"')]


def test_an_unreadable_setting_is_reported() -> None:
    ds = replaced(dataset(), "M1", sessions="LEC(start_pattern);TUT")
    assert issues(ds) == [
        ("Modules", "M1", "sessions", 'cannot read "LEC(start_pattern)": expected name=value')
    ]


@pytest.mark.parametrize(
    ("setting", "why"),
    [
        ("max_groups=0", "max_groups must be an integer ≥ 1"),
        ("weekly=x", "weekly must be an integer ≥ 1"),
        ("teachers=-1", "teachers must be an integer ≥ 0"),
        ("delivery=hybrid", "delivery must be in_person or online"),
        ("start_pattern=9H", 'unknown start pattern "9H"'),
    ],
)
def test_a_bad_setting_value_is_reported(setting: str, why: str) -> None:
    ds = replaced(dataset(), "M1", sessions=f"LEC({setting});TUT")
    assert issues(ds) == [("Modules", "M1", "sessions", f'cannot read "LEC({setting})": {why}')]


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


def test_a_session_carries_its_types_tags_and_its_modules_tags_win() -> None:
    ds = dataset()

    def tagged(row, tags):  # type: ignore[no-untyped-def]
        return row.model_copy(update={"tags": tags})

    ds = ds.model_copy(
        update={
            "references": tuple(
                tagged(r, (("block", "a"), ("who", "type")))
                if r.code == "LEC"
                else tagged(r, (("who", "module"),))
                if r.code == "M1"
                else r
                for r in ds.references
            )
        }
    )
    assert dict(by_code(ds)["M1-LEC"].tags) == {"block": "a", "who": "module"}
