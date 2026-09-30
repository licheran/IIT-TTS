"""Reading a workbook into a dataset (spec 03 sections 1 and 3).

The container readers (`workbook.py`, `csvzip.py`) hand this module raw sheets. Import is atomic:
every sheet is typed and validated, every problem is collected as an `ImportIssue` in the format
`<Sheet>!R<row>C<col> [<column>]: <message>`, and a `Dataset` is built only if there are none.

Everything is driven by the preset's sheet definitions. The only per-target code is turning a
typed row into the core object of its target.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from pydantic import ValidationError

from tts.core.constraints.catalogue import CATALOGUE
from tts.core.hierarchy import find_cycles
from tts.core.model import (
    Assignment,
    Availability,
    CapacityRule,
    Constraint,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    Pin,
    PooledChoice,
    PooledRequirement,
    PooledSpec,
    Reference,
    Resource,
    Result,
    StartPattern,
    Template,
    TimeModel,
)
from tts.core.selectors import (
    Selector,
    SelectorError,
    TagClause,
    check_target,
    format_selector,
    parse,
)
from tts.core.sheets import ColumnDef, PooledMapping, Preset, SheetDef
from tts.io.tables import KEY_SEP, LIST_SEP, STAR, WorkbookData, row_key
from tts.presets import UnknownPresetError, get_preset

FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """One problem found while importing, with its position in the file."""

    sheet: str
    row: int | None = None
    col: int | None = None
    column: str | None = None
    message: str = ""

    def format(self) -> str:
        if self.row is None:
            return f"{self.sheet}: {self.message}"
        where = f"{self.sheet}!R{self.row}" + (f"C{self.col}" if self.col is not None else "")
        label = f" [{self.column}]" if self.column else ""
        return f"{where}{label}: {self.message}"


@dataclass(slots=True)
class RawRow:
    """One data row as read from the file. `number` is its 1-based row in the sheet."""

    number: int
    values: list[object]


@dataclass(slots=True)
class RawSheet:
    name: str
    headers: list[str]
    rows: list[RawRow] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    """`data` is set exactly when `errors` is empty."""

    errors: tuple[ImportIssue, ...]
    data: WorkbookData | None = None
    summary: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


# --- Typing cells -------------------------------------------------------------------------------

_INT = re.compile(r"^[+-]?\d+$")
_TIME = re.compile(r"^(\d{1,2}):(\d{2})$")


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _as_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value).strip()


def _split_list(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(LIST_SEP) if part.strip())


class _Bad(Exception):
    """A cell that cannot be typed. The message goes into the issue."""


def _coerce(column: ColumnDef, raw: object) -> object:
    """A typed value for a non-blank cell, or raises `_Bad`."""
    kind = column.kind
    shown = _as_text(raw)
    if kind in ("str", "selector"):
        text = shown
        if column.choices and text not in column.choices:
            raise _Bad(f'expected one of {", ".join(column.choices)}, got "{text}"')
        return column.to_stored(text)
    if kind == "int":
        floor = column.minimum
        expected = "integer" if floor is None else f"integer ≥ {floor}"
        if isinstance(raw, bool):
            raise _Bad(f'expected {expected}, got "{shown}"')
        if isinstance(raw, int):
            number = raw
        elif isinstance(raw, float) and raw.is_integer():
            number = int(raw)
        elif isinstance(raw, str) and _INT.match(raw.strip()):
            number = int(raw.strip())
        else:
            raise _Bad(f'expected {expected}, got "{shown}"')
        if floor is not None and number < floor:
            raise _Bad(f'expected {expected}, got "{shown}"')
        return number
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        lowered = shown.lower()
        if lowered in ("true", "1"):
            return True
        if lowered in ("false", "0"):
            return False
        raise _Bad(f'expected true or false, got "{shown}"')
    if kind == "time":
        if isinstance(raw, datetime):
            raw = raw.time()
        if isinstance(raw, time):
            return time(raw.hour, raw.minute)
        if isinstance(raw, float) and 0 <= raw < 1:
            minutes = round(raw * 24 * 60)
            return time(minutes // 60 % 24, minutes % 60)
        match = _TIME.match(shown)
        if match and int(match[1]) < 24 and int(match[2]) < 60:
            return time(int(match[1]), int(match[2]))
        raise _Bad(f'expected HH:MM, got "{shown}"')
    if kind == "list":
        return _split_list(shown)
    if kind == "pairs":
        pairs: dict[str, str] = {}
        for item in _split_list(shown):
            key, sep, value = item.partition("=")
            if not sep or not key.strip():
                raise _Bad(f'expected key=value pairs separated by "{LIST_SEP}", got "{shown}"')
            if key.strip() in pairs:
                raise _Bad(f'duplicate key "{key.strip()}"')
            pairs[key.strip()] = value.strip()
        return pairs
    if kind == "json":
        if isinstance(raw, str):
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError as error:
                raise _Bad(f"expected a JSON object, got invalid JSON ({error.msg})") from None
        else:
            loaded = raw
        if not isinstance(loaded, dict):
            raise _Bad("expected a JSON object")
        return loaded
    raise AssertionError(f"unknown column kind {kind}")


@dataclass(slots=True)
class _Row:
    sheet: SheetDef
    number: int
    values: dict[str, Any]
    cols: dict[str, int]
    notes: dict[str, str]

    def value(self, field_name: str) -> Any:
        """The value of the column holding a core field, or None."""
        for column in self.sheet.columns:
            if column.field == field_name:
                return self.values.get(column.name)
        return None

    def col(self, field_name: str) -> int | None:
        for column in self.sheet.columns:
            if column.field == field_name:
                return self.cols.get(column.name)
        return None

    def column_name(self, field_name: str) -> str | None:
        for column in self.sheet.columns:
            if column.field == field_name:
                return column.name
        return None


class _Import:
    def __init__(self, raw: dict[str, RawSheet], preset: Preset | None) -> None:
        self.raw = raw
        self.preset = preset
        self.issues: list[ImportIssue] = []
        self.rows: dict[str, list[_Row]] = {}

    def issue(
        self,
        sheet: str,
        row: int | None = None,
        col: int | None = None,
        column: str | None = None,
        message: str = "",
    ) -> None:
        self.issues.append(ImportIssue(sheet, row, col, column, message))

    def issue_at(self, row: _Row, column: str, message: str) -> None:
        self.issue(row.sheet.name, row.number, row.cols.get(column), column, message)

    # -- _meta --

    def read_meta(self) -> dict[str, str]:
        sheet = self.raw.get("_meta")
        meta: dict[str, str] = {}
        if sheet is None:
            self.issue("_meta", message="sheet is missing")
            return meta
        try:
            key_at, value_at = sheet.headers.index("key"), sheet.headers.index("value")
        except ValueError:
            self.issue("_meta", 1, None, None, 'columns "key" and "value" are required')
            return meta
        for row in sheet.rows:
            key = (
                _as_text(row.values[key_at])
                if key_at < len(row.values) and not _is_blank(row.values[key_at])
                else ""
            )
            value = row.values[value_at] if value_at < len(row.values) else None
            if not key:
                self.issue("_meta", row.number, key_at + 1, "key", "required")
            elif key in meta:
                self.issue("_meta", row.number, key_at + 1, "key", f'duplicate "{key}"')
            else:
                meta[key] = "" if _is_blank(value) else _as_text(value)
        version = meta.get("format_version")
        if version is None:
            self.issue("_meta", message='"format_version" is required')
        elif not _INT.match(version):
            self.issue("_meta", message=f'format_version must be an integer, got "{version}"')
        elif int(version) > FORMAT_VERSION:
            self.issue(
                "_meta", message=f"format_version {version} not supported (max {FORMAT_VERSION})"
            )
        if "preset" not in meta:
            self.issue("_meta", message='"preset" is required')
        return meta

    # -- sheets --

    def read_sheets(self) -> None:
        assert self.preset is not None
        known = {s.name: s for s in self.preset.sheets}
        for name in self.raw:
            if name != "_meta" and not name.startswith("_") and name not in known:
                self.issue(name, message="unknown sheet")
        for sheet in self.preset.sheets:
            if sheet.target == "meta":
                continue
            raw = self.raw.get(sheet.name)
            self.rows[sheet.name] = self.read_sheet(sheet, raw) if raw is not None else []

    def read_sheet(self, sheet: SheetDef, raw: RawSheet) -> list[_Row]:
        by_name = {c.name: c for c in sheet.columns}
        index: dict[str, int] = {}
        extras: dict[int, str] = {}
        seen: dict[str, int] = {}
        for position, header in enumerate(raw.headers):
            header = header.strip()
            if not header:
                continue
            if header in seen:
                self.issue(
                    sheet.name,
                    1,
                    position + 1,
                    header,
                    f"duplicate column (first at C{seen[header]})",
                )
                continue
            seen[header] = position + 1
            if header in by_name:
                index[header] = position
            elif header.startswith("x_"):
                extras[position] = header
            else:
                self.issue(sheet.name, 1, position + 1, header, "unknown column")
        for column in sheet.columns:
            if column.required and column.name not in index:
                self.issue(sheet.name, 1, None, column.name, "missing column")

        rows = []
        for raw_row in raw.rows:
            values: dict[str, Any] = {}
            cols: dict[str, int] = {}
            for column in sheet.columns:
                at = index.get(column.name)
                cell = raw_row.values[at] if at is not None and at < len(raw_row.values) else None
                if at is not None:
                    cols[column.name] = at + 1
                if _is_blank(cell):
                    values[column.name] = column.default
                    continue
                try:
                    values[column.name] = _coerce(column, cell)
                except _Bad as bad:
                    self.issue(
                        sheet.name,
                        raw_row.number,
                        at + 1 if at is not None else None,
                        column.name,
                        str(bad),
                    )
                    values[column.name] = None
            notes = {
                header: _as_text(raw_row.values[at])
                for at, header in extras.items()
                if at < len(raw_row.values) and not _is_blank(raw_row.values[at])
            }
            row = _Row(sheet, raw_row.number, values, cols, notes)
            for column in sheet.columns:
                if (
                    column.name not in index
                    and not column.required
                    and column.required_when is None
                ):
                    continue
                if values.get(column.name) is not None or column.derive is not None:
                    continue
                if (
                    column.required
                    and column.name in index
                    and _is_blank(
                        raw_row.values[index[column.name]]
                        if index[column.name] < len(raw_row.values)
                        else None
                    )
                ):
                    self.issue_at(row, column.name, "required")
                elif column.required_when is not None:
                    other, wanted = column.required_when
                    if values.get(other) == wanted:
                        self.issue_at(row, column.name, f'required when {other} is "{wanted}"')
            rows.append(row)
        return rows

    # -- cross-row checks --

    def code_of(self, row: _Row) -> str | None:
        code = row.value("code")
        return code if isinstance(code, str) else None

    def check_codes(self) -> dict[str, dict[str, _Row]]:
        """Unique codes per namespace. Returns codes by sheet name."""
        assert self.preset is not None
        by_sheet: dict[str, dict[str, _Row]] = {}
        resources: dict[str, _Row] = {}
        for sheet in self.preset.sheets:
            codes: dict[str, _Row] = {}
            by_sheet[sheet.name] = codes
            if not any(c.field == "code" for c in sheet.columns) or sheet.target in (
                "meta",
                "assignment",
            ):
                continue
            namespace = resources if sheet.target == "resource" else codes
            for row in self.rows.get(sheet.name, []):
                code = self.code_of(row)
                if code is None:
                    continue
                first = namespace.get(code)
                if first is None:
                    namespace[code] = row
                    codes[code] = row
                    continue
                where = (
                    f"R{first.number}"
                    if first.sheet is sheet
                    else f"{first.sheet.name}!R{first.number}"
                )
                self.issue_at(
                    row, row.column_name("code") or "code", f'duplicate "{code}" (first at {where})'
                )
        return by_sheet

    def check_references(self, codes: dict[str, dict[str, _Row]]) -> None:
        assert self.preset is not None
        for sheet in self.preset.sheets:
            for row in self.rows.get(sheet.name, []):
                for column in sheet.columns:
                    value = row.values.get(column.name)
                    if not column.refs or value is None:
                        continue
                    known: set[str] = set()
                    for target in column.refs:
                        known |= set(codes.get(target, {}))
                    items = value if isinstance(value, tuple) else (value,)
                    for item in items:
                        if column.allow_star and item == STAR:
                            continue
                        if item not in known:
                            self.issue_at(row, column.name, f'unknown code "{item}"')

    def check_rows(self) -> None:
        assert self.preset is not None
        for sheet in self.preset.sheets:
            for row in self.rows.get(sheet.name, []):
                {
                    "period": self.check_period,
                    "template": self.check_template,
                    "event": self.check_event,
                    "constraint": self.check_constraint,
                    "resource": self.check_resource,
                }.get(sheet.target, lambda r: None)(row)
        self.check_cycles()
        self.check_assignments()

    def periods_by_start(self) -> dict[time, list[str]]:
        """Period codes by start time, from the typed `period` rows."""
        assert self.preset is not None
        found: dict[time, list[str]] = defaultdict(list)
        for sheet in self.preset.sheets:
            if sheet.target != "period":
                continue
            for row in self.rows.get(sheet.name, []):
                start, code = row.value("start"), row.value("code")
                if start is not None and code is not None:
                    found[start].append(code)
        return found

    def check_assignments(self) -> None:
        """Each assignment row names an activity, a day and a start that is exactly one period."""
        assert self.preset is not None
        by_start = self.periods_by_start()
        runs: dict[str, _Row] = {}
        for sheet in self.preset.sheets:
            if sheet.target != "assignment":
                continue
            for row in self.rows.get(sheet.name, []):
                run = row.value("run")
                if run and run not in runs:
                    runs[run] = row
                for name, field_name in (("activity", "event"), ("day", "day"), ("start", "start")):
                    if row.value(field_name) is None and row.column_name(field_name) is not None:
                        self.issue_at(row, row.column_name(field_name) or name, "required")
                start = row.value("start")
                if start is not None and len(by_start.get(start, [])) != 1:
                    what = (
                        "no period starts at"
                        if start not in by_start
                        else "several periods start at"
                    )
                    self.issue_at(
                        row,
                        row.column_name("start") or "start",
                        f"{what} {start.strftime('%H:%M')}",
                    )
            if len(runs) > 1:
                self.issue(sheet.name, message=f"contains several runs ({', '.join(sorted(runs))})")

    def check_period(self, row: _Row) -> None:
        start, end = row.value("start"), row.value("end")
        if start is not None and end is not None and end <= start:
            self.issue_at(row, row.column_name("end") or "end", "end must be after start")

    def check_resource(self, row: _Row) -> None:
        tag_columns = {
            c.field.split(":", 1)[1]: c.name
            for c in row.sheet.columns
            if c.field.startswith("tag:")
        }
        tags = row.value("tags") or {}
        for key, column in tag_columns.items():
            if key in tags:
                self.issue_at(
                    row,
                    row.column_name("tags") or "tags",
                    f'tag "{key}" has its own column, {column}',
                )

    def check_template(self, row: _Row) -> None:
        targets = row.value("targets")
        if targets is not None:
            self.check_selector(row, "targets", targets, "resource")

    def check_selector(self, row: _Row, field_name: str, text: str, target: str) -> None:
        column = row.column_name(field_name) or field_name
        try:
            check_target(parse(text), target)  # type: ignore[arg-type]
        except SelectorError as error:
            self.issue_at(row, column, error.message)

    def check_constraint(self, row: _Row) -> None:
        kind = row.values.get("type")
        target = CATALOGUE.get(kind) if isinstance(kind, str) else None
        if isinstance(kind, str) and target is None:
            self.issue_at(row, "type", f'"{kind}" is not in the catalogue')
        scope = row.values.get("scope")
        if isinstance(scope, str):
            try:
                selector = parse(scope)
                if target is not None:
                    check_target(selector, target)
            except SelectorError as error:
                self.issue_at(row, "scope", error.message)

    def pooled_of(self, row: _Row) -> list[tuple[int, PooledMapping, str | None, int]]:
        """(ordinal, mapping, type value, count) of each pooled requirement a row asks for.

        Records issues. Mappings without a type column (ADR-0006) ask for any resource of their
        type whenever their count is at least 1.
        """
        found = []
        for ordinal, mapping in enumerate(row.sheet.pooled_mappings):
            wanted = (
                self._typed_pool(row, mapping)
                if mapping.type_column is not None
                else self._untyped_pool(row, mapping)
            )
            if wanted is not None:
                found.append((ordinal, mapping, wanted[0], wanted[1]))
        return found

    def _untyped_pool(self, row: _Row, mapping: PooledMapping) -> tuple[None, int] | None:
        if mapping.count_column is None:
            return None, 1
        count = row.values.get(mapping.count_column)
        if count is None:
            column = row.sheet.column(mapping.count_column)
            default = column.default if column is not None else None
            count = default if isinstance(default, int) and not isinstance(default, bool) else 1
        return (None, count) if count >= 1 else None

    def _typed_pool(self, row: _Row, mapping: PooledMapping) -> tuple[str, int] | None:
        """A type column (for example a room type) with an optional count column."""
        assert mapping.type_column is not None
        type_column = mapping.type_column
        kind = row.values.get(type_column)
        count = row.values.get(mapping.count_column) if mapping.count_column else None
        online = row.values.get("delivery") == "online"
        if mapping.count_column is None:
            return (kind, 1) if kind else None
        count_column = mapping.count_column
        if online:
            if kind:
                self.issue_at(row, type_column, "an online activity cannot have a room type")
            if count:
                self.issue_at(row, count_column, "an online activity cannot have rooms")
            return None
        if not kind:
            if count is None or count > 0:
                self.issue_at(
                    row,
                    type_column,
                    f"required unless {count_column} is 0 (or the activity is online)",
                )
            return None
        if count is None:
            count = 1
        if count < 1:
            self.issue_at(row, count_column, f"expected integer ≥ 1 when {type_column} is set")
            return None
        return kind, count

    def check_event(self, row: _Row) -> None:
        self.pooled_of(row)

    def check_cycles(self) -> None:
        parents: dict[str, str] = {}
        where: dict[str, _Row] = {}
        assert self.preset is not None
        for sheet in self.preset.sheets:
            if sheet.target != "resource":
                continue
            for row in self.rows.get(sheet.name, []):
                code, parent = self.code_of(row), row.value("parent")
                if code is not None and isinstance(parent, str):
                    parents.setdefault(code, parent)
                    where.setdefault(code, row)
        for cycle in find_cycles(parents):
            row = where[cycle[0]]
            path = " → ".join((*cycle, cycle[0]))
            self.issue_at(row, row.column_name("parent") or "parent", f"cycle {path}")


def _pool_filter(mapping: PooledMapping, value: str | None) -> str:
    """The filter of a pooled requirement: a tag test, or `all` for a mapping without a type."""
    if mapping.tag is None or value is None:
        return "all"
    return format_selector(Selector((TagClause(mapping.tag, value),)))


class _Build:
    """Turns validated typed rows into a `Dataset` (and the optional `Result`)."""

    def __init__(self, imp: _Import, preset: Preset, meta: dict[str, str]) -> None:
        self.imp = imp
        self.preset = preset
        self.meta = meta

    def rows(self, target: str) -> list[_Row]:
        return [
            r
            for s in self.preset.sheets
            if s.target == target
            for r in self.imp.rows.get(s.name, [])
        ]

    def build(self) -> tuple[Dataset, Result | None, str]:
        periods = [
            Period(
                code=r.value("code"),
                start=r.value("start"),
                end=r.value("end"),
                order=r.value("order"),
                is_break=bool(r.value("is_break")),
            )
            for r in self.rows("period")
        ]
        time_model = TimeModel(
            days=tuple(
                Day(code=r.value("code"), label=r.value("label") or "", order=r.value("order"))
                for r in self.rows("day")
            ),
            periods=tuple(periods),
            start_patterns=tuple(
                StartPattern(
                    code=r.value("code"),
                    duration=r.value("duration"),
                    start_periods=r.value("start_periods"),
                    days=r.value("days") or None,
                )
                for r in self.rows("start_pattern")
            ),
        )
        events, fixed, pooled = self.events()
        dataset = Dataset(
            preset=self.preset.name,
            resource_types=self.preset.resource_types,
            resources=tuple(self.resource(r) for r in self.rows("resource")),
            reference_types=self.preset.reference_types,
            references=tuple(self.reference(r) for r in self.rows("reference")),
            time=time_model,
            events=tuple(events),
            fixed=tuple(fixed),
            pooled=tuple(pooled),
            availability=tuple(self.availability(periods)),
            constraints=tuple(
                Constraint(
                    code=r.value("code"),
                    type=r.value("type"),
                    scope=r.value("scope"),
                    params=r.value("params") or {},
                    hard=r.value("hard"),
                    weight=r.value("weight"),
                    active=r.value("active"),
                )
                for r in self.rows("constraint")
            ),
            templates=tuple(self.template(r) for r in self.rows("template")),
            pins=tuple(
                Pin(
                    event=r.value("event"),
                    day=r.value("day"),
                    start_period=r.value("start_period"),
                    resources=r.value("resources") or (),
                    source=r.value("source"),
                )
                for r in self.rows("pin")
            ),
        )
        result, run = self.result()
        return dataset, result, run

    def fields(self, row: _Row) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
        """(plain fields, tags, attributes) of a resource or reference row."""
        tags: dict[str, str] = dict(row.value("tags") or {})
        attributes: dict[str, Any] = {}
        plain: dict[str, Any] = {}
        for column in row.sheet.columns:
            value = row.values.get(column.name)
            if value is None:
                continue
            if column.field.startswith("tag:"):
                tags[column.field.split(":", 1)[1]] = value
            elif column.field.startswith("attr:"):
                attributes[column.field.split(":", 1)[1]] = value
            else:
                plain[column.field] = value
        return plain, tags, attributes

    def resource(self, row: _Row) -> Resource:
        plain, tags, attributes = self.fields(row)
        return Resource(
            code=plain["code"],
            type=row.sheet.resource_type,
            name=plain.get("name", ""),
            parent=plain.get("parent"),
            capacity=plain.get("capacity"),
            attributes=attributes,
            tags=tags,
        )

    def reference(self, row: _Row) -> Reference:
        plain, tags, attributes = self.fields(row)
        return Reference(
            code=plain["code"],
            type=row.sheet.reference_type,
            name=plain.get("name", ""),
            attributes=attributes,
            tags=tags,
        )

    def template(self, row: _Row) -> Template:
        specs = tuple(
            PooledSpec(
                resource_type=mapping.resource_type,
                ordinal=ordinal,
                count=count,
                filter=_pool_filter(mapping, value),
                capacity_rule=CapacityRule.parse(mapping.capacity_rule),
            )
            for ordinal, mapping, value, count in self.imp.pooled_of(row)
        )
        return Template(
            code=row.value("code"),
            kind=row.value("kind"),
            mode=row.value("mode"),
            reference=row.value("reference"),
            targets=row.value("targets"),
            batch_size=row.value("batch_size"),
            fixed=row.value("fixed") or (),
            pooled=specs,
            duration=row.value("duration"),
            start_pattern=row.value("start_pattern"),
            sessions_per_week=row.value("sessions_per_week"),
            active=row.value("active"),
        )

    def events(self) -> tuple[list[Event], list[FixedRequirement], list[PooledRequirement]]:
        events: list[Event] = []
        fixed: set[tuple[str, str]] = set()
        pooled: list[PooledRequirement] = []
        for row in self.rows("event"):
            code = row.value("code")
            events.append(
                Event(
                    code=code,
                    kind=row.value("kind"),
                    duration=row.value("duration"),
                    start_pattern=row.value("start_pattern"),
                    reference=row.value("reference"),
                    delivery=row.value("delivery"),
                    tags=row.value("tags") or {},
                    template=row.value("template"),
                )
            )
            for column in row.sheet.columns:
                if column.expands_to is not None:
                    fixed |= {(code, item) for item in row.values.get(column.name) or ()}
            for ordinal, mapping, value, count in self.imp.pooled_of(row):
                pooled.append(
                    PooledRequirement(
                        event=code,
                        resource_type=mapping.resource_type,
                        ordinal=ordinal,
                        count=count,
                        filter=_pool_filter(mapping, value),
                        capacity_rule=CapacityRule.parse(mapping.capacity_rule),
                    )
                )
        for row in self.rows("fixed"):
            fixed.add((row.value("event"), row.value("resource")))
        return events, [FixedRequirement(event=e, resource=r) for e, r in sorted(fixed)], pooled

    def availability(self, periods: list[Period]) -> list[Availability]:
        found = []
        for row in self.rows("availability"):
            period = row.value("period")
            for code in [p.code for p in periods] if period == STAR else [period]:
                found.append(
                    Availability(
                        resource=row.value("resource"),
                        day=row.value("day"),
                        period=code,
                        status=row.value("status"),
                    )
                )
        return found

    def result(self) -> tuple[Result | None, str]:
        rows = self.rows("assignment")
        if not rows:
            return None, ""
        by_start = self.imp.periods_by_start()  # every start is exactly one period (checked)
        assignments = []
        run = ""
        for row in rows:
            run = run or row.value("run") or ""
            chosen = [(0, row.value("resources") or ())]
            for column in row.sheet.columns:  # one column per requirement (ADR-0006)
                name, _, ordinal = column.field.partition(":")
                if name == "resources" and ordinal.isdigit():
                    chosen.append((int(ordinal), row.value(column.field) or ()))
            assignments.append(
                Assignment(
                    event=row.value("event"),
                    day=row.value("day"),
                    start_period=by_start[row.value("start")][0],
                    chosen=tuple(
                        PooledChoice(ordinal=n, resources=items) for n, items in chosen if items
                    ),
                )
            )
        return Result(assignments=tuple(assignments)), run


def import_raw(raw: dict[str, RawSheet], preset: Preset | None = None) -> ImportOutcome:
    """Validate raw sheets and build the workbook's data. Collects every problem first."""
    imp = _Import(raw, preset)
    meta = imp.read_meta()

    if imp.preset is None:
        name = meta.get("preset")
        if name is not None:
            try:
                imp.preset = get_preset(name)
            except UnknownPresetError:
                imp.issue("_meta", message=f'unknown preset "{name}"')
    if imp.preset is None:
        return ImportOutcome(tuple(imp.issues))
    preset_in_use = imp.preset

    imp.read_sheets()
    codes = imp.check_codes()
    imp.check_references(codes)
    imp.check_rows()
    summary = {name: len(rows) for name, rows in imp.rows.items() if rows}
    if imp.issues:
        return ImportOutcome(tuple(_ordered(imp.issues, raw)), summary=summary)

    build = _Build(imp, preset_in_use, meta)
    try:
        dataset, result, run = build.build()
    except ValidationError as error:
        imp.issue("workbook", message=str(error).splitlines()[0])
        return ImportOutcome(tuple(imp.issues), summary=summary)
    if imp.issues:  # found while building the result
        return ImportOutcome(tuple(_ordered(imp.issues, raw)), summary=summary)
    for problem in dataset.validate_invariants():
        imp.issue(problem.table, message=f"{problem.key}: {problem.message}")
    if imp.issues:
        return ImportOutcome(tuple(imp.issues), summary=summary)

    notes: dict[tuple[str, str], dict[str, str]] = {}
    for sheet_name, rows in imp.rows.items():
        for row in rows:
            if row.notes:
                notes[(sheet_name, row_key(row.sheet, row.values))] = dict(row.notes)
    extra_meta = {k: v for k, v in meta.items() if k not in ("format_version", "preset")}
    data = WorkbookData(dataset=dataset, result=result, meta=extra_meta, notes=notes, run=run)
    return ImportOutcome((), data, summary)


def _ordered(issues: list[ImportIssue], raw: dict[str, RawSheet]) -> list[ImportIssue]:
    """Issues in file order: by sheet (as read), then row, then column."""
    order = {name: i for i, name in enumerate(raw)}
    return sorted(
        issues,
        key=lambda i: (order.get(i.sheet, len(order)), i.row or 0, i.col or 0, i.message),
    )


__all__ = [
    "FORMAT_VERSION",
    "KEY_SEP",
    "ImportIssue",
    "ImportOutcome",
    "RawRow",
    "RawSheet",
    "import_raw",
]
