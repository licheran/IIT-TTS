import re
from pathlib import Path

import pytest

from tts.core.sheets import ColumnDef, Preset, SheetDef
from tts.presets import PRESETS, UnknownPresetError, get_preset
from tts.presets.academic_weekly import PRESET_NAME, types
from tts.presets.academic_weekly.preset import PRESET, PRESET_V2
from tts.presets.academic_weekly.sheets import (
    FORMAT_VERSION,
    HAND_MADE_FORMAT_VERSION,
    RESOURCE_SHEETS,
    SHEETS,
)

SPEC = Path(__file__).resolve().parents[3] / "docs" / "spec" / "03-workbook-format.md"


def spec_sheets() -> dict[str, list[tuple[str, bool]]]:
    """Sheet name -> [(column, required)] read from the table in spec 03 section 2."""
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("## 2. Sheets", 1)[1].split("### 2.1", 1)[0]
    found: dict[str, list[tuple[str, bool]]] = {}
    for line in section.splitlines():
        match = re.match(
            r"^\| `(?P<sheet>[A-Za-z_]+)`(?: \(export only\))? \| (?P<cols>.*) \|$", line
        )
        if not match:
            continue
        cols = match["cols"]
        if match["sheet"] == "_meta":
            cols = cols.split(". ", 1)[0]  # the rest lists metadata keys, not columns
        cols = re.sub(r"\([^)]*\)", "", cols)
        found[match["sheet"]] = [
            (m[1], m[2] == "*") for m in re.finditer(r"`([A-Za-z_]+)(\*?)`", cols)
        ]
    return found


def test_the_spec_table_was_found() -> None:
    assert len(spec_sheets()) == 21


def test_sheets_match_the_spec_in_name_and_order() -> None:
    assert [s.name for s in SHEETS] == list(spec_sheets())


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda s: s.name)
def test_columns_match_the_spec_in_name_order_and_required_flag(sheet: SheetDef) -> None:
    expected = spec_sheets()[sheet.name]
    actual = [(c.name, c.required) for c in sheet.columns]
    # `batch_size` is "required if batched": conditional, so not marked `required` unconditionally.
    conditional = {c.name for c in sheet.columns if c.required_when}
    adjusted = [(name, req) for name, req in expected if name not in conditional]
    assert [(n, r) for n, r in actual if n not in conditional] == adjusted
    assert [n for n, _ in actual] == [n for n, _ in expected]


def test_required_when_is_the_conditional_case_named_by_the_spec() -> None:
    templates = PRESET.sheet("Templates")
    assert templates is not None
    (batch,) = [c for c in templates.columns if c.required_when]
    assert (batch.name, batch.required_when) == ("batch_size", ("mode", "batched"))


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda s: s.name)
def test_column_names_are_unique_within_a_sheet(sheet: SheetDef) -> None:
    names = [c.name for c in sheet.columns]
    assert len(names) == len(set(names))


def test_sheet_names_are_unique() -> None:
    names = [s.name for s in SHEETS]
    assert len(names) == len(set(names))


def test_references_point_at_existing_sheets() -> None:
    names = {s.name for s in SHEETS}
    for sheet in SHEETS:
        for column in sheet.columns:
            assert set(column.refs) <= names, (sheet.name, column.name)


def test_convenience_columns_expand_into_join_sheets() -> None:
    by_name = {s.name: s for s in SHEETS}
    for sheet in SHEETS:
        for column in sheet.columns:
            if column.expands_to is not None:
                target = by_name[column.expands_to]
                assert target.target == "fixed"
                assert column.kind == "list"
                assert column.convenience
    convenience = {c.name for s in SHEETS for c in s.columns if c.convenience}
    assert convenience == {"groups", "teachers"}


def test_pooled_mappings_name_existing_columns() -> None:
    for sheet in SHEETS:
        if sheet.pooled is None:
            continue
        assert sheet.column(sheet.pooled.type_column) is not None
        if sheet.pooled.count_column is not None:
            assert sheet.column(sheet.pooled.count_column) is not None
        assert sheet.pooled.resource_type == types.ROOM


def test_resource_sheets_cover_every_resource_type_once() -> None:
    mapped = [s.resource_type for s in SHEETS if s.target == "resource"]
    assert sorted(m for m in mapped if m) == sorted(t.code for t in types.RESOURCE_TYPES)
    assert [s.name for s in SHEETS if s.target == "resource"] == list(RESOURCE_SHEETS)


def test_reference_sheet_maps_the_module_type() -> None:
    (sheet,) = [s for s in SHEETS if s.target == "reference"]
    assert (sheet.name, sheet.reference_type) == ("Modules", types.MODULE)


def test_only_assignments_is_export_only() -> None:
    assert [s.name for s in SHEETS if s.export_only] == ["Assignments"]


def test_derived_columns_only_appear_on_the_assignments_sheet() -> None:
    derived = {(s.name, c.name) for s in SHEETS for c in s.columns if c.derived}
    assert {sheet for sheet, _ in derived} == {"Assignments"}
    assert {name for _, name in derived} == {
        "module",
        "kind",
        "end",
        "groups",
        "teachers",
        "buildings",
    }


def test_the_defaults_named_by_the_spec() -> None:
    def col(sheet: str, name: str) -> ColumnDef:
        found = PRESET.sheet(sheet)
        assert found is not None
        column = found.column(name)
        assert column is not None
        return column

    assert col("Periods", "is_break").default is False
    assert col("Activities", "delivery").default == "in_person"
    assert col("Templates", "sessions_per_week").default == 1
    assert col("Templates", "active").default is True
    assert col("Constraints", "hard").default is True
    assert col("Constraints", "weight").default == 1
    assert col("Constraints", "active").default is True
    assert col("Pins", "source").default == "user"
    assert col("Templates", "mode").choices == ("joint", "per_group", "batched")
    assert col("Availability", "status").choices == ("unavailable", "avoid")
    assert col("Availability", "period").allow_star


def test_the_format_versions_are_two_and_one() -> None:
    assert FORMAT_VERSION == 2  # configured datasets (spec 03 section 2a)
    assert HAND_MADE_FORMAT_VERSION == 1  # hand-made datasets (spec 03 section 2)


def test_the_preset_is_registered_and_serialisable() -> None:
    assert get_preset(PRESET_NAME, 1) is PRESET
    assert get_preset(PRESET_NAME) is PRESET_V2  # the newest
    assert set(PRESETS) == {PRESET_NAME, "exams"}  # the second preset (Phase 11)
    assert Preset.model_validate_json(PRESET.model_dump_json()) == PRESET


def test_an_unknown_preset_names_the_known_ones() -> None:
    with pytest.raises(UnknownPresetError, match="academic_weekly"):
        get_preset("nope")
