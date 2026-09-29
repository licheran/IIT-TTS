"""Declarative sheet definitions: how tables of a workbook map onto the core model.

A preset supplies a `Preset` (its types and its sheets). The workbook reader and writer, and the
UI's table editors, are all driven by these definitions, so no code refers to a particular sheet.
The format itself is specified in `docs/spec/03-workbook-format.md`.

A sheet's `target` names the core table its rows become. Each column's `field` says which part
of that row it fills. Fields understood by every target:

- `code`, `name`, `label`, `order`, and the plain fields of the core model (`kind`, `duration`, ...)
- `parent` and `capacity` (resources)
- `tags` (a `key=value` list)
- `attr:<name>` and `tag:<key>`: one attribute or tag held in its own column
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from tts.core.model import ReferenceType, ResourceType

ColumnKind = Literal["str", "int", "bool", "time", "list", "pairs", "json", "selector"]
Target = Literal[
    "meta",
    "day",
    "period",
    "start_pattern",
    "resource",
    "reference",
    "template",
    "event",
    "fixed",
    "availability",
    "constraint",
    "pin",
    "assignment",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ColumnDef(_Frozen):
    """One column of a sheet.

    `refs` lists the sheets whose codes the value must name (for a `list` column, each item).
    `required_when` is a (column, value) pair: the column is required when that other column
    holds that value. `expands_to` marks a convenience column: on import its items become rows of
    the named join sheet, and it is never written on export. `derived` columns are descriptive
    and only written on export.
    """

    name: str
    field: str
    kind: ColumnKind = "str"
    required: bool = False
    required_when: tuple[str, str] | None = None
    refs: tuple[str, ...] = ()
    allow_star: bool = False
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    default: str | int | bool | None = None
    expands_to: str | None = None
    derived: bool = False
    label: str = ""

    @property
    def convenience(self) -> bool:
        return self.expands_to is not None


class PooledMapping(_Frozen):
    """Columns that stand for a pooled requirement (for example a room type and a count)."""

    resource_type: str
    tag: str
    capacity_rule: str
    type_column: str
    count_column: str | None = None


class SheetDef(_Frozen):
    """One sheet: its columns and the core table its rows become."""

    name: str
    target: Target
    columns: tuple[ColumnDef, ...]
    resource_type: str | None = None
    reference_type: str | None = None
    pooled: PooledMapping | None = None
    export_only: bool = False
    label: str = ""

    def column(self, name: str) -> ColumnDef | None:
        return next((c for c in self.columns if c.name == name), None)

    @property
    def required_columns(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns if c.required)


class Preset(_Frozen):
    """A packaged domain: its types, sheets and default vocabulary. No scheduling logic."""

    name: str
    resource_types: tuple[ResourceType, ...]
    reference_types: tuple[ReferenceType, ...]
    sheets: tuple[SheetDef, ...]

    def sheet(self, name: str) -> SheetDef | None:
        return next((s for s in self.sheets if s.name == name), None)
