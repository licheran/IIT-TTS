"""CSV-zip container for the workbook format: `<Sheet>.csv` files, UTF-8, same columns (spec 03)."""

import csv
import zipfile
from collections.abc import Sequence
from io import BytesIO, StringIO
from pathlib import Path
from typing import BinaryIO

from tts.core.sheets import Preset
from tts.io.importer import ImportIssue, ImportOutcome, RawRow, RawSheet, import_raw
from tts.io.tables import Cell, Table, WorkbookData, build_tables
from tts.presets import get_preset

MAX_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 10 * MAX_BYTES  # guards against a zip bomb
_STAMP = (1980, 1, 1, 0, 0, 0)  # fixed, so the same data gives the same bytes


def export_csvzip(
    data: WorkbookData, dest: str | Path | BinaryIO, preset: Preset | None = None
) -> None:
    preset = preset or get_preset(data.dataset.preset)
    write_csvzip(build_tables(data, preset), dest)


def write_csvzip(tables: Sequence[Table], dest: str | Path | BinaryIO) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for table in tables:
            buffer = StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(table.headers)
            for row in table.rows:
                writer.writerow([_text(cell) for cell in row])
            info = zipfile.ZipInfo(f"{table.name}.csv", date_time=_STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, buffer.getvalue().encode("utf-8"))


def _text(cell: Cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, bool):
        return "true" if cell else "false"
    return str(cell)


def import_csvzip(
    source: str | Path | BinaryIO | bytes,
    preset: Preset | None = None,
    max_bytes: int = MAX_BYTES,
) -> ImportOutcome:
    """Read a CSV zip. Never raises for a bad file: the problem comes back as an issue."""
    if isinstance(source, bytes):
        payload = source
    elif isinstance(source, str | Path):
        path = Path(source)
        if not path.is_file():
            return ImportOutcome((ImportIssue("workbook", message=f"file not found: {path}"),))
        payload = path.read_bytes()
    else:
        payload = source.read(max_bytes + 1)
    if len(payload) > max_bytes:
        return ImportOutcome(
            (
                ImportIssue(
                    "workbook", message=f"file is larger than {max_bytes // (1024 * 1024)} MB"
                ),
            )
        )
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile:
        return ImportOutcome((ImportIssue("workbook", message="not a valid .zip file"),))
    with archive:
        infos = [
            i for i in archive.infolist() if not i.is_dir() and i.filename.lower().endswith(".csv")
        ]
        if sum(i.file_size for i in infos) > MAX_UNPACKED_BYTES:
            return ImportOutcome(
                (ImportIssue("workbook", message="the zip unpacks to too much data"),)
            )
        raw: dict[str, RawSheet] = {}
        for info in infos:
            name = Path(info.filename).name[: -len(".csv")]
            try:
                text = archive.read(info).decode("utf-8-sig")
            except UnicodeDecodeError:
                return ImportOutcome((ImportIssue(name, message="not valid UTF-8"),))
            raw[name] = _raw_sheet(name, text)
    return import_raw(raw, preset)


def _raw_sheet(name: str, text: str) -> RawSheet:
    reader = csv.reader(StringIO(text, newline=""))
    first = next(reader, [])
    sheet = RawSheet(name, list(first))
    for number, values in enumerate(reader, start=2):
        if all(not v.strip() for v in values):
            continue
        sheet.rows.append(RawRow(number, [v if v != "" else None for v in values]))
    return sheet
