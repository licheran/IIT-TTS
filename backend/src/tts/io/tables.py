"""Shared types of the workbook reader and writer, and the step from a dataset to tables.

A `Table` is one sheet as typed cells. `build_tables` turns a `WorkbookData` into tables using
only the preset's sheet definitions (`tts.core.sheets`), so the same code serves every preset. The
containers (`workbook.py` for .xlsx, `csvzip.py` for a CSV zip) write tables to files, and
`importer.py` does the reverse.
"""

import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import time

from tts.core.model import (
    CapacityRule,
    Dataset,
    Event,
    PooledSpec,
    Result,
)
from tts.core.selectors import TagClause, parse
from tts.core.sheets import ColumnDef, Preset, SheetDef
from tts.core.timegrid import TimeGrid

Cell = str | int | bool | None

LIST_SEP = ";"
KEY_SEP = "\x1f"  # joins the parts of a composite row key. Never appears in a code.
STAR = "*"


class WorkbookError(ValueError):
    """Base class of workbook errors that are not row-level import issues."""


class WorkbookExportError(WorkbookError):
    """A dataset holds something the workbook format cannot express."""


@dataclass(frozen=True, slots=True)
class Table:
    """One sheet: headers and typed cells (`str`, `int`, `bool` or blank)."""

    name: str
    headers: tuple[str, ...]
    rows: tuple[tuple[Cell, ...], ...]


@dataclass(frozen=True, slots=True)
class WorkbookData:
    """Everything a workbook carries: the dataset, optional assignments and the user's extras.

    `meta` holds the `_meta` rows other than `format_version` and `preset`. `notes` holds the
    user's `x_` columns: it maps (sheet name, row key) to {header: text}. They are kept through
    an import and export but never used by the engine.
    """

    dataset: Dataset
    result: Result | None = None
    meta: Mapping[str, str] = field(default_factory=dict)
    notes: Mapping[tuple[str, str], Mapping[str, str]] = field(default_factory=dict)
    run: str = ""


# --- Formatting cells --------------------------------------------------------------------------


def format_list(items: Iterable[str], where: str = "") -> str | None:
    values = list(items)
    for item in values:
        if LIST_SEP in item:
            raise WorkbookExportError(
                f'{where}: "{item}" contains "{LIST_SEP}" and cannot be listed'
            )
    return LIST_SEP.join(values) if values else None


def format_pairs(pairs: Iterable[tuple[str, str]], where: str = "") -> str | None:
    parts = []
    for key, value in pairs:
        if any(c in key for c in f"{LIST_SEP}=") or LIST_SEP in value:
            raise WorkbookExportError(f'{where}: tag "{key}={value}" cannot be written')
        parts.append(f"{key}={value}")
    return LIST_SEP.join(parts) if parts else None


def format_time(value: time) -> str:
    return value.strftime("%H:%M")


def text_or_none(value: str) -> str | None:
    return value if value else None


# --- Row keys, which identify a row for the user's x_ notes --------------------------------------

_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "meta": ("key",),
    "fixed": ("event", "resource"),
    "availability": ("resource", "day", "period", "status"),
    "pin": ("event",),
    "assignment": ("event",),
}


def row_key(sheet: SheetDef, values: Mapping[str, object]) -> str:
    """The key of a row given its values by column name. `code` for most sheets."""
    fields = _KEY_FIELDS.get(sheet.target, ("code",))
    by_field = {c.field: values.get(c.name) for c in sheet.columns}
    return KEY_SEP.join("" if by_field.get(f) is None else str(by_field[f]) for f in fields)


# --- Dataset to tables --------------------------------------------------------------------------

Values = dict[str, Cell]


class _Export:
    def __init__(self, data: WorkbookData, preset: Preset) -> None:
        self.data = data
        self.ds = data.dataset
        self.preset = preset
        self.grid = TimeGrid(self.ds.time)
        self.resources = {r.code: r for r in self.ds.resources}
        self.type_sheet = {
            s.resource_type: s for s in preset.sheets if s.target == "resource" and s.resource_type
        }
        self.sheet_of: dict[str, str] = {}
        for r in self.ds.resources:
            sheet = self.type_sheet.get(r.type)
            if sheet is None:
                raise WorkbookExportError(f'resource "{r.code}": type "{r.type}" has no sheet')
            self.sheet_of[r.code] = sheet.name
        self.pooled: dict[str, list[PooledSpec]] = defaultdict(list)
        for q in self.ds.pooled:
            self.pooled[q.event].append(q)
        # A fixed requirement no join sheet can list would be dropped silently, so refuse it.
        listed = {
            ref
            for s in preset.sheets
            if s.target == "fixed"
            for c in s.columns
            if c.field == "resource"
            for ref in c.refs
        }
        for f in self.ds.fixed:
            if self.sheet_of.get(f.resource) not in listed:
                raise WorkbookExportError(
                    f'event "{f.event}" is fixed on "{f.resource}", which no sheet can list'
                )

    # -- helpers --

    def refs_of(self, sheet: SheetDef, field_name: str) -> tuple[str, ...]:
        column = next(c for c in sheet.columns if c.field == field_name)
        return column.refs

    def require_sheet(self, code: str, refs: tuple[str, ...], where: str) -> None:
        if refs and self.sheet_of.get(code) not in refs:
            raise WorkbookExportError(
                f'{where}: "{code}" is on sheet {self.sheet_of.get(code)}, expected one of '
                + ", ".join(refs)
            )

    def pooled_columns(
        self, sheet: SheetDef, specs: list[PooledSpec], where: str
    ) -> tuple[str | None, int]:
        """The room-type-and-count columns standing for an event's or template's pooled specs."""
        mapping = sheet.pooled
        if mapping is None:
            if specs:
                raise WorkbookExportError(f"{where}: pooled requirements have no columns here")
            return None, 0
        if not specs:
            return None, 0
        if len(specs) > 1:
            raise WorkbookExportError(f"{where}: the workbook holds one pooled requirement")
        spec = specs[0]
        if (
            spec.resource_type != mapping.resource_type
            or spec.ordinal != 0
            or spec.capacity_rule != CapacityRule.parse(mapping.capacity_rule)
        ):
            raise WorkbookExportError(f"{where}: this pooled requirement has no columns")
        try:
            parsed = parse(spec.filter)
        except ValueError:
            parsed = None
        clauses = parsed.clauses if parsed is not None else ()
        if len(clauses) != 1 or not isinstance(clauses[0], TagClause) or clauses[0].negate:
            raise WorkbookExportError(f'{where}: filter "{spec.filter}" is not a single tag test')
        if clauses[0].key != mapping.tag:
            raise WorkbookExportError(
                f'{where}: filter "{spec.filter}" does not test {mapping.tag}'
            )
        if mapping.count_column is None and spec.count != 1:
            raise WorkbookExportError(f"{where}: count {spec.count} has no column here")
        return clauses[0].value, spec.count

    # -- one sheet at a time --

    def rows(self, sheet: SheetDef) -> list[Values]:
        build: dict[str, Callable[[SheetDef], list[Values]]] = {
            "meta": self.meta_rows,
            "day": self.day_rows,
            "period": self.period_rows,
            "start_pattern": self.pattern_rows,
            "resource": self.resource_rows,
            "reference": self.reference_rows,
            "template": self.template_rows,
            "event": self.event_rows,
            "fixed": self.fixed_rows,
            "availability": self.availability_rows,
            "constraint": self.constraint_rows,
            "pin": self.pin_rows,
            "assignment": self.assignment_rows,
        }
        return build[sheet.target](sheet)

    def by_field(self, sheet: SheetDef, fields: Mapping[str, Cell]) -> Values:
        """Map values keyed by field name onto the sheet's columns (skipping absent ones)."""
        out: Values = {}
        for column in sheet.columns:
            if column.field in fields:
                value = fields[column.field]
                out[column.name] = column.to_shown(value) if isinstance(value, str) else value
        return out

    def meta_rows(self, sheet: SheetDef) -> list[Values]:
        clash = {"format_version", "preset"} & set(self.data.meta)
        if clash:
            raise WorkbookExportError(f"_meta: {sorted(clash)} are written by the exporter")
        pairs = [("format_version", "1"), ("preset", self.preset.name)]
        pairs += sorted(self.data.meta.items())
        return [{"key": k, "value": v} for k, v in pairs]

    def day_rows(self, sheet: SheetDef) -> list[Values]:
        return [
            self.by_field(sheet, {"code": d.code, "label": text_or_none(d.label), "order": d.order})
            for d in self.ds.time.days
        ]

    def period_rows(self, sheet: SheetDef) -> list[Values]:
        return [
            self.by_field(
                sheet,
                {
                    "code": p.code,
                    "start": format_time(p.start),
                    "end": format_time(p.end),
                    "order": p.order,
                    "is_break": p.is_break,
                },
            )
            for p in self.ds.time.periods
        ]

    def pattern_rows(self, sheet: SheetDef) -> list[Values]:
        return [
            self.by_field(
                sheet,
                {
                    "code": s.code,
                    "duration": s.duration,
                    "start_periods": format_list(s.start_periods, s.code),
                    "days": format_list(s.days or (), s.code),
                },
            )
            for s in self.ds.time.start_patterns
        ]

    def resource_rows(self, sheet: SheetDef) -> list[Values]:
        rows = []
        tag_fields = {c.field.split(":", 1)[1] for c in sheet.columns if c.field.startswith("tag:")}
        attr_fields = {
            c.field.split(":", 1)[1] for c in sheet.columns if c.field.startswith("attr:")
        }
        for r in self.ds.resources:
            if r.type != sheet.resource_type:
                continue
            extra_attrs = {k for k, _ in r.attributes} - attr_fields
            if extra_attrs:
                raise WorkbookExportError(
                    f'{sheet.name} "{r.code}": attributes {sorted(extra_attrs)} have no column'
                )
            fields: dict[str, Cell] = {
                "code": r.code,
                "name": text_or_none(r.name),
                "parent": r.parent,
                "capacity": r.capacity,
                "tags": format_pairs(((k, v) for k, v in r.tags if k not in tag_fields), r.code),
            }
            for name in attr_fields:
                value = r.attribute(name)
                fields[f"attr:{name}"] = None if value is None else str(value)
            for key in tag_fields:
                fields[f"tag:{key}"] = r.tag(key)
            if r.parent is not None:
                self.require_sheet(
                    r.parent, self.refs_of(sheet, "parent"), f'{sheet.name} "{r.code}" parent'
                )
            rows.append(self.checked(sheet, r.code, self.by_field(sheet, fields)))
        return rows

    def checked(self, sheet: SheetDef, key: str, values: Values) -> Values:
        """Fail on an empty required column: the workbook could not be read back."""
        for column in sheet.columns:
            if column.required and column.name in values and values[column.name] is None:
                raise WorkbookExportError(f'{sheet.name} "{key}": {column.name} is required')
        return values

    def reference_rows(self, sheet: SheetDef) -> list[Values]:
        rows = []
        attr_fields = {
            c.field.split(":", 1)[1] for c in sheet.columns if c.field.startswith("attr:")
        }
        for ref in self.ds.references:
            if ref.type != sheet.reference_type:
                continue
            extra = {k for k, _ in ref.attributes} - attr_fields
            if extra:
                raise WorkbookExportError(
                    f'{sheet.name} "{ref.code}": attributes {sorted(extra)} have no column'
                )
            fields: dict[str, Cell] = {
                "code": ref.code,
                "name": text_or_none(ref.name),
                "tags": format_pairs(ref.tags, ref.code),
            }
            for name in attr_fields:
                value = dict(ref.attributes).get(name)
                fields[f"attr:{name}"] = None if value is None else str(value)
            rows.append(self.by_field(sheet, fields))
        for ref in self.ds.references:
            if not any(
                ref.type == s.reference_type for s in self.preset.sheets if s.target == "reference"
            ):
                raise WorkbookExportError(f'reference "{ref.code}": type "{ref.type}" has no sheet')
        return rows

    def template_rows(self, sheet: SheetDef) -> list[Values]:
        rows = []
        for t in self.ds.templates:
            room_type, _ = self.pooled_columns(sheet, list(t.pooled), f'template "{t.code}"')
            rows.append(
                self.by_field(
                    sheet,
                    {
                        "code": t.code,
                        "reference": t.reference,
                        "kind": t.kind,
                        "mode": t.mode,
                        "targets": t.targets,
                        "batch_size": t.batch_size,
                        "fixed": format_list(t.fixed, t.code),
                        "duration": t.duration,
                        "start_pattern": t.start_pattern,
                        "pooled_type": room_type,
                        "sessions_per_week": t.sessions_per_week,
                        "active": t.active,
                    },
                )
            )
        return rows

    def event_rows(self, sheet: SheetDef) -> list[Values]:
        rows = []
        for e in self.ds.events:
            room_type, count = self.pooled_columns(
                sheet, self.pooled.get(e.code, []), f'event "{e.code}"'
            )
            rows.append(
                self.by_field(
                    sheet,
                    {
                        "code": e.code,
                        "reference": e.reference,
                        "kind": e.kind,
                        "duration": e.duration,
                        "start_pattern": e.start_pattern,
                        "delivery": e.delivery,
                        "pooled_type": room_type,
                        "pooled_count": count,
                        "template": e.template,
                        "tags": format_pairs(e.tags, e.code),
                    },
                )
            )
        return rows

    def fixed_rows(self, sheet: SheetDef) -> list[Values]:
        refs = self.refs_of(sheet, "resource")
        rows = []
        for f in self.ds.fixed:
            if self.sheet_of.get(f.resource) in refs:
                rows.append(self.by_field(sheet, {"event": f.event, "resource": f.resource}))
        return rows

    def availability_rows(self, sheet: SheetDef) -> list[Values]:
        period_column = next(c for c in sheet.columns if c.field == "period")
        all_periods = [p.code for p in self.ds.time.periods]
        groups: dict[tuple[str, str, str], list[str]] = {}
        for a in self.ds.availability:
            groups.setdefault((a.resource, a.day, a.status), []).append(a.period)
        rows = []
        for (resource, day, status), periods in groups.items():
            whole_day = (
                period_column.allow_star and all_periods and set(periods) == set(all_periods)
            )
            for period in [STAR] if whole_day else periods:
                rows.append(
                    self.by_field(
                        sheet,
                        {"resource": resource, "day": day, "period": period, "status": status},
                    )
                )
        return rows

    def constraint_rows(self, sheet: SheetDef) -> list[Values]:
        return [
            self.by_field(
                sheet,
                {
                    "code": c.code,
                    "type": c.type,
                    "scope": c.scope,
                    "params": json.dumps(c.params, sort_keys=True) if c.params else None,
                    "hard": c.hard,
                    "weight": c.weight,
                    "active": c.active,
                },
            )
            for c in self.ds.constraints
        ]

    def pin_rows(self, sheet: SheetDef) -> list[Values]:
        return [
            self.by_field(
                sheet,
                {
                    "event": p.event,
                    "day": p.day,
                    "start_period": p.start_period,
                    "resources": format_list(p.resources, p.event),
                    "source": p.source,
                },
            )
            for p in self.ds.pins
        ]

    def assignment_rows(self, sheet: SheetDef) -> list[Values]:
        result = self.data.result
        if result is None:
            return []
        events = {e.code: e for e in self.ds.events}
        periods = {p.code: p for p in self.ds.time.periods}
        rows = []
        for a in result.assignments:
            event = events.get(a.event)
            chosen = sorted({r for c in a.chosen for r in c.resources})
            fields: dict[str, Cell] = {
                "run": text_or_none(self.data.run),
                "event": a.event,
                "day": a.day,
                "resources": format_list(chosen, a.event),
            }
            start_period = periods.get(a.start_period)
            if start_period is not None:
                fields["start"] = format_time(start_period.start)
                if event is not None:
                    fields["end"] = self.end_time(a.day, a.start_period, event)
            values = self.by_field(sheet, fields)
            for column in sheet.columns:
                if column.derive is not None and column.derive != "end":
                    values[column.name] = self.derived(column, a.event, event, chosen)
            rows.append(values)
        return rows

    def end_time(self, day: str, period: str, event: Event) -> str | None:
        try:
            last = self.grid.slot(day, period) + event.duration - 1
            _, last_period = self.grid.codes(last)
        except ValueError:
            return None
        if self.grid.day_index(last) != self.grid.day_index(self.grid.slot(day, period)):
            return None
        return format_time(next(p.end for p in self.ds.time.periods if p.code == last_period))

    def derived(self, column: ColumnDef, code: str, event: Event | None, chosen: list[str]) -> Cell:
        kind, _, argument = (column.derive or "").partition(":")
        if kind == "event.reference":
            return event.reference if event else None
        if kind == "event.kind":
            return event.kind if event else None
        sheet = self.preset.sheet(argument)
        if kind == "fixed" and sheet is not None:
            refs = self.refs_of(sheet, "resource")
            found = [
                f.resource
                for f in self.ds.fixed
                if f.event == code and self.sheet_of.get(f.resource) in refs
            ]
            return format_list(found, code)
        if kind == "ancestors":
            found_up: set[str] = set()
            parents = {r.code: r.parent for r in self.ds.resources}
            for start in chosen:
                current = parents.get(start)
                seen: set[str] = set()
                while current is not None and current not in seen:
                    seen.add(current)
                    if self.sheet_of.get(current) == argument:
                        found_up.add(current)
                    current = parents.get(current)
            return format_list(sorted(found_up), code)
        raise WorkbookExportError(f'unknown derived column "{column.derive}"')


def build_tables(data: WorkbookData, preset: Preset) -> list[Table]:
    """Every sheet of the workbook, in the preset's order. `Assignments` only with a result."""
    export = _Export(data, preset)
    tables = []
    for sheet in preset.sheets:
        if sheet.export_only and data.result is None:
            continue
        rows = export.rows(sheet)
        defined = [c for c in sheet.columns if not c.convenience]
        keys = [row_key(sheet, r) for r in rows]

        extras: set[str] = set()
        for key in keys:
            extras |= {h for h, v in data.notes.get((sheet.name, key), {}).items() if v != ""}
        headers = tuple(c.name for c in defined) + tuple(sorted(extras))

        cells = []
        for key, values in zip(keys, rows, strict=True):
            notes = data.notes.get((sheet.name, key), {})
            cells.append(
                tuple(
                    values.get(h)
                    if h in values
                    else _note(notes, h, defined_names={c.name for c in defined})
                    for h in headers
                )
            )
        tables.append(Table(sheet.name, headers, tuple(cells)))
    return tables


def _note(notes: Mapping[str, str], header: str, defined_names: set[str]) -> Cell:
    if header in defined_names:
        return None
    value = notes.get(header)
    return value if value else None


__all__ = [
    "Cell",
    "Table",
    "WorkbookData",
    "WorkbookError",
    "WorkbookExportError",
    "build_tables",
    "format_list",
    "format_pairs",
    "format_time",
    "row_key",
]
