"""Check any timetable against the rules (FR-14): a workbook with assignments or a FET export."""

from typing import Literal

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

from tts.api.deps import DbSession
from tts.api.errors import ApiError
from tts.api.workbooks import problems
from tts.core.model import Dataset, Result
from tts.core.verifier import hard_violations, verify
from tts.io.csvzip import MAX_BYTES, import_csvzip
from tts.io.fet_html import (
    FetConversionError,
    FetParseError,
    parse_fet_groups_html_text,
    to_dataset,
)
from tts.io.workbook import import_xlsx

router = APIRouter(tags=["validate"])


class RefOut(BaseModel):
    kind: str
    code: str


class ViolationOut(BaseModel):
    code: str
    constraint_code: str
    severity: str
    penalty: int
    refs: list[RefOut]
    message: str


class ValidateOut(BaseModel):
    source: Literal["workbook", "fet"]
    valid: bool
    hard: int
    soft: int
    warnings: int
    events: int
    placed: int
    violations: list[ViolationOut]


def _report(source: Literal["workbook", "fet"], dataset: Dataset, result: Result) -> ValidateOut:
    violations = verify(dataset, result)
    return ValidateOut(
        source=source,
        valid=not hard_violations(violations),
        hard=len(hard_violations(violations)),
        soft=sum(v.severity == "soft" for v in violations),
        warnings=sum(v.severity == "warning" for v in violations),
        events=len(dataset.events),
        placed=len(result.assignments),
        violations=[
            ViolationOut(
                code=v.code,
                constraint_code=v.constraint_code,
                severity=v.severity,
                penalty=v.penalty,
                refs=[RefOut(kind=r.kind, code=r.code) for r in v.refs],
                message=v.message,
            )
            for v in violations
        ],
    )


@router.post("/validate")
async def validate(file: UploadFile, session: DbSession) -> ValidateOut:
    """Upload a workbook (`.xlsx` or CSV `.zip`) with an Assignments sheet, or a FET groups HTML.

    Nothing is stored. Every violation is returned.
    """
    del session  # nothing is read from or written to the database
    name = (file.filename or "").lower()
    payload = await file.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ApiError(413, "too_large", "the file is larger than 20 MB")

    if name.endswith((".html", ".htm")) or payload.lstrip()[:1] == b"<":
        try:
            fet = parse_fet_groups_html_text(payload.decode("utf-8", errors="replace"))
            dataset, result = to_dataset(fet)
        except (FetParseError, FetConversionError) as error:
            raise ApiError(422, "invalid_fet_export", str(error)) from None
        return _report("fet", dataset, result)

    outcome = import_csvzip(payload) if name.endswith(".zip") else import_xlsx(payload)
    if outcome.data is None:
        raise ApiError(422, "invalid_workbook", "the workbook has problems", problems(outcome))
    if outcome.data.result is None:
        raise ApiError(422, "no_assignments", "the workbook has no Assignments sheet to check")
    return _report("workbook", outcome.data.dataset, outcome.data.result)
