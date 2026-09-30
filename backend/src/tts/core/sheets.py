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

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ConfigIssue:
    """A mistake a preset finds in the configuration, placed on a row (by code) and a column."""

    sheet: str
    code: str
    column: str
    message: str


class ColumnDef(_Frozen):
    """One column of a sheet.

    `refs` lists the sheets whose codes the value must name (for a `list` column, each item).
    `required_when` is a (column, value) pair: the column is required when that other column
    holds that value. `expands_to` marks a convenience column: on import its items become rows of
    the named join sheet, and it is never written on export. A column with `derive` is
    descriptive: written on export only, computed as one of `event.reference`, `event.kind`,
    `end` (the end time of the last covered period), `fixed:<join sheet>` (the event's fixed
    resources that sheet lists) or `ancestors:<resource sheet>` (the chosen resources' ancestors
    of that sheet's type).
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
    derive: str | None = None
    label: str = ""
    stored_as: tuple[tuple[str, str], ...] = ()

    def to_stored(self, value: str) -> str:
        """The value the core model keeps for a workbook value."""
        return dict(self.stored_as).get(value, value)

    def to_shown(self, value: str) -> str:
        """The workbook value for a value the core model keeps."""
        return {stored: shown for shown, stored in self.stored_as}.get(value, value)

    @property
    def convenience(self) -> bool:
        return self.expands_to is not None

    @property
    def derived(self) -> bool:
        return self.derive is not None


class PooledMapping(_Frozen):
    """Columns that stand for a pooled requirement (for example a room type and a count).

    With a `type_column`, the requirement's filter is the tag test `tag=<value>` and a blank value
    means no requirement. Without one, any resource of `resource_type` will do (filter `all`) and
    the requirement exists whenever its count is at least 1. Without a `count_column` the count
    is 1. The n-th mapping of a sheet (ADR-0006) is the requirement with ordinal n, and its
    columns use the fields `pooled_type:<n>` and `pooled_count:<n>` (plain `pooled_type` and
    `pooled_count` for the first).
    """

    resource_type: str
    capacity_rule: str
    tag: str | None = None
    type_column: str | None = None
    count_column: str | None = None


class SheetDef(_Frozen):
    """One sheet: its columns and the core table its rows become."""

    name: str
    target: Target
    columns: tuple[ColumnDef, ...]
    resource_type: str | None = None
    reference_type: str | None = None
    pooled: PooledMapping | None = None
    more_pooled: tuple[PooledMapping, ...] = ()
    export_only: bool = False
    label: str = ""

    def column(self, name: str) -> ColumnDef | None:
        return next((c for c in self.columns if c.name == name), None)

    @property
    def pooled_mappings(self) -> tuple[PooledMapping, ...]:
        """Every pooled mapping, in ordinal order (ADR-0006)."""
        return ((self.pooled,) if self.pooled is not None else ()) + self.more_pooled

    @property
    def required_columns(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns if c.required)


class Preset(_Frozen):
    """A packaged domain: its types, sheets and default vocabulary. No scheduling logic."""

    name: str
    resource_types: tuple[ResourceType, ...]
    reference_types: tuple[ReferenceType, ...]
    sheets: tuple[SheetDef, ...]
    format_version: int = 1

    def sheet(self, name: str) -> SheetDef | None:
        return next((s for s in self.sheets if s.name == name), None)
