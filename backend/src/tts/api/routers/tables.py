"""Table views of a dataset: one table per sheet of the preset."""

from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from tts.api.deps import DbSession
from tts.api.schemas import RowIn, RowOut, TablePage
from tts.api.workbooks import (
    create_row,
    delete_row,
    key_of,
    load_data,
    preset_of,
    sheet_def,
    tables_by_name,
    update_row,
)
from tts.io.tables import Cell, Table

router = APIRouter(prefix="/datasets/{dataset_id}/tables", tags=["tables"])


class KeyOut(BaseModel):
    key: str


def _sort_key(value: Cell) -> tuple[int, str, int]:
    if value is None:
        return (2, "", 0)
    if isinstance(value, bool):
        return (0, "", int(value))
    if isinstance(value, int):
        return (0, "", value)
    return (1, value.casefold(), 0)


def _filtered(table: Table, text: str) -> list[tuple[Cell, ...]]:
    """Rows with `text` in any cell, or `column:text` to look in one column."""
    text = text.strip().casefold()
    if not text:
        return list(table.rows)
    column, _, needle = text.partition(":")
    names = {h.casefold(): i for i, h in enumerate(table.headers)}
    if needle and column in names:
        at = names[column]
        return [r for r in table.rows if needle.strip() in str(r[at] or "").casefold()]
    return [r for r in table.rows if any(text in str(c).casefold() for c in r if c is not None)]


@router.get("/{sheet}")
def list_rows(
    dataset_id: int,
    sheet: str,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=10000)] = 100,
    sort: str | None = None,
    filter: str = "",  # noqa: A002 (the query parameter is named by the spec)
) -> TablePage:
    """Rows of a sheet. `sort` is a column name, with a leading `-` for descending."""
    preset = preset_of(session, dataset_id)
    definition = sheet_def(preset, sheet)
    table = tables_by_name(load_data(session, dataset_id), preset)[sheet]
    rows = _filtered(table, filter)
    if sort:
        name = sort.lstrip("-")
        if name in table.headers:
            at = table.headers.index(name)
            rows.sort(key=lambda r: _sort_key(r[at]), reverse=sort.startswith("-"))
    total = len(rows)
    chunk = rows[(page - 1) * size : page * size]
    return TablePage(
        sheet=sheet,
        headers=list(table.headers),
        rows=[
            RowOut(
                key=key_of(table, definition, r), values=dict(zip(table.headers, r, strict=True))
            )
            for r in chunk
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post("/{sheet}", status_code=201)
def add_row(dataset_id: int, sheet: str, body: RowIn, session: DbSession) -> KeyOut:
    return KeyOut(key=create_row(session, dataset_id, sheet, _values(body)))


@router.patch("/{sheet}/{key:path}")
def patch_row(dataset_id: int, sheet: str, key: str, body: RowIn, session: DbSession) -> KeyOut:
    return KeyOut(key=update_row(session, dataset_id, sheet, key, _values(body)))


@router.delete("/{sheet}/{key:path}", status_code=204)
def remove_row(dataset_id: int, sheet: str, key: str, session: DbSession) -> None:
    delete_row(session, dataset_id, sheet, key)


def _values(body: RowIn) -> dict[str, Any]:
    return body.values
