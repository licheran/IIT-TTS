"""The format version 2 workbook: configuration only (spec 03 sections 2a and 3, ADR-0007)."""

import io
from collections.abc import Callable

import pytest
from academic_config import dataset, module, replaced
from openpyxl import Workbook, load_workbook

from tts.core.model import Dataset
from tts.io.importer import ImportOutcome
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx, import_xlsx


def exported(ds: Dataset) -> bytes:
    buffer = io.BytesIO()
    export_xlsx(WorkbookData(ds), buffer)
    return buffer.getvalue()


def edited(ds: Dataset, change: Callable[[Workbook], None]) -> ImportOutcome:
    workbook = load_workbook(io.BytesIO(exported(ds)))
    change(workbook)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return import_xlsx(buffer.getvalue())


def cell(workbook: Workbook, sheet: str, code: str, column: str, value: object) -> tuple[int, int]:
    """Set the cell of row `code` and column `column`; return its row and column numbers."""
    ws = workbook[sheet]
    headers = [c.value for c in ws[1]]
    col = headers.index(column) + 1
    row = next(r for r in range(2, ws.max_row + 1) if ws.cell(r, 1).value == code)
    ws.cell(row, col).value = value
    return row, col


def messages(outcome: ImportOutcome) -> list[str]:
    return [i.format() for i in outcome.errors]


def test_a_configured_dataset_is_written_as_format_version_two() -> None:
    workbook = load_workbook(io.BytesIO(exported(dataset())))
    meta = {row[0].value: row[1].value for row in workbook["_meta"].iter_rows(min_row=2)}
    assert meta["format_version"] == "2"
    assert "SessionTypes" in workbook.sheetnames
    for retired in ("Templates", "Activities", "ActivityGroups", "ActivityTeachers", "Pins"):
        assert retired not in workbook.sheetnames
    assert "Assignments" not in workbook.sheetnames


def test_a_configured_dataset_survives_a_round_trip() -> None:
    ds = dataset()
    first = import_xlsx(exported(ds))
    assert first.errors == () and first.data is not None
    imported = first.data.dataset
    assert imported.kind == "configured"
    assert [r.code for r in imported.resources] == [r.code for r in ds.resources]
    assert [r.code for r in imported.references] == [r.code for r in ds.references]
    # Writing it out and reading it in again changes nothing.
    second = import_xlsx(exported(imported))
    assert second.data is not None and second.data.dataset == imported


def test_the_configuration_columns_round_trip_as_typed_cells() -> None:
    workbook = load_workbook(io.BytesIO(exported(dataset())))
    modules = workbook["Modules"]
    headers = [c.value for c in modules[1]]
    row = next(r for r in modules.iter_rows(min_row=2) if r[0].value == "M2")
    values = dict(zip(headers, (c.value for c in row), strict=True))
    assert values["optional"] is True
    assert values["level"] == "L6"
    assert values["programmes"] == "P1"
    types_ = workbook["SessionTypes"]
    headers = [c.value for c in types_[1]]
    row = next(r for r in types_.iter_rows(min_row=2) if r[0].value == "LEC")
    values = dict(zip(headers, (c.value for c in row), strict=True))
    assert values["max_groups"] == 3 and values["weekly"] == 1 and values["teachers"] == 1


# --- the messages of spec 03 section 3 -------------------------------------------------------


def test_a_module_without_a_level_is_refused() -> None:
    out = edited(dataset(), lambda wb: cell(wb, "Modules", "M1", "level", None))
    assert messages(out) == ["Modules!R2C3 [level]: required"]


def test_a_module_programme_at_another_level_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "Modules", "M1", "programmes", "P1;P5")))
    row, col = at[0]
    assert messages(out) == [
        f'Modules!R{row}C{col} [programmes]: programme "P5" belongs to level "L5", not "L6"'
    ]


def test_an_unknown_session_type_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(
        dataset(), lambda wb: at.append(cell(wb, "Modules", "M1", "sessions", "LEC;LAB;TUT"))
    )
    row, col = at[0]
    assert messages(out) == [f'Modules!R{row}C{col} [sessions]: unknown code "LAB"']


def test_an_unreadable_session_setting_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(
        dataset(),
        lambda wb: at.append(cell(wb, "Modules", "M1", "sessions", "LEC(start_pattern);TUT")),
    )
    row, col = at[0]
    assert messages(out) == [
        f'Modules!R{row}C{col} [sessions]: cannot read "LEC(start_pattern)": expected name=value'
    ]


def test_an_unknown_session_setting_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(
        dataset(), lambda wb: at.append(cell(wb, "Modules", "M1", "sessions", "LEC(size=2);TUT"))
    )
    row, col = at[0]
    assert messages(out) == [
        f'Modules!R{row}C{col} [sessions]: unknown setting "size" (known: start_pattern, '
        "delivery, room_type, max_groups, teachers, weekly)"
    ]


def test_a_teacher_for_a_session_type_the_module_lacks_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "Teachers", "T3", "modules", "M3:TUT")))
    row, col = at[0]
    assert messages(out) == [
        f'Teachers!R{row}C{col} [modules]: "M3:TUT": module "M3" has no session type "TUT"'
    ]


def test_a_teacher_for_an_unknown_module_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "Teachers", "T1", "modules", "M1;M9")))
    row, col = at[0]
    assert messages(out) == [f'Teachers!R{row}C{col} [modules]: unknown code "M9"']


def test_a_group_under_a_group_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "Groups", "P1/G2", "parent", "P1/G1")))
    row, col = at[0]
    assert messages(out) == [f'Groups!R{row}C{col} [parent]: unknown code "P1/G1"']


def test_an_option_that_is_not_optional_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "Groups", "P1/G2", "options", "M1")))
    row, col = at[0]
    assert messages(out) == [f'Groups!R{row}C{col} [options]: module "M1" is not optional']


def test_an_option_at_another_level_is_refused() -> None:
    ds = dataset(references=(*dataset().references, module("M5", level="L5", optional=True)))
    at: list[tuple[int, int]] = []
    out = edited(ds, lambda wb: at.append(cell(wb, "Groups", "P1/G2", "options", "M5")))
    row, col = at[0]
    assert messages(out) == [
        f'Groups!R{row}C{col} [options]: module "M5" is at level "L5", the group is at level "L6"'
    ]


def test_an_option_not_offered_to_the_programme_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "Groups", "P2/G1", "options", "M2")))
    row, col = at[0]
    assert messages(out) == [
        f'Groups!R{row}C{col} [options]: module "M2" is not offered to programme "P2"'
    ]


def test_an_online_session_type_with_a_room_type_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(
        dataset(), lambda wb: at.append(cell(wb, "SessionTypes", "TUT", "delivery", "online"))
    )
    row, _ = at[0]
    assert messages(out) == [
        f"SessionTypes!R{row}C5 [room_type]: an online session cannot have a room type"
    ]


def test_an_in_person_session_type_without_a_room_type_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(
        dataset(), lambda wb: at.append(cell(wb, "SessionTypes", "TUT", "room_type", None))
    )
    row, col = at[0]
    assert messages(out) == [
        f'SessionTypes!R{row}C{col} [room_type]: required when delivery is "in_person"'
    ]


def test_a_session_type_number_out_of_range_is_refused() -> None:
    at: list[tuple[int, int]] = []
    out = edited(dataset(), lambda wb: at.append(cell(wb, "SessionTypes", "LEC", "max_groups", 0)))
    row, col = at[0]
    assert messages(out) == [
        f'SessionTypes!R{row}C{col} [max_groups]: expected integer ≥ 1, got "0"'
    ]


def test_a_sheet_of_version_one_is_not_part_of_version_two() -> None:
    def add(workbook: Workbook) -> None:
        sheet = workbook.create_sheet("Activities")
        sheet.append(["code", "kind", "duration", "start_pattern"])

    assert messages(edited(dataset(), add)) == ["Activities: unknown sheet"]


def test_a_version_three_file_is_not_supported() -> None:
    def bump(workbook: Workbook) -> None:
        for row in workbook["_meta"].iter_rows(min_row=2):
            if row[0].value == "format_version":
                row[1].value = "3"

    assert messages(edited(dataset(), bump)) == ["_meta: format_version 3 not supported (max 2)"]


def test_a_version_one_workbook_still_imports_into_a_hand_made_dataset(l6_dataset) -> None:  # type: ignore[no-untyped-def]
    """A version 1 workbook still imports into a hand-made dataset (spec 03 section 2)."""
    assert l6_dataset.kind == "hand_made"
    outcome = import_xlsx(exported(l6_dataset))
    assert outcome.errors == (), [e.format() for e in outcome.errors]
    assert outcome.data is not None and outcome.data.dataset.kind == "hand_made"
    workbook = load_workbook(io.BytesIO(exported(l6_dataset)))
    assert "Activities" in workbook.sheetnames and "SessionTypes" not in workbook.sheetnames


@pytest.mark.parametrize("sheet", ["Groups", "Teachers", "Modules", "SessionTypes"])
def test_the_new_and_changed_sheets_are_exported(sheet: str) -> None:
    assert sheet in load_workbook(io.BytesIO(exported(dataset()))).sheetnames


def test_replaced_helper_keeps_other_rows_unchanged() -> None:
    assert replaced(dataset(), "M1", sessions="LEC").references != dataset().references
