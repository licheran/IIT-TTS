"""The exams section of the wiki (`docs/wiki/exams/`) matches the exams preset's sheets."""

from pathlib import Path

import pytest
from test_wiki_tables import columns_table, expected_cells

from tts.core.sheets import SheetDef
from tts.presets.academic_weekly.sheets import SHEETS as ACADEMIC
from tts.presets.exams.sheets import SHEETS as EXAMS

WIKI = Path(__file__).resolve().parents[3] / "docs" / "wiki"
PAGES = WIKI / "exams"
ACADEMIC_BY_NAME = {s.name: s for s in ACADEMIC}
SHARED = {"_meta", "StartPatterns", "Availability", "Constraints"}


def has_page(sheet: SheetDef) -> bool:
    return (PAGES / f"{sheet.name}.md").is_file()


@pytest.mark.parametrize("sheet", EXAMS, ids=lambda s: s.name)
def test_each_exams_sheet_has_a_page_or_shares_the_academic_one(sheet: SheetDef) -> None:
    overview = (PAGES / "README.md").read_text("utf-8")
    assert f"`{sheet.name}`" in overview, "listed in the overview"
    if sheet.name in SHARED:
        assert not has_page(sheet)
        assert f"](../tables/{sheet.name}.md)" in overview
        twin = ACADEMIC_BY_NAME[sheet.name]
        assert [(c.name, c.kind, c.required, c.default) for c in sheet.columns] == [
            (c.name, c.kind, c.required, c.default) for c in twin.columns
        ], "a shared sheet must have the academic sheet's columns"
        return
    assert has_page(sheet), f"no exams page for {sheet.name}"
    assert f"]({sheet.name}.md)" in overview
    shown = columns_table(PAGES / f"{sheet.name}.md")
    assert list(shown) == [c.name for c in sheet.columns]
    for column in sheet.columns:
        cells = shown[column.name]
        kind, required, default = expected_cells(column)
        assert (cells[2], cells[3], cells[4]) == (kind, required, default), column.name
        assert cells[1] not in ("", "—"), column.name
        for name in (*column.refs, *column.choices):
            assert name in cells[5], f"{sheet.name}.{column.name}: should mention {name}"
        if column.expands_to:
            assert column.expands_to in cells[5]


def test_every_page_of_the_exams_section_is_a_sheet_of_the_preset() -> None:
    names = {s.name for s in EXAMS}
    pages = {p.stem for p in PAGES.glob("*.md") if p.stem != "README"}
    assert pages <= names and pages == names - SHARED


def test_the_overview_names_the_tab_labels_of_the_preset() -> None:
    overview = (PAGES / "README.md").read_text("utf-8")
    for sheet in EXAMS:
        if not sheet.export_only and sheet.name != "_meta":
            assert f"| {sheet.label} |" in overview or sheet.label in overview, sheet.label
