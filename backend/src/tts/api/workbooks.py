"""Datasets as workbooks: loading, saving and editing rows through the workbook contract.

Table edits do not touch the tables directly. They change one sheet of the dataset's workbook
tables and re-import the result, so a row edit obeys exactly the rules of a file import (spec 03)
and reports its problems the same way.
"""

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from tts.api.errors import ApiError, not_found
from tts.core.model import Dataset
from tts.core.sheets import Preset, SheetDef
from tts.io.importer import ImportIssue, ImportOutcome, RawRow, RawSheet, import_raw
from tts.io.tables import KEY_SEP, Cell, Table, WorkbookData, build_tables, row_key
from tts.presets import UnknownPresetError, get_preset, preset_for_kind
from tts.store.repositories import DatasetRepo


def preset_of(session: Session, dataset_id: int) -> Preset:
    repo = DatasetRepo(session)
    name = repo.info(dataset_id).preset
    try:
        get_preset(name)  # an unknown preset is an error whatever the kind
        return preset_for_kind(name, repo.kind(dataset_id))
    except UnknownPresetError as error:
        raise ApiError(422, "unknown_preset", str(error)) from None


def pack_extras(data: WorkbookData) -> dict[str, Any]:
    """The workbook extras (the `_meta` rows and the user's `x_` notes) as stored JSON."""
    return {
        "meta": dict(data.meta),
        "notes": [[sheet, key, dict(cells)] for (sheet, key), cells in sorted(data.notes.items())],
    }


def unpack_extras(
    extras: Mapping[str, Any],
) -> tuple[dict[str, str], dict[tuple[str, str], dict[str, str]]]:
    meta = dict(extras.get("meta", {}))
    notes = {(sheet, key): dict(cells) for sheet, key, cells in extras.get("notes", [])}
    return meta, notes


def load_data(session: Session, dataset_id: int) -> WorkbookData:
    repo = DatasetRepo(session)
    dataset = repo.load(dataset_id)
    meta, notes = unpack_extras(repo.extras(dataset_id))
    return WorkbookData(dataset=dataset, meta=meta, notes=notes)


def save_data(
    session: Session, dataset_id: int, data: WorkbookData, keep: Dataset | None = None
) -> None:
    """Replace the dataset with `data`. With `keep`, the edits of that (older) dataset stay."""
    dataset = data.dataset if keep is None else keep_edits(keep, data.dataset)
    DatasetRepo(session).save(dataset_id, dataset, pack_extras(data))


def keep_edits(before: Dataset, after: Dataset) -> Dataset:
    """`after` with the edits `before` had.

    An edit is a declared event of a demand. The workbook of a configured dataset has no sheet
    for them, so a change made through its tables would otherwise forget them. One that no longer
    fits the configuration stays, and pre-flight names it (spec 05 section 2.2).
    """
    if after.kind != "configured":
        return after
    codes = {e.code for e in before.events if e.demand is not None}
    if not codes:
        return after
    return after.model_copy(
        update={
            "events": tuple(
                sorted(
                    (*after.events, *(e for e in before.events if e.code in codes)),
                    key=lambda e: e.code,
                )
            ),
            "fixed": (*after.fixed, *(f for f in before.fixed if f.event in codes)),
            "pins": (*after.pins, *(p for p in before.pins if p.event in codes)),
        }
    )


def issue_dict(issue: ImportIssue) -> dict[str, Any]:
    return {
        "sheet": issue.sheet,
        "row": issue.row,
        "col": issue.col,
        "column": issue.column,
        "message": issue.message,
        "text": issue.format(),
    }


def problems(outcome: ImportOutcome) -> list[dict[str, Any]]:
    return [issue_dict(i) for i in outcome.errors]


def tables_by_name(data: WorkbookData, preset: Preset) -> dict[str, Table]:
    """The tables the application shows and edits (hidden join sheets folded into columns)."""
    return {t.name: t for t in build_tables(data, preset, shortcuts=True)}


def _raw(tables: Mapping[str, Table]) -> dict[str, RawSheet]:
    raw = {}
    for name, table in tables.items():
        sheet = RawSheet(name, list(table.headers))
        for number, row in enumerate(table.rows, start=2):
            sheet.rows.append(RawRow(number, list(row)))
        raw[name] = sheet
    return raw


def reimport(tables: Mapping[str, Table], preset: Preset) -> WorkbookData:
    """Build the workbook data back from edited tables, or raise the row-level problems."""
    outcome = import_raw(_raw(tables), preset)
    if outcome.data is None:
        raise ApiError(422, "invalid_table", "the change is not valid", problems(outcome))
    return outcome.data


def sheet_def(preset: Preset, sheet: str) -> SheetDef:
    found = preset.sheet(sheet)
    if found is None or found.export_only or found.hidden or found.import_only:
        raise not_found(f'no table "{sheet}" in preset {preset.name}')
    return found


def key_of(table: Table, sheet: SheetDef, row: tuple[Cell, ...]) -> str:
    return row_key(sheet, dict(zip(table.headers, row, strict=True)))


def show_key(key: str) -> str:
    return key.replace(KEY_SEP, " / ")


def _coerce(column: str, value: Any) -> Cell:
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, str):
        return value if value.strip() else None
    raise ApiError(422, "invalid_value", f'"{column}": expected text, a number or true/false')


def _row_from(
    table: Table, values: Mapping[str, Any], base: tuple[Cell, ...] | None
) -> tuple[Cell, ...]:
    unknown = [k for k in values if k not in table.headers]
    if unknown:
        raise ApiError(422, "unknown_column", f'unknown column "{unknown[0]}"', unknown)
    row: list[Cell] = list(base) if base is not None else [None] * len(table.headers)
    for at, header in enumerate(table.headers):
        if header in values:
            row[at] = _coerce(header, values[header])
    return tuple(row)


def _with_note_columns(table: Table, values: Mapping[str, Any]) -> Table:
    """Let an edit add an `x_` note column that the table does not have yet."""
    extra = [k for k in values if k not in table.headers and k.startswith("x_")]
    if not extra:
        return table
    rows = tuple(row + (None,) * len(extra) for row in table.rows)
    return Table(table.name, table.headers + tuple(extra), rows)


def _replace_rows(table: Table, rows: list[tuple[Cell, ...]]) -> Table:
    return Table(table.name, table.headers, tuple(rows))


def create_row(
    session: Session, dataset_id: int, sheet_name: str, values: Mapping[str, Any]
) -> str:
    preset = preset_of(session, dataset_id)
    sheet = sheet_def(preset, sheet_name)
    data = load_data(session, dataset_id)
    tables = tables_by_name(data, preset)
    table = _with_note_columns(tables[sheet_name], values)
    row = _row_from(table, values, None)
    key = key_of(table, sheet, row)
    if any(key_of(table, sheet, r) == key for r in table.rows):
        raise ApiError(
            409, "duplicate_key", f'a row with key "{show_key(key)}" already exists in {sheet_name}'
        )
    tables[sheet_name] = _replace_rows(table, [*table.rows, row])
    save_data(session, dataset_id, reimport(tables, preset), keep=data.dataset)
    return key


def update_row(
    session: Session, dataset_id: int, sheet_name: str, key: str, values: Mapping[str, Any]
) -> str:
    preset = preset_of(session, dataset_id)
    sheet = sheet_def(preset, sheet_name)
    data = load_data(session, dataset_id)
    tables = tables_by_name(data, preset)
    table = _with_note_columns(tables[sheet_name], values)
    rows = list(table.rows)
    at = next((i for i, r in enumerate(rows) if key_of(table, sheet, r) == key), None)
    if at is None:
        raise not_found(f'no row "{show_key(key)}" in {sheet_name}')
    rows[at] = _row_from(table, values, rows[at])
    new_key = key_of(table, sheet, rows[at])
    if new_key != key and any(
        key_of(table, sheet, r) == new_key for i, r in enumerate(rows) if i != at
    ):
        raise ApiError(409, "duplicate_key", f'a row with key "{show_key(new_key)}" already exists')
    tables[sheet_name] = _replace_rows(table, rows)
    save_data(session, dataset_id, reimport(tables, preset), keep=data.dataset)
    return new_key


def delete_row(session: Session, dataset_id: int, sheet_name: str, key: str) -> None:
    preset = preset_of(session, dataset_id)
    sheet = sheet_def(preset, sheet_name)
    data = load_data(session, dataset_id)
    tables = tables_by_name(data, preset)
    table = tables[sheet_name]
    rows = [r for r in table.rows if key_of(table, sheet, r) != key]
    if len(rows) == len(table.rows):
        raise not_found(f'no row "{show_key(key)}" in {sheet_name}')
    tables[sheet_name] = _replace_rows(table, rows)
    save_data(session, dataset_id, reimport(tables, preset), keep=data.dataset)
