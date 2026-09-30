"""The academic table reference (`docs/wiki/tables/`) matches the sheet definitions."""

import re
from pathlib import Path

import pytest

from tts.core.selectors import parse as parse_selector
from tts.core.sheets import ColumnDef, SheetDef
from tts.presets.academic_weekly.sheets import SHEETS

WIKI = Path(__file__).resolve().parents[3] / "docs" / "wiki" / "tables"

TYPE_WORDS = {
    "str": "text",
    "int": "whole number",
    "bool": "true/false",
    "time": "time (HH:MM)",
    "list": "list",
    "pairs": "key=value pairs",
    "json": "JSON",
    "selector": "selector",
}


def columns_table(page: Path) -> dict[str, list[str]]:
    """The rows of a page's Columns table, by column name, each as its list of cells."""
    text = page.read_text("utf-8")
    body = text[text.index("## Columns") :].split("\n## ", 1)[0]
    rows = {}
    for line in body.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) == 6 and cells[0].startswith("`"):
            rows[cells[0].strip("`")] = cells
    return rows


def expected_cells(column: ColumnDef) -> tuple[str, str, str]:
    kind = TYPE_WORDS[column.kind]
    if column.kind == "int" and column.minimum is not None:
        kind += f" ≥ {column.minimum}"
    if column.required:
        required = "yes"
    elif column.required_when:
        required = f"yes, when {column.required_when[0]} is {column.required_when[1]}"
    else:
        required = "no"
    if column.default is None:
        default = "—"
    elif isinstance(column.default, bool):
        default = "true" if column.default else "false"
    else:
        default = f"`{column.default}`"
    return kind, required, default


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda s: s.name)
def test_every_table_has_a_page_whose_columns_match_the_sheet_definition(sheet: SheetDef) -> None:
    page = WIKI / f"{sheet.name}.md"
    assert page.is_file(), f"no wiki page for the {sheet.name} table"
    assert f"`{sheet.name}`" in page.read_text("utf-8")
    shown = columns_table(page)
    assert list(shown) == [c.name for c in sheet.columns], "columns, in workbook order"
    for column in sheet.columns:
        cells = shown[column.name]
        kind, required, default = expected_cells(column)
        assert cells[2] == kind, f"{sheet.name}.{column.name}: type"
        assert cells[3] == required, f"{sheet.name}.{column.name}: required"
        assert cells[4] == default, f"{sheet.name}.{column.name}: default"
        assert cells[1] not in ("", "—"), f"{sheet.name}.{column.name}: meaning"
        for name in (*column.refs, *column.choices):
            assert name in cells[5], f"{sheet.name}.{column.name}: should mention {name}"
        if column.allow_star:
            assert "`*`" in cells[5]
        if column.expands_to:
            assert column.expands_to in cells[5]
        if column.derive:
            assert "filled in by the program" in cells[5]


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda s: s.name)
def test_a_table_with_tags_links_to_the_tags_page(sheet: SheetDef) -> None:
    text = (WIKI / f"{sheet.name}.md").read_text("utf-8")
    has_tags = any(c.name == "tags" for c in sheet.columns)
    assert ("](tags.md)" in text) == has_tags


def test_the_tables_overview_lists_every_table_in_workbook_order() -> None:
    text = (WIKI / "README.md").read_text("utf-8")
    links = re.findall(r"\]\(([A-Za-z_]+)\.md\) \|$", text, re.M)
    assert links == [s.name for s in SHEETS]


def test_the_tags_page_names_every_sheet_with_a_tags_column_and_its_selectors_parse() -> None:
    text = (WIKI / "tags.md").read_text("utf-8")
    for sheet in SHEETS:
        if any(c.name == "tags" for c in sheet.columns):
            assert f"]({sheet.name}.md)" in text, sheet.name
    selectors = re.findall(r"^\| `((?:type|tag):[^`]+)` \|", text, re.M)
    assert len(selectors) >= 6
    for selector in selectors:
        parse_selector(selector)
