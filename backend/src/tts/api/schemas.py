"""Request and response bodies of the API (the OpenAPI schema is generated from these)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from tts.core.model import ResourceType
from tts.core.sheets import SheetDef


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    preset: str


class DatasetPatch(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DatasetOut(BaseModel):
    id: int
    name: str
    preset: str
    kind: str
    version: int
    created_at: datetime
    updated_at: datetime


class RowOut(BaseModel):
    """One table row. `key` identifies it in `PATCH` and `DELETE` (parts joined by U+001F)."""

    key: str
    values: dict[str, Any]


class TablePage(BaseModel):
    sheet: str
    headers: list[str]
    rows: list[RowOut]
    total: int
    page: int
    size: int


class RowIn(BaseModel):
    values: dict[str, Any]


class ImportProblem(BaseModel):
    sheet: str
    row: int | None = None
    col: int | None = None
    column: str | None = None
    message: str
    text: str


class ImportResult(BaseModel):
    ok: bool
    errors: list[ImportProblem] = []
    summary: dict[str, int] = {}


class RefOut(BaseModel):
    """An entity a finding is about. `sheet` is the table that holds it, to link to its row."""

    kind: str
    code: str
    sheet: str | None = None


class IssueOut(BaseModel):
    severity: str
    kind: str
    message: str
    refs: list[RefOut] = []


class PreflightOut(BaseModel):
    issues: list[IssueOut]
    has_errors: bool


class PlannedOut(BaseModel):
    """What the solver will schedule for one module and kind of session."""

    demand: str
    module: str | None
    kind: str
    groups: list[str]
    groups_per_session: int | None
    blocks: int
    per_week: int
    sessions: int


class SchemaOut(BaseModel):
    preset: str
    kind: str
    format_version: int
    sheets: list[SheetDef]
    labels: dict[str, str]
    resource_types: list[ResourceType]
