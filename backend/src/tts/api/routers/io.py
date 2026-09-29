"""Import and export of a dataset's whole configuration as a workbook."""

import zipfile
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, UploadFile
from fastapi.responses import Response

from tts.api.deps import DbSession
from tts.api.errors import ApiError
from tts.api.schemas import ImportProblem, ImportResult
from tts.api.workbooks import load_data, preset_of, problems, save_data
from tts.io.csvzip import MAX_BYTES, export_csvzip, import_csvzip
from tts.io.tables import WorkbookError
from tts.io.workbook import export_xlsx, import_xlsx

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["io"])


def _is_xlsx(name: str, payload: bytes) -> bool:
    if name.lower().endswith(".xlsx"):
        return True
    if name.lower().endswith(".zip"):
        return False
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            return "[Content_Types].xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


@router.post("/import")
async def import_workbook(dataset_id: int, file: UploadFile, session: DbSession) -> ImportResult:
    """Replace the dataset with the workbook's content. Any problem changes nothing."""
    preset = preset_of(session, dataset_id)
    payload = await file.read(MAX_BYTES + 1)
    if _is_xlsx(file.filename or "", payload):
        outcome = import_xlsx(payload, preset)
    else:
        outcome = import_csvzip(payload, preset)
    if outcome.data is None:
        return ImportResult(
            ok=False,
            errors=[ImportProblem(**p) for p in problems(outcome)],
            summary=outcome.summary,
        )
    save_data(session, dataset_id, outcome.data)
    return ImportResult(ok=True, summary=outcome.summary)


@router.get("/export")
def export_workbook(
    dataset_id: int, session: DbSession, format: Literal["xlsx", "csvzip"] = "xlsx"
) -> Response:
    preset = preset_of(session, dataset_id)
    data = load_data(session, dataset_id)
    buffer = BytesIO()
    try:
        if format == "xlsx":
            export_xlsx(data, buffer, preset)
            media, extension = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx",
            )
        else:
            export_csvzip(data, buffer, preset)
            media, extension = "application/zip", "zip"
    except WorkbookError as error:
        raise ApiError(422, "not_exportable", str(error)) from None
    return Response(
        buffer.getvalue(),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="dataset-{dataset_id}.{extension}"'},
    )
