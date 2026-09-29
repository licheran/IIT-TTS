"""Helpers to build small raw workbooks and break them in specific ways."""

import copy
from typing import Any

from tts.io.importer import ImportOutcome, RawRow, RawSheet, import_raw

Sheets = dict[str, list[list[Any]]]


def base_sheets() -> Sheets:
    """A small valid workbook: every list is `[headers, *rows]`."""
    return {
        "_meta": [
            ["key", "value"],
            ["format_version", 1],
            ["preset", "academic_weekly"],
            ["institution", "Test Institute"],
        ],
        "Days": [["code", "label", "order"], ["Mon", "Monday", 1], ["Tue", "Tuesday", 2]],
        "Periods": [
            ["code", "start", "end", "order", "is_break"],
            ["P1", "08:00", "09:00", 1, False],
            ["P2", "09:00", "10:00", 2, False],
            ["P3", "10:00", "11:00", 3, True],
            ["P4", "11:00", "12:00", 4, False],
        ],
        "StartPatterns": [
            ["code", "duration", "start_periods", "days"],
            ["1H", 1, "P1;P2;P4", None],
            ["2H", 2, "P1;P2", None],
        ],
        "Programmes": [["code", "name", "level", "tags"], ["PR1", "Programme 1", None, None]],
        "Groups": [
            ["code", "name", "parent", "size", "tags"],
            ["G1", "Group 1", "PR1", 30, None],
            ["G2", None, "PR1", 25, "batch=b"],
        ],
        "Teachers": [["code", "name", "tags"], ["T1", "Teacher 1", None]],
        "Buildings": [
            ["code", "name", "abbreviation", "campus", "tags"],
            ["B1", "Building 1", "BLD", None, None],
        ],
        "Rooms": [
            ["code", "name", "building", "capacity", "room_type", "tags"],
            ["R1", None, "B1", 60, "lab", None],
            ["R2", None, "B1", 40, "hall", "floor=2"],
        ],
        "Modules": [
            ["code", "name", "level", "programme", "tags"],
            ["M1", "Module 1", None, "PR1", None],
        ],
        "Activities": [
            [
                "code",
                "module",
                "kind",
                "duration",
                "start_pattern",
                "delivery",
                "room_type",
                "room_count",
                "template",
                "groups",
                "teachers",
                "tags",
            ],
            ["A1", "M1", "LEC", 2, "2H", None, "lab", None, None, "G1;G2", "T1", None],
            ["A2", "M1", "TUT", 1, "1H", "online", None, 0, None, "G1", None, "note=hi"],
        ],
        "Availability": [
            ["resource", "day", "period", "status"],
            ["T1", "Mon", "*", "unavailable"],
            ["R1", "Tue", "P1", "avoid"],
        ],
        "Constraints": [
            ["code", "type", "scope", "params", "hard", "weight", "active"],
            ["C1", "max_gaps", "type:StudentGroup", '{"max": 2, "per": "day"}', False, 5, True],
        ],
        "Pins": [
            ["activity", "day", "start_period", "rooms", "source"],
            ["A1", "Mon", "P1", "R1", "user"],
        ],
    }


def to_raw(sheets: Sheets) -> dict[str, RawSheet]:
    raw = {}
    for name, rows in sheets.items():
        sheet = RawSheet(name, [str(h) if h is not None else "" for h in rows[0]])
        for number, values in enumerate(rows[1:], start=2):
            sheet.rows.append(RawRow(number, list(values)))
        raw[name] = sheet
    return raw


def load(sheets: Sheets) -> ImportOutcome:
    return import_raw(to_raw(sheets))


def edited(**changes: Any) -> Sheets:
    """The base workbook with sheets replaced (a value of None removes the sheet)."""
    sheets = copy.deepcopy(base_sheets())
    for name, rows in changes.items():
        if rows is None:
            sheets.pop(name, None)
        else:
            sheets[name] = rows
    return sheets


def set_cell(sheets: Sheets, sheet: str, row: int, column: str, value: Any) -> Sheets:
    """Set a cell of a copy. `row` is the 1-based sheet row (2 is the first data row)."""
    out = copy.deepcopy(sheets)
    out[sheet][row - 1][out[sheet][0].index(column)] = value
    return out


def drop_column(sheets: Sheets, sheet: str, column: str) -> Sheets:
    out = copy.deepcopy(sheets)
    at = out[sheet][0].index(column)
    out[sheet] = [[v for i, v in enumerate(row) if i != at] for row in out[sheet]]
    return out


def add_column(sheets: Sheets, sheet: str, header: str, values: list[Any]) -> Sheets:
    out = copy.deepcopy(sheets)
    out[sheet][0].append(header)
    for row, value in zip(out[sheet][1:], values, strict=True):
        row.append(value)
    return out


def messages(outcome: ImportOutcome) -> list[str]:
    return [e.format() for e in outcome.errors]
