"""Request and response bodies of the API (the OpenAPI schema is generated from these)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    preset: str


class DatasetPatch(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DatasetOut(BaseModel):
    id: int
    name: str
    preset: str
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
    kind: str
    code: str


class IssueOut(BaseModel):
    severity: str
    kind: str
    message: str
    refs: list[RefOut] = []


class PreflightOut(BaseModel):
    issues: list[IssueOut]
    has_errors: bool


class ExpandOut(BaseModel):
    committed: bool
    added: list[str] = []
    changed: list[str] = []
    removed: list[str] = []


class SchemaOut(BaseModel):
    preset: str
    format_version: int
    sheets: list[dict[str, Any]]
    labels: dict[str, str]
    resource_types: list[dict[str, Any]]
