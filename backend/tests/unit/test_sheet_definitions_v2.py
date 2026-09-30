"""The version 2 sheets of the academic preset match spec 03 section 2a (ADR-0007)."""

import re
from pathlib import Path

import pytest

from tts.core.sheets import SheetDef
from tts.presets import PRESET_VERSIONS, get_preset, preset_for
from tts.presets.academic_weekly import PRESET_NAME
from tts.presets.academic_weekly.preset import PRESET, PRESET_V2
from tts.presets.academic_weekly.sheets import SHEETS, SHEETS_V2

SPEC = Path(__file__).resolve().parents[3] / "docs" / "spec" / "03-workbook-format.md"


def spec_sheets_v2() -> dict[str, list[tuple[str, bool]]]:
    """Sheet name -> [(column, required)] read from the table in spec 03 section 2a."""
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("## 2a. Sheets", 1)[1].split("Not in version 2:", 1)[0]
    found: dict[str, list[tuple[str, bool]]] = {}
    for line in section.splitlines():
        match = re.match(r"^\| `(?P<sheet>[A-Za-z_]+)` \| (?P<cols>.*) \|$", line)
        if not match:
            continue
        cols = match["cols"]
        if match["sheet"] == "_meta":
            cols = cols.split(". ", 1)[0]
        cols = re.sub(r"\([^)]*\)", "", cols)
        found[match["sheet"]] = [
            (m[1], m[2] == "*") for m in re.finditer(r"`([A-Za-z_]+)(\*?)`", cols)
        ]
    return found


def test_the_spec_table_was_found() -> None:
    assert len(spec_sheets_v2()) == 16


def test_sheets_match_the_spec_in_name_and_order() -> None:
    assert [s.name for s in SHEETS_V2] == list(spec_sheets_v2())


@pytest.mark.parametrize("sheet", SHEETS_V2, ids=lambda s: s.name)
def test_columns_match_the_spec_in_name_order_and_required_flag(sheet: SheetDef) -> None:
    expected = spec_sheets_v2()[sheet.name]
    conditional = {c.name for c in sheet.columns if c.required_when}
    actual = [(c.name, c.required) for c in sheet.columns]
    assert [n for n, _ in actual] == [n for n, _ in expected]
    assert [(n, r) for n, r in actual if n not in conditional] == [
        (n, r) for n, r in expected if n not in conditional
    ]


def test_version_two_holds_configuration_only() -> None:
    names = {s.name for s in SHEETS_V2}
    for retired in (
        "Templates", "Activities", "ActivityGroups", "ActivityTeachers", "Pins", "Assignments",
    ):  # fmt: skip
        assert retired not in names
    assert not any(s.export_only for s in SHEETS_V2)
    assert {s.name for s in SHEETS_V2} - {s.name for s in SHEETS} == {"SessionTypes"}


def test_groups_hang_only_under_programmes_in_version_two() -> None:
    groups = PRESET_V2.sheet("Groups")
    assert groups is not None and groups.column("parent").refs == ("Programmes",)  # type: ignore[union-attr]
    assert PRESET.sheet("Groups").column("parent").refs == ("Programmes", "Groups")  # type: ignore[union-attr]


def test_a_module_needs_a_level_and_a_session_type_needs_a_start_pattern() -> None:
    assert PRESET_V2.sheet("Modules").column("level").required  # type: ignore[union-attr]
    assert PRESET_V2.sheet("SessionTypes").column("start_pattern").required  # type: ignore[union-attr]


def test_a_room_type_is_required_when_the_session_is_in_person() -> None:
    column = PRESET_V2.sheet("SessionTypes").column("room_type")  # type: ignore[union-attr]
    assert column.required_when == ("delivery", "in_person")


def test_list_columns_of_version_two_are_lists() -> None:
    for sheet, name in (("Groups", "options"), ("Teachers", "modules"), ("Modules", "sessions")):
        assert PRESET_V2.sheet(sheet).column(name).kind == "list"  # type: ignore[union-attr]


def test_the_versions_are_registered() -> None:
    assert sorted(PRESET_VERSIONS[PRESET_NAME]) == [1, 2]
    assert get_preset(PRESET_NAME, 1) is PRESET
    assert get_preset(PRESET_NAME, 2) is PRESET_V2
    assert PRESET.format_version == 1 and PRESET_V2.format_version == 2


def test_the_dataset_decides_which_version_holds_it() -> None:
    from fixtures import ev, make_dataset, res
    from tts.core.model import Dataset

    hand_made = make_dataset(resources=[res("g1")], events=[ev("e1")]).model_copy(
        update={"preset": PRESET_NAME}
    )
    assert preset_for(hand_made) is PRESET
    assert preset_for(Dataset(preset=PRESET_NAME)) is PRESET_V2
    assert preset_for(Dataset(preset="exams")).format_version == 1
